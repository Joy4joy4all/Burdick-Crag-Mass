"""
Edge Coupling Test — Burdick 2D Substrate Geometry
====================================================
Stephen Justin Burdick, 2026 — Emerald Entities LLC

Tests the edge-coupling hypothesis:
  J_edge(r) = |d(V_bar²)/dr|  (Compton-smoothed by 1/√λ)
vs the classic source:
  J_classic(r) = V_bar²/r

Run on two galaxies simultaneously:
  IC2574   — regression galaxy (won at grid 64, lost at grid 128 with classic)
  NGC4217  — solid win (best substrate margin in full dataset, +46.76 km/s)

If edge coupling:
  - rescues IC2574 without breaking NGC4217 → hypothesis supported
  - breaks NGC4217 → 2D edge effect is real but needs refinement
  - does nothing → geometry argument doesn't hold numerically

Run: python test_edge_coupling.py
"""

import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.substrate_solver import SubstrateSolver
from core.sparc_ingest import load_galaxy
from core.rotation_compare import compare_rotation

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

GRID    = 128
LAYERS  = 6
LAM     = 0.1
SETTLE  = 12000
MEASURE = 3000

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "sparc_raw")

# IC2574:  regression (classic won g64, lost g128)
# NGC4217: solid win (best margin in dataset at g128)
GALAXIES = ["IC2574", "NGC4217"]

# Known Newton baselines from batch_20260325_122443
NEWTON_BASELINE = {
    "IC2574":  {"rms_newton": 18.9, "rms_classic": 23.8, "winner_classic": "NEWTON"},
    "NGC4217": {"rms_newton": 64.4, "rms_classic": 17.6, "winner_classic": "SUBSTRATE"},
}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def run_galaxy(name, source_mode, lam=LAM):
    dat_path = os.path.join(DATA_DIR, f"{name}_rotmod.dat")
    if not os.path.exists(dat_path):
        print(f"  NOT FOUND: {dat_path}")
        return None

    gal = load_galaxy(dat_path, GRID, source_mode=source_mode, lam=lam)
    J   = gal["source_field"]

    solver = SubstrateSolver(
        grid=GRID, layers=LAYERS, lam=lam,
        settle=SETTLE, measure=MEASURE
    )
    result = solver.run(J, verbose=False)
    comp   = compare_rotation(result, gal)

    return {
        "galaxy":      name,
        "mode":        source_mode,
        "rms_newton":  comp["rms_newton"],
        "rms_sub":     comp["rms_substrate"],
        "rms_mond":    comp["rms_mond"],
        "corr_sub":    comp["corr_substrate"],
        "outer_rms_sub":   comp["outer_rms_substrate"],
        "outer_rms_newton":comp["outer_rms_newton"],
        "winner":      comp["winner"],
        "outer_winner":comp["outer_winner"],
        "sub_vs_newton": comp["sub_vs_newton"],
        "corr_full":   result["corr_full"],
        "corr_inner":  result["corr_radial_inner"],
        "elapsed":     result["elapsed"],
    }


def print_result(r, baseline):
    if r is None:
        return
    delta = r["rms_newton"] - r["rms_sub"]
    won   = "✓ SUB WINS" if r["winner"] == "SUBSTRATE" else "✗ NEWTON WINS"
    print(f"\n  Mode:          {r['mode']}")
    print(f"  Newton RMS:    {r['rms_newton']:.2f} km/s")
    print(f"  Substrate RMS: {r['rms_sub']:.2f} km/s   Δ={delta:+.2f}")
    print(f"  Shape corr:    {r['corr_sub']:+.4f}")
    print(f"  Outer:  Sub={r['outer_rms_sub']:.2f}  Newton={r['outer_rms_newton']:.2f}")
    print(f"  Winner: {won}  (outer: {r['outer_winner']})")
    print(f"  Field: Ψ~Φ={r['corr_full']:+.4f}  inner={r['corr_inner']:+.4f}")
    print(f"  Time:  {r['elapsed']:.1f}s")
    if baseline:
        print(f"  [Known classic g128: Sub={baseline['rms_classic']:.1f}  "
              f"N={baseline['rms_newton']:.1f}  winner={baseline['winner_classic']}]")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  EDGE COUPLING TEST — Burdick 2D Substrate Geometry")
    print(f"  Grid={GRID}  Layers={LAYERS}  λ={LAM}")
    print(f"  Compton length σ = 1/√λ = {1/np.sqrt(LAM):.2f} grid units")
    print("=" * 65)
    print()
    print("  Hypothesis: J couples at disk edge (|dV_bar²/dr|), not center.")
    print("  Compton smoothing: σ=1/√λ, set by wave equation, no new params.")
    print()

    all_results = {}

    for galaxy in GALAXIES:
        print(f"\n{'█'*65}")
        print(f"  GALAXY: {galaxy}")
        print(f"{'█'*65}")
        baseline = NEWTON_BASELINE.get(galaxy)

        results = {}
        for mode in ["classic", "edge"]:
            print(f"\n  Running {mode.upper()}...")
            t0 = time.time()
            r = run_galaxy(galaxy, mode)
            if r:
                results[mode] = r
                print_result(r, baseline if mode == "classic" else None)

        all_results[galaxy] = results

    # ── Side-by-side summary ──
    print(f"\n\n{'='*65}")
    print(f"  SUMMARY — CLASSIC vs EDGE")
    print(f"{'='*65}")
    print(f"\n  {'Galaxy':<10} {'Mode':<10} {'Sub RMS':>9} {'Nwt RMS':>9}"
          f" {'Δ':>7} {'Winner':<12} {'Outer'}")
    print(f"  {'─'*10} {'─'*10} {'─'*9} {'─'*9} {'─'*7} {'─'*12} {'─'*10}")

    for galaxy in GALAXIES:
        results = all_results.get(galaxy, {})
        for mode in ["classic", "edge"]:
            r = results.get(mode)
            if r:
                won = "SUB ✓" if r["winner"] == "SUBSTRATE" else "NEWTON"
                outer = "SUB" if r["outer_winner"] == "SUBSTRATE" else "NEWTON"
                print(f"  {galaxy:<10} {mode:<10} {r['rms_sub']:>9.2f}"
                      f" {r['rms_newton']:>9.2f} {r['sub_vs_newton']:>+7.2f}"
                      f" {won:<12} {outer}")
        print()

    # ── Verdict ──
    print(f"  VERDICT:")
    for galaxy in GALAXIES:
        results = all_results.get(galaxy, {})
        c = results.get("classic")
        e = results.get("edge")
        if not c or not e:
            continue
        c_won = c["winner"] == "SUBSTRATE"
        e_won = e["winner"] == "SUBSTRATE"
        if not c_won and e_won:
            print(f"  {galaxy}: RESCUED by edge coupling  "
                  f"({c['rms_sub']:.1f} → {e['rms_sub']:.1f} km/s)")
        elif c_won and e_won:
            delta = e["rms_sub"] - c["rms_sub"]
            print(f"  {galaxy}: Held — edge {'improved' if delta<0 else 'degraded'}"
                  f" by {abs(delta):.1f} km/s  ({delta:+.1f})")
        elif c_won and not e_won:
            print(f"  {galaxy}: BROKEN by edge coupling  "
                  f"({c['rms_sub']:.1f} → {e['rms_sub']:.1f} km/s)")
        else:
            print(f"  {galaxy}: Still losing — edge Δ={e['rms_sub']-c['rms_sub']:+.1f} km/s")
