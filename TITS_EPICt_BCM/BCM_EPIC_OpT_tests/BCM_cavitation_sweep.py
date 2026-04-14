# -*- coding: utf-8 -*-
"""
BCM v9 Cavitation Sweep — Throat Bandwidth Test
=================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

Narrows the L1 corridor width while holding pump amplitudes and
separation constant. Finds the cavitation threshold — the throat
diameter where substrate flow exceeds capacity and the bridge
collapses.

Industrial analog: reducing orifice plate diameter on a fixed-pressure
pump line until flow becomes turbulent, then breaks suction.

Usage:
    python BCM_cavitation_sweep.py
    python BCM_cavitation_sweep.py --pair Spica --phase 0.0
    python BCM_cavitation_sweep.py --width-start 0.06 --width-end 0.005 --width-steps 12
"""

import numpy as np
import json
import os
import time
import argparse


def run_cavitation_sweep(pair_name="Spica", phase=0.0, grid=192,
                         width_start=0.06, width_end=0.005, width_steps=12,
                         settle=25000, measure=6000, amp_A=None):
    """
    Sweep corridor_width_frac from wide (default 0.06) to narrow.
    Monitors L1 diagnostics and three-point drift at each width.
    Finds the cavitation threshold where the bridge breaks.
    """
    from BCM_stellar_overrides import (build_binary_source, BINARY_REGISTRY)
    from core.substrate_solver import SubstrateSolver

    if pair_name not in BINARY_REGISTRY:
        print(f"ERROR: '{pair_name}' not in BINARY_REGISTRY.")
        print(f"Available: {list(BINARY_REGISTRY.keys())}")
        return

    pair = BINARY_REGISTRY[pair_name]

    # Generate width values (log-spaced for finer resolution near zero)
    widths = np.logspace(np.log10(width_start), np.log10(width_end),
                          width_steps)

    print(f"\n{'='*70}")
    print(f"  BCM v11 COMBINED STRESS SWEEP")
    print(f"  {pair_name}  phase={phase:.2f}  grid={grid}")
    if amp_A is not None:
        print(f"  amp_A OVERRIDE: {amp_A}")
    print(f"  Corridor width: {width_start:.4f} → {width_end:.4f} "
          f"({width_steps} steps, log-spaced)")
    print(f"{'='*70}")

    print(f"\n  {'width':>8} {'cos_dphi':>10} {'curl':>12} "
          f"{'sig_drift':>10} {'I_B':>10} {'Psi~Phi':>8} "
          f"{'elapsed':>8} {'verdict'}")
    print(f"  {'-'*8} {'-'*10} {'-'*12} {'-'*10} {'-'*10} "
          f"{'-'*8} {'-'*8} {'-'*20}")

    results = []

    for cwf in widths:
        J, info = build_binary_source(pair, grid=grid,
                                       orbital_phase=phase,
                                       corridor_width_frac=cwf,
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

        # Three-point sampling for sig_drift and I_B
        rho_avg = result.get("rho_avg")
        sigma_avg = result.get("sigma_avg")
        sig_drift = 0.0
        i_b = 0.0

        if sigma_avg is not None:
            sig_field = sigma_avg.sum(axis=0)
            pump_A = info["pump_A"]
            pump_B = info["pump_B"]
            mid_ax = (pump_A[0] + l1x) // 2
            mid_ay = (pump_A[1] + l1y) // 2
            mid_bx = (l1x + pump_B[0]) // 2
            mid_by = (l1y + pump_B[1]) // 2

            def _sample(f, cx, cy):
                y0 = max(0, cy - r)
                y1 = min(grid, cy + r)
                x0 = max(0, cx - r)
                x1 = min(grid, cx + r)
                return float(np.max(np.abs(f[y0:y1, x0:x1])))

            sig_ma = _sample(sig_field, mid_ax, mid_ay)
            sig_l1 = _sample(sig_field, l1x, l1y)
            sig_mb = _sample(sig_field, mid_bx, mid_by)
            sig_drift = sig_ma - sig_mb
            i_b = sig_mb - sig_l1

        # Verdict
        if l1_cos_mean > 0.999:
            if i_b > 10:
                verdict = "COHERENT (resistant)"
            else:
                verdict = "COHERENT (drain)"
        elif l1_cos_mean > 0.99:
            verdict = "STRESSED"
        elif l1_cos_mean > 0.9:
            verdict = "PARTIAL"
        elif l1_cos_mean > 0.5:
            verdict = "DECOHERENT"
        else:
            verdict = ">>> CAVITATION <<<"

        print(f"  {cwf:>8.4f} {l1_cos_mean:>+10.6f} "
              f"{l1_curl_max:>12.2e} {sig_drift:>+10.1f} "
              f"{i_b:>+10.1f} {corr:>+8.4f} {elapsed:>7.1f}s "
              f"{verdict}")

        entry = {
            "corridor_width_frac": round(float(cwf), 6),
            "cos_delta_phi":       round(l1_cos_mean, 6),
            "curl_max":            l1_curl_max,
            "sig_drift":           round(sig_drift, 2),
            "I_B":                 round(i_b, 2),
            "corr_full":           round(corr, 4),
            "elapsed":             round(elapsed, 1),
            "verdict":             verdict,
        }
        results.append(entry)

        # Early stop if cavitation detected
        if l1_cos_mean < 0.5:
            print(f"\n  >>> CAVITATION DETECTED at width={cwf:.4f}")
            break

    # Save results
    base = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir,
        f"BCM_cavitation_{pair_name}_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title":        "BCM v9 Cavitation Sweep — Throat Bandwidth Test",
        "author":       "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "pair":         pair_name,
        "phase":        phase,
        "grid":         grid,
        "width_range":  [round(width_start, 6), round(width_end, 6),
                         width_steps],
        "n_runs":       len(results),
        "results":      results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")

    # Summary
    print(f"\n  {'='*70}")
    print(f"  CAVITATION SWEEP SUMMARY — {pair_name}")
    print(f"  {'='*70}")
    coherent = sum(1 for r in results if "COHERENT" in r["verdict"])
    stressed = sum(1 for r in results if r["verdict"] == "STRESSED")
    cavitated = sum(1 for r in results if "CAVITATION" in r["verdict"])
    print(f"  Coherent: {coherent}  Stressed: {stressed}  Cavitated: {cavitated}")
    if results:
        widest = results[0]
        narrowest = results[-1]
        print(f"  Widest:    cwf={widest['corridor_width_frac']:.4f}  "
              f"drift={widest['sig_drift']:+.1f}  I_B={widest['I_B']:+.1f}")
        print(f"  Narrowest: cwf={narrowest['corridor_width_frac']:.4f}  "
              f"drift={narrowest['sig_drift']:+.1f}  I_B={narrowest['I_B']:+.1f}")
    print(f"{'='*70}\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v9 Cavitation Sweep — Throat Bandwidth Test")
    parser.add_argument("--pair", type=str, default="Spica",
                        help="Binary pair name")
    parser.add_argument("--phase", type=float, default=0.0,
                        help="Orbital phase (0.0=periastron)")
    parser.add_argument("--grid", type=int, default=192,
                        help="Solver grid size")
    parser.add_argument("--width-start", type=float, default=0.06,
                        help="Starting corridor width fraction (default)")
    parser.add_argument("--width-end", type=float, default=0.005,
                        help="Ending corridor width fraction (narrowest)")
    parser.add_argument("--width-steps", type=int, default=12,
                        help="Number of width steps (log-spaced)")
    parser.add_argument("--settle", type=int, default=25000,
                        help="Solver settle steps")
    parser.add_argument("--measure", type=int, default=6000,
                        help="Solver measure steps")
    parser.add_argument("--amp-A", type=float, default=None,
                        help="Override pump A amplitude (combined stress)")
    args = parser.parse_args()

    run_cavitation_sweep(pair_name=args.pair, phase=args.phase, grid=args.grid,
                         width_start=args.width_start, width_end=args.width_end,
                         width_steps=args.width_steps,
                         settle=args.settle, measure=args.measure,
                         amp_A=args.amp_A)
