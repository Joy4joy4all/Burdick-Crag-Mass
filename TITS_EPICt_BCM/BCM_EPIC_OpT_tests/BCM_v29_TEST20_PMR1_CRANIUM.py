# -*- coding: utf-8 -*-
"""
BCM v29 TEST20 — PMR 1 / EXPOSED CRANIUM NEBULA HYBRID EDGE CASE
=================================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Adversarial basis: ChatGPT post-Test19 analysis + ESA/JWST PMR 1 data.
Equation form:     Gemini engineering formalization channel.
Code execution:    The code builder.

Purpose:
    Test whether Variant 2 with the confirmed saturation kernel correctly
    handles a real hybrid nebular object: PMR 1 / Exposed Cranium Nebula
    (PN G272.8+01.0). This object does not fit any single clean class.
    It bridges SHOCK_INSCRIPTION, POST_PUMP_SHELL, and SCATTER_MEMORY
    simultaneously.

PMR 1 OBSERVATIONAL BASIS (JWST NIRCam + MIRI, February 2026):
    Distance:     ~5,000 ly (Vela constellation)
    Diameter:     ~3.2 ly (~2.2 arcminutes)
    Morphology:   Two-hemisphere brain structure split by a sharp vertical
                  dark lane. Outer hydrogen shell overlays asymmetric inner
                  cloud of heavier elements. Material erupting at northern
                  pole with weaker mirrored feature at southern pole.
    Central engine: High mass-loss stellar core with Wolf-Rayet-like
                  signatures [WC4:] — endpoint UNCERTAIN per ESA/NASA.
                  Cannot confirm Wolf-Rayet supernova progenitor vs
                  ordinary planetary-nebula white-dwarf pathway.
                  Use: "candidate high mass-loss engine, endpoint uncertain."
    Sources: ESA JWST multimedia release, Space.com analysis.

COMPONENT VECTOR [D_dust, C_cool, S_shock, I_ion, G_grad]:
    D_dust  = 0.85  (strong dark-lane dust memory holds skull boundary)
    C_cool  = 0.60  (moderate cooling / dense lane retention)
    S_shock = 0.90  (strong bipolar/polar outflow inscription)
    I_ion   = 0.75  (strong ionization from high mass-loss central engine)
    G_grad  = 0.30  (weak global gravitational condensation — shell geometry)

HYBRID OPERATOR (ChatGPT formalization, SJB direction):
    PMR 1 is NOT a single-class object. It requires a weighted blend:

    F_hybrid = 0.45 * F_shock + 0.35 * F_shell + 0.20 * F_scatter

    Where (using Test19 class operators):
      F_shock   = S * (0.5*C + 0.5*G)        = 0.90 * 0.45 = 0.405
      F_shell   = D * I                       = 0.85 * 0.75 = 0.6375
      F_scatter = D * G * (1 - I)             = 0.85 * 0.30 * 0.25 = 0.06375
      F_hybrid  = 0.45*0.405 + 0.35*0.6375 + 0.20*0.06375
               ≈ 0.182 + 0.223 + 0.013 = 0.418

EXPECTED BEHAVIOR:
    The dark lane should drive early BARYONIC_CONDENSATION locally.
    The polar eruption should drive SHOCK_INSCRIPTION_ACTIVE at boundary.
    The outer shell should hold as POST_PUMP_SHELL_MEMORY.
    The hybrid blend should land in HYBRID_SHOCK_SHELL_ACTIVE — bounded,
    not runaway, with significant baryonic consumption from dark lane.

NEW STATES FOR HYBRID CLASS:
    HYBRID_SHOCK_SHELL_ACTIVE         governed growth, all three mechanisms active
    HYBRID_SHELL_INSCRIPTION          shell memory + active shock writing
    HYBRID_CONDENSATION_ACTIVE        dark lane dominating, shell holding

Test sequence context:
    Test16: architecture (non-pump lane proved)
    Test17: real targets, universal product too punishing
    Test18: class operators, fractional space had no brakes
    Test19: saturation kernel confirmed, zero cap escapes
    Test20: hybrid edge case — PMR 1 Exposed Cranium (THIS TEST)
    Next:   Crag Tier Batch Sweep on stabilized Variant 2 infrastructure
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

from bcm_thresholds import KAPPA_CMB, LAMBDA_DECAY

# ── Constants (same as Test19) ────────────────────────────────────────────────
XI_S            = 0.0
T2_ACTIVE       = False
T3_ACTIVE       = False
SIGMA_CMB_BG    = 0.01
SIGMA_FORM_CRIT = 0.05
SIGMA_FORM_CAP  = 1.0
N_STEPS         = 2000
N_R             = 64
DT              = 0.01
ETA_ION_BLOWOUT = 0.5    # PLACEHOLDER

GROWTH_ACTIVE_MIN = 1.25
GROWTH_STASIS_LO  = 0.90

# ── PMR 1 target definition ───────────────────────────────────────────────────
PMR1_TARGET = {
    "target_name":  "PMR_1_CRANIUM",
    "nebula_class": "HYBRID_SHOCK_SHELL",
    "components":   [0.85, 0.60, 0.90, 0.75, 0.30],
    "hybrid_weights": [0.45, 0.35, 0.20],   # shock, shell, scatter
    "observational_basis": (
        "JWST NIRCam+MIRI 2026. PN G272.8+01.0. ~5000 ly, Vela. ~3.2 ly diameter. "
        "Outer H shell, asymmetric inner cloud (heavy elements), vertical dark lane, "
        "polar eruption N stronger than S. Central engine: candidate high mass-loss "
        "[WC4:] Wolf-Rayet-like signatures — endpoint UNCERTAIN (ESA/NASA). "
        "May produce white dwarf not supernova. Do NOT hard-classify as confirmed "
        "Wolf-Rayet supernova progenitor."
    ),
}

# Also run the five Test19 targets for baseline comparison
COMPARISON_TARGETS = [
    {
        "target_name":  "CHAMAELEON_I",
        "nebula_class": "DARK_CONDENSATE",
        "components":   [1.00, 0.95, 0.00, 0.00, 0.85],
    },
    {
        "target_name":  "HH_211",
        "nebula_class": "SHOCK_INSCRIPTION",
        "components":   [0.50, 0.70, 1.00, 0.10, 0.45],
    },
    {
        "target_name":  "NGC_3132",
        "nebula_class": "POST_PUMP_SHELL",
        "components":   [0.85, 0.50, 0.30, 0.75, 0.20],
    },
]


def class_operator(nebula_class: str,
                   comp: List[float],
                   hybrid_weights: List[float] = None) -> Dict[str, Any]:
    """Class-specific and hybrid F_form operators."""
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
                "f_form_net": drive - blowout}

    elif nebula_class == "SHOCK_INSCRIPTION":
        return {"operator": "F_shock = S*(0.5*C + 0.5*G)",
                "f_form_net": S * (0.5 * C + 0.5 * G)}

    elif nebula_class == "POST_PUMP_SHELL":
        return {"operator": "F_shell = D*I",
                "f_form_net": D * I}

    elif nebula_class == "HYBRID_SHOCK_SHELL":
        w_shock, w_shell, w_scatter = hybrid_weights or [0.45, 0.35, 0.20]
        f_shock   = S * (0.5 * C + 0.5 * G)
        f_shell   = D * I
        f_scatter = D * G * (1.0 - I)
        f_hybrid  = w_shock * f_shock + w_shell * f_shell + w_scatter * f_scatter
        return {
            "operator": "F_hybrid = 0.45*F_shock + 0.35*F_shell + 0.20*F_scatter",
            "f_form_net":  round(f_hybrid, 6),
            "f_shock":     round(f_shock, 6),
            "f_shell":     round(f_shell, 6),
            "f_scatter":   round(f_scatter, 6),
            "w_shock":     w_shock,
            "w_shell":     w_shell,
            "w_scatter":   w_scatter,
        }
    return {"operator": "UNKNOWN", "f_form_net": 0.0}


def classify(nebula_class: str, growth_ratio: float,
             sigma_final_mean: float, baryonic_total: float,
             f_net: float, nan_flag: bool, inf_flag: bool) -> str:
    if nan_flag or inf_flag:
        return "NUMERICAL_FAILURE"
    if f_net <= 0.0:
        return "IONIZED_BLOWOUT" if nebula_class == "IONIZED_FORMATION" \
               else "F_FORM_ZERO_NO_DRIVE"
    if sigma_final_mean > SIGMA_FORM_CAP:
        return "FORMATION_RUNAWAY"

    if nebula_class == "HYBRID_SHOCK_SHELL":
        if growth_ratio > GROWTH_ACTIVE_MIN and baryonic_total > 0:
            return "HYBRID_SHOCK_SHELL_ACTIVE"
        elif growth_ratio > GROWTH_ACTIVE_MIN:
            return "HYBRID_CONDENSATION_ACTIVE"
        elif growth_ratio >= GROWTH_STASIS_LO:
            return "HYBRID_SHELL_INSCRIPTION"
        else:
            return "HYBRID_DECAYING"

    if growth_ratio > GROWTH_ACTIVE_MIN and baryonic_total > 0:
        if nebula_class == "SHOCK_INSCRIPTION":
            return "SHOCK_INSCRIPTION_ACTIVE"
        if nebula_class == "POST_PUMP_SHELL":
            return "POST_PUMP_SHELL_MEMORY"
        return "BARYONIC_CONDENSATION"
    if growth_ratio > GROWTH_ACTIVE_MIN:
        return "FORMATION_ACTIVE_STABLE"
    if growth_ratio >= GROWTH_STASIS_LO:
        if nebula_class == "SCATTER_MEMORY":
            return "SCATTER_MEMORY_ACTIVE"
        if nebula_class == "POST_PUMP_SHELL":
            return "POST_PUMP_SHELL_MEMORY"
        return "FORMATION_MEMORY_STASIS"
    return "FORMATION_DECAY"


def run_target(target: Dict[str, Any]) -> Dict[str, Any]:
    name  = target["target_name"]
    cls   = target["nebula_class"]
    comp  = target["components"]
    hw    = target.get("hybrid_weights", None)
    D, C, S, I, G = comp

    op_info = class_operator(cls, comp, hw)
    f_net   = op_info["f_form_net"]
    f_safe  = max(f_net, 0.0)

    r     = np.linspace(0, 1, N_R)
    sigma = np.exp(-((r - 0.5) ** 2) / (2 * 0.1 ** 2)) * 0.1
    sigma_initial_mean = float(sigma.mean())

    I_CMB = KAPPA_CMB * SIGMA_CMB_BG

    delta_w        = 0.0
    baryonic_accum = 0.0
    sigma_track    = [sigma_initial_mean]
    nan_flag = False
    inf_flag = False

    for step in range(N_STEPS):
        sigma_eff = sigma * f_safe + KAPPA_CMB * SIGMA_CMB_BG
        phi_form  = np.clip(sigma_eff / SIGMA_FORM_CRIT, 0.0, 1.0)

        # Dynamic saturation kernel — live sigma
        saturation_kernel = np.clip(1.0 - sigma / SIGMA_FORM_CAP, 0.0, 1.0)

        # T1 with saturation
        T1 = sigma_eff * phi_form * saturation_kernel

        # T5 drain — NOT saturated
        T5 = LAMBDA_DECAY * sigma

        # Drive
        formation_work = T1 * f_safe
        cmb_bias       = I_CMB * sigma_eff
        d_sigma        = formation_work + cmb_bias - T5

        # G_grad diffusion
        lap = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        d_sigma += G * 0.01 * lap

        sigma = np.clip(sigma + DT * d_sigma, 0.0, None)

        # Baryonic consumption
        baryonic_step   = float(np.sum(
            f_safe * (1.0 - saturation_kernel) * np.abs(d_sigma)
        ))
        baryonic_accum += baryonic_step
        delta_w        += float(np.sum(np.abs(d_sigma)))

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

    result = {
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
    }
    if "observational_basis" in target:
        result["observational_basis"] = target["observational_basis"]
    return result


def run_test():
    print("BCM v29 TEST20 — PMR 1 EXPOSED CRANIUM NEBULA HYBRID EDGE CASE")
    print(f"Backend: {_BACKEND}")
    print(f"Xi_S={XI_S} | T2={T2_ACTIVE} | T3={T3_ACTIVE}")
    print(f"SIGMA_FORM_CAP={SIGMA_FORM_CAP} | RUNAWAY = cap escape only")
    print()

    all_targets = [PMR1_TARGET] + COMPARISON_TARGETS
    results = []
    state_counts: Dict[str, int] = {}
    architecture_clean = True
    cap_escapes = 0

    for target in all_targets:
        r = run_target(target)
        if r["nan_detected"] or r["inf_detected"]:
            architecture_clean = False
        if r["cap_escaped"]:
            cap_escapes += 1
        st = r["formation_state"]
        state_counts[st] = state_counts.get(st, 0) + 1

        primary = "*** PRIMARY TARGET ***" \
                  if target["target_name"] == "PMR_1_CRANIUM" else ""
        print(f"{r['target_name']} ({r['nebula_class']}) {primary}")
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

    # ── PMR 1 specific read ───────────────────────────────────────────────────
    pmr1_result = results[0]
    pmr1_state  = pmr1_result["formation_state"]

    # ── verdict ───────────────────────────────────────────────────────────────
    if not architecture_clean:
        verdict  = "ARCHITECTURE_FAILURE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_FAILED"]
    elif pmr1_result["cap_escaped"]:
        verdict  = "PMR1_CAP_ESCAPED__SATURATION_INSUFFICIENT"
        hyp_keys = ["H_V29_NEBULAR_SATURATION_KERNEL_FAILED"]
    elif pmr1_state in ("HYBRID_SHOCK_SHELL_ACTIVE",
                        "HYBRID_CONDENSATION_ACTIVE",
                        "HYBRID_SHELL_INSCRIPTION"):
        if cap_escapes == 0:
            verdict  = "PMR1_HYBRID_CONFIRMED__SATURATION_HOLDS"
            hyp_keys = ["H_V29_NEBULAR_SATURATION_KERNEL",
                        "H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
                        "H_V29_DARK_CONDENSATE",
                        "H_V29_SHOCK_INSCRIPTION",
                        "H_V29_PMR1_HYBRID_EDGE_CASE"]
        else:
            verdict  = "PMR1_HYBRID_ACTIVE__OTHER_CAP_ESCAPES"
            hyp_keys = ["H_V29_NEBULAR_SATURATION_KERNEL",
                        "H_V29_PMR1_HYBRID_EDGE_CASE"]
    else:
        verdict  = f"PMR1_STATE_{pmr1_state}__INVESTIGATE"
        hyp_keys = ["H_V29_PMR1_HYBRID_EDGE_CASE"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST20_PMR1_CRANIUM_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST20",
        "test_name": "PMR1_EXPOSED_CRANIUM_HYBRID_EDGE_CASE",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",
        "backend":   _BACKEND,

        "variant":   "NEBULAR_V2",
        "xi_s":      XI_S,
        "t2_active": T2_ACTIVE,
        "t3_active": T3_ACTIVE,

        "kappa_cmb":       KAPPA_CMB,
        "sigma_form_cap":  SIGMA_FORM_CAP,
        "sigma_form_crit": SIGMA_FORM_CRIT,
        "lambda_decay":    LAMBDA_DECAY,

        "pmr1_central_engine_note": (
            "Central engine endpoint UNCERTAIN per ESA/NASA. "
            "Wolf-Rayet [WC4:] signatures observed but white-dwarf "
            "pathway not excluded. Do NOT classify as confirmed "
            "supernova progenitor."
        ),

        "pmr1_result":           pmr1_result,
        "comparison_results":    results[1:],
        "all_results":           results,
        "formation_state_counts": state_counts,
        "cap_escapes":           cap_escapes,
        "architecture_clean":    architecture_clean,

        "verdict":        verdict,
        "hypothesis_keys": hyp_keys,

        "test_sequence_note": (
            "Test16: arch proved. Test17: real targets, product too punishing. "
            "Test18: class operators active. Test19: saturation confirmed. "
            "Test20: PMR1 hybrid edge case. Next: Crag Tier Batch Sweep."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    print("=" * 60)
    print("TEST20 — SUMMARY")
    print("=" * 60)
    print(f"PMR 1 formation state: {pmr1_state}")
    print(f"Architecture clean:    {architecture_clean}")
    print(f"Cap escapes:           {cap_escapes}")
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
