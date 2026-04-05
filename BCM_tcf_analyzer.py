# -*- coding: utf-8 -*-
"""
BCM v9 Time-Cost Function Analyzer — Substrate Invoice
========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Reads existing tunnel time-series JSONs and computes the four
time-cost corners from the sig_drift trajectory. No new solver
runs required.

The Four Corners:
  TCF_transient:   total cost to open the bridge (entry fee)
  TCF_observable:  running cost during measurement (utility bill)
  TCF_existential: minimum fixed cost (HR 1099 baseline lease)
  TCF_alternating: variable cost between orbital positions

Usage:
    python BCM_tcf_analyzer.py data/results/BCM_tunnel_Spica_*.json
    python BCM_tcf_analyzer.py --all
    python BCM_tcf_analyzer.py --compare
"""

import numpy as np
import json
import os
import glob
import argparse


def analyze_tcf(filepath):
    """
    Compute Time-Cost Function from a single tunnel time-series JSON.

    Returns dict with four cost corners and life expectancy estimate.
    """
    with open(filepath) as f:
        data = json.load(f)

    ts = data.get("timeseries", [])
    if not ts:
        print(f"  ERROR: No timeseries data in {filepath}")
        return None

    pair = data.get("pair", "unknown")
    phase = data.get("phase", 0.0)
    grid = data.get("grid", 0)
    settle = data.get("settle", 25000)

    # Extract sig_drift trajectory
    steps = [e["step"] for e in ts]
    drifts = [e["sig_drift"] for e in ts]

    # Separate settle and measure phases
    settle_entries = [e for e in ts if e["phase"] == "settle"]
    measure_entries = [e for e in ts if e["phase"] == "measure"]

    # --- TCF_transient: entry fee ---
    # Total sig_drift accumulated during settle phase
    tcf_transient = settle_entries[-1]["sig_drift"] if settle_entries else 0.0

    # Turnstile opening: step where sig_drift first exceeds 10% of final
    turnstile_step = 0
    threshold = tcf_transient * 0.1
    for e in settle_entries:
        if e["sig_drift"] >= threshold:
            turnstile_step = e["step"]
            break

    # Stabilization: step where rate of change drops below 10% of peak rate
    settle_rates = []
    for i in range(1, len(settle_entries)):
        dt = settle_entries[i]["step"] - settle_entries[i-1]["step"]
        dd = settle_entries[i]["sig_drift"] - settle_entries[i-1]["sig_drift"]
        rate = dd / dt if dt > 0 else 0
        settle_rates.append((settle_entries[i]["step"], rate))

    peak_rate = max(r for _, r in settle_rates) if settle_rates else 0
    stable_step = settle
    for step, rate in settle_rates:
        if rate < peak_rate * 0.5 and step > turnstile_step:
            stable_step = step
            break

    # --- TCF_observable: running cost during measurement ---
    if len(measure_entries) >= 2:
        d_first = measure_entries[0]["sig_drift"]
        d_last = measure_entries[-1]["sig_drift"]
        s_first = measure_entries[0]["step"]
        s_last = measure_entries[-1]["step"]
        dt_measure = s_last - s_first
        tcf_observable = (d_last - d_first) / dt_measure if dt_measure > 0 else 0
        # Per 1000 steps for readability
        tcf_observable_k = tcf_observable * 1000
    else:
        tcf_observable = 0
        tcf_observable_k = 0

    # --- TCF_existential: base rate (computed, compared externally) ---
    # This is just the observable rate for this run — comparison to
    # HR 1099 baseline happens in the compare function
    tcf_existential = tcf_observable_k

    # --- I_B at final measurement step ---
    i_b_final = 0.0
    if measure_entries:
        last = measure_entries[-1]
        sig_mb = last.get("sig_midB_amp", 0)
        sig_l1 = last.get("sig_l1_amp", 0)
        i_b_final = sig_mb - sig_l1

    # --- sig_midB budget (B's total substrate at end of measurement) ---
    budget_b = 0.0
    if measure_entries:
        budget_b = measure_entries[-1].get("sig_midB_amp",
                   measure_entries[-1].get("sig_midB_amp", 0))

    # --- Life expectancy estimate ---
    # If drain rate is tcf_observable per step, and B's budget is budget_b,
    # then steps_remaining = budget_b / tcf_observable (if tcf_observable > 0)
    steps_remaining = 0
    if tcf_observable > 0 and budget_b > 0:
        steps_remaining = budget_b / tcf_observable

    # --- Drift rate trajectory (per 1000 steps) ---
    rate_trajectory = []
    for i in range(1, len(ts)):
        dt = ts[i]["step"] - ts[i-1]["step"]
        dd = ts[i]["sig_drift"] - ts[i-1]["sig_drift"]
        rate = (dd / dt * 1000) if dt > 0 else 0
        rate_trajectory.append({
            "step": ts[i]["step"],
            "phase": ts[i]["phase"],
            "rate_per_k": round(rate, 2),
        })

    result = {
        "file":              os.path.basename(filepath),
        "pair":              pair,
        "phase":             phase,
        "grid":              grid,
        "settle":            settle,
        "tcf_transient":     round(tcf_transient, 2),
        "turnstile_step":    turnstile_step,
        "stable_step":       stable_step,
        "tcf_observable_k":  round(tcf_observable_k, 2),
        "tcf_existential_k": round(tcf_existential, 2),
        "budget_b":          round(budget_b, 2),
        "i_b_final":         round(i_b_final, 2),
        "steps_remaining":   round(steps_remaining, 0),
        "rate_trajectory":   rate_trajectory,
    }

    return result


def print_invoice(result):
    """Print a formatted substrate invoice for one run."""
    if result is None:
        return

    print(f"\n{'='*65}")
    print(f"  SUBSTRATE INVOICE — {result['pair']} phase={result['phase']}")
    print(f"  Grid: {result['grid']}  Settle: {result['settle']}")
    print(f"{'='*65}")

    print(f"\n  ENTRY FEE (TCF_transient)")
    print(f"    Total settle-phase drift:  {result['tcf_transient']:,.1f}")
    print(f"    Turnstile opened at step:  {result['turnstile_step']}")
    print(f"    Stabilized at step:        {result['stable_step']}")

    print(f"\n  RUNNING COST (TCF_observable)")
    print(f"    Drain rate (measure phase): {result['tcf_observable_k']:.2f} "
          f"per 1000 steps")

    print(f"\n  STAR B STATUS")
    print(f"    Budget (sig_midB):         {result['budget_b']:,.1f}")
    print(f"    Independence (I_B):        {result['i_b_final']:+.1f}")
    if result['i_b_final'] > 0:
        print(f"    Status:                    RESISTANT")
    else:
        print(f"    Status:                    DRAIN (colonized)")

    if result['steps_remaining'] > 0 and result['budget_b'] > 0:
        print(f"\n  LIFE EXPECTANCY")
        print(f"    Steps to budget zero:      {result['steps_remaining']:,.0f}")
        print(f"    (at current drain rate)")

    # Rate trajectory
    print(f"\n  RATE TRAJECTORY (drift per 1000 steps)")
    print(f"  {'step':>6} {'phase':>8} {'rate':>10}")
    print(f"  {'-'*6} {'-'*8} {'-'*10}")
    for r in result["rate_trajectory"]:
        marker = " <<" if r["phase"] == "measure" else ""
        print(f"  {r['step']:>6} {r['phase']:>8} {r['rate_per_k']:>10.2f}{marker}")

    print(f"{'='*65}\n")


def compare_systems(results):
    """Compare TCF across multiple systems."""
    if not results:
        return

    print(f"\n{'='*70}")
    print(f"  COMPARATIVE SUBSTRATE LEDGER")
    print(f"{'='*70}")

    print(f"\n  {'System':<25} {'Phase':>6} {'Entry Fee':>10} "
          f"{'Rate/k':>8} {'Budget_B':>10} {'I_B':>8} {'Status'}")
    print(f"  {'-'*25} {'-'*6} {'-'*10} {'-'*8} {'-'*10} {'-'*8} {'-'*15}")

    # Sort by drain rate descending
    sorted_results = sorted(results, key=lambda r: r["tcf_observable_k"],
                             reverse=True)

    for r in sorted_results:
        status = "RESISTANT" if r["i_b_final"] > 0 else "DRAIN"
        label = f"{r['pair']} ph={r['phase']}"
        print(f"  {label:<25} {r['phase']:>6.1f} "
              f"{r['tcf_transient']:>10,.1f} "
              f"{r['tcf_observable_k']:>8.2f} "
              f"{r['budget_b']:>10,.1f} "
              f"{r['i_b_final']:>+8.1f} {status}")

    # Find HR 1099 baseline if present
    hr_results = [r for r in results if r["pair"] == "HR_1099"]
    if hr_results:
        baseline = min(r["tcf_observable_k"] for r in hr_results)
        print(f"\n  EXISTENTIAL BASELINE (HR 1099): {baseline:.2f} per 1000 steps")
        print(f"\n  INEFFICIENCY TAX (rate above baseline):")
        for r in sorted_results:
            if r["pair"] != "HR_1099":
                tax = r["tcf_observable_k"] - baseline
                label = f"{r['pair']} ph={r['phase']}"
                print(f"    {label:<25} +{tax:.2f} per 1000 steps")

    print(f"{'='*70}\n")


def find_tunnel_jsons(search_dir=None):
    """Find all tunnel time-series JSONs in data/results."""
    if search_dir is None:
        base = os.path.dirname(os.path.abspath(__file__))
        search_dir = os.path.join(base, "data", "results")

    pattern = os.path.join(search_dir, "BCM_tunnel_*.json")
    files = sorted(glob.glob(pattern))
    return files


def main():
    parser = argparse.ArgumentParser(
        description="BCM v9 Time-Cost Function Analyzer")
    parser.add_argument("files", nargs="*",
                        help="Tunnel time-series JSON files to analyze")
    parser.add_argument("--all", action="store_true",
                        help="Analyze all tunnel JSONs in data/results/")
    parser.add_argument("--compare", action="store_true",
                        help="Show comparative ledger across all systems")
    args = parser.parse_args()

    files = args.files
    if args.all or args.compare:
        files = find_tunnel_jsons()
        if not files:
            print("No tunnel time-series JSONs found in data/results/")
            return

    if not files:
        print("Usage: python BCM_tcf_analyzer.py <json_files...>")
        print("       python BCM_tcf_analyzer.py --all")
        print("       python BCM_tcf_analyzer.py --compare")
        return

    results = []
    for fp in files:
        r = analyze_tcf(fp)
        if r is not None:
            results.append(r)
            if not args.compare:
                print_invoice(r)

    if args.compare and results:
        compare_systems(results)


if __name__ == "__main__":
    main()
