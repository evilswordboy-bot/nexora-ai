from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Any

from app.models.schemas import (
    PCBBoard,
    PCBComponent,
    PCBTrack,
    PCBNet,
    PCBRatsnestLine,
)
from app.services.pcb_studio.footprints import FOOTPRINT_LIBRARY, get_footprint_definition


def get_pad_absolute_position(
    component: PCBComponent,
    pad_number: str,
) -> Optional[Tuple[float, float]]:
    """Calculates the absolute board coordinates (x_mm, y_mm) for a component pad."""
    fp = get_footprint_definition(component.footprint_id)
    if not fp:
        return (component.pos_x_mm, component.pos_y_mm)

    pad_def = next((p for p in fp.pads if str(p.pad_number) == str(pad_number)), None)
    if not pad_def:
        # Fallback to component origin if pad not explicitly numbered
        return (component.pos_x_mm, component.pos_y_mm)

    rad = math.radians(component.rotation_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Rotate relative coordinates and offset by component position
    abs_x = component.pos_x_mm + (pad_def.rel_x_mm * cos_a - pad_def.rel_y_mm * sin_a)
    abs_y = component.pos_y_mm + (pad_def.rel_x_mm * sin_a + pad_def.rel_y_mm * cos_a)

    return (round(abs_x, 3), round(abs_y, 3))


def is_connection_routed(
    pos_a: Tuple[float, float],
    pos_b: Tuple[float, float],
    tracks: List[PCBTrack],
    net_id: str,
    snap_radius_mm: float = 0.75,
) -> bool:
    """
    Checks if an electrical track path exists between two pad locations for a net.
    Considers direct segments or track endpoints touching the pad vicinities.
    """
    net_tracks = [t for t in tracks if t.net_id == net_id]
    if not net_tracks:
        return False

    # Check direct single track
    for t in net_tracks:
        dist_start_a = math.hypot(t.start_x_mm - pos_a[0], t.start_y_mm - pos_a[1])
        dist_end_b = math.hypot(t.end_x_mm - pos_b[0], t.end_y_mm - pos_b[1])
        if dist_start_a <= snap_radius_mm and dist_end_b <= snap_radius_mm:
            return True

        dist_start_b = math.hypot(t.start_x_mm - pos_b[0], t.start_y_mm - pos_b[1])
        dist_end_a = math.hypot(t.end_x_mm - pos_a[0], t.end_y_mm - pos_a[1])
        if dist_start_b <= snap_radius_mm and dist_end_a <= snap_radius_mm:
            return True

    # Check if both endpoints touch ANY connected tracks in net
    touches_a = any(
        math.hypot(t.start_x_mm - pos_a[0], t.start_y_mm - pos_a[1]) <= snap_radius_mm
        or math.hypot(t.end_x_mm - pos_a[0], t.end_y_mm - pos_a[1]) <= snap_radius_mm
        for t in net_tracks
    )
    touches_b = any(
        math.hypot(t.start_x_mm - pos_b[0], t.start_y_mm - pos_b[1]) <= snap_radius_mm
        or math.hypot(t.end_x_mm - pos_b[0], t.end_y_mm - pos_b[1]) <= snap_radius_mm
        for t in net_tracks
    )

    return touches_a and touches_b


def calculate_ratsnest(board: PCBBoard) -> List[PCBRatsnestLine]:
    """
    Computes unrouted flylines (ratsnest) between connected pads for all nets.
    Uses Euclidean Minimum Spanning Tree (MST) per net to minimize total wirelength.
    """
    comp_map = {c.component_instance_id: c for c in board.components}
    ratsnest: List[PCBRatsnestLine] = []

    for net in board.nets:
        if len(net.connections) < 2:
            continue

        pad_nodes: List[Dict[str, Any]] = []
        for conn in net.connections:
            comp = comp_map.get(conn.component_instance_id)
            if not comp:
                continue
            pos = get_pad_absolute_position(comp, conn.pad_number)
            if pos:
                pad_nodes.append({
                    "ref": f"{comp.ref_des}.{conn.pad_number}",
                    "pos": pos,
                    "comp_id": comp.component_instance_id,
                })

        if len(pad_nodes) < 2:
            continue

        # Build Minimum Spanning Tree for the net's pads
        n = len(pad_nodes)
        visited = [False] * n
        visited[0] = True
        edges_added = 0

        while edges_added < n - 1:
            best_dist = float("inf")
            best_pair = (-1, -1)

            for i in range(n):
                if not visited[i]:
                    continue
                pos_i = pad_nodes[i]["pos"]
                for j in range(n):
                    if visited[j]:
                        continue
                    pos_j = pad_nodes[j]["pos"]
                    dist = math.hypot(pos_i[0] - pos_j[0], pos_i[1] - pos_j[1])
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (i, j)

            if best_pair[0] == -1 or best_pair[1] == -1:
                break

            idx_a, idx_b = best_pair
            visited[idx_b] = True
            edges_added += 1

            pos_a = pad_nodes[idx_a]["pos"]
            pos_b = pad_nodes[idx_b]["pos"]

            # Check if this edge is already routed by existing tracks
            routed = is_connection_routed(pos_a, pos_b, board.tracks, net.net_id)
            if not routed:
                ratsnest.append(
                    PCBRatsnestLine(
                        net_id=net.net_id,
                        start_x=round(pos_a[0], 2),
                        start_y=round(pos_a[1], 2),
                        end_x=round(pos_b[0], 2),
                        end_y=round(pos_b[1], 2),
                        start_ref=pad_nodes[idx_a]["ref"],
                        end_ref=pad_nodes[idx_b]["ref"],
                    )
                )

    return ratsnest


def calculate_routing_summary(board: PCBBoard) -> Dict[str, Any]:
    """Computes total connections, unrouted count, and completion percentage."""
    ratsnest = calculate_ratsnest(board)
    total_connections = 0
    for net in board.nets:
        if len(net.connections) >= 2:
            total_connections += len(net.connections) - 1

    unrouted_count = len(ratsnest)
    routed_count = max(0, total_connections - unrouted_count)
    completion_pct = 100.0 if total_connections == 0 else round((routed_count / total_connections) * 100.0, 1)

    return {
        "total_connections": total_connections,
        "routed_connections": routed_count,
        "unrouted_connections": unrouted_count,
        "completion_percentage": completion_pct,
        "ratsnest": ratsnest,
    }


def assisted_route_path(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    mode: str = "45_degree",
) -> List[Tuple[float, float]]:
    """
    Computes assisted professional trace routing waypoints (45-degree or 90-degree orthogonal).
    Returns list of vertices: [start, midpoint(s), end].
    """
    dx = end_x - start_x
    dy = end_y - start_y

    if abs(dx) < 0.01 and abs(dy) < 0.01:
        return [(start_x, start_y)]

    if mode == "direct":
        return [(round(start_x, 3), round(start_y, 3)), (round(end_x, 3), round(end_y, 3))]

    if mode == "orthogonal":
        # Straight 90-degree dogleg
        mid_x = end_x
        mid_y = start_y
        return [
            (round(start_x, 3), round(start_y, 3)),
            (round(mid_x, 3), round(mid_y, 3)),
            (round(end_x, 3), round(end_y, 3)),
        ]

    # Standard 45-degree chamfered routing
    min_delta = min(abs(dx), abs(dy))
    dir_x = 1.0 if dx >= 0 else -1.0
    dir_y = 1.0 if dy >= 0 else -1.0

    if abs(dx) >= abs(dy):
        # Move diagonally by dy first, then straight along x
        mid1_x = start_x + (min_delta * dir_x)
        mid1_y = end_y
        return [
            (round(start_x, 3), round(start_y, 3)),
            (round(mid1_x, 3), round(mid1_y, 3)),
            (round(end_x, 3), round(end_y, 3)),
        ]
    else:
        # Move diagonally by dx first, then straight along y
        mid1_x = end_x
        mid1_y = start_y + (min_delta * dir_y)
        return [
            (round(start_x, 3), round(start_y, 3)),
            (round(mid1_x, 3), round(mid1_y, 3)),
            (round(end_x, 3), round(end_y, 3)),
        ]
