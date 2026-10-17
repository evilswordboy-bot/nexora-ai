from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from app.config import settings
from app.models.schemas import (
    PCBBoard,
    PCBComponent,
    PCBTrack,
    PCBVia,
    PCBNet,
    PCBNetPadConnection,
    PCBDesignRules,
    PCBProject,
    PCBDrcReport,
    PCBOverviewResponse,
)
from app.services.pcb_studio.footprints import FOOTPRINT_LIBRARY
from app.services.pcb_studio.drc import run_design_rule_check
from app.services.schematic_studio.catalog import detect_eda_toolchains


def utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class PCBStudioEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.pcb_db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pcb_projects (
                    project_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    schematic_project_id TEXT,
                    version TEXT NOT NULL,
                    board_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pcb_revisions (
                    revision_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    board_json TEXT NOT NULL,
                    drc_report_json TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES pcb_projects(project_id) ON DELETE CASCADE
                )
            """)
            conn.commit()

        # Seed sample project if empty
        self._seed_sample_project_if_empty()

    def _seed_sample_project_if_empty(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM pcb_projects")
            row = cursor.fetchone()
            if row and row["count"] > 0:
                return

        # Create 5V Regulated IoT Power & Status Board sample
        board = PCBBoard(
            board_id="brd_demo_sample",
            title="IoT Power Regulator & Status Beacon",
            width_mm=80.0,
            height_mm=55.0,
            corner_radius_mm=3.0,
            layer_count=2,
            copper_thickness_oz=1.0,
            board_thickness_mm=1.6,
            components=[
                PCBComponent(
                    component_instance_id="c_j1",
                    ref_des="J1",
                    value="VIN_BARREL_JACK",
                    footprint_id="PinHeader_1x02_P2.54mm",
                    pos_x_mm=15.0,
                    pos_y_mm=27.5,
                    rotation_deg=0.0,
                    side="top",
                    attributes={"description": "DC Barrel Power In (7-12V)"},
                ),
                PCBComponent(
                    component_instance_id="c_u1",
                    ref_des="U1",
                    value="AMS1117-5.0",
                    footprint_id="SOT-223",
                    pos_x_mm=38.0,
                    pos_y_mm=27.5,
                    rotation_deg=0.0,
                    side="top",
                    attributes={"description": "5.0V Low Dropout Linear Regulator"},
                ),
                PCBComponent(
                    component_instance_id="c_c1",
                    ref_des="C1",
                    value="10uF",
                    footprint_id="0805",
                    pos_x_mm=28.0,
                    pos_y_mm=22.0,
                    rotation_deg=90.0,
                    side="top",
                    attributes={"voltage": "25V"},
                ),
                PCBComponent(
                    component_instance_id="c_c2",
                    ref_des="C2",
                    value="22uF",
                    footprint_id="0805",
                    pos_x_mm=48.0,
                    pos_y_mm=22.0,
                    rotation_deg=90.0,
                    side="top",
                    attributes={"voltage": "16V"},
                ),
                PCBComponent(
                    component_instance_id="c_r1",
                    ref_des="R1",
                    value="470R",
                    footprint_id="0805",
                    pos_x_mm=58.0,
                    pos_y_mm=24.0,
                    rotation_deg=0.0,
                    side="top",
                    attributes={"power": "0.125W"},
                ),
                PCBComponent(
                    component_instance_id="c_d1",
                    ref_des="D1",
                    value="LED_CYAN",
                    footprint_id="LED_0805",
                    pos_x_mm=68.0,
                    pos_y_mm=24.0,
                    rotation_deg=0.0,
                    side="top",
                    attributes={"color": "cyan"},
                ),
                PCBComponent(
                    component_instance_id="c_mh1",
                    ref_des="H1",
                    value="M3_MOUNTING_HOLE",
                    footprint_id="MountingHole_M3",
                    pos_x_mm=6.0,
                    pos_y_mm=6.0,
                    rotation_deg=0.0,
                    side="top",
                    attributes={},
                ),
                PCBComponent(
                    component_instance_id="c_mh2",
                    ref_des="H2",
                    value="M3_MOUNTING_HOLE",
                    footprint_id="MountingHole_M3",
                    pos_x_mm=74.0,
                    pos_y_mm=49.0,
                    rotation_deg=0.0,
                    side="top",
                    attributes={},
                ),
            ],
            tracks=[
                # Power input track from J1 to C1 and U1
                PCBTrack(
                    track_id="tr_1",
                    net_id="VIN",
                    layer="F.Cu",
                    start_x_mm=16.27,
                    start_y_mm=27.5,
                    end_x_mm=28.0,
                    end_y_mm=22.0,
                    width_mm=0.60,
                ),
                PCBTrack(
                    track_id="tr_2",
                    net_id="VIN",
                    layer="F.Cu",
                    start_x_mm=28.0,
                    start_y_mm=22.0,
                    end_x_mm=38.0,
                    end_y_mm=24.4,
                    width_mm=0.60,
                ),
                # 5V Output track from U1 to C2 and R1
                PCBTrack(
                    track_id="tr_3",
                    net_id="+5V",
                    layer="F.Cu",
                    start_x_mm=38.0,
                    start_y_mm=27.5,
                    end_x_mm=48.0,
                    end_y_mm=22.0,
                    width_mm=0.50,
                ),
                PCBTrack(
                    track_id="tr_4",
                    net_id="+5V",
                    layer="F.Cu",
                    start_x_mm=48.0,
                    start_y_mm=22.0,
                    end_x_mm=56.9,
                    end_y_mm=24.0,
                    width_mm=0.40,
                ),
                # LED connection
                PCBTrack(
                    track_id="tr_5",
                    net_id="NET_LED",
                    layer="F.Cu",
                    start_x_mm=59.1,
                    start_y_mm=24.0,
                    end_x_mm=66.9,
                    end_y_mm=24.0,
                    width_mm=0.30,
                ),
            ],
            vias=[
                PCBVia(
                    via_id="via_gnd_1",
                    net_id="GND",
                    x_mm=38.0,
                    y_mm=33.0,
                    diameter_mm=0.6,
                    drill_mm=0.3,
                    start_layer="F.Cu",
                    end_layer="B.Cu",
                )
            ],
            zones=[],
            nets=[
                PCBNet(
                    net_id="VIN",
                    name="VIN",
                    color="#f59e0b",
                    is_power=True,
                    is_ground=False,
                    voltage_level_v=12.0,
                    connections=[
                        PCBNetPadConnection(component_instance_id="c_j1", pad_number="1"),
                        PCBNetPadConnection(component_instance_id="c_c1", pad_number="1"),
                        PCBNetPadConnection(component_instance_id="c_u1", pad_number="3"),
                    ],
                ),
                PCBNet(
                    net_id="+5V",
                    name="+5V",
                    color="#ef4444",
                    is_power=True,
                    is_ground=False,
                    voltage_level_v=5.0,
                    connections=[
                        PCBNetPadConnection(component_instance_id="c_u1", pad_number="2"),
                        PCBNetPadConnection(component_instance_id="c_c2", pad_number="1"),
                        PCBNetPadConnection(component_instance_id="c_r1", pad_number="1"),
                    ],
                ),
                PCBNet(
                    net_id="GND",
                    name="GND",
                    color="#10b981",
                    is_power=False,
                    is_ground=True,
                    voltage_level_v=0.0,
                    connections=[
                        PCBNetPadConnection(component_instance_id="c_j1", pad_number="2"),
                        PCBNetPadConnection(component_instance_id="c_c1", pad_number="2"),
                        PCBNetPadConnection(component_instance_id="c_u1", pad_number="1"),
                        PCBNetPadConnection(component_instance_id="c_c2", pad_number="2"),
                        PCBNetPadConnection(component_instance_id="c_d1", pad_number="2"),
                    ],
                ),
                PCBNet(
                    net_id="NET_LED",
                    name="NET_LED",
                    color="#06b6d4",
                    is_power=False,
                    is_ground=False,
                    connections=[
                        PCBNetPadConnection(component_instance_id="c_r1", pad_number="2"),
                        PCBNetPadConnection(component_instance_id="c_d1", pad_number="1"),
                    ],
                ),
            ],
            design_rules=PCBDesignRules(
                min_trace_width_mm=0.25,
                min_clearance_mm=0.20,
                min_board_edge_clearance_mm=0.50,
                min_drill_diameter_mm=0.30,
            ),
        )

        project = PCBProject(
            project_id="prj_pcb_demo_power",
            user_id="default_user",
            workspace_id="default_workspace",
            title="IoT Power Regulator & Status Beacon",
            description="2-Layer 5V power regulator PCB with AMS1117-5.0 LDO, decoupling capacitors, and power status LED.",
            schematic_project_id="prj_schematic_sample_1",
            version="v1.0.0",
            board=board,
        )
        self.save_project(project, notes="Initial seed reference design")

    def save_project(
        self,
        project: PCBProject,
        version_bump: bool = False,
        notes: str = "",
    ) -> PCBProject:
        """Saves a PCB project and records a version snapshot in SQLite."""
        if version_bump:
            try:
                parts = project.version.lstrip("v").split(".")
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                project.version = f"v{major}.{minor}.{patch + 1}"
            except Exception:
                project.version = f"v1.0.{uuid.uuid4().hex[:4]}"

        board_json = project.board.model_dump_json()
        now_str = utc_iso()

        drc_report = run_design_rule_check(project.board)
        drc_json = drc_report.model_dump_json()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pcb_projects (
                    project_id, user_id, workspace_id, title, description,
                    schematic_project_id, version, board_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    version=excluded.version,
                    board_json=excluded.board_json,
                    updated_at=excluded.updated_at
                """,
                (
                    project.project_id,
                    project.user_id,
                    project.workspace_id,
                    project.title,
                    project.description,
                    project.schematic_project_id,
                    project.version,
                    board_json,
                    project.created_at.isoformat() if hasattr(project.created_at, "isoformat") else str(project.created_at),
                    now_str,
                ),
            )

            # Record Revision
            rev_id = f"rev_{uuid.uuid4().hex[:10]}"
            cursor.execute(
                """
                INSERT INTO pcb_revisions (
                    revision_id, project_id, version, board_json, drc_report_json, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rev_id,
                    project.project_id,
                    project.version,
                    board_json,
                    drc_json,
                    notes or f"Snapshot at {now_str}",
                    now_str,
                ),
            )
            conn.commit()

        return self.get_project(project.project_id) or project

    def get_project(self, project_id: str) -> Optional[PCBProject]:
        """Retrieves a PCB project by project_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pcb_projects WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None

            board_data = json.loads(row["board_json"])
            board = PCBBoard(**board_data)

            cursor.execute(
                "SELECT revision_id, version, notes, created_at FROM pcb_revisions WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
            revisions = [dict(r) for r in cursor.fetchall()]

            return PCBProject(
                project_id=row["project_id"],
                user_id=row["user_id"],
                workspace_id=row["workspace_id"],
                title=row["title"],
                description=row["description"] or "",
                schematic_project_id=row["schematic_project_id"],
                version=row["version"],
                board=board,
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "")),
                updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "")),
                history_revisions=revisions,
            )

    def list_projects(self, user_id: str = "default_user") -> List[PCBProject]:
        """Lists all PCB projects for a user."""
        projects: List[PCBProject] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT project_id FROM pcb_projects WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            )
            rows = cursor.fetchall()

        for r in rows:
            p = self.get_project(r["project_id"])
            if p:
                projects.append(p)
        return projects

    def delete_project(self, project_id: str) -> bool:
        """Deletes a PCB project and its revisions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pcb_revisions WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM pcb_projects WHERE project_id = ?", (project_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_revision(self, revision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a revision by revision_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pcb_revisions WHERE revision_id = ?", (revision_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "revision_id": row["revision_id"],
                "project_id": row["project_id"],
                "version": row["version"],
                "board": json.loads(row["board_json"]),
                "drc_report": json.loads(row["drc_report_json"]) if row["drc_report_json"] else None,
                "notes": row["notes"],
                "created_at": row["created_at"],
            }

    def rollback_to_revision(self, project_id: str, revision_id: str) -> Optional[PCBProject]:
        """Rolls back the active board of a project to a specific revision snapshot."""
        rev = self.get_revision(revision_id)
        if not rev or rev["project_id"] != project_id:
            return None

        project = self.get_project(project_id)
        if not project:
            return None

        project.board = PCBBoard(**rev["board"])
        project.version = rev["version"] + "-rollback"
        return self.save_project(project, version_bump=False, notes=f"Rolled back to revision {revision_id}")

    def diff_board_revisions(
        self,
        board_a: PCBBoard,
        board_b: PCBBoard,
    ) -> Dict[str, Any]:
        """Calculates differences between two PCB board layouts."""
        refs_a = {c.ref_des: c for c in board_a.components}
        refs_b = {c.ref_des: c for c in board_b.components}

        added_components = [refs_b[r].model_dump() for r in refs_b if r not in refs_a]
        removed_components = [refs_a[r].model_dump() for r in refs_a if r not in refs_b]

        moved_components = []
        for r in refs_a:
            if r in refs_b:
                ca = refs_a[r]
                cb = refs_b[r]
                if abs(ca.pos_x_mm - cb.pos_x_mm) > 0.01 or abs(ca.pos_y_mm - cb.pos_y_mm) > 0.01:
                    moved_components.append({
                        "ref_des": r,
                        "old_pos": (ca.pos_x_mm, ca.pos_y_mm),
                        "new_pos": (cb.pos_x_mm, cb.pos_y_mm),
                    })

        tracks_delta = len(board_b.tracks) - len(board_a.tracks)
        vias_delta = len(board_b.vias) - len(board_a.vias)

        return {
            "components_added_count": len(added_components),
            "components_removed_count": len(removed_components),
            "components_moved_count": len(moved_components),
            "added_components": added_components,
            "removed_components": removed_components,
            "moved_components": moved_components,
            "tracks_delta": tracks_delta,
            "vias_delta": vias_delta,
            "board_size_a": (board_a.width_mm, board_a.height_mm),
            "board_size_b": (board_b.width_mm, board_b.height_mm),
        }

    def get_overview(self, user_id: str = "default_user") -> PCBOverviewResponse:
        """Provides an executive overview of PCB projects and library availability."""
        projects = self.list_projects(user_id)
        toolchains = detect_eda_toolchains()

        return PCBOverviewResponse(
            stage=28,
            projects_count=len(projects),
            footprints_count=len(FOOTPRINT_LIBRARY),
            recent_projects=projects[:5],
            toolchains=toolchains,
        )


_engine_instance: Optional[PCBStudioEngine] = None


def get_pcb_engine() -> PCBStudioEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PCBStudioEngine()
    return _engine_instance
