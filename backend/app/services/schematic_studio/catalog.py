from __future__ import annotations

import shutil
from typing import Dict, List, Optional
from app.models.schemas import (
    SchematicComponentDef,
    SchematicPin,
)


def detect_eda_toolchains() -> Dict[str, bool]:
    """Probes host PATH for electronic circuit simulation and EDA toolchains."""
    return {
        "ngspice": shutil.which("ngspice") is not None,
        "kicad_cli": shutil.which("kicad-cli") is not None or shutil.which("eeschema") is not None,
        "python_pyspice": shutil.which("python") is not None,
    }


def build_standard_component_catalog() -> Dict[str, SchematicComponentDef]:
    """Returns the comprehensive standard component library for schematic capture."""
    return {
        # 1. PASSIVE RESISTOR
        "resistor_generic": SchematicComponentDef(
            component_id="resistor_generic",
            name="Resistor (Fixed)",
            ref_des_prefix="R",
            category="passive_resistor",
            default_value="10k",
            default_tolerance="5%",
            footprint="0805",
            description="Fixed carbon or metal film resistor. Dissipates up to 250mW (1/4W) in typical package.",
            symbol_type="resistor_us",
            max_voltage_v=200.0,
            max_power_mw=250.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="1", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left"),
                SchematicPin(pin_id="2", pin_number="2", name="2", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 2. POTENTIOMETER
        "potentiometer": SchematicComponentDef(
            component_id="potentiometer",
            name="Potentiometer (Trimpot)",
            ref_des_prefix="RV",
            category="passive_resistor",
            default_value="10k",
            default_tolerance="10%",
            footprint="Bourns_3296W",
            description="3-terminal variable resistor / voltage divider with wiper.",
            symbol_type="potentiometer",
            max_voltage_v=100.0,
            max_power_mw=500.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="CCW", pin_type="passive", rel_x=-20.0, rel_y=-10.0, orientation="left"),
                SchematicPin(pin_id="2", pin_number="2", name="WIPER", pin_type="passive", rel_x=0.0, rel_y=20.0, orientation="bottom"),
                SchematicPin(pin_id="3", pin_number="3", name="CW", pin_type="passive", rel_x=20.0, rel_y=-10.0, orientation="right"),
            ],
        ),

        # 3. CERAMIC CAPACITOR (NON-POLARIZED)
        "capacitor_ceramic": SchematicComponentDef(
            component_id="capacitor_ceramic",
            name="Capacitor (Ceramic/Film)",
            ref_des_prefix="C",
            category="passive_capacitor",
            default_value="100nF",
            default_tolerance="10%",
            footprint="0805",
            description="Non-polarized ceramic MLCC capacitor for high-frequency decoupling and timing.",
            symbol_type="capacitor_non_polarized",
            max_voltage_v=50.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="1", pin_type="passive", rel_x=-15.0, rel_y=0.0, orientation="left"),
                SchematicPin(pin_id="2", pin_number="2", name="2", pin_type="passive", rel_x=15.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 4. ELECTROLYTIC CAPACITOR (POLARIZED)
        "capacitor_electrolytic": SchematicComponentDef(
            component_id="capacitor_electrolytic",
            name="Capacitor (Electrolytic Polarized)",
            ref_des_prefix="C",
            category="passive_capacitor",
            default_value="10uF",
            default_tolerance="20%",
            footprint="Radial_D5_P2",
            description="Polarized aluminum electrolytic capacitor for bulk power rail smoothing.",
            symbol_type="capacitor_polarized",
            max_voltage_v=25.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="+", pin_type="passive", rel_x=-15.0, rel_y=0.0, orientation="left", notes="Anode (Positive)"),
                SchematicPin(pin_id="2", pin_number="2", name="-", pin_type="passive", rel_x=15.0, rel_y=0.0, orientation="right", notes="Cathode (Negative)"),
            ],
        ),

        # 5. INDUCTOR
        "inductor_generic": SchematicComponentDef(
            component_id="inductor_generic",
            name="Inductor (Choke)",
            ref_des_prefix="L",
            category="passive_inductor",
            default_value="10uH",
            default_tolerance="10%",
            footprint="Inductor_0805",
            description="Wire-wound or multilayer inductor for LC filters and DC-DC converters.",
            symbol_type="inductor",
            max_current_ma=500.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="1", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left"),
                SchematicPin(pin_id="2", pin_number="2", name="2", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 6. SWITCHING DIODE 1N4148
        "diode_1n4148": SchematicComponentDef(
            component_id="diode_1n4148",
            name="1N4148 Fast Switching Diode",
            ref_des_prefix="D",
            category="semiconductor_diode",
            default_value="1N4148",
            footprint="DO-35",
            description="High-speed small-signal silicon switching diode (4ns recovery time).",
            symbol_type="diode",
            max_voltage_v=100.0,
            max_current_ma=200.0,
            forward_voltage_v=0.72,
            datasheet_url="https://www.vishay.com/docs/81857/1n4148.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Anode"),
                SchematicPin(pin_id="K", pin_number="2", name="K", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right", notes="Cathode"),
            ],
        ),

        # 7. POWER RECTIFIER DIODE 1N4007
        "diode_1n4007": SchematicComponentDef(
            component_id="diode_1n4007",
            name="1N4007 Power Rectifier Diode",
            ref_des_prefix="D",
            category="semiconductor_diode",
            default_value="1N4007",
            footprint="DO-41",
            description="1A 1000V general purpose silicon rectifier diode and inductive flyback clamp.",
            symbol_type="diode",
            max_voltage_v=1000.0,
            max_current_ma=1000.0,
            forward_voltage_v=1.0,
            datasheet_url="https://www.diodes.com/assets/Datasheets/ds28002.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Anode"),
                SchematicPin(pin_id="K", pin_number="2", name="K", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right", notes="Cathode"),
            ],
        ),

        # 8. ZENER DIODE 3.3V
        "zener_3v3": SchematicComponentDef(
            component_id="zener_3v3",
            name="3.3V Zener Diode (BZX55C3V3)",
            ref_des_prefix="D",
            category="semiconductor_diode",
            default_value="3.3V",
            footprint="DO-35",
            description="3.3V 500mW voltage reference and overvoltage clamp diode.",
            symbol_type="zener_diode",
            max_voltage_v=3.3,
            max_power_mw=500.0,
            breakdown_voltage_v=3.3,
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Anode"),
                SchematicPin(pin_id="K", pin_number="2", name="K", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right", notes="Cathode (Bar)"),
            ],
        ),

        # 9. RED LED
        "led_red": SchematicComponentDef(
            component_id="led_red",
            name="LED (Red 5mm / 0805)",
            ref_des_prefix="D",
            category="semiconductor_led",
            default_value="Red",
            footprint="LED_0805",
            description="Standard gallium arsenide phosphide red light emitting diode. Vf ~ 2.0V, If ~ 20mA.",
            symbol_type="led",
            max_voltage_v=5.0,  # Max reverse voltage
            max_current_ma=25.0,
            forward_voltage_v=2.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Anode (+)"),
                SchematicPin(pin_id="K", pin_number="2", name="K", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right", notes="Cathode (-)"),
            ],
        ),

        # 10. GREEN LED
        "led_green": SchematicComponentDef(
            component_id="led_green",
            name="LED (Green 5mm / 0805)",
            ref_des_prefix="D",
            category="semiconductor_led",
            default_value="Green",
            footprint="LED_0805",
            description="Standard green light emitting diode. Vf ~ 2.2V, If ~ 20mA.",
            symbol_type="led",
            max_voltage_v=5.0,
            max_current_ma=25.0,
            forward_voltage_v=2.2,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Anode (+)"),
                SchematicPin(pin_id="K", pin_number="2", name="K", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right", notes="Cathode (-)"),
            ],
        ),

        # 11. BLUE LED
        "led_blue": SchematicComponentDef(
            component_id="led_blue",
            name="LED (Blue 5mm / 0805)",
            ref_des_prefix="D",
            category="semiconductor_led",
            default_value="Blue",
            footprint="LED_0805",
            description="InGaN high-intensity blue light emitting diode. Vf ~ 3.2V, If ~ 20mA.",
            symbol_type="led",
            max_voltage_v=5.0,
            max_current_ma=25.0,
            forward_voltage_v=3.2,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Anode (+)"),
                SchematicPin(pin_id="K", pin_number="2", name="K", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right", notes="Cathode (-)"),
            ],
        ),

        # 12. BJT NPN TRANSISTOR 2N2222
        "bjt_npn_2n2222": SchematicComponentDef(
            component_id="bjt_npn_2n2222",
            name="2N2222 NPN Bipolar Junction Transistor",
            ref_des_prefix="Q",
            category="semiconductor_transistor_bjt",
            default_value="2N2222",
            footprint="TO-92",
            description="General purpose NPN switching and amplifier transistor. Vceo=40V, Ic=800mA max.",
            symbol_type="bjt_npn",
            max_voltage_v=40.0,
            max_current_ma=800.0,
            max_power_mw=625.0,
            beta_hfe=150.0,
            datasheet_url="https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="B", pin_number="1", name="B", pin_type="input", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Base"),
                SchematicPin(pin_id="C", pin_number="2", name="C", pin_type="passive", rel_x=15.0, rel_y=-20.0, orientation="top", notes="Collector"),
                SchematicPin(pin_id="E", pin_number="3", name="E", pin_type="passive", rel_x=15.0, rel_y=20.0, orientation="bottom", notes="Emitter (Arrow out)"),
            ],
        ),

        # 13. BJT PNP TRANSISTOR 2N3906
        "bjt_pnp_2n3906": SchematicComponentDef(
            component_id="bjt_pnp_2n3906",
            name="2N3906 PNP Bipolar Junction Transistor",
            ref_des_prefix="Q",
            category="semiconductor_transistor_bjt",
            default_value="2N3906",
            footprint="TO-92",
            description="General purpose PNP transistor for high-side switching and complementary stages.",
            symbol_type="bjt_pnp",
            max_voltage_v=40.0,
            max_current_ma=200.0,
            max_power_mw=625.0,
            beta_hfe=100.0,
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="B", pin_number="1", name="B", pin_type="input", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Base"),
                SchematicPin(pin_id="E", pin_number="2", name="E", pin_type="passive", rel_x=15.0, rel_y=-20.0, orientation="top", notes="Emitter (Arrow in)"),
                SchematicPin(pin_id="C", pin_number="3", name="C", pin_type="passive", rel_x=15.0, rel_y=20.0, orientation="bottom", notes="Collector"),
            ],
        ),

        # 14. N-CHANNEL MOSFET 2N7000
        "mosfet_n_2n7000": SchematicComponentDef(
            component_id="mosfet_n_2n7000",
            name="2N7000 N-Channel Logic MOSFET",
            ref_des_prefix="Q",
            category="semiconductor_transistor_mosfet",
            default_value="2N7000",
            footprint="TO-92",
            description="60V 200mA logic-level N-channel enhancement mode MOSFET for fast low-side switching.",
            symbol_type="mosfet_n",
            max_voltage_v=60.0,
            max_current_ma=200.0,
            max_power_mw=400.0,
            datasheet_url="https://www.onsemi.com/pdf/datasheet/2n7000-d.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="G", pin_number="1", name="G", pin_type="input", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Gate"),
                SchematicPin(pin_id="D", pin_number="2", name="D", pin_type="passive", rel_x=15.0, rel_y=-20.0, orientation="top", notes="Drain"),
                SchematicPin(pin_id="S", pin_number="3", name="S", pin_type="passive", rel_x=15.0, rel_y=20.0, orientation="bottom", notes="Source"),
            ],
        ),

        # 15. POWER N-CHANNEL MOSFET IRFZ44N
        "mosfet_n_irfz44n": SchematicComponentDef(
            component_id="mosfet_n_irfz44n",
            name="IRFZ44N Power N-Channel MOSFET",
            ref_des_prefix="Q",
            category="semiconductor_transistor_mosfet",
            default_value="IRFZ44N",
            footprint="TO-220",
            description="55V 49A high-current N-channel power MOSFET (Rds(on) = 17.5mOhm). Requires heatsink for high loads.",
            symbol_type="mosfet_n",
            max_voltage_v=55.0,
            max_current_ma=49000.0,
            max_power_mw=94000.0,
            datasheet_url="https://www.infineon.com/dgdl/irfz44n.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="G", pin_number="1", name="G", pin_type="input", rel_x=-20.0, rel_y=0.0, orientation="left", notes="Gate"),
                SchematicPin(pin_id="D", pin_number="2", name="D", pin_type="passive", rel_x=15.0, rel_y=-20.0, orientation="top", notes="Drain (Center pin / tab)"),
                SchematicPin(pin_id="S", pin_number="3", name="S", pin_type="passive", rel_x=15.0, rel_y=20.0, orientation="bottom", notes="Source"),
            ],
        ),

        # 16. DUAL OPERATIONAL AMPLIFIER LM358
        "opamp_lm358": SchematicComponentDef(
            component_id="opamp_lm358",
            name="LM358 Dual Operational Amplifier",
            ref_des_prefix="U",
            category="analog_opamp",
            default_value="LM358",
            footprint="DIP-8",
            description="Dual low-power operational amplifier designed to operate from a single 3V to 32V power supply.",
            symbol_type="opamp",
            max_voltage_v=32.0,
            quiescent_current_ma=1.0,
            datasheet_url="https://www.ti.com/lit/ds/symlink/lm358.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="OUT_A", pin_type="output", rel_x=25.0, rel_y=0.0, orientation="right"),
                SchematicPin(pin_id="2", pin_number="2", name="IN-_A", pin_type="input", rel_x=-25.0, rel_y=-10.0, orientation="left", notes="Inverting A"),
                SchematicPin(pin_id="3", pin_number="3", name="IN+_A", pin_type="input", rel_x=-25.0, rel_y=10.0, orientation="left", notes="Non-inverting A"),
                SchematicPin(pin_id="4", pin_number="4", name="GND/V-", pin_type="power_in", rel_x=0.0, rel_y=25.0, orientation="bottom", notes="Ground or negative rail"),
                SchematicPin(pin_id="5", pin_number="5", name="IN+_B", pin_type="input", rel_x=-25.0, rel_y=40.0, orientation="left", notes="Non-inverting B"),
                SchematicPin(pin_id="6", pin_number="6", name="IN-_B", pin_type="input", rel_x=-25.0, rel_y=60.0, orientation="left", notes="Inverting B"),
                SchematicPin(pin_id="7", pin_number="7", name="OUT_B", pin_type="output", rel_x=25.0, rel_y=50.0, orientation="right"),
                SchematicPin(pin_id="8", pin_number="8", name="VCC/V+", pin_type="power_in", rel_x=0.0, rel_y=-25.0, orientation="top", notes="Positive supply rail"),
            ],
        ),

        # 17. 5V LINEAR REGULATOR LM7805
        "regulator_lm7805": SchematicComponentDef(
            component_id="regulator_lm7805",
            name="LM7805 5V 1A Positive Voltage Regulator",
            ref_des_prefix="U",
            category="analog_regulator",
            default_value="LM7805",
            footprint="TO-220",
            description="Fixed 5.0V positive voltage regulator with internal current limiting and thermal shutdown.",
            symbol_type="regulator_3pin",
            max_voltage_v=35.0,
            max_current_ma=1500.0,
            quiescent_current_ma=5.0,
            datasheet_url="https://www.sparkfun.com/datasheets/Components/LM7805.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="IN", pin_number="1", name="INPUT", pin_type="power_in", rel_x=-25.0, rel_y=0.0, orientation="left", notes="7V to 25V recommended"),
                SchematicPin(pin_id="GND", pin_number="2", name="GND", pin_type="power_in", rel_x=0.0, rel_y=25.0, orientation="bottom", notes="Common ground"),
                SchematicPin(pin_id="OUT", pin_number="3", name="OUTPUT", pin_type="power_out", rel_x=25.0, rel_y=0.0, orientation="right", notes="Regulated 5.0V output"),
            ],
        ),

        # 18. 3.3V LDO REGULATOR AMS1117-3.3
        "regulator_ams1117_3v3": SchematicComponentDef(
            component_id="regulator_ams1117_3v3",
            name="AMS1117-3.3 3.3V 800mA LDO Regulator",
            ref_des_prefix="U",
            category="analog_regulator",
            default_value="AMS1117-3.3",
            footprint="SOT-223",
            description="Low dropout positive voltage regulator with 1.1V dropout at 800mA. Ideal for 5V -> 3.3V MCU rails.",
            symbol_type="regulator_3pin",
            max_voltage_v=15.0,
            max_current_ma=800.0,
            quiescent_current_ma=5.0,
            datasheet_url="http://www.advanced-monolithic.com/pdf/ds1117.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="GND", pin_number="1", name="GND", pin_type="power_in", rel_x=0.0, rel_y=25.0, orientation="bottom", notes="Ground"),
                SchematicPin(pin_id="OUT", pin_number="2", name="VOUT", pin_type="power_out", rel_x=25.0, rel_y=0.0, orientation="right", notes="3.3V regulated output"),
                SchematicPin(pin_id="IN", pin_number="3", name="VIN", pin_type="power_in", rel_x=-25.0, rel_y=0.0, orientation="left", notes="4.5V to 12V input"),
            ],
        ),

        # 19. NE555 PRECISION TIMER
        "timer_ne555": SchematicComponentDef(
            component_id="timer_ne555",
            name="NE555 Precision Timer IC",
            ref_des_prefix="U",
            category="analog_timer",
            default_value="NE555",
            footprint="DIP-8",
            description="Highly stable controller capable of producing accurate timing pulses and astable oscillations.",
            symbol_type="ic_timer",
            max_voltage_v=18.0,
            max_current_ma=200.0,
            quiescent_current_ma=3.0,
            datasheet_url="https://www.ti.com/lit/ds/symlink/ne555.pdf",
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="GND", pin_type="power_in", rel_x=0.0, rel_y=30.0, orientation="bottom"),
                SchematicPin(pin_id="2", pin_number="2", name="TRIG", pin_type="input", rel_x=-30.0, rel_y=-10.0, orientation="left"),
                SchematicPin(pin_id="3", pin_number="3", name="OUT", pin_type="output", rel_x=30.0, rel_y=0.0, orientation="right"),
                SchematicPin(pin_id="4", pin_number="4", name="RESET", pin_type="input", rel_x=-30.0, rel_y=-20.0, orientation="left"),
                SchematicPin(pin_id="5", pin_number="5", name="CTRL", pin_type="passive", rel_x=30.0, rel_y=15.0, orientation="right"),
                SchematicPin(pin_id="6", pin_number="6", name="THRES", pin_type="input", rel_x=-30.0, rel_y=10.0, orientation="left"),
                SchematicPin(pin_id="7", pin_number="7", name="DISCH", pin_type="open_collector", rel_x=30.0, rel_y=-15.0, orientation="right"),
                SchematicPin(pin_id="8", pin_number="8", name="VCC", pin_type="power_in", rel_x=0.0, rel_y=-30.0, orientation="top"),
            ],
        ),

        # 20. 74HC08 QUAD 2-INPUT AND GATE
        "logic_and_74hc08": SchematicComponentDef(
            component_id="logic_and_74hc08",
            name="74HC08 Quad 2-Input AND Gate",
            ref_des_prefix="U",
            category="digital_logic_gate",
            default_value="74HC08",
            footprint="DIP-14",
            description="High-speed CMOS 2-input positive-AND gate (Single gate unit represented).",
            symbol_type="logic_and",
            max_voltage_v=6.0,
            max_current_ma=25.0,
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="input", rel_x=-25.0, rel_y=-10.0, orientation="left"),
                SchematicPin(pin_id="B", pin_number="2", name="B", pin_type="input", rel_x=-25.0, rel_y=10.0, orientation="left"),
                SchematicPin(pin_id="Y", pin_number="3", name="Y", pin_type="output", rel_x=25.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 21. 74HC32 QUAD 2-INPUT OR GATE
        "logic_or_74hc32": SchematicComponentDef(
            component_id="logic_or_74hc32",
            name="74HC32 Quad 2-Input OR Gate",
            ref_des_prefix="U",
            category="digital_logic_gate",
            default_value="74HC32",
            footprint="DIP-14",
            description="High-speed CMOS 2-input positive-OR gate (Single gate unit represented).",
            symbol_type="logic_or",
            max_voltage_v=6.0,
            max_current_ma=25.0,
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="input", rel_x=-25.0, rel_y=-10.0, orientation="left"),
                SchematicPin(pin_id="B", pin_number="2", name="B", pin_type="input", rel_x=-25.0, rel_y=10.0, orientation="left"),
                SchematicPin(pin_id="Y", pin_number="3", name="Y", pin_type="output", rel_x=25.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 22. 74HC04 HEX INVERTER (NOT GATE)
        "logic_not_74hc04": SchematicComponentDef(
            component_id="logic_not_74hc04",
            name="74HC04 Hex Inverter (NOT Gate)",
            ref_des_prefix="U",
            category="digital_logic_gate",
            default_value="74HC04",
            footprint="DIP-14",
            description="High-speed CMOS inverting buffer gate.",
            symbol_type="logic_not",
            max_voltage_v=6.0,
            max_current_ma=25.0,
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="A", pin_number="1", name="A", pin_type="input", rel_x=-25.0, rel_y=0.0, orientation="left"),
                SchematicPin(pin_id="Y", pin_number="2", name="Y", pin_type="output", rel_x=25.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 23. SPST PUSHBUTTON SWITCH
        "switch_spst": SchematicComponentDef(
            component_id="switch_spst",
            name="SPST Pushbutton Switch",
            ref_des_prefix="SW",
            category="electromechanical_switch",
            default_value="Tactile",
            footprint="SW_Tactile_6x6mm",
            description="Momentary normally-open single-pole single-throw tactile pushbutton switch.",
            symbol_type="switch_spst",
            max_voltage_v=24.0,
            max_current_ma=50.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="1", pin_type="passive", rel_x=-20.0, rel_y=0.0, orientation="left"),
                SchematicPin(pin_id="2", pin_number="2", name="2", pin_type="passive", rel_x=20.0, rel_y=0.0, orientation="right"),
            ],
        ),

        # 24. 5V SPDT RELAY
        "relay_spdt_5v": SchematicComponentDef(
            component_id="relay_spdt_5v",
            name="5V SPDT Electromechanical Relay",
            ref_des_prefix="K",
            category="electromechanical_relay",
            default_value="5V Coil",
            footprint="Relay_Songle_SRD_5V",
            description="Electromechanical relay with 5V DC coil (70mA) and 10A 250VAC contacts. Requires flyback diode across coil.",
            symbol_type="relay_spdt",
            max_voltage_v=250.0,
            max_current_ma=10000.0,
            spec_verification="verified_datasheet_spec",
            pins=[
                SchematicPin(pin_id="COIL_P", pin_number="1", name="COIL+", pin_type="passive", rel_x=-25.0, rel_y=-15.0, orientation="left", notes="Coil terminal 1"),
                SchematicPin(pin_id="COIL_N", pin_number="2", name="COIL-", pin_type="passive", rel_x=-25.0, rel_y=15.0, orientation="left", notes="Coil terminal 2"),
                SchematicPin(pin_id="COM", pin_number="3", name="COM", pin_type="passive", rel_x=25.0, rel_y=0.0, orientation="right", notes="Common contact"),
                SchematicPin(pin_id="NC", pin_number="4", name="NC", pin_type="passive", rel_x=25.0, rel_y=-15.0, orientation="right", notes="Normally closed contact"),
                SchematicPin(pin_id="NO", pin_number="5", name="NO", pin_type="passive", rel_x=25.0, rel_y=15.0, orientation="right", notes="Normally open contact"),
            ],
        ),

        # 25. DC VOLTAGE SOURCE
        "vsource_dc": SchematicComponentDef(
            component_id="vsource_dc",
            name="DC Voltage Source",
            ref_des_prefix="V",
            category="power_source",
            default_value="5V",
            footprint="TestPoint",
            description="Ideal or lab bench DC power supply source.",
            symbol_type="vsource_dc",
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="+", pin_number="1", name="+", pin_type="power_out", rel_x=0.0, rel_y=-20.0, orientation="top"),
                SchematicPin(pin_id="-", pin_number="2", name="-", pin_type="power_out", rel_x=0.0, rel_y=20.0, orientation="bottom"),
            ],
        ),

        # 26. GROUND SYMBOL
        "ground": SchematicComponentDef(
            component_id="ground",
            name="Ground (GND)",
            ref_des_prefix="GND",
            category="power_source",
            default_value="0V",
            footprint="NetTie",
            description="Reference circuit ground node (SPICE node 0).",
            symbol_type="ground",
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="GND", pin_type="power_out", rel_x=0.0, rel_y=-15.0, orientation="top"),
            ],
        ),

        # 27. VCC POWER RAIL
        "rail_vcc": SchematicComponentDef(
            component_id="rail_vcc",
            name="VCC Power Rail Symbol",
            ref_des_prefix="PWR",
            category="power_source",
            default_value="VCC",
            footprint="NetTie",
            description="Global positive supply rail connection point.",
            symbol_type="power_rail",
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="VCC", pin_type="power_out", rel_x=0.0, rel_y=15.0, orientation="bottom"),
            ],
        ),

        # 28. +3.3V POWER RAIL
        "rail_3v3": SchematicComponentDef(
            component_id="rail_3v3",
            name="+3.3V Power Rail Symbol",
            ref_des_prefix="PWR",
            category="power_source",
            default_value="+3.3V",
            footprint="NetTie",
            description="Dedicated +3.3V power rail symbol.",
            symbol_type="power_rail",
            max_voltage_v=3.3,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="+3V3", pin_type="power_out", rel_x=0.0, rel_y=15.0, orientation="bottom"),
            ],
        ),

        # 29. +5V POWER RAIL
        "rail_5v": SchematicComponentDef(
            component_id="rail_5v",
            name="+5V Power Rail Symbol",
            ref_des_prefix="PWR",
            category="power_source",
            default_value="+5V",
            footprint="NetTie",
            description="Dedicated +5.0V power rail symbol.",
            symbol_type="power_rail",
            max_voltage_v=5.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="+5V", pin_type="power_out", rel_x=0.0, rel_y=15.0, orientation="bottom"),
            ],
        ),

        # 30. PIN HEADER 1x4
        "header_1x4": SchematicComponentDef(
            component_id="header_1x4",
            name="4-Pin Male Header (0.1\")",
            ref_des_prefix="J",
            category="connector_header",
            default_value="4-Pin 2.54mm",
            footprint="PinHeader_1x04_P2.54mm_Vertical",
            description="Standard 4-pin single-row breakable header for I2C, UART, or power.",
            symbol_type="connector_header",
            max_voltage_v=100.0,
            max_current_ma=2000.0,
            spec_verification="standard_generic_model",
            pins=[
                SchematicPin(pin_id="1", pin_number="1", name="1", pin_type="passive", rel_x=20.0, rel_y=-15.0, orientation="right"),
                SchematicPin(pin_id="2", pin_number="2", name="2", pin_type="passive", rel_x=20.0, rel_y=-5.0, orientation="right"),
                SchematicPin(pin_id="3", pin_number="3", name="3", pin_type="passive", rel_x=20.0, rel_y=5.0, orientation="right"),
                SchematicPin(pin_id="4", pin_number="4", name="4", pin_type="passive", rel_x=20.0, rel_y=15.0, orientation="right"),
            ],
        ),
    }
