from __future__ import annotations

import math

import pandas as pd

from .models import CellSpec, PackConfig, PackElectrical


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def simulate_constant_current_discharge(
    cell: CellSpec,
    cfg: PackConfig,
    current_a: float,
    initial_soc: float = 1.0,
    dt_s: float = 1.0,
    max_time_s: float = 24 * 3600,
) -> pd.DataFrame:
    """
    Simple constant-current discharge model.

    Model:
      - SOC decreases by coulomb counting: dSOC = I * dt / (Capacity_As)
      - OCV is linear with SOC between ocv_full and ocv_empty
      - Vterm = OCV_pack - I*R_pack

    Returns:
      DataFrame with columns:
        time_s, soc, pack_ocv_v, pack_v_v, pack_i_a, pack_p_w, energy_wh_used
    """
    cell.validate()
    cfg.validate()

    if current_a <= 0:
        raise ValueError("current_a must be > 0")
    if dt_s <= 0:
        raise ValueError("dt_s must be > 0")
    if max_time_s <= 0:
        raise ValueError("max_time_s must be > 0")

    elec = PackElectrical.from_cell_and_config(cell, cfg)
    soc = _clamp(float(initial_soc), 0.0, 1.0)

    cap_as = elec.capacity_ah * 3600.0
    cutoff_pack_v = cfg.series_s * cell.cutoff_v

    t = 0.0
    e_wh_used = 0.0
    rows: list[dict[str, float]] = []

    while t <= max_time_s:
        ocv_cell = cell.ocv_empty_v + soc * (cell.ocv_full_v - cell.ocv_empty_v)
        ocv_pack = cfg.series_s * ocv_cell

        v_pack = ocv_pack - current_a * elec.internal_resistance_ohm
        p_w = v_pack * current_a
        e_wh_used += max(0.0, p_w) * (dt_s / 3600.0)

        rows.append(
            {
                "time_s": t,
                "soc": soc,
                "pack_ocv_v": ocv_pack,
                "pack_v_v": v_pack,
                "pack_i_a": current_a,
                "pack_p_w": p_w,
                "energy_wh_used": e_wh_used,
            }
        )

        # Stop conditions (pack hits cutoff or is empty)
        if v_pack <= cutoff_pack_v or soc <= 0.0 or math.isnan(v_pack):
            break

        # Advance state
        dsoc = (current_a * dt_s) / cap_as
        soc = _clamp(soc - dsoc, 0.0, 1.0)
        t += dt_s

    return pd.DataFrame(rows)

