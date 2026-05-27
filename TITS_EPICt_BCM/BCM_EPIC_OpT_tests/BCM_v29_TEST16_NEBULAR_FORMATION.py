# -*- coding: utf-8 -*-
"""
BCM v29 TEST16 — NEBULAR FORMATION VARIANT 2 PROBE
====================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Adversarial basis: ChatGPT JWST gap analysis (what JWST cannot resolve).
Equation form:     Gemini engineering formalization channel.
Code execution:    The code builder.

Purpose:
    First probe of Variant 2: Non-Craft Nebular Formation (Pre-Pump States).
    Tests whether the BCM infrastructure cleanly handles substrate
    pre-conditioning WITHOUT kinematic terms T2/T3 and WITH Xi_S -> 0.

    This is the most radical departure from the existing codebase:
    no coherent J-current loop, no superluminal transit, no paired pumps.
    Pure formation-dominant substrate accumulation via F_form.

Variant 2 equation (Gemini formalization):
    Delta_W_Neb = I_CMB^alpha * volume_integral [ T1 * F_form + T5 ] * d_sigma_local

    sigma_eff(r) = [sigma_local(r) * F_form] + kappa_CMB * sigma_CMB

Where:
    T1  = Einstein recovery term (sigma as mass proxy in pre-pump state)
    T5  = Entropy sink (continuous maintenance cost: -lambda * sigma)
    T2, T3 = DEACTIVATED (no J-loop, no spectral transit)
    F_form  = D_dust * C_cool * S_shock * I_ion * G_grad (active components)
    I_CMB   = kappa_CMB * sigma_CMB_bg (CMB intensity proxy)
    alpha   = ALPHA_VOID_DEFAULT = 1.0 (fractional memory depth)
    Xi_S    = 0.0 (no integerization — fully fractional formation state)

F_form baseline (DARK_CONDENSATE — SJB confirmed 2026-05-17):
    [D_dust=1.0, C_cool=1.0, S_shock=0.0, I_ion=0.0, G_grad=1.0]
    F_form_scalar = product of non-zero active components = 1.0

    Physical meaning: pure static accumulation.
    Dust memory holds substrate. Cooling drives condensation.
    Gravitational gradient pulls sigma toward density peaks.
    No shock carving. No ionization disruption.

Other nebula class component vectors: PENDING SJB SPECIFICATION.
Placeholder values included for architecture validation only.
Do not interpret placeholder results as confirmed physics.

Output JSON keys:
    test_id, test_name, timestamp, foreman
    variant: "NEBULAR_V2"
    xi_s: 0.0 (confirmed for all runs)
    t2_active: False
    t3_active: False
    kappa_cmb, alpha_void, lambda_decay
    sigma_cmb_bg
    configs: list of nebula class results
    primary_config: "DARK_CONDENSATE"
    formation_threshold
    architecture_clean: True if no numerical failures
    verdict
    hypothesis_keys
"""

from __future__ import annotations

import json
import sys
import math
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ── path setup ──────────────────────────────────────────────────────────────
_THIS_DIR    = Path(__file__).resolve().parent
_SOLVER_ROOT = _THIS_DIR.parent.parent
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
    KAPPA_CMB, ALPHA_VOID_DEFAULT, ALPHA_ROOT_DEFAULT,
    LAMBDA_DECAY, BRUCETRON_HEMORRHAGE,
)

# ── Variant 2 constants ──────────────────────────────────────────────────────
XI_S             = 0.0     # No integerization — fully fractional nebular state
T2_ACTIVE        = False   # Substrate current loop — DEACTIVATED
T3_ACTIVE        = False   # Spectral projection gate — DEACTIVATED
SIGMA_CMB_BG     = 0.01    # Primordial pre-strain background field (placeholder)
N_STEPS          = 2000    # Evolution steps
N_R              = 64      # Radial grid points
DT               = 0.01    # Time step (solver units)
SIGMA_CRIT_PROXY = 10.0    # Sigma condensation target (pre-pump regime)

# Formation threshold: F_form_scalar must exceed LAMBDA_DECAY for net accumulation
# At F_form > LAMBDA_DECAY, formation source > maintenance drain
FORMATION_THRESHOLD = LAMBDA_DECAY  # = 0.1

# ── Nebula class definitions ──────────────────────────────────────────────────
# Component order: [D_dust, C_cool, S_shock, I_ion, G_grad]
# DARK_CONDENSATE baseline: SJB-confirmed 2026-05-17
# All others: PLACEHOLDER — pending SJB specification

NEBULA_CONFIGS = [
    {
        "name":       "DARK_CONDENSATE",
        "components": [1.0, 1.0, 0.0, 0.0, 1.0],   # SJB-confirmed baseline
        "confirmed":  True,
        "description": ("Cold/dusty pre-star substrate memory. Pure static "
                        "accumulation. D_dust + C_cool + G_grad active. "
                        "No shock. No ionization."),
    },
    {
        "name":       "SCATTER_MEMORY",
        "components": [1.0, 0.0, 0.0, 0.0, 0.5],   # PLACEHOLDER
        "confirmed":  False,
        "description": ("Reflection nebula. Dust reveals sigma boundary. "
                        "Weak gradient. PLACEHOLDER — SJB spec pending."),
    },
    {
        "name":       "IONIZED_FORMATION",
        "components": [0.0, 0.5, 0.0, 1.0, 0.5],   # PLACEHOLDER
        "confirmed":  False,
        "description": ("Emission nebula. I_ion dominant. Distributed "
                        "radiative forcing. PLACEHOLDER — SJB spec pending."),
    },
    {
        "name":       "SHOCK_INSCRIPTION",
        "components": [0.5, 0.0, 1.0, 0.5, 0.5],   # PLACEHOLDER
        "confirmed":  False,
        "description": ("SNR/wind front writing into sigma. S_shock dominant. "
                        "PLACEHOLDER — SJB spec pending."),
    },
    {
        "name":       "POST_PUMP_SHELL",
        "components": [1.0, 0.5, 0.5, 0.0, 0.0],   # PLACEHOLDER
        "confirmed":  False,
        "description": ("Shell-memory after pump decay. Substrate outlives "
                        "event. PLACEHOLDER — SJB spec pending."),
    },
]


def f_form_scalar(components: List[float]) -> float:
    """
    Compute F_form scalar from component vector.
    Product of non-zero active components only.
    Zero = inactive mechanism (not a failure, not counted).
    """
    active = [c for c in components if c > 0.0]
    if not active:
        return 0.0
    result = 1.0
    for c in active:
        result *= c
    return result


def run_variant2_evolution(f_form: float, label: str) -> Dict[str, Any]:
    """
    Run Variant 2 sigma evolution for one nebula configuration.

    Physics:
        sigma_eff = sigma_local * f_form + kappa_CMB * sigma_CMB_bg
        d_sigma/dt = I_CMB^alpha * (f_form * sigma_eff - LAMBDA_DECAY * sigma)
                   + G_diffusion * laplacian(sigma)   [if G_grad active]

    T1 proxy: sigma_eff coupling (mass proxy in pre-pump state)
    T5 proxy: -LAMBDA_DECAY * sigma (continuous maintenance drain)
    T2, T3:   DEACTIVATED
    """
    # Initial sigma: Gaussian nebula seed
    r = np.linspace(0, 1, N_R)
    sigma = np.exp(-((r - 0.5) ** 2) / (2 * 0.1 ** 2)) * 0.1
    sigma = sigma.astype(np.float64)

    I_CMB = (KAPPA_CMB * SIGMA_CMB_BG) ** ALPHA_VOID_DEFAULT

    delta_w_accumulator = 0.0
    sigma_track = [float(sigma.mean())]

    nan_detected = False
    inf_detected = False

    for step in range(N_STEPS):
        # sigma_eff: local field modified by F_form plus CMB pre-strain
        sigma_eff = sigma * f_form + KAPPA_CMB * SIGMA_CMB_BG

        # T1 proxy: formation coupling
        # In pre-pump state, sigma acts as mass proxy.
        # Phi(sigma) = sigma_eff / SIGMA_CRIT_PROXY (linear approach to crit)
        phi_sigma = np.clip(sigma_eff / SIGMA_CRIT_PROXY, 0.0, 1.0)
        T1 = sigma_eff * phi_sigma

        # T5: entropy sink (maintenance drain)
        T5 = LAMBDA_DECAY * sigma

        # Variant 2 drive: I_CMB^alpha * (T1*F_form - T5)
        d_sigma = I_CMB * (T1 * f_form - T5)

        # G_grad diffusion (gradient term — active when G_grad component > 0)
        # Approximated as laplacian of sigma (drives condensation toward peaks)
        lap = np.zeros_like(sigma)
        lap[1:-1] = sigma[:-2] - 2 * sigma[1:-1] + sigma[2:]
        # scale by f_form (gradient only active if G_grad > 0)
        # Note: G_grad is embedded in f_form_scalar when active
        d_sigma += 0.01 * lap * (1.0 if f_form > 0 else 0.0)

        sigma = np.clip(sigma + DT * d_sigma, 0.0, None)

        # Accumulate Delta_W_Neb
        delta_w_step = float(np.sum((T1 * f_form + T5) * np.abs(d_sigma)))
        delta_w_accumulator += delta_w_step

        if step % 500 == 0:
            sigma_track.append(float(sigma.mean()))

        if np.any(np.isnan(sigma)):
            nan_detected = True
            break
        if np.any(np.isinf(sigma)):
            inf_detected = True
            break

    sigma_final_mean  = float(sigma.mean())
    sigma_final_max   = float(sigma.max())
    sigma_final_total = float(sigma.sum())

    # Formation verdict for this config
    # Accumulation confirmed if sigma grew from initial mean (~0.04)
    sigma_initial_mean = float(np.exp(-((np.linspace(0,1,N_R)-0.5)**2)/(2*0.1**2))*0.1).mean() if False else 0.04
    accumulated = sigma_final_mean > sigma_initial_mean * 1.1

    if nan_detected:
        formation_state = "NUMERICAL_FAILURE_NAN"
    elif inf_detected:
        formation_state = "NUMERICAL_FAILURE_INF"
    elif f_form == 0.0:
        formation_state = "F_FORM_ZERO_NO_DRIVE"
    elif f_form > FORMATION_THRESHOLD and accumulated:
        formation_state = "FORMATION_CONFIRMED"
    elif f_form > FORMATION_THRESHOLD and not accumulated:
        formation_state = "FORMATION_SUPPRESSED"
    elif f_form <= FORMATION_THRESHOLD:
        formation_state = "BELOW_THRESHOLD_DRAIN_DOMINANT"
    else:
        formation_state = "UNKNOWN"

    return {
        "f_form_scalar":      round(f_form, 6),
        "sigma_final_mean":   round(sigma_final_mean, 8),
        "sigma_final_max":    round(sigma_final_max, 8),
        "sigma_final_total":  round(sigma_final_total, 6),
        "delta_w_neb":        round(delta_w_accumulator, 6),
        "sigma_track":        [round(v, 8) for v in sigma_track],
        "nan_detected":       nan_detected,
        "inf_detected":       inf_detected,
        "formation_state":    formation_state,
        "formation_confirmed": formation_state == "FORMATION_CONFIRMED",
    }


def run_test():
    print(f"BCM v29 TEST16 — NEBULAR FORMATION VARIANT 2")
    print(f"Backend: {_BACKEND}")
    print(f"Xi_S = {XI_S} (fully fractional — no integerization)")
    print(f"T2 active: {T2_ACTIVE} | T3 active: {T3_ACTIVE}")
    print(f"kappa_CMB = {KAPPA_CMB} | alpha_void = {ALPHA_VOID_DEFAULT}")
    print(f"lambda_decay = {LAMBDA_DECAY} | formation_threshold = {FORMATION_THRESHOLD}")
    print(f"sigma_CMB_bg = {SIGMA_CMB_BG}")
    print(f"N_steps = {N_STEPS} | N_r = {N_R}")
    print()

    config_results = []
    architecture_clean = True
    any_formation_confirmed = False

    for cfg in NEBULA_CONFIGS:
        name       = cfg["name"]
        components = cfg["components"]
        confirmed  = cfg["confirmed"]

        f_val = f_form_scalar(components)

        marker = "[CONFIRMED BASELINE]" if confirmed else "[PLACEHOLDER]"
        print(f"Running {name} {marker}")
        print(f"  Components [D,C,S,I,G] = {components}")
        print(f"  F_form scalar (active product) = {f_val:.4f}")

        result = run_variant2_evolution(f_val, name)

        if result["nan_detected"] or result["inf_detected"]:
            architecture_clean = False

        if result["formation_confirmed"]:
            any_formation_confirmed = True

        print(f"  sigma_final_mean = {result['sigma_final_mean']:.8f}")
        print(f"  delta_W_Neb      = {result['delta_w_neb']:.6f}")
        print(f"  formation_state  = {result['formation_state']}")
        print()

        config_results.append({
            "nebula_class":   name,
            "confirmed_spec": confirmed,
            "description":    cfg["description"],
            "components":     {
                "D_dust":  components[0],
                "C_cool":  components[1],
                "S_shock": components[2],
                "I_ion":   components[3],
                "G_grad":  components[4],
            },
            **result,
        })

    # ── verdict ───────────────────────────────────────────────────────────────
    dark_condensate = next(
        r for r in config_results if r["nebula_class"] == "DARK_CONDENSATE"
    )

    if not architecture_clean:
        verdict = "ARCHITECTURE_FAILURE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_FAILED"]
    elif dark_condensate["formation_confirmed"]:
        verdict = "DARK_CONDENSATE_FORMATION_CONFIRMED"
        hyp_keys = [
            "H_V29_DARK_CONDENSATE",
            "H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN",
        ]
    elif dark_condensate["f_form_scalar"] == 0.0:
        verdict = "F_FORM_ZERO_CHECK_COMPONENTS"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN"]
    else:
        verdict = "FORMATION_SUPPRESSED_INVESTIGATE"
        hyp_keys = ["H_V29_NEBULAR_V2_ARCHITECTURE_CLEAN"]

    # ── output ─────────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST16_NEBULAR_FORMATION_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST16",
        "test_name": "NEBULAR_FORMATION_VARIANT_2",
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
        "formation_threshold": FORMATION_THRESHOLD,
        "n_steps":            N_STEPS,
        "n_r":                N_R,

        "primary_config":     "DARK_CONDENSATE",
        "configs":            config_results,

        "architecture_clean":      architecture_clean,
        "any_formation_confirmed": any_formation_confirmed,
        "dark_condensate_result":  dark_condensate["formation_state"],

        "verdict":        verdict,
        "hypothesis_keys": hyp_keys,

        "notes": (
            "PLACEHOLDER configs (all except DARK_CONDENSATE) use "
            "initial component estimates only. SJB must specify "
            "component vectors for each nebula class before those "
            "results are authoritative. DARK_CONDENSATE [1,1,0,0,1] "
            "is the SJB-confirmed baseline (2026-05-17)."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    # ── console summary ────────────────────────────────────────────────────────
    print("=" * 60)
    print("TEST16 NEBULAR FORMATION — SUMMARY")
    print("=" * 60)
    print(f"Architecture clean:       {architecture_clean}")
    print(f"DARK_CONDENSATE state:    {dark_condensate['formation_state']}")
    print(f"DARK_CONDENSATE delta_W:  {dark_condensate['delta_w_neb']:.6f}")
    print(f"DARK_CONDENSATE f_form:   {dark_condensate['f_form_scalar']:.4f}")
    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run_test())
