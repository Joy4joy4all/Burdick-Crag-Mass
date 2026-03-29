"""
Layer Scaling Runner
====================
Stephen Justin Burdick, 2026

Runs the substrate solver at increasing layer counts
to measure how layer depth affects Poisson recovery.

Designed for overnight runs on your local machine.

Usage:
    python run_layers.py                    # default: 4,6,12,42,72
    python run_layers.py --layers 4 6 42    # custom layer counts
    python run_layers.py --grid 256         # higher resolution
"""

import numpy as np
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.substrate_solver import SubstrateSolver, gaussian_source


def run_layer_test(grid, layers, lam, settle, measure):
    """Run a single layer test, return results dict."""
    J = gaussian_source(grid)
    solver = SubstrateSolver(
        grid=grid, layers=layers, lam=lam,
        settle=settle, measure=measure
    )
    return solver.run(J)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--layers", nargs="+", type=int,
                        default=[4, 6, 12, 42, 72])
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--settle", type=int, default=20000)
    parser.add_argument("--measure", type=int, default=5000)
    parser.add_argument("--output", type=str,
                        default=os.path.join(os.path.dirname(__file__),
                                             "..", "data", "results",
                                             "layer_scaling.json"))
    args = parser.parse_args()

    print("=" * 60)
    print("  LAYER SCALING TEST")
    print(f"  Grid={args.grid} Settle={args.settle}")
    print(f"  Layers: {args.layers}")
    print("=" * 60)

    results = {}

    for n_layers in args.layers:
        print(f"\n{'█' * 60}")
        print(f"  {n_layers} LAYERS")
        print(f"{'█' * 60}")

        for lam, label in [(0.0001, "CTRL"), (0.1, "REAL")]:
            print(f"\n  {label} λ={lam}")
            t0 = time.time()
            try:
                r = run_layer_test(args.grid, n_layers, lam,
                                   args.settle, args.measure)
                elapsed = time.time() - t0
                results[f"{n_layers}L_{label}"] = {
                    "layers": n_layers,
                    "regime": label,
                    "lambda": lam,
                    "full": float(r["corr_full"]),
                    "inner": float(r["corr_radial_inner"]),
                    "radial": float(r["corr_radial_full"]),
                    "layer_coh": float(r["layer_coherence"]),
                    "elapsed": elapsed,
                }
                print(f"  Done in {elapsed:.1f}s")
            except Exception as e:
                print(f"  ERROR: {e}")
                results[f"{n_layers}L_{label}"] = {"error": str(e)}

    # Summary
    print(f"\n\n{'=' * 60}")
    print(f"  LAYER SCALING PROGRESSION")
    print(f"{'=' * 60}")
    print(f"\n  {'Config':<12} {'Ψ~Φ':>10} {'Inner':>10} {'Radial':>10}"
          f" {'Layers':>8} {'Time':>8}")
    print(f"  {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10}"
          f" {'─' * 8} {'─' * 8}")

    for key in sorted(results.keys()):
        r = results[key]
        if "error" in r:
            print(f"  {key:<12} ERROR: {r['error']}")
            continue
        print(f"  {key:<12} {r['full']:>+10.4f} {r['inner']:>+10.4f}"
              f" {r['radial']:>+10.4f} {r['layers']:>8}"
              f" {r['elapsed']:>7.1f}s")

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {args.output}")

    # The answer and the names
    ctrl_results = {k: v for k, v in results.items()
                    if "CTRL" in k and "error" not in v}
    if ctrl_results:
        best = max(ctrl_results.items(), key=lambda x: x[1]["full"])
        print(f"\n  Best control: {best[0]} at {best[1]['full']:+.6f}")
