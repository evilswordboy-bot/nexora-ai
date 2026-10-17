from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional, Tuple, Any

from app.models.schemas import (
    PCBBoard,
    PCBTrack,
    PCBVia,
    PCBComponent,
    PCBDrcFinding,
    PCBDrcReport,
)
from app.services.pcb_studio.footprints import FOOTPRINT_LIBRARY, get_footprint_definition
from app.services.pcb_studio.routing import (
    get_pad_absolute_position,
    calculate_routing_summary,
)


def point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
) -> float:
    """Calculates perpendicular Euclidean distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-9:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def segment_to_segment_distance(
    x1: float, y1: float, x2: float, y2: float,
    x3: float, y3: float, x4: float, y4: float,
) -> float:
    """Calculates minimum Euclidean distance between two 2D line segments."""
    # Check if segments intersect
    def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
        return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

    if (
        ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4)
        and ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4)
    ):
        return 0.0  # They intersect

    d1 = point_to_segment_distance(x1, y1, x3, y3, x4, y4)
    d2 = point_to_segment_distance(x2, y2, x3, y3, x4, y4)
    d3 = point_to_segment_distance(x3, y3, x1, y1, x2, y2)
    d4 = point_to_segment_distance(x4, y4, x1, y1, x2, y2)
    return min(d1, d2, d3, d4)


def run_design_rule_check(board: PCBBoard) -> PCBDrcReport:
    """
    Executes geometric and electrical Design Rule Checks (DRC) on the PCB layout.
    
    Checks include:
    1. Minimum trace width violation
    2. Copper-to-copper clearance violation between distinct nets
    3. Board-edge clearance violation
    4. Drill hole diameter violation
    5. Direct short circuits (intersecting tracks of different nets)
    6. Unrouted net connections (ratsnest flylines)
    7. Overlapping component courtyards
    8. High-current / thermal trace width advisory
    """
    rules = board.design_rules
    findings: List[PCBDrcFinding] = []

    # 1. Minimum Trace Width Check
    for track in board.tracks:
        if track.width_mm < rules.min_trace_width_mm - 1e-4:
            mid_x = (track.start_x_mm + track.end_x_mm) / 2.0
            mid_y = (track.start_y_mm + track.end_y_mm) / 2.0
            findings.append(
                PCBDrcFinding(
                    finding_id=f"drc_w_{uuid.uuid4().hex[:8]}",
                    rule_code="DRC_MIN_TRACE_WIDTH",
                    severity="critical",
                    title="Minimum Trace Width Violation",
                    message=f"Track width {track.width_mm:.3f}mm is below minimum allowable width ({rules.min_trace_width_mm:.2f}mm).",
                    affected_layer=track.layer,
                    affected_net=track.net_id,
                    pos_x_mm=round(mid_x, 2),
                    pos_y_mm=round(mid_y, 2),
                    remediation_steps=f"Increase track width to at least {rules.min_trace_width_mm:.2f}mm to prevent etching defects.",
                )
            )

    # 2. Minimum Drill Diameter Check (Vias & Pads)
    for via in board.vias:
        if via.drill_mm < rules.min_drill_diameter_mm - 1e-4:
            findings.append(
                PCBDrcFinding(
                    finding_id=f"drc_drill_{uuid.uuid4().hex[:8]}",
                    rule_code="DRC_MIN_DRILL_DIAMETER",
                    severity="critical",
                    title="Minimum Via Drill Diameter Violation",
                    message=f"Via drill {via.drill_mm:.3f}mm is below fabrication limit ({rules.min_drill_diameter_mm:.2f}mm).",
                    affected_layer="All",
                    affected_net=via.net_id,
                    pos_x_mm=round(via.x_mm, 2),
                    pos_y_mm=round(via.y_mm, 2),
                    remediation_steps=f"Enlarge via drill diameter to at least {rules.min_drill_diameter_mm:.2f}mm (typical standard drill).",
                )
            )

    # 3. Board Edge Clearance Check
    edge_margin = rules.min_board_edge_clearance_mm
    for track in board.tracks:
        for x, y in [(track.start_x_mm, track.start_y_mm), (track.end_x_mm, track.end_y_mm)]:
            if (
                x < edge_margin
                or y < edge_margin
                or x > board.width_mm - edge_margin
                or y > board.height_mm - edge_margin
            ):
                findings.append(
                    PCBDrcFinding(
                        finding_id=f"drc_edge_{uuid.uuid4().hex[:8]}",
                        rule_code="DRC_BOARD_EDGE_CLEARANCE",
                        severity="critical",
                        title="Board-Edge Clearance Violation",
                        message=f"Copper track at ({x:.2f}, {y:.2f}) is closer than {edge_margin:.2f}mm to board edge.",
                        affected_layer=track.layer,
                        affected_net=track.net_id,
                        pos_x_mm=round(x, 2),
                        pos_y_mm=round(y, 2),
                        remediation_steps=f"Route track at least {edge_margin:.2f}mm away from board boundaries to avoid milling damage.",
                    )
                )
                break

    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        w = fp.width_mm if fp else 5.0
        h = fp.height_mm if fp else 5.0
        if (
            comp.pos_x_mm - w / 2 < edge_margin
            or comp.pos_y_mm - h / 2 < edge_margin
            or comp.pos_x_mm + w / 2 > board.width_mm - edge_margin
            or comp.pos_y_mm + h / 2 > board.height_mm - edge_margin
        ):
            findings.append(
                PCBDrcFinding(
                    finding_id=f"drc_edge_c_{uuid.uuid4().hex[:8]}",
                    rule_code="DRC_COMPONENT_BOARD_EDGE",
                    severity="warning",
                    title="Component Exceeds Safe Board Margin",
                    message=f"Component {comp.ref_des} ({comp.footprint_id}) is placed too close to board perimeter.",
                    affected_layer="Top",
                    affected_net=None,
                    pos_x_mm=round(comp.pos_x_mm, 2),
                    pos_y_mm=round(comp.pos_y_mm, 2),
                    remediation_steps="Move component inward to maintain safe clearance from routing edge.",
                )
            )

    # 4. Clearance & Short Circuit Detection (Track-to-Track on same layer)
    track_count = len(board.tracks)
    for i in range(track_count):
        t1 = board.tracks[i]
        for j in range(i + 1, track_count):
            t2 = board.tracks[j]
            # Only test if on same layer and different electrical nets
            if t1.layer != t2.layer or t1.net_id == t2.net_id:
                continue

            dist = segment_to_segment_distance(
                t1.start_x_mm, t1.start_y_mm, t1.end_x_mm, t1.end_y_mm,
                t2.start_x_mm, t2.start_y_mm, t2.end_x_mm, t2.end_y_mm,
            )
            required_clearance = rules.min_clearance_mm + (t1.width_mm + t2.width_mm) / 2.0

            if dist < 0.01:
                # Direct intersection / Short circuit
                findings.append(
                    PCBDrcFinding(
                        finding_id=f"drc_short_{uuid.uuid4().hex[:8]}",
                        rule_code="DRC_ELECTRICAL_SHORT",
                        severity="critical",
                        title="Copper Short Circuit Detected",
                        message=f"Short circuit between Net '{t1.net_id}' and Net '{t2.net_id}' on layer {t1.layer}.",
                        affected_layer=t1.layer,
                        affected_net=f"{t1.net_id} / {t2.net_id}",
                        pos_x_mm=round((t1.start_x_mm + t2.start_x_mm) / 2.0, 2),
                        pos_y_mm=round((t1.start_y_mm + t2.start_y_mm) / 2.0, 2),
                        remediation_steps="Reroute one of the tracks onto another layer using vias or separate the copper paths.",
                    )
                )
            elif dist < required_clearance:
                # Clearance violation
                findings.append(
                    PCBDrcFinding(
                        finding_id=f"drc_clear_{uuid.uuid4().hex[:8]}",
                        rule_code="DRC_COPPER_CLEARANCE",
                        severity="critical",
                        title="Copper Clearance Violation",
                        message=f"Spacing between Net '{t1.net_id}' and Net '{t2.net_id}' is {dist:.3f}mm (required {rules.min_clearance_mm:.2f}mm).",
                        affected_layer=t1.layer,
                        affected_net=f"{t1.net_id} / {t2.net_id}",
                        pos_x_mm=round((t1.start_x_mm + t2.start_x_mm) / 2.0, 2),
                        pos_y_mm=round((t1.start_y_mm + t2.start_y_mm) / 2.0, 2),
                        remediation_steps=f"Increase clearance to at least {rules.min_clearance_mm:.2f}mm to avoid solder bridging during manufacturing.",
                    )
                )

    # 5. Overlapping Components Detection
    comp_count = len(board.components)
    for i in range(comp_count):
        c1 = board.components[i]
        fp1 = get_footprint_definition(c1.footprint_id)
        w1 = (fp1.width_mm if fp1 else 4.0) / 2.0
        h1 = (fp1.height_mm if fp1 else 4.0) / 2.0

        for j in range(i + 1, comp_count):
            c2 = board.components[j]
            fp2 = get_footprint_definition(c2.footprint_id)
            w2 = (fp2.width_mm if fp2 else 4.0) / 2.0
            h2 = (fp2.height_mm if fp2 else 4.0) / 2.0

            # Only test if on same side
            if c1.side != c2.side:
                continue

            overlap_x = (w1 + w2) - abs(c1.pos_x_mm - c2.pos_x_mm)
            overlap_y = (h1 + h2) - abs(c1.pos_y_mm - c2.pos_y_mm)

            if overlap_x > 0.5 and overlap_y > 0.5:
                findings.append(
                    PCBDrcFinding(
                        finding_id=f"drc_overlap_{uuid.uuid4().hex[:8]}",
                        rule_code="DRC_COMPONENT_COLLISION",
                        severity="warning",
                        title="Component Physical Overlap",
                        message=f"Component {c1.ref_des} and {c2.ref_des} courtyards collide on the {c1.side} layer.",
                        affected_layer=c1.side,
                        affected_net=None,
                        pos_x_mm=round((c1.pos_x_mm + c2.pos_x_mm) / 2.0, 2),
                        pos_y_mm=round((c1.pos_y_mm + c2.pos_y_mm) / 2.0, 2),
                        remediation_steps=f"Separate components {c1.ref_des} and {c2.ref_des} to allow pick-and-place nozzle clearance and solder fillet formation.",
                    )
                )

    # 6. Unrouted Net Connections (Ratsnest)
    routing_stats = calculate_routing_summary(board)
    unrouted_count = routing_stats["unrouted_connections"]
    completion_pct = routing_stats["completion_percentage"]

    if unrouted_count > 0:
        findings.append(
            PCBDrcFinding(
                finding_id=f"drc_unrouted_{uuid.uuid4().hex[:8]}",
                rule_code="DRC_UNROUTED_NETS",
                severity="warning",
                title=f"Incomplete Routing ({unrouted_count} Flylines Remaining)",
                message=f"Board has {unrouted_count} unrouted connection(s). Overall routing completion: {completion_pct:.1f}%.",
                affected_layer="All",
                affected_net=None,
                pos_x_mm=None,
                pos_y_mm=None,
                remediation_steps="Complete routing of all active net flylines before submitting for fabrication.",
            )
        )

    # 7. High-Current / Thermal Trace Width Review
    power_net_names = {"vcc", "+5v", "+3v3", "3v3", "+12v", "12v", "pwr", "power", "vbat", "bat"}
    for track in board.tracks:
        net_lower = track.net_id.lower()
        if any(p in net_lower for p in power_net_names):
            if track.width_mm < 0.50:
                findings.append(
                    PCBDrcFinding(
                        finding_id=f"drc_pwr_{uuid.uuid4().hex[:8]}",
                        rule_code="DRC_POWER_TRACE_WIDTH_ADVISORY",
                        severity="info",
                        title="Power Trace Sizing Recommendation",
                        message=f"Power rail trace '{track.net_id}' has width {track.width_mm:.2f}mm. For currents >1A, standard IPC guidelines recommend >= 0.50mm - 0.80mm.",
                        affected_layer=track.layer,
                        affected_net=track.net_id,
                        pos_x_mm=round(track.start_x_mm, 2),
                        pos_y_mm=round(track.start_y_mm, 2),
                        remediation_steps="Use the IPC-2152 trace width calculator to size high-current power traces properly.",
                    )
                )

    critical_count = sum(1 for f in findings if f.severity == "critical")
    warning_count = sum(1 for f in findings if f.severity == "warning")
    passed = critical_count == 0

    return PCBDrcReport(
        total_findings=len(findings),
        critical_count=critical_count,
        warning_count=warning_count,
        passed=passed,
        findings=findings,
        routing_completion_pct=completion_pct,
        unrouted_nets_count=unrouted_count,
    )
