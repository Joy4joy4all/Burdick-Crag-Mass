# -*- coding: utf-8 -*-
"""
BCM v29 TEST15 — CUBE3 / CUBE4 COLLATERAL CHECK
=================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Purpose:
    Check whether Cube 3 HEARTBEAT_BELOW_TARE (OVERCOME) records
    correlate with Cube 4 MODE_PERSISTENT_HOT anomalies in the same
    source files.

Hypothesis (from v29 handoff):
    No chi headspace (Cube 4 anomaly) = heartbeat loses pressure relief
    = drops below tare floor (Cube 3 OVERCOME).
    If confirmed: measurable cross-cube dependency.

Method:
    1. Run Cube 3 and Cube 4 projections on every ingested JSON.
    2. Record per-file counts of:
         Cube 3: HEARTBEAT_HEMORRHAGE / HEARTBEAT_BELOW_TARE / HEARTBEAT_ACTIVE
         Cube 4: MODE_PERSISTENT_HOT / resolved
    3. For each file, check if Cube 4 anomalies co-occur with Cube 3 BELOW_TARE.
    4. Report correlation and overall BELOW_TARE count.

Expected null result:
    If no BELOW_TARE records exist in the corpus, the hypothesis is
    NOT REFUTED — it is simply untestable against the current ingested set.
    The BELOW_TARE condition requires brucetron_rms < F2_TARE_FLOOR (0.000518),
    which represents a pathologically cold craft state not present in
    the v17-v26 test corpus (those tests ran hot, without chi freeboard or
    with it driving equilibrium to 0.0045, not near zero).

Output:
    cube3_hemorrhage_count
    cube3_below_tare_count
    cube3_fighting_count      (resolved, heartbeat active)
    cube4_mode_persistent_count
    cube4_resolved_count
    files_with_both_c3_below_and_c4_hot   (cross-cube co-occurrence)
    collateral_confirmed      (True if co-occurrence > 0)
    corpus_note               (explanation if below_tare = 0)
    verdict
    hypothesis_key
"""

from __future__ import annotations

import json
import sys
import statistics
from pathlib import Path
from datetime import datetime
from collections import defaultdict

_THIS_DIR      = Path(__file__).resolve().parent
_SOLVER_ROOT   = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"

if str(_GENESIS_BRAIN) not in sys.path:
    sys.path.insert(0, str(_GENESIS_BRAIN))

from anchor_state import build_reduced_from_json
from qt_layer import Cube3Physical, Cube4Tesseract


def run_check():
    json_files = sorted(_RESULTS_DIR.glob("*.json"))
    json_files = [f for f in json_files if not f.name.startswith("_")]

    if not json_files:
        print(f"ERROR: No JSON files in {_RESULTS_DIR}")
        sys.exit(1)

    print(f"Scanning {len(json_files)} JSON files (Cube 3 + Cube 4)...")

    cube3 = Cube3Physical()
    cube4 = Cube4Tesseract()

    # global counters
    c3_hemorrhage  = 0
    c3_below_tare  = 0
    c3_fighting    = 0
    c4_hot         = 0
    c4_resolved    = 0

    # per-file tracking for co-occurrence
    # file_name -> {c3_below: int, c4_hot: int}
    per_file = defaultdict(lambda: {"c3_below": 0, "c4_hot": 0,
                                    "c3_hemorrhage": 0, "c3_fighting": 0})

    for jf in json_files:
        fname = jf.name
        try:
            states = build_reduced_from_json(jf)
        except Exception as e:
            print(f"  SKIP {fname}: {e}")
            continue

        for st in states:
            # ── Cube 3 ────────────────────────────────────────────────────
            r3 = cube3.project(st)
            if "HEARTBEAT_HEMORRHAGE" in r3.flags:
                c3_hemorrhage += 1
                per_file[fname]["c3_hemorrhage"] += 1
            elif "HEARTBEAT_BELOW_TARE" in r3.flags:
                c3_below_tare += 1
                per_file[fname]["c3_below"] += 1
            elif "HEARTBEAT_ACTIVE" in r3.flags:
                c3_fighting += 1
                per_file[fname]["c3_fighting"] += 1

            # ── Cube 4 ────────────────────────────────────────────────────
            r4 = cube4.project(st)
            if r4.state == "ANOMALY":
                c4_hot += 1
                per_file[fname]["c4_hot"] += 1
            elif r4.state == "RESOLVED":
                c4_resolved += 1

    # ── co-occurrence ────────────────────────────────────────────────────────
    co_occur_files = [
        fname for fname, d in per_file.items()
        if d["c3_below"] > 0 and d["c4_hot"] > 0
    ]
    collateral_confirmed = len(co_occur_files) > 0

    # ── corpus note ──────────────────────────────────────────────────────────
    if c3_below_tare == 0:
        corpus_note = (
            "No HEARTBEAT_BELOW_TARE records in corpus. "
            "Pre-v19 tests ran HOT (no chi freeboard) producing HEMORRHAGE. "
            "Post-v19 tests have chi freeboard driving bruce to ~0.0045 "
            "equilibrium — not below F2_TARE_FLOOR (0.000518). "
            "BELOW_TARE requires pathologically cold craft state not "
            "represented in v17-v26 ingested corpus. "
            "Hypothesis is UNTESTABLE against current corpus, not refuted."
        )
        verdict = "HYPOTHESIS_UNTESTABLE_CORPUS_GAP"
        hyp_key = "H_V29_CUBE3_CUBE4_COLLATERAL_CORPUS_GAP"
    elif collateral_confirmed:
        corpus_note = (
            f"Co-occurrence found in {len(co_occur_files)} file(s). "
            "Cube 4 MODE_PERSISTENT_HOT and Cube 3 BELOW_TARE share source files."
        )
        verdict = "COLLATERAL_CONFIRMED"
        hyp_key = "H_V29_CUBE3_CUBE4_COLLATERAL_CONFIRMED"
    else:
        corpus_note = (
            f"BELOW_TARE records exist ({c3_below_tare}) but do not co-occur "
            "with Cube 4 MODE_PERSISTENT_HOT in the same source files."
        )
        verdict = "COLLATERAL_NOT_CONFIRMED"
        hyp_key = "H_V29_CUBE3_CUBE4_COLLATERAL_NOT_CONFIRMED"

    # ── total projections ────────────────────────────────────────────────────
    c3_total = c3_hemorrhage + c3_below_tare + c3_fighting
    c3_unknown = sum(
        1 for d in per_file.values()
        if d["c3_hemorrhage"] + d["c3_below"] + d["c3_fighting"] == 0
    )

    # ── output ───────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v29_TEST15_CUBE3_CUBE4_COLLATERAL_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    result_dict = {
        "test_id":   "BCM_v29_TEST15",
        "test_name": "CUBE3_CUBE4_COLLATERAL_CHECK",
        "timestamp": ts,
        "foreman":   "Stephen Justin Burdick Sr.",

        "cube3_hemorrhage_count":  c3_hemorrhage,
        "cube3_below_tare_count":  c3_below_tare,
        "cube3_fighting_count":    c3_fighting,

        "cube4_mode_persistent_count": c4_hot,
        "cube4_resolved_count":        c4_resolved,

        "files_with_both_c3_below_and_c4_hot": co_occur_files,
        "collateral_confirmed":  collateral_confirmed,
        "corpus_note":           corpus_note,

        "verdict":        verdict,
        "hypothesis_key": hyp_key,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result_dict, fh, indent=2)

    # ── console ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("CUBE 3 / CUBE 4 COLLATERAL CHECK — RESULTS")
    print("=" * 60)
    print(f"Cube 3 HEARTBEAT_HEMORRHAGE:  {c3_hemorrhage}")
    print(f"Cube 3 HEARTBEAT_BELOW_TARE:  {c3_below_tare}")
    print(f"Cube 3 HEARTBEAT_ACTIVE:      {c3_fighting}")
    print()
    print(f"Cube 4 MODE_PERSISTENT_HOT:   {c4_hot}")
    print(f"Cube 4 RESOLVED:              {c4_resolved}")
    print()
    print(f"Files with C3 BELOW + C4 HOT: {len(co_occur_files)}")
    print(f"Collateral confirmed:          {collateral_confirmed}")
    print()
    print(f"Corpus note: {corpus_note}")
    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_key}")
    print()
    print(f"JSON written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run_check())
