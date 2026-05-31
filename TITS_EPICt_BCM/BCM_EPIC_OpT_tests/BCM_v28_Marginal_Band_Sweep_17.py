# -*- coding: utf-8 -*-
"""
BCM_v28_Marginal_Band_Sweep_17.py  (rebuild — corpus reader)

Purpose
-------
Characterize the MARGINAL classifier band using REAL corpus data from
the v19 combined drain + chi tests and v25 cube2 phase reconciliation
tests — the exact files producing the 1777 STABLE Cube 2 anomalies
(all 10/10 persistent) in the AUTO-10 cube export of 2026-05-09.

Why the v1 proxy failed
-----------------------
The first version ran a simplified 0D sigma-ODE that settled to
DIFFUSIVE_HEALING everywhere. That showed the MARGINAL band cannot
be reproduced without the full 2D SubstrateSolver wave dynamics.
Finding: MARGINAL is an emergent wave-field regime, not a scalar
parameter boundary. This rebuild reads ACTUAL corpus data.

coh_est formula (verbatim from qt_layer.py / v25 test 3 lines 566-582)
-----------------------------------------------------------------------
    mag = |growth_rate|
    mag < 1e-5  -> coh = 1.0   (DIFFUSIVE_HEALING)
    mag > 1e-3  -> coh = 0.0   (BOUNDARY_NONLINEAR)
    else        -> coh = 1.0 - (mag - 1e-5) / (1e-3 - 1e-5)

coh_est is DERIVED from |growth_rate|, not a field measurement.
MARGINAL band maps to |growth_rate| in [~6e-5, ~1.6e-4].

Three classifiers
-----------------
  v19 test_zone        : sign(growth_rate) -> GREEN / YELLOW / RED
  v24 regime           : coh_est thresholds -> DIFFUSIVE_HEALING / MARGINAL /
                                               COHERENCE_FAILURE / BOUNDARY_NONLINEAR
  v28 marginal_band_flag (NEW): coh_est in [MARG_COH_LO, MARG_COH_HI]

Corpus sources
--------------
  BCM_v19_combined_drain_chi_*.json
  BCM_v25_cube2_phase_reconciliation_3_*.json
  BCM_v25_cube2_phase_reconciliation_7_*.json

Hypothesis: H_V28_MARGINAL_BAND_BOUNDARY_REAL
  MARGINAL is a physically distinct attractor between DIFFUSIVE_HEALING
  and COHERENCE_FAILURE detectable by the joint (growth_rate, coh_est)
  gate. Band confirmed if divergence_rate > 0.20 AND marginal_fraction
  > 0.15 in the real corpus.

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems -- 2026
All theoretical IP: Burdick.
"""

import glob
import json
import os
import sys
import time
from datetime import datetime

import numpy as np

# ============================================================================
# PATH RESOLUTION  (two-level climb: TITS_EPICt_BCM/BCM_EPIC_OpT_tests -> root)
# ============================================================================
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_SOLVER_ROOT  = os.path.dirname(os.path.dirname(_THIS_DIR))
_DATA_RESULTS = os.path.join(_SOLVER_ROOT, "data", "results")

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_Marginal_Band_Sweep_17"
TEST_NUMBER = 17
HYP_ID      = "H_V28_MARGINAL_BAND_BOUNDARY_REAL"

# ============================================================================
# FROZEN CONSTANTS (Work Formulas Sections 2, 8)
# ============================================================================
BRUCETRON_HEMORRHAGE         = 0.0045
CHI_C                        = 0.002582
REGIME_DIFFUSIVE_HEALING_MIN = 0.95
COHERENCE_YELLOW             = 0.85
REGIME_COHERENCE_FAILURE_MIN = 0.74

# v28 MARGINAL band gate (new -- this test validates them)
MARG_COH_LO = 0.82   # buffer below COHERENCE_FAILURE ceiling
MARG_COH_HI = 0.97   # buffer below DIFFUSIVE_HEALING floor

# Corpus file patterns (relative to data/results/)
CORPUS_PATTERNS = [
    "BCM_v19_combined_drain_chi_*.json",
    "BCM_v25_cube2_phase_reconciliation_3_*.json",
    "BCM_v25_cube2_phase_reconciliation_7_*.json",
]


# ============================================================================
# COH_EST FORMULA  (verbatim from qt_layer.py / v25 test 3)
# ============================================================================

def compute_coh_est(growth_rate):
    """
    v24 coherence estimate derived from growth_rate magnitude.
    Verbatim from qt_layer.py -- how Cube 2 computes coh_est on ingestion.
    """
    if growth_rate is None:
        return None
    mag = abs(float(growth_rate))
    if mag < 1e-5:
        return 1.0
    elif mag > 1e-3:
        return 0.0
    else:
        return 1.0 - (mag - 1e-5) / (1e-3 - 1e-5)


# ============================================================================
# THREE CLASSIFIERS
# ============================================================================

def classify_test_zone(growth_rate):
    """v19 test_zone: sign of growth_rate (verbatim v19 source lines 425-431)."""
    if growth_rate < -1e-6:
        return "GREEN"
    elif abs(growth_rate) < 1e-6:
        return "YELLOW"
    else:
        return "RED"


def classify_regime(coh_est):
    """v24 regime: coh_est thresholds (verbatim qt_layer.py Cube2Substrate)."""
    if coh_est is None:
        return None
    if coh_est >= REGIME_DIFFUSIVE_HEALING_MIN:
        return "DIFFUSIVE_HEALING"
    elif coh_est >= COHERENCE_YELLOW:
        return "MARGINAL"
    elif coh_est >= REGIME_COHERENCE_FAILURE_MIN:
        return "COHERENCE_FAILURE"
    else:
        return "BOUNDARY_NONLINEAR"


def get_marginal_band_flag(coh_est):
    """v28 marginal_band_flag: joint coh gate (NEW -- this test defines it)."""
    if coh_est is None:
        return False
    return MARG_COH_LO <= coh_est <= MARG_COH_HI


def zones_agree(test_zone, regime):
    """
    v25 agreement rule (verbatim v25 test 3 zones_in_agreement lines 601-616).
    GREEN  <-> DIFFUSIVE_HEALING or MARGINAL
    YELLOW <-> MARGINAL
    RED    <-> COHERENCE_FAILURE or BOUNDARY_NONLINEAR
    """
    if regime is None:
        return False
    if test_zone == "GREEN":
        return regime in ("DIFFUSIVE_HEALING", "MARGINAL")
    if test_zone == "YELLOW":
        return regime == "MARGINAL"
    if test_zone == "RED":
        return regime in ("COHERENCE_FAILURE", "BOUNDARY_NONLINEAR")
    return False


# ============================================================================
# CORPUS PARSERS
# ============================================================================

def parse_v19_file(data, source_file):
    """
    Schema: {"results": [{"lambda": lam, "configs": [{"name": ...,
             "growth_rate": ..., "bruce_rms": ..., "zone": ...}]}]}
    v19 does not pre-compute coh_est -- computed here.
    """
    samples = []
    for block in data.get("results", []):
        lam = block.get("lambda")
        for cfg in block.get("configs", []):
            growth = cfg.get("growth_rate")
            if growth is None:
                continue
            coh = compute_coh_est(growth)
            zone = cfg.get("zone") or cfg.get("test_zone")
            samples.append({
                "source":      source_file,
                "schema":      "v19",
                "name":        cfg.get("name", "unnamed"),
                "lambda_val":  float(lam) if lam is not None else None,
                "growth_rate": float(growth),
                "bruce_rms":   float(cfg.get("bruce_rms", 0.0)),
                "phi_rms":     float(cfg.get("phi_rms", 0.0)),
                "chi_op_late": float(cfg.get("chi_op_late", 0.0)),
                "test_zone":   zone,
                "coh_est":     float(coh) if coh is not None else None,
            })
    return samples


def parse_v25_flat_file(data, source_file):
    """
    Schema: {"results": [{"config_name": ..., "lambda_val": ...,
             "growth_rate": ..., "coh_est": ..., "test_zone": ...,
             "regime": ..., "divergence_flag": ...}]}
    coh_est is pre-computed; use it directly.
    """
    samples = []
    for cfg in data.get("results", []):
        if not isinstance(cfg, dict):
            continue
        growth = cfg.get("growth_rate")
        if growth is None:
            continue
        coh = cfg.get("coh_est")
        if coh is None:
            coh = compute_coh_est(growth)
        samples.append({
            "source":       source_file,
            "schema":       "v25_flat",
            "name":         cfg.get("config_name") or cfg.get("name", "unnamed"),
            "lambda_val":   cfg.get("lambda_val"),
            "growth_rate":  float(growth),
            "bruce_rms":    float(cfg.get("bruce_rms", 0.0)),
            "phi_rms":      float(cfg.get("phi_rms", 0.0)),
            "chi_op_late":  float(cfg.get("chi_op_late", 0.0)),
            "test_zone":    cfg.get("test_zone"),
            "coh_est":      float(coh) if coh is not None else None,
            "regime_v25":   cfg.get("regime"),
            "divergence_v25": cfg.get("divergence_flag"),
        })
    return samples


def detect_schema(data):
    """Detect v19 vs v25_flat schema from first results entry."""
    results = data.get("results", [])
    if not results:
        return "unknown"
    first = results[0]
    if not isinstance(first, dict):
        return "unknown"
    if "configs" in first and "lambda" in first:
        return "v19"
    if "lambda_val" in first or "config_name" in first or "growth_rate" in first:
        return "v25_flat"
    return "unknown"


def load_corpus(data_results_dir):
    """Find and parse all matching corpus files. Returns (samples, file_list)."""
    all_samples = []
    files_loaded = []

    for pattern in CORPUS_PATTERNS:
        for fpath in sorted(glob.glob(os.path.join(data_results_dir, pattern))):
            fname = os.path.basename(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"  WARNING: could not load {fname}: {e}")
                continue

            schema = detect_schema(data)
            if schema == "v19":
                samples = parse_v19_file(data, fname)
            elif schema == "v25_flat":
                samples = parse_v25_flat_file(data, fname)
            else:
                print(f"  SKIP (unknown schema): {fname}")
                continue

            print(f"  Loaded {len(samples):>3} samples  [{schema}]  {fname}")
            all_samples.extend(samples)
            files_loaded.append(fname)

    return all_samples, files_loaded


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()

    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 72)
    print(f"BCM v28 MARGINAL BAND SWEEP -- Test {TEST_NUMBER}  (corpus reader)")
    print(f"Corpus dir : {_DATA_RESULTS}")
    print(f"Hypothesis : {HYP_ID}")
    print("=" * 72)

    print("\nCORPUS LOAD:")
    all_samples, files_loaded = load_corpus(_DATA_RESULTS)

    if not all_samples:
        print("\nERROR: no corpus samples found.")
        print(f"Expected files in: {_DATA_RESULTS}")
        for p in CORPUS_PATTERNS:
            print(f"  {p}")
        return 1

    total = len(all_samples)
    print(f"\n  Total samples: {total}  from {len(files_loaded)} file(s)")

    # ------------------------------------------------------------------
    # APPLY THREE CLASSIFIERS
    # ------------------------------------------------------------------
    classified = []
    regime_counts = {k: 0 for k in
                     ("DIFFUSIVE_HEALING","MARGINAL","COHERENCE_FAILURE",
                      "BOUNDARY_NONLINEAR")}
    zone_counts   = {k: 0 for k in ("GREEN","YELLOW","RED")}

    agree_count   = 0
    diverge_count = 0
    marginal_count = 0
    marginal_growths = []
    marginal_cohs    = []
    diverge_marginal_red  = 0
    diverge_cohfail_green = 0

    for s in all_samples:
        growth = s["growth_rate"]
        coh    = s["coh_est"]

        tz     = s.get("test_zone") or classify_test_zone(growth)
        regime = classify_regime(coh)
        m_flag = get_marginal_band_flag(coh)
        agree  = zones_agree(tz, regime)

        classified.append({**s,
            "test_zone_v28":      tz,
            "regime_v28":         regime,
            "marginal_band_flag": m_flag,
            "classifier_agree":   agree,
        })

        if regime in regime_counts:
            regime_counts[regime] += 1
        if tz in zone_counts:
            zone_counts[tz] += 1

        if agree:
            agree_count += 1
        else:
            diverge_count += 1
            if regime == "MARGINAL"          and tz == "RED":
                diverge_marginal_red  += 1
            if regime == "COHERENCE_FAILURE" and tz == "GREEN":
                diverge_cohfail_green += 1

        if m_flag:
            marginal_count += 1
            marginal_growths.append(growth)
            marginal_cohs.append(coh)

    # ------------------------------------------------------------------
    # SUMMARY METRICS
    # ------------------------------------------------------------------
    agreement_rate  = agree_count  / total
    divergence_rate = diverge_count / total
    marginal_frac   = marginal_count / total

    mean_growth_marginal = float(np.mean(marginal_growths)) if marginal_growths else 0.0
    std_growth_marginal  = float(np.std(marginal_growths))  if len(marginal_growths) > 1 else 0.0
    mean_coh_marginal    = float(np.mean(marginal_cohs))    if marginal_cohs else 0.0
    std_coh_marginal     = float(np.std(marginal_cohs))     if len(marginal_cohs) > 1 else 0.0

    coherence_score  = (max(0.0, 1.0 - std_coh_marginal / 0.15)
                        if len(marginal_cohs) > 1 else
                        0.5 if marginal_count == 1 else 0.0)
    overlap_fraction = divergence_rate
    band_confirmed   = (divergence_rate > 0.20 and marginal_frac > 0.15)

    # ------------------------------------------------------------------
    # PRINT RESULTS (MARGINAL and DIVERGE only to keep output manageable)
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("MARGINAL + DIVERGE SAMPLES:")
    print(f"  {'NAME':<42} {'ZONE':<8} {'REGIME':<22} {'MARG':<6} {'AGREE'}")
    print("-" * 92)
    shown = 0
    for r in classified:
        if r["marginal_band_flag"] or not r["classifier_agree"]:
            name = str(r.get("name", ""))[:41]
            print(
                f"  {name:<42} "
                f"{str(r['test_zone_v28']):<8} "
                f"{str(r['regime_v28']):<22} "
                f"{str(r['marginal_band_flag']):<6} "
                f"{'AGREE' if r['classifier_agree'] else 'DIVERGE'}"
            )
            shown += 1
            if shown >= 50:
                remaining = sum(
                    1 for x in classified[shown:]
                    if x["marginal_band_flag"] or not x["classifier_agree"]
                )
                print(f"  ... ({remaining} more not shown)")
                break

    print()
    print("=" * 72)
    print("SUMMARY")
    print(f"  Files loaded        : {len(files_loaded)}")
    print(f"  Total samples       : {total}")
    print(f"  MARGINAL flagged    : {marginal_count}  ({marginal_frac*100:.1f}%)")
    print(f"  Classifier agree    : {agree_count}  ({agreement_rate*100:.1f}%)")
    print(f"  Classifier diverge  : {diverge_count}  ({divergence_rate*100:.1f}%)")
    print(f"    - MARGINAL+RED    : {diverge_marginal_red}")
    print(f"    - COHFAIL+GREEN   : {diverge_cohfail_green}")
    print(f"  Regime distribution : {regime_counts}")
    print(f"  Zone distribution   : {zone_counts}")
    if marginal_count > 0:
        print(f"  Mean growth (MARG)  : {mean_growth_marginal:.4e}")
        print(f"  Std  growth (MARG)  : {std_growth_marginal:.4e}")
        print(f"  Mean coh (MARG)     : {mean_coh_marginal:.4f}")
        print(f"  Std  coh (MARG)     : {std_coh_marginal:.4f}")
    print(f"  coherence_score     : {coherence_score:.4f}")
    print(f"  overlap_fraction    : {overlap_fraction:.4f}")
    print(f"  Band confirmed      : {band_confirmed}")
    print("=" * 72)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT (Test 13 pattern)
    # ------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"Corpus reader applied three classifiers to {total} real samples "
        f"from {len(files_loaded)} file(s) "
        f"(v19 combined drain chi + v25 cube2 phase reconciliation 3/7). "
        f"These are the exact files generating 1777 STABLE Cube 2 anomalies "
        f"(all 10/10) in AUTO-10 cube export 2026-05-09. "
        f"coh_est verbatim from qt_layer.py: "
        f"1-(mag-1e-5)/(1e-3-1e-5) for mag=|growth_rate| in [1e-5,1e-3]. "
        f"v28 marginal_band_flag: coh_est in [{MARG_COH_LO}, {MARG_COH_HI}]. "
        f"divergence_rate={divergence_rate:.4f}  "
        f"marginal_fraction={marginal_frac:.4f}  "
        f"MARGINAL+RED={diverge_marginal_red}  "
        f"COHFAIL+GREEN={diverge_cohfail_green}. "
        f"Band confirmed={band_confirmed} "
        f"(requires divergence_rate>0.20 AND marginal_fraction>0.15). "
        f"v1 proxy finding: simplified 0D ODE yields DIFFUSIVE_HEALING "
        f"everywhere -- MARGINAL is emergent wave-field regime of 2D solver."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if band_confirmed else 0,
        "evidence_type": "primary",
        "pass_count":    0,
        "total_configs": total,
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":           coherence_score,
            "overlap_fraction":          overlap_fraction,
            "total_samples":             total,
            "files_loaded":              len(files_loaded),
            "marginal_count":            marginal_count,
            "marginal_fraction":         float(marginal_frac),
            "agree_count":               agree_count,
            "diverge_count":             diverge_count,
            "agreement_rate":            float(agreement_rate),
            "divergence_rate":           float(divergence_rate),
            "diverge_marginal_red":      diverge_marginal_red,
            "diverge_cohfail_green":     diverge_cohfail_green,
            "mean_growth_marginal":      float(mean_growth_marginal),
            "std_growth_marginal":       float(std_growth_marginal),
            "mean_coh_marginal":         float(mean_coh_marginal),
            "std_coh_marginal":          float(std_coh_marginal),
            "band_confirmed":            band_confirmed,
            "regime_diffusive_healing":  regime_counts["DIFFUSIVE_HEALING"],
            "regime_marginal":           regime_counts["MARGINAL"],
            "regime_coherence_failure":  regime_counts["COHERENCE_FAILURE"],
            "regime_boundary_nonlinear": regime_counts["BOUNDARY_NONLINEAR"],
            "zone_green":                zone_counts["GREEN"],
            "zone_yellow":               zone_counts["YELLOW"],
            "zone_red":                  zone_counts["RED"],
            "v1_proxy_finding": (
                "0D_ODE_gives_DIFFUSIVE_HEALING_everywhere_"
                "MARGINAL_is_emergent_wave_field_regime"
            ),
            "marg_coh_lo":              MARG_COH_LO,
            "marg_coh_hi":              MARG_COH_HI,
            "cube2_stable_anomalies":   1777,
        },
        "context": {
            "corpus_patterns":    CORPUS_PATTERNS,
            "files_loaded":       files_loaded,
            "coh_est_formula":    "1-(mag-1e-5)/(1e-3-1e-5), mag=|growth_rate|",
            "brucetron_hemorrhage": BRUCETRON_HEMORRHAGE,
            "chi_c":              CHI_C,
            "framework":          "corpus_reader_three_classifier_sweep",
        },
        "keywords": [
            "classifier_divergence",
            "test_zone",
            "regime",
            "diffusive_lock",
            "fracture_lambda",
            "attractor",
            "regime_classification_confidence",
            "brucetron",
            "lambda",
            "classifier",
        ],
    }

    output = {
        "test_name":    TEST_NAME,
        "test_number":  TEST_NUMBER,
        "timestamp":    timestamp,
        "target":       "Cube2_Marginal_Band_Real_Corpus",
        "framework":    "corpus_reader_three_classifier_sweep",
        "v28_partition": "cube2_classifier_resolution (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "elapsed_seconds": time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Next: EPIC COLLECTOR -> INGEST SELECTED -> REFRESH Q-CUBE -> AUTO-10")

    return 0


if __name__ == "__main__":
    sys.exit(main())
