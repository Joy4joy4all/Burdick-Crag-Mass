# -*- coding: utf-8 -*-
"""
BCM v29 TEST12 — CUBE4 TESSERACT TRIAGE
========================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Purpose:
    Classify the 96 Cube 4 (Tesseract / phi) anomalies by failure path.
    Identify gate candidates vs correct physics anomalies.

Cube 4 anomaly gate (qt_layer.py line 1195):
    FIRES when: chi_ratio > 10.0 AND phi_load > 0.5
    Reason: "mode persistent with elevated phi_load"
    (also fires when phi_load >= 1.0 — PHI_BREACHED, separate path)

Triage question:
    Are all 96 correct physics, or are some records in a safe operating
    band where chi is absorbing the phase load and phi_load, while elevated,
    is genuinely below breach level with headroom intact?

Classification scheme:
    PHI_BREACHED         phi_load >= 1.0 — phase safety limit exceeded
    MODE_PERSISTENT_HOT  chi_ratio > 10 AND phi_load > 0.5 AND phi_load < 1.0
                         (mode cannot collapse, phi elevated but not breached)
    MODE_PERSISTENT_SAFE chi_ratio > 10 AND phi_load in [0.3, 0.5]
                         (mode cannot collapse, but phi load is moderate)
    UNKNOWN_PATH         does not match either gate (should not occur)

Gate candidate criteria:
    A record is a gate CANDIDATE if:
      - chi_ratio > 10.0 (mode persistent, confirmed)
      - phi_load < 0.5 (phi load moderate — not a genuine crew risk)
      - phi_rms < PHI_SAFETY (not breached)
    These are MODE_PERSISTENT_SAFE records — mode rigidity is real but
    phi is not in the danger zone. The gate fired because chi was high,
    but the operational risk is low.

    Records with phi_load >= 0.5 (MODE_PERSISTENT_HOT) and phi_load >= 1.0
    (PHI_BREACHED) are NOT gate candidates — they are correct physics.

Output JSON keys:
    total_anomalies
    phi_breached_count       (phi_load >= 1.0, correct physics)
    mode_persistent_hot      (chi>10, phi 0.5-1.0, review needed)
    mode_persistent_safe     (chi>10, phi 0.3-0.5, gate candidate)
    unknown_path
    gate_candidate_count     (= mode_persistent_safe)
    correct_physics_count    (= phi_breached + mode_persistent_hot)
    phi_load_distribution    {min, max, mean, median}
    chi_ratio_distribution   {min, max, mean}
    source_files             list of unique source files in anomaly set
    sample_records           first 5 gate candidates (for review)
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
_THIS_DIR = Path(__file__).resolve().parent
_SOLVER_ROOT = _THIS_DIR.parent.parent          # climb two levels
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_RESULTS_DIR = _SOLVER_ROOT / "data" / "results"

# Add genesis_brain to path for imports
if str(_GENESIS_BRAIN) not in sys.path:
    sys.path.insert(0, str(_GENESIS_BRAIN))

from anchor_state import build_reduced_from_json
from qt_layer import QTStack, Cube4Tesseract
from bcm_thresholds import CHI_C, PHI_SAFETY

# ── constants (from qt_layer Cube4 gate) ────────────────────────────────────
CHI_RATIO_PERSISTENT_THRESHOLD = 10.0   # chi/chi_c above this = mode rigid
PHI_LOAD_HOT_THRESHOLD         = 0.5    # phi_load above this = elevated
PHI_LOAD_BREACH_THRESHOLD      = 1.0    # phi_load at/above this = breached

GATE_CANDIDATE_CHI_MIN  = 10.0   # must be mode-persistent
GATE_CANDIDATE_PHI_MAX  = 0.5    # phi load must be moderate (not hot)


def classify_anomaly(phi_load, chi_ratio):
    """Return failure path label for one Cube 4 anomaly record."""
    if phi_load is None:
        return "UNKNOWN_PATH"
    if phi_load >= PHI_LOAD_BREACH_THRESHOLD:
        return "PHI_BREACHED"
    if chi_ratio is not None and chi_ratio > CHI_RATIO_PERSISTENT_THRESHOLD:
        if phi_load >= PHI_LOAD_HOT_THRESHOLD:
            return "MODE_PERSISTENT_HOT"
        else:
            return "MODE_PERSISTENT_SAFE"
    return "UNKNOWN_PATH"


def is_gate_candidate(phi_load, chi_ratio):
    """Return True if this record is a gate candidate."""
    if phi_load is None or chi_ratio is None:
        return False
    return (
        chi_ratio > GATE_CANDIDATE_CHI_MIN
        and phi_load < GATE_CANDIDATE_PHI_MAX
        and phi_load < PHI_LOAD_BREACH_THRESHOLD
    )


def run_triage():
    # ── find all ingested JSONs ──────────────────────────────────────────────
    json_files = sorted(_RESULTS_DIR.glob("*.json"))
    json_files = [f for f in json_files
                  if not f.name.startswith("_")]   # skip state files

    if not json_files:
        print(f"ERROR: No JSON files found in {_RESULTS_DIR}")
        sys.exit(1)

    print(f"Scanning {len(json_files)} JSON files for Cube 4 anomalies...")

    cube4 = Cube4Tesseract()
    stack = QTStack()

    # ── collect all Cube 4 anomaly records ──────────────────────────────────
    anomaly_records = []   # list of dicts with phi_load, chi_ratio, source

    for jf in json_files:
        try:
            states = build_reduced_from_json(jf)
        except Exception as e:
            print(f"  SKIP {jf.name}: {e}")
            continue

        for st in states:
            result = cube4.project(st)
            if result.state != "ANOMALY":
                continue
            phi_load  = result.raw_metrics.get("phi_load")
            chi_ratio = result.raw_metrics.get("chi_ratio")
            anomaly_records.append({
                "source_file":  jf.name,
                "config_name":  st.config_name or "-",
                "phi_load":     phi_load,
                "chi_ratio":    chi_ratio,
                "phi_rms":      st.phi_rms,
                "anomaly_reason": result.anomaly_reason,
                "flags":        result.flags,
            })

    total = len(anomaly_records)
    print(f"Total Cube 4 anomalies found: {total}")

    # ── classify ─────────────────────────────────────────────────────────────
    counts = {
        "PHI_BREACHED":         0,
        "MODE_PERSISTENT_HOT":  0,
        "MODE_PERSISTENT_SAFE": 0,
        "UNKNOWN_PATH":         0,
    }
    gate_candidates = []
    correct_physics = []

    phi_loads   = []
    chi_ratios  = []
    source_files = set()

    for rec in anomaly_records:
        pl = rec["phi_load"]
        cr = rec["chi_ratio"]
        path = classify_anomaly(pl, cr)
        rec["failure_path"] = path
        counts[path] += 1

        if pl is not None:
            phi_loads.append(pl)
        if cr is not None:
            chi_ratios.append(cr)
        source_files.add(rec["source_file"])

        if is_gate_candidate(pl, cr):
            gate_candidates.append(rec)
        else:
            correct_physics.append(rec)

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

    phi_dist = dist(phi_loads)
    chi_dist = {
        "min":  round(min(chi_ratios), 2) if chi_ratios else None,
        "max":  round(max(chi_ratios), 2) if chi_ratios else None,
        "mean": round(statistics.mean(chi_ratios), 2) if chi_ratios else None,
    }

    # ── verdict ──────────────────────────────────────────────────────────────
    gate_count    = len(gate_candidates)
    correct_count = len(correct_physics)

    if gate_count == 0:
        verdict = "ALL_CORRECT_PHYSICS"
        hyp_key = "H_V29_CUBE4_PHI_LOAD_CORRECT_PHYSICS"
    elif gate_count < 10:
        verdict = "FEW_GATE_CANDIDATES"
        hyp_key = "H_V29_CUBE4_PHI_LOAD_PARTIAL_GATE"
    else:
        verdict = "GATE_CANDIDATES_IDENTIFIED"
        hyp_key = "H_V29_CUBE4_PHI_LOAD_HAS_GATE"

    # ── sample gate candidates ───────────────────────────────────────────────
    sample_candidates = []
    for rec in gate_candidates[:5]:
        sample_candidates.append({
            "source_file":    rec["source_file"],
            "config_name":    rec["config_name"],
            "phi_load":       round(rec["phi_load"], 4) if rec["phi_load"] else None,
            "chi_ratio":      round(rec["chi_ratio"], 2) if rec["chi_ratio"] else None,
            "anomaly_reason": rec["anomaly_reason"],
        })

    # ── build output ─────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST12_CUBE4_TESSERACT_TRIAGE_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":    "BCM_v29_TEST12",
        "test_name":  "CUBE4_TESSERACT_TRIAGE",
        "timestamp":  ts,
        "foreman":    "Stephen Justin Burdick Sr.",

        "total_anomalies":      total,
        "phi_breached_count":   counts["PHI_BREACHED"],
        "mode_persistent_hot":  counts["MODE_PERSISTENT_HOT"],
        "mode_persistent_safe": counts["MODE_PERSISTENT_SAFE"],
        "unknown_path":         counts["UNKNOWN_PATH"],

        "gate_candidate_count":  gate_count,
        "correct_physics_count": correct_count,

        "phi_load_distribution":  phi_dist,
        "chi_ratio_distribution": chi_dist,

        "source_files":    sorted(source_files),
        "sample_candidates": sample_candidates,

        "verdict":       verdict,
        "hypothesis_key": hyp_key,

        "gate_candidate_criteria": {
            "chi_ratio_min":  GATE_CANDIDATE_CHI_MIN,
            "phi_load_max":   GATE_CANDIDATE_PHI_MAX,
            "description":    "mode rigid but phi load moderate — not a crew risk",
        },
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    # ── console summary ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("CUBE 4 TESSERACT TRIAGE — RESULTS")
    print("=" * 60)
    print(f"Total anomalies:       {total}")
    print(f"  PHI_BREACHED:        {counts['PHI_BREACHED']}")
    print(f"  MODE_PERSISTENT_HOT: {counts['MODE_PERSISTENT_HOT']}")
    print(f"  MODE_PERSISTENT_SAFE:{counts['MODE_PERSISTENT_SAFE']}")
    print(f"  UNKNOWN_PATH:        {counts['UNKNOWN_PATH']}")
    print()
    print(f"Gate candidates:       {gate_count}")
    print(f"Correct physics:       {correct_count}")
    print()
    print(f"phi_load  min={phi_dist['min']}  max={phi_dist['max']}  "
          f"mean={phi_dist['mean']}")
    print(f"chi_ratio min={chi_dist['min']}  max={chi_dist['max']}  "
          f"mean={chi_dist['mean']}")
    print()
    print(f"VERDICT:       {verdict}")
    print(f"HYPOTHESIS:    {hyp_key}")
    print()
    print(f"JSON written:  {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run_triage())
