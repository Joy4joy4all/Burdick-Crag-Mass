# -*- coding: utf-8 -*-
"""
BCM v29 TEST14 — CUBE6 ZONE_MISMATCH_OTHER TRIAGE
===================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Purpose:
    Classify the ~38 Cube 6 (Guardians) anomalies that are neither
    GUARDIAN_PROXY_LIMITATION_RESOLVED nor TRUE_GUARDIAN_CONFLICT.
    These are the residual ZONE_MISMATCH records not caught by Test 09.

Cube 6 anomaly logic (qt_layer.py):
    ANOMALY fires when test_zone != formula_zone
    AND brucetron_load >= GUARDIAN_PROXY_LOAD_MAX (0.5)
      OR formula_zone != GREEN
    (i.e. the PROXY_LIMITATION gate did not fire)

Known Cube 6 anomaly populations (from Test 09 + handoff):
    TRUE_GUARDIAN_CONFLICT : 106 records
        brucetron CRITICAL (load >= 1.0) while growth_rate is negative
        correct physics — crew risk signal
    GUARDIAN_PROXY_LIMITATION_RESOLVED : 48 resolved (not anomalies)
    ZONE_MISMATCH_OTHER : ~38 records — UNKNOWN pattern

This test reads every Cube 6 anomaly and classifies the residual 38
by:
    mismatch_direction  (test_zone vs formula_zone: which is higher)
    brucetron_load band (LOW / RISING / CRITICAL / SATURATED)
    chi_buffer sign     (positive = absorbing, negative = collapsed)
    growth_rate sign    (positive = growing, negative = decaying)

Classification paths:
    TRUE_GUARDIAN_CONFLICT   bruce CRITICAL + growth negative (known)
    GREEN_REPORTED_RED       test_zone=GREEN but formula=RED
    RED_REPORTED_GREEN       test_zone=RED but formula=GREEN + load >= 0.5
                             (not caught by PROXY gate because load high)
    YELLOW_MISMATCH          test_zone=YELLOW/ORANGE vs formula different
    OTHER                    does not match any above

Gate candidate criteria for residual:
    RED_REPORTED_GREEN with brucetron_load in [0.5, 1.0):
        test_zone=RED (positive growth) but formula=GREEN
        load is RISING but not CRITICAL
        Chi buffer may be absorbing
        If chi_buffer > 0: chi is absorbing load — the RED overshoot
        is similar to PROXY_LIMITATION but load is in the 0.5 boundary
        zone. Need data to decide.
"""

from __future__ import annotations

import json
import sys
import statistics
from pathlib import Path
from datetime import datetime

_THIS_DIR      = Path(__file__).resolve().parent
_SOLVER_ROOT   = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"

if str(_GENESIS_BRAIN) not in sys.path:
    sys.path.insert(0, str(_GENESIS_BRAIN))

from anchor_state import build_reduced_from_json
from qt_layer import Cube6Guardians
from bcm_thresholds import BRUCETRON_HEMORRHAGE, CHI_C

GUARDIAN_PROXY_LOAD_MAX = 0.5    # from qt_layer gate


def classify_mismatch(test_zone, formula_zone, brucetron_load, growth_rate,
                      chi_buffer):
    """Classify one Cube 6 anomaly record into a failure path."""
    if brucetron_load is not None and brucetron_load >= 1.0 and \
            growth_rate is not None and growth_rate < 0:
        return "TRUE_GUARDIAN_CONFLICT"

    tz = "YELLOW" if test_zone == "ORANGE" else test_zone

    if tz == "GREEN" and formula_zone == "RED":
        return "GREEN_REPORTED_RED"

    if tz == "RED" and formula_zone == "GREEN":
        # PROXY gate would have fired if load < 0.5 — these are load >= 0.5
        return "RED_REPORTED_GREEN_HIGH_LOAD"

    if tz in ("YELLOW", "ORANGE") or formula_zone in ("YELLOW", "ORANGE"):
        return "YELLOW_MISMATCH"

    return "OTHER"


def run_triage():
    json_files = sorted(_RESULTS_DIR.glob("*.json"))
    json_files = [f for f in json_files if not f.name.startswith("_")]

    if not json_files:
        print(f"ERROR: No JSON files found in {_RESULTS_DIR}")
        sys.exit(1)

    print(f"Scanning {len(json_files)} JSON files for Cube 6 anomalies...")

    cube6 = Cube6Guardians()

    counts = {
        "TRUE_GUARDIAN_CONFLICT":        0,
        "GREEN_REPORTED_RED":            0,
        "RED_REPORTED_GREEN_HIGH_LOAD":  0,
        "YELLOW_MISMATCH":               0,
        "OTHER":                         0,
    }

    all_anomalies    = []
    residual_records = []   # everything that is NOT TRUE_GUARDIAN_CONFLICT
    source_files     = set()

    # distributions
    loads_by_path   = {}
    growth_by_path  = {}
    chi_buf_by_path = {}

    for jf in json_files:
        try:
            states = build_reduced_from_json(jf)
        except Exception as e:
            print(f"  SKIP {jf.name}: {e}")
            continue

        for st in states:
            result = cube6.project(st)
            if result.state != "ANOMALY":
                continue

            rm           = result.raw_metrics
            test_zone    = rm.get("test_zone")
            formula_zone = rm.get("formula_zone")
            bruce_load   = rm.get("brucetron_load")
            chi_buffer   = rm.get("chi_buffer")
            growth       = st.growth_rate
            sigma_trend  = rm.get("sigma_trend")

            path = classify_mismatch(
                test_zone, formula_zone, bruce_load, growth, chi_buffer
            )
            counts[path] += 1

            rec = {
                "source_file":   jf.name,
                "config_name":   st.config_name or "-",
                "test_zone":     test_zone,
                "formula_zone":  formula_zone,
                "brucetron_load": bruce_load,
                "chi_buffer":    chi_buffer,
                "growth_rate":   growth,
                "failure_path":  path,
                "anomaly_reason": result.anomaly_reason,
                "flags":         result.flags,
            }
            all_anomalies.append(rec)
            source_files.add(jf.name)

            # accumulate distributions per path
            for container, val in [
                (loads_by_path,   bruce_load),
                (growth_by_path,  growth),
                (chi_buf_by_path, chi_buffer),
            ]:
                container.setdefault(path, [])
                if val is not None:
                    container[path].append(val)

            if path != "TRUE_GUARDIAN_CONFLICT":
                residual_records.append(rec)

    total    = len(all_anomalies)
    residual = len(residual_records)

    print(f"Total Cube 6 anomalies: {total}")
    print(f"Residual (non-conflict): {residual}")

    # ── per-path stats ───────────────────────────────────────────────────────
    def mean_or_none(vals):
        return round(statistics.mean(vals), 4) if vals else None

    path_stats = {}
    for path in counts:
        path_stats[path] = {
            "count":          counts[path],
            "mean_load":      mean_or_none(loads_by_path.get(path, [])),
            "mean_growth":    mean_or_none(growth_by_path.get(path, [])),
            "mean_chi_buf":   mean_or_none(chi_buf_by_path.get(path, [])),
        }

    # ── gate candidate assessment ─────────────────────────────────────────────
    # RED_REPORTED_GREEN_HIGH_LOAD: load in [0.5, 1.0), chi absorbing?
    high_load_with_chi = [
        r for r in residual_records
        if r["failure_path"] == "RED_REPORTED_GREEN_HIGH_LOAD"
        and r["chi_buffer"] is not None
        and r["chi_buffer"] > 0
    ]
    gate_candidate_count = len(high_load_with_chi)

    # ── verdict ──────────────────────────────────────────────────────────────
    if residual == 0:
        verdict = "ALL_TRUE_GUARDIAN_CONFLICT"
        hyp_key = "H_V29_CUBE6_ZONE_MISMATCH_ALL_CONFLICT"
    elif gate_candidate_count > 0:
        verdict = "RESIDUAL_HAS_GATE_CANDIDATES"
        hyp_key = "H_V29_CUBE6_ZONE_MISMATCH_PARTIAL_GATE"
    else:
        verdict = "RESIDUAL_ALL_CORRECT_PHYSICS"
        hyp_key = "H_V29_CUBE6_ZONE_MISMATCH_CORRECT_PHYSICS"

    # ── sample residual records ───────────────────────────────────────────────
    sample_residual = []
    for rec in residual_records[:8]:
        sample_residual.append({
            "source_file":   rec["source_file"],
            "config_name":   rec["config_name"],
            "test_zone":     rec["test_zone"],
            "formula_zone":  rec["formula_zone"],
            "load":          round(rec["brucetron_load"], 3)
                             if rec["brucetron_load"] else None,
            "chi_buffer":    round(rec["chi_buffer"], 6)
                             if rec["chi_buffer"] else None,
            "growth_rate":   rec["growth_rate"],
            "failure_path":  rec["failure_path"],
            "anomaly_reason": rec["anomaly_reason"],
        })

    # ── build output ─────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST14_CUBE6_ZONE_MISMATCH_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST14",
        "test_name": "CUBE6_ZONE_MISMATCH_OTHER_TRIAGE",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",

        "total_anomalies":       total,
        "residual_count":        residual,
        "gate_candidate_count":  gate_candidate_count,

        "path_breakdown":  path_stats,
        "source_files":    sorted(source_files),
        "sample_residual": sample_residual,

        "verdict":        verdict,
        "hypothesis_key": hyp_key,

        "gate_candidate_criteria": {
            "path":        "RED_REPORTED_GREEN_HIGH_LOAD",
            "condition":   "brucetron_load in [0.5, 1.0) AND chi_buffer > 0",
            "description": "test_zone=RED but formula=GREEN, load elevated "
                           "but not critical, chi is absorbing — "
                           "may be an extended PROXY_LIMITATION with higher load",
        },
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    # ── console summary ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("CUBE 6 ZONE_MISMATCH_OTHER TRIAGE — RESULTS")
    print("=" * 60)
    print(f"Total Cube 6 anomalies:    {total}")
    print(f"Residual (non-conflict):   {residual}")
    print()
    for path, st in path_stats.items():
        if st["count"] > 0:
            print(f"  {path:<36} {st['count']:>3}  "
                  f"load={st['mean_load']}  "
                  f"growth={st['mean_growth']}  "
                  f"chi={st['mean_chi_buf']}")
    print()
    print(f"Gate candidates "
          f"(RED_GREEN_HIGH_LOAD + chi absorbing): {gate_candidate_count}")
    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_key}")
    print()
    print(f"JSON written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run_triage())
