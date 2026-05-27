# -*- coding: utf-8 -*-
"""
BCM v29 TEST17 — NEBULAR FORMATION VARIANT 2 (REAL-WORLD TARGETS)
==================================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Adversarial basis: ChatGPT JWST gap analysis.
Equation form:     Gemini engineering formalization channel.
Observational targets: Gemini empirical nebula registry (JWST/ALMA data).
Code execution:    The code builder.

Test16 established architecture clean. This test probes real physics
using five empirically-grounded nebula targets with component vectors
derived from JWST observational profiles.

Fixes applied from Test16 post-analysis:
  1. sigma_initial_mean computed from actual array (not hardcoded)
  2. Five-state formation classifier (adds NEUTRAL_STASIS, SLOW_DRIFT, DECAY)
  3. Drive equation separated: local_drive + cmb_bias - T5 (not all CMB-scaled)
  4. SIGMA_FORM_CRIT = 0.05 (nebular pre-pump scale, not galactic 10.0)
  5. growth_ratio bands replace binary accumulation check

Corrected Variant 2 drive:
    local_drive = T1 * f_form           (local formation — not CMB-gated)
    cmb_bias    = I_CMB * sigma_eff     (primordial pre-strain contribution)
    d_sigma     = local_drive + cmb_bias - T5

Five-state formation classifier:
    growth_ratio = sigma_final_mean / sigma_initial_mean
    > 1.10  → FORMATION_CONFIRMED
    1.02–1.10 → FORMATION_SLOW_DRIFT
    0.98–1.02 → FORMATION_NEUTRAL_STASIS  (dark condensate memory state)
    0.90–0.98 → FORMATION_SLOW_DECAY
    < 0.90  → FORMATION_DECAY

Five real-world targets (Gemini empirical registry):
  1. CHAMAELEON_I   — DARK_CONDENSATE   — [1.00, 0.95, 0.00, 0.00, 0.85]
  2. NGC_1333       — SCATTER_MEMORY    — [0.90, 0.40, 0.15, 0.20, 0.60]
  3. TARANTULA_30DOR— IONIZED_FORMATION — [0.35, 0.85, 0.60, 1.00, 0.70]
  4. HH_211         — SHOCK_INSCRIPTION — [0.50, 0.70, 1.00, 0.10, 0.45]
  5. NGC_3132       — POST_PUMP_SHELL   — [0.85, 0.50, 0.30, 0.75, 0.20]

Output JSON keys:
    test_id, test_name, timestamp, foreman
    variant, xi_s, t2_active, t3_active
    kappa_cmb, alpha_void, lambda_decay, sigma_cmb_bg, sigma_form_crit
    targets: list of per-target results
    formation_state_counts
    architecture_clean
    verdict, hypothesis_keys
"""

from __future__ import annotations

import json
import sys
import math
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ── path setup ──────────────────────────────────────────────────────────────
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

from bcm_thresholds import (
    KAPPA_CMB, ALPHA_VOID_DEFAULT,
    LAMBDA_DECAY,
)

# ── Variant 2 constants ──────────────────────────────────────────────────────
XI_S            = 0.0    # Fully fractional — no integerization
T2_ACTIVE       = False  # Substrate current loop DEACTIVATED
T3_ACTIVE       = False  # Spectral projection gate DEACTIVATED
SIGMA_CMB_BG    = 0.01   # Primordial pre-strain background (placeholder)
SIGMA_FORM_CRIT = 0.05   # Pre-pump nebular formation scale (not galactic 10.0)
N_STEPS         = 2000
N_R             = 64
DT              = 0.01

# Formation threshold for F_form_scalar (above = source competitive with drain)
FORMATION_THRESHOLD = LAMBDA_DECAY   # = 0.1

# Growth ratio bands for five-state classifier
GROWTH_CONFIRMED    = 1.10
GROWTH_SLOW_UPPER   = 1.02
GROWTH_STASIS_LOWER = 0.98
GROWTH_SLOW_LOWER   = 0.90

# ── Real-world nebula target registry (Gemini empirical, JWST/ALMA data) ────
# Components: [D_dust, C_cool, S_shock, I_ion, G_grad]

NEBULA_TARGETS = [
    {
        "target_name":  "CHAMAELEON_I",
        "nebula_class": "DARK_CONDENSATE",
        "components":   [1.00, 0.95, 0.00, 0.00, 0.85],
        "observational_basis": (
            "JWST pristine ice core. ~10 K, extreme visual extinction. "
            "Coldest interstellar ices measured (H2O, CO2, CH4, COS). "
            "High dust retention, intense localized entropy dump, zero "
            "ionizing interference. Distance ~630 ly. Ced 110 IRS 4."
        ),
    },
    {
        "target_name":  "NGC_1333",
        "nebula_class": "SCATTER_MEMORY",
        "components":   [0.90, 0.40, 0.15, 0.20, 0.60],
        "observational_basis": (
            "Perseus molecular cloud reflection nebula. Illuminated by "
            "BD+30 549 (B8, Teff~13100 K). ~450 M_sun total mass. "
            "Structured dust scattering along cold hidden gas lanes. "
            "Distance ~967 ly. Multi-generational low-mass star clusters."
        ),
    },
    {
        "target_name":  "TARANTULA_30DOR",
        "nebula_class": "IONIZED_FORMATION",
        "components":   [0.35, 0.85, 0.60, 1.00, 0.70],
        "observational_basis": (
            "Most luminous starburst region in Local Group. R136 super "
            "star cluster (1.5e4 to 1e7 M_sun/pc^3). Mass surface density "
            "178 M_sun/pc^2 (40% above Milky Way baseline). Extreme UV "
            "radiative pressure. Diameter ~200 pc, LMC."
        ),
    },
    {
        "target_name":  "HH_211",
        "nebula_class": "SHOCK_INSCRIPTION",
        "components":   [0.50, 0.70, 1.00, 0.10, 0.45],
        "observational_basis": (
            "Class 0 protostellar jet analog. ~8% M_sun, few tens of kyr "
            "old. Bipolar jets at 80-100 km/s. Bow shocks in H2, CO, SiO. "
            "Pure kinetic inscription. Distance ~1000 ly, Perseus."
        ),
    },
    {
        "target_name":  "NGC_3132",
        "nebula_class": "POST_PUMP_SHELL",
        "components":   [0.85, 0.50, 0.30, 0.75, 0.20],
        "observational_basis": (
            "Southern Ring Nebula. JWST ERO target. Multi-stellar core, "
            "pre-white dwarf ~0.7 M_sun, Teff~100000 K. Two perpendicular "
            "expanding rings at ~14.5 km/s. Molecule-rich post-pump shell. "
            "Distance ~2000 ly, diameter ~0.4 ly."
        ),
    },
]


def f_form_scalar(components: List[float]) -> float:
    """
    F_form = product of ALL non-zero active components.
    Zero = inactive mechanism (excluded from product, not a failure).
    """
    active = [c for c in components if c > 0.0]
    if not active:
        return 0.0
    result = 1.0
    for c in active:
        result *= c
    return result


def formation_state_from_ratio(ratio: float, f_form: float) -> str:
    """Five-state formation classifier. Stasis is valid physics."""
    if f_form == 0.0:
        return "F_FORM_ZERO_NO_DRIVE"
    if ratio > GROWTH_CONFIRMED:
        return "FORMATION_CONFIRMED"
    if ratio >= GROWTH_SLOW_UPPER:
        return "FORMATION_SLOW_DRIFT"
    if ratio >= GROWTH_STASIS_LOWER:
        return "FORMATION_NEUTRAL_STASIS"
    if ratio >= GROWTH_SLOW_LOWER:
        return "FORMATION_SLOW_DECAY"
    return "FORMATION_DECAY"


def run_variant2(target: Dict[str, Any]) -> Dict[str, Any]:
    """
    Variant 2 evolution for one real-world target.

    Corrected drive equation (separated from Test16):
        sigma_eff    = sigma_local * f_form + kappa_CMB * sigma_CMB_bg
        T1           = sigma_eff * phi_form     (formation coupling)
        T5           = LAMBDA_DECAY * sigma     (maintenance drain — local, not CMB-scaled)
        I_CMB        = kappa_CMB * sigma_CMB_bg (CMB intensity proxy)
        local_drive  = T1 * f_form
        cmb_bias     = I_CMB * sigma_eff
        d_sigma      = local_drive + cmb_bias - T5
    """
    name       = target["target_name"]
    components = target["components"]
    f_form     = f_form_scalar(components)

    # Initial sigma: Gaussian nebula seed
    r     = np.linspace(0, 1, N_R)
    sigma = np.exp(-((r - 0.5) ** 2) / (2 * 0.1 ** 2)) * 0.1

    # Store actual initial mean (not hardcoded)
    sigma_initial_mean = float(sigma.mean())

    I_CMB = KAPPA_CMB * SIGMA_CMB_BG   # CMB intensity proxy (alpha=1.0 so no power)

    delta_w = 0.0
    sigma_track = [sigma_initial_mean]

    nan_flag = False
    inf_flag = False

    for step in range(N_STEPS):
        # sigma_eff: local substrate field with CMB pre-strain
        sigma_eff = sigma * f_form + KAPPA_CMB * SIGMA_CMB_BG

        # T1: formation coupling at nebular scale
        phi_form = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)
        T1 = sigma_eff * phi_form

        # T5: maintenance drain (local, not CMB-scaled)
        T5 = LAMBDA_DECAY * sigma

        # Corrected drive: separated local formation + CMB bias
        local_drive = T1 * f_form
        cmb_bias    = I_CMB * sigma_eff
        d_sigma     = local_drive + cmb_bias - T5

        # G_grad diffusion (condensation toward density peaks)
        lap = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        g_grad_component = target["components"][4]
        d_sigma += g_grad_component * 0.01 * lap

        sigma = np.clip(sigma + DT * d_sigma, 0.0, None)

        # Accumulate Delta_W_Neb = integral of [T1*F_form + T5] * |d_sigma|
        delta_w += float(np.sum((T1 * f_form + T5) * np.abs(d_sigma)))

        if step % 500 == 0:
            sigma_track.append(float(sigma.mean()))

        if np.any(np.isnan(sigma)):
            nan_flag = True
            break
        if np.any(np.isinf(sigma)):
            inf_flag = True
            break

    sigma_final_mean  = float(sigma.mean())
    sigma_final_max   = float(sigma.max())
    sigma_final_total = float(sigma.sum())

    growth_ratio = sigma_final_mean / max(sigma_initial_mean, 1e-12)

    if nan_flag or inf_flag:
        state = "NUMERICAL_FAILURE"
    else:
        state = formation_state_from_ratio(growth_ratio, f_form)

    return {
        "target_name":       name,
        "nebula_class":      target["nebula_class"],
        "components":        {
            "D_dust":  target["components"][0],
            "C_cool":  target["components"][1],
            "S_shock": target["components"][2],
            "I_ion":   target["components"][3],
            "G_grad":  target["components"][4],
        },
        "f_form_scalar":      round(f_form, 6),
        "sigma_initial_mean": round(sigma_initial_mean, 8),
        "sigma_final_mean":   round(sigma_final_mean, 8),
        "sigma_final_max":    round(sigma_final_max, 8),
        "sigma_final_total":  round(sigma_final_total, 6),
        "growth_ratio":       round(growth_ratio, 6),
        "delta_w_neb":        round(delta_w, 6),
        "sigma_track":        [round(v, 8) for v in sigma_track],
        "nan_detected":       nan_flag,
        "inf_detected":       inf_flag,
        "formation_state":    state,
        "observational_basis": target["observational_basis"],
    }


def run_test():
    print("BCM v29 TEST17 — NEBULAR FORMATION VARIANT 2 (REAL-WORLD TARGETS)")
    print(f"Backend: {_BACKEND}")
    print(f"Xi_S={XI_S} | T2={T2_ACTIVE} | T3={T3_ACTIVE}")
    print(f"kappa_CMB={KAPPA_CMB} | alpha_void={ALPHA_VOID_DEFAULT}")
    print(f"SIGMA_FORM_CRIT={SIGMA_FORM_CRIT} | LAMBDA_DECAY={LAMBDA_DECAY}")
    print(f"FORMATION_THRESHOLD={FORMATION_THRESHOLD}")
    print()

    target_results = []
    architecture_clean = True
    state_counts: Dict[str, int] = {}

    for target in NEBULA_TARGETS:
        name = target["target_name"]
        cls  = target["nebula_class"]
        comp = target["components"]
        f_s  = f_form_scalar(comp)
        print(f"{name} ({cls})")
        print(f"  Components [D,C,S,I,G] = {comp}")
        print(f"  F_form scalar           = {f_s:.6f}")

        result = run_variant2(target)

        if result["nan_detected"] or result["inf_detected"]:
            architecture_clean = False

        state = result["formation_state"]
        state_counts[state] = state_counts.get(state, 0) + 1

        print(f"  sigma_initial_mean = {result['sigma_initial_mean']:.8f}")
        print(f"  sigma_final_mean   = {result['sigma_final_mean']:.8f}")
        print(f"  growth_ratio       = {result['growth_ratio']:.6f}")
        print(f"  delta_W_Neb        = {result['delta_w_neb']:.6f}")
        print(f"  formation_state    = {state}")
        print()

        target_results.append(result)

    # ── verdict ───────────────────────────────────────────────────────────────
    if not architecture_clean:
        verdict  = "ARCHITECTURE_FAILURE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_FAILED"]
    else:
        confirmed_count = state_counts.get("FORMATION_CONFIRMED", 0)
        stasis_count    = state_counts.get("FORMATION_NEUTRAL_STASIS", 0)
        decay_count     = state_counts.get("FORMATION_DECAY", 0)

        if confirmed_count >= 1 and architecture_clean:
            verdict = "FORMATION_CONFIRMED_IN_SUBSET"
        elif stasis_count >= 1 and confirmed_count == 0:
            verdict = "STASIS_DOMINANT_CALIBRATION_NEEDED"
        elif decay_count == 5:
            verdict = "ALL_DECAY_DRIVE_UNDERSIZED"
        else:
            verdict = "MIXED_FORMATION_STATES"

        hyp_keys = [
            "H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
            "H_V29_DARK_CONDENSATE",
            "H_V29_SHOCK_INSCRIPTION",
        ]

    # ── output ────────────────────────────────────────────────────────────────
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST17_NEBULAR_FORMATION_TARGETS_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST17",
        "test_name": "NEBULAR_FORMATION_VARIANT2_REAL_TARGETS",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",
        "backend":   _BACKEND,

        "variant":   "NEBULAR_V2",
        "xi_s":      XI_S,
        "t2_active": T2_ACTIVE,
        "t3_active": T3_ACTIVE,

        "kappa_cmb":          KAPPA_CMB,
        "alpha_void":         ALPHA_VOID_DEFAULT,
        "lambda_decay":       LAMBDA_DECAY,
        "sigma_cmb_bg":       SIGMA_CMB_BG,
        "sigma_form_crit":    SIGMA_FORM_CRIT,
        "formation_threshold": FORMATION_THRESHOLD,
        "n_steps":            N_STEPS,
        "n_r":                N_R,

        "fixes_from_test16": [
            "sigma_initial_mean computed from actual array",
            "five-state formation classifier added",
            "drive equation separated: local_drive + cmb_bias - T5",
            "SIGMA_FORM_CRIT=0.05 (nebular scale, not galactic)",
            "growth_ratio bands replace binary accumulation check",
        ],

        "targets":               target_results,
        "formation_state_counts": state_counts,
        "architecture_clean":    architecture_clean,

        "verdict":        verdict,
        "hypothesis_keys": hyp_keys,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    print("=" * 60)
    print("TEST17 — SUMMARY")
    print("=" * 60)
    print(f"Architecture clean: {architecture_clean}")
    print(f"Formation state counts:")
    for s, c in sorted(state_counts.items()):
        print(f"  {s}: {c}")
    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
