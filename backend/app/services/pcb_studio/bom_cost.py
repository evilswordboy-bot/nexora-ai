from __future__ import annotations

from typing import Dict, List, Optional, Any
from collections import defaultdict
import urllib.parse

from app.models.schemas import (
    PCBBoard,
    PCBBOMItem,
    PCBCostEstimateRequest,
    PCBCostEstimateResult,
)
from app.services.pcb_studio.footprints import FOOTPRINT_LIBRARY, get_footprint_definition


def get_approx_unit_cost(footprint_id: str, value: str) -> float:
    """Estimates typical component prototype unit cost based on package and type."""
    fp_lower = footprint_id.lower()
    val_lower = value.lower()

    if "soic" in fp_lower or "dip" in fp_lower:
        return 0.65
    if "to-220" in fp_lower or "sot-223" in fp_lower:
        return 0.45
    if "to-92" in fp_lower:
        return 0.15
    if "sod-123" in fp_lower or "diode" in val_lower:
        return 0.08
    if "led" in fp_lower or "led" in val_lower:
        return 0.05
    if "radial" in fp_lower:
        return 0.20
    if "pinheader" in fp_lower:
        return 0.30
    if "mountinghole" in fp_lower:
        return 0.00
    # 0805, 0603, 1206 passives
    return 0.02


def extract_pcb_bom(board: PCBBoard) -> List[PCBBOMItem]:
    """
    Extracts an aggregated Bill of Materials (BOM) from the PCB board layout,
    grouping identical components by value and footprint.
    """
    groups: Dict[tuple, List[str]] = defaultdict(list)
    for comp in board.components:
        key = (comp.value.strip(), comp.footprint_id.strip())
        groups[key].append(comp.ref_des)

    bom_items: List[PCBBOMItem] = []
    for (value, fp_id), ref_list in sorted(groups.items(), key=lambda x: x[1][0]):
        ref_list_sorted = sorted(ref_list)
        ref_str = ", ".join(ref_list_sorted)
        qty = len(ref_list)
        unit_cost = get_approx_unit_cost(fp_id, value)
        total_cost = round(qty * unit_cost, 2)

        fp_def = get_footprint_definition(fp_id)
        pkg_name = fp_def.name if fp_def else fp_id

        # Generate DigiKey / Octopart search query link
        search_query = urllib.parse.quote(f"{value} {fp_id}")
        supplier_url = f"https://www.digikey.com/en/products/result?keywords={search_query}"

        bom_items.append(
            PCBBOMItem(
                ref_des=ref_str,
                value=value,
                package_footprint=pkg_name,
                quantity=qty,
                datasheet_url=None,
                supplier_part_id=f"PART-{fp_id.upper()}-{value.replace(' ', '')}",
                approx_unit_cost_usd=unit_cost,
                approx_total_cost_usd=total_cost,
                source_status="standard_catalog",
            )
        )

    return bom_items


def estimate_prototype_cost(
    req: PCBCostEstimateRequest,
    bom_items: Optional[List[PCBBOMItem]] = None,
) -> PCBCostEstimateResult:
    """
    Calculates transparent prototype PCB fabrication and assembly cost estimates.
    Clearly discloses all calculation formulas and pricing assumptions.
    """
    w_mm = max(10.0, req.board_width_mm)
    h_mm = max(10.0, req.board_height_mm)
    qty = max(1, req.quantity)
    layers = max(1, min(8, req.layer_count))
    finish = req.surface_finish
    lead_days = max(1, req.lead_time_days)

    area_cm2 = (w_mm * h_mm) / 100.0

    # Layer scaling multiplier
    layer_mult = 1.0 if layers <= 2 else (2.0 if layers == 4 else 3.5)

    # Base setup tooling fee
    base_tooling = 12.00 * layer_mult

    # Material cost per board: $0.035 / cm^2
    material_cost = area_cm2 * 0.035 * layer_mult * qty

    # Surface finish fee
    finish_fee = 18.00 if finish == "ENIG" else 0.00

    # Lead time rush fee
    rush_mult = 1.6 if lead_days <= 2 else (1.25 if lead_days <= 3 else 1.0)

    fab_subtotal = (base_tooling + material_cost + finish_fee) * rush_mult
    fab_cost = round(fab_subtotal, 2)
    unit_fab_cost = round(fab_cost / qty, 2)

    # Component costs from BOM
    component_cost = 0.0
    if bom_items:
        component_cost = round(sum(item.approx_total_cost_usd for item in bom_items) * qty, 2)
    else:
        component_cost = round(area_cm2 * 0.12 * qty, 2)

    total_cost = round(fab_cost + component_cost, 2)

    cost_breakdown = {
        "tooling_base_usd": round(base_tooling, 2),
        "substrate_material_usd": round(material_cost, 2),
        "surface_finish_usd": round(finish_fee, 2),
        "lead_time_expedite_factor": round(rush_mult, 2),
        "pcb_fabrication_total_usd": fab_cost,
        "estimated_components_total_usd": component_cost,
    }

    pricing_assumptions = [
        f"Standard FR-4 substrate (Tg 130-140°C), 1.6mm thickness, 1 oz copper weight.",
        f"Prototype pooling rates: Setup tooling base ${base_tooling:.2f} for {layers}-layer build.",
        f"Surface finish: {'Electroless Nickel Immersion Gold (ENIG)' if finish == 'ENIG' else 'Lead-Free Hot Air Solder Leveling (HASL)'}.",
        f"Production lead time: {lead_days} working days (multiplier {rush_mult:.2f}x).",
        "Estimates do not include regional import duties, customs taxes, or carrier freight.",
    ]

    return PCBCostEstimateResult(
        board_width_mm=round(w_mm, 2),
        board_height_mm=round(h_mm, 2),
        board_area_cm2=round(area_cm2, 2),
        layer_count=layers,
        quantity=qty,
        surface_finish=finish,
        lead_time_days=lead_days,
        estimated_pcb_fabrication_cost_usd=fab_cost,
        estimated_unit_cost_usd=unit_fab_cost,
        estimated_component_cost_usd=component_cost,
        estimated_total_prototype_cost_usd=total_cost,
        cost_breakdown=cost_breakdown,
        pricing_assumptions=pricing_assumptions,
        is_formal_quote=False,
    )
