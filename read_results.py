"""
Results Reader & Pattern Analyzer
===================================
Stephen Justin Burdick, 2026 — Emerald Entities LLC

CLI tool. Reads ALL JSON files from data/results/.
Surfaces patterns, win records, stubborn galaxies,
pipeline performance, and mass bracket breakdowns.

Usage:
    python read_results.py
    python read_results.py --results-dir data/results
    python read_results.py --galaxy NGC2403
    python read_results.py --mode stubborn
    python read_results.py --mode bracket
    python read_results.py --mode pipeline
    python read_results.py --mode galaxy --galaxy NGC2403
"""

import os
import sys
import json
import argparse
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.run_record import load_all_records, mass_bracket


# ─────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────

W = 65

def header(title):
    print(f"\n{'═'*W}")
    print(f"  {title}")
    print(f"{'═'*W}")

def section(title):
    print(f"\n  {'─'*55}")
    print(f"  {title}")
    print(f"  {'─'*55}")

def win_color(winner):
    """ASCII winner tag."""
    tags = {"SUBSTRATE": "[SUB]", "NEWTON": "[NWT]", "MOND": "[MND]",
            "TIE": "[TIE]", None: "[---]"}
    return tags.get(winner, "[???]")


# ─────────────────────────────────────────
# SUMMARY — all runs
# ─────────────────────────────────────────

def show_summary(records):
    header("SUBSTRATE SOLVER — RUN DATABASE SUMMARY")

    total = len(records)
    with_rms = [r for r in records
                if r.get("results", {}).get("rms_newton") is not None]
    legacy = sum(1 for r in records if r.get("_legacy"))

    print(f"\n  Total records loaded:  {total}")
    print(f"  With rotation curves:  {len(with_rms)}")
    if legacy:
        print(f"  Legacy (pre-schema):   {legacy}  (no pipeline detail)")

    # Unique galaxies
    galaxies = set(r["galaxy"] for r in records)
    print(f"  Unique galaxies:       {len(galaxies)}")

    # Unique pipelines
    pipelines = set(r.get("pipeline", {}).get("observable", "unknown")
                    for r in records)
    print(f"  Unique observables:    {len(pipelines)}  {list(pipelines)}")

    # Parameter ranges seen
    lambdas = set(r.get("parameters", {}).get("lambda")
                  for r in records if r.get("parameters", {}).get("lambda") is not None)
    grids   = set(r.get("parameters", {}).get("grid")
                  for r in records if r.get("parameters", {}).get("grid") is not None)
    layers_set = set(r.get("parameters", {}).get("layers")
                     for r in records if r.get("parameters", {}).get("layers") is not None)
    if lambdas: print(f"  λ values seen:         {sorted(lambdas)}")
    if grids:   print(f"  Grid sizes seen:       {sorted(grids)}")
    if layers_set: print(f"  Layer counts seen:     {sorted(layers_set)}")

    # Most recent runs
    section("MOST RECENT 10 RUNS")
    print(f"  {'Timestamp':<20} {'Galaxy':<16} {'Observable':<22} {'Winner':<10} {'RMS_S':>7}")
    print(f"  {'─'*20} {'─'*16} {'─'*22} {'─'*10} {'─'*7}")
    for r in records[:10]:
        ts    = r.get("timestamp", "")[:19]
        gal   = r.get("galaxy", "?")[:15]
        obs   = (r.get("pipeline", {}).get("observable") or "legacy")[:21]
        win   = r.get("results", {}).get("winner") or "---"
        rms_s = r.get("results", {}).get("rms_substrate")
        rms_s_str = f"{rms_s:>7.1f}" if rms_s is not None else "    ---"
        print(f"  {ts:<20} {gal:<16} {obs:<22} {win_color(win):<10} {rms_s_str}")

    # Overall win record
    if with_rms:
        section("OVERALL WIN RECORD")
        winners = [r["results"]["winner"] for r in with_rms]
        outer_w = [r["results"].get("outer_winner") for r in with_rms]
        sub_w = winners.count("SUBSTRATE")
        nwt_w = winners.count("NEWTON")
        mnd_w = winners.count("MOND")
        tie_w = winners.count("TIE")
        print(f"  Substrate:  {sub_w:>4}  ({sub_w/len(with_rms)*100:.1f}%)")
        print(f"  Newton:     {nwt_w:>4}  ({nwt_w/len(with_rms)*100:.1f}%)")
        print(f"  MOND:       {mnd_w:>4}  ({mnd_w/len(with_rms)*100:.1f}%)")
        print(f"  Tie:        {tie_w:>4}")
        print(f"  ─── Total: {len(with_rms)}")

        outer_sub = sum(1 for w in outer_w if w == "SUBSTRATE")
        print(f"\n  Outer-radii substrate wins: {outer_sub} / {len(with_rms)}"
              f"  ({outer_sub/len(with_rms)*100:.1f}%)")

        avg_rms_n = np.mean([r["results"]["rms_newton"]    for r in with_rms])
        avg_rms_m = np.mean([r["results"]["rms_mond"]      for r in with_rms])
        avg_rms_s = np.mean([r["results"]["rms_substrate"] for r in with_rms])
        print(f"\n  Avg RMS — Newton: {avg_rms_n:.2f}  MOND: {avg_rms_m:.2f}"
              f"  Substrate: {avg_rms_s:.2f} km/s")


# ─────────────────────────────────────────
# PIPELINE PERFORMANCE
# ─────────────────────────────────────────

def show_pipeline(records):
    header("PIPELINE PERFORMANCE MATRIX")

    with_rms = [r for r in records
                if r.get("results", {}).get("rms_newton") is not None]
    if not with_rms:
        print("  No rotation curve results found."); return

    by_pipeline = defaultdict(list)
    for r in with_rms:
        obs = r.get("pipeline", {}).get("observable") or "legacy"
        by_pipeline[obs].append(r)

    print(f"\n  {'Observable':<28} {'N':>4} {'Sub%':>6} {'NwtRMS':>8}"
          f" {'SubRMS':>8} {'ΔRMS':>8} {'OutSub%':>9}")
    print(f"  {'─'*28} {'─'*4} {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*9}")

    for obs, runs in sorted(by_pipeline.items(), key=lambda x: -len(x[1])):
        n = len(runs)
        sub_wins = sum(1 for r in runs if r["results"]["winner"] == "SUBSTRATE")
        avg_n = np.mean([r["results"]["rms_newton"]    for r in runs])
        avg_s = np.mean([r["results"]["rms_substrate"] for r in runs])
        delta = avg_n - avg_s
        outer_sub = sum(1 for r in runs
                        if r["results"].get("outer_winner") == "SUBSTRATE")
        print(f"  {obs:<28} {n:>4} {sub_wins/n*100:>5.1f}%"
              f" {avg_n:>8.2f} {avg_s:>8.2f} {delta:>+8.2f} {outer_sub/n*100:>8.1f}%")

    # Per pipeline x bracket
    section("PIPELINE × MASS BRACKET")
    brackets = ["dwarf", "low", "mid", "high", "massive"]
    print(f"  {'Observable':<22}", end="")
    for b in brackets:
        print(f" {b:>9}", end="")
    print()
    print(f"  {'─'*22}", end="")
    for _ in brackets:
        print(f" {'─'*9}", end="")
    print()

    for obs, runs in sorted(by_pipeline.items(), key=lambda x: -len(x[1])):
        print(f"  {obs[:21]:<22}", end="")
        for b in brackets:
            subset = [r for r in runs
                      if r.get("galaxy_properties", {}).get("mass_bracket") == b]
            if not subset:
                print(f" {'---':>9}", end="")
            else:
                sw = sum(1 for r in subset if r["results"]["winner"] == "SUBSTRATE")
                print(f" {sw:>3}/{len(subset):<5}", end="")
        print()


# ─────────────────────────────────────────
# MASS BRACKET VIEW
# ─────────────────────────────────────────

def show_bracket(records):
    header("MASS BRACKET BREAKDOWN")

    with_rms = [r for r in records
                if r.get("results", {}).get("rms_newton") is not None]
    if not with_rms:
        print("  No rotation curve results."); return

    brackets = ["dwarf", "low", "mid", "high", "massive"]
    labels = {
        "dwarf":   "Dwarf     (V < 50)",
        "low":     "Low       (50–100)",
        "mid":     "Mid       (100–150)",
        "high":    "High      (150–200)",
        "massive": "Massive   (V > 200)",
    }

    for b in brackets:
        subset = [r for r in with_rms
                  if r.get("galaxy_properties", {}).get("mass_bracket") == b]
        if not subset:
            continue

        section(f"{labels[b]}  — {len(subset)} galaxies")
        winners = [r["results"]["winner"] for r in subset]
        avg_n = np.mean([r["results"]["rms_newton"]    for r in subset])
        avg_m = np.mean([r["results"]["rms_mond"]      for r in subset])
        avg_s = np.mean([r["results"]["rms_substrate"] for r in subset])

        print(f"  Substrate: {winners.count('SUBSTRATE'):>3}  Newton: {winners.count('NEWTON'):>3}"
              f"  MOND: {winners.count('MOND'):>3}  Tie: {winners.count('TIE'):>3}")
        print(f"  Avg RMS — Newton: {avg_n:.2f}  MOND: {avg_m:.2f}"
              f"  Substrate: {avg_s:.2f} km/s  Δ: {avg_n-avg_s:+.2f}")

        # Top 5 best and worst substrate results in bracket
        by_delta = sorted(subset, key=lambda r: r["results"]["sub_vs_newton"], reverse=True)
        print(f"\n  Best substrate (by RMS vs Newton):")
        print(f"  {'Galaxy':<16} {'RMS_N':>7} {'RMS_S':>7} {'ΔRMS':>7}")
        for r in by_delta[:5]:
            g = r["galaxy"]
            rn = r["results"]["rms_newton"]
            rs = r["results"]["rms_substrate"]
            print(f"  {g:<16} {rn:>7.1f} {rs:>7.1f} {rn-rs:>+7.1f}")

        print(f"\n  Worst substrate:")
        for r in by_delta[-3:]:
            g = r["galaxy"]
            rn = r["results"]["rms_newton"]
            rs = r["results"]["rms_substrate"]
            print(f"  {g:<16} {rn:>7.1f} {rs:>7.1f} {rn-rs:>+7.1f}")


# ─────────────────────────────────────────
# STUBBORN GALAXIES
# ─────────────────────────────────────────

def show_stubborn(records):
    header("STUBBORN GALAXIES — Newton wins every run")

    with_rms = [r for r in records
                if r.get("results", {}).get("rms_newton") is not None]
    if not with_rms:
        print("  No rotation curve results."); return

    # Group by galaxy
    by_galaxy = defaultdict(list)
    for r in with_rms:
        by_galaxy[r["galaxy"]].append(r)

    stubborn = {}
    substrate_always = {}
    mixed = {}

    for gal, runs in by_galaxy.items():
        winners = set(r["results"]["winner"] for r in runs)
        if winners == {"NEWTON"} or winners == {"NEWTON", "TIE"}:
            stubborn[gal] = runs
        elif "SUBSTRATE" in winners and "NEWTON" not in winners:
            substrate_always[gal] = runs
        else:
            mixed[gal] = runs

    print(f"\n  Galaxies where Newton wins EVERY run:   {len(stubborn)}")
    print(f"  Galaxies where Substrate wins every run: {len(substrate_always)}")
    print(f"  Mixed (depends on parameters):           {len(mixed)}")

    if stubborn:
        section(f"STUBBORN — {len(stubborn)} galaxies (never beaten Newton)")
        print(f"  {'Galaxy':<16} {'Bracket':<10} {'Runs':>5} {'Best Sub RMS':>14}"
              f" {'Newton RMS':>12}")
        print(f"  {'─'*16} {'─'*10} {'─'*5} {'─'*14} {'─'*12}")
        for gal, runs in sorted(stubborn.items(),
                                 key=lambda x: np.mean([r["results"]["rms_substrate"]
                                                        for r in x[1]])):
            b = runs[0].get("galaxy_properties", {}).get("mass_bracket", "?")
            best_sub = min(r["results"]["rms_substrate"] for r in runs)
            avg_nwt  = np.mean([r["results"]["rms_newton"] for r in runs])
            print(f"  {gal:<16} {b:<10} {len(runs):>5}"
                  f" {best_sub:>14.2f} {avg_nwt:>12.2f}")

    if substrate_always:
        section(f"RELIABLE SUBSTRATE WINS — {len(substrate_always)} galaxies")
        print(f"  {'Galaxy':<16} {'Bracket':<10} {'Runs':>5}"
              f" {'Avg Sub RMS':>12} {'Avg Nwt RMS':>12}")
        for gal, runs in sorted(substrate_always.items(),
                                  key=lambda x: np.mean([r["results"]["sub_vs_newton"]
                                                          for r in x[1]]), reverse=True)[:15]:
            b = runs[0].get("galaxy_properties", {}).get("mass_bracket", "?")
            avg_s = np.mean([r["results"]["rms_substrate"] for r in runs])
            avg_n = np.mean([r["results"]["rms_newton"]    for r in runs])
            print(f"  {gal:<16} {b:<10} {len(runs):>5} {avg_s:>12.2f} {avg_n:>12.2f}")


# ─────────────────────────────────────────
# SINGLE GALAXY PROFILE
# ─────────────────────────────────────────

def show_galaxy(records, galaxy_name):
    header(f"GALAXY PROFILE — {galaxy_name}")

    runs = [r for r in records if r["galaxy"] == galaxy_name]
    if not runs:
        print(f"  No records found for {galaxy_name}.")
        return

    print(f"\n  {len(runs)} run(s) found.")
    gp = runs[0].get("galaxy_properties", {})
    print(f"  V_max={gp.get('v_max', '?'):.1f} km/s  "
          f"R_max={gp.get('r_max', '?'):.1f} kpc  "
          f"Bracket={gp.get('mass_bracket', '?')}")

    print(f"\n  {'Timestamp':<20} {'λ':>6} {'Grid':>5} {'Observable':<22}"
          f" {'Winner':<10} {'RMS_N':>7} {'RMS_S':>7} {'Δ':>7}")
    print(f"  {'─'*20} {'─'*6} {'─'*5} {'─'*22} {'─'*10} {'─'*7} {'─'*7} {'─'*7}")

    runs_rms = [r for r in runs if r.get("results", {}).get("rms_newton") is not None]
    for r in sorted(runs_rms, key=lambda x: x.get("results", {}).get("rms_substrate", 999)):
        ts   = r.get("timestamp", "")[:19]
        lam  = r.get("parameters", {}).get("lambda") or "?"
        grid = r.get("parameters", {}).get("grid") or "?"
        obs  = (r.get("pipeline", {}).get("observable") or "legacy")[:21]
        win  = r.get("results", {}).get("winner") or "---"
        rn   = r["results"]["rms_newton"]
        rs   = r["results"]["rms_substrate"]
        print(f"  {ts:<20} {str(lam):>6} {str(grid):>5} {obs:<22}"
              f" {win_color(win):<10} {rn:>7.1f} {rs:>7.1f} {rn-rs:>+7.1f}")

    if runs_rms:
        best = min(runs_rms, key=lambda r: r["results"]["rms_substrate"])
        print(f"\n  Best run: observable={best.get('pipeline',{}).get('observable')}"
              f"  λ={best.get('parameters',{}).get('lambda')}"
              f"  grid={best.get('parameters',{}).get('grid')}")
        print(f"  Best RMS: Newton={best['results']['rms_newton']:.2f}"
              f"  Substrate={best['results']['rms_substrate']:.2f}")
        if best.get("notes"):
            print(f"  Notes: {best['notes']}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Substrate Solver Results Analyzer")
    parser.add_argument("--results-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "data", "results"))
    parser.add_argument("--mode", type=str, default="summary",
                        choices=["summary", "pipeline", "bracket", "stubborn", "galaxy"],
                        help="What to show")
    parser.add_argument("--galaxy", type=str, default=None,
                        help="Galaxy name for --mode galaxy")
    args = parser.parse_args()

    print(f"  Loading from: {args.results_dir}")
    records = load_all_records(args.results_dir)

    if not records:
        print(f"  No JSON files found in {args.results_dir}")
        sys.exit(0)

    print(f"  {len(records)} record(s) loaded.")

    if args.mode == "summary":
        show_summary(records)
    elif args.mode == "pipeline":
        show_pipeline(records)
    elif args.mode == "bracket":
        show_bracket(records)
    elif args.mode == "stubborn":
        show_stubborn(records)
    elif args.mode == "galaxy":
        if not args.galaxy:
            print("  --mode galaxy requires --galaxy <name>")
            sys.exit(1)
        show_galaxy(records, args.galaxy)

    print(f"\n{'═'*W}\n")
