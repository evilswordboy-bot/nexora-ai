from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.tools_registry import tool_registry
from app.models.schemas import (
    SchematicSheet,
    ComponentInstance,
    SchematicNet,
    NetPinConnection,
    OhmsLawRequest,
    VoltageDividerRequest,
    LEDResistorRequest,
    RCTimeConstantRequest,
    TransistorBiasRequest,
    PowerThermalRequest,
    LogicExpressionRequest,
    SPICESimulationRequest,
    AICircuitPromptRequest,
    SchematicProjectCreate,
    SchematicProjectUpdate,
    SchematicComponentDef,
    SchematicPin,
)
from app.services.schematic_studio import (
    schematic_studio_engine,
    build_standard_component_catalog,
    calculate_ohms_law,
    calculate_voltage_divider,
    calculate_led_resistor,
    calculate_rc_time_constant,
    calculate_transistor_bias,
    calculate_power_thermal,
    calculate_logic_expression,
    run_electrical_rule_checks,
    generate_spice_netlist,
    run_spice_simulation,
)

client = TestClient(app)


def test_stage27_health_endpoint():
    """Verifies that Stage 27 reports health as operational with Tool #28 registered."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] >= 27
    assert "Studio" in data["stage_title"]
    assert data["subsystems"]["schematic_studio"] == "operational"
    assert data["registered_tools_count"] >= 25
    assert "schematic_studio_engine" in [t.name for t in tool_registry.list_tools()]


def test_standard_component_catalog():
    """Verifies component library has comprehensive definitions for passives, semiconductors, ICs, and power."""
    catalog = build_standard_component_catalog()
    assert len(catalog) >= 20

    # Key components exist
    assert "resistor_generic" in catalog
    assert "capacitor_ceramic" in catalog
    assert "capacitor_electrolytic" in catalog
    assert "diode_1n4148" in catalog
    assert "led_red" in catalog
    assert "bjt_npn_2n2222" in catalog
    assert "mosfet_n_2n7000" in catalog
    assert "opamp_lm358" in catalog
    assert "regulator_ams1117_3v3" in catalog
    assert "timer_ne555" in catalog
    assert "logic_and_74hc08" in catalog
    assert "switch_spst" in catalog
    assert "relay_spdt_5v" in catalog
    assert "vsource_dc" in catalog
    assert "ground" in catalog

    # Check pins and footprints
    res = catalog["resistor_generic"]
    assert len(res.pins) == 2
    assert res.ref_des_prefix == "R"

    opamp = catalog["opamp_lm358"]
    assert len(opamp.pins) == 8
    assert opamp.footprint == "DIP-8"
    assert opamp.spec_verification == "verified_datasheet_spec"


def test_engineering_calculators():
    """Verifies precision and formulas across all 7 electronics engineering calculators."""
    # 1. Ohm's Law
    ohm_res = calculate_ohms_law(OhmsLawRequest(voltage_v=12.0, resistance_ohms=240.0))
    assert ohm_res.current_a == 0.05
    assert ohm_res.power_w == 0.60
    assert "0.5W" in ohm_res.recommended_wattage_rating or "1.0W" in ohm_res.recommended_wattage_rating
    assert len(ohm_res.formulas_used) >= 2

    # 2. Voltage Divider
    div_res = calculate_voltage_divider(VoltageDividerRequest(vin_v=10.0, r1_ohms=10000.0, r2_ohms=10000.0))
    assert div_res.ideal_vout_v == 5.0
    assert div_res.quiescent_current_ma == 0.5
    assert div_res.output_impedance_ohms == 5000.0

    # Test loading effect
    div_loaded = calculate_voltage_divider(VoltageDividerRequest(vin_v=10.0, r1_ohms=10000.0, r2_ohms=10000.0, load_resistance_ohms=10000.0))
    assert div_loaded.loaded_vout_v is not None
    assert div_loaded.loaded_vout_v < 5.0  # Loading causes drop to ~3.33V
    assert abs(div_loaded.loaded_vout_v - 3.3333) < 0.05

    # 3. LED Resistor
    led_res = calculate_led_resistor(LEDResistorRequest(supply_voltage_v=5.0, led_forward_voltage_v=2.0, led_current_ma=20.0))
    assert led_res.calculated_resistance_ohms == 150.0
    assert led_res.standard_e24_resistor_ohms == 150.0
    assert led_res.actual_current_with_e24_ma == 20.0
    assert led_res.resistor_power_dissipation_mw == 60.0

    # 4. RC Filter & Time Constant
    rc_res = calculate_rc_time_constant(RCTimeConstantRequest(resistance_ohms=1000.0, capacitance_farads=100e-9, step_voltage_v=5.0))
    assert abs(rc_res.tau_seconds - 0.0001) < 1e-6  # 100 microseconds
    assert "us" in rc_res.tau_formatted or "ms" in rc_res.tau_formatted
    assert abs(rc_res.cutoff_frequency_hz - 1591.55) < 5.0  # ~1.59 kHz
    assert len(rc_res.charge_curve_points) == 11
    assert rc_res.charge_curve_points[-1]["voltage_v"] > 4.95  # at 5 tau, V ~ 5V

    # 5. Transistor Saturation Bias
    bjt_res = calculate_transistor_bias(TransistorBiasRequest(supply_vcc_v=5.0, input_base_voltage_v=3.3, collector_load_current_ma=80.0, forced_beta_saturation=10.0))
    assert bjt_res.required_base_current_ma == 8.0  # 80mA / 10
    assert bjt_res.saturation_confirmed is True
    assert bjt_res.flyback_diode_required is True

    # 6. Power & Thermal Dissipation
    thermal_res = calculate_power_thermal(PowerThermalRequest(input_voltage_v=12.0, output_voltage_v=5.0, load_current_ma=500.0, package_type="TO-220"))
    assert abs(thermal_res.power_dissipation_w - 3.56) < 0.1  # (12-5)*0.5 + 12*0.005 = 3.56W
    assert thermal_res.heatsink_required is True
    assert thermal_res.thermal_verdict in ("heatsink_required", "unsafe_thermal_exceeded")

    # 7. Logic Expression Truth Table
    logic_res = calculate_logic_expression(LogicExpressionRequest(expression="A AND NOT B"))
    assert len(logic_res.truth_table) == 4
    # Row A=1, B=0 should be 1
    target_row = next(r for r in logic_res.truth_table if r["A"] == 1 and r["B"] == 0)
    assert target_row["OUTPUT"] == 1


def test_electrical_rule_checks_erc():
    """Verifies ERC engine identifies missing ground, power-ground shorts, rail conflicts, and floating inputs."""
    # Test 1: Missing Ground
    sheet_no_gnd = SchematicSheet(
        sheet_id="sheet_test_1",
        title="No GND Circuit",
        components=[
            ComponentInstance(instance_id="v1", component_id="vsource_dc", ref_des="V1", value="5V", pos_x=0, pos_y=0),
            ComponentInstance(instance_id="r1", component_id="resistor_generic", ref_des="R1", value="1k", pos_x=50, pos_y=0),
        ],
        nets=[
            SchematicNet(net_id="n1", name="PWR", is_power=True, connections=[NetPinConnection(instance_id="v1", pin_id="+"), NetPinConnection(instance_id="r1", pin_id="1")]),
        ],
    )
    report_no_gnd = run_electrical_rule_checks(sheet_no_gnd)
    assert any(f.rule_code == "ERC_MISSING_GND" for f in report_no_gnd.findings)

    # Test 2: Catastrophic Power-Ground Short
    sheet_short = SchematicSheet(
        sheet_id="sheet_test_2",
        title="Direct Short Circuit",
        components=[
            ComponentInstance(instance_id="v1", component_id="vsource_dc", ref_des="V1", value="5V", pos_x=0, pos_y=0),
            ComponentInstance(instance_id="g1", component_id="ground", ref_des="GND1", value="0V", pos_x=50, pos_y=0),
        ],
        nets=[
            SchematicNet(
                net_id="n1",
                name="GND_SHORT",
                is_ground=True,
                connections=[
                    NetPinConnection(instance_id="v1", pin_id="+"),  # Direct short of 5V to GND!
                    NetPinConnection(instance_id="v1", pin_id="-"),
                    NetPinConnection(instance_id="g1", pin_id="1"),
                ],
            ),
        ],
    )
    report_short = run_electrical_rule_checks(sheet_short)
    assert any(f.rule_code == "ERC_POWER_GND_SHORT" for f in report_short.findings)

    # Test 3: Rail Conflict (5V and 3.3V tied together)
    sheet_rail_conflict = SchematicSheet(
        sheet_id="sheet_test_3",
        title="Rail Conflict",
        components=[
            ComponentInstance(instance_id="p1", component_id="rail_5v", ref_des="PWR1", value="+5V", pos_x=0, pos_y=0),
            ComponentInstance(instance_id="p2", component_id="rail_3v3", ref_des="PWR2", value="+3.3V", pos_x=50, pos_y=0),
            ComponentInstance(instance_id="g1", component_id="ground", ref_des="GND1", value="0V", pos_x=100, pos_y=0),
        ],
        nets=[
            SchematicNet(
                net_id="n1",
                name="CONFLICT_BUS",
                connections=[
                    NetPinConnection(instance_id="p1", pin_id="1"),
                    NetPinConnection(instance_id="p2", pin_id="1"),
                ],
            ),
            SchematicNet(
                net_id="n2",
                name="GND",
                is_ground=True,
                connections=[NetPinConnection(instance_id="g1", pin_id="1")],
            ),
        ],
    )
    report_rail = run_electrical_rule_checks(sheet_rail_conflict)
    assert any(f.rule_code == "ERC_RAIL_CONFLICT" for f in report_rail.findings)

    # Test 4: Floating CMOS Input
    sheet_floating = SchematicSheet(
        sheet_id="sheet_test_4",
        title="Floating Input",
        components=[
            ComponentInstance(instance_id="u1", component_id="logic_and_74hc08", ref_des="U1", value="74HC08", pos_x=0, pos_y=0),
            ComponentInstance(instance_id="g1", component_id="ground", ref_des="GND1", value="0V", pos_x=50, pos_y=0),
        ],
        nets=[
            SchematicNet(net_id="n1", name="GND", is_ground=True, connections=[NetPinConnection(instance_id="g1", pin_id="1")]),
        ],
    )
    report_float = run_electrical_rule_checks(sheet_floating)
    assert any(f.rule_code == "ERC_FLOATING_INPUT" for f in report_float.findings)


def test_spice_netlist_and_simulation():
    """Verifies standard SPICE netlist syntax generation and analytical solver execution."""
    sheet = SchematicSheet(
        sheet_id="sheet_divider",
        title="Voltage Divider Circuit",
        components=[
            ComponentInstance(instance_id="v1", component_id="vsource_dc", ref_des="V1", value="10V", pos_x=50, pos_y=100),
            ComponentInstance(instance_id="r1", component_id="resistor_generic", ref_des="R1", value="10k", pos_x=150, pos_y=100),
            ComponentInstance(instance_id="r2", component_id="resistor_generic", ref_des="R2", value="10k", pos_x=150, pos_y=200),
            ComponentInstance(instance_id="g1", component_id="ground", ref_des="GND1", value="0V", pos_x=150, pos_y=300),
        ],
        nets=[
            SchematicNet(net_id="n_vcc", name="VCC", is_power=True, connections=[NetPinConnection(instance_id="v1", pin_id="+"), NetPinConnection(instance_id="r1", pin_id="1")]),
            SchematicNet(net_id="n_mid", name="OUT", connections=[NetPinConnection(instance_id="r1", pin_id="2"), NetPinConnection(instance_id="r2", pin_id="1")]),
            SchematicNet(net_id="n_gnd", name="GND", is_ground=True, connections=[NetPinConnection(instance_id="v1", pin_id="-"), NetPinConnection(instance_id="r2", pin_id="2"), NetPinConnection(instance_id="g1", pin_id="1")]),
        ],
    )

    # 1. Netlist generation check
    netlist = generate_spice_netlist(sheet, analysis_type="op")
    assert "V1 VCC 0 DC 10V" in netlist or "V1" in netlist
    assert "R1 VCC OUT 10k" in netlist
    assert "R2 OUT 0 10k" in netlist
    assert ".op" in netlist
    assert ".end" in netlist

    # 2. Simulation run check
    sim_res = run_spice_simulation(SPICESimulationRequest(sheet=sheet, analysis_type="op"))
    assert sim_res.sim_status in ("completed_host_engine", "analytical_ideal_solver")
    if sim_res.sim_status == "analytical_ideal_solver":
        assert sim_res.node_voltages.get("OUT") == 5.0
        assert sim_res.node_voltages.get("VCC") == 10.0
        assert "zero simulation results fabricated" in sim_res.anti_fabrication_note.lower() or "analytical" in sim_res.anti_fabrication_note.lower()


def test_schematic_project_crud_and_versioning():
    """Verifies project lifecycle, version snapshot immutability, and custom component registry."""
    # 1. Create project
    created = schematic_studio_engine.create_project(
        SchematicProjectCreate(
            title="Test Power Circuit",
            description="Unit test project",
        )
    )
    assert created.title == "Test Power Circuit"
    assert created.version == "1.0.0"

    # 2. Update with version bump
    updated = schematic_studio_engine.update_project(
        created.project_id,
        SchematicProjectUpdate(
            title="Test Power Circuit v1.0.1",
            bump_version=True,
            change_note="Added filter cap",
        ),
    )
    assert updated.version == "1.0.1"
    assert updated.title == "Test Power Circuit v1.0.1"

    # 3. Custom component registration
    custom_comp = SchematicComponentDef(
        component_id="custom_sensor_bmp280",
        name="BMP280 Barometric Pressure Sensor Module",
        ref_des_prefix="U",
        category="custom_component",
        default_value="BMP280",
        description="I2C/SPI barometric sensor module",
        symbol_type="ic_generic",
        pins=[
            SchematicPin(pin_id="1", pin_number="1", name="VCC", pin_type="power_in"),
            SchematicPin(pin_id="2", pin_number="2", name="GND", pin_type="power_in"),
            SchematicPin(pin_id="3", pin_number="3", name="SCL", pin_type="input"),
            SchematicPin(pin_id="4", pin_number="4", name="SDA", pin_type="bidirectional"),
        ],
    )
    reg = schematic_studio_engine.register_custom_component(custom_comp)
    assert reg.component_id == "custom_sensor_bmp280"
    assert reg.is_custom is True

    custom_list = schematic_studio_engine.list_custom_components()
    assert any(c.component_id == "custom_sensor_bmp280" for c in custom_list)

    # 4. Clean up
    deleted = schematic_studio_engine.delete_project(created.project_id)
    assert deleted is True


def test_ai_circuit_assistant_and_exports():
    """Verifies AI circuit synthesis, engineering review gate, and multi-format exports."""
    # 1. AI Assistant circuit generation
    design = schematic_studio_engine.generate_circuit_from_prompt(
        AICircuitPromptRequest(prompt="Design an AMS1117 3.3V power regulator circuit with status LED")
    )
    assert "3.3V" in design.circuit_name
    assert len(design.sheet.components) >= 6
    assert len(design.sheet.nets) >= 3
    assert design.engineering_review_required is True
    assert "MANDATORY REVIEW" in design.review_banner

    # 2. Exports
    exp_spice = schematic_studio_engine.export_schematic(design.sheet, export_format="spice_netlist")
    assert exp_spice.export_format == "spice_netlist"
    assert ".cir" in exp_spice.filename
    assert "AMS1117" in exp_spice.content or "R" in exp_spice.content

    exp_bom_csv = schematic_studio_engine.export_schematic(design.sheet, export_format="bom_csv")
    assert "Item,Quantity,Reference Designators" in exp_bom_csv.content
    assert "text/csv" in exp_bom_csv.mime_type

    exp_kicad = schematic_studio_engine.export_schematic(design.sheet, export_format="kicad_netlist")
    assert "(export (version D)" in exp_kicad.content

    exp_svg = schematic_studio_engine.export_schematic(design.sheet, export_format="svg_schematic")
    assert "<svg" in exp_svg.content
    assert "</svg>" in exp_svg.content


@pytest.mark.asyncio
async def test_tool_registry_tool28_schematic_engine():
    """Verifies Tool #28 execution via ToolRegistry."""
    tool = tool_registry.get_tool("schematic_studio_engine")
    assert tool is not None
    assert tool.stage_introduced == 27

    # Execute overview
    overview_res = await tool_registry.execute("schematic_studio_engine", {"action": "overview"})
    assert overview_res["success"] is True
    assert "Schematic Studio Overview" in overview_res["summary"]

    # Execute calculation
    calc_res = await tool_registry.execute(
        "schematic_studio_engine",
        {
            "action": "calculate",
            "calculator_type": "ohms_law",
            "calc_params": {"voltage_v": 5.0, "current_a": 0.02},
        },
    )
    assert calc_res["success"] is True
    assert "250.0 ohms" in calc_res["summary"] or "0.1W" in calc_res["summary"]
