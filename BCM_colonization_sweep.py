# -*- coding: utf-8 -*-
"""
BCM Substrate Colonization Sweep (Forward)
============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Sweeps amp_A upward while holding amp_B at natural value.
Tests substrate colonization by increasing the dominant pump.

Usage:
    python BCM_colonization_sweep.py
    python BCM_colonization_sweep.py --pair Spica --phase 0.0
    python BCM_colonization_sweep.py --amp-start 20 --amp-end 100 --amp-step 5
"""

import numpy as np
import json
import os
import time
import argparse


def run_sweep(pair_name="Spica", phase=0.0, grid=192,
              amp_start=20, amp_end=100, amp_step=5,
              settle=25000, measure=6000):
    """
    Sweep amp_A while holding amp_B at its natural value.
    Logs cos(delta_phi), curl, and torus diagnostics at each step.
    """
    from BCM_stellar_overrides import (build_binary_source, BINARY_REGISTRY,
                                        _stellar_amplitude)
    from core.substrate_solver import SubstrateSolver

    if pair_name not in BINARY_REGISTRY:
        print(f"ERROR: '{pair_name}' not in BINARY_REGISTRY.")
        print(f"Available: {list(BINARY_REGISTRY.keys())}")
        return

    pair = BINARY_REGISTRY[pair_name]

    # Get natural amp_B for reference
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

    star_B_name = pair.get("star_B")
    if registry and star_B_name and star_B_name in registry:
        natural_amp_B = _stellar_amplitude(registry[star_B_name])
    elif "star_B_proxy" in pair:
        natural_amp_B = _stellar_amplitude(pair["star_B_proxy"])
    else:
        natural_amp_B = 2.4

    print(f"\n{'='*65}")
    print(f"  BCM SUBSTRATE COLONIZATION SWEEP (FORWARD)")
    print(f"  {pair_name}  phase={phase:.2f}  grid={grid}")
    print(f"  amp_B (held) = {natural_amp_B:.1f}")
    print(f"  amp_A sweep: {amp_start} to {amp_end} step {amp_step}")
    print(f"{'='*65}")

    print(f"\n  {'amp_A':>6} {'ratio':>8} {'cos_dphi':>10} {'curl':>12} "
          f"{'Psi~Phi':>8} {'elapsed':>8} {'verdict'}")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*12} {'-'*8} {'-'*8} {'-'*20}")

    results = []

    for amp_A in range(amp_start, amp_end + 1, amp_step):
        ratio = amp_A / natural_amp_B

        J, info = build_binary_source(pair, grid=grid,
                                       orbital_phase=phase,
                                       amp_A_override=amp_A)

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

        print(f"  {amp_A:>6} {ratio:>7.1f}:1 {l1_cos_mean:>+10.6f} "
              f"{l1_curl_max:>12.2e} {corr:>+8.4f} {elapsed:>7.1f}s "
              f"{verdict}")

        entry = {
            "amp_A":        amp_A,
            "amp_B":        round(natural_amp_B, 2),
            "ratio":        round(ratio, 2),
            "cos_delta_phi": round(l1_cos_mean, 6),
            "curl_max":     l1_curl_max,
            "corr_full":    round(corr, 4),
            "elapsed":      round(elapsed, 1),
            "verdict":      verdict,
        }
        results.append(entry)

        # Early stop if collapsed
        if l1_cos_mean < 0.5:
            print(f"\n  >>> TORUS COLLAPSE DETECTED at amp_A={amp_A} "
                  f"(ratio {ratio:.1f}:1)")
            break

    # Save results
    base = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir,
        f"BCM_colonization_{pair_name}_forward_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":        "BCM Substrate Colonization Sweep (FORWARD)",
        "author":       "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "pair":         pair_name,
        "phase":        phase,
        "grid":         grid,
        "mode":         "FORWARD",
        "sweep_target": "A",
        "amp_B_held":   round(natural_amp_B, 2),
        "amp_A_range":  [amp_start, amp_end, amp_step],
        "n_runs":       len(results),
        "results":      results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")

    # Summary
    print(f"\n  {'='*65}")
    print(f"  FORWARD SWEEP SUMMARY -- {pair_name}")
    print(f"  {'='*65}")
    coherent = sum(1 for r in results if r["verdict"] == "COHERENT")
    stressed = sum(1 for r in results if r["verdict"] == "STRESSED")
    collapsed = sum(1 for r in results if "COLLAPSED" in r["verdict"])
    print(f"  Coherent: {coherent}  Stressed: {stressed}  Collapsed: {collapsed}")
    if collapsed > 0:
        first_collapse = next(r for r in results if "COLLAPSED" in r["verdict"])
        print(f"  Collapse at: amp_A={first_collapse['amp_A']} "
              f"(ratio {first_collapse['ratio']}:1)")
    print(f"{'='*65}\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM Substrate Colonization Sweep (Forward)")
    parser.add_argument("--pair", type=str, default="Spica",
                        help="Binary pair name")
    parser.add_argument("--phase", type=float, default=0.0,
                        help="Orbital phase (0.0=periastron)")
    parser.add_argument("--grid", type=int, default=192,
                        help="Solver grid size")
    parser.add_argument("--amp-start", type=int, default=20,
                        help="Starting amp_A")
    parser.add_argument("--amp-end", type=int, default=100,
                        help="Ending amp_A")
    parser.add_argument("--amp-step", type=int, default=5,
                        help="amp_A increment")
    parser.add_argument("--settle", type=int, default=25000,
                        help="Solver settle steps")
    parser.add_argument("--measure", type=int, default=6000,
                        help="Solver measure steps")
    args = parser.parse_args()

    run_sweep(pair_name=args.pair, phase=args.phase, grid=args.grid,
              amp_start=args.amp_start, amp_end=args.amp_end,
              amp_step=args.amp_step, settle=args.settle,
              measure=args.measure)
