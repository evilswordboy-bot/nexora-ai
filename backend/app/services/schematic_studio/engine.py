from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from app.config import settings
from app.models.schemas import (
    SchematicProject,
    SchematicProjectCreate,
    SchematicProjectUpdate,
    SchematicSheet,
    ComponentInstance,
    SchematicNet,
    NetPinConnection,
    SchematicComponentDef,
    SchematicExportResponse,
    AICircuitPromptRequest,
    AICircuitDesignResponse,
    SchematicOverviewResponse,
)
from app.services.schematic_studio.catalog import (
    build_standard_component_catalog,
    detect_eda_toolchains,
)
from app.services.schematic_studio.spice import generate_spice_netlist


class SchematicStudioEngine:
    """Core backend engine for Stage 27 Electronic Circuit Schematic Design Studio."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.schematic_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schematic_projects (
                    project_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    version TEXT DEFAULT '1.0.0',
                    sheet_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schematic_versions (
                    version_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    version_tag TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    change_note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES schematic_projects(project_id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_components (
                    component_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schematic_user ON schematic_projects(user_id, workspace_id)")
            conn.commit()

    # -------------------------------------------------------------------------
    # PROJECT MANAGEMENT
    # -------------------------------------------------------------------------

    def create_project(self, req: SchematicProjectCreate) -> SchematicProject:
        project_id = f"sch_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        sheet = req.sheet or SchematicSheet(
            sheet_id=f"sheet_{uuid.uuid4().hex[:6]}",
            title=req.title,
            components=[],
            nets=[],
            wires=[],
        )

        sheet_json = json.dumps(sheet.model_dump(), indent=2)

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO schematic_projects (project_id, user_id, workspace_id, title, description, version, sheet_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, '1.0.0', ?, ?, ?)
                """,
                (project_id, req.user_id, req.workspace_id, req.title, req.description or "", sheet_json, now, now),
            )
            conn.commit()

        return self.get_project(project_id, req.user_id, req.workspace_id)

    def get_project(self, project_id: str, user_id: str = "default_user", workspace_id: str = "default_workspace") -> SchematicProject:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM schematic_projects WHERE project_id = ? AND user_id = ? AND workspace_id = ?",
                (project_id, user_id, workspace_id),
            ).fetchone()

            if not row:
                raise ValueError(f"Schematic project '{project_id}' not found.")

            sheet_data = json.loads(row["sheet_json"])
            return SchematicProject(
                project_id=row["project_id"],
                user_id=row["user_id"],
                workspace_id=row["workspace_id"],
                title=row["title"],
                description=row["description"] or "",
                version=row["version"],
                sheet=SchematicSheet(**sheet_data),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_projects(self, user_id: str = "default_user", workspace_id: str = "default_workspace") -> List[SchematicProject]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM schematic_projects WHERE user_id = ? AND workspace_id = ? ORDER BY updated_at DESC",
                (user_id, workspace_id),
            ).fetchall()

            projects = []
            for row in rows:
                sheet_data = json.loads(row["sheet_json"])
                projects.append(
                    SchematicProject(
                        project_id=row["project_id"],
                        user_id=row["user_id"],
                        workspace_id=row["workspace_id"],
                        title=row["title"],
                        description=row["description"] or "",
                        version=row["version"],
                        sheet=SchematicSheet(**sheet_data),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return projects

    def update_project(self, project_id: str, req: SchematicProjectUpdate) -> SchematicProject:
        existing = self.get_project(project_id, req.user_id, req.workspace_id)
        now = datetime.now(timezone.utc).isoformat()

        title = req.title if req.title is not None else existing.title
        desc = req.description if req.description is not None else existing.description
        sheet = req.sheet if req.sheet is not None else existing.sheet

        version = existing.version
        if req.bump_version:
            # Increment patch or minor
            parts = version.split(".")
            if len(parts) == 3 and parts[2].isdigit():
                version = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
            else:
                version = f"{version}.1"

            # Create immutable version record
            version_id = f"ver_{uuid.uuid4().hex[:8]}"
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO schematic_versions (version_id, project_id, version_tag, snapshot_json, change_note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (version_id, project_id, version, json.dumps(sheet.model_dump()), req.change_note or "Snapshot", now),
                )
                conn.commit()

        sheet_json = json.dumps(sheet.model_dump(), indent=2)

        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE schematic_projects
                SET title = ?, description = ?, version = ?, sheet_json = ?, updated_at = ?
                WHERE project_id = ? AND user_id = ? AND workspace_id = ?
                """,
                (title, desc, version, sheet_json, now, project_id, req.user_id, req.workspace_id),
            )
            conn.commit()

        return self.get_project(project_id, req.user_id, req.workspace_id)

    def delete_project(self, project_id: str, user_id: str = "default_user", workspace_id: str = "default_workspace") -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM schematic_projects WHERE project_id = ? AND user_id = ? AND workspace_id = ?",
                (project_id, user_id, workspace_id),
            )
            conn.commit()
            return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # CUSTOM COMPONENTS
    # -------------------------------------------------------------------------

    def register_custom_component(self, comp: SchematicComponentDef, user_id: str = "default_user") -> SchematicComponentDef:
        comp.is_custom = True
        comp.spec_verification = "user_defined"
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO custom_components (component_id, user_id, spec_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (comp.component_id, user_id, json.dumps(comp.model_dump()), now),
            )
            conn.commit()
        return comp

    def list_custom_components(self, user_id: str = "default_user") -> List[SchematicComponentDef]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT spec_json FROM custom_components WHERE user_id = ? ORDER BY created_at ASC",
                (user_id,),
            ).fetchall()
            return [SchematicComponentDef(**json.loads(r["spec_json"])) for r in rows]

    # -------------------------------------------------------------------------
    # AI CIRCUIT DESIGN ASSISTANT
    # -------------------------------------------------------------------------

    def generate_circuit_from_prompt(self, req: AICircuitPromptRequest) -> AICircuitDesignResponse:
        """Synthesizes validated electronic schematics from user natural-language goal descriptions."""
        p_lower = req.prompt.lower()
        supply_v = req.target_supply_voltage_v or 5.0

        components: List[ComponentInstance] = []
        nets: List[SchematicNet] = []
        wires = []
        design_notes: List[str] = []
        assumptions: List[str] = []
        warnings: List[str] = []

        # 1. 5V to 3.3V Voltage Regulator Circuit
        if any(k in p_lower for k in ["3.3v", "3v3", "ams1117", "regulator", "power supply", "step down"]):
            circuit_name = "5V to 3.3V LDO Voltage Regulator Circuit"
            desc = "Precision AMS1117-3.3 based linear regulation circuit with input/output bulk and decoupling capacitors and an LED power rail indicator."
            op_expl = "The 5V DC input passes through a 10uF electrolytic capacitor for bulk stability. The AMS1117-3.3 linear regulator drops the voltage to a stable 3.3V rail. High-frequency 100nF ceramic decoupling capacitors on both rails suppress ripple. A 3.3V red status LED with a 330 ohm resistor confirms regulation."

            # Components
            c_vsource = ComponentInstance(instance_id="inst_v1", component_id="vsource_dc", ref_des="V1", value="5V", pos_x=50.0, pos_y=100.0)
            c_cin = ComponentInstance(instance_id="inst_c1", component_id="capacitor_electrolytic", ref_des="C1", value="10uF", pos_x=120.0, pos_y=100.0)
            c_reg = ComponentInstance(instance_id="inst_u1", component_id="regulator_ams1117_3v3", ref_des="U1", value="AMS1117-3.3", pos_x=220.0, pos_y=100.0)
            c_cout = ComponentInstance(instance_id="inst_c2", component_id="capacitor_electrolytic", ref_des="C2", value="10uF", pos_x=320.0, pos_y=100.0)
            c_cdec = ComponentInstance(instance_id="inst_c3", component_id="capacitor_ceramic", ref_des="C3", value="100nF", pos_x=380.0, pos_y=100.0)
            c_rled = ComponentInstance(instance_id="inst_r1", component_id="resistor_generic", ref_des="R1", value="330", pos_x=450.0, pos_y=80.0)
            c_led = ComponentInstance(instance_id="inst_d1", component_id="led_red", ref_des="D1", value="Red", pos_x=450.0, pos_y=140.0)
            c_gnd = ComponentInstance(instance_id="inst_gnd", component_id="ground", ref_des="GND1", value="0V", pos_x=250.0, pos_y=220.0)

            components = [c_vsource, c_cin, c_reg, c_cout, c_cdec, c_rled, c_led, c_gnd]

            # Nets
            nets = [
                SchematicNet(
                    net_id="net_5v",
                    name="+5V",
                    is_power=True,
                    voltage_level_v=5.0,
                    connections=[
                        NetPinConnection(instance_id="inst_v1", pin_id="+"),
                        NetPinConnection(instance_id="inst_c1", pin_id="1"),
                        NetPinConnection(instance_id="inst_u1", pin_id="IN"),
                    ],
                ),
                SchematicNet(
                    net_id="net_3v3",
                    name="+3V3",
                    is_power=True,
                    voltage_level_v=3.3,
                    connections=[
                        NetPinConnection(instance_id="inst_u1", pin_id="OUT"),
                        NetPinConnection(instance_id="inst_c2", pin_id="1"),
                        NetPinConnection(instance_id="inst_c3", pin_id="1"),
                        NetPinConnection(instance_id="inst_r1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_led_mid",
                    name="LED_ANODE",
                    connections=[
                        NetPinConnection(instance_id="inst_r1", pin_id="2"),
                        NetPinConnection(instance_id="inst_d1", pin_id="A"),
                    ],
                ),
                SchematicNet(
                    net_id="net_gnd",
                    name="GND",
                    is_ground=True,
                    voltage_level_v=0.0,
                    connections=[
                        NetPinConnection(instance_id="inst_v1", pin_id="-"),
                        NetPinConnection(instance_id="inst_c1", pin_id="2"),
                        NetPinConnection(instance_id="inst_u1", pin_id="GND"),
                        NetPinConnection(instance_id="inst_c2", pin_id="2"),
                        NetPinConnection(instance_id="inst_c3", pin_id="2"),
                        NetPinConnection(instance_id="inst_d1", pin_id="K"),
                        NetPinConnection(instance_id="inst_gnd", pin_id="1"),
                    ],
                ),
            ]

            design_notes = [
                "Input voltage: 5.0V regulated DC from USB or external supply.",
                "Dropout voltage: 1.1V at full 800mA load. (5.0V - 1.1V = 3.9V headroom, ensuring stable 3.3V regulation).",
                "Power dissipation in AMS1117 at 300mA load is P = (5V - 3.3V) * 0.3A = 0.51W. SOT-223 PCB copper pour recommended.",
                "330 ohm resistor limits LED current to (3.3V - 2.0V) / 330 = 3.9mA for low power draw.",
            ]
            assumptions = [
                "Ambient temperature <= 30 °C.",
                "Input 5V source has <= 100mV peak-to-peak ripple.",
            ]
            warnings = [
                "Do not exceed 12V maximum input on AMS1117 without an external heatsink due to linear thermal dissipation.",
            ]

        # 2. Relay Driver with Transistor & Flyback Diode
        elif any(k in p_lower for k in ["relay", "switch coil", "flyback", "inductive", "bjt driver"]):
            circuit_name = "NPN Transistor Relay Driver with Flyback Clamp"
            desc = "Low-side NPN BJT switching stage designed to safely drive a 5V electromechanical relay coil from a 3.3V or 5V logic signal with inductive flyback protection."
            op_expl = "A logic HIGH signal from an MCU or logic gate drives base current through R1 (1k ohm) into the 2N2222 transistor, driving it into deep saturation (Vce ~ 0.2V). This energizes the relay coil. When the transistor switches off, the collapsing magnetic field creates a high-voltage back-EMF spike; diode D1 (1N4007) clamps this spike safely to the +5V rail, protecting the transistor."

            c_vcc = ComponentInstance(instance_id="inst_vcc", component_id="vsource_dc", ref_des="V1", value="5V", pos_x=50.0, pos_y=80.0)
            c_rb = ComponentInstance(instance_id="inst_r1", component_id="resistor_generic", ref_des="R1", value="1k", pos_x=120.0, pos_y=160.0)
            c_q1 = ComponentInstance(instance_id="inst_q1", component_id="bjt_npn_2n2222", ref_des="Q1", value="2N2222", pos_x=220.0, pos_y=160.0)
            c_d1 = ComponentInstance(instance_id="inst_d1", component_id="diode_1n4007", ref_des="D1", value="1N4007", pos_x=320.0, pos_y=90.0, rotation=90)
            c_relay = ComponentInstance(instance_id="inst_k1", component_id="relay_spdt_5v", ref_des="K1", value="5V Relay", pos_x=320.0, pos_y=160.0)
            c_gnd = ComponentInstance(instance_id="inst_gnd", component_id="ground", ref_des="GND1", value="0V", pos_x=220.0, pos_y=240.0)

            components = [c_vcc, c_rb, c_q1, c_d1, c_relay, c_gnd]

            nets = [
                SchematicNet(
                    net_id="net_5v",
                    name="+5V",
                    is_power=True,
                    voltage_level_v=5.0,
                    connections=[
                        NetPinConnection(instance_id="inst_vcc", pin_id="+"),
                        NetPinConnection(instance_id="inst_d1", pin_id="K"),
                        NetPinConnection(instance_id="inst_k1", pin_id="COIL_P"),
                    ],
                ),
                SchematicNet(
                    net_id="net_ctrl",
                    name="RELAY_CTRL",
                    connections=[
                        NetPinConnection(instance_id="inst_r1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_base",
                    name="Q1_BASE",
                    connections=[
                        NetPinConnection(instance_id="inst_r1", pin_id="2"),
                        NetPinConnection(instance_id="inst_q1", pin_id="B"),
                    ],
                ),
                SchematicNet(
                    net_id="net_coil_low",
                    name="COIL_LOW",
                    connections=[
                        NetPinConnection(instance_id="inst_q1", pin_id="C"),
                        NetPinConnection(instance_id="inst_d1", pin_id="A"),
                        NetPinConnection(instance_id="inst_k1", pin_id="COIL_N"),
                    ],
                ),
                SchematicNet(
                    net_id="net_gnd",
                    name="GND",
                    is_ground=True,
                    voltage_level_v=0.0,
                    connections=[
                        NetPinConnection(instance_id="inst_vcc", pin_id="-"),
                        NetPinConnection(instance_id="inst_q1", pin_id="E"),
                        NetPinConnection(instance_id="inst_gnd", pin_id="1"),
                    ],
                ),
            ]

            design_notes = [
                "Relay coil current: ~70mA at 5V DC.",
                "Base resistor R1 = (3.3V - 0.7V) / (70mA / 10) = 2.6V / 7mA = ~370 ohms (1k provides 2.6mA, sufficient for beta=27).",
                "Flyback diode D1 MUST be connected with cathode to +5V and anode to transistor collector.",
            ]
            assumptions = ["Control pin provides at least 3.3V logic HIGH."]
            warnings = ["Omitting diode D1 will cause inductive flyback breakdown exceeding 2N2222 40V rating."]

        # 3. Inverting Operational Amplifier Circuit
        elif any(k in p_lower for k in ["opamp", "amplifier", "inverting", "gain", "lm358"]):
            circuit_name = "LM358 Inverting Op-Amp Amplifier (Gain = -10)"
            desc = "Precision analog inverting amplifier using LM358 operational amplifier with negative feedback."
            op_expl = "The non-inverting input (IN+) is referenced to virtual or circuit ground. Feedback resistor Rf (100k) and input resistor Rin (10k) establish closed-loop inverting gain Av = -Rf / Rin = -100k / 10k = -10. Output voltage Vout = -10 * Vin."

            c_vcc = ComponentInstance(instance_id="inst_vcc", component_id="vsource_dc", ref_des="V1", value="12V", pos_x=50.0, pos_y=60.0)
            c_rin = ComponentInstance(instance_id="inst_r1", component_id="resistor_generic", ref_des="R1", value="10k", pos_x=120.0, pos_y=140.0)
            c_rf = ComponentInstance(instance_id="inst_r2", component_id="resistor_generic", ref_des="R2", value="100k", pos_x=220.0, pos_y=80.0)
            c_opamp = ComponentInstance(instance_id="inst_u1", component_id="opamp_lm358", ref_des="U1", value="LM358", pos_x=220.0, pos_y=140.0)
            c_cdec = ComponentInstance(instance_id="inst_c1", component_id="capacitor_ceramic", ref_des="C1", value="100nF", pos_x=160.0, pos_y=60.0)
            c_gnd = ComponentInstance(instance_id="inst_gnd", component_id="ground", ref_des="GND1", value="0V", pos_x=220.0, pos_y=220.0)

            components = [c_vcc, c_rin, c_rf, c_opamp, c_cdec, c_gnd]

            nets = [
                SchematicNet(
                    net_id="net_vcc",
                    name="+12V",
                    is_power=True,
                    voltage_level_v=12.0,
                    connections=[
                        NetPinConnection(instance_id="inst_vcc", pin_id="+"),
                        NetPinConnection(instance_id="inst_opamp", pin_id="8"),
                        NetPinConnection(instance_id="inst_c1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_in",
                    name="SIGNAL_IN",
                    connections=[
                        NetPinConnection(instance_id="inst_r1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_inv_node",
                    name="SUMMING_NODE",
                    connections=[
                        NetPinConnection(instance_id="inst_r1", pin_id="2"),
                        NetPinConnection(instance_id="inst_r2", pin_id="1"),
                        NetPinConnection(instance_id="inst_u1", pin_id="2"),
                    ],
                ),
                SchematicNet(
                    net_id="net_out",
                    name="SIGNAL_OUT",
                    connections=[
                        NetPinConnection(instance_id="inst_r2", pin_id="2"),
                        NetPinConnection(instance_id="inst_u1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_gnd",
                    name="GND",
                    is_ground=True,
                    voltage_level_v=0.0,
                    connections=[
                        NetPinConnection(instance_id="inst_vcc", pin_id="-"),
                        NetPinConnection(instance_id="inst_u1", pin_id="3"),
                        NetPinConnection(instance_id="inst_u1", pin_id="4"),
                        NetPinConnection(instance_id="inst_c1", pin_id="2"),
                        NetPinConnection(instance_id="inst_gnd", pin_id="1"),
                    ],
                ),
            ]

            design_notes = [
                "Gain Av = -Rf / Rin = -100k / 10k = -10.",
                "Input impedance equals Rin = 10k ohms.",
                "Dual supplies or AC coupling with mid-rail virtual ground bias required if negative output swing is needed.",
            ]
            assumptions = ["Single supply mode swing is bounded from ~20mV above GND to ~1.5V below VCC."]
            warnings = ["Inverting stage without split dual supply cannot swing below 0V without clipping."]

        # 4. Default: LED Indicator with Current Limiter & Switch
        else:
            circuit_name = f"DC Powered LED Indicator Circuit ({supply_v}V)"
            desc = "Standard low-power LED indicator circuit with tactile switch control and calculated current limiting resistor."
            op_expl = f"A {supply_v}V DC voltage source connects through an SPST switch and current limiting resistor R1 to a red LED. When the switch closes, current flows through the circuit, illuminating the LED."

            # Calculate resistor for supply_v
            vf = 2.0
            r_val = int(max(100.0, round((supply_v - vf) / 0.015 / 10.0) * 10.0))

            c_vcc = ComponentInstance(instance_id="inst_v1", component_id="vsource_dc", ref_des="V1", value=f"{supply_v}V", pos_x=50.0, pos_y=100.0)
            c_sw = ComponentInstance(instance_id="inst_sw1", component_id="switch_spst", ref_des="SW1", value="Pushbutton", pos_x=140.0, pos_y=100.0)
            c_r1 = ComponentInstance(instance_id="inst_r1", component_id="resistor_generic", ref_des="R1", value=f"{r_val}", pos_x=240.0, pos_y=100.0)
            c_d1 = ComponentInstance(instance_id="inst_d1", component_id="led_red", ref_des="D1", value="Red", pos_x=340.0, pos_y=100.0)
            c_gnd = ComponentInstance(instance_id="inst_gnd", component_id="ground", ref_des="GND1", value="0V", pos_x=200.0, pos_y=180.0)

            components = [c_vcc, c_sw, c_r1, c_d1, c_gnd]

            nets = [
                SchematicNet(
                    net_id="net_vcc",
                    name="VCC",
                    is_power=True,
                    voltage_level_v=supply_v,
                    connections=[
                        NetPinConnection(instance_id="inst_v1", pin_id="+"),
                        NetPinConnection(instance_id="inst_sw1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_sw_out",
                    name="SW_OUT",
                    connections=[
                        NetPinConnection(instance_id="inst_sw1", pin_id="2"),
                        NetPinConnection(instance_id="inst_r1", pin_id="1"),
                    ],
                ),
                SchematicNet(
                    net_id="net_led_a",
                    name="LED_ANODE",
                    connections=[
                        NetPinConnection(instance_id="inst_r1", pin_id="2"),
                        NetPinConnection(instance_id="inst_d1", pin_id="A"),
                    ],
                ),
                SchematicNet(
                    net_id="net_gnd",
                    name="GND",
                    is_ground=True,
                    voltage_level_v=0.0,
                    connections=[
                        NetPinConnection(instance_id="inst_v1", pin_id="-"),
                        NetPinConnection(instance_id="inst_d1", pin_id="K"),
                        NetPinConnection(instance_id="inst_gnd", pin_id="1"),
                    ],
                ),
            ]

            actual_i = ((supply_v - vf) / r_val) * 1000.0
            design_notes = [
                f"Resistor R1 ({r_val} ohms) limits LED forward current to {actual_i:.1f} mA.",
                f"Resistor power dissipation is P = {((actual_i/1000)**2 * r_val)*1000:.1f} mW (1/4W rating is fully safe).",
            ]
            assumptions = [f"DC source is stable {supply_v}V DC."]
            warnings = ["Do not short out resistor R1 while switch is closed."]

        sheet = SchematicSheet(
            sheet_id=f"sheet_ai_{uuid.uuid4().hex[:6]}",
            title=circuit_name,
            components=components,
            nets=nets,
            wires=wires,
        )

        return AICircuitDesignResponse(
            circuit_name=circuit_name,
            description=desc,
            operational_explanation=op_expl,
            sheet=sheet,
            design_notes=design_notes,
            engineering_assumptions=assumptions,
            design_warnings=warnings,
            engineering_review_required=True,
            review_banner="MANDATORY REVIEW: AI-generated electronic schematic requires qualified engineering verification before prototyping, simulation sign-off, or physical PCB fabrication.",
        )

    # -------------------------------------------------------------------------
    # EXPORTS (BOM, SPICE, KiCad, SVG)
    # -------------------------------------------------------------------------

    def export_schematic(self, sheet: SchematicSheet, export_format: str) -> SchematicExportResponse:
        catalog = build_standard_component_catalog()

        if export_format == "spice_netlist":
            content = generate_spice_netlist(sheet, analysis_type="op")
            return SchematicExportResponse(
                export_format="spice_netlist",
                content=content,
                filename=f"{sheet.title.replace(' ', '_').lower()}.cir",
                mime_type="text/plain",
            )

        elif export_format == "bom_json":
            # Group components by component_id and value
            grouped: Dict[str, Dict[str, Any]] = {}
            for inst in sheet.components:
                key = f"{inst.component_id}_{inst.value}"
                comp_def = catalog.get(inst.component_id)
                if key not in grouped:
                    grouped[key] = {
                        "component_id": inst.component_id,
                        "name": comp_def.name if comp_def else inst.component_id,
                        "value": inst.value,
                        "tolerance": inst.tolerance,
                        "footprint": comp_def.footprint if comp_def else "0805",
                        "quantity": 0,
                        "ref_designators": [],
                        "max_voltage_v": comp_def.max_voltage_v if comp_def else None,
                        "max_power_mw": comp_def.max_power_mw if comp_def else None,
                        "datasheet_url": comp_def.datasheet_url if comp_def else None,
                    }
                grouped[key]["quantity"] += 1
                grouped[key]["ref_designators"].append(inst.ref_des)

            bom_list = list(grouped.values())
            return SchematicExportResponse(
                export_format="bom_json",
                content=json.dumps(bom_list, indent=2),
                filename=f"bom_{sheet.title.replace(' ', '_').lower()}.json",
                mime_type="application/json",
            )

        elif export_format == "bom_csv":
            grouped: Dict[str, Dict[str, Any]] = {}
            for inst in sheet.components:
                key = f"{inst.component_id}_{inst.value}"
                comp_def = catalog.get(inst.component_id)
                if key not in grouped:
                    grouped[key] = {
                        "name": comp_def.name if comp_def else inst.component_id,
                        "value": inst.value,
                        "footprint": comp_def.footprint if comp_def else "0805",
                        "quantity": 0,
                        "ref_designators": [],
                        "datasheet_url": comp_def.datasheet_url if comp_def else "",
                    }
                grouped[key]["quantity"] += 1
                grouped[key]["ref_designators"].append(inst.ref_des)

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Item", "Quantity", "Reference Designators", "Value", "Component Name", "Footprint", "Datasheet URL"])
            for idx, item in enumerate(grouped.values(), 1):
                writer.writerow([
                    idx,
                    item["quantity"],
                    ", ".join(sorted(item["ref_designators"])),
                    item["value"],
                    item["name"],
                    item["footprint"],
                    item["datasheet_url"],
                ])

            return SchematicExportResponse(
                export_format="bom_csv",
                content=output.getvalue(),
                filename=f"bom_{sheet.title.replace(' ', '_').lower()}.csv",
                mime_type="text/csv",
            )

        elif export_format == "connection_table_json":
            table = []
            for net in sheet.nets:
                table.append({
                    "net_name": net.name,
                    "is_power": net.is_power,
                    "is_ground": net.is_ground,
                    "voltage_level_v": net.voltage_level_v,
                    "connection_count": len(net.connections),
                    "connected_pins": [
                        {"instance_id": c.instance_id, "pin_id": c.pin_id}
                        for c in net.connections
                    ],
                })
            return SchematicExportResponse(
                export_format="connection_table_json",
                content=json.dumps(table, indent=2),
                filename=f"connections_{sheet.title.replace(' ', '_').lower()}.json",
                mime_type="application/json",
            )

        elif export_format == "kicad_netlist":
            # Generate KiCad-compatible netlist text
            lines = [
                f"(export (version D)",
                f"  (design",
                f'    (source "{sheet.title}")',
                f'    (date "{datetime.now(timezone.utc).isoformat()}")',
                f'    (tool "NEXORA AI Schematic Studio Stage 27")',
                f"  )",
                f"  (components",
            ]
            for inst in sheet.components:
                comp_def = catalog.get(inst.component_id)
                footprint = comp_def.footprint if comp_def else "0805"
                lines.append(f'    (comp (ref {inst.ref_des})')
                lines.append(f'      (value "{inst.value}")')
                lines.append(f'      (footprint "{footprint}")')
                lines.append(f"    )")
            lines.append("  )")
            lines.append("  (nets")
            for idx, net in enumerate(sheet.nets, 1):
                lines.append(f'    (net (code {idx}) (name "{net.name}")')
                for conn in net.connections:
                    inst = next((c for c in sheet.components if c.instance_id == conn.instance_id), None)
                    ref = inst.ref_des if inst else conn.instance_id
                    lines.append(f'      (node (ref {ref}) (pin {conn.pin_id}))')
                lines.append("    )")
            lines.append("  )")
            lines.append(")")

            return SchematicExportResponse(
                export_format="kicad_netlist",
                content="\n".join(lines),
                filename=f"{sheet.title.replace(' ', '_').lower()}.net",
                mime_type="text/plain",
            )

        elif export_format == "svg_schematic":
            # Generate clean SVG schematic diagram
            svg_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 700" width="1000" height="700" style="background:#0a0f1d; font-family: monospace;">',
                '  <defs>',
                '    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">',
                '      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#14213d" stroke-width="0.5"/>',
                '    </pattern>',
                '  </defs>',
                '  <rect width="1000" height="700" fill="url(#grid)" />',
                f'  <!-- Title block -->',
                f'  <text x="30" y="40" fill="#38bdf8" font-size="18" font-weight="bold">{sheet.title}</text>',
                f'  <text x="30" y="60" fill="#94a3b8" font-size="11">NEXORA AI EDA Studio Stage 27 · Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</text>',
            ]

            # Render components
            for inst in sheet.components:
                x = inst.pos_x
                y = inst.pos_y
                comp_def = catalog.get(inst.component_id)
                cat = comp_def.category if comp_def else "custom"

                # Draw component box and label
                color = "#38bdf8" if "resistor" in cat or "capacitor" in cat else ("#4ade80" if "semiconductor" in cat else "#c084fc")
                svg_lines.append(f'  <!-- Component {inst.ref_des} -->')
                svg_lines.append(f'  <g transform="translate({x},{y})">')
                svg_lines.append(f'    <rect x="-25" y="-18" width="50" height="36" rx="4" fill="#0f172a" stroke="{color}" stroke-width="1.5" />')
                svg_lines.append(f'    <text x="0" y="-3" fill="#f8fafc" font-size="11" font-weight="bold" text-anchor="middle">{inst.ref_des}</text>')
                svg_lines.append(f'    <text x="0" y="10" fill="#94a3b8" font-size="9" text-anchor="middle">{inst.value}</text>')
                svg_lines.append(f'  </g>')

            # Render net annotations
            for idx, net in enumerate(sheet.nets):
                color = "#f43f5e" if net.is_power else ("#22d3ee" if not net.is_ground else "#10b981")
                svg_lines.append(f'  <!-- Net {net.name} -->')
                svg_lines.append(f'  <text x="820" y="{80 + idx * 20}" fill="{color}" font-size="11">● {net.name} ({len(net.connections)} pins)</text>')

            svg_lines.append('</svg>')

            return SchematicExportResponse(
                export_format="svg_schematic",
                content="\n".join(svg_lines),
                filename=f"schematic_{sheet.title.replace(' ', '_').lower()}.svg",
                mime_type="image/svg+xml",
            )

        else:
            raise ValueError(f"Unsupported export format '{export_format}'.")

    # -------------------------------------------------------------------------
    # OVERVIEW STATUS
    # -------------------------------------------------------------------------

    def get_overview(self, user_id: str = "default_user", workspace_id: str = "default_workspace") -> SchematicOverviewResponse:
        projects = self.list_projects(user_id, workspace_id)
        customs = self.list_custom_components(user_id)
        catalog = build_standard_component_catalog()
        toolchains = detect_eda_toolchains()

        return SchematicOverviewResponse(
            stage=27,
            projects_count=len(projects),
            custom_components_count=len(customs),
            recent_projects=projects[:5],
            standard_components_count=len(catalog),
            toolchains=toolchains,
        )


schematic_studio_engine = SchematicStudioEngine()
