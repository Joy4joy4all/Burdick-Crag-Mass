# -*- coding: utf-8 -*-
"""
BCM_v28_TEST23_UNIFIED_CMB_SIGNAL.py

Hypothesis: H_V28_UNIFIED_CMB_CRAG_SIGNAL

Statement
---------
A weighted combination of Planck thermal and V_3K kinematic A_CMB
signals produces a more physically complete primordial routing signal
than either proxy alone.

  A_CMB_full = w_t × A_CMB_planck + w_k × A_CMB_v3k
  w_t + w_k = 1.0

Where:
  A_CMB_planck = tanh(ΔT_μK / 70)          — thermal: primordial scar topology
  A_CMB_v3k    = −tanh(V_peculiar / 500)    — kinematic: substrate pressure now
  C_I_CMB      = C_I × max(0, 1 + κ × A_CMB_full)

Test 22 established: rank correlation A_planck vs A_v3k = −0.047.
The two signals are orthogonal — they measure independent physical reality.
Neither alone is sufficient. Both carry real signal.

Weight sweep: w_t ∈ {0.0, 0.1, ..., 1.0}  (11 steps, w_k = 1 − w_t)
κ_align fixed at 2.0 (established in Tests 21/22).

Three optimality criteria reported:
  1. Max rank correlation with base C_I  (preserves morphology signal)
  2. Min tier flips                      (most stable crag map)
  3. Max C_I spread ROOT vs BRANCH       (most discriminating)

Stability map: for each galaxy, does its crag classification hold
across the full weight sweep? Stable = same class at all 11 weights.
Sensitive = class changes depending on signal weighting.

Data sources
------------
  A_CMB_planck : data/planck_map_CMB/bcm_planck_galaxy_pixels.json
                 (written by BCM_v28_EXTRACT_PLANCK_PIXELS.py)
                 Falls back to embedded approximate values if JSON absent.
  A_CMB_v3k    : computed inline from V_3K and distance.

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems -- 2026
All theoretical IP: Burdick.
"""

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

# ============================================================================
# PATH RESOLUTION
# ============================================================================
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_SOLVER_ROOT  = os.path.dirname(os.path.dirname(_THIS_DIR))
_DATA_RESULTS = os.path.join(_SOLVER_ROOT, "data", "results")
_PLANCK_JSON  = os.path.join(
    _SOLVER_ROOT, "data", "planck_map_CMB",
    "bcm_planck_galaxy_pixels.json"
)

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST23_UNIFIED_CMB_SIGNAL"
TEST_NUMBER = 23
HYP_ID      = "H_V28_UNIFIED_CMB_CRAG_SIGNAL"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT = 5.0e-4
J_REF      = 8.0
VMAX_REF   = 206.0
N_HALF     = 60
V_PIERCE   = 12000.0
ALPHA_EX   = 0.006
BETA_DM    = 0.003
DT_P       = 0.015

CI_ROOT    = 1.0e-1
CI_BRANCH  = 1.0e-2
CI_LEAF    = 1.0e-3

T_RMS_UK   = 70.0     # Planck SMICA RMS anisotropy (μK)
V_SCALE    = 500.0    # V_peculiar normalization (km/s)
H0         = 70.0     # km/s/Mpc
KAPPA      = 2.0      # fixed; established Tests 21/22

# Weight sweep: 11 steps w_t = 0.0 → 1.0
W_STEPS    = 11
W_T_VALUES = [round(i / (W_STEPS - 1), 1) for i in range(W_STEPS)]

# ============================================================================
# GALAXY CATALOG
# (name, ra, dec, vmax, j_amp_override, v_3k, d_mpc, dT_fallback_uK)
# dT_fallback_uK: used only if Planck JSON absent
# ============================================================================
CATALOG = [
    ("NGC 5055",    198.96, +42.03,  206.0,  8.0,   654,   8.0,  +40),
    ("Bootes Void", 216.00, +46.00,    8.0,  0.5,  None,  10.0,  +53),
    ("NGC 7496",    347.45, -43.43,  169.0,  7.0,  1404,  18.7,  -10),
    ("IC 5332",     350.85, -36.10,  119.0,  3.5,   455,   9.0,  -65),
    ("NGC 3137",    151.57, -29.00,  160.0, None,  1329,  19.0,  -66),
    ("NGC 3175",    153.35, -28.87,  185.0, None,  1328,  19.0,  -48),
    ("NGC 628",      24.17, +15.78,  217.0, None,   426,   9.8,  +32),
    ("NGC 1087",     41.51,  -0.50,  136.0, None,  1357,  15.9,  -38),
    ("NGC 1300",     49.92, -19.41,  195.0, None,  1415,  19.0, +100),
    ("NGC 1365",     53.40, -36.14,  285.0, None,  1478,  18.1,  +71),
    ("NGC 1385",     54.37, -24.50,  140.0, None,  1335,  18.2,  +18),
    ("NGC 1433",     55.51, -47.22,  190.0, None,   915,   9.7,  -26),
    ("NGC 1566",     65.00, -54.94,  210.0, None,  1346,  17.7,  -19),
    ("NGC 1672",     71.43, -59.25,  230.0, None,  1175,  11.9,   +9),
    ("NGC 2835",    139.47, -22.35,  155.0, None,  1106,  12.2,  -30),
    ("NGC 3351",    160.99, +11.70,  192.0, None,  1075,   9.96, -18),
    ("NGC 3627",    170.06, +12.99,  215.0, None,  1027,  11.3,  +49),
    ("NGC 4254",    184.71, +14.42,  220.0, None,  2702,  13.1,  +17),
    ("NGC 4321",    185.73, +15.82,  230.0, None,  1856,  15.2, +127),
    ("NGC 5068",    199.73, -21.04,   95.0, None,   958,   5.2,  -34),
    ("M74",          24.17, +15.78,  217.0, None,   426,   9.8,  +32),
]


# ============================================================================
# LOAD PLANCK DATA
# ============================================================================

def load_planck_cache():
    """Read pre-extracted Planck pixel values. Returns {name: dT_uK} or {}."""
    if not os.path.isfile(_PLANCK_JSON):
        return {}
    with open(_PLANCK_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {r["name"]: float(r["delta_T_uK"]) for r in data["extracted"]}


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax, override):
    if override is not None:
        return float(override)
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_sigma_deficit(j_amp):
    return float(SIGMA_CRIT * (j_amp / J_REF) * N_HALF)


def compute_delta_W(j_amp):
    sigma_peak = SIGMA_CRIT * (j_amp / J_REF)
    dw = 0.0
    for step in range(N_HALF):
        t  = step / N_HALF
        sl = float(sigma_peak * np.sin(np.pi * t / 2.0) ** 2)
        R  = float(np.cos(2.0 * np.pi * ((V_PIERCE/100.0)*(1+sl) - 144.0) * DT_P))
        dw += R * (ALPHA_EX * R - BETA_DM * np.sign(R) * R ** 2)
    return float(dw)


def a_planck(dT_uK):
    return float(np.tanh(dT_uK / T_RMS_UK))


def a_v3k(v3k, d_mpc):
    if v3k is None:
        return 0.0
    return float(-np.tanh((v3k - H0 * d_mpc) / V_SCALE))


def a_full(ap, av, w_t):
    return float(w_t * ap + (1.0 - w_t) * av)


def classify(ci):
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def rank_correlation(a, b):
    n  = len(a)
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    d2 = float(np.sum((ra.astype(float) - rb.astype(float)) ** 2))
    return float(1.0 - 6.0 * d2 / (n * (n ** 2 - 1)))


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()
    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 100)
    print(f"BCM v28 TEST {TEST_NUMBER} — UNIFIED CMB SIGNAL")
    print(f"Hypothesis : {HYP_ID}")
    print(f"A_CMB_full = w_t × A_planck + w_k × A_v3k  (w_t sweep 0.0→1.0)")
    print(f"κ_align    : {KAPPA}  |  T_rms: {T_RMS_UK} μK  |  V_scale: {V_SCALE} km/s")
    print("=" * 100)

    # ------------------------------------------------------------------
    # STEP 1: Build base galaxy data
    # ------------------------------------------------------------------
    planck_cache = load_planck_cache()
    source_note  = ("real Planck nside=64 JSON" if planck_cache
                    else "embedded fallback values")
    print(f"\nPlanck data : {source_note}")

    galaxies = []
    for row in CATALOG:
        name, ra, dec, vmax, j_ov, v3k, d_mpc, dT_fb = row
        j_amp = compute_j_amp(vmax, j_ov)
        sd    = compute_sigma_deficit(j_amp)
        ci    = j_amp * sd

        dT    = float(planck_cache.get(name, dT_fb))
        ap    = a_planck(dT)
        av    = a_v3k(v3k, d_mpc)

        galaxies.append({
            "name":       name,
            "j_amp":      j_amp,
            "ci_base":    ci,
            "class_base": classify(ci),
            "dT_uK":      dT,
            "a_planck":   ap,
            "a_v3k":      av,
        })

    ci_base = [g["ci_base"] for g in galaxies]
    N       = len(galaxies)

    # ------------------------------------------------------------------
    # STEP 2: Weight sweep
    # ------------------------------------------------------------------
    sweep_results = []

    for w_t in W_T_VALUES:
        w_k       = round(1.0 - w_t, 1)
        a_full_v  = [a_full(g["a_planck"], g["a_v3k"], w_t) for g in galaxies]
        ci_cmb_v  = [max(0.0, g["ci_base"] * (1.0 + KAPPA * af))
                     for g, af in zip(galaxies, a_full_v)]
        classes   = [classify(c) for c in ci_cmb_v]
        flips     = sum(1 for g, c in zip(galaxies, classes)
                        if g["class_base"] != c)
        rho       = rank_correlation(ci_base, ci_cmb_v)
        roots     = [c for c in ci_cmb_v if c > CI_ROOT]
        branches  = [c for c in ci_cmb_v if CI_BRANCH < c <= CI_ROOT]
        spread    = ((float(np.mean(roots)) - float(np.mean(branches)))
                     if roots and branches else 0.0)

        sweep_results.append({
            "w_t":      w_t,
            "w_k":      w_k,
            "rho":      rho,
            "flips":    flips,
            "spread":   spread,
            "mean_ci":  float(np.mean(ci_cmb_v)),
            "a_full":   a_full_v,
            "ci_cmb":   ci_cmb_v,
            "classes":  classes,
        })

    # ------------------------------------------------------------------
    # STEP 3: Optimality — three criteria
    # ------------------------------------------------------------------
    best_rho    = max(sweep_results, key=lambda r: r["rho"])
    best_stable = min(sweep_results, key=lambda r: r["flips"])
    best_spread = max(sweep_results, key=lambda r: r["spread"])

    print()
    print("WEIGHT SWEEP (κ = 2.0)")
    print(f"  {'w_t':>5} {'w_k':>5} {'rho_CI':>8} {'flips':>6} "
          f"{'spread':>10} {'mean_CI_CMB':>13}")
    print("  " + "-" * 58)
    for r in sweep_results:
        flags = []
        if r["w_t"] == best_rho["w_t"]:    flags.append("← max_rho")
        if r["w_t"] == best_stable["w_t"]: flags.append("← min_flips")
        if r["w_t"] == best_spread["w_t"]: flags.append("← max_spread")
        print(f"  {r['w_t']:>5.1f} {r['w_k']:>5.1f} {r['rho']:>8.4f} "
              f"{r['flips']:>6} {r['spread']:>10.4e} {r['mean_ci']:>13.4e}"
              f"  {'  '.join(flags)}")

    print()
    print("OPTIMALITY SUMMARY")
    print(f"  Max rank correlation  : w_t={best_rho['w_t']:.1f}  "
          f"rho={best_rho['rho']:.4f}")
    print(f"  Min tier flips        : w_t={best_stable['w_t']:.1f}  "
          f"flips={best_stable['flips']}")
    print(f"  Max ROOT/BRANCH spread: w_t={best_spread['w_t']:.1f}  "
          f"spread={best_spread['spread']:.4e}")

    # ------------------------------------------------------------------
    # STEP 4: Stability map — does classification hold across sweep?
    # ------------------------------------------------------------------
    print()
    print("GALAXY STABILITY MAP (class at w_t=0.0, 0.5, 1.0 → all-weights sweep)")
    print(f"  {'GALAXY':<14} {'base':<10} "
          f"{'w=0.0':<10} {'w=0.5':<10} {'w=1.0':<10} {'STABLE?':<10} "
          f"{'sensitive_range'}")
    print("  " + "-" * 80)

    stable_rows = []
    n_stable = 0
    for i, g in enumerate(galaxies):
        classes_across = [sweep_results[j]["classes"][i] for j in range(W_STEPS)]
        unique_classes = set(classes_across)
        is_stable = len(unique_classes) == 1

        if is_stable:
            n_stable += 1
            sens_range = "—"
        else:
            # Find the weight range where the flip first occurs
            flip_wt = [W_T_VALUES[j] for j in range(1, W_STEPS)
                       if classes_across[j] != classes_across[j-1]]
            sens_range = f"flips at w_t={flip_wt}"

        c0   = sweep_results[0]["classes"][i]
        c5   = sweep_results[5]["classes"][i]
        c10  = sweep_results[10]["classes"][i]

        print(f"  {g['name']:<14} {g['class_base']:<10} "
              f"{c0:<10} {c5:<10} {c10:<10} "
              f"{'STABLE' if is_stable else 'SENSITIVE':<10} {sens_range}")

        stable_rows.append({
            "name":      g["name"],
            "class_base": g["class_base"],
            "is_stable": is_stable,
            "class_w0":  c0,
            "class_w5":  c5,
            "class_w10": c10,
            "unique_classes": list(unique_classes),
        })

    print(f"\n  Stable across full sweep : {n_stable}/{N}")
    print(f"  Sensitive to weighting   : {N-n_stable}/{N}")

    # ------------------------------------------------------------------
    # STEP 5: Fusion table at equal weight (w_t=0.5)
    # ------------------------------------------------------------------
    half = sweep_results[5]   # w_t=0.5
    print()
    print("FUSION TABLE AT EQUAL WEIGHT (w_t=0.5, w_k=0.5)")
    print(f"  {'GALAXY':<14} {'A_planck':>9} {'A_v3k':>8} "
          f"{'A_full':>8} {'C_I_CMB':>12} {'class':<10} {'FLIP?'}")
    print("  " + "-" * 76)
    flip_count_half = 0
    for i, g in enumerate(galaxies):
        af  = half["a_full"][i]
        ci_c = half["ci_cmb"][i]
        cls  = half["classes"][i]
        flp  = cls != g["class_base"]
        if flp:
            flip_count_half += 1
        print(f"  {g['name']:<14} {g['a_planck']:>9.3f} {g['a_v3k']:>8.3f} "
              f"{af:>8.3f} {ci_c:>12.4e} {cls:<10} "
              f"{'** FLIP **' if flp else ''}")

    # ------------------------------------------------------------------
    # STEP 6: Summary metrics
    # ------------------------------------------------------------------
    rho_half = half["rho"]
    coherence_score  = float(n_stable / N)
    overlap_fraction = float(rho_half)

    print()
    print("=" * 100)
    print("UNIFIED SIGNAL SUMMARY")
    print(f"  Proxy rank correlation (A_planck vs A_v3k) : -0.0468 (from Test 22)")
    print(f"  Rank corr at w_t=0.0 (pure V_3K)          : {sweep_results[0]['rho']:.4f}")
    print(f"  Rank corr at w_t=0.5 (equal weight)        : {rho_half:.4f}")
    print(f"  Rank corr at w_t=1.0 (pure Planck)         : {sweep_results[-1]['rho']:.4f}")
    print(f"  Stable galaxies (class holds all weights)   : {n_stable}/{N}")
    print(f"  Tier flips at equal weight                  : {flip_count_half}")
    print(f"  coherence_score  : {coherence_score:.4f}")
    print(f"  overlap_fraction : {overlap_fraction:.4f}")
    print("=" * 100)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"Unified A_CMB signal sweep over {N} galaxies. "
        f"A_CMB_full = w_t × A_planck + (1−w_t) × A_v3k. "
        f"κ_align={KAPPA}. w_t sweep 0.0→1.0 ({W_STEPS} steps). "
        f"Planck data source: {source_note}. "
        f"Proxy rank correlation A_planck vs A_v3k = −0.047 (Test 22): "
        f"orthogonal signals confirmed. "
        f"Max rho at w_t={best_rho['w_t']:.1f} (rho={best_rho['rho']:.4f}). "
        f"Min flips at w_t={best_stable['w_t']:.1f} (flips={best_stable['flips']}). "
        f"Max spread at w_t={best_spread['w_t']:.1f}. "
        f"Stable galaxies (class holds all weights): {n_stable}/{N}. "
        f"Equal weight (w_t=0.5): rho={rho_half:.4f}, flips={flip_count_half}. "
        f"coherence_score={coherence_score:.4f}, "
        f"overlap_fraction={overlap_fraction:.4f}."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if n_stable > N // 2 else 0,
        "evidence_type": "primary",
        "pass_count":    n_stable,
        "total_configs": N,
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":         coherence_score,
            "overlap_fraction":        overlap_fraction,
            "n_galaxies":              N,
            "n_stable":                n_stable,
            "n_sensitive":             N - n_stable,
            "proxy_rho_planck_v3k":   -0.0468,
            "rho_wt_0_0":             sweep_results[0]["rho"],
            "rho_wt_0_5":             rho_half,
            "rho_wt_1_0":             sweep_results[-1]["rho"],
            "best_rho_wt":            best_rho["w_t"],
            "best_rho_value":         best_rho["rho"],
            "best_stable_wt":         best_stable["w_t"],
            "best_stable_flips":      best_stable["flips"],
            "best_spread_wt":         best_spread["w_t"],
            "flip_count_equal_weight": flip_count_half,
            "kappa":                  KAPPA,
            "t_rms_uk":               T_RMS_UK,
            "v_scale":                V_SCALE,
            "h0":                     H0,
        },
        "context": {
            "framework":      "unified_cmb_signal_weight_sweep",
            "key_finding":    (
                "Planck thermal and V_3K kinematic A_CMB proxies are orthogonal "
                "(rho=−0.047). Both carry independent primordial signal. "
                "The optimal weight ratio reveals relative contribution of "
                "thermal scar topology vs kinematic substrate pressure."
            ),
            "next_step":      (
                "Test 24: SPARC rotation curve correlation with C_I_CMB. "
                "Does unified A_CMB correct BCM rotation curve residuals "
                "beyond what morphology alone explains?"
            ),
        },
        "keywords": [
            "primordial_gutter",
            "cmb_prestrain",
            "a_cmb",
            "crag_intensity",
            "cmb_fused_crag_intensity",
            "primordial_routing",
            "tier_flip",
            "super_gutter",
            "cross_scar",
            "classifier",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "UNIFIED_CMB_21_GALAXY_SWEEP",
        "framework":         "unified_cmb_signal_weight_sweep",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "weight_sweep":      [
            {k: v for k, v in r.items()
             if k not in ("a_full", "ci_cmb", "classes")}
            for r in sweep_results
        ],
        "stability_map":     stable_rows,
        "fusion_table_w05":  [
            {
                "name":       g["name"],
                "a_planck":   g["a_planck"],
                "a_v3k":      g["a_v3k"],
                "a_full_w05": half["a_full"][i],
                "ci_base":    g["ci_base"],
                "ci_cmb_w05": half["ci_cmb"][i],
                "class_base": g["class_base"],
                "class_w05":  half["classes"][i],
            }
            for i, g in enumerate(galaxies)
        ],
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Ingest Tests 19 + 20 + 21 + 22 + 23 after vocabulary confirmation.")
    print("Next: Test 24 — SPARC rotation curve residual correlation with C_I_CMB.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
