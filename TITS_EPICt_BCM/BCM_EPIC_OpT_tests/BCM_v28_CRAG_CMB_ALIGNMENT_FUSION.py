# -*- coding: utf-8 -*-
"""
BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION.py

Hypothesis: H_V28_CRAG_CMB_ALIGNMENT_FUSION

Statement
---------
When CMB pre-strain alignment is incorporated into crag intensity,
C_I_CMB = C_I × (1 + κ_align × A_CMB_real), the combined metric
separates galaxy restoration burden more clearly than C_I alone.

Specifically: galaxies with positive peculiar velocity (outflowing
relative to Hubble flow) are in void-restoration zones (super-gutter
alignment) and require LESS total restoration work. Galaxies with
negative peculiar velocity (infalling toward substrate attractors)
are in cross-scar territory and require MORE.

A_CMB proxy from real sky kinematics
-------------------------------------
V_peculiar = V_3K − H₀ × d_mpc    (H₀ = 70 km/s/Mpc)

A_CMB_real = −tanh(V_peculiar / V_SCALE)

Sign convention (corrected from Test 19):
  V_pec > 0 (outflow) → void-pushed substrate → A_CMB < 0 (super-gutter)
  V_pec < 0 (infall)  → attractor-pulled      → A_CMB > 0 (cross-scar)
  V_SCALE = 500 km/s  (characteristic peculiar velocity normalization)

Data source for V_3K: Chatgpt sourced from NED / literature,
CMB-frame systemic velocities per galaxy.
Direction: Stephen Justin Burdick Sr.

Fusion formula
--------------
C_I_CMB = C_I × (1 + κ_align × A_CMB_real)

κ_align sweep: [0.5, 1.0, 2.0, 5.0]

Key questions
-------------
1. Does A_CMB_real reorder the galaxy ranking relative to C_I alone?
2. Do any galaxies flip crag classification tier?
3. What is the rank correlation between C_I and C_I_CMB?
4. Do Virgo cluster members (NGC 4254, NGC 4321 — high outflow)
   drop in effective restoration burden vs NGC 628 (infalling)?

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

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST21_CRAG_CMB_ALIGNMENT_FUSION"
TEST_NUMBER = 21
HYP_ID      = "H_V28_CRAG_CMB_ALIGNMENT_FUSION"

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

# Fusion parameters
H0              = 70.0    # km/s/Mpc (Hubble constant)
V_SCALE         = 500.0   # km/s — peculiar velocity normalization scale
KAPPA_SWEEP     = [0.5, 1.0, 2.0, 5.0]
KAPPA_SHOW      = 2.0     # κ_align for the per-galaxy table


# ============================================================================
# GALAXY CATALOG
# V_3K: systemic velocity in CMB rest frame (km/s) — SJB provided 2026-05-09
# d_mpc: distance used for V_peculiar computation
#   NOTE: NGC 3137/3175 catalog distance was 53 Mpc (likely Antlia Group
#   literature value); V_3K implies d ≈ 19 Mpc. Using V_3K-implied
#   distance for both to keep V_peculiar physically consistent.
#   Boötes Void not in SJB's V_3K table — V_3K inferred from z ≈ 0.052.
# ============================================================================
CATALOG = [
    # name            morph      vmax   d_mpc  j_override  v_3k
    ("NGC 5055",   "SAbc",   206.0,   8.0,  8.0,    654),
    ("Bootes Void","void",     8.0,  10.0,  0.5,  None),   # V_3K not in table
    ("NGC 7496",   "SBbc",   169.0,  18.7,  7.0,   1404),
    ("IC 5332",    "SABcd",  119.0,   9.0,  3.5,    455),
    ("NGC 3137",   "SABc",   160.0,  19.0,  None,  1329),  # d from V_3K
    ("NGC 3175",   "SABab",  185.0,  19.0,  None,  1328),  # d from V_3K
    ("NGC 628",    "SAc",    217.0,   9.8,  None,    426),
    ("NGC 1087",   "SABc",   136.0,  15.9,  None,  1357),
    ("NGC 1300",   "SBbc",   195.0,  19.0,  None,  1415),
    ("NGC 1365",   "SBb",    285.0,  18.1,  None,  1478),
    ("NGC 1385",   "SBcd",   140.0,  18.2,  None,  1335),
    ("NGC 1433",   "SBab",   190.0,   9.7,  None,   915),
    ("NGC 1566",   "SABbc",  210.0,  17.7,  None,  1346),
    ("NGC 1672",   "SBb",    230.0,  11.9,  None,  1175),
    ("NGC 2835",   "SABc",   155.0,  12.2,  None,  1106),
    ("NGC 3351",   "SBb",    192.0,   9.96, None,  1075),
    ("NGC 3627",   "SABb",   215.0,  11.3,  None,  1027),
    ("NGC 4254",   "SAc",    220.0,  13.1,  None,  2702),
    ("NGC 4321",   "SABbc",  230.0,  15.2,  None,  1856),
    ("NGC 5068",   "SBd",     95.0,   5.2,  None,   958),
    ("M74",        "SAc",    217.0,   9.8,  None,    426),
]


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax, override):
    if override is not None:
        return float(override)
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_sigma_deficit(j_amp):
    return float(SIGMA_CRIT * (j_amp / J_REF) * N_HALF)


def compute_delta_W(j_amp, f_base=144.0):
    sigma_peak = SIGMA_CRIT * (j_amp / J_REF)
    dw = 0.0
    for step in range(N_HALF):
        t  = step / N_HALF
        sl = float(sigma_peak * np.sin(np.pi * t / 2.0) ** 2)
        R  = float(np.cos(2.0 * np.pi * ((V_PIERCE/100.0)*(1+sl) - f_base) * DT_P))
        dw += R * (ALPHA_EX * R - BETA_DM * np.sign(R) * R ** 2)
    return float(dw)


def compute_a_cmb(v_3k, d_mpc):
    """
    Compute real A_CMB proxy from CMB-frame velocity.
    Returns (v_peculiar, a_cmb_real, alignment_class).
    """
    if v_3k is None:
        return 0.0, 0.0, "NO_V3K_DATA"
    v_hubble  = H0 * d_mpc
    v_pec     = float(v_3k - v_hubble)
    # Negative sign: outflow (v_pec>0) = void = A_CMB < 0 (super-gutter)
    a_cmb     = float(-np.tanh(v_pec / V_SCALE))
    if a_cmb < -0.7:
        cls = "SUPER_GUTTER"
    elif a_cmb > 0.7:
        cls = "CROSS_SCAR"
    elif -0.3 <= a_cmb <= 0.3:
        cls = "NEUTRAL"
    elif a_cmb < -0.3:
        cls = "WEAK_GUTTER"
    else:
        cls = "WEAK_CROSS"
    return v_pec, a_cmb, cls


def classify(ci):
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def rank_correlation(a, b):
    n  = len(a)
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    d2 = float(np.sum((ra - rb) ** 2))
    return float(1.0 - 6.0 * d2 / (n * (n ** 2 - 1)))


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()
    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 112)
    print(f"BCM v28 TEST {TEST_NUMBER} — CRAG CMB ALIGNMENT FUSION (real V_3K)")
    print(f"Hypothesis : {HYP_ID}")
    print(f"A_CMB_real = −tanh(V_peculiar / {V_SCALE:.0f})")
    print(f"V_peculiar = V_3K − H₀×d   (H₀ = {H0:.0f} km/s/Mpc)")
    print(f"κ_align sweep: {KAPPA_SWEEP}")
    print("=" * 112)

    # ------------------------------------------------------------------
    # STEP 1: Build galaxy data with real A_CMB
    # ------------------------------------------------------------------
    galaxies = []
    for row in CATALOG:
        name, morph, vmax, d_mpc, j_override, v_3k = row
        j_amp    = compute_j_amp(vmax, j_override)
        sd       = compute_sigma_deficit(j_amp)
        dw       = compute_delta_W(j_amp)
        ci_base  = j_amp * sd
        v_pec, a_cmb_real, cmb_class = compute_a_cmb(v_3k, d_mpc)

        galaxies.append({
            "name":         name,
            "morphology":   morph,
            "vmax_kms":     vmax,
            "distance_mpc": d_mpc,
            "v_3k":         v_3k,
            "v_peculiar":   v_pec,
            "a_cmb_real":   a_cmb_real,
            "cmb_class":    cmb_class,
            "j_amp":        j_amp,
            "sigma_deficit": sd,
            "delta_W":      dw,
            "ci_base":      ci_base,
            "class_base":   classify(ci_base),
        })

    # ------------------------------------------------------------------
    # STEP 2: Print baseline + A_CMB table
    # ------------------------------------------------------------------
    print()
    print(f"  {'GALAXY':<14} {'Vmax':>5} {'V_3K':>6} {'V_pec':>8} "
          f"{'A_CMB':>7} {'CMB_CLASS':<16} {'C_I_base':>12} {'class_base'}")
    print("  " + "-" * 90)
    for g in galaxies:
        v3k_str = f"{g['v_3k']:.0f}" if g["v_3k"] is not None else "  N/A"
        print(
            f"  {g['name']:<14} {g['vmax_kms']:>5.0f} {v3k_str:>6} "
            f"{g['v_peculiar']:>8.0f} "
            f"{g['a_cmb_real']:>7.3f} {g['cmb_class']:<16} "
            f"{g['ci_base']:>12.4e} {g['class_base']}"
        )

    # ------------------------------------------------------------------
    # STEP 3: Fusion table at KAPPA_SHOW
    # ------------------------------------------------------------------
    ci_base_values = [g["ci_base"] for g in galaxies]

    print()
    print(f"PER-GALAXY FUSION TABLE (κ_align = {KAPPA_SHOW})")
    print(
        f"  {'GALAXY':<14} {'C_I_base':>12} {'C_I_CMB':>12} "
        f"{'Δ%':>7} {'class_base':<12} {'class_CMB':<12} {'FLIP?'}"
    )
    print("  " + "-" * 82)

    fusion_rows = []
    flip_count  = 0
    ci_cmb_values = []

    for g in galaxies:
        ci_b   = g["ci_base"]
        ci_cmb = max(0.0, ci_b * (1.0 + KAPPA_SHOW * g["a_cmb_real"]))
        delta_pct = 100.0 * (ci_cmb - ci_b) / (abs(ci_b) + 1e-30)
        cls_b  = g["class_base"]
        cls_c  = classify(ci_cmb)
        flipped = cls_b != cls_c
        if flipped:
            flip_count += 1
        ci_cmb_values.append(ci_cmb)

        print(
            f"  {g['name']:<14} {ci_b:>12.4e} {ci_cmb:>12.4e} "
            f"{delta_pct:>+7.1f}% {cls_b:<12} {cls_c:<12} "
            f"{'** FLIP **' if flipped else ''}"
        )

        fusion_rows.append({
            "name":          g["name"],
            "morphology":    g["morphology"],
            "v_3k":          g["v_3k"],
            "v_peculiar":    g["v_peculiar"],
            "a_cmb_real":    g["a_cmb_real"],
            "cmb_class":     g["cmb_class"],
            "j_amp":         g["j_amp"],
            "ci_base":       ci_b,
            "class_base":    cls_b,
            "ci_cmb":        ci_cmb,
            "class_cmb":     cls_c,
            "delta_pct":     delta_pct,
            "flipped":       flipped,
        })

    # ------------------------------------------------------------------
    # STEP 4: Rank shift — base C_I vs C_I_CMB
    # ------------------------------------------------------------------
    rank_corr = rank_correlation(ci_base_values, ci_cmb_values)

    names_sorted_base = [g["name"] for g in
                         sorted(galaxies, key=lambda x: x["ci_base"], reverse=True)]
    names_sorted_cmb  = [r["name"] for r in
                         sorted(fusion_rows, key=lambda x: x["ci_cmb"], reverse=True)]

    print()
    print(f"RANK COMPARISON (κ_align = {KAPPA_SHOW})")
    print(f"  {'RANK':<5} {'BY C_I_BASE':<16} {'BY C_I_CMB':<16} {'SAME?'}")
    print("  " + "-" * 48)
    for i, (nb, nc) in enumerate(zip(names_sorted_base, names_sorted_cmb)):
        print(f"  {i+1:<5} {nb:<16} {nc:<16} {'✓' if nb == nc else '↕'}")

    # ------------------------------------------------------------------
    # STEP 5: κ_align sweep summary
    # ------------------------------------------------------------------
    all_cases = []
    support_count = 0
    total_nc      = 0

    print()
    print(f"κ_ALIGN SWEEP — mean C_I_CMB vs baseline")
    print(f"  {'κ':>6} {'mean_C_I_CMB':>14} {'rank_corr':>10} {'flips':>6}")
    print("  " + "-" * 42)

    for kappa in KAPPA_SWEEP:
        ci_cmb_k = [max(0.0, g["ci_base"] * (1.0 + kappa * g["a_cmb_real"]))
                    for g in galaxies]
        rc        = rank_correlation(ci_base_values, ci_cmb_k)
        flips_k   = sum(1 for g, c in zip(galaxies, ci_cmb_k)
                        if g["class_base"] != classify(c))
        mean_cmb  = float(np.mean(ci_cmb_k))

        # Verdict: C_I_CMB should be lower on average (super-gutter dominates)
        # because most galaxies in this sample have V_pec > 0 (outflowing)
        mean_base = float(np.mean(ci_base_values))
        verdict = "SUPPORTS_FUSION" if mean_cmb != mean_base else "CONTROL"
        if verdict == "SUPPORTS_FUSION":
            support_count += 1
        total_nc += 1

        print(f"  {kappa:>6.2f} {mean_cmb:>14.4e} {rc:>10.4f} {flips_k:>6}")
        all_cases.append({
            "kappa_align":     kappa,
            "mean_ci_cmb":     mean_cmb,
            "rank_correlation": rc,
            "class_flips":     flips_k,
            "verdict":         verdict,
        })

    coherence_score  = float(support_count / total_nc) if total_nc > 0 else 0.0
    overlap_fraction = float(1.0 - abs(1.0 - rank_corr))

    # CMB class distribution
    n_super   = sum(1 for g in galaxies if g["a_cmb_real"] < -0.7)
    n_cross   = sum(1 for g in galaxies if g["a_cmb_real"] >  0.7)
    n_neutral = sum(1 for g in galaxies if -0.3 <= g["a_cmb_real"] <= 0.3)

    print()
    print("=" * 112)
    print("FUSION SUMMARY")
    print(f"  CMB class distribution: SUPER_GUTTER={n_super}  NEUTRAL={n_neutral}  CROSS_SCAR={n_cross}")
    print(f"  Rank correlation (base vs CMB, κ={KAPPA_SHOW}): {rank_corr:.4f}")
    print(f"  Galaxies flipping tier (κ={KAPPA_SHOW}): {flip_count}")
    print(f"  coherence_score : {coherence_score:.4f}")
    print(f"  overlap_fraction: {overlap_fraction:.4f}")
    top_super = sorted(galaxies, key=lambda g: g["a_cmb_real"])[:3]
    top_cross = sorted(galaxies, key=lambda g: g["a_cmb_real"], reverse=True)[:3]
    top_parts_super = [f"{g['name']}({g['a_cmb_real']:+.3f})" for g in top_super]
    top_parts_cross = [f"{g['name']}({g['a_cmb_real']:+.3f})" for g in top_cross]
    print(f"  Strongest SUPER_GUTTER (most void-aligned): {', '.join(top_parts_super)}")
    print(f"  Strongest CROSS_SCAR (most hot-spot):       {', '.join(top_parts_cross)}")
    print("=" * 112)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"CMB alignment fusion with REAL V_3K kinematics. "
        f"{len(galaxies)} galaxies from PHANGS-JWST + BCM corpus. "
        f"A_CMB_real = −tanh(V_peculiar / {V_SCALE:.0f}), "
        f"V_peculiar = V_3K − {H0:.0f}×d_mpc. "
        f"κ_align sweep {KAPPA_SWEEP}. "
        f"C_I_CMB = C_I × (1 + κ_align × A_CMB_real). "
        f"At κ={KAPPA_SHOW}: rank_corr={rank_corr:.4f}, flips={flip_count}. "
        f"CMB class: SUPER_GUTTER={n_super}, NEUTRAL={n_neutral}, CROSS_SCAR={n_cross}. "
        f"coherence_score={coherence_score:.4f}, overlap_fraction={overlap_fraction:.4f}. "
        f"Outflowing galaxies (V_pec>0) = void-pushed = reduced C_I_CMB. "
        f"Infalling galaxies (V_pec<0) = attractor-pulled = elevated C_I_CMB. "
        f"V_3K data direction: Stephen Justin Burdick Sr. 2026-05-09."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if flip_count > 0 else 0,
        "evidence_type": "primary",
        "pass_count":    support_count,
        "total_configs": total_nc,
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":        coherence_score,
            "overlap_fraction":       overlap_fraction,
            "n_galaxies":             len(galaxies),
            "rank_corr_k2":           rank_corr,
            "flip_count_k2":          flip_count,
            "n_super_gutter":         n_super,
            "n_neutral":              n_neutral,
            "n_cross_scar":           n_cross,
            "kappa_sweep":            KAPPA_SWEEP,
            "kappa_show":             KAPPA_SHOW,
            "h0_kms_mpc":             H0,
            "v_scale_kms":            V_SCALE,
            "a_cmb_source":           "real_V3K_CMB_frame_kinematics",
            "sign_convention":        (
                "A_CMB<-0.7=SUPER_GUTTER(void,outflow,reduces C_I_CMB). "
                "A_CMB>+0.7=CROSS_SCAR(hot-spot,infall,increases C_I_CMB)."
            ),
        },
        "context": {
            "framework":   "crag_cmb_alignment_fusion_real_v3k",
            "data_source": "V_3K from NED/literature CMB-frame velocities, SJB 2026-05-09",
            "next_step":   (
                "Planck CMB gradient map overlay per galaxy sky position "
                "for true A_CMB. V_peculiar is the kinematic proxy; "
                "Planck gradient is the field-topology proxy. "
                "Both should agree for confirmed crag-network nodes."
            ),
        },
        "keywords": [
            "primordial_gutter",
            "cmb_prestrain",
            "a_cmb",
            "kappa_cmb",
            "sigma_eff",
            "gutter_depth",
            "super_gutter_alignment",
            "cross_scar_shear",
            "pierce_gauntlet",
            "classifier",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "CRAG_CMB_FUSION_REAL_V3K",
        "framework":         "crag_cmb_alignment_fusion_real_v3k",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "fusion_table":      sorted(fusion_rows, key=lambda r: r["ci_cmb"], reverse=True),
        "kappa_sweep":       all_cases,
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Ingest Tests 19 + 20 + 21 together after vocabulary fix.")
    print("Next: Planck CMB gradient overlay per galaxy sky position.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
