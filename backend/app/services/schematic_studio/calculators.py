from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Tuple, Any

from app.models.schemas import (
    OhmsLawRequest,
    OhmsLawResult,
    VoltageDividerRequest,
    VoltageDividerResult,
    ResistorPairRecommendation,
    LEDResistorRequest,
    LEDResistorResult,
    RCTimeConstantRequest,
    RCTimeConstantResult,
    TransistorBiasRequest,
    TransistorBiasResult,
    PowerThermalRequest,
    PowerThermalResult,
    LogicExpressionRequest,
    LogicExpressionResult,
)

E12_BASE = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24_BASE = [
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1
]


def find_nearest_standard_resistor(val: float, series: str = "E24", round_up: bool = False) -> float:
    """Finds the nearest standard decade resistor value in E12 or E24 series."""
    if val <= 0:
        return 1.0
    decade = 10 ** math.floor(math.log10(val))
    norm = val / decade
    table = E24_BASE if series == "E24" else E12_BASE

    if round_up:
        candidates = [c for c in table if c >= norm - 1e-6]
        if candidates:
            return round(candidates[0] * decade, 2)
        return round(table[0] * (decade * 10), 2)

    best = min(table, key=lambda c: abs(c - norm))
    return round(best * decade, 2)


def calculate_ohms_law(req: OhmsLawRequest) -> OhmsLawResult:
    """Calculates V, I, R, and P from any 2 known parameters."""
    v = req.voltage_v
    i = req.current_a
    r = req.resistance_ohms
    p = req.power_w

    formulas: List[str] = []

    # Solve for V, I, R, P
    if v is not None and i is not None:
        if i == 0:
            raise ValueError("Current cannot be zero when calculating resistance.")
        r = v / i
        p = v * i
        formulas.extend(["R = V / I", "P = V * I"])
    elif v is not None and r is not None:
        if r <= 0:
            raise ValueError("Resistance must be greater than zero.")
        i = v / r
        p = (v ** 2) / r
        formulas.extend(["I = V / R", "P = V^2 / R"])
    elif v is not None and p is not None:
        if v == 0:
            raise ValueError("Voltage cannot be zero when calculating current from power.")
        i = p / v
        r = (v ** 2) / p
        formulas.extend(["I = P / V", "R = V^2 / P"])
    elif i is not None and r is not None:
        v = i * r
        p = (i ** 2) * r
        formulas.extend(["V = I * R", "P = I^2 * R"])
    elif i is not None and p is not None:
        if i == 0:
            raise ValueError("Current cannot be zero when calculating voltage from power.")
        v = p / i
        r = p / (i ** 2)
        formulas.extend(["V = P / I", "R = P / I^2"])
    elif r is not None and p is not None:
        if r <= 0 or p < 0:
            raise ValueError("Resistance must be positive and power non-negative.")
        v = math.sqrt(p * r)
        i = math.sqrt(p / r)
        formulas.extend(["V = sqrt(P * R)", "I = sqrt(P / R)"])
    else:
        raise ValueError("Must provide at least 2 distinct parameters out of (voltage, current, resistance, power).")

    # Wattage recommendation
    if p <= 0.10:
        recommended_wattage = "0.125W (1/8W SMD 0805 or THT)"
    elif p <= 0.20:
        recommended_wattage = "0.25W (1/4W standard axial or 1206 SMD)"
    elif p <= 0.40:
        recommended_wattage = "0.5W (1/2W power resistor)"
    elif p <= 0.80:
        recommended_wattage = "1.0W (1W metal oxide or wirewound)"
    elif p <= 1.6:
        recommended_wattage = "2.0W (2W wirewound power resistor)"
    else:
        recommended_wattage = f"{math.ceil(p * 2)}W (High-power chassis or aluminum-housed resistor)"

    thermal_advisory = (
        f"Continuous power dissipation is {p*1000:.1f} mW. "
        "Standard practice recommends derating resistors to 50% rated power for reliability and low thermal drift."
    )

    return OhmsLawResult(
        voltage_v=round(v, 4),
        current_a=round(i, 6),
        resistance_ohms=round(r, 4),
        power_w=round(p, 6),
        recommended_wattage_rating=recommended_wattage,
        thermal_derating_advisory=thermal_advisory,
        formulas_used=formulas,
    )


def calculate_voltage_divider(req: VoltageDividerRequest) -> VoltageDividerResult:
    """Calculates voltage divider output, output impedance, loading effects, and standard resistor pairs."""
    vin = req.vin_v
    r1 = req.r1_ohms
    r2 = req.r2_ohms
    target_vout = req.target_vout_v
    rl = req.load_resistance_ohms

    formulas = ["Vout = Vin * (R2 / (R1 + R2))", "Zout = (R1 * R2) / (R1 + R2)"]
    recommended_pairs: List[ResistorPairRecommendation] = []

    if target_vout is not None and (r1 is None or r2 is None):
        if target_vout >= vin or target_vout <= 0:
            raise ValueError("Target Vout must be strictly between 0 and Vin.")
        ratio = target_vout / vin
        # Search E24 series for best pairs with total resistance between 5k and 100k
        candidates = []
        for base_r2 in [1e3, 2.2e3, 3.3e3, 4.7e3, 10e3, 22e3, 33e3, 47e3, 100e3]:
            needed_r1 = base_r2 * (1.0 - ratio) / ratio
            std_r1 = find_nearest_standard_resistor(needed_r1, "E24")
            calc_vout = vin * (base_r2 / (std_r1 + base_r2))
            err = abs(calc_vout - target_vout) / target_vout * 100.0
            candidates.append((err, std_r1, base_r2, calc_vout))

        candidates.sort(key=lambda x: x[0])
        best = candidates[0]
        r1 = best[1]
        r2 = best[2]

        for c in candidates[:3]:
            recommended_pairs.append(
                ResistorPairRecommendation(
                    r1_ohms=c[1],
                    r2_ohms=c[2],
                    actual_vout_v=round(c[3], 4),
                    error_pct=round(c[0], 2),
                    series="E24",
                )
            )

    if r1 is None or r2 is None:
        raise ValueError("Must provide either (R1 and R2) or (target_vout_v).")

    ideal_vout = vin * (r2 / (r1 + r2))
    quiescent_i_ma = (vin / (r1 + r2)) * 1000.0
    z_out = (r1 * r2) / (r1 + r2)
    p_r1_mw = ((vin - ideal_vout) ** 2 / r1) * 1000.0
    p_r2_mw = (ideal_vout ** 2 / r2) * 1000.0

    loaded_vout = None
    loading_err_pct = None
    if rl is not None and rl > 0:
        r2_parallel_rl = (r2 * rl) / (r2 + rl)
        loaded_vout = vin * (r2_parallel_rl / (r1 + r2_parallel_rl))
        loading_err_pct = abs(ideal_vout - loaded_vout) / ideal_vout * 100.0
        formulas.append("Vloaded = Vin * ((R2 // RL) / (R1 + (R2 // RL)))")

    return VoltageDividerResult(
        vin_v=round(vin, 4),
        r1_ohms=round(r1, 2),
        r2_ohms=round(r2, 2),
        ideal_vout_v=round(ideal_vout, 4),
        loaded_vout_v=round(loaded_vout, 4) if loaded_vout is not None else None,
        loading_effect_error_pct=round(loading_err_pct, 2) if loading_err_pct is not None else None,
        quiescent_current_ma=round(quiescent_i_ma, 4),
        output_impedance_ohms=round(z_out, 2),
        r1_power_mw=round(p_r1_mw, 2),
        r2_power_mw=round(p_r2_mw, 2),
        recommended_pairs=recommended_pairs,
        formulas_used=formulas,
    )


def calculate_led_resistor(req: LEDResistorRequest) -> LEDResistorResult:
    """Calculates current-limiting resistor for LEDs with E12 and E24 standard selection."""
    vs = req.supply_voltage_v
    vf = req.led_forward_voltage_v
    target_ma = req.led_current_ma

    if vs <= vf:
        raise ValueError(f"Supply voltage ({vs}V) must be greater than LED forward voltage ({vf}V).")
    if target_ma <= 0:
        raise ValueError("Target LED current must be greater than 0 mA.")

    target_a = target_ma / 1000.0
    v_drop = vs - vf
    calc_r = v_drop / target_a

    # Standard values (round up to prevent overcurrent)
    std_e12 = find_nearest_standard_resistor(calc_r, "E12", round_up=True)
    std_e24 = find_nearest_standard_resistor(calc_r, "E24", round_up=True)

    actual_i_e24_ma = (v_drop / std_e24) * 1000.0
    p_resistor_mw = (actual_i_e24_ma / 1000.0) ** 2 * std_e24 * 1000.0

    if p_resistor_mw <= 100.0:
        rec_power = "0.125W (1/8W SMD 0805)"
    elif p_resistor_mw <= 200.0:
        rec_power = "0.25W (1/4W standard axial / 1206 SMD)"
    else:
        rec_power = "0.5W (1/2W metal film)"

    safety_margin = ((target_ma - actual_i_e24_ma) / target_ma) * 100.0

    return LEDResistorResult(
        supply_voltage_v=round(vs, 2),
        led_forward_voltage_v=round(vf, 2),
        target_current_ma=round(target_ma, 2),
        calculated_resistance_ohms=round(calc_r, 2),
        standard_e12_resistor_ohms=std_e12,
        standard_e24_resistor_ohms=std_e24,
        actual_current_with_e24_ma=round(actual_i_e24_ma, 2),
        resistor_power_dissipation_mw=round(p_resistor_mw, 2),
        recommended_resistor_power_rating=rec_power,
        safety_margin_pct=round(safety_margin, 1),
        formulas_used=[
            "R = (Vsupply - Vf) / Iled",
            "P_R = I^2 * R",
            "I_actual = (Vsupply - Vf) / R_standard",
        ],
    )


def calculate_rc_time_constant(req: RCTimeConstantRequest) -> RCTimeConstantResult:
    """Calculates RC time constant, cutoff frequency, rise time, and charge response."""
    r = req.resistance_ohms
    c = req.capacitance_farads
    vstep = req.step_voltage_v

    if r <= 0 or c <= 0:
        raise ValueError("Resistance and Capacitance must both be positive non-zero values.")

    tau = r * c
    fc = 1.0 / (2.0 * math.pi * tau)
    tr = 2.197 * tau  # 10% to 90% rise time = ln(9) * tau
    t_95 = 3.0 * tau
    t_99 = 4.6 * tau  # ln(100) * tau

    # Format human readable
    if tau < 1e-6:
        tau_fmt = f"{tau*1e9:.2f} ns"
    elif tau < 1e-3:
        tau_fmt = f"{tau*1e6:.2f} us"
    elif tau < 1.0:
        tau_fmt = f"{tau*1e3:.2f} ms"
    else:
        tau_fmt = f"{tau:.3f} s"

    if fc < 1e3:
        fc_fmt = f"{fc:.2f} Hz"
    elif fc < 1e6:
        fc_fmt = f"{fc/1e3:.2f} kHz"
    else:
        fc_fmt = f"{fc/1e6:.2f} MHz"

    # Generate 11 sample points from t=0 to t=5*tau
    curve_points = []
    for step in range(11):
        t_sample = (step / 2.0) * tau  # 0, 0.5 tau, 1.0 tau, ... 5.0 tau
        v_sample = vstep * (1.0 - math.exp(-t_sample / tau)) if tau > 0 else vstep
        curve_points.append({
            "t_seconds": round(t_sample, 8),
            "t_normalized": round(step * 0.5, 1),
            "voltage_v": round(v_sample, 4),
            "percentage": round((v_sample / vstep) * 100.0, 1),
        })

    return RCTimeConstantResult(
        resistance_ohms=r,
        capacitance_farads=c,
        tau_seconds=round(tau, 8),
        tau_formatted=tau_fmt,
        cutoff_frequency_hz=round(fc, 2),
        cutoff_frequency_formatted=fc_fmt,
        rise_time_10_90_seconds=round(tr, 8),
        time_to_95_pct_seconds=round(t_95, 8),
        time_to_99_pct_seconds=round(t_99, 8),
        charge_curve_points=curve_points,
        formulas_used=[
            "tau = R * C",
            "fc = 1 / (2 * pi * R * C)",
            "V(t) = Vstep * (1 - e^(-t / tau))",
            "t_rise(10-90%) = 2.2 * R * C",
        ],
    )


def calculate_transistor_bias(req: TransistorBiasRequest) -> TransistorBiasResult:
    """Calculates BJT base resistor for deep saturation switching or load driver."""
    vcc = req.supply_vcc_v
    vin = req.input_base_voltage_v
    ic_ma = req.collector_load_current_ma
    vbe = req.vbe_sat_v
    vce = req.vce_sat_v
    forced_beta = req.forced_beta_saturation

    if vin <= vbe:
        raise ValueError(f"Input base voltage ({vin}V) must exceed Vbe saturation ({vbe}V).")
    if ic_ma <= 0:
        raise ValueError("Collector current must be greater than zero.")

    # Base current for forced saturation
    ib_ma = ic_ma / forced_beta
    v_base_resistor = vin - vbe
    rb_ohms = (v_base_resistor / (ib_ma / 1000.0))

    std_rb = find_nearest_standard_resistor(rb_ohms, "E24")
    actual_ib_ma = (v_base_resistor / std_rb) * 1000.0

    p_transistor_mw = (vce * (ic_ma / 1000.0) + vbe * (actual_ib_ma / 1000.0)) * 1000.0
    p_rb_mw = ((v_base_resistor ** 2) / std_rb) * 1000.0

    notes = [
        f"Forced beta of {forced_beta:.0f} ensures guaranteed saturation over component temperature variations.",
        f"Standard base resistor: {std_rb:.0f} ohms (delivers {actual_ib_ma:.2f} mA base drive).",
        "An inductive load (e.g. relay coil or DC motor) MUST include a reverse-biased flyback diode across the load.",
    ]

    return TransistorBiasResult(
        transistor_type=req.transistor_type,
        required_base_current_ma=round(ib_ma, 3),
        base_resistor_ohms=round(rb_ohms, 2),
        standard_e24_base_resistor_ohms=std_rb,
        actual_base_current_ma=round(actual_ib_ma, 3),
        collector_current_ma=round(ic_ma, 2),
        transistor_power_dissipation_mw=round(p_transistor_mw, 2),
        base_resistor_power_mw=round(p_rb_mw, 2),
        saturation_confirmed=actual_ib_ma >= ib_ma * 0.95,
        flyback_diode_required=True,
        notes_and_tradeoffs=notes,
        formulas_used=[
            "Ib_sat = Ic / forced_beta",
            "Rb = (Vin - Vbe_sat) / Ib_sat",
            "P_q = (Vce_sat * Ic) + (Vbe_sat * Ib)",
        ],
    )


def calculate_power_thermal(req: PowerThermalRequest) -> PowerThermalResult:
    """Calculates linear regulator or power transistor thermal dissipation and heatsink requirements."""
    vin = req.input_voltage_v
    vout = req.output_voltage_v
    i_load_a = req.load_current_ma / 1000.0
    i_q_a = req.quiescent_current_ma / 1000.0
    ta = req.ambient_temp_c

    if vin < vout:
        raise ValueError(f"Input voltage ({vin}V) must be greater than or equal to output voltage ({vout}V).")

    v_drop = vin - vout
    # P = (Vin - Vout) * Iload + Vin * Iq
    power_w = (v_drop * i_load_a) + (vin * i_q_a)

    # Typical Theta_ja by package type if not provided
    package_theta = {
        "TO-220": 65.0,
        "SOT-223": 62.0,
        "TO-92": 180.0,
        "DPAK": 50.0,
        "SOIC-8": 125.0,
    }
    theta_ja = req.theta_ja_c_per_w or package_theta.get(req.package_type, 65.0)

    tj = ta + (power_w * theta_ja)
    max_tj = 125.0

    heatsink_req = tj > max_tj or power_w > 1.0
    rec_heatsink_theta = None
    if heatsink_req:
        # Theta_sa = ((Tj_max - Ta) / P) - Theta_jc - Theta_cs
        # Assume Theta_jc ~ 4.0 C/W, Theta_cs ~ 1.0 C/W
        theta_margin = ((max_tj - 20.0 - ta) / power_w) - 5.0
        rec_heatsink_theta = round(max(0.5, theta_margin), 1)

    efficiency = (vout * i_load_a) / (vin * (i_load_a + i_q_a)) * 100.0 if vin > 0 else 0.0

    if tj <= 85.0:
        verdict = "safe_without_heatsink"
        advisory = f"Operating at {tj:.1f} °C junction temp. Ambient air convection is sufficient."
    elif tj <= max_tj:
        verdict = "heatsink_required"
        advisory = f"High junction temperature ({tj:.1f} °C). A small clip-on heatsink is recommended for longevity."
    else:
        verdict = "unsafe_thermal_exceeded"
        advisory = f"CRITICAL: Junction temperature ({tj:.1f} °C) exceeds 125 °C limit! Thermal shutdown will occur. Heatsink mandatory."

    return PowerThermalResult(
        power_dissipation_w=round(power_w, 4),
        theta_ja_used=round(theta_ja, 1),
        estimated_junction_temp_c=round(tj, 1),
        max_recommended_junction_temp_c=max_tj,
        heatsink_required=heatsink_req,
        recommended_heatsink_thermal_resistance_c_per_w=rec_heatsink_theta,
        efficiency_pct=round(efficiency, 1),
        thermal_verdict=verdict,
        advisory=advisory,
        formulas_used=[
            "P_diss = (Vin - Vout) * Iload + Vin * Iq",
            "Tj = Ta + (P_diss * Theta_ja)",
            "Efficiency = (Vout * Iload) / (Vin * (Iload + Iq))",
        ],
    )


def calculate_logic_expression(req: LogicExpressionRequest) -> LogicExpressionResult:
    """Evaluates Boolean logic expression and generates a truth table and canonical minterms."""
    raw_expr = req.expression.strip()

    # Normalize logic operators: AND -> &, OR -> |, NOT -> ~, XOR -> ^
    expr = raw_expr
    expr = re.sub(r"\bAND\b", "&", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b", "|", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "~", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bXOR\b", "^", expr, flags=re.IGNORECASE)

    # Detect variables if not provided
    if req.variables:
        vars_list = sorted(list(set(req.variables)))
    else:
        # Find single capital or lowercase identifier letters A, B, C, D
        found_vars = set(re.findall(r"\b[A-Za-z]\b", expr))
        vars_list = sorted(list(found_vars))

    if not vars_list:
        vars_list = ["A", "B"]

    if len(vars_list) > 4:
        raise ValueError("Maximum 4 variables supported for truth table generation.")

    num_rows = 2 ** len(vars_list)
    truth_table: List[Dict[str, Any]] = []
    sop_minterms: List[int] = []
    pos_maxterms: List[int] = []

    for i in range(num_rows):
        row_dict: Dict[str, Any] = {}
        eval_env: Dict[str, int] = {}
        for bit_idx, var_name in enumerate(vars_list):
            val = (i >> (len(vars_list) - 1 - bit_idx)) & 1
            row_dict[var_name] = val
            eval_env[var_name] = val

        # Evaluate safely using bitwise operators
        safe_eval_expr = expr
        for var_name, val in eval_env.items():
            safe_eval_expr = re.sub(rf"\b{var_name}\b", str(val), safe_eval_expr)

        try:
            # Only allowed characters: 0, 1, &, |, ~, ^, (, ), spaces
            if not re.match(r"^[\s01&|~^()]+$", safe_eval_expr):
                raise ValueError("Expression contains unsupported symbols.")
            eval_res = eval(safe_eval_expr) & 1
        except Exception:
            eval_res = 0

        row_dict["OUTPUT"] = eval_res
        row_dict["minterm_index"] = i
        truth_table.append(row_dict)

        if eval_res == 1:
            sop_minterms.append(i)
        else:
            pos_maxterms.append(i)

    return LogicExpressionResult(
        expression=raw_expr,
        normalized_expression=expr,
        variables=vars_list,
        truth_table=truth_table,
        sop_minterms=sop_minterms,
        pos_maxterms=pos_maxterms,
        is_tautology=len(sop_minterms) == num_rows,
        is_contradiction=len(sop_minterms) == 0,
    )
