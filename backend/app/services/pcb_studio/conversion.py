from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional, Tuple, Any

from app.models.schemas import (
    SchematicSheet,
    SchematicProject,
    SchematicComponentDef,
    PCBBoard,
    PCBComponent,
    PCBNet,
    PCBNetPadConnection,
    PCBDesignRules,
    SchematicToPCBResponse,
)
from app.services.pcb_studio.footprints import (
    FOOTPRINT_LIBRARY,
    map_schematic_footprint_alias,
    get_footprint_definition,
)
from app.services.schematic_studio.catalog import build_standard_component_catalog


def convert_schematic_to_pcb(
    sheet: SchematicSheet,
    board_width_mm: float = 100.0,
    board_height_mm: float = 80.0,
    layer_count: int = 2,
    custom_footprint_overrides: Optional[Dict[str, str]] = None,
    board_title: str = "Converted Board",
) -> SchematicToPCBResponse:
    """
    Converts a validated SchematicSheet and its netlist into a PCB project layout.
    
    Adheres strictly to the rule:
    - Never silently substitute an unknown or unmapped footprint.
    - Preserves component references (ref_des), values, and electrical nets.
    - Positions components on a neat grid within board margins.
    """
    overrides = custom_footprint_overrides or {}
    standard_catalog = build_standard_component_catalog()

    mapped_components: List[PCBComponent] = []
    unmapped_components: List[Dict[str, str]] = []
    conversion_notes: List[str] = []
    warnings: List[str] = []

    # Margin and grid placement setup
    margin_mm = 10.0
    usable_width = max(20.0, board_width_mm - 2 * margin_mm)
    usable_height = max(20.0, board_height_mm - 2 * margin_mm)

    curr_x = margin_mm + 5.0
    curr_y = margin_mm + 8.0
    row_height_max = 12.0

    # 1. Process each component instance
    for comp in sheet.components:
        target_footprint_key: Optional[str] = None
        ref_des = comp.ref_des
        val = comp.value

        # Check explicit override first
        if ref_des in overrides:
            target_footprint_key = overrides[ref_des]
        elif comp.component_id in overrides:
            target_footprint_key = overrides[comp.component_id]
        else:
            # Check if component definition provides a footprint
            comp_def: Optional[SchematicComponentDef] = standard_catalog.get(comp.component_id)
            if comp_def and comp_def.footprint:
                target_footprint_key = comp_def.footprint
            elif comp.attributes and comp.attributes.get("footprint"):
                target_footprint_key = str(comp.attributes["footprint"])

        # Map alias if available
        resolved_fp_id: Optional[str] = None
        if target_footprint_key:
            resolved_fp_id = map_schematic_footprint_alias(target_footprint_key)
            if not resolved_fp_id and target_footprint_key in FOOTPRINT_LIBRARY:
                resolved_fp_id = target_footprint_key

        # Strict check: Never silently substitute
        if not resolved_fp_id or resolved_fp_id not in FOOTPRINT_LIBRARY:
            unmapped_components.append({
                "instance_id": comp.instance_id,
                "ref_des": ref_des,
                "value": val,
                "component_id": comp.component_id,
                "requested_footprint": str(target_footprint_key or "unspecified"),
                "reason": f"Footprint '{target_footprint_key}' not found in standard footprint library and no valid override provided. Must not silently substitute.",
            })
            warnings.append(
                f"Component {ref_des} ({val}) has unmapped footprint '{target_footprint_key}'. Excluded from automatic placement until mapped."
            )
            continue

        fp_def = FOOTPRINT_LIBRARY[resolved_fp_id]
        comp_w = fp_def.width_mm + 6.0
        comp_h = fp_def.height_mm + 6.0

        # Auto-placement grid check
        if curr_x + comp_w > margin_mm + usable_width:
            curr_x = margin_mm + 5.0
            curr_y += row_height_max + 6.0
            row_height_max = 12.0

        row_height_max = max(row_height_max, comp_h)

        placed_comp = PCBComponent(
            component_instance_id=comp.instance_id,
            ref_des=ref_des,
            value=val,
            footprint_id=resolved_fp_id,
            pos_x_mm=round(curr_x + comp_w / 2.0, 2),
            pos_y_mm=round(curr_y + comp_h / 2.0, 2),
            rotation_deg=0.0,
            side="top",
            attributes={
                "schematic_component_id": comp.component_id,
                "tolerance": comp.tolerance,
                "package_name": fp_def.name,
                "category": fp_def.category,
            },
        )
        mapped_components.append(placed_comp)
        curr_x += comp_w + 3.0

    # 2. Map electrical nets
    pcb_nets: List[PCBNet] = []
    valid_instance_ids = {c.component_instance_id for c in mapped_components}

    for s_net in sheet.nets:
        net_pads: List[PCBNetPadConnection] = []
        for conn in s_net.connections:
            if conn.instance_id in valid_instance_ids:
                net_pads.append(
                    PCBNetPadConnection(
                        component_instance_id=conn.instance_id,
                        pad_number=str(conn.pin_id),
                    )
                )

        pcb_net = PCBNet(
            net_id=s_net.net_id,
            name=s_net.name,
            color=s_net.color or ("#ef4444" if s_net.is_power else "#10b981" if s_net.is_ground else "#06b6d4"),
            is_power=s_net.is_power,
            is_ground=s_net.is_ground,
            voltage_level_v=s_net.voltage_level_v,
            connections=net_pads,
        )
        pcb_nets.append(pcb_net)

    conversion_notes.append(
        f"Successfully converted schematic with {len(mapped_components)} components placed and {len(pcb_nets)} nets preserved."
    )
    if unmapped_components:
        conversion_notes.append(
            f"Flagged {len(unmapped_components)} components with missing or unverified footprints."
        )

    board = PCBBoard(
        board_id=f"brd_{uuid.uuid4().hex[:10]}",
        title=board_title,
        width_mm=float(board_width_mm),
        height_mm=float(board_height_mm),
        layer_count=int(layer_count),
        components=mapped_components,
        tracks=[],
        vias=[],
        zones=[],
        nets=pcb_nets,
        design_rules=PCBDesignRules(
            min_trace_width_mm=0.25,
            min_clearance_mm=0.20,
            min_board_edge_clearance_mm=0.50,
            min_drill_diameter_mm=0.30,
            default_via_diameter_mm=0.60,
            layer_count=int(layer_count),
        ),
    )

    return SchematicToPCBResponse(
        board=board,
        mapped_count=len(mapped_components),
        unmapped_components=unmapped_components,
        conversion_notes=conversion_notes,
        warnings=warnings,
    )
