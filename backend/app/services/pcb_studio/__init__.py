from __future__ import annotations

from app.services.pcb_studio.footprints import (
    FOOTPRINT_LIBRARY,
    get_footprint_definition,
    map_schematic_footprint_alias,
    list_available_footprints,
)
from app.services.pcb_studio.conversion import convert_schematic_to_pcb
from app.services.pcb_studio.routing import (
    calculate_ratsnest,
    calculate_routing_summary,
    assisted_route_path,
    get_pad_absolute_position,
)
from app.services.pcb_studio.drc import run_design_rule_check
from app.services.pcb_studio.constraints import (
    calculate_trace_width,
    calculate_microstrip_impedance,
)
from app.services.pcb_studio.bom_cost import (
    extract_pcb_bom,
    estimate_prototype_cost,
)
from app.services.pcb_studio.export import export_pcb_package
from app.services.pcb_studio.engine import PCBStudioEngine, get_pcb_engine

__all__ = [
    "FOOTPRINT_LIBRARY",
    "get_footprint_definition",
    "map_schematic_footprint_alias",
    "list_available_footprints",
    "convert_schematic_to_pcb",
    "calculate_ratsnest",
    "calculate_routing_summary",
    "assisted_route_path",
    "get_pad_absolute_position",
    "run_design_rule_check",
    "calculate_trace_width",
    "calculate_microstrip_impedance",
    "extract_pcb_bom",
    "estimate_prototype_cost",
    "export_pcb_package",
    "PCBStudioEngine",
    "get_pcb_engine",
]
