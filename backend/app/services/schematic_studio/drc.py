from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
import uuid

from app.models.schemas import (
    SchematicSheet,
    SchematicComponentDef,
    ERCReport,
    ERCFinding,
)
from app.services.schematic_studio.catalog import build_standard_component_catalog


def run_electrical_rule_checks(
    sheet: SchematicSheet,
    custom_components: Optional[Dict[str, SchematicComponentDef]] = None,
) -> ERCReport:
    """Executes rule-based Electrical Rule Checks (ERC) on a schematic sheet."""
    catalog = build_standard_component_catalog()
    if custom_components:
        catalog.update(custom_components)

    findings: List[ERCFinding] = []
    passed_rules: List[str] = []

    # Map instance_id -> ComponentInstance
    inst_by_id = {c.instance_id: c for c in sheet.components}
    # Map (instance_id, pin_id) -> Net
    pin_to_net: Dict[tuple[str, str], str] = {}
    net_by_name = {n.name: n for n in sheet.nets}
    net_by_id = {n.net_id: n for n in sheet.nets}

    for net in sheet.nets:
        for conn in net.connections:
            pin_to_net[(conn.instance_id, conn.pin_id)] = net.name

    # Check 1: Missing Ground Reference
    has_active_components = any(
        c.component_id.startswith(("opamp", "regulator", "timer", "bjt", "mosfet", "vsource", "logic", "mcu"))
        or (c.component_id in catalog and catalog[c.component_id].category in (
            "analog_opamp", "analog_regulator", "analog_timer", "digital_logic_gate",
            "semiconductor_transistor_bjt", "semiconductor_transistor_mosfet", "power_source", "microcontroller_module"
        ))
        for c in sheet.components
    )
    ground_net_found = any(
        net.is_ground or "gnd" in net.name.lower() or "ground" in net.name.lower()
        for net in sheet.nets
    ) or any(c.component_id == "ground" for c in sheet.components)

    if has_active_components and not ground_net_found:
        findings.append(
            ERCFinding(
                finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                rule_code="ERC_MISSING_GND",
                severity="critical",
                title="Missing Ground Reference (GND)",
                message="Circuit contains active semiconductors or power sources but has no identified ground net (GND).",
                affected_components=[c.ref_des for c in sheet.components if c.component_id.startswith(("vsource", "opamp", "regulator", "timer"))],
                affected_nets=[],
                remediation_steps="Place a Ground (GND) component or label the negative return net as 'GND'.",
            )
        )
    else:
        passed_rules.append("ERC_MISSING_GND")

    # Check 2: Power and Ground Direct Short (Critical)
    shorted_nets = []
    for net in sheet.nets:
        has_pwr_out = False
        has_gnd = False
        pwr_insts = []
        gnd_insts = []

        is_gnd_net = net.is_ground or "gnd" in net.name.lower()

        for conn in net.connections:
            inst = inst_by_id.get(conn.instance_id)
            if not inst:
                continue
            comp_def = catalog.get(inst.component_id)
            if not comp_def:
                continue
            pin_def = next((p for p in comp_def.pins if p.pin_id == conn.pin_id), None)
            if not pin_def:
                continue

            if pin_def.pin_type == "power_out" or "vcc" in pin_def.name.lower() or "out" in pin_def.name.lower() and comp_def.category == "analog_regulator":
                if not ("gnd" in pin_def.name.lower()):
                    has_pwr_out = True
                    pwr_insts.append(inst.ref_des)

            if pin_def.name.lower() == "gnd" or inst.component_id == "ground" or (pin_def.pin_id == "-" and comp_def.category == "power_source"):
                has_gnd = True
                gnd_insts.append(inst.ref_des)

        if has_pwr_out and (has_gnd or is_gnd_net):
            shorted_nets.append(net.name)
            findings.append(
                ERCFinding(
                    finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                    rule_code="ERC_POWER_GND_SHORT",
                    severity="critical",
                    title=f"Catastrophic Power-GND Short on Net '{net.name}'",
                    message=f"Net '{net.name}' directly bridges positive power sources ({', '.join(pwr_insts)}) to circuit ground ({', '.join(gnd_insts)}).",
                    affected_components=list(set(pwr_insts + gnd_insts)),
                    affected_nets=[net.name],
                    remediation_steps="Disconnect power and ground pins immediately to avoid destroying power supplies and components.",
                )
            )

    if not shorted_nets:
        passed_rules.append("ERC_POWER_GND_SHORT")

    # Check 3: Rail Conflict (Connecting multiple distinct power rails e.g. 5V and 3.3V)
    for net in sheet.nets:
        power_voltages = set()
        for conn in net.connections:
            inst = inst_by_id.get(conn.instance_id)
            if not inst:
                continue
            comp_def = catalog.get(inst.component_id)
            if not comp_def:
                continue
            if inst.component_id == "rail_3v3":
                power_voltages.add(3.3)
            elif inst.component_id == "rail_5v":
                power_voltages.add(5.0)
            elif comp_def.category == "analog_regulator":
                if "3v3" in comp_def.name.lower():
                    power_voltages.add(3.3)
                elif "5v" in comp_def.name.lower() or "7805" in comp_def.name.lower():
                    power_voltages.add(5.0)

        if len(power_voltages) > 1:
            findings.append(
                ERCFinding(
                    finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                    rule_code="ERC_RAIL_CONFLICT",
                    severity="critical",
                    title=f"Power Rail Voltage Conflict on Net '{net.name}'",
                    message=f"Net '{net.name}' ties multiple distinct voltage rails together ({list(power_voltages)}V) without level translation.",
                    affected_components=[inst.ref_des for conn in net.connections if (inst := inst_by_id.get(conn.instance_id))],
                    affected_nets=[net.name],
                    remediation_steps="Separate the 3.3V and 5.0V power domains. Use a dedicated voltage regulator or bidirectional level shifter.",
                )
            )
        else:
            passed_rules.append("ERC_RAIL_CONFLICT")

    # Check 4: Floating Inputs on ICs and Logic Gates
    floating_inputs = []
    for inst in sheet.components:
        comp_def = catalog.get(inst.component_id)
        if not comp_def:
            continue
        for pin in comp_def.pins:
            if pin.pin_type == "input":
                net_name = pin_to_net.get((inst.instance_id, pin.pin_id))
                if not net_name:
                    floating_inputs.append((inst.ref_des, pin.name))
                else:
                    # Check if net has only 1 connection
                    net_obj = net_by_name.get(net_name)
                    if net_obj and len(net_obj.connections) < 2:
                        floating_inputs.append((inst.ref_des, pin.name))

    if floating_inputs:
        for ref_des, pin_name in floating_inputs:
            findings.append(
                ERCFinding(
                    finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                    rule_code="ERC_FLOATING_INPUT",
                    severity="warning",
                    title=f"Floating Input Pin: {ref_des}.{pin_name}",
                    message=f"High-impedance input pin '{pin_name}' on '{ref_des}' is unconnected. Floating CMOS inputs cause oscillation and high quiescent current.",
                    affected_components=[ref_des],
                    affected_nets=[],
                    remediation_steps="Tie unused CMOS inputs to VCC or GND, or connect appropriate drive signals.",
                )
            )
    else:
        passed_rules.append("ERC_FLOATING_INPUT")

    # Check 5: Output Contention (Multiple output pins driving the same net)
    for net in sheet.nets:
        output_pins = []
        for conn in net.connections:
            inst = inst_by_id.get(conn.instance_id)
            if not inst:
                continue
            comp_def = catalog.get(inst.component_id)
            if not comp_def:
                continue
            pin_def = next((p for p in comp_def.pins if p.pin_id == conn.pin_id), None)
            if pin_def and pin_def.pin_type == "output":
                output_pins.append(f"{inst.ref_des}.{pin_def.name}")

        if len(output_pins) > 1:
            findings.append(
                ERCFinding(
                    finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                    rule_code="ERC_OUTPUT_CONTENTION",
                    severity="critical",
                    title=f"Output Contention on Net '{net.name}'",
                    message=f"Multiple active push-pull outputs ({', '.join(output_pins)}) are shorted together on net '{net.name}'.",
                    affected_components=[p.split(".")[0] for p in output_pins],
                    affected_nets=[net.name],
                    remediation_steps="Isolate outputs using logic gates, multiplexers, or open-collector outputs with a shared pull-up.",
                )
            )
        else:
            passed_rules.append("ERC_OUTPUT_CONTENTION")

    # Check 6: LED Connected Without Current-Limiting Resistor
    for inst in sheet.components:
        comp_def = catalog.get(inst.component_id)
        if comp_def and comp_def.category == "semiconductor_led":
            anode_net = pin_to_net.get((inst.instance_id, "A"))
            cathode_net = pin_to_net.get((inst.instance_id, "K"))

            # Check if anode is directly on a power rail and cathode on GND with no resistor
            is_direct_power = False
            if anode_net and cathode_net:
                anode_is_pwr = any("vcc" in anode_net.lower() or "5v" in anode_net.lower() or "3v3" in anode_net.lower() for _ in [1])
                cathode_is_gnd = "gnd" in cathode_net.lower()
                if anode_is_pwr and cathode_is_gnd:
                    # Check if any resistor is in either net
                    anode_net_obj = net_by_name.get(anode_net)
                    cathode_net_obj = net_by_name.get(cathode_net)
                    has_resistor = False
                    for conn in (anode_net_obj.connections if anode_net_obj else []) + (cathode_net_obj.connections if cathode_net_obj else []):
                        other_inst = inst_by_id.get(conn.instance_id)
                        if other_inst and other_inst.ref_des.startswith("R"):
                            has_resistor = True
                            break
                    if not has_resistor:
                        is_direct_power = True

            if is_direct_power:
                findings.append(
                    ERCFinding(
                        finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                        rule_code="ERC_OVERCURRENT_WARNING",
                        severity="critical",
                        title=f"LED {inst.ref_des} Connected Directly Across Power Rail Without Resistor",
                        message=f"LED '{inst.ref_des}' is wired directly between power and ground without a series current-limiting resistor. Immediate burnout will occur.",
                        affected_components=[inst.ref_des],
                        affected_nets=[anode_net, cathode_net],
                        remediation_steps="Insert a series current-limiting resistor (e.g. 220 to 470 ohms) in series with the LED anode or cathode.",
                    )
                )

    # Check 7: Reverse Polarity on Polarized Capacitors
    for inst in sheet.components:
        comp_def = catalog.get(inst.component_id)
        if comp_def and comp_def.symbol_type == "capacitor_polarized":
            plus_net = pin_to_net.get((inst.instance_id, "1"))
            minus_net = pin_to_net.get((inst.instance_id, "2"))
            if plus_net and minus_net:
                if "gnd" in plus_net.lower() and any(k in minus_net.lower() for k in ["vcc", "5v", "3v3", "12v", "+"]):
                    findings.append(
                        ERCFinding(
                            finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                            rule_code="ERC_REVERSE_POLARITY",
                            severity="critical",
                            title=f"Reverse Polarity on Electrolytic Capacitor {inst.ref_des}",
                            message=f"Polarized capacitor '{inst.ref_des}' has its positive terminal (+) connected to ground net '{plus_net}' and negative terminal (-) to positive rail '{minus_net}'.",
                            affected_components=[inst.ref_des],
                            affected_nets=[plus_net, minus_net],
                            remediation_steps="Swap the connections to ensure positive terminal connects to positive supply and negative terminal connects to GND.",
                        )
                    )

    # Check 8: Open-Collector Pin Without Pull-Up Resistor
    for inst in sheet.components:
        comp_def = catalog.get(inst.component_id)
        if not comp_def:
            continue
        for pin in comp_def.pins:
            if pin.pin_type == "open_collector":
                net_name = pin_to_net.get((inst.instance_id, pin.pin_id))
                if net_name:
                    net_obj = net_by_name.get(net_name)
                    has_pullup = False
                    if net_obj:
                        for conn in net_obj.connections:
                            other_inst = inst_by_id.get(conn.instance_id)
                            if other_inst and other_inst.ref_des.startswith("R"):
                                has_pullup = True
                                break
                    if not has_pullup:
                        findings.append(
                            ERCFinding(
                                finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                                rule_code="ERC_MISSING_PULLUP",
                                severity="warning",
                                title=f"Open-Collector Pin {inst.ref_des}.{pin.name} Lacks Pull-Up Resistor",
                                message=f"Pin '{pin.name}' on '{inst.ref_des}' has an open-collector/open-drain stage but net '{net_name}' has no pull-up resistor to VCC.",
                                affected_components=[inst.ref_des],
                                affected_nets=[net_name],
                                remediation_steps="Add a pull-up resistor (e.g. 4.7k to 10k ohms) between the net and the positive supply rail.",
                            )
                        )

    # Check 9: Decoupling Capacitor Recommendation for Active ICs
    for inst in sheet.components:
        comp_def = catalog.get(inst.component_id)
        if comp_def and comp_def.category in ("analog_opamp", "analog_timer", "digital_logic_gate", "microcontroller_module"):
            vcc_pin = next((p for p in comp_def.pins if p.pin_type == "power_in" and "v" in p.name.lower()), None)
            if vcc_pin:
                net_name = pin_to_net.get((inst.instance_id, vcc_pin.pin_id))
                if net_name:
                    net_obj = net_by_name.get(net_name)
                    has_decoupling_cap = False
                    if net_obj:
                        for conn in net_obj.connections:
                            other_inst = inst_by_id.get(conn.instance_id)
                            if other_inst and other_inst.ref_des.startswith("C"):
                                has_decoupling_cap = True
                                break
                    if not has_decoupling_cap:
                        findings.append(
                            ERCFinding(
                                finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                                rule_code="ERC_MISSING_DECOUPLING",
                                severity="info",
                                title=f"Recommended Decoupling Capacitor for IC {inst.ref_des}",
                                message=f"Power rail for '{inst.ref_des}' has no nearby high-frequency decoupling capacitor (e.g. 100nF ceramic).",
                                affected_components=[inst.ref_des],
                                affected_nets=[net_name],
                                remediation_steps="Place a 100nF ceramic capacitor physically close to the IC VCC and GND pins.",
                            )
                        )

    # Check 10: Uncertain Component Ratings
    for inst in sheet.components:
        comp_def = catalog.get(inst.component_id)
        if not comp_def or comp_def.spec_verification == "user_defined" or (comp_def.max_voltage_v is None and comp_def.max_power_mw is None):
            findings.append(
                ERCFinding(
                    finding_id=f"erc_{uuid.uuid4().hex[:8]}",
                    rule_code="ERC_UNCERTAIN_RATING",
                    severity="info",
                    title=f"Unverified Electrical Ratings for {inst.ref_des}",
                    message=f"Component '{inst.ref_des}' ({inst.component_id}) lacks verified maximum voltage/power ratings in the catalog.",
                    affected_components=[inst.ref_des],
                    affected_nets=[],
                    remediation_steps="Verify operating limits against manufacturer datasheet before high-voltage or high-power deployment.",
                )
            )

    crit_count = sum(1 for f in findings if f.severity == "critical")
    warn_count = sum(1 for f in findings if f.severity == "warning")
    info_count = sum(1 for f in findings if f.severity == "info")

    return ERCReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_findings=len(findings),
        critical_count=crit_count,
        warning_count=warn_count,
        info_count=info_count,
        findings=findings,
        passed_rule_checks=list(set(passed_rules)),
    )
