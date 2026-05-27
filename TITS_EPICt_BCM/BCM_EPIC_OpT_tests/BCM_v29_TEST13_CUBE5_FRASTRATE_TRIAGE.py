# -*- coding: utf-8 -*-
"""
BCM v29 TEST13 — CUBE5 BUFFER / FRASTRATE TRIAGE
==================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Purpose:
    Classify the 98 Cube 5 (Buffer / Frastrate) anomalies by failure path.
    Identify gate candidates vs correct physics anomalies.

Cube 5 anomaly gates (qt_layer.py lines 996-1008):
    PATH A: commit_gate in (REFLECT, HARD_REFLECT)
            Pi ratio too high — boundary flooded or at collapse
    PATH B: frastrate_signal > 1e6
            Bruce at hemorrhage AND sigma completely stagnant

CRITICAL NOTE on sigma_crit estimate (qt_layer.py lines 880-885):
    sigma_crit_est = 10.0 * lambda_val  (v24 placeholder)
    This is explicitly flagged as uncalibrated in the source.
    Pi = sigma_scaled / sigma_crit_est
    Records triggering PATH A may be artifacts of the placeholder,
    not genuine boundary failures.

Classification scheme:
    FRASTRATE_RECALL      frastrate_signal > 1e6 (Path B — real crew signal)
    PI_REFLECT            Pi in REFLECT band (PI_MARGINAL=1.0 to PI_COLLAPSE=2.0)
    PI_HARD_REFLECT       Pi >= PI_COLLAPSE=2.0 (bulk flood)
    MIXED                 both paths firing simultaneously
    UNKNOWN_PATH          neither gate matched

Gate candidate criteria:
    PATH A records (PI_REFLECT / PI_HARD_REFLECT) are candidates IF:
      - frastrate_signal is NOT also > 1e6 (not a real crew event)
      - sigma_crit_est flag is SIGMA_CRIT_UNCALIBRATED
        (lambda was missing — Pi was computed without calibration)
    These may be placeholder artifacts. The FRASTRATE_RECALL path
    is real physics regardless of calibration state.

Output JSON keys:
    total_anomalies
    frastrate_recall_count   (Path B — correct physics)
    pi_reflect_count         (Path A only — review needed)
    pi_hard_reflect_count    (Path A only, Pi >= 2.0)
    mixed_count              (both paths)
    unknown_path_count
    gate_candidate_count     (Path A records where crit is uncalibrated)
    correct_physics_count
    pi_ratio_distribution    {min, max, mean, median}
    frastrate_signal_stats   {below_1e6, above_1e6}
    lambda_present_count     (lambda available for calibration)
    lambda_missing_count     (SIGMA_CRIT_UNCALIBRATED flag)
    source_files
    sample_candidates
    verdict
    hypothesis_key
"""

from __future__ import annotations

import json
import os
import sys
import statistics
from pathlib import Path
from datetime import datetime

# ── path setup ──────────────────────────────────────────────────────────────
_THIS_DIR    = Path(__file__).resolve().parent
_SOLVER_ROOT = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"

if str(_GENESIS_BRAIN) not in sys.path:
    sys.path.insert(0, str(_GENESIS_BRAIN))

from anchor_state import build_reduced_from_json
from qt_layer import QTStack, Cube5Buffer
from bcm_thresholds import PI_STABLE, PI_MARGINAL, PI_COLLAPSE, BRUCETRON_HEMORRHAGE

# ── thresholds ───────────────────────────────────────────────────────────────
FRASTRATE_RECALL_THRESHOLD = 1.0e6   # Path B gate
# PI_MARGINAL=1.0, PI_COLLAPSE=2.0 — from bcm_thresholds


def classify_anomaly(commit_gate, frastrate_signal, flags):
    """Return failure path label for one Cube 5 anomaly record."""
    path_a = commit_gate in ("REFLECT", "HARD_REFLECT")
    path_b = frastrate_signal is not None and frastrate_signal > FRASTRATE_RECALL_THRESHOLD

    if path_a and path_b:
        return "MIXED"
    if path_b:
        return "FRASTRATE_RECALL"
    if path_a:
        if commit_gate == "HARD_REFLECT":
            return "PI_HARD_REFLECT"
        return "PI_REFLECT"
    return "UNKNOWN_PATH"


def is_gate_candidate(path, flags):
    """
    Gate candidate: Path A only (not FRASTRATE_RECALL or MIXED)
    AND sigma_crit was uncalibrated (SIGMA_CRIT_UNCALIBRATED in flags).
    These Pi-based anomalies may be placeholder artifacts.
    """
    if path not in ("PI_REFLECT", "PI_HARD_REFLECT"):
        return False
    return "SIGMA_CRIT_UNCALIBRATED" in flags


def run_triage():
    json_files = sorted(_RESULTS_DIR.glob("*.json"))
    json_files = [f for f in json_files if not f.name.startswith("_")]

    if not json_files:
        print(f"ERROR: No JSON files found in {_RESULTS_DIR}")
        sys.exit(1)

    print(f"Scanning {len(json_files)} JSON files for Cube 5 anomalies...")

    cube5 = Cube5Buffer()

    counts = {
        "FRASTRATE_RECALL":  0,
        "PI_REFLECT":        0,
        "PI_HARD_REFLECT":   0,
        "MIXED":             0,
        "UNKNOWN_PATH":      0,
    }

    gate_candidates  = []
    correct_physics  = []
    all_anomalies    = []

    pi_ratios        = []
    fras_signals     = []
    fras_below_1e6   = 0
    fras_above_1e6   = 0
    lambda_present   = 0
    lambda_missing   = 0
    source_files     = set()

    for jf in json_files:
        try:
            states = build_reduced_from_json(jf)
        except Exception as e:
            print(f"  SKIP {jf.name}: {e}")
            continue

        for st in states:
            result = cube5.project(st)
            if result.state != "ANOMALY":
                continue

            commit_gate      = result.raw_metrics.get("commit_gate")
            frastrate_signal = result.raw_metrics.get("frastrate_signal")
            pi_ratio         = result.raw_metrics.get("pi_ratio")
            flags            = result.flags or []

            path = classify_anomaly(commit_gate, frastrate_signal, flags)
            counts[path] += 1

            if pi_ratio is not None:
                pi_ratios.append(pi_ratio)
            if frastrate_signal is not None:
                fras_signals.append(frastrate_signal)
                if frastrate_signal > FRASTRATE_RECALL_THRESHOLD:
                    fras_above_1e6 += 1
                else:
                    fras_below_1e6 += 1

            if "SIGMA_CRIT_UNCALIBRATED" in flags:
                lambda_missing += 1
            else:
                lambda_present += 1

            rec = {
                "source_file":      jf.name,
                "config_name":      st.config_name or "-",
                "commit_gate":      commit_gate,
                "pi_ratio":         pi_ratio,
                "frastrate_signal": frastrate_signal,
                "failure_path":     path,
                "flags":            flags,
                "anomaly_reason":   result.anomaly_reason,
            }
            all_anomalies.append(rec)
            source_files.add(jf.name)

            if is_gate_candidate(path, flags):
                gate_candidates.append(rec)
            else:
                correct_physics.append(rec)

    total        = len(all_anomalies)
    gate_count   = len(gate_candidates)
    correct_count = len(correct_physics)

    print(f"Total Cube 5 anomalies found: {total}")

    # ── distributions ────────────────────────────────────────────────────────
    def dist(vals):
        if not vals:
            return {"min": None, "max": None, "mean": None, "median": None}
        return {
            "min":    round(min(vals), 6),
            "max":    round(max(vals), 6),
            "mean":   round(statistics.mean(vals), 6),
            "median": round(statistics.median(vals), 6),
        }

    pi_dist = dist(pi_ratios)

    # ── verdict ──────────────────────────────────────────────────────────────
    if gate_count == 0:
        verdict = "ALL_CORRECT_PHYSICS"
        hyp_key = "H_V29_CUBE5_FRASTRATE_CORRECT_PHYSICS"
    elif gate_count < 10:
        verdict = "FEW_GATE_CANDIDATES"
        hyp_key = "H_V29_CUBE5_FRASTRATE_PARTIAL_GATE"
    else:
        verdict = "GATE_CANDIDATES_IDENTIFIED"
        hyp_key = "H_V29_CUBE5_FRASTRATE_HAS_GATE"

    # ── sample gate candidates ───────────────────────────────────────────────
    sample_candidates = []
    for rec in gate_candidates[:5]:
        sample_candidates.append({
            "source_file":    rec["source_file"],
            "config_name":    rec["config_name"],
            "commit_gate":    rec["commit_gate"],
            "pi_ratio":       round(rec["pi_ratio"], 4) if rec["pi_ratio"] else None,
            "frastrate_signal": rec["frastrate_signal"],
            "flags":          rec["flags"],
            "anomaly_reason": rec["anomaly_reason"],
        })

    # ── build output ─────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST13_CUBE5_FRASTRATE_TRIAGE_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":    "BCM_v29_TEST13",
        "test_name":  "CUBE5_FRASTRATE_TRIAGE",
        "timestamp":  ts,
        "foreman":    "Stephen Justin Burdick Sr.",

        "total_anomalies":       total,
        "frastrate_recall_count": counts["FRASTRATE_RECALL"],
        "pi_reflect_count":      counts["PI_REFLECT"],
        "pi_hard_reflect_count": counts["PI_HARD_REFLECT"],
        "mixed_count":           counts["MIXED"],
        "unknown_path_count":    counts["UNKNOWN_PATH"],

        "gate_candidate_count":  gate_count,
        "correct_physics_count": correct_count,

        "pi_ratio_distribution": pi_dist,
        "frastrate_signal_stats": {
            "below_1e6": fras_below_1e6,
            "above_1e6": fras_above_1e6,
        },
        "lambda_present_count":  lambda_present,
        "lambda_missing_count":  lambda_missing,

        "source_files":       sorted(source_files),
        "sample_candidates":  sample_candidates,

        "verdict":       verdict,
        "hypothesis_key": hyp_key,

        "gate_candidate_criteria": {
            "path":        "PI_REFLECT or PI_HARD_REFLECT only",
            "condition":   "SIGMA_CRIT_UNCALIBRATED flag present",
            "description": "Pi anomaly where sigma_crit was placeholder (lambda missing)",
        },
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    # ── console summary ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("CUBE 5 BUFFER / FRASTRATE TRIAGE — RESULTS")
    print("=" * 60)
    print(f"Total anomalies:        {total}")
    print(f"  FRASTRATE_RECALL:     {counts['FRASTRATE_RECALL']}")
    print(f"  PI_REFLECT:           {counts['PI_REFLECT']}")
    print(f"  PI_HARD_REFLECT:      {counts['PI_HARD_REFLECT']}")
    print(f"  MIXED:                {counts['MIXED']}")
    print(f"  UNKNOWN_PATH:         {counts['UNKNOWN_PATH']}")
    print()
    print(f"Lambda present (calibrated): {lambda_present}")
    print(f"Lambda missing (uncalib):    {lambda_missing}")
    print()
    print(f"frastrate_signal above 1e6: {fras_above_1e6}")
    print(f"frastrate_signal below 1e6: {fras_below_1e6}")
    print()
    print(f"Pi ratio  min={pi_dist['min']}  max={pi_dist['max']}  "
          f"mean={pi_dist['mean']}")
    print()
    print(f"Gate candidates:       {gate_count}")
    print(f"Correct physics:       {correct_count}")
    print()
    print(f"VERDICT:       {verdict}")
    print(f"HYPOTHESIS:    {hyp_key}")
    print()
    print(f"JSON written:  {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run_triage())
