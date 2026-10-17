from __future__ import annotations

import io
import math
import zipfile
from typing import Dict, List, Optional, Tuple, Any

from app.models.schemas import (
    PCBBoard,
    PCBTrack,
    PCBVia,
    PCBComponent,
    PCBExportResponse,
)
from app.services.pcb_studio.footprints import FOOTPRINT_LIBRARY, get_footprint_definition
from app.services.pcb_studio.routing import get_pad_absolute_position
from app.services.pcb_studio.bom_cost import extract_pcb_bom


def format_gerber_coord(val_mm: float) -> str:
    """Formats mm coordinate into standard Gerber 4.6 format (nanometers / fixed scale)."""
    val_int = int(round(val_mm * 1000000))
    return f"{val_int:010d}" if val_int >= 0 else f"-{abs(val_int):09d}"


def generate_edge_cuts_gerber(board: PCBBoard) -> str:
    """Generates RS-274X Gerber for Edge.Cuts (Board Outline)."""
    w = board.width_mm
    h = board.height_mm

    out = [
        "G04 Nexora AI PCB Studio - Board Outline (Edge.Cuts)*",
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%LPD*%",
        "%ADD10C,0.150*%",  # 0.15mm line aperture
        "D10*",
        "G01*",
        # Move to (0,0) and draw perimeter
        f"X{format_gerber_coord(0)}Y{format_gerber_coord(0)}D02*",
        f"X{format_gerber_coord(w)}Y{format_gerber_coord(0)}D01*",
        f"X{format_gerber_coord(w)}Y{format_gerber_coord(h)}D01*",
        f"X{format_gerber_coord(0)}Y{format_gerber_coord(h)}D01*",
        f"X{format_gerber_coord(0)}Y{format_gerber_coord(0)}D01*",
        "M02*",
    ]
    return "\n".join(out)


def generate_copper_layer_gerber(board: PCBBoard, layer_name: str) -> str:
    """Generates RS-274X Gerber for copper layers (F.Cu or B.Cu)."""
    is_top = layer_name.lower().startswith("f")
    side = "top" if is_top else "bottom"

    out = [
        f"G04 Nexora AI PCB Studio - Copper Layer ({layer_name})*",
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%LPD*%",
        "%ADD10C,0.250*%",   # Default 0.25mm trace aperture
        "%ADD11C,0.500*%",   # 0.50mm trace aperture
        "%ADD12C,0.600*%",   # Via annular ring aperture
        "%ADD20R,1.500X1.000*%",  # SMD pad aperture
        "%ADD21C,1.600*%",        # THT pad aperture
        "G01*",
    ]

    # 1. Flash SMD and THT pads on this layer
    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        if not fp:
            continue
        for pad in fp.pads:
            # Include pad if it's THT or on this side
            if pad.pad_type == "thru_hole" or (comp.side == side and layer_name in pad.layers):
                pos = get_pad_absolute_position(comp, pad.pad_number)
                if pos:
                    aperture = "D21" if pad.pad_type == "thru_hole" else "D20"
                    out.append(f"{aperture}*")
                    out.append(f"X{format_gerber_coord(pos[0])}Y{format_gerber_coord(pos[1])}D03*")

    # 2. Flash Vias
    out.append("D12*")
    for via in board.vias:
        out.append(f"X{format_gerber_coord(via.x_mm)}Y{format_gerber_coord(via.y_mm)}D03*")

    # 3. Draw Tracks on this layer
    for track in board.tracks:
        if track.layer == layer_name:
            aperture = "D11" if track.width_mm >= 0.4 else "D10"
            out.append(f"{aperture}*")
            out.append(f"X{format_gerber_coord(track.start_x_mm)}Y{format_gerber_coord(track.start_y_mm)}D02*")
            out.append(f"X{format_gerber_coord(track.end_x_mm)}Y{format_gerber_coord(track.end_y_mm)}D01*")

    out.append("M02*")
    return "\n".join(out)


def generate_silkscreen_gerber(board: PCBBoard, layer_name: str) -> str:
    """Generates RS-274X Gerber for Silkscreen (F.SilkS or B.SilkS)."""
    is_top = layer_name.lower().startswith("f")
    side = "top" if is_top else "bottom"

    out = [
        f"G04 Nexora AI PCB Studio - Silkscreen Layer ({layer_name})*",
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%LPD*%",
        "%ADD10C,0.150*%",  # 0.15mm silkscreen pen
        "D10*",
        "G01*",
    ]

    for comp in board.components:
        if comp.side != side:
            continue
        fp = get_footprint_definition(comp.footprint_id)
        w = (fp.width_mm if fp else 5.0) / 2.0
        h = (fp.height_mm if fp else 5.0) / 2.0
        cx = comp.pos_x_mm
        cy = comp.pos_y_mm

        # Draw component bounding outline box
        out.append(f"X{format_gerber_coord(cx - w)}Y{format_gerber_coord(cy - h)}D02*")
        out.append(f"X{format_gerber_coord(cx + w)}Y{format_gerber_coord(cy - h)}D01*")
        out.append(f"X{format_gerber_coord(cx + w)}Y{format_gerber_coord(cy + h)}D01*")
        out.append(f"X{format_gerber_coord(cx - w)}Y{format_gerber_coord(cy + h)}D01*")
        out.append(f"X{format_gerber_coord(cx - w)}Y{format_gerber_coord(cy - h)}D01*")

    out.append("M02*")
    return "\n".join(out)


def generate_solder_mask_gerber(board: PCBBoard, layer_name: str) -> str:
    """Generates RS-274X Gerber for Solder Mask (F.Mask or B.Mask)."""
    is_top = layer_name.lower().startswith("f")
    side = "top" if is_top else "bottom"

    out = [
        f"G04 Nexora AI PCB Studio - Solder Mask ({layer_name})*",
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%LPD*%",
        "%ADD20R,1.600X1.100*%",  # SMD pad mask opening (+0.1mm clearance)
        "%ADD21C,1.800*%",        # THT pad mask opening
        "G01*",
    ]

    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        if not fp:
            continue
        for pad in fp.pads:
            if pad.pad_type == "thru_hole" or comp.side == side:
                pos = get_pad_absolute_position(comp, pad.pad_number)
                if pos:
                    aperture = "D21" if pad.pad_type == "thru_hole" else "D20"
                    out.append(f"{aperture}*")
                    out.append(f"X{format_gerber_coord(pos[0])}Y{format_gerber_coord(pos[1])}D03*")

    out.append("M02*")
    return "\n".join(out)


def generate_excellon_drill(board: PCBBoard) -> str:
    """Generates industry-standard Excellon NC Drill file."""
    # Group holes by drill diameter
    drill_tools: Dict[float, List[Tuple[float, float]]] = {}

    # Via holes
    via_drill = round(board.design_rules.min_drill_diameter_mm, 2)
    drill_tools[via_drill] = [(via.x_mm, via.y_mm) for via in board.vias]

    # Component THT pads
    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        if not fp:
            continue
        for pad in fp.pads:
            if pad.pad_type == "thru_hole" and pad.drill_diameter_mm:
                d = round(pad.drill_diameter_mm, 2)
                pos = get_pad_absolute_position(comp, pad.pad_number)
                if pos:
                    if d not in drill_tools:
                        drill_tools[d] = []
                    drill_tools[d].append(pos)

    out = [
        "M48",
        "; Nexora AI PCB Studio Excellon NC Drill File",
        "; Units: Metric (mm)",
        "METRIC,LZ",
    ]

    tool_map: Dict[float, str] = {}
    tool_idx = 1
    for d in sorted(drill_tools.keys()):
        tool_code = f"T{tool_idx:02d}"
        tool_map[d] = tool_code
        out.append(f"{tool_code}C{d:.3f}")
        tool_idx += 1

    out.append("%")
    out.append("G90")
    out.append("G05")

    for d, points in sorted(drill_tools.items()):
        if not points:
            continue
        t_code = tool_map[d]
        out.append(f"{t_code}")
        for x, y in points:
            # Excellon 3.3 metric format
            x_val = int(round(x * 1000))
            y_val = int(round(y * 1000))
            out.append(f"X{x_val}Y{y_val}")

    out.append("M30")
    return "\n".join(out)


def generate_pick_and_place_csv(board: PCBBoard) -> str:
    """Generates Centroid Pick and Place CSV for SMT assembly machines."""
    out = ["Ref,Val,Package,PosX,PosY,Rot,Side"]
    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        pkg = fp.name if fp else comp.footprint_id
        val = comp.value.replace(",", " ")
        out.append(
            f"{comp.ref_des},{val},{pkg},{comp.pos_x_mm:.3f},{comp.pos_y_mm:.3f},{comp.rotation_deg:.1f},{comp.side}"
        )
    return "\n".join(out)


def generate_bom_csv(board: PCBBoard) -> str:
    """Generates Bill of Materials (BOM) CSV export."""
    items = extract_pcb_bom(board)
    out = ["RefDes,Value,Package,Quantity,ApproxUnitCostUSD,ApproxTotalCostUSD,SupplierPartID"]
    for item in items:
        out.append(
            f'"{item.ref_des}","{item.value}","{item.package_footprint}",{item.quantity},{item.approx_unit_cost_usd:.2f},{item.approx_total_cost_usd:.2f},"{item.supplier_part_id}"'
        )
    return "\n".join(out)


def generate_kicad_pcb(board: PCBBoard) -> str:
    """
    Generates native KiCad 7 / 8 PCB file format (S-expression).
    Engineers can open this directly in KiCad PCB Editor.
    """
    lines = [
        '(kicad_pcb (version 20221018) (generator "nexora_pcb_studio")',
        f'  (general (thickness {board.board_thickness_mm}))',
        '  (paper "A4")',
        '  (layers',
        '    (0 "F.Cu" signal)',
        '    (31 "B.Cu" signal)',
        '    (36 "B.SilkS" user "B.SilkS")',
        '    (37 "F.SilkS" user "F.SilkS")',
        '    (38 "B.Mask" user)',
        '    (39 "F.Mask" user)',
        '    (44 "Edge.Cuts" user)',
        '  )',
        '  (setup',
        '    (pad_to_mask_clearance 0.05)',
        '    (pcbplotparams',
        '      (layerselection 0x00010fc_ffffffff)',
        '      (plotframeref false)',
        '      (viasonmask false)',
        '      (mode 1)',
        '      (usegerberextensions true)',
        '    )',
        '  )',
    ]

    # Nets declaration
    lines.append('  (net 0 "")')
    net_id_to_num = {"": 0}
    for idx, net in enumerate(board.nets, start=1):
        net_id_to_num[net.net_id] = idx
        lines.append(f'  (net {idx} "{net.name or net.net_id}")')

    # Board boundary (Edge.Cuts)
    w = board.width_mm
    h = board.height_mm
    lines.extend([
        f'  (gr_line (start 0 0) (end {w} 0) (layer "Edge.Cuts") (width 0.15))',
        f'  (gr_line (start {w} 0) (end {w} {h}) (layer "Edge.Cuts") (width 0.15))',
        f'  (gr_line (start {w} {h}) (end 0 {h}) (layer "Edge.Cuts") (width 0.15))',
        f'  (gr_line (start 0 {h}) (end 0 0) (layer "Edge.Cuts") (width 0.15))',
    ])

    # Footprints
    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        fp_name = fp.name if fp else comp.footprint_id
        side_layer = "F.Cu" if comp.side == "top" else "B.Cu"
        lines.extend([
            f'  (footprint "{fp_name}" (layer "{side_layer}")',
            f'    (at {comp.pos_x_mm} {comp.pos_y_mm} {comp.rotation_deg})',
            f'    (fp_text reference "{comp.ref_des}" (at 0 -3) (layer "{side_layer.replace("Cu", "SilkS")}") (effects (font (size 1 1) (thickness 0.15))))',
            f'    (fp_text value "{comp.value}" (at 0 3) (layer "{side_layer.replace("Cu", "SilkS")}") (effects (font (size 1 1) (thickness 0.15))))',
        ])
        if fp:
            for pad in fp.pads:
                pad_type_str = "smd" if pad.pad_type == "smd" else "thru_hole"
                pad_shape_str = "rect" if pad.shape == "rect" else ("circle" if pad.shape == "circle" else "roundrect")
                drill_str = f" (drill {pad.drill_diameter_mm})" if pad.drill_diameter_mm else ""
                pad_layer_str = '"F.Cu" "F.Mask"' if comp.side == "top" and pad.pad_type == "smd" else ('"B.Cu" "B.Mask"' if pad.pad_type == "smd" else '"*.Cu" "*.Mask"')
                lines.append(
                    f'    (pad "{pad.pad_number}" {pad_type_str} {pad_shape_str} (at {pad.rel_x_mm} {pad.rel_y_mm}) (size {pad.width_mm} {pad.height_mm}){drill_str} (layers {pad_layer_str}))'
                )
        lines.append('  )')

    # Tracks
    for track in board.tracks:
        net_num = net_id_to_num.get(track.net_id, 0)
        lines.append(
            f'  (segment (start {track.start_x_mm} {track.start_y_mm}) (end {track.end_x_mm} {track.end_y_mm}) (width {track.width_mm}) (layer "{track.layer}") (net {net_num}))'
        )

    # Vias
    for via in board.vias:
        net_num = net_id_to_num.get(via.net_id, 0)
        lines.append(
            f'  (via (at {via.x_mm} {via.y_mm}) (size {via.diameter_mm}) (drill {via.drill_mm}) (layers "{via.start_layer}" "{via.end_layer}") (net {net_num}))'
        )

    lines.append(")")
    return "\n".join(lines)


def generate_svg_preview(board: PCBBoard) -> str:
    """Generates an aesthetic SVG 2D vector graphic of the PCB."""
    w = board.width_mm
    h = board.height_mm
    margin = 5.0
    view_w = w + (margin * 2)
    view_h = h + (margin * 2)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-margin} {-margin} {view_w} {view_h}" width="{view_w*10}px" height="{view_h*10}px" style="background:#090d16; border-radius:8px;">',
        '  <defs>',
        '    <linearGradient id="boardGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '      <stop offset="0%" stop-color="#064e3b" />',
        '      <stop offset="100%" stop-color="#022c22" />',
        '    </linearGradient>',
        '    <linearGradient id="goldPad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '      <stop offset="0%" stop-color="#fef08a" />',
        '      <stop offset="100%" stop-color="#eab308" />',
        '    </linearGradient>',
        '  </defs>',
        # PCB Substrate
        f'  <rect x="0" y="0" width="{w}" height="{h}" rx="{board.corner_radius_mm}" fill="url(#boardGrad)" stroke="#10b981" stroke-width="0.3" />',
    ]

    # Bottom copper tracks (semi-transparent blue)
    for track in board.tracks:
        if track.layer == "B.Cu":
            svg_parts.append(
                f'  <line x1="{track.start_x_mm}" y1="{track.start_y_mm}" x2="{track.end_x_mm}" y2="{track.end_y_mm}" stroke="#3b82f6" stroke-width="{track.width_mm}" stroke-linecap="round" opacity="0.6"/>'
            )

    # Top copper tracks (copper amber/cyan)
    for track in board.tracks:
        if track.layer == "F.Cu":
            svg_parts.append(
                f'  <line x1="{track.start_x_mm}" y1="{track.start_y_mm}" x2="{track.end_x_mm}" y2="{track.end_y_mm}" stroke="#06b6d4" stroke-width="{track.width_mm}" stroke-linecap="round" />'
            )

    # Vias
    for via in board.vias:
        svg_parts.append(
            f'  <circle cx="{via.x_mm}" cy="{via.y_mm}" r="{via.diameter_mm/2}" fill="url(#goldPad)" stroke="#0284c7" stroke-width="0.1"/>'
        )
        svg_parts.append(
            f'  <circle cx="{via.x_mm}" cy="{via.y_mm}" r="{via.drill_mm/2}" fill="#090d16" />'
        )

    # Components & Pads
    for comp in board.components:
        fp = get_footprint_definition(comp.footprint_id)
        if not fp:
            continue

        # Draw component silkscreen box
        half_w = fp.width_mm / 2.0
        half_h = fp.height_mm / 2.0
        svg_parts.append(
            f'  <rect x="{comp.pos_x_mm - half_w}" y="{comp.pos_y_mm - half_h}" width="{fp.width_mm}" height="{fp.height_mm}" fill="none" stroke="#f8fafc" stroke-width="0.15" stroke-dasharray="0.5,0.5" opacity="0.7"/>'
        )
        svg_parts.append(
            f'  <text x="{comp.pos_x_mm}" y="{comp.pos_y_mm - half_h - 0.5}" fill="#38bdf8" font-size="1.4" font-family="monospace" text-anchor="middle">{comp.ref_des}</text>'
        )

        for pad in fp.pads:
            pos = get_pad_absolute_position(comp, pad.pad_number)
            if not pos:
                continue
            px, py = pos
            if pad.pad_type == "thru_hole":
                svg_parts.append(
                    f'  <circle cx="{px}" cy="{py}" r="{pad.width_mm/2}" fill="url(#goldPad)" stroke="#ca8a04" stroke-width="0.1"/>'
                )
                if pad.drill_diameter_mm:
                    svg_parts.append(
                        f'  <circle cx="{px}" cy="{py}" r="{pad.drill_diameter_mm/2}" fill="#090d16" />'
                    )
            else:
                svg_parts.append(
                    f'  <rect x="{px - pad.width_mm/2}" y="{py - pad.height_mm/2}" width="{pad.width_mm}" height="{pad.height_mm}" rx="0.1" fill="url(#goldPad)" stroke="#ca8a04" stroke-width="0.1"/>'
                )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def export_pcb_package(board: PCBBoard, export_format: str) -> PCBExportResponse:
    """Exports the PCB in the requested standard engineering format."""
    board_clean_name = board.title.lower().replace(" ", "_").replace("-", "_")

    if export_format == "kicad_pcb":
        content = generate_kicad_pcb(board)
        return PCBExportResponse(
            export_format="kicad_pcb",
            filename=f"{board_clean_name}.kicad_pcb",
            mime_type="application/x-kicad-pcb",
            content=content,
        )

    if export_format == "excellon_drill":
        content = generate_excellon_drill(board)
        return PCBExportResponse(
            export_format="excellon_drill",
            filename=f"{board_clean_name}.drl",
            mime_type="text/plain",
            content=content,
        )

    if export_format == "pick_and_place_csv":
        content = generate_pick_and_place_csv(board)
        return PCBExportResponse(
            export_format="pick_and_place_csv",
            filename=f"{board_clean_name}_positions.csv",
            mime_type="text/csv",
            content=content,
        )

    if export_format == "bom_csv":
        content = generate_bom_csv(board)
        return PCBExportResponse(
            export_format="bom_csv",
            filename=f"{board_clean_name}_bom.csv",
            mime_type="text/csv",
            content=content,
        )

    if export_format == "svg_board":
        content = generate_svg_preview(board)
        return PCBExportResponse(
            export_format="svg_board",
            filename=f"{board_clean_name}_preview.svg",
            mime_type="image/svg+xml",
            content=content,
        )

    # Default / 'gerber_zip': Generate full Gerber RS-274X layer suite
    files = {
        f"{board_clean_name}_F_Cu.gtl": generate_copper_layer_gerber(board, "F.Cu"),
        f"{board_clean_name}_B_Cu.gbl": generate_copper_layer_gerber(board, "B.Cu"),
        f"{board_clean_name}_F_SilkS.gto": generate_silkscreen_gerber(board, "F.SilkS"),
        f"{board_clean_name}_B_SilkS.gbo": generate_silkscreen_gerber(board, "B.SilkS"),
        f"{board_clean_name}_F_Mask.gts": generate_solder_mask_gerber(board, "F.Mask"),
        f"{board_clean_name}_B_Mask.gbs": generate_solder_mask_gerber(board, "B.Mask"),
        f"{board_clean_name}_Edge_Cuts.gml": generate_edge_cuts_gerber(board),
        f"{board_clean_name}.drl": generate_excellon_drill(board),
        f"{board_clean_name}_positions.csv": generate_pick_and_place_csv(board),
    }

    # Package into in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, text in files.items():
            zf.writestr(fname, text)

    import base64
    zip_bytes = zip_buffer.getvalue()
    b64_content = base64.b64encode(zip_bytes).decode("ascii")

    return PCBExportResponse(
        export_format="gerber_zip",
        filename=f"{board_clean_name}_gerbers.zip",
        mime_type="application/zip",
        content=b64_content,
        files=files,
    )
