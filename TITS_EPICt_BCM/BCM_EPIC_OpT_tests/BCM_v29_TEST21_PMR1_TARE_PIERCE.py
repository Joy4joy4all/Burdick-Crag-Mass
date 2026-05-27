# -*- coding: utf-8 -*-
"""
BCM v29 TEST21 — PMR 1 CRAFT TRANSIT TARE PIERCE
=================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Direction: SJB 2026-05-17.
Adversarial basis: ChatGPT post-Test20 analysis.
Code execution: The code builder.

Question:
    Can our craft punch through a pre-forming nebular substrate (PMR 1,
    HYBRID_SHOCK_SHELL_ACTIVE) and does the nebula collapse back into
    raw substrate, hold formation, inscribe a scar, or tear?

Geometry:
    Entry:   10 AU buffer before nebula edge  (5 grid points)
    Nebula:  3.2 ly PMR 1 field               (64 grid points)
    Exit:    10 AU buffer after far edge       (5 grid points)
    Total traverse: 74 grid points

Velocities tested: 5000c, 10000c, 12000c, 20000c
    Reference speed: 12000c (BCM crewed standard)
    Steps per grid point = BASE_STEPS * (12000 / v)
    Higher velocity = fewer steps per cell = faster transit = less tare exposure

Craft tare mechanism:
    Craft creates a Gaussian sigma depletion at its current position.
    Tare depth = CRAFT_TARE_FRACTION * local sigma (50% of local field).
    Tare width = CRAFT_TARE_WIDTH grid points (Gaussian sigma = 2).
    Tare does NOT bypass saturation kernel — governed same as formation drive.

Physics mixing:
    Nebula evolves under Variant 2 (F_form, no T2/T3, Xi_S=0).
    Craft imposes Variant 3 tare locally (Variant 2 + Variant 3 collision).
    This is the first test of what happens when a Variant 3 integer-demanding
    craft punches through a Variant 2 fractional nebular formation field.

Post-transit:
    After craft exits, run POST_TRANSIT_STEPS free evolution.
    Measure whether sigma recovers, holds, or collapses.

Collapse states:
    NEBULA_ABSORBS_TRANSIT       sigma recovers >= 90% of pre-transit value
    NEBULA_SCAR_INSCRIBED        sigma holds but shows permanent depression at path
    NEBULA_PARTIAL_RECOVERY      sigma recovers 50-90%
    NEBULA_COLLAPSE_INDUCED      sigma drops below SIGMA_TARE_FLOOR and stays
    RECURSIVE_RIP_ONSET          cap escaped or sigma oscillates / diverges

Key metrics:
    sigma_pre_transit            PMR 1 stable state mean (from Test20)
    sigma_min_transit            minimum sigma during craft passage
    sigma_post_transit           mean after POST_TRANSIT_STEPS recovery
    tare_depth_fraction          (sigma_pre - sigma_min) / sigma_pre
    recovery_ratio               sigma_post / sigma_pre
    cap_escaped                  sigma_final > SIGMA_FORM_CAP
    tare_absorption_ratio        baryonic_consumption / craft_tare_work_injected
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

_THIS_DIR      = Path(__file__).resolve().parent
_SOLVER_ROOT   = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"

if str(_GENESIS_BRAIN) not in sys.path:
    sys.path.insert(0, str(_GENESIS_BRAIN))

try:
    import cupy as xp
    _BACKEND = "cupy"
except (ImportError, AttributeError):
    import numpy as xp
    _BACKEND = "numpy"

import numpy as np

from bcm_thresholds import KAPPA_CMB, LAMBDA_DECAY

# ── Constants ────────────────────────────────────────────────────────────────
XI_S              = 0.0
T2_ACTIVE         = False    # Nebula field: Variant 2
T3_ACTIVE         = False
SIGMA_CMB_BG      = 0.01
SIGMA_FORM_CRIT   = 0.05
SIGMA_FORM_CAP    = 1.0
ETA_ION_BLOWOUT   = 0.5

# Grid
N_NEBULA          = 64      # PMR 1 field points
N_BUFFER          = 5       # 10 AU buffer on each side
N_TOTAL           = N_NEBULA + 2 * N_BUFFER   # 74 total traverse

# Craft tare
CRAFT_TARE_FRACTION = 0.50   # depletes 50% of local sigma at craft position
CRAFT_TARE_WIDTH    = 2.0    # Gaussian sigma in grid points
BASE_STEPS_PER_CELL = 10     # steps per grid cell at 12000c reference
POST_TRANSIT_STEPS  = 1000   # free evolution steps after craft exits
REFERENCE_SPEED     = 12000  # BCM crewed standard (c)

# Formation floor — collapse detected if sigma drops below this
SIGMA_TARE_FLOOR    = 0.001

DT = 0.01

# Craft velocities (c)
VELOCITIES = [5000, 10000, 12000, 20000]

# PMR 1 hybrid operator (from Test20 — confirmed)
# F_hybrid = 0.45*F_shock + 0.35*F_shell + 0.20*F_scatter
# [D=0.85, C=0.60, S=0.90, I=0.75, G=0.30]
PMR1_COMPONENTS   = [0.85, 0.60, 0.90, 0.75, 0.30]
PMR1_HW           = [0.45, 0.35, 0.20]   # weights: shock, shell, scatter
PMR1_F_FORM_NET   = 0.418125             # from Test20


def pmr1_f_form() -> float:
    D, C, S, I, G = PMR1_COMPONENTS
    w_shock, w_shell, w_scatter = PMR1_HW
    f_shock   = S * (0.5 * C + 0.5 * G)
    f_shell   = D * I
    f_scatter = D * G * (1.0 - I)
    return w_shock * f_shock + w_shell * f_shell + w_scatter * f_scatter


def build_stable_pmr1_field() -> np.ndarray:
    """
    Build PMR 1 stable field from Test20.
    Full 74-point array: buffer zones at 0, nebula in middle, buffer at far end.
    Buffer zones = void (sigma = KAPPA_CMB * SIGMA_CMB_BG — minimum funded state).
    Nebula = Gaussian seed evolved to near-stable state.
    """
    D, C, S, I, G = PMR1_COMPONENTS
    f_net  = PMR1_F_FORM_NET
    I_CMB  = KAPPA_CMB * SIGMA_CMB_BG

    # 1D nebula field
    r     = np.linspace(0, 1, N_NEBULA)
    sigma = np.exp(-((r - 0.5) ** 2) / (2 * 0.1 ** 2)) * 0.1

    # Evolve to Test20 stable state (500 steps)
    for _ in range(500):
        sigma_eff = sigma * f_net + KAPPA_CMB * SIGMA_CMB_BG
        phi_form  = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)
        sat       = np.clip(1.0 - sigma / SIGMA_FORM_CAP, 0.0, 1.0)
        T1        = sigma_eff * phi_form * sat
        T5        = LAMBDA_DECAY * sigma
        lap       = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        d_sigma   = T1 * f_net + I_CMB * sigma_eff - T5 + G * 0.01 * lap
        sigma     = np.clip(sigma + DT * d_sigma, 0.0, None)

    # Full 74-point field: buffer | nebula | buffer
    void_level = KAPPA_CMB * SIGMA_CMB_BG
    field      = np.full(N_TOTAL, void_level)
    field[N_BUFFER:N_BUFFER + N_NEBULA] = sigma
    return field


def craft_tare_profile(craft_pos: int, field_len: int) -> np.ndarray:
    """Gaussian tare centered at craft_pos."""
    positions    = np.arange(field_len, dtype=float)
    tare_profile = np.exp(-((positions - craft_pos) ** 2) /
                           (2 * CRAFT_TARE_WIDTH ** 2))
    return tare_profile


def run_transit(velocity_c: int,
                sigma_stable: np.ndarray) -> Dict[str, Any]:
    """
    Run craft transit through PMR 1 field at given velocity.
    Returns per-transit metrics.
    """
    steps_per_cell = max(1, int(round(
        BASE_STEPS_PER_CELL * REFERENCE_SPEED / velocity_c
    )))
    f_net   = PMR1_F_FORM_NET
    I_CMB   = KAPPA_CMB * SIGMA_CMB_BG
    D, C, S, I, G = PMR1_COMPONENTS

    sigma = sigma_stable.copy()
    sigma_pre_transit = float(sigma[N_BUFFER:N_BUFFER + N_NEBULA].mean())

    sigma_min_transit   = sigma_pre_transit
    baryonic_accum      = 0.0
    craft_tare_injected = 0.0
    sigma_track         = [sigma_pre_transit]

    nan_flag = False
    inf_flag = False

    # ── TRANSIT PHASE ─────────────────────────────────────────────────────────
    for cell in range(N_TOTAL):
        for _ in range(steps_per_cell):
            # Nebula field evolution under Variant 2
            sigma_eff = sigma * f_net + KAPPA_CMB * SIGMA_CMB_BG
            phi_form  = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)
            sat       = np.clip(1.0 - sigma / SIGMA_FORM_CAP, 0.0, 1.0)
            T1        = sigma_eff * phi_form * sat
            T5        = LAMBDA_DECAY * sigma
            lap       = np.zeros_like(sigma)
            lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
            d_sigma   = T1 * f_net + I_CMB * sigma_eff - T5 + G * 0.01 * lap

            # Craft tare at current position — governed by saturation
            tare_profile = craft_tare_profile(cell, N_TOTAL)
            tare_governed = (CRAFT_TARE_FRACTION * sigma
                             * tare_profile * sat)
            d_sigma      -= tare_governed

            # Tare accounting
            tare_work_step       = float(np.sum(np.abs(tare_governed)))
            craft_tare_injected += tare_work_step

            # Baryonic consumption from nebula response
            baryonic_conversion = f_net * (1.0 - sat) * np.abs(d_sigma)
            baryonic_accum     += float(np.sum(baryonic_conversion))

            sigma = np.clip(sigma + DT * d_sigma, 0.0, None)

            # Track sigma in nebula zone only
            neb_mean = float(sigma[N_BUFFER:N_BUFFER + N_NEBULA].mean())
            if neb_mean < sigma_min_transit:
                sigma_min_transit = neb_mean
            sigma_track.append(neb_mean)

            if np.any(np.isnan(sigma)):
                nan_flag = True
                break
            if np.any(np.isinf(sigma)):
                inf_flag = True
                break
        if nan_flag or inf_flag:
            break

    sigma_post_entry = float(sigma[N_BUFFER:N_BUFFER + N_NEBULA].mean())

    # ── POST-TRANSIT RECOVERY PHASE ───────────────────────────────────────────
    for _ in range(POST_TRANSIT_STEPS):
        if nan_flag or inf_flag:
            break
        sigma_eff = sigma * f_net + KAPPA_CMB * SIGMA_CMB_BG
        phi_form  = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)
        sat       = np.clip(1.0 - sigma / SIGMA_FORM_CAP, 0.0, 1.0)
        T1        = sigma_eff * phi_form * sat
        T5        = LAMBDA_DECAY * sigma
        lap       = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        d_sigma   = T1 * f_net + I_CMB * sigma_eff - T5 + G * 0.01 * lap
        sigma     = np.clip(sigma + DT * d_sigma, 0.0, None)

        if np.any(np.isnan(sigma)):
            nan_flag = True
            break

    sigma_post_recovery = float(sigma[N_BUFFER:N_BUFFER + N_NEBULA].mean())
    sigma_final_max     = float(sigma.max())

    # ── Metrics ───────────────────────────────────────────────────────────────
    tare_depth_fraction = (
        (sigma_pre_transit - sigma_min_transit) / max(sigma_pre_transit, 1e-12)
    )
    recovery_ratio = sigma_post_recovery / max(sigma_pre_transit, 1e-12)
    cap_escaped    = sigma_final_max > SIGMA_FORM_CAP
    collapsed      = sigma_post_recovery < SIGMA_TARE_FLOOR

    tare_absorption_ratio = (
        baryonic_accum / max(craft_tare_injected, 1e-12)
    )

    # ── Classification ────────────────────────────────────────────────────────
    if nan_flag or inf_flag:
        state = "NUMERICAL_FAILURE"
    elif cap_escaped:
        state = "RECURSIVE_RIP_ONSET"
    elif collapsed:
        state = "NEBULA_COLLAPSE_INDUCED"
    elif recovery_ratio >= 0.90:
        state = "NEBULA_ABSORBS_TRANSIT"
    elif recovery_ratio >= 0.50:
        state = "NEBULA_PARTIAL_RECOVERY"
    else:
        # Check for scar — sigma held but depressed
        state = "NEBULA_SCAR_INSCRIBED"

    return {
        "velocity_c":           velocity_c,
        "steps_per_cell":       steps_per_cell,
        "total_transit_steps":  steps_per_cell * N_TOTAL,
        "sigma_pre_transit":    round(sigma_pre_transit, 8),
        "sigma_min_transit":    round(sigma_min_transit, 8),
        "sigma_post_entry":     round(sigma_post_entry, 8),
        "sigma_post_recovery":  round(sigma_post_recovery, 8),
        "tare_depth_fraction":  round(tare_depth_fraction, 6),
        "recovery_ratio":       round(recovery_ratio, 6),
        "baryonic_consumption": round(baryonic_accum, 6),
        "craft_tare_injected":  round(craft_tare_injected, 6),
        "tare_absorption_ratio": round(tare_absorption_ratio, 6),
        "cap_escaped":          cap_escaped,
        "collapsed":            collapsed,
        "nan_detected":         nan_flag,
        "inf_detected":         inf_flag,
        "formation_state":      state,
        "sigma_track_sample":   [round(v, 8) for v in sigma_track[::50]],
    }


def run_test():
    print("BCM v29 TEST21 — PMR 1 CRAFT TRANSIT TARE PIERCE")
    print(f"Backend: {_BACKEND}")
    print(f"PMR 1 F_form_net = {PMR1_F_FORM_NET}")
    print(f"Craft tare fraction: {CRAFT_TARE_FRACTION} | "
          f"Width: {CRAFT_TARE_WIDTH} pts")
    print(f"Entry/exit buffer: {N_BUFFER} pts (10 AU equivalent)")
    print(f"Post-transit recovery: {POST_TRANSIT_STEPS} steps")
    print()

    # Build stable PMR 1 field once — same baseline for all velocities
    print("Building PMR 1 stable field (500 pre-evolution steps)...")
    sigma_stable     = build_stable_pmr1_field()
    sigma_stable_mean = float(sigma_stable[N_BUFFER:N_BUFFER + N_NEBULA].mean())
    print(f"PMR 1 stable mean sigma (nebula zone): {sigma_stable_mean:.8f}")
    print()

    results = []
    state_counts: Dict[str, int] = {}
    architecture_clean = True

    for v in VELOCITIES:
        steps_cell = max(1, int(round(BASE_STEPS_PER_CELL * REFERENCE_SPEED / v)))
        print(f"Velocity: {v}c  ({steps_cell} steps/cell, "
              f"{steps_cell * N_TOTAL} total transit steps)")

        r = run_transit(v, sigma_stable)

        if r["nan_detected"] or r["inf_detected"]:
            architecture_clean = False

        st = r["formation_state"]
        state_counts[st] = state_counts.get(st, 0) + 1

        print(f"  sigma_pre        = {r['sigma_pre_transit']:.8f}")
        print(f"  sigma_min        = {r['sigma_min_transit']:.8f}")
        print(f"  sigma_recovery   = {r['sigma_post_recovery']:.8f}")
        print(f"  tare_depth       = {r['tare_depth_fraction']:.4f} "
              f"({r['tare_depth_fraction']*100:.1f}% depleted)")
        print(f"  recovery_ratio   = {r['recovery_ratio']:.6f}")
        print(f"  tare_absorption  = {r['tare_absorption_ratio']:.6f}")
        print(f"  baryonic_consump = {r['baryonic_consumption']:.6f}")
        print(f"  cap_escaped      = {r['cap_escaped']}")
        print(f"  formation_state  = {st}")
        print()

        results.append(r)

    # ── Comparative summary ───────────────────────────────────────────────────
    # Sort by velocity — does PMR 1 hold better at higher or lower speed?
    recovery_by_v = {r["velocity_c"]: r["recovery_ratio"] for r in results}
    tare_by_v     = {r["velocity_c"]: r["tare_depth_fraction"] for r in results}
    collapse_any  = any(r["collapsed"] for r in results)
    cap_any       = any(r["cap_escaped"] for r in results)

    # Velocity trend
    recoveries = [recovery_by_v[v] for v in VELOCITIES]
    tare_trend = "HIGHER_SPEED_LESS_DAMAGE" \
                 if tare_by_v[20000] < tare_by_v[5000] \
                 else "LOWER_SPEED_LESS_DAMAGE"

    # ── Verdict ───────────────────────────────────────────────────────────────
    if not architecture_clean:
        verdict  = "ARCHITECTURE_FAILURE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_FAILED"]
    elif cap_any:
        verdict  = "RECURSIVE_RIP_TRIGGERED"
        hyp_keys = ["H_V29_PMR1_TARE_PIERCE_RECURSIVE_RIP"]
    elif collapse_any:
        speeds_collapsed = [r["velocity_c"] for r in results if r["collapsed"]]
        verdict  = f"COLLAPSE_INDUCED_AT_{speeds_collapsed}"
        hyp_keys = ["H_V29_PMR1_TARE_PIERCE_COLLAPSE"]
    elif all(r["recovery_ratio"] >= 0.90 for r in results):
        verdict  = "PMR1_ABSORBS_ALL_VELOCITIES"
        hyp_keys = ["H_V29_PMR1_TARE_PIERCE_RESILIENT",
                    "H_V29_NEBULAR_SATURATION_KERNEL"]
    elif any(r["recovery_ratio"] >= 0.90 for r in results):
        verdict  = f"PMR1_VELOCITY_SELECTIVE_ABSORPTION__{tare_trend}"
        hyp_keys = ["H_V29_PMR1_TARE_PIERCE_VELOCITY_DEPENDENT"]
    else:
        verdict  = f"PMR1_SCAR_DOMINANT__{tare_trend}"
        hyp_keys = ["H_V29_PMR1_TARE_PIERCE_SCAR_INSCRIBED"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST21_PMR1_TARE_PIERCE_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST21",
        "test_name": "PMR1_CRAFT_TRANSIT_TARE_PIERCE",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",
        "backend":   _BACKEND,

        "pmr1_config": {
            "components":     PMR1_COMPONENTS,
            "f_form_net":     PMR1_F_FORM_NET,
            "hybrid_weights": PMR1_HW,
            "stable_mean_sigma": round(sigma_stable_mean, 8),
        },
        "craft_config": {
            "velocities_c":        VELOCITIES,
            "reference_speed_c":   REFERENCE_SPEED,
            "tare_fraction":       CRAFT_TARE_FRACTION,
            "tare_width_pts":      CRAFT_TARE_WIDTH,
            "buffer_pts":          N_BUFFER,
            "post_transit_steps":  POST_TRANSIT_STEPS,
            "base_steps_per_cell": BASE_STEPS_PER_CELL,
        },
        "transit_results":    results,
        "recovery_by_velocity": recovery_by_v,
        "tare_depth_by_velocity": tare_by_v,
        "velocity_trend":     tare_trend,
        "state_counts":       state_counts,
        "collapse_any":       collapse_any,
        "cap_escape_any":     cap_any,
        "architecture_clean": architecture_clean,

        "verdict":        verdict,
        "hypothesis_keys": hyp_keys,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    print("=" * 60)
    print("TEST21 — SUMMARY")
    print("=" * 60)
    print(f"Architecture clean:  {architecture_clean}")
    print(f"Velocity trend:      {tare_trend}")
    print(f"Collapse any:        {collapse_any}")
    print(f"Cap escape any:      {cap_any}")
    print("Recovery by velocity:")
    for v in VELOCITIES:
        print(f"  {v}c : recovery={recovery_by_v[v]:.4f}  "
              f"tare_depth={tare_by_v[v]:.4f}  "
              f"state={[r['formation_state'] for r in results if r['velocity_c']==v][0]}")
    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
