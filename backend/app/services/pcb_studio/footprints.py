from __future__ import annotations

from typing import Dict, List, Optional
from app.models.schemas import PCBFootprintDef, PCBPadDef


def get_standard_footprints() -> Dict[str, PCBFootprintDef]:
    """Returns the verified standard footprint library for discrete and IC packages."""
    return {
        # 1. SMD 0805 Resistor / Capacitor
        "0805": PCBFootprintDef(
            footprint_id="0805",
            name="SMD 0805 (2012 Metric)",
            category="smd_passive",
            description="Standard 2-pad SMD passive for resistors and ceramic capacitors (2.0mm x 1.25mm)",
            width_mm=3.0,
            height_mm=1.5,
            courtyard={"min_x": -1.8, "min_y": -1.0, "max_x": 1.8, "max_y": 1.0},
            model_3d={"shape": "box", "color": "#1e293b", "height_mm": 0.6},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.0, height_mm=1.3, rel_x_mm=-0.95, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=1.0, height_mm=1.3, rel_x_mm=0.95, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
            ],
        ),

        # 2. SMD 0603 Small Passive
        "0603": PCBFootprintDef(
            footprint_id="0603",
            name="SMD 0603 (1608 Metric)",
            category="smd_passive",
            description="Compact 2-pad SMD passive for dense layouts (1.6mm x 0.8mm)",
            width_mm=2.4,
            height_mm=1.1,
            courtyard={"min_x": -1.4, "min_y": -0.8, "max_x": 1.4, "max_y": 0.8},
            model_3d={"shape": "box", "color": "#1e293b", "height_mm": 0.45},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=0.8, height_mm=0.9, rel_x_mm=-0.75, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=0.8, height_mm=0.9, rel_x_mm=0.75, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
            ],
        ),

        # 3. SMD 1206 Medium Power Passive
        "1206": PCBFootprintDef(
            footprint_id="1206",
            name="SMD 1206 (3216 Metric)",
            category="smd_passive",
            description="Higher-power SMD passive up to 0.5W dissipation (3.2mm x 1.6mm)",
            width_mm=4.2,
            height_mm=1.9,
            courtyard={"min_x": -2.4, "min_y": -1.2, "max_x": 2.4, "max_y": 1.2},
            model_3d={"shape": "box", "color": "#1e293b", "height_mm": 0.7},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.1, height_mm=1.8, rel_x_mm=-1.5, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=1.1, height_mm=1.8, rel_x_mm=1.5, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
            ],
        ),

        # 4. SMD SOD-123 Diode
        "SOD-123": PCBFootprintDef(
            footprint_id="SOD-123",
            name="SOD-123 Diode",
            category="smd_diode",
            description="Standard surface-mount diode package with polarized cathode bar",
            width_mm=3.8,
            height_mm=1.8,
            courtyard={"min_x": -2.2, "min_y": -1.1, "max_x": 2.2, "max_y": 1.1},
            model_3d={"shape": "diode_body", "color": "#09090b", "height_mm": 1.2},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.2, height_mm=0.9, rel_x_mm=-1.6, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),  # Cathode
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=1.2, height_mm=0.9, rel_x_mm=1.6, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),   # Anode
            ],
        ),

        # 5. SMD LED 0805
        "LED_0805": PCBFootprintDef(
            footprint_id="LED_0805",
            name="SMD LED 0805",
            category="smd_led",
            description="Surface-mount indicator LED with cathode mark (Pin 1 = Cathode, Pin 2 = Anode)",
            width_mm=3.0,
            height_mm=1.5,
            courtyard={"min_x": -1.8, "min_y": -1.0, "max_x": 1.8, "max_y": 1.0},
            model_3d={"shape": "led_lens", "color": "#10b981", "height_mm": 0.8},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.0, height_mm=1.3, rel_x_mm=-0.95, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=1.0, height_mm=1.3, rel_x_mm=0.95, rel_y_mm=0.0, pad_type="smd", layers=["F.Cu"]),
            ],
        ),

        # 6. Through-Hole TO-92 (Transistors / Sensors)
        "TO-92": PCBFootprintDef(
            footprint_id="TO-92",
            name="TO-92 Inline",
            category="thru_hole_transistor",
            description="3-pin through-hole package for small-signal transistors (2N3904, 2N3906, DS18B20)",
            width_mm=5.2,
            height_mm=4.5,
            courtyard={"min_x": -3.0, "min_y": -2.5, "max_x": 3.0, "max_y": 2.5},
            model_3d={"shape": "to92_cylinder", "color": "#18181b", "height_mm": 4.8},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.5, height_mm=1.5, rel_x_mm=-2.54, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="2", shape="circle", width_mm=1.5, height_mm=1.5, rel_x_mm=0.0, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="3", shape="circle", width_mm=1.5, height_mm=1.5, rel_x_mm=2.54, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
            ],
        ),

        # 7. Through-Hole TO-220 Power Package (LM7805, IRFZ44N)
        "TO-220": PCBFootprintDef(
            footprint_id="TO-220",
            name="TO-220-3 Vertical",
            category="thru_hole_power",
            description="3-pin through-hole power transistor / linear regulator with metal heatsink tab",
            width_mm=10.4,
            height_mm=5.0,
            courtyard={"min_x": -5.5, "min_y": -3.0, "max_x": 5.5, "max_y": 3.0},
            model_3d={"shape": "to220_tab", "color": "#27272a", "height_mm": 15.0},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=2.0, height_mm=2.0, rel_x_mm=-2.54, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.1, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="2", shape="circle", width_mm=2.0, height_mm=2.0, rel_x_mm=0.0, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.1, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="3", shape="circle", width_mm=2.0, height_mm=2.0, rel_x_mm=2.54, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.1, layers=["F.Cu", "B.Cu"]),
            ],
        ),

        # 8. SOT-223 SMD Voltage Regulator (AMS1117-3.3)
        "SOT-223": PCBFootprintDef(
            footprint_id="SOT-223",
            name="SOT-223-3 Tab",
            category="smd_power",
            description="Surface mount regulator package with large thermal dissipation tab",
            width_mm=7.0,
            height_mm=7.5,
            courtyard={"min_x": -3.8, "min_y": -4.2, "max_x": 3.8, "max_y": 4.2},
            model_3d={"shape": "sot223_body", "color": "#18181b", "height_mm": 1.8},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.0, height_mm=1.8, rel_x_mm=-2.3, rel_y_mm=-3.1, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=1.0, height_mm=1.8, rel_x_mm=0.0, rel_y_mm=-3.1, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="3", shape="roundrect", width_mm=1.0, height_mm=1.8, rel_x_mm=2.3, rel_y_mm=-3.1, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="4", shape="roundrect", width_mm=3.3, height_mm=1.8, rel_x_mm=0.0, rel_y_mm=3.1, pad_type="smd", layers=["F.Cu"]),  # Tab (Vout)
            ],
        ),

        # 9. SOIC-8 SMD IC (LM358, 555 Timer, EEPROM)
        "SOIC-8": PCBFootprintDef(
            footprint_id="SOIC-8",
            name="SOIC-8 (1.27mm Pitch)",
            category="smd_ic",
            description="Standard 8-pin small outline IC for op-amps, timers, and transceivers",
            width_mm=6.2,
            height_mm=5.0,
            courtyard={"min_x": -3.5, "min_y": -2.8, "max_x": 3.5, "max_y": 2.8},
            model_3d={"shape": "ic_sop", "color": "#09090b", "height_mm": 1.75},
            pads=[
                # Left row (1..4)
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=-2.7, rel_y_mm=-1.905, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="2", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=-2.7, rel_y_mm=-0.635, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="3", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=-2.7, rel_y_mm=0.635, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="4", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=-2.7, rel_y_mm=1.905, pad_type="smd", layers=["F.Cu"]),
                # Right row (8..5)
                PCBPadDef(pad_number="5", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=2.7, rel_y_mm=1.905, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="6", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=2.7, rel_y_mm=0.635, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="7", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=2.7, rel_y_mm=-0.635, pad_type="smd", layers=["F.Cu"]),
                PCBPadDef(pad_number="8", shape="roundrect", width_mm=1.8, height_mm=0.6, rel_x_mm=2.7, rel_y_mm=-1.905, pad_type="smd", layers=["F.Cu"]),
            ],
        ),

        # 10. DIP-8 Through-Hole IC
        "DIP-8": PCBFootprintDef(
            footprint_id="DIP-8",
            name="DIP-8 (7.62mm Row Spacing)",
            category="thru_hole_ic",
            description="8-pin Dual In-line Package (NE555, LM358, etc.) for prototyping sockets",
            width_mm=10.2,
            height_mm=9.5,
            courtyard={"min_x": -5.5, "min_y": -5.2, "max_x": 5.5, "max_y": 5.2},
            model_3d={"shape": "ic_dip", "color": "#18181b", "height_mm": 3.6},
            pads=[
                # Left side (1..4)
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.6, height_mm=1.6, rel_x_mm=-3.81, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="2", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-3.81, rel_y_mm=-1.27, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="3", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-3.81, rel_y_mm=1.27, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="4", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-3.81, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                # Right side (8..5)
                PCBPadDef(pad_number="5", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=3.81, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="6", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=3.81, rel_y_mm=1.27, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="7", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=3.81, rel_y_mm=-1.27, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="8", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=3.81, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
            ],
        ),

        # 11. DIP-14 Through-Hole Logic IC
        "DIP-14": PCBFootprintDef(
            footprint_id="DIP-14",
            name="DIP-14 (7.62mm Row Spacing)",
            category="thru_hole_ic",
            description="14-pin Dual In-line Package for 74-series logic gates (74HC08, 74HC04, 74HC00)",
            width_mm=19.5,
            height_mm=9.5,
            courtyard={"min_x": -10.2, "min_y": -5.2, "max_x": 10.2, "max_y": 5.2},
            model_3d={"shape": "ic_dip", "color": "#18181b", "height_mm": 3.6},
            pads=[
                # Pins 1 to 7 on left/bottom
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.6, height_mm=1.6, rel_x_mm=-7.62, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="2", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-5.08, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="3", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-2.54, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="4", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=0.0, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="5", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=2.54, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="6", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=5.08, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="7", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=7.62, rel_y_mm=-3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                # Pins 14 down to 8 on right/top
                PCBPadDef(pad_number="8", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=7.62, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="9", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=5.08, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="10", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=2.54, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="11", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=0.0, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="12", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-2.54, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="13", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-5.08, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="14", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=-7.62, rel_y_mm=3.81, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),
            ],
        ),

        # 12. 2-Pin Screw Terminal / Pin Header (Power Input / Sensor Jack)
        "PinHeader_1x02_P2.54mm": PCBFootprintDef(
            footprint_id="PinHeader_1x02_P2.54mm",
            name="Pin Header 1x02 (2.54mm Pitch)",
            category="connector",
            description="2-pin through-hole header or 5mm terminal block for power/ground connections",
            width_mm=5.6,
            height_mm=3.2,
            courtyard={"min_x": -3.0, "min_y": -1.8, "max_x": 3.0, "max_y": 1.8},
            model_3d={"shape": "pin_header", "color": "#18181b", "height_mm": 8.5},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.7, height_mm=1.7, rel_x_mm=-1.27, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.0, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="2", shape="circle", width_mm=1.7, height_mm=1.7, rel_x_mm=1.27, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.0, layers=["F.Cu", "B.Cu"]),
            ],
        ),

        # 13. 4-Pin Header (I2C / UART / Sensor Interface)
        "PinHeader_1x04_P2.54mm": PCBFootprintDef(
            footprint_id="PinHeader_1x04_P2.54mm",
            name="Pin Header 1x04 (2.54mm Pitch)",
            category="connector",
            description="4-pin vertical header for I2C (VCC, GND, SDA, SCL) or serial communication",
            width_mm=10.8,
            height_mm=3.2,
            courtyard={"min_x": -5.6, "min_y": -1.8, "max_x": 5.6, "max_y": 1.8},
            model_3d={"shape": "pin_header", "color": "#18181b", "height_mm": 8.5},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.7, height_mm=1.7, rel_x_mm=-3.81, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.0, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="2", shape="circle", width_mm=1.7, height_mm=1.7, rel_x_mm=-1.27, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.0, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="3", shape="circle", width_mm=1.7, height_mm=1.7, rel_x_mm=1.27, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.0, layers=["F.Cu", "B.Cu"]),
                PCBPadDef(pad_number="4", shape="circle", width_mm=1.7, height_mm=1.7, rel_x_mm=3.81, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=1.0, layers=["F.Cu", "B.Cu"]),
            ],
        ),

        # 14. Radial Electrolytic Capacitor D6.3mm
        "Radial_Cap_D6.3mm": PCBFootprintDef(
            footprint_id="Radial_Cap_D6.3mm",
            name="Radial Capacitor D6.3mm (P2.5mm)",
            category="thru_hole_passive",
            description="Electrolytic bulk filter capacitor with polarized circular aluminum can",
            width_mm=6.5,
            height_mm=6.5,
            courtyard={"min_x": -3.5, "min_y": -3.5, "max_x": 3.5, "max_y": 3.5},
            model_3d={"shape": "radial_can", "color": "#1e3a8a", "height_mm": 11.0},
            pads=[
                PCBPadDef(pad_number="1", shape="roundrect", width_mm=1.6, height_mm=1.6, rel_x_mm=-1.25, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),  # + Positive
                PCBPadDef(pad_number="2", shape="circle", width_mm=1.6, height_mm=1.6, rel_x_mm=1.25, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=0.8, layers=["F.Cu", "B.Cu"]),     # - Negative
            ],
        ),

        # 15. Standard M3 PCB Mounting Hole
        "MountingHole_M3": PCBFootprintDef(
            footprint_id="MountingHole_M3",
            name="Mounting Hole M3 (3.2mm Drill)",
            category="mechanical",
            description="M3 screw mounting hole with 6.0mm annular ground ring for chassis bonding",
            width_mm=6.5,
            height_mm=6.5,
            courtyard={"min_x": -3.3, "min_y": -3.3, "max_x": 3.3, "max_y": 3.3},
            model_3d={"shape": "mounting_hole", "color": "#64748b", "height_mm": 1.6},
            pads=[
                PCBPadDef(pad_number="1", shape="circle", width_mm=6.0, height_mm=6.0, rel_x_mm=0.0, rel_y_mm=0.0, pad_type="thru_hole", drill_diameter_mm=3.2, layers=["F.Cu", "B.Cu"]),
            ],
        ),
    }


def map_schematic_footprint_alias(raw_footprint: str) -> Optional[str]:
    """Resolves standard schematic footprint hints/aliases to verified library footprint IDs."""
    if not raw_footprint:
        return None
    raw = raw_footprint.strip()
    catalog = get_standard_footprints()
    if raw in catalog:
        return raw

    # Common aliases & mappings
    lower = raw.lower()
    if "0805" in lower:
        return "LED_0805" if "led" in lower else "0805"
    if "0603" in lower:
        return "0603"
    if "1206" in lower:
        return "1206"
    if "sod-123" in lower or "sod123" in lower:
        return "SOD-123"
    if "to-92" in lower or "to92" in lower:
        return "TO-92"
    if "to-220" in lower or "to220" in lower:
        return "TO-220"
    if "sot-223" in lower or "sot223" in lower:
        return "SOT-223"
    if "soic-8" in lower or "so-8" in lower or "soic8" in lower:
        return "SOIC-8"
    if "dip-8" in lower or "dip8" in lower:
        return "DIP-8"
    if "dip-14" in lower or "dip14" in lower:
        return "DIP-14"
    if "radial" in lower or "cap_radial" in lower or "6.3" in lower:
        return "Radial_Cap_D6.3mm"
    if "1x02" in lower or "2pin" in lower or "terminal" in lower or "header_2" in lower:
        return "PinHeader_1x02_P2.54mm"
    if "1x04" in lower or "4pin" in lower or "header_4" in lower:
        return "PinHeader_1x04_P2.54mm"
    if "m3" in lower or "mounting" in lower:
        return "MountingHole_M3"

    return None


FOOTPRINT_LIBRARY: Dict[str, PCBFootprintDef] = get_standard_footprints()


def get_footprint_definition(footprint_id: str) -> Optional[PCBFootprintDef]:
    """Retrieves a footprint definition from the standard library."""
    return FOOTPRINT_LIBRARY.get(footprint_id)


def list_available_footprints() -> List[PCBFootprintDef]:
    """Returns a list of all available standard footprint definitions."""
    return list(FOOTPRINT_LIBRARY.values())
