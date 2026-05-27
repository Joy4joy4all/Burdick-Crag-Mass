# -*- coding: utf-8 -*-
"""
BCM v29 TEST18 — NEBULAR FORMATION CLASS-SPECIFIC OPERATORS
=============================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Adversarial basis: ChatGPT JWST gap analysis + Test17 post-analysis.
Equation form:     Gemini engineering formalization channel.
Code execution:    The code builder.

Test17 found:
  - Architecture clean. Non-pump lane confirmed.
  - Universal product F_form is too punishing for mixed-channel nebulae.
  - Dark condensate (Chamaeleon I) ran away: sigma 1330, delta_W 14.7e9.
  - All four mixed-channel targets decayed under product rule.

This test replaces the universal F_form product with class-specific
formation operators, adds a saturation cap, and adds a runaway guard.

CLASS-SPECIFIC FORMATION OPERATORS (ChatGPT analysis, Gemini form):

  DARK_CONDENSATE:
    F_dark = D_dust * C_cool * G_grad
    (quiet cooperation — product valid for single-channel locks)

  SCATTER_MEMORY:
    F_scatter = D_dust * G_grad * (1 - I_ion)
    (reveals boundary, not accumulates; ionization subtracts from memory)
    Expected state: SCATTER_MEMORY_STASIS (not FORMATION_CONFIRMED)

  IONIZED_FORMATION:
    F_ion_drive   = I_ion * C_cool * G_grad
    F_ion_blowout = ETA_ION_BLOWOUT * I_ion * (1 - D_dust)
    F_ion_net     = F_ion_drive - F_ion_blowout
    (ionization drives AND erodes; net determines balance or blowout)
    ETA_ION_BLOWOUT = 0.5 (placeholder — pending SJB calibration)

  SHOCK_INSCRIPTION:
    F_shock = S_shock * (0.5 * C_cool + 0.5 * G_grad)
    (shock dominant — additive channel weight, not product-killed by low I_ion)
    Expected state: SHOCK_INSCRIPTION_ACTIVE if delta_sigma writes structure

  POST_PUMP_SHELL:
    F_shell = D_dust * I_ion
    (residual memory — dust holds hysteresis echo under UV field)
    Expected state: POST_PUMP_SHELL_MEMORY (not FORMATION_CONFIRMED)

SATURATION CAP:
    formation_drive *= (1.0 - sigma / SIGMA_FORM_CAP)
    SIGMA_FORM_CAP = 1.0
    Prevents dark condensate runaway. Real cores saturate into protostellar seeds.

RUNAWAY GUARD:
    if delta_w_neb > DELTA_W_NEB_RUNAWAY: state = FORMATION_RUNAWAY
    DELTA_W_NEB_RUNAWAY = 1e3

UPDATED STATE TABLE:
    FORMATION_CONFIRMED_STABLE   sigma grew AND delta_W < runaway threshold
    FORMATION_RUNAWAY            delta_W > 1e3 OR sigma > SIGMA_FORM_CAP * 10
    FORMATION_NEUTRAL_STASIS     growth_ratio 0.98-1.02
    FORMATION_SLOW_DRIFT         growth_ratio 1.02-1.10
    FORMATION_SLOW_DECAY         growth_ratio 0.90-0.98
    FORMATION_DECAY              growth_ratio < 0.90
    SCATTER_MEMORY_STASIS        scatter class holding boundary
    SHOCK_INSCRIPTION_ACTIVE     shock wrote gradient structure into sigma
    POST_PUMP_SHELL_MEMORY       shell class holding residual memory
    IONIZED_ACTIVE_BALANCE       net F_ion > 0, some formation
    IONIZED_BLOWOUT              net F_ion <= 0, ionization eroding substrate
    F_FORM_ZERO_NO_DRIVE         no active formation mechanism
    NUMERICAL_FAILURE            nan/inf detected
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

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

from bcm_thresholds import KAPPA_CMB, ALPHA_VOID_DEFAULT, LAMBDA_DECAY

# ── Variant 2 constants ──────────────────────────────────────────────────────
XI_S             = 0.0
T2_ACTIVE        = False
T3_ACTIVE        = False
SIGMA_CMB_BG     = 0.01
SIGMA_FORM_CRIT  = 0.05
SIGMA_FORM_CAP   = 1.0      # Saturation cap — prevents runaway
N_STEPS          = 2000
N_R              = 64
DT               = 0.01

DELTA_W_NEB_RUNAWAY = 1e3   # Runaway guard threshold
ETA_ION_BLOWOUT     = 0.5   # Ionized blowout coefficient — PLACEHOLDER

# Growth ratio bands
GROWTH_CONFIRMED  = 1.10
GROWTH_STASIS_HI  = 1.02
GROWTH_STASIS_LO  = 0.98
GROWTH_DECAY_LO   = 0.90

# ── Real-world targets (same five as Test17) ──────────────────────────────────
NEBULA_TARGETS = [
    {
        "target_name":  "CHAMAELEON_I",
        "nebula_class": "DARK_CONDENSATE",
        "components":   [1.00, 0.95, 0.00, 0.00, 0.85],
        "observational_basis": "JWST pristine ice core ~10K. Extreme visual extinction. Coldest ices measured.",
    },
    {
        "target_name":  "NGC_1333",
        "nebula_class": "SCATTER_MEMORY",
        "components":   [0.90, 0.40, 0.15, 0.20, 0.60],
        "observational_basis": "Perseus reflection nebula. BD+30 549 illumination. ~450 M_sun. Dust boundary visualizer.",
    },
    {
        "target_name":  "TARANTULA_30DOR",
        "nebula_class": "IONIZED_FORMATION",
        "components":   [0.35, 0.85, 0.60, 1.00, 0.70],
        "observational_basis": "R136 super star cluster. Extreme UV radiative pressure. Starburst, LMC.",
    },
    {
        "target_name":  "HH_211",
        "nebula_class": "SHOCK_INSCRIPTION",
        "components":   [0.50, 0.70, 1.00, 0.10, 0.45],
        "observational_basis": "Class 0 protostellar jet. 80-100 km/s bipolar jets. Bow shocks H2/CO/SiO.",
    },
    {
        "target_name":  "NGC_3132",
        "nebula_class": "POST_PUMP_SHELL",
        "components":   [0.85, 0.50, 0.30, 0.75, 0.20],
        "observational_basis": "Southern Ring Nebula. JWST ERO. Post-white-dwarf shell. Two expanding rings.",
    },
]


def class_operator(nebula_class: str,
                   comp: List[float]) -> Dict[str, Any]:
    """
    Compute class-specific F_form operator and net scalar.
    Returns dict with operator_name, f_form_net, and operator components.
    """
    D, C, S, I, G = comp

    if nebula_class == "DARK_CONDENSATE":
        f_net = D * C * G   # quiet cooperation — only these three
        return {
            "operator": "F_dark = D_dust * C_cool * G_grad",
            "f_form_net": f_net,
            "notes": "Product valid for single-channel lock. No shock/ionization.",
        }

    elif nebula_class == "SCATTER_MEMORY":
        f_net = D * G * (1.0 - I)   # ionization subtracts from memory
        return {
            "operator": "F_scatter = D_dust * G_grad * (1 - I_ion)",
            "f_form_net": f_net,
            "notes": "Reveals boundary, does not accumulate. Expected: STASIS.",
        }

    elif nebula_class == "IONIZED_FORMATION":
        f_drive    = I * C * G
        f_blowout  = ETA_ION_BLOWOUT * I * (1.0 - D)
        f_net      = f_drive - f_blowout
        return {
            "operator": "F_ion = I*C*G - eta*I*(1-D)  [eta=0.5 placeholder]",
            "f_form_net":  f_net,
            "f_ion_drive": f_drive,
            "f_ion_blowout": f_blowout,
            "notes": "Drive minus blowout. Net determines balance or erosion.",
        }

    elif nebula_class == "SHOCK_INSCRIPTION":
        f_net = S * (0.5 * C + 0.5 * G)   # shock dominant, not product-killed
        return {
            "operator": "F_shock = S_shock * (0.5*C_cool + 0.5*G_grad)",
            "f_form_net": f_net,
            "notes": "Shock dominant. Additive weight. Not killed by low I_ion.",
        }

    elif nebula_class == "POST_PUMP_SHELL":
        f_net = D * I   # dust holds hysteresis echo under UV field
        return {
            "operator": "F_shell = D_dust * I_ion",
            "f_form_net": f_net,
            "notes": "Residual memory. Expected: POST_PUMP_SHELL_MEMORY.",
        }

    else:
        f_net = 0.0
        return {
            "operator": "UNKNOWN_CLASS",
            "f_form_net": 0.0,
            "notes": "Unrecognized nebula class.",
        }


def classify_state(nebula_class: str,
                   growth_ratio: float,
                   delta_w: float,
                   sigma_final_mean: float,
                   f_net: float,
                   nan_flag: bool,
                   inf_flag: bool) -> str:
    """Class-aware state classification."""
    if nan_flag or inf_flag:
        return "NUMERICAL_FAILURE"
    if f_net <= 0.0:
        if nebula_class == "IONIZED_FORMATION":
            return "IONIZED_BLOWOUT"
        return "F_FORM_ZERO_NO_DRIVE"

    # Runaway check (universal)
    if delta_w > DELTA_W_NEB_RUNAWAY or sigma_final_mean > SIGMA_FORM_CAP * 10:
        return "FORMATION_RUNAWAY"

    # Class-specific expected states
    if nebula_class == "SCATTER_MEMORY":
        if GROWTH_STASIS_LO <= growth_ratio <= GROWTH_STASIS_HI:
            return "SCATTER_MEMORY_STASIS"
        elif growth_ratio < GROWTH_STASIS_LO:
            return "SCATTER_MEMORY_FADING"
        else:
            return "SCATTER_MEMORY_ACTIVE"

    if nebula_class == "POST_PUMP_SHELL":
        if growth_ratio >= GROWTH_STASIS_LO:
            return "POST_PUMP_SHELL_MEMORY"
        else:
            return "POST_PUMP_SHELL_FADING"

    if nebula_class == "IONIZED_FORMATION":
        if f_net > 0 and growth_ratio >= GROWTH_STASIS_LO:
            return "IONIZED_ACTIVE_BALANCE"
        elif f_net > 0 and growth_ratio > GROWTH_CONFIRMED:
            return "IONIZED_FORMATION_CONFIRMED"
        else:
            return "IONIZED_BLOWOUT"

    if nebula_class == "SHOCK_INSCRIPTION":
        # Shock writes gradient structure — check spatial max vs mean
        if growth_ratio >= GROWTH_STASIS_LO:
            return "SHOCK_INSCRIPTION_ACTIVE"
        else:
            return "SHOCK_INSCRIPTION_FADING"

    # Generic (covers DARK_CONDENSATE and any future class)
    if growth_ratio > GROWTH_CONFIRMED:
        return "FORMATION_CONFIRMED_STABLE"
    if growth_ratio >= GROWTH_STASIS_HI:
        return "FORMATION_SLOW_DRIFT"
    if growth_ratio >= GROWTH_STASIS_LO:
        return "FORMATION_NEUTRAL_STASIS"
    if growth_ratio >= GROWTH_DECAY_LO:
        return "FORMATION_SLOW_DECAY"
    return "FORMATION_DECAY"


def run_target(target: Dict[str, Any]) -> Dict[str, Any]:
    name  = target["target_name"]
    cls   = target["nebula_class"]
    comp  = target["components"]

    op_info = class_operator(cls, comp)
    f_net   = op_info["f_form_net"]

    D, C, S, I, G = comp

    # Initial sigma: Gaussian seed
    r     = np.linspace(0, 1, N_R)
    sigma = np.exp(-((r - 0.5) ** 2) / (2 * 0.1 ** 2)) * 0.1
    sigma_initial_mean = float(sigma.mean())

    I_CMB = KAPPA_CMB * SIGMA_CMB_BG

    delta_w   = 0.0
    sigma_track = [sigma_initial_mean]
    nan_flag  = False
    inf_flag  = False

    for step in range(N_STEPS):
        sigma_eff  = sigma * max(f_net, 0.0) + KAPPA_CMB * SIGMA_CMB_BG
        phi_form   = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)

        # T1 with saturation cap
        saturation     = np.clip(1.0 - sigma / SIGMA_FORM_CAP, 0.0, 1.0)
        T1_saturated   = sigma_eff * phi_form * saturation

        # T5: maintenance drain (local, not CMB-scaled)
        T5 = LAMBDA_DECAY * sigma

        # Corrected drive: local formation + CMB bias - drain
        local_drive = T1_saturated * max(f_net, 0.0)
        cmb_bias    = I_CMB * sigma_eff
        d_sigma     = local_drive + cmb_bias - T5

        # G_grad diffusion term
        lap = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        d_sigma += G * 0.01 * lap

        sigma = np.clip(sigma + DT * d_sigma, 0.0, None)
        delta_w += float(np.sum(np.abs(d_sigma)))

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
    growth_ratio = sigma_final_mean / max(sigma_initial_mean, 1e-12)

    state = classify_state(
        cls, growth_ratio, delta_w, sigma_final_mean,
        f_net, nan_flag, inf_flag
    )

    return {
        "target_name":       name,
        "nebula_class":      cls,
        "components":        {"D_dust": D, "C_cool": C, "S_shock": S, "I_ion": I, "G_grad": G},
        "operator_info":     op_info,
        "f_form_net":        round(f_net, 6),
        "sigma_initial_mean": round(sigma_initial_mean, 8),
        "sigma_final_mean":  round(sigma_final_mean, 8),
        "sigma_final_max":   round(sigma_final_max, 8),
        "growth_ratio":      round(growth_ratio, 6),
        "delta_w_neb":       round(delta_w, 4),
        "sigma_track":       [round(v, 8) for v in sigma_track],
        "nan_detected":      nan_flag,
        "inf_detected":      inf_flag,
        "formation_state":   state,
        "observational_basis": target["observational_basis"],
    }


def run_test():
    print("BCM v29 TEST18 — NEBULAR FORMATION CLASS-SPECIFIC OPERATORS")
    print(f"Backend: {_BACKEND}")
    print(f"Xi_S={XI_S} | T2={T2_ACTIVE} | T3={T3_ACTIVE}")
    print(f"SIGMA_FORM_CAP={SIGMA_FORM_CAP} | DELTA_W_RUNAWAY={DELTA_W_NEB_RUNAWAY}")
    print(f"ETA_ION_BLOWOUT={ETA_ION_BLOWOUT} [placeholder]")
    print()

    results = []
    state_counts: Dict[str, int] = {}
    architecture_clean = True

    for target in NEBULA_TARGETS:
        name = target["target_name"]
        cls  = target["nebula_class"]
        print(f"{name} ({cls})")

        r = run_target(target)

        if r["nan_detected"] or r["inf_detected"]:
            architecture_clean = False

        state = r["formation_state"]
        state_counts[state] = state_counts.get(state, 0) + 1

        print(f"  Operator: {r['operator_info']['operator']}")
        print(f"  F_form_net       = {r['f_form_net']:.6f}")
        print(f"  sigma_initial    = {r['sigma_initial_mean']:.8f}")
        print(f"  sigma_final      = {r['sigma_final_mean']:.8f}")
        print(f"  growth_ratio     = {r['growth_ratio']:.6f}")
        print(f"  delta_W_Neb      = {r['delta_w_neb']:.4f}")
        print(f"  formation_state  = {state}")
        print()

        results.append(r)

    # ── verdict ───────────────────────────────────────────────────────────────
    runaway_count  = state_counts.get("FORMATION_RUNAWAY", 0)
    stable_count   = state_counts.get("FORMATION_CONFIRMED_STABLE", 0)
    active_states  = sum(
        state_counts.get(s, 0) for s in [
            "SHOCK_INSCRIPTION_ACTIVE", "IONIZED_ACTIVE_BALANCE",
            "IONIZED_FORMATION_CONFIRMED", "POST_PUMP_SHELL_MEMORY",
            "SCATTER_MEMORY_STASIS",
        ]
    )

    if not architecture_clean:
        verdict  = "ARCHITECTURE_FAILURE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_FAILED"]
    elif runaway_count > 0:
        verdict  = "CLASS_OPERATORS_ACTIVE__RUNAWAY_PERSISTS"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
                    "H_V29_DARK_CONDENSATE",
                    "H_V29_NEBULAR_CLASS_OPERATORS_PARTIAL"]
    elif stable_count >= 1 and active_states >= 3:
        verdict  = "CLASS_OPERATORS_VALIDATED__ALL_STATES_DISTINCT"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
                    "H_V29_DARK_CONDENSATE",
                    "H_V29_SHOCK_INSCRIPTION",
                    "H_V29_NEBULAR_CLASS_OPERATORS_CONFIRMED"]
    elif active_states >= 2:
        verdict  = "CLASS_OPERATORS_ACTIVE__PARTIAL_SEPARATION"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
                    "H_V29_NEBULAR_CLASS_OPERATORS_PARTIAL"]
    else:
        verdict  = "CLASS_OPERATORS_NEED_CALIBRATION"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST18_NEBULAR_CLASS_OPERATORS_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST18",
        "test_name": "NEBULAR_FORMATION_CLASS_OPERATORS",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",
        "backend":   _BACKEND,

        "variant":   "NEBULAR_V2",
        "xi_s":      XI_S,
        "t2_active": T2_ACTIVE,
        "t3_active": T3_ACTIVE,

        "kappa_cmb":              KAPPA_CMB,
        "sigma_form_crit":        SIGMA_FORM_CRIT,
        "sigma_form_cap":         SIGMA_FORM_CAP,
        "delta_w_neb_runaway":    DELTA_W_NEB_RUNAWAY,
        "eta_ion_blowout":        ETA_ION_BLOWOUT,
        "lambda_decay":           LAMBDA_DECAY,

        "class_operators": {
            "DARK_CONDENSATE":   "F_dark = D_dust * C_cool * G_grad",
            "SCATTER_MEMORY":    "F_scatter = D_dust * G_grad * (1 - I_ion)",
            "IONIZED_FORMATION": "F_ion = I*C*G - eta*I*(1-D)  [eta=0.5 placeholder]",
            "SHOCK_INSCRIPTION": "F_shock = S_shock * (0.5*C_cool + 0.5*G_grad)",
            "POST_PUMP_SHELL":   "F_shell = D_dust * I_ion",
        },

        "targets":               results,
        "formation_state_counts": state_counts,
        "architecture_clean":    architecture_clean,

        "verdict":        verdict,
        "hypothesis_keys": hyp_keys,

        "pending_calibration": [
            "ETA_ION_BLOWOUT=0.5 is placeholder — SJB calibration needed",
            "SIGMA_FORM_CAP=1.0 is first estimate — needs per-class tuning",
            "DELTA_W_NEB_RUNAWAY=1e3 is first threshold — calibrate after stable runs",
        ],
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    print("=" * 60)
    print("TEST18 — SUMMARY")
    print("=" * 60)
    print(f"Architecture clean: {architecture_clean}")
    print("Formation state counts:")
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
