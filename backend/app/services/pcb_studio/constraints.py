from __future__ import annotations

import math
from typing import Dict, List, Optional, Any

from app.models.schemas import (
    TraceWidthRequest,
    TraceWidthResult,
    ImpedanceRequest,
    ImpedanceResult,
)


def calculate_trace_width(req: TraceWidthRequest) -> TraceWidthResult:
    """
    Calculates minimum required PCB copper trace width according to IPC-2152 / IPC-2221.
    
    Formula:
      I = k * (delta_T ^ 0.44) * (A ^ 0.725)
      Where:
        k = 0.048 for external layers
        k = 0.024 for internal layers
        A = cross-sectional area in mils^2
        delta_T = allowable temperature rise in °C
        I = current in Amperes
    """
    current_a = max(0.01, req.current_a)
    temp_rise_c = max(1.0, req.temp_rise_c or 10.0)
    copper_oz = max(0.25, req.copper_thickness_oz or 1.0)
    layer = req.layer_type.lower()

    # IPC constant k
    k = 0.048 if layer == "external" else 0.024

    # Area in mils^2: A = (I / (k * delta_T^0.44)) ^ (1 / 0.725)
    area_sq_mils = (current_a / (k * (temp_rise_c ** 0.44))) ** (1.0 / 0.725)

    # Thickness: 1 oz copper = 1.378 mils = 0.035 mm
    thickness_mils = copper_oz * 1.378
    thickness_mm = copper_oz * 0.035

    # Trace width: W = A / thickness
    width_mils = area_sq_mils / thickness_mils
    width_mm = width_mils * 0.0254

    # Electrical parameters: Copper resistivity at 25°C = 1.72e-8 ohm*m
    # Adjust for operating temperature (ambient 25°C + temp_rise_c)
    t_operating = 25.0 + temp_rise_c
    rho_copper = 1.72e-8 * (1.0 + 0.00393 * (t_operating - 20.0))

    area_sq_m = (width_mm * 1e-3) * (thickness_mm * 1e-3)
    resistance_per_meter = rho_copper / max(area_sq_m, 1e-12)
    voltage_drop_per_meter = current_a * resistance_per_meter
    power_loss_per_meter = (current_a ** 2) * resistance_per_meter

    advisory_notes: List[str] = []
    if width_mm < 0.20:
        advisory_notes.append(
            f"Calculated width ({width_mm:.3f}mm) is smaller than standard PCB fabrication capability. Recommend minimum 0.25mm."
        )
        width_mm = max(width_mm, 0.25)
        width_mils = width_mm / 0.0254

    if current_a >= 3.0:
        advisory_notes.append(
            "For currents >= 3A, consider using polygon copper pours, 2 oz copper weight, or routing on multiple layers in parallel with stitching vias."
        )

    formula_str = (
        f"IPC-2152: A = [ I / ({k} * ΔT^0.44) ]^(1/0.725) mils²; "
        f"Width = A / ({copper_oz:.1f} oz * 1.378 mils)"
    )

    return TraceWidthResult(
        current_a=round(current_a, 3),
        temp_rise_c=round(temp_rise_c, 1),
        copper_thickness_oz=round(copper_oz, 2),
        layer_type=layer,
        min_width_mm=round(width_mm, 3),
        min_width_mils=round(width_mils, 2),
        cross_section_area_sq_mils=round(area_sq_mils, 2),
        resistance_per_meter_ohms=round(resistance_per_meter, 4),
        voltage_drop_per_meter_v=round(voltage_drop_per_meter, 4),
        power_loss_per_meter_w=round(power_loss_per_meter, 4),
        standard_documented_formula=formula_str,
        advisory_notes=advisory_notes,
    )


def calculate_microstrip_impedance(req: ImpedanceRequest) -> ImpedanceResult:
    """
    Calculates single-ended microstrip transmission line characteristic impedance Z0
    and propagation delay according to IPC-2141 standard equations.
    
    Formula:
      Z0 = (87 / sqrt(er + 1.41)) * ln( (5.98 * h) / (0.8 * w + t) )
      Where:
        w = trace width (mm)
        t = copper thickness (mm)
        h = dielectric height to reference plane (mm)
        er = relative dielectric constant of substrate (FR-4 ~ 4.2 - 4.5)
    """
    w = max(0.05, req.trace_width_mm)
    h = max(0.05, req.dielectric_height_mm or 1.6)
    copper_oz = max(0.25, req.copper_thickness_oz or 1.0)
    t = copper_oz * 0.035  # mm
    er = max(1.0, req.dielectric_constant_er or 4.5)

    # IPC-2141 microstrip impedance formula
    numerator = 5.98 * h
    denominator = 0.8 * w + t
    argument = max(1.001, numerator / max(denominator, 1e-4))
    z0 = (87.0 / math.sqrt(er + 1.41)) * math.log(argument)

    # Effective dielectric constant calculation
    ratio_h_w = h / w
    er_eff = ((er + 1.0) / 2.0) + (((er - 1.0) / 2.0) * (1.0 / math.sqrt(1.0 + 12.0 * ratio_h_w)))

    # Propagation delay Tpd in ps/mm: c = 299.792 mm/ns -> 1/c * sqrt(er_eff)
    c_mm_per_ps = 0.299792  # speed of light in mm/ps
    prop_delay_ps_per_mm = math.sqrt(er_eff) / c_mm_per_ps

    is_rf = 45.0 <= z0 <= 55.0

    if is_rf:
        advisory = f"Z0 = {z0:.1f} Ω closely matches standard 50 Ω single-ended RF / high-speed transmission line requirements."
    elif 85.0 <= z0 <= 95.0:
        advisory = f"Z0 = {z0:.1f} Ω is well suited for 90 Ω high-speed USB 2.0 differential impedance routing."
    elif z0 < 45.0:
        advisory = f"Z0 = {z0:.1f} Ω is low. Increase dielectric separation (h) or decrease trace width (w) to raise impedance."
    else:
        advisory = f"Z0 = {z0:.1f} Ω is high. Decrease dielectric thickness (h) or widen trace (w) to achieve target impedance."

    return ImpedanceResult(
        trace_width_mm=round(w, 3),
        dielectric_height_mm=round(h, 3),
        copper_thickness_oz=round(copper_oz, 2),
        dielectric_constant_er=round(er, 2),
        characteristic_impedance_ohms=round(z0, 2),
        propagation_delay_ps_per_mm=round(prop_delay_ps_per_mm, 2),
        effective_dielectric_constant=round(er_eff, 3),
        is_rf_controlled=is_rf,
        advisory=advisory,
    )
