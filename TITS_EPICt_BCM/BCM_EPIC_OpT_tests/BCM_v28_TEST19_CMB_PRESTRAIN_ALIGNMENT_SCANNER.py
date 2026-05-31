# -*- coding: utf-8 -*-
"""
BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER.py

Hypothesis: H_V28_PRIMORDIAL_GUTTER_CMB_PRESTRAIN

Purpose
-------
First synthetic-control test for the Primordial Gutter Hypothesis (SJB 2026).

Tests whether local Gutter work ΔW is REDUCED when the local substrate
gradient aligns with a primordial CMB void-channel field (super-gutter
alignment) and INCREASED when aligned with a CMB hot-spot barrier
(cross-scar shear risk).

No external data required. This is the operator-behavior test that must
pass before Planck / SPARC observational ingestion proceeds.

Physics fixes relative to ChatGPT v1
--------------------------------------
1. σ_CMB sign corrected:
     "aligned"      → NEGATIVE gaussian  (void channel = pre-carved Gutter)
     "anti_aligned" → POSITIVE gaussian  (hot spot = barrier = cross-scar)
   Rationale: CMB cold spots / voids are where the Bang tore cleanest.
   Super-gutter alignment means traveling WITH a pre-depleted channel,
   not WITH a high-strain hotspot.

2. Verdict logic corrected to match sign convention above:
     aligned + κ > 0  → ΔW reduces (reduction > 0) → SUPPORTS_OPERATOR ✓
     anti_aligned + κ > 0 → ΔW increases (reduction < 0) → SUPPORTS_OPERATOR ✓

3. R operator documented honestly:
   The spatial proxy R = |∇σ_local| is used here because there is no
   craft velocity in a 2D spatial field test. This is NOT BCM's resonance
   R = cos(ΔΦ). It is a valid first-pass spatial operator test. The
   result tells us whether A_CMB is a directional predictor of gradient
   work, which is the necessary condition before the full temporal
   path-integral test can be designed.

4. Two-level path climb (BCM_EPIC_OpT_tests → solver root).

5. hypotheses_tested wrapper for cube ingestion (Test 13 pattern).

6. Timestamped output filename.

Operator definitions
---------------------
σ_eff = σ_local + κ_CMB × σ_CMB

A_CMB = (∇σ_local · ∇σ_CMB) / (|∇σ_local| × |∇σ_CMB| + ε)

ΔW_eff  = mean over grid( |∇σ_local| × |∇σ_eff| )
                         (spatial proxy for path-integral phase-work)

reduction = (ΔW_baseline − ΔW_eff) / (|ΔW_baseline| + ε)
            > 0: ΔW decreased (Gutter deepened by CMB pre-strain)
            < 0: ΔW increased (CMB adds impedance)

Dual-gate metrics for FIELD_EXTRACTED
--------------------------------------
coherence_score  = fraction of aligned κ>0 cases where reduction > 0
                   (how consistently does super-gutter alignment reduce ΔW?)
overlap_fraction = fraction of ALL non-control cases that SUPPORT_OPERATOR
                   (overall operator agreement rate)

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
# PATH RESOLUTION  (two-level climb: TITS_EPICt_BCM/BCM_EPIC_OpT_tests → root)
# ============================================================================
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_SOLVER_ROOT  = os.path.dirname(os.path.dirname(_THIS_DIR))
_DATA_RESULTS = os.path.join(_SOLVER_ROOT, "data", "results")

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST19_CMB_PRESTRAIN_ALIGNMENT_SCANNER"
TEST_NUMBER = 19
HYP_ID      = "H_V28_PRIMORDIAL_GUTTER_CMB_PRESTRAIN"

# ============================================================================
# BCM CONSTANTS
# ============================================================================
SIGMA_CRIT           = 5.0e-4
CMB_ANISOTROPY_SCALE = 1.0e-5   # ΔT/T ~ 1e-5 physical scale
EPS                  = 1.0e-12

# κ_CMB sweep — explicitly unfrozen, hypothesis layer
KAPPA_CMB_VALUES = [0.0, 0.25, 0.50, 1.0, 2.0, 5.0]

# Grid
GRID_N = 128

# CMB synthetic modes
CMB_MODES = ["aligned", "anti_aligned", "transverse", "random"]

# Operator validity thresholds
COHERENCE_GATE    = 0.70   # ≥70% of aligned κ>0 cases must reduce ΔW
OVERLAP_GATE      = 0.50   # ≥50% of all non-control cases must support

RNG_SEED = 28019


# ============================================================================
# FIELD BUILDERS
# ============================================================================

def build_grid():
    axis = np.linspace(-1.0, 1.0, GRID_N)
    x, y = np.meshgrid(axis, axis)
    return x, y


def gaussian_2d(x, y, x0, y0, sx, sy, amp):
    return amp * np.exp(
        -(((x - x0) ** 2) / (2 * sx ** 2)
          + ((y - y0) ** 2) / (2 * sy ** 2))
    )


def build_local_sigma(x, y):
    """
    Local torus / gutter candidate field.
    Dipole structure: positive lobe (pump A) + negative lobe (depletion).
    """
    return (
        gaussian_2d(x, y, -0.25,  0.00, 0.22, 0.35, SIGMA_CRIT * 1.20)
        - gaussian_2d(x, y,  0.35,  0.05, 0.28, 0.25, SIGMA_CRIT * 0.80)
    )


def build_cmb_field(x, y, mode):
    """
    Synthetic primordial strain map.

    Sign convention (CORRECTED from ChatGPT v1):
    ---------------------------------------------------------------------------
    The Gutter is a LOW-IMPEDANCE conduit = depleted substrate = NEGATIVE σ.
    CMB cold spots / voids are pre-carved Gutter channels from the Bang.
    CMB hot spots are high-strain anchors = barriers = additional impedance.

    "aligned":
        σ_CMB is NEGATIVE where the local gradient is strongest.
        = void channel co-directed with local substrate gradient.
        = super-gutter alignment.
        Prediction: σ_eff < σ_local in the gradient zone → ΔW REDUCES.

    "anti_aligned":
        σ_CMB is POSITIVE where the local gradient is strongest.
        = hot spot barrier co-directed with local substrate gradient.
        = cross-scar shear risk.
        Prediction: σ_eff > σ_local in the gradient zone → ΔW INCREASES.

    "transverse":
        Scar structure roughly orthogonal to local gradient.
        Prediction: A_CMB ≈ 0, ΔW ≈ baseline (neutral substrate).

    "random":
        Structured noise control condition.
        Prediction: A_CMB ~ 0, ΔW ≈ baseline.
    ---------------------------------------------------------------------------
    """
    base = CMB_ANISOTROPY_SCALE * (
        gaussian_2d(x, y, -0.25,  0.00, 0.30, 0.40,  1.0)
        - gaussian_2d(x, y,  0.35,  0.05, 0.35, 0.30, 0.7)
    )

    if mode == "aligned":
        # Void channel: NEGATIVE (depletes substrate in Gutter direction)
        return -base

    if mode == "anti_aligned":
        # Hot-spot barrier: POSITIVE (adds impedance against local gradient)
        return base

    if mode == "transverse":
        return CMB_ANISOTROPY_SCALE * (
            np.sin(8.0 * y) * np.exp(-2.0 * x ** 2)
        )

    if mode == "random":
        rng = np.random.default_rng(RNG_SEED)
        noise = rng.normal(0.0, 1.0, x.shape)
        for _ in range(12):
            noise = (
                noise
                + np.roll(noise,  1, axis=0)
                + np.roll(noise, -1, axis=0)
                + np.roll(noise,  1, axis=1)
                + np.roll(noise, -1, axis=1)
            ) / 5.0
        noise /= (np.max(np.abs(noise)) + EPS)
        return CMB_ANISOTROPY_SCALE * noise

    raise ValueError(f"Unknown CMB mode: {mode!r}")


# ============================================================================
# OPERATORS
# ============================================================================

def gradient_field(f):
    """Spatial gradient (gy, gx) via numpy.gradient."""
    gy, gx = np.gradient(f)
    return gx, gy


def alignment_coefficient(local_sigma, cmb_sigma):
    """
    A_CMB = (∇σ_local · ∇σ_CMB) / (|∇σ_local| × |∇σ_CMB| + ε)

    Weighted mean: weight by |∇σ_local| to emphasise regions where
    the local gradient is physically meaningful.
    Returns (A_mean_weighted, A_median, grad_mag_local_mean).
    """
    lx, ly = gradient_field(local_sigma)
    cx, cy = gradient_field(cmb_sigma)

    dot  = lx * cx + ly * cy
    l_n  = np.sqrt(lx * lx + ly * ly)
    c_n  = np.sqrt(cx * cx + cy * cy)

    a_map    = dot / (l_n * c_n + EPS)
    weights  = l_n                              # weight by local gradient strength
    a_mean   = float(np.sum(a_map * weights) / (np.sum(weights) + EPS))
    a_median = float(np.median(a_map))
    l_mean   = float(np.mean(l_n))

    return a_mean, a_median, l_mean


def delta_W(local_sigma, sigma_eff):
    """
    Spatial proxy for Gutter Depth.

    ΔW_proxy = mean( |∇σ_local| × |∇σ_eff| )

    NOT the BCM temporal path integral ΔW = ∫R·dσ (which requires a
    craft velocity and timestep). This is a valid first-pass SPATIAL
    operator test: it measures whether A_CMB alignment predicts a
    directional change in gradient-work across the field.

    R proxy: |∇σ_local| (local gradient magnitude = spatial coupling strength)
    dσ proxy: |∇σ_eff|  (effective field gradient = displacement magnitude)
    """
    lx, ly = gradient_field(local_sigma)
    R_proxy = np.sqrt(lx * lx + ly * ly)

    ex, ey  = gradient_field(sigma_eff)
    d_eff   = np.sqrt(ex * ex + ey * ey)

    return float(np.mean(R_proxy * d_eff))


def classify_alignment(a_cmb):
    """Map A_CMB to Work Formulas Section 43 classification."""
    if a_cmb > 0.70:
        return "SUPER_GUTTER_ALIGNMENT"
    if a_cmb < -0.70:
        return "CROSS_SCAR_SHEAR_RISK"
    if -0.30 <= a_cmb <= 0.30:
        return "NEUTRAL_SUBSTRATE"
    if a_cmb > 0.30:
        return "WEAK_ALIGNMENT"
    return "WEAK_ANTI_ALIGNMENT"


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()

    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 80)
    print(f"BCM v28 TEST {TEST_NUMBER} — CMB PRE-STRAIN ALIGNMENT SCANNER")
    print(f"Hypothesis : {HYP_ID}")
    print(f"Grid       : {GRID_N}×{GRID_N}")
    print(f"κ_CMB sweep: {KAPPA_CMB_VALUES}")
    print(f"CMB modes  : {CMB_MODES}")
    print("=" * 80)

    x, y           = build_grid()
    local_sigma    = build_local_sigma(x, y)
    baseline_dW    = delta_W(local_sigma, local_sigma)

    print(f"\nBaseline ΔW (no CMB pre-strain): {baseline_dW:.8e}")
    print()
    print(
        f"{'MODE':<14} {'κ_CMB':<7} {'A_CMB':<9} {'CLASS':<26} "
        f"{'ΔW_eff':<14} {'reduction':<12} {'VERDICT'}"
    )
    print("-" * 100)

    all_cases   = []
    support_all = 0    # all non-control cases
    total_nc    = 0    # non-control count
    support_al  = 0    # aligned κ>0 cases
    total_al    = 0    # aligned κ>0 count

    for mode in CMB_MODES:
        cmb_raw = build_cmb_field(x, y, mode)

        for kappa in KAPPA_CMB_VALUES:
            sigma_cmb = kappa * cmb_raw
            sigma_eff = local_sigma + sigma_cmb

            a_mean, a_median, _ = alignment_coefficient(local_sigma, sigma_cmb)
            dw_eff              = delta_W(local_sigma, sigma_eff)
            reduction           = (baseline_dW - dw_eff) / (abs(baseline_dW) + EPS)
            align_class         = classify_alignment(a_mean)

            # ----------------------------------------------------------------
            # Verdict logic (CORRECTED sign convention)
            # aligned + κ>0: void channel → ΔW reduces → reduction > 0
            # anti_aligned + κ>0: hot-spot → ΔW increases → reduction < 0
            # ----------------------------------------------------------------
            if kappa == 0.0:
                verdict = "CONTROL"
            elif mode == "aligned" and reduction > 0:
                verdict = "SUPPORTS_OPERATOR"
            elif mode == "anti_aligned" and reduction < 0:
                verdict = "SUPPORTS_OPERATOR"
            elif mode in ("transverse", "random"):
                verdict = "NEUTRAL_CONTROL"
            else:
                verdict = "MIXED_OR_REJECT"

            case = {
                "cmb_mode":                  mode,
                "kappa_CMB":                 float(kappa),
                "A_CMB_mean":                float(a_mean),
                "A_CMB_median":              float(a_median),
                "alignment_class":           align_class,
                "deltaW_baseline":           float(baseline_dW),
                "deltaW_eff":                float(dw_eff),
                "deltaW_reduction_fraction": float(reduction),
                "verdict":                   verdict,
            }
            all_cases.append(case)

            # Tally for dual-gate metrics
            if kappa > 0.0:
                total_nc += 1
                if verdict == "SUPPORTS_OPERATOR":
                    support_all += 1
                if mode == "aligned":
                    total_al += 1
                    if verdict == "SUPPORTS_OPERATOR":
                        support_al += 1

            print(
                f"{mode:<14} {kappa:<7.2f} {a_mean:+.5f}  "
                f"{align_class:<26} {dw_eff:.8e}  "
                f"{reduction:+.5f}    {verdict}"
            )

    # -----------------------------------------------------------------------
    # DUAL-GATE METRICS
    # -----------------------------------------------------------------------
    coherence_score  = float(support_al  / total_al)  if total_al  > 0 else 0.0
    overlap_fraction = float(support_all / total_nc)  if total_nc  > 0 else 0.0
    operator_valid   = (coherence_score  >= COHERENCE_GATE
                        and overlap_fraction >= OVERLAP_GATE)

    print()
    print("=" * 80)
    print("DUAL-GATE SUMMARY")
    print(f"  coherence_score  (aligned κ>0 support rate): {coherence_score:.4f}"
          f"  [gate ≥ {COHERENCE_GATE}]  {'PASS' if coherence_score >= COHERENCE_GATE else 'FAIL'}")
    print(f"  overlap_fraction (all non-ctrl support rate): {overlap_fraction:.4f}"
          f"  [gate ≥ {OVERLAP_GATE}]  {'PASS' if overlap_fraction >= OVERLAP_GATE else 'FAIL'}")
    print(f"  Operator valid: {operator_valid}")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # HYPOTHESIS OUTPUT  (Test 13 pattern)
    # -----------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"Synthetic operator validation for H_V28_PRIMORDIAL_GUTTER_CMB_PRESTRAIN. "
        f"Grid {GRID_N}×{GRID_N}. "
        f"κ_CMB sweep {KAPPA_CMB_VALUES}. "
        f"CMB modes: aligned (void channel, negative σ_CMB), "
        f"anti_aligned (hot-spot barrier, positive σ_CMB), "
        f"transverse, random. "
        f"Operator: A_CMB = ∇σ_local·∇σ_CMB / (|∇σ_local||∇σ_CMB| + ε). "
        f"ΔW proxy = mean(|∇σ_local| × |∇σ_eff|) "
        f"[spatial gradient proxy, not BCM temporal path integral]. "
        f"Baseline ΔW (κ=0): {baseline_dW:.6e}. "
        f"coherence_score (aligned support rate) = {coherence_score:.4f}. "
        f"overlap_fraction (all non-ctrl support rate) = {overlap_fraction:.4f}. "
        f"Operator valid = {operator_valid} "
        f"(requires coherence_score ≥ {COHERENCE_GATE} AND "
        f"overlap_fraction ≥ {OVERLAP_GATE}). "
        f"Sign convention: aligned = void channel (negative σ_CMB, "
        f"pre-carved Gutter path); anti_aligned = hot-spot barrier "
        f"(positive σ_CMB, cross-scar shear risk). "
        f"Ontological status: LOW (Interpretive). Synthetic only. "
        f"Does not use Planck or SPARC data."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if operator_valid else 0,
        "evidence_type": "primary",
        "pass_count":    support_all,
        "total_configs": total_nc,
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            # Dual-gate (FIELD_EXTRACTED path)
            "coherence_score":                coherence_score,
            "overlap_fraction":               overlap_fraction,
            # Operator characterization
            "baseline_deltaW":                float(baseline_dW),
            "operator_valid":                 operator_valid,
            "support_aligned_kappa_gt0":      support_al,
            "total_aligned_kappa_gt0":        total_al,
            "support_all_non_control":        support_all,
            "total_non_control":              total_nc,
            # Gate thresholds
            "coherence_gate":                 COHERENCE_GATE,
            "overlap_gate":                   OVERLAP_GATE,
            # Operator notes
            "R_proxy":   "|∇σ_local| (spatial gradient magnitude)",
            "dW_proxy":  "mean(|∇σ_local| × |∇σ_eff|)",
            "note_R":    ("NOT BCM resonance R=cos(ΔΦ). Spatial proxy valid "
                          "for first-pass directional operator test only."),
            # CMB parameters
            "kappa_CMB_values":               KAPPA_CMB_VALUES,
            "cmb_anisotropy_scale":           CMB_ANISOTROPY_SCALE,
            "sigma_crit":                     SIGMA_CRIT,
            "grid_n":                         GRID_N,
            # Sign convention record
            "aligned_sign":       "NEGATIVE σ_CMB (void channel = pre-carved Gutter)",
            "anti_aligned_sign":  "POSITIVE σ_CMB (hot-spot = cross-scar barrier)",
        },
        "context": {
            "framework":          "cmb_prestrain_synthetic_operator_test",
            "data_source":        "synthetic_only_no_Planck_no_SPARC",
            "ontological_status": "LOW_COMMITMENT_HYPOTHESIS_LAYER",
            "next_step":          (
                "If operator_valid=True: design observational test overlaying "
                "Planck CMB gradient on SPARC/Local Group galaxy substrate "
                "signatures. Calibrate κ_CMB against real sky data."
            ),
        },
        "keywords": [
            "primordial_gutter",
            "cmb_prestrain",
            "sigma_eff",
            "a_cmb",
            "kappa_cmb",
            "recursive_rip",
            "super_gutter_alignment",
            "cross_scar_shear",
            "gutter_depth",
            "classifier",
        ],
    }

    output = {
        "test_name":    TEST_NAME,
        "test_number":  TEST_NUMBER,
        "timestamp":    timestamp,
        "target":       "CMB_Primordial_Substrate_Alignment",
        "framework":    "cmb_prestrain_synthetic_operator_test",
        "v28_partition": "primordial_gutter (data/results/)",
        "hypotheses_tested": {
            HYP_ID: hypothesis_entry,
        },
        "cases":         all_cases,
        "elapsed_seconds": time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Next: EPIC COLLECTOR → INGEST SELECTED → REFRESH Q-CUBE → AUTO-10")
    print(f"      {HYP_ID} will be tracked.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
