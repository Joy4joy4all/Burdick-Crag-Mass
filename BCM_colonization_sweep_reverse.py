# -*- coding: utf-8 -*-
"""
BCM Substrate Colonization Reverse Sweep
==========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Holds amp_A at natural value, sweeps amp_B upward to find the
colonization boundary -- the ratio where Star B regains independent
substrate status.

Usage:
    python BCM_colonization_sweep_reverse.py
    python BCM_colonization_sweep_reverse.py --pair Spica --phase 0.0
    python BCM_colonization_sweep_reverse.py --amp-start 2 --amp-end 20 --amp-step 1
"""

import numpy as np
import json
import os
import time
import argparse


def run_reverse_sweep(pair_name="Spica", phase=0.0, grid=192,
                      amp_start=2, amp_end=20, amp_step=1,
                      settle=25000, measure=6000):
    """
    Hold amp_A at natural value, sweep amp_B upward.
    Finds where Star B regains independent substrate status.
    """
    from BCM_stellar_overrides import (build_binary_source, BINARY_REGISTRY,
                                        _stellar_amplitude)
    from core.substrate_solver import SubstrateSolver

    if pair_name not in BINARY_REGISTRY:
        print(f"ERROR: '{pair_name}' not in BINARY_REGISTRY.")
        print(f"Available: {list(BINARY_REGISTRY.keys())}")
        return

    pair = BINARY_REGISTRY[pair_name]

    # Load registry
    registry = None
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        reg_path = os.path.join(base, "data", "results",
                                 "BCM_stellar_registry.json")
        if os.path.exists(reg_path):
            with open(reg_path, encoding="utf-8") as f:
                data = json.load(f)
            registry = data.get("stars", {})
    except Exception:
        pass

    # Get natural amp_A (held constant)
    star_A_name = pair.get("star_A")
    if registry and star_A_name and star_A_name in registry:
        natural_amp_A = _stellar_amplitude(registry[star_A_name])
    else:
        natural_amp_A = 20.0

    print(f"\n{'='*65}")
    print(f"  BCM SUBSTRATE COLONIZATION REVERSE SWEEP")
    print(f"  {pair_name}  phase={phase:.2f}  grid={grid}")
    print(f"  amp_A (held) = {natural_amp_A:.1f}")
    print(f"  amp_B sweep: {amp_start} to {amp_end} step {amp_step}")
    print(f"{'='*65}")

    print(f"\n  {'amp_B':>6} {'ratio':>8} {'cos_dphi':>10} {'curl':>12} "
          f"{'Psi~Phi':>8} {'elapsed':>8} {'verdict'}")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*12} {'-'*8} {'-'*8} {'-'*20}")

    results = []

    for amp_B in range(amp_start, amp_end + 1, amp_step):
        amp_B_val = float(amp_B)
        ratio = natural_amp_A / amp_B_val

        J, info = build_binary_source(pair, grid=grid,
                                       orbital_phase=phase,
                                       amp_A_override=natural_amp_A,
                                       amp_B_override=amp_B_val)

        solver = SubstrateSolver(grid=grid, layers=6, lam=0.1,
                                  settle=settle, measure=measure)
        result = solver.run(J, verbose=False)

        # L1 diagnostics
        l1x, l1y = info["L1"]
        r = min(8, grid // 16)
        cpf = result.get("cos_delta_phi_field")
        dpf = result.get("delta_phi_field")

        l1_cos_mean = 0.0
        l1_curl_max = 0.0

        if cpf is not None and dpf is not None:
            l1_region = cpf[max(0,l1y-r):l1y+r, max(0,l1x-r):l1x+r]
            l1_active = l1_region[l1_region > 0]
            if len(l1_active) > 0:
                l1_cos_mean = float(np.mean(l1_active))

            grad_y, grad_x = np.gradient(dpf)
            curl = np.gradient(grad_y, axis=1) - np.gradient(grad_x, axis=0)
            l1_curl = curl[max(0,l1y-r):l1y+r, max(0,l1x-r):l1x+r]
            l1_curl_max = float(np.max(np.abs(l1_curl)))

        corr = result.get("corr_full", 0)
        elapsed = result.get("elapsed", 0)

        if l1_cos_mean > 0.999:
            verdict = "COHERENT"
        elif l1_cos_mean > 0.99:
            verdict = "STRESSED"
        elif l1_cos_mean > 0.9:
            verdict = "PARTIAL"
        elif l1_cos_mean > 0.5:
            verdict = "DECOHERENT"
        else:
            verdict = ">>> COLLAPSED <<<"

        print(f"  {amp_B:>6} {ratio:>7.1f}:1 {l1_cos_mean:>+10.6f} "
              f"{l1_curl_max:>12.2e} {corr:>+8.4f} {elapsed:>7.1f}s "
              f"{verdict}")

        entry = {
            "amp_A":        round(natural_amp_A, 2),
            "amp_B":        round(amp_B_val, 2),
            "ratio":        round(ratio, 2),
            "cos_delta_phi": round(l1_cos_mean, 6),
            "curl_max":     l1_curl_max,
            "corr_full":    round(corr, 4),
            "elapsed":      round(elapsed, 1),
            "verdict":      verdict,
        }
        results.append(entry)

    # Save results
    base = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir,
        f"BCM_colonization_{pair_name}_reverse_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":        "BCM Substrate Colonization Reverse Sweep",
        "author":       "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "pair":         pair_name,
        "phase":        phase,
        "grid":         grid,
        "mode":         "REVERSE",
        "sweep_target": "B",
        "amp_A_held":   round(natural_amp_A, 2),
        "amp_B_range":  [amp_start, amp_end, amp_step],
        "n_runs":       len(results),
        "results":      results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")

    # Summary
    print(f"\n  {'='*65}")
    print(f"  REVERSE SWEEP SUMMARY -- {pair_name}")
    print(f"  {'='*65}")
    coherent = sum(1 for r in results if r["verdict"] == "COHERENT")
    stressed = sum(1 for r in results if r["verdict"] == "STRESSED")
    print(f"  Coherent: {coherent}  Stressed: {stressed}")
    if results:
        first = results[0]
        last = results[-1]
        print(f"  Start: ratio {first['ratio']}:1  cos={first['cos_delta_phi']}")
        print(f"  End:   ratio {last['ratio']}:1  cos={last['cos_delta_phi']}")
    print(f"{'='*65}\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM Substrate Colonization Reverse Sweep")
    parser.add_argument("--pair", type=str, default="Spica",
                        help="Binary pair name")
    parser.add_argument("--phase", type=float, default=0.0,
                        help="Orbital phase (0.0=periastron)")
    parser.add_argument("--grid", type=int, default=192,
                        help="Solver grid size")
    parser.add_argument("--amp-start", type=int, default=2,
                        help="Starting amp_B")
    parser.add_argument("--amp-end", type=int, default=20,
                        help="Ending amp_B")
    parser.add_argument("--amp-step", type=int, default=1,
                        help="amp_B increment")
    parser.add_argument("--settle", type=int, default=25000,
                        help="Solver settle steps")
    parser.add_argument("--measure", type=int, default=6000,
                        help="Solver measure steps")
    args = parser.parse_args()

    run_reverse_sweep(pair_name=args.pair, phase=args.phase, grid=args.grid,
                      amp_start=args.amp_start, amp_end=args.amp_end,
                      amp_step=args.amp_step, settle=args.settle,
                      measure=args.measure)
