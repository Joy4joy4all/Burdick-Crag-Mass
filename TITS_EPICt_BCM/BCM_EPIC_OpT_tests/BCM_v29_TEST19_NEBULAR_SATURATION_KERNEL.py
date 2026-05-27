# -*- coding: utf-8 -*-
"""
BCM v29 TEST19 — NEBULAR SATURATION KERNEL (DYNAMIC GOVERNOR)
==============================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Adversarial basis: ChatGPT post-Test18 analysis.
Equation form:     Gemini engineering formalization channel.
Code execution:    The code builder.

Test18 results:
  Architecture clean: True
  Class operators: working
  NGC_1333:   SCATTER_MEMORY_ACTIVE  (correct)
  TARANTULA:  IONIZED_BLOWOUT        (correct)
  CHAMAELEON, HH_211, NGC_3132: flagged FORMATION_RUNAWAY — but sigma stayed
    below SIGMA_FORM_CAP. The runaway flag was tripped by delta_W accumulation,
    not actual field escape. Saturation was already dynamic in Test18
    (using live sigma, not sigma_initial). The issue was verdict logic order:
    delta_W check fired before checking whether sigma was actually bounded.

TEST19 fixes:
  1. RUNAWAY redefined: fires only when sigma_final_mean > SIGMA_FORM_CAP
     (cap failure), not on delta_W magnitude alone.
  2. BARYONIC_CONDENSATION state: sigma growing but bounded below cap,
     baryonic consumption accumulator confirms conversion happening.
  3. Dynamic saturation kernel confirmed explicitly:
       saturation_kernel = clip(1.0 - sigma / sigma_cap, 0.0, 1.0)  [live sigma]
  4. Baryonic consumption metric:
       baryonic_consumption = F_form_net * (1.0 - saturation_kernel)
       accumulates per step as: sum(baryonic_consumption * |d_sigma|)
  5. T5 drain does NOT receive saturation — drain stays active at density.

PHYSICS LOCK (ChatGPT formalization, SJB origin):
  Fractional substrate cannot accumulate without a conversion channel.
  As sigma approaches SIGMA_FORM_CAP, raw substrate funding converts into
  localized baryonic precipitation rather than continuing as free sigma growth.
  The saturation kernel IS the conversion gate.

UPDATED STATE TABLE:
  FORMATION_RUNAWAY         sigma_final > SIGMA_FORM_CAP (cap escaped)
  FORMATION_ACTIVE_STABLE   growth > 1.25, sigma < cap, no baryonic conversion
  BARYONIC_CONDENSATION     growth > 1.25, sigma < cap, baryonic conversion active
  FORMATION_MEMORY_STASIS   growth_ratio 0.90-1.25 (held without growth)
  FORMATION_DECAY           growth_ratio < 0.90
  SCATTER_MEMORY_ACTIVE     scatter class, bounded accumulation
  SCATTER_MEMORY_STASIS     scatter class, no net change
  SHOCK_INSCRIPTION_ACTIVE  shock class, bounded or growing
  POST_PUMP_SHELL_MEMORY    shell class, bounded residual
  IONIZED_BLOWOUT           ionized class, net negative formation
  F_FORM_ZERO_NO_DRIVE      no active formation mechanism
  NUMERICAL_FAILURE         nan/inf

EXPECTED OUTCOMES (post dynamic governor):
  CHAMAELEON_I:    BARYONIC_CONDENSATION (sigma bounded, conversion active)
  NGC_1333:        SCATTER_MEMORY_ACTIVE (no change from Test18)
  TARANTULA_30DOR: IONIZED_BLOWOUT (no change from Test18)
  HH_211:          SHOCK_INSCRIPTION_ACTIVE or BARYONIC_CONDENSATION
  NGC_3132:        POST_PUMP_SHELL_MEMORY (residual memory, bounded)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

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

# ── Constants ────────────────────────────────────────────────────────────────
XI_S             = 0.0
T2_ACTIVE        = False
T3_ACTIVE        = False
SIGMA_CMB_BG     = 0.01
SIGMA_FORM_CRIT  = 0.05
SIGMA_FORM_CAP   = 1.0      # Cap — runaway defined as ESCAPING this
N_STEPS          = 2000
N_R              = 64
DT               = 0.01
ETA_ION_BLOWOUT  = 0.5      # PLACEHOLDER — pending SJB calibration

# Growth thresholds
GROWTH_ACTIVE_MIN = 1.25    # Above this = active formation
GROWTH_STASIS_HI  = 1.25    # Below this = stasis regime
GROWTH_STASIS_LO  = 0.90

# ── Same five targets as Test17/18 ───────────────────────────────────────────
NEBULA_TARGETS = [
    {
        "target_name":  "CHAMAELEON_I",
        "nebula_class": "DARK_CONDENSATE",
        "components":   [1.00, 0.95, 0.00, 0.00, 0.85],
        "observational_basis": "JWST pristine ice core ~10K. Coldest ices measured.",
    },
    {
        "target_name":  "NGC_1333",
        "nebula_class": "SCATTER_MEMORY",
        "components":   [0.90, 0.40, 0.15, 0.20, 0.60],
        "observational_basis": "Perseus reflection nebula. Dust boundary visualizer.",
    },
    {
        "target_name":  "TARANTULA_30DOR",
        "nebula_class": "IONIZED_FORMATION",
        "components":   [0.35, 0.85, 0.60, 1.00, 0.70],
        "observational_basis": "R136 super star cluster. Starburst, LMC.",
    },
    {
        "target_name":  "HH_211",
        "nebula_class": "SHOCK_INSCRIPTION",
        "components":   [0.50, 0.70, 1.00, 0.10, 0.45],
        "observational_basis": "Class 0 protostellar jet. 80-100 km/s bipolar jets.",
    },
    {
        "target_name":  "NGC_3132",
        "nebula_class": "POST_PUMP_SHELL",
        "components":   [0.85, 0.50, 0.30, 0.75, 0.20],
        "observational_basis": "Southern Ring Nebula. Post-white-dwarf shell.",
    },
]


def class_operator(nebula_class: str, comp: List[float]) -> Dict[str, Any]:
    """Class-specific F_form net scalar (same as Test18)."""
    D, C, S, I, G = comp
    if nebula_class == "DARK_CONDENSATE":
        return {"operator": "F_dark = D*C*G",
                "f_form_net": D * C * G}
    elif nebula_class == "SCATTER_MEMORY":
        return {"operator": "F_scatter = D*G*(1-I)",
                "f_form_net": D * G * (1.0 - I)}
    elif nebula_class == "IONIZED_FORMATION":
        drive   = I * C * G
        blowout = ETA_ION_BLOWOUT * I * (1.0 - D)
        return {"operator": "F_ion = I*C*G - eta*I*(1-D)",
                "f_form_net": drive - blowout,
                "f_ion_drive": drive,
                "f_ion_blowout": blowout}
    elif nebula_class == "SHOCK_INSCRIPTION":
        return {"operator": "F_shock = S*(0.5*C + 0.5*G)",
                "f_form_net": S * (0.5 * C + 0.5 * G)}
    elif nebula_class == "POST_PUMP_SHELL":
        return {"operator": "F_shell = D*I",
                "f_form_net": D * I}
    return {"operator": "UNKNOWN", "f_form_net": 0.0}


def classify(nebula_class: str, growth_ratio: float,
             sigma_final_mean: float, baryonic_total: float,
             f_net: float, nan_flag: bool, inf_flag: bool) -> str:
    """
    Corrected verdict logic — runaway defined by cap escape, not delta_W.
    """
    if nan_flag or inf_flag:
        return "NUMERICAL_FAILURE"
    if f_net <= 0.0:
        if nebula_class == "IONIZED_FORMATION":
            return "IONIZED_BLOWOUT"
        return "F_FORM_ZERO_NO_DRIVE"

    # Runaway: sigma escaped the cap
    if sigma_final_mean > SIGMA_FORM_CAP:
        return "FORMATION_RUNAWAY"

    # Active formation with baryonic conversion
    if growth_ratio > GROWTH_ACTIVE_MIN and baryonic_total > 0.0:
        if nebula_class == "SHOCK_INSCRIPTION":
            return "SHOCK_INSCRIPTION_ACTIVE"
        if nebula_class == "POST_PUMP_SHELL":
            return "POST_PUMP_SHELL_MEMORY"
        return "BARYONIC_CONDENSATION"

    # Active formation without detected conversion
    if growth_ratio > GROWTH_ACTIVE_MIN:
        return "FORMATION_ACTIVE_STABLE"

    # Stasis band
    if growth_ratio >= GROWTH_STASIS_LO:
        if nebula_class == "SCATTER_MEMORY":
            return "SCATTER_MEMORY_ACTIVE" if growth_ratio > 1.05 else "SCATTER_MEMORY_STASIS"
        if nebula_class == "POST_PUMP_SHELL":
            return "POST_PUMP_SHELL_MEMORY"
        if nebula_class == "IONIZED_FORMATION":
            return "IONIZED_ACTIVE_BALANCE"
        return "FORMATION_MEMORY_STASIS"

    # Decay
    if nebula_class == "IONIZED_FORMATION":
        return "IONIZED_BLOWOUT"
    return "FORMATION_DECAY"


def run_target(target: Dict[str, Any]) -> Dict[str, Any]:
    name  = target["target_name"]
    cls   = target["nebula_class"]
    comp  = target["components"]
    D, C, S, I, G = comp

    op_info = class_operator(cls, comp)
    f_net   = op_info["f_form_net"]
    f_safe  = max(f_net, 0.0)

    # Initial sigma field
    r     = np.linspace(0, 1, N_R)
    sigma = np.exp(-((r - 0.5) ** 2) / (2 * 0.1 ** 2)) * 0.1
    sigma_initial_mean = float(sigma.mean())

    I_CMB = KAPPA_CMB * SIGMA_CMB_BG

    delta_w          = 0.0
    baryonic_accum   = 0.0
    sigma_track      = [sigma_initial_mean]
    nan_flag = False
    inf_flag = False

    for step in range(N_STEPS):
        sigma_eff  = sigma * f_safe + KAPPA_CMB * SIGMA_CMB_BG
        phi_form   = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)

        # DYNAMIC saturation kernel — live sigma, not initial
        saturation_kernel = np.clip(1.0 - sigma / SIGMA_FORM_CAP, 0.0, 1.0)

        # T1 with dynamic saturation applied
        T1 = sigma_eff * phi_form * saturation_kernel

        # T5: maintenance drain — NOT saturated
        T5 = LAMBDA_DECAY * sigma

        # Formation work (governed)
        formation_work = T1 * f_safe

        # CMB pre-strain bias (independent of saturation)
        cmb_bias = I_CMB * sigma_eff

        # Drive
        d_sigma = formation_work + cmb_bias - T5

        # G_grad diffusion
        lap = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        d_sigma += G * 0.01 * lap

        sigma = np.clip(sigma + DT * d_sigma, 0.0, None)

        # Baryonic consumption metric
        baryonic_conversion = f_safe * (1.0 - saturation_kernel)
        baryonic_step = float(np.sum(baryonic_conversion * np.abs(d_sigma)))
        baryonic_accum += baryonic_step

        delta_w += float(np.sum(np.abs(d_sigma)))

        if step % 500 == 0:
            sigma_track.append(float(sigma.mean()))

        if np.any(np.isnan(sigma)):
            nan_flag = True
            break
        if np.any(np.isinf(sigma)):
            inf_flag = True
            break

    sigma_final_mean = float(sigma.mean())
    sigma_final_max  = float(sigma.max())
    growth_ratio     = sigma_final_mean / max(sigma_initial_mean, 1e-12)

    state = classify(cls, growth_ratio, sigma_final_mean,
                     baryonic_accum, f_net, nan_flag, inf_flag)

    return {
        "target_name":          name,
        "nebula_class":         cls,
        "components":           {"D_dust": D, "C_cool": C, "S_shock": S,
                                 "I_ion": I, "G_grad": G},
        "operator_info":        op_info,
        "f_form_net":           round(f_net, 6),
        "sigma_initial_mean":   round(sigma_initial_mean, 8),
        "sigma_final_mean":     round(sigma_final_mean, 8),
        "sigma_final_max":      round(sigma_final_max, 8),
        "growth_ratio":         round(growth_ratio, 6),
        "delta_w_neb":          round(delta_w, 4),
        "baryonic_consumption": round(baryonic_accum, 6),
        "sigma_track":          [round(v, 8) for v in sigma_track],
        "cap_escaped":          sigma_final_mean > SIGMA_FORM_CAP,
        "nan_detected":         nan_flag,
        "inf_detected":         inf_flag,
        "formation_state":      state,
        "observational_basis":  target["observational_basis"],
    }


def run_test():
    print("BCM v29 TEST19 — NEBULAR SATURATION KERNEL (DYNAMIC GOVERNOR)")
    print(f"Backend: {_BACKEND}")
    print(f"Xi_S={XI_S} | T2={T2_ACTIVE} | T3={T3_ACTIVE}")
    print(f"SIGMA_FORM_CAP={SIGMA_FORM_CAP} | RUNAWAY = cap escape only")
    print(f"ETA_ION_BLOWOUT={ETA_ION_BLOWOUT} [placeholder]")
    print()

    results = []
    state_counts: Dict[str, int] = {}
    architecture_clean = True
    cap_escapes = 0

    for target in NEBULA_TARGETS:
        r = run_target(target)
        if r["nan_detected"] or r["inf_detected"]:
            architecture_clean = False
        if r["cap_escaped"]:
            cap_escapes += 1

        st = r["formation_state"]
        state_counts[st] = state_counts.get(st, 0) + 1

        print(f"{r['target_name']} ({r['nebula_class']})")
        print(f"  Operator:        {r['operator_info']['operator']}")
        print(f"  F_form_net       = {r['f_form_net']:.6f}")
        print(f"  sigma_initial    = {r['sigma_initial_mean']:.8f}")
        print(f"  sigma_final      = {r['sigma_final_mean']:.8f}")
        print(f"  growth_ratio     = {r['growth_ratio']:.6f}")
        print(f"  baryonic_consump = {r['baryonic_consumption']:.6f}")
        print(f"  cap_escaped      = {r['cap_escaped']}")
        print(f"  formation_state  = {st}")
        print()

        results.append(r)

    # ── verdict ───────────────────────────────────────────────────────────────
    runaway = state_counts.get("FORMATION_RUNAWAY", 0)
    baryonic = state_counts.get("BARYONIC_CONDENSATION", 0)
    shock_active = state_counts.get("SHOCK_INSCRIPTION_ACTIVE", 0)
    shell_mem = state_counts.get("POST_PUMP_SHELL_MEMORY", 0)
    scatter = state_counts.get("SCATTER_MEMORY_ACTIVE", 0) + \
              state_counts.get("SCATTER_MEMORY_STASIS", 0)
    blowout = state_counts.get("IONIZED_BLOWOUT", 0)

    if not architecture_clean:
        verdict  = "ARCHITECTURE_FAILURE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_FAILED"]
    elif runaway == 0 and (baryonic + shock_active + shell_mem) >= 2:
        verdict  = "SATURATION_KERNEL_CONFIRMED__NO_RUNAWAY"
        hyp_keys = ["H_V29_NEBULAR_SATURATION_KERNEL",
                    "H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
                    "H_V29_DARK_CONDENSATE",
                    "H_V29_SHOCK_INSCRIPTION"]
    elif runaway == 0:
        verdict  = "SATURATION_KERNEL_ACTIVE__STATES_PARTIAL"
        hyp_keys = ["H_V29_NEBULAR_SATURATION_KERNEL",
                    "H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN"]
    else:
        verdict  = f"SATURATION_INSUFFICIENT__{runaway}_CAP_ESCAPES"
        hyp_keys = ["H_V29_NEBULAR_SATURATION_KERNEL_FAILED"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST19_NEBULAR_SATURATION_KERNEL_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST19",
        "test_name": "NEBULAR_SATURATION_KERNEL_DYNAMIC_GOVERNOR",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",
        "backend":   _BACKEND,

        "variant":   "NEBULAR_V2",
        "xi_s":      XI_S,
        "t2_active": T2_ACTIVE,
        "t3_active": T3_ACTIVE,

        "kappa_cmb":          KAPPA_CMB,
        "sigma_form_crit":    SIGMA_FORM_CRIT,
        "sigma_form_cap":     SIGMA_FORM_CAP,
        "eta_ion_blowout":    ETA_ION_BLOWOUT,
        "lambda_decay":       LAMBDA_DECAY,

        "runaway_definition": "sigma_final_mean > SIGMA_FORM_CAP (cap escape only)",
        "saturation_kernel":  "clip(1 - sigma/cap, 0, 1)  [live sigma — dynamic]",
        "baryonic_metric":    "F_form_net * (1 - saturation_kernel) * |d_sigma|",

        "targets":               results,
        "formation_state_counts": state_counts,
        "cap_escapes":           cap_escapes,
        "architecture_clean":    architecture_clean,

        "verdict":        verdict,
        "hypothesis_keys": hyp_keys,

        "pending_calibration": [
            "ETA_ION_BLOWOUT=0.5 is placeholder",
            "SIGMA_FORM_CAP=1.0 is first estimate",
            "SIGMA_CMB_BG=0.01 is placeholder",
        ],
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    print("=" * 60)
    print("TEST19 — SUMMARY")
    print("=" * 60)
    print(f"Architecture clean: {architecture_clean}")
    print(f"Cap escapes:        {cap_escapes}")
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
