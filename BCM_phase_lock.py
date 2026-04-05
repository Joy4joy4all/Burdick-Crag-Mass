# -*- coding: utf-8 -*-
"""
BCM v10 Phase-Lock Coherence Analyzer — Φ_crit Extractor
==========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Sweeps cos_delta_phi threshold (Φ_min) across the spatial phase
field to find the critical coherence where the bridge disconnects.

The law being tested:
    Existence requires phase coherence above a critical threshold.

Method:
    1. Run binary solver to get cos_delta_phi_field (2D spatial)
    2. Sweep Φ_min from 0.999999 down to 0.5
    3. At each threshold, compute surviving region and bridge
       connectivity via flood-fill from pump A to pump B
    4. Report Φ_crit: the highest Φ_min where bridge disconnects

Usage:
    python BCM_phase_lock.py --pair Spica --phase 0.0
    python BCM_phase_lock.py --pair HR_1099 --phase 0.5
    python BCM_phase_lock.py --compare
"""

import numpy as np
import json
import os
import time
import argparse


def flood_fill_connected(field, threshold, start, end, grid):
    """
    Check if start and end are connected through regions where
    field > threshold. Uses BFS flood fill.

    Returns:
        connected: bool
        n_surviving: number of pixels above threshold
        n_reachable: number of pixels reachable from start
    """
    mask = field > threshold
    n_surviving = int(np.sum(mask))

    if not mask[start[1], start[0]] or not mask[end[1], end[0]]:
        return False, n_surviving, 0

    visited = np.zeros_like(mask, dtype=bool)
    queue = [(start[0], start[1])]
    visited[start[1], start[0]] = True
    n_reachable = 0

    while queue:
        x, y = queue.pop(0)
        n_reachable += 1

        # Check if we reached the end
        if abs(x - end[0]) <= 2 and abs(y - end[1]) <= 2:
            return True, n_surviving, n_reachable

        # 4-connected neighbors
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid and 0 <= ny < grid:
                if mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((nx, ny))

    return False, n_surviving, n_reachable


def analyze_phase_lock(pair_name="Spica", phase=0.0, grid=192,
                        settle=25000, measure=6000):
    """
    Run binary solver and sweep Φ_min to find Φ_crit.
    """
    from BCM_stellar_overrides import run_binary

    print(f"\n{'='*65}")
    print(f"  BCM v10 PHASE-LOCK COHERENCE — {pair_name}")
    print(f"  phase={phase:.2f}  grid={grid}")
    print(f"{'='*65}")

    # Run solver
    print(f"  Running solver...")
    result, J, info = run_binary(pair_name, grid=grid,
                                  orbital_phase=phase,
                                  settle=settle, measure=measure,
                                  verbose=True)

    cpf = result.get("cos_delta_phi_field")
    if cpf is None:
        print("  ERROR: cos_delta_phi_field not available. "
              "Requires scipy (hilbert transform).")
        return None

    pump_A = info["pump_A"]
    pump_B = info["pump_B"]
    l1 = info["L1"]
    amp_A = info.get("amp_A", 0)
    amp_B = info.get("amp_B", 0)

    print(f"  Pump A: {pump_A}  amp={amp_A:.1f}")
    print(f"  Pump B: {pump_B}  amp={amp_B:.1f}")
    print(f"  L1: {l1}")

    # Field statistics
    cpf_l1_region = cpf[max(0, l1[1]-8):l1[1]+8,
                         max(0, l1[0]-8):l1[0]+8]
    cpf_active = cpf_l1_region[cpf_l1_region > 0]
    cpf_min_l1 = float(np.min(cpf_active)) if len(cpf_active) > 0 else 0
    cpf_mean_l1 = float(np.mean(cpf_active)) if len(cpf_active) > 0 else 0

    print(f"  cos_dphi field: min={np.min(cpf):.6f}  "
          f"max={np.max(cpf):.6f}")
    print(f"  L1 region: min={cpf_min_l1:.6f}  mean={cpf_mean_l1:.6f}")

    # --- Φ_min sweep ---
    phi_values = [
        0.999999, 0.99999, 0.9999, 0.999, 0.998, 0.995,
        0.99, 0.98, 0.97, 0.95, 0.93, 0.90,
        0.85, 0.80, 0.70, 0.60, 0.50
    ]

    total_pixels = grid * grid

    print(f"\n  {'Phi_min':>10} {'surviving':>10} {'%':>6} "
          f"{'reachable':>10} {'connected':>10} {'status'}")
    print(f"  {'-'*10} {'-'*10} {'-'*6} {'-'*10} {'-'*10} {'-'*15}")

    results = []
    phi_crit = None
    phi_first_connect = None

    for phi_min in phi_values:
        connected, n_surv, n_reach = flood_fill_connected(
            cpf, phi_min, pump_A, pump_B, grid)

        pct = 100.0 * n_surv / total_pixels

        if connected:
            status = "CONNECTED"
            if phi_first_connect is None:
                phi_first_connect = phi_min
        else:
            status = "DISCONNECTED"
            phi_crit = phi_min

        print(f"  {phi_min:>10.6f} {n_surv:>10} {pct:>5.1f}% "
              f"{n_reach:>10} {connected!s:>10} {status}")

        results.append({
            "phi_min":     phi_min,
            "n_surviving": n_surv,
            "pct_surviving": round(pct, 2),
            "n_reachable": n_reach,
            "connected":   connected,
            "status":      status,
        })

    # --- Summary ---
    print(f"\n  {'='*65}")
    print(f"  PHASE-LOCK SUMMARY — {pair_name}  phase={phase:.1f}")
    print(f"  {'='*65}")

    if phi_crit is not None and phi_first_connect is not None:
        print(f"  Φ_crit (last disconnected):    {phi_crit:.6f}")
        print(f"  Φ_connect (first connected):   {phi_first_connect:.6f}")
        print(f"  Break band: [{phi_first_connect:.6f}, {phi_crit:.6f}]")
    elif phi_first_connect is not None:
        print(f"  Bridge connected at all tested Φ_min down to "
              f"{phi_values[-1]}")
        print(f"  First connection at: {phi_first_connect:.6f}")
    else:
        print(f"  Bridge NEVER connected at any tested threshold")

    # I_B from sigma field
    sigma_avg = result.get("sigma_avg")
    i_b = 0.0
    if sigma_avg is not None:
        sig_field = sigma_avg.sum(axis=0)
        r = min(8, grid // 16)

        def _s(f, cx, cy):
            return float(np.max(np.abs(
                f[max(0,cy-r):cy+r, max(0,cx-r):cx+r])))

        sig_l1 = _s(sig_field, l1[0], l1[1])
        mid_bx = (l1[0] + pump_B[0]) // 2
        mid_by = (l1[1] + pump_B[1]) // 2
        sig_mb = _s(sig_field, mid_bx, mid_by)
        i_b = sig_mb - sig_l1

    sync = info.get("synchronized", False)
    print(f"  I_B: {i_b:+.1f}  "
          f"{'RESISTANT' if i_b > 0 else 'DRAIN'}  "
          f"{'SYNC' if sync else 'UNSYNC'}")

    # --- Save ---
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_phaselock_{pair_name}_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":     "BCM v10 Phase-Lock Coherence Analysis",
        "author":    "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "pair":      pair_name,
        "phase":     phase,
        "grid":      grid,
        "amp_A":     amp_A,
        "amp_B":     amp_B,
        "ratio":     round(amp_A / max(0.01, amp_B), 1),
        "sync":      sync,
        "cpf_min":   round(float(np.min(cpf)), 8),
        "cpf_max":   round(float(np.max(cpf)), 8),
        "cpf_l1_min": round(cpf_min_l1, 8),
        "cpf_l1_mean": round(cpf_mean_l1, 8),
        "phi_crit":  phi_crit,
        "phi_first_connect": phi_first_connect,
        "I_B":       round(i_b, 2),
        "n_steps":   len(results),
        "sweep":     results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")

    return out_data


def compare_systems(results_list):
    """Compare Φ_crit across multiple systems."""
    print(f"\n{'='*70}")
    print(f"  PHASE-LOCK COMPARATIVE TABLE")
    print(f"{'='*70}")
    print(f"\n  {'System':<25} {'Ratio':>6} {'Sync':>5} "
          f"{'Φ_crit':>10} {'I_B':>8} {'Status'}")
    print(f"  {'-'*25} {'-'*6} {'-'*5} {'-'*10} {'-'*8} {'-'*12}")

    for r in results_list:
        label = f"{r['pair']} ph={r['phase']}"
        sync = "SYNC" if r.get("sync") else "—"
        phi_c = r.get("phi_crit")
        phi_str = f"{phi_c:.6f}" if phi_c is not None else "NONE"
        i_b = r.get("I_B", 0)
        status = "RESISTANT" if i_b > 0 else "DRAIN"
        print(f"  {label:<25} {r.get('ratio', 0):>5.1f}x {sync:>5} "
              f"{phi_str:>10} {i_b:>+8.1f} {status}")

    # Check for universal Φ_crit
    crits = [r["phi_crit"] for r in results_list
             if r.get("phi_crit") is not None]
    if crits:
        print(f"\n  Φ_crit range: {min(crits):.6f} — {max(crits):.6f}")
        if max(crits) - min(crits) < 0.01:
            print(f"  >>> CANDIDATE INVARIANT: Φ_crit ~ {np.mean(crits):.6f}")
        else:
            print(f"  >>> System-dependent. Not a universal constant.")

    print(f"{'='*70}\n")


def run_compare(grid=192, settle=25000, measure=6000):
    """Run phase-lock analysis on all three binary systems."""
    systems = [
        ("Spica", 0.0),
        ("Spica", 0.5),
        ("Alpha_Cen", 0.5),
        ("HR_1099", 0.5),
        ("HR_1099", 0.0),
    ]

    results = []
    for pair, phase in systems:
        r = analyze_phase_lock(pair, phase, grid, settle, measure)
        if r is not None:
            results.append(r)

    if results:
        compare_systems(results)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v10 Phase-Lock Coherence Analyzer")
    parser.add_argument("--pair", type=str, default=None,
                        help="Binary pair name (omit for --compare)")
    parser.add_argument("--phase", type=float, default=0.0)
    parser.add_argument("--grid", type=int, default=192)
    parser.add_argument("--settle", type=int, default=25000)
    parser.add_argument("--measure", type=int, default=6000)
    parser.add_argument("--compare", action="store_true",
                        help="Run all five systems and compare")
    args = parser.parse_args()

    if args.compare:
        run_compare(grid=args.grid, settle=args.settle,
                     measure=args.measure)
    elif args.pair:
        analyze_phase_lock(pair_name=args.pair, phase=args.phase,
                            grid=args.grid, settle=args.settle,
                            measure=args.measure)
    else:
        print("Usage: python BCM_phase_lock.py --pair Spica --phase 0.0")
        print("       python BCM_phase_lock.py --compare")
