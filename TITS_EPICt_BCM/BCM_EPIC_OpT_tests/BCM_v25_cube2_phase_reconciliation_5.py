# -*- coding: utf-8 -*-
"""
BCM v25 -- Cube 2 Phase Reconciliation Test 5
===============================================
Observer Reconciliation + Genesis Trail
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick. Claude is code executor only.

PRIMACY STATEMENT
-----------------
Burdick Crag Mass (BCM) is the sole theoretical framework of Stephen
Justin Burdick Sr. This test is built under his direction per
contract BCM_TEST_TEMPLATE_CONTRACT.py v1.1. ChatGPT specified the
observer reconciliation framework. Grok specified the genesis trail
architecture (JSONL, append-only, bidirectional provenance). Claude
implements exactly to final spec.

PURPOSE
-------
Tests 3 and 4 surfaced 500 STABLE anomalies in Cube 2. They are not
500 physics discoveries -- they are the same classification mismatch
repeated. The cube has become a phase-boundary detector, not an
anomaly detector.

Test 5 is the ontology refinement: prove that DIFFUSIVE_LOCK is a
real regime distinct from DIFFUSIVE_HEALING, so the cube can stop
flagging the same observer-mismatch as new anomalies.

This test runs NO PHYSICS. It is pure meta-analysis of existing T3
and T4 JSON outputs. Per ChatGPT: "Do not run another lambda sweep.
You already resolved the boundary. You need a classification
reconciliation test, not a physics test."

HYPOTHESES (H7, H8, H9 per ChatGPT spec)
----------------------------------------
  H7  DIFFUSIVE_LOCK_SEPARATES_FROM_DIFFUSIVE
      Distribution separability between lock=True and lock=False
      within regime=DIFFUSIVE_HEALING samples.
      Metric: KS-statistic (scipy if available, numpy fallback).
      PASS: separability >= 0.70

  H8  TEST_ZONE_FAILS_ON_LOCK_STATE
      P(test_zone == "RED" | lock_flag == True)
      PASS: >= 0.80 (classifier blind spot confirmed)

  H9  REGIME_COLLAPSES_TWO_STATES
      Fraction of lock=True samples where regime == "DIFFUSIVE_HEALING"
      PASS: == 1.00 (regime is coarse-grained, needs splitting)

GENESIS TRAIL (Grok architecture)
---------------------------------
If H7, H8, H9 all PASS, test appends a proposal line to:
  TITS_EPICt_BCM/genesis_brain/vocabulary_genesis.jsonl

Proposal includes: timestamp, proposal_id, evidence, threshold_spec,
source_data filenames, status=PROPOSED, foreman_review=PENDING.
Never auto-approved. Never modifies hypothesis_vocabulary.py directly.
Foreman reviews and manually propagates if approved. The log is
append-only; rejected proposals stay forever as evidence of rigor.

OUTPUT JSON: data/results/BCM_v25_cube2_phase_reconciliation_5_{ts}.json
GENESIS LOG: TITS_EPICt_BCM/genesis_brain/vocabulary_genesis.jsonl
"""

import os
import sys
import json
import time
import glob
import argparse


# Bootstrap path chain (contract compliance)
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)


# ============================================================================
# LOCKED THRESHOLDS (carried from Test 4, unchanged)
# ============================================================================
LOCK_CHI_OP_MAX    = 0.005
LOCK_COH_EST_MIN   = 0.97
LOCK_GROWTH_MAGMAX = 1e-4


# ============================================================================
# HYPOTHESES (per ChatGPT specification)
# ============================================================================

HYPOTHESES = {
    "DIFFUSIVE_LOCK_SEPARATES_FROM_DIFFUSIVE": {
        "statement": (
            "Distributions of lock_flag=True vs lock_flag=False samples "
            "(within regime=DIFFUSIVE_HEALING) are statistically distinct. "
            "Metric: KS-statistic on growth_rate distributions."),
        "keywords": ["diffusive_lock", "separability", "distribution",
                     "attractor_state"],
        "cube_target": 2,
        "metric": "H7_ks_separability",
        "pass_condition": "H7_ks_separability >= 0.70",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["lock_flag"],
        "context_hold": ["regime", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "TEST_ZONE_FAILS_ON_LOCK_STATE": {
        "statement": (
            "When lock_flag=True, test_zone classifies RED in >= 80% "
            "of cases. Confirms classifier blind spot in the lock basin."),
        "keywords": ["test_zone", "lock_state", "classifier_blindspot",
                     "definition_mismatch"],
        "cube_target": 2,
        "metric": "H8_test_zone_red_rate_under_lock",
        "pass_condition": "H8_test_zone_red_rate_under_lock >= 0.80",
        "bucket": "DEFINITION_MISMATCH",
        "context_vary": ["lock_flag"],
        "context_hold": ["physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "REGIME_COLLAPSES_TWO_STATES": {
        "statement": (
            "All lock_flag=True samples have regime == 'DIFFUSIVE_HEALING'. "
            "Confirms regime classification is coarse-grained and collapses "
            "two distinct physical states into one label."),
        "keywords": ["regime", "coarse_graining", "state_collapse",
                     "ontology_refinement"],
        "cube_target": 2,
        "metric": "H9_regime_collapse_rate",
        "pass_condition": "H9_regime_collapse_rate >= 1.00",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["lock_flag"],
        "context_hold": ["physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
}


def evaluate_hypothesis(hyp_key, metric_value):
    """Evaluate hypothesis against aggregate metric."""
    hyp = HYPOTHESES[hyp_key]
    metric = hyp["metric"]
    condition = hyp["pass_condition"]
    try:
        expr = condition.replace(metric, str(float(metric_value)))
        ok = bool(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return {"observed_value": float(metric_value),
                "result": "ERROR", "direction": 0,
                "confidence": "LOW", "error": str(e)}
    return {
        "observed_value": float(metric_value),
        "result":    "PASS" if ok else "FAIL",
        "direction": +1 if ok else -1,
        "confidence": "HIGH",
        "pass_count":    1 if ok else 0,
        "fail_count":    0 if ok else 1,
    }


# ============================================================================
# INPUT DISCOVERY
# ============================================================================

def discover_test_jsons(results_dir, explicit_t3=None, explicit_t4=None):
    """
    Auto-discover latest T3 and T4 JSONs, or use explicit paths.
    Returns (t3_path, t4_path). Raises on missing.
    """
    if explicit_t3 and explicit_t4:
        if not os.path.exists(explicit_t3):
            raise FileNotFoundError(f"T3 JSON not found: {explicit_t3}")
        if not os.path.exists(explicit_t4):
            raise FileNotFoundError(f"T4 JSON not found: {explicit_t4}")
        return explicit_t3, explicit_t4

    t3_pat = os.path.join(
        results_dir, "BCM_v25_cube2_phase_reconciliation_3_*.json")
    t4_pat = os.path.join(
        results_dir, "BCM_v25_cube2_phase_reconciliation_4_*.json")

    t3_files = sorted(glob.glob(t3_pat))
    t4_files = sorted(glob.glob(t4_pat))

    if not t3_files:
        raise FileNotFoundError(
            f"No Test 3 JSONs found matching: {t3_pat}")
    if not t4_files:
        raise FileNotFoundError(
            f"No Test 4 JSONs found matching: {t4_pat}")

    # Latest = last after sort (timestamps are in filenames)
    return t3_files[-1], t4_files[-1]


def load_samples(t3_path, t4_path):
    """
    Load T3 and T4 JSONs, return unified sample list with metadata.
    Each sample is annotated with source_test and original filename.
    """
    samples = []
    for path, label in [(t3_path, "T3"), (t4_path, "T4")]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        fname = os.path.basename(path)
        for r in data.get("results", []):
            s = dict(r)  # shallow copy
            s["source_test"] = label
            s["source_file"] = fname
            samples.append(s)
    return samples


# ============================================================================
# LOCK FLAG (applied retroactively to all samples)
# ============================================================================

def compute_lock_flag(sample):
    """
    Apply lock_flag definition to a sample. Samples from T4 already have
    this field; T3 samples do not. Compute from raw physics where
    needed.
    """
    if "diffusive_lock_flag" in sample:
        return bool(sample["diffusive_lock_flag"])
    chi_op = sample.get("chi_op_late", sample.get("chi_op", None))
    coh_est = sample.get("coh_est", None)
    growth = sample.get("growth_rate", sample.get("growth", None))
    if chi_op is None or coh_est is None or growth is None:
        return False
    return (chi_op < LOCK_CHI_OP_MAX
            and coh_est > LOCK_COH_EST_MIN
            and abs(growth) < LOCK_GROWTH_MAGMAX)


# ============================================================================
# METRICS (H7, H8, H9)
# ============================================================================

def compute_H7_separability(samples):
    """
    H7: KS statistic comparing growth_rate distributions for
    lock=True vs lock=False samples WITHIN regime=DIFFUSIVE_HEALING.

    Uses scipy.stats.ks_2samp if available; numpy fallback otherwise.
    Returns KS statistic in [0, 1] where higher = more separable.
    """
    locked = [s for s in samples
              if s.get("regime") == "DIFFUSIVE_HEALING"
              and compute_lock_flag(s)]
    unlocked = [s for s in samples
                if s.get("regime") == "DIFFUSIVE_HEALING"
                and not compute_lock_flag(s)]

    # Extract growth values
    g_locked = [float(s.get("growth_rate",
                             s.get("growth", 0.0)))
                for s in locked]
    g_unlocked = [float(s.get("growth_rate",
                               s.get("growth", 0.0)))
                  for s in unlocked]

    n_locked = len(g_locked)
    n_unlocked = len(g_unlocked)

    if n_locked < 2 or n_unlocked < 2:
        # Insufficient data -- return marginal value (favors FAIL)
        return 0.0, n_locked, n_unlocked

    # Try scipy first, numpy fallback
    try:
        from scipy.stats import ks_2samp
        stat, _pval = ks_2samp(g_locked, g_unlocked)
        return float(stat), n_locked, n_unlocked
    except ImportError:
        # Numpy fallback: compute KS stat manually
        import numpy as np
        a = np.sort(np.array(g_locked))
        b = np.sort(np.array(g_unlocked))
        # Combined sorted unique values
        all_vals = np.sort(np.concatenate([a, b]))
        # ECDFs at each point
        cdf_a = np.searchsorted(a, all_vals, side='right') / len(a)
        cdf_b = np.searchsorted(b, all_vals, side='right') / len(b)
        stat = float(np.max(np.abs(cdf_a - cdf_b)))
        return stat, n_locked, n_unlocked


def compute_H8_test_zone_red_rate(samples):
    """
    H8: P(test_zone == "RED" | lock_flag == True).
    Of all locked samples, what fraction have test_zone=RED?
    """
    locked = [s for s in samples if compute_lock_flag(s)]
    if not locked:
        return 0.0, 0, 0
    red_locked = sum(1 for s in locked
                     if s.get("test_zone") == "RED")
    return red_locked / len(locked), red_locked, len(locked)


def compute_H9_regime_collapse(samples):
    """
    H9: Fraction of lock=True samples where regime == "DIFFUSIVE_HEALING".
    If 1.0 -> regime collapses both states into one label.
    """
    locked = [s for s in samples if compute_lock_flag(s)]
    if not locked:
        return 0.0, 0, 0
    dh_count = sum(1 for s in locked
                   if s.get("regime") == "DIFFUSIVE_HEALING")
    return dh_count / len(locked), dh_count, len(locked)


# ============================================================================
# GENESIS TRAIL WRITER (Grok architecture)
# ============================================================================

def get_genesis_log_path():
    """Return canonical genesis log path."""
    return os.path.join(
        _PROJECT_ROOT, "TITS_EPICt_BCM", "genesis_brain",
        "vocabulary_genesis.jsonl")


def ensure_genesis_log(log_path):
    """
    Create the genesis log with a header line if it doesn't exist.
    Header is a JSON object with a leading '_comment' field; parsers
    can filter it out or ignore it.
    """
    if os.path.exists(log_path):
        return False  # already exists
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    header = {
        "_comment": "BCM_VOCABULARY_GENESIS_LOG",
        "_schema": "jsonl_append_only",
        "_created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "_owner": "Stephen Justin Burdick Sr. (Foreman)",
        "_purpose": (
            "Append-only audit trail of vocabulary evolution proposals "
            "from AI cube analysis. Each proposal requires manual "
            "Foreman review. Rejected proposals are preserved as "
            "evidence of rigorous hypothesis testing. Never rewrite."),
        "_parsing_note": (
            "Lines where '_comment' or '_schema' is present are "
            "metadata; skip them when iterating proposals."),
    }
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")
    return True


def next_proposal_id(log_path):
    """
    Scan the log and return the next proposal_id as a zero-padded string.
    If log doesn't exist or has no proposals, returns '001'.
    """
    if not os.path.exists(log_path):
        return "001"
    max_id = 0
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if "_comment" in obj or "_schema" in obj:
                    continue
                pid = obj.get("proposal_id")
                if pid is None:
                    continue
                try:
                    n = int(str(pid))
                    if n > max_id:
                        max_id = n
                except ValueError:
                    pass
    except Exception:
        pass
    return f"{(max_id + 1):03d}"


def append_genesis_proposal(log_path, proposal):
    """Append a single proposal as a JSON line to the genesis log."""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(proposal) + "\n")


def build_proposal_record(proposal_id, metrics_results, source_files):
    """
    Build the full proposal record per Grok's schema.
    Only called when H7, H8, H9 all PASS.
    """
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000000"),
        "proposal_id": proposal_id,
        "proposer": "Test 5",
        "test_name": "BCM_v25_cube2_phase_reconciliation_5",
        "proposed_term": "DIFFUSIVE_LOCK",
        "proposal_type": "SPLIT_REGIME",
        "parent_regime": "DIFFUSIVE_HEALING",
        "evidence": {
            "H7_separability": {
                "observed":  round(
                    metrics_results["H7_ks_separability"], 6),
                "threshold": ">=0.70",
                "result":    metrics_results["H7_result"],
            },
            "H8_test_zone_failure": {
                "observed":  round(
                    metrics_results["H8_test_zone_red_rate_under_lock"],
                    6),
                "threshold": ">=0.80",
                "result":    metrics_results["H8_result"],
            },
            "H9_regime_collapse": {
                "observed":  round(
                    metrics_results["H9_regime_collapse_rate"], 6),
                "threshold": ">=1.00",
                "result":    metrics_results["H9_result"],
            },
        },
        "threshold_spec": {
            "chi_op":      f"<{LOCK_CHI_OP_MAX}",
            "coh_est":     f">{LOCK_COH_EST_MIN}",
            "abs_growth":  f"<{LOCK_GROWTH_MAGMAX}",
        },
        "source_data":       source_files,
        "status":            "PROPOSED",
        "foreman_review":    "PENDING",
        "reviewer":          "Stephen Justin Burdick Sr.",
        "review_date":       None,
        "review_verdict":    None,
        "lineage_note": (
            "Hypothesis lineage from cube2 phase reconciliation "
            "series (T3 -> T4 -> T5). ChatGPT specified reconciliation "
            "framework; Grok specified genesis trail architecture; "
            "Foreman Burdick owns all theoretical decisions."),
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=("BCM v25 -- Cube 2 Phase Reconciliation Test 5 "
                     "(observer reconciliation, pure analysis)"))
    parser.add_argument("--test3-json", type=str, default=None,
                        help="Explicit path to Test 3 JSON (overrides auto)")
    parser.add_argument("--test4-json", type=str, default=None,
                        help="Explicit path to Test 4 JSON (overrides auto)")
    parser.add_argument("--no-log", action="store_true",
                        help=("Skip writing to genesis log "
                              "(for dry-runs / test harness use)"))
    args = parser.parse_args()

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")

    print("=" * 65)
    print("  BCM v25 -- CUBE 2 PHASE RECONCILIATION TEST 5")
    print("  Observer Reconciliation + Genesis Trail")
    print("  Stephen Justin Burdick Sr. -- GIBUSH Systems")
    print("=" * 65)

    # Discover input files
    try:
        t3_path, t4_path = discover_test_jsons(
            results_dir, args.test3_json, args.test4_json)
    except FileNotFoundError as e:
        print(f"\n  ERROR: {e}")
        print("  Cannot run Test 5 without prior test outputs.")
        print("  Run Test 3 and Test 4 first.")
        sys.exit(1)

    print(f"  T3 input: {os.path.basename(t3_path)}")
    print(f"  T4 input: {os.path.basename(t4_path)}")

    # Load samples
    t0 = time.time()
    samples = load_samples(t3_path, t4_path)
    n_total = len(samples)
    print(f"  Loaded {n_total} samples from T3 + T4 combined")

    # Breakdown
    n_locked = sum(1 for s in samples if compute_lock_flag(s))
    n_dh = sum(1 for s in samples
               if s.get("regime") == "DIFFUSIVE_HEALING")
    print(f"  Regime=DIFFUSIVE_HEALING: {n_dh}/{n_total}")
    print(f"  lock_flag=True:           {n_locked}/{n_total}")
    print("=" * 65)

    # Compute metrics
    print("\n  COMPUTING HYPOTHESES:\n")

    h7_stat, h7_n_locked, h7_n_unlocked = compute_H7_separability(samples)
    print(f"  H7 (separability):")
    print(f"    locked samples within DH: {h7_n_locked}")
    print(f"    unlocked samples within DH: {h7_n_unlocked}")
    print(f"    KS statistic: {h7_stat:.4f}")

    h8_rate, h8_red_count, h8_total = compute_H8_test_zone_red_rate(samples)
    print(f"\n  H8 (test_zone=RED under lock):")
    print(f"    RED count: {h8_red_count}/{h8_total}")
    print(f"    rate: {h8_rate:.4f}")

    h9_rate, h9_dh_count, h9_total = compute_H9_regime_collapse(samples)
    print(f"\n  H9 (regime collapse DIFFUSIVE_HEALING on lock):")
    print(f"    DH count: {h9_dh_count}/{h9_total}")
    print(f"    rate: {h9_rate:.4f}")

    metrics = {
        "H7_ks_separability":            h7_stat,
        "H7_locked_sample_count":        h7_n_locked,
        "H7_unlocked_sample_count":      h7_n_unlocked,
        "H8_test_zone_red_rate_under_lock": h8_rate,
        "H8_red_locked_count":           h8_red_count,
        "H8_total_locked_count":         h8_total,
        "H9_regime_collapse_rate":       h9_rate,
        "H9_diffusive_healing_count":    h9_dh_count,
        "H9_total_locked_count":         h9_total,
    }

    # Evaluate hypotheses
    print("\n  HYPOTHESIS EVALUATION:\n")
    hypotheses_tested = {}
    hypothesis_results_summary = {}
    for hkey, hdecl in HYPOTHESES.items():
        metric_name = hdecl["metric"]
        metric_value = metrics.get(metric_name, 0.0)
        eval_result = evaluate_hypothesis(hkey, metric_value)
        hypotheses_tested[hkey] = {**hdecl, **eval_result}
        hypothesis_results_summary[hkey] = eval_result["result"]
        print(f"    {hkey}: {eval_result['result']} "
              f"(observed={eval_result['observed_value']:.4f})")

    # Check if all three PASS -> propose vocabulary update
    all_pass = all(v == "PASS"
                   for v in hypothesis_results_summary.values())

    proposal_record = None
    genesis_log_action = "not_written"
    if all_pass and not args.no_log:
        # Prepare genesis log
        log_path = get_genesis_log_path()
        log_created = ensure_genesis_log(log_path)
        proposal_id = next_proposal_id(log_path)

        # Build metrics payload for proposal
        metrics_payload = {
            "H7_ks_separability":                 metrics[
                "H7_ks_separability"],
            "H7_result":                          hypothesis_results_summary[
                "DIFFUSIVE_LOCK_SEPARATES_FROM_DIFFUSIVE"],
            "H8_test_zone_red_rate_under_lock":   metrics[
                "H8_test_zone_red_rate_under_lock"],
            "H8_result":                          hypothesis_results_summary[
                "TEST_ZONE_FAILS_ON_LOCK_STATE"],
            "H9_regime_collapse_rate":            metrics[
                "H9_regime_collapse_rate"],
            "H9_result":                          hypothesis_results_summary[
                "REGIME_COLLAPSES_TWO_STATES"],
        }

        source_files = [
            os.path.basename(t3_path),
            os.path.basename(t4_path),
        ]

        proposal_record = build_proposal_record(
            proposal_id, metrics_payload, source_files)
        append_genesis_proposal(log_path, proposal_record)

        if log_created:
            genesis_log_action = f"created_and_proposal_{proposal_id}_appended"
        else:
            genesis_log_action = f"proposal_{proposal_id}_appended"

        print(f"\n  GENESIS TRAIL:")
        print(f"    Proposal ID:    {proposal_id}")
        print(f"    Proposed term:  DIFFUSIVE_LOCK")
        print(f"    Status:         PROPOSED (awaiting Foreman review)")
        print(f"    Log path:       {log_path}")

    elif all_pass and args.no_log:
        print(f"\n  GENESIS TRAIL: skipped (--no-log)")
    else:
        failed = [k for k, v in hypothesis_results_summary.items()
                  if v != "PASS"]
        print(f"\n  GENESIS TRAIL: no proposal generated "
              f"(one or more hypotheses did not PASS: {failed})")

    # Build output JSON
    elapsed_total = time.time() - t0
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = results_dir
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(
        out_dir,
        f"BCM_v25_cube2_phase_reconciliation_5_{timestamp}.json")

    output = {
        "test":              "cube2_phase_reconciliation_5",
        "version":           "v25",
        "test_type":         "observer_reconciliation",
        "predecessor_tests": [
            os.path.basename(t3_path),
            os.path.basename(t4_path),
        ],
        "total_samples_analyzed": n_total,
        "samples_with_lock_flag": n_locked,
        "samples_in_diffusive_healing": n_dh,
        "timestamp":         timestamp,
        "elapsed_total":     float(elapsed_total),
        "thresholds_used": {
            "LOCK_CHI_OP_MAX":    LOCK_CHI_OP_MAX,
            "LOCK_COH_EST_MIN":   LOCK_COH_EST_MIN,
            "LOCK_GROWTH_MAGMAX": LOCK_GROWTH_MAGMAX,
        },
        "aggregate_metrics": metrics,
        "hypotheses_tested": hypotheses_tested,
        "proposed_vocabulary_update": (
            proposal_record if proposal_record else None),
        "genesis_log_action": genesis_log_action,
        "foreman_note": (
            "Test 5: observer reconciliation (no new physics). "
            "Meta-analysis of T3 + T4 outputs to validate "
            "DIFFUSIVE_LOCK as a distinct regime requiring vocabulary "
            "update. ChatGPT specified H7-H9; Grok specified genesis "
            "trail JSONL architecture; Foreman Burdick reviews and "
            "approves any vocabulary changes. Cube proposes; cube "
            "never self-approves. Haptic-curve-level audit trail."),
        "results": [],  # Test 5 produces no per-config results
                        # (pure meta-analysis)
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 65}")
    print(f"  TEST 5 SUMMARY")
    print(f"{'=' * 65}")
    print(f"  Elapsed:       {elapsed_total:.2f}s")
    print(f"  Samples:       {n_total}")
    print(f"  All PASS:      {all_pass}")
    print(f"  JSON saved:    {out_path}")
    if proposal_record:
        print(f"  Genesis log:   {genesis_log_action}")


if __name__ == "__main__":
    main()
