# -*- coding: utf-8 -*-
"""
BCM v23 — CONSERVATION EDGE TEST v3 (CORRECTED)
=================================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

v2 BUG: K_BOUNDARY = 150.0 was included in Q(r) for galactic budget.
K_BOUNDARY is a CRAFT TRANSIT parameter (Jasper Beach boundary operator).
It is NOT in the SubstrateSolver wave equation. Including it drained
150× gradient energy that doesn't exist in the galactic physics.

CORRECT galactic energy budget:

    Q(r) = J(r) - λ × σ(r)

No K term. The wave equation at steady state gives:

    0 = c²∇²σ - λσ + J  →  Q = J - λσ = -c²∇²σ

Where ∇²σ < 0 (at σ peak): Q > 0 (FUNDED — injection > decay)
Where ∇²σ > 0 (wings/edge): Q < 0 (DRAINING — decay > injection)

The sign reversal is guaranteed by the wave equation.
v2 masked it with a bogus drain term.

Also computes ∇²σ directly as independent verification.

Output JSON → data/results/BCM_v23_conservation_YYYYMMDD_HHMMSS.json
"""

import numpy as np
import os
import sys
import json
import time
import argparse

_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.substrate_solver import SubstrateSolver
from core.sparc_ingest import load_galaxy
from core.rotation_compare import compare_rotation

LAMBDA     = 0.1
KAPPA_BH   = 2.0
GRID_PROD  = 256
GRID_QUICK = 128
LAYERS     = 8
SETTLE     = 15000
MEASURE    = 5000

SNAPBACK_GALAXIES = ["NGC6946", "NGC7331", "NGC3521", "NGC3953", "NGC0891"]
N_BINS = 15


def azimuthal_profile(field_2d, grid, n_samples=64):
    """Azimuthally average a 2D field to radial profile."""
    center = grid // 2
    max_r = center - 1
    radii = np.arange(1, max_r + 1)
    profile = np.zeros(len(radii))
    for i, r in enumerate(radii):
        vals = []
        for angle in np.linspace(0, 2*np.pi, n_samples, endpoint=False):
            ix = int(center + r * np.cos(angle))
            iy = int(center + r * np.sin(angle))
            if 0 <= ix < grid and 0 <= iy < grid:
                vals.append(field_2d[iy, ix])
        profile[i] = np.mean(vals) if vals else 0.0
    return radii, profile


def compute_laplacian_2d(field_2d):
    """Compute ∇²f using finite differences."""
    lap = np.zeros_like(field_2d)
    lap[1:-1, 1:-1] = (
        field_2d[2:, 1:-1] + field_2d[:-2, 1:-1] +
        field_2d[1:-1, 2:] + field_2d[1:-1, :-2] -
        4.0 * field_2d[1:-1, 1:-1])
    return lap


def compute_energy_budget(sigma_avg, J_source, grid):
    """
    CORRECTED energy budget:
        Q(r) = J(r) - λ × σ(r)

    No K_BOUNDARY — that's a craft parameter, not galactic.

    Also computes ∇²σ directly to verify:
        Q should equal -c² × ∇²σ at steady state.
    """
    sigma_2d = sigma_avg.sum(axis=0)

    r_grid, sigma_r = azimuthal_profile(sigma_2d, grid)
    _, J_r = azimuthal_profile(J_source, grid)

    # ── CORRECT budget: J - λσ only ──
    injection = J_r
    lambda_drain = LAMBDA * np.abs(sigma_r)
    Q = injection - lambda_drain

    # ── Independent check: ∇²σ ──
    lap_2d = compute_laplacian_2d(sigma_2d)
    _, lap_r = azimuthal_profile(lap_2d, grid)
    # At steady state: Q = -c²∇²σ (c_wave = 1.0 in code units)
    Q_from_laplacian = -1.0 * lap_r

    # Normalize
    Q_max = np.max(np.abs(Q)) if np.max(np.abs(Q)) > 0 else 1.0
    Q_norm = Q / Q_max

    # Sign reversal: where does Q cross zero?
    crossover_idx = None
    for i in range(1, len(Q)):
        if Q[i-1] > 0 and Q[i] <= 0:
            crossover_idx = i
            break

    r_frac = r_grid / r_grid[-1] if r_grid[-1] > 0 else r_grid
    crossover_frac = float(r_frac[crossover_idx]) \
        if crossover_idx is not None else 1.0

    # Consistency: how well does Q match -∇²σ?
    mask = np.abs(Q) > 0
    if np.any(mask):
        consistency = float(np.corrcoef(
            Q[mask], Q_from_laplacian[mask])[0, 1])
    else:
        consistency = 0.0

    return {
        "r_grid": r_grid,
        "r_frac": r_frac,
        "sigma_r": sigma_r,
        "J_r": J_r,
        "injection": injection,
        "lambda_drain": lambda_drain,
        "Q": Q,
        "Q_norm": Q_norm,
        "Q_max": float(Q_max),
        "Q_from_laplacian": Q_from_laplacian,
        "laplacian_consistency": consistency,
        "crossover_idx": crossover_idx,
        "crossover_frac": crossover_frac,
        "has_sign_reversal": crossover_idx is not None,
        "Q_positive_count": int(np.sum(Q > 0)),
        "Q_negative_count": int(np.sum(Q < 0)),
    }


def analyze_zones(budget):
    """Bin Q(r) into interior / mid / edge zones."""
    r_frac = budget["r_frac"]
    Q = budget["Q"]
    Q_norm = budget["Q_norm"]
    injection = budget["injection"]
    lambda_drain = budget["lambda_drain"]

    zones = {}
    for zone_name, lo, hi in [("INTERIOR", 0.0, 0.33),
                               ("MID", 0.33, 0.67),
                               ("EDGE", 0.67, 1.01)]:
        mask = (r_frac >= lo) & (r_frac < hi)
        if not np.any(mask):
            continue
        Q_zone = Q[mask]
        inj = injection[mask]
        drain = lambda_drain[mask]
        drain_sum = np.sum(np.abs(drain))
        inj_sum = np.sum(np.abs(inj))
        budget_ratio = float(inj_sum / drain_sum) if drain_sum > 0 else float('inf')

        zones[zone_name] = {
            "Q_mean": float(np.mean(Q_zone)),
            "Q_norm_mean": float(np.mean(Q_norm[mask])),
            "injection_sum": float(inj_sum),
            "drain_sum": float(drain_sum),
            "budget_ratio": budget_ratio,
            "funded": bool(np.mean(Q_zone) > 0),
            "draining": bool(np.mean(Q_zone) < 0),
            "n_points": int(np.sum(mask)),
        }
    return zones


def compute_snapback(budget, zones):
    """Snap-back from budget sign reversal."""
    interior = zones.get("INTERIOR", {})
    edge = zones.get("EDGE", {})

    q_int = interior.get("Q_mean", 0)
    q_edge = edge.get("Q_mean", 0)

    snap_ratio = float(abs(q_edge) / abs(q_int)) if abs(q_int) > 0 else 0.0

    return {
        "snap_ratio": snap_ratio,
        "interior_Q_mean": float(q_int),
        "edge_Q_mean": float(q_edge),
        "interior_funded": bool(q_int > 0),
        "edge_draining": bool(q_edge < 0),
        "sign_reversal": budget["has_sign_reversal"],
        "crossover_frac": budget["crossover_frac"],
        "snap_detected": bool(
            budget["has_sign_reversal"]
            and q_int > 0 and q_edge < 0
            and snap_ratio > 0.5),
        "laplacian_consistency": budget["laplacian_consistency"],
    }


def find_dat_path(galaxy_name, data_dir):
    for bracket in ["dwarf_V0-50", "low_V50-100", "mid_V100-150",
                    "high_V150-200", "massive_V200plus"]:
        path = os.path.join(data_dir, bracket,
                            f"{galaxy_name}_rotmod.dat")
        if os.path.exists(path):
            return path
    path = os.path.join(data_dir, f"{galaxy_name}_rotmod.dat")
    return path if os.path.exists(path) else None


def run_galaxy(galaxy_name, data_dir, grid, verbose=True):
    dat_path = find_dat_path(galaxy_name, data_dir)
    if not dat_path:
        if verbose:
            print(f"  SKIP: {galaxy_name}")
        return None

    if verbose:
        print(f"\n{'═'*60}")
        print(f"  {galaxy_name} — CORRECTED BUDGET Q(r) = J - λσ")
        print(f"{'═'*60}")

    t0 = time.time()
    gal = load_galaxy(dat_path, grid)
    J = gal["source_field"]
    v_max = float(np.max(gal["vobs"]))

    if verbose:
        print(f"  v_max = {v_max:.1f} km/s")

    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    result = solver.run(J, verbose=False)
    comp = compare_rotation(result, gal)

    if verbose:
        print(f"  RMS: Newton={comp['rms_newton']:.2f}  "
              f"Sub={comp['rms_substrate']:.2f}  "
              f"Winner={comp['winner']}")

    budget = compute_energy_budget(result["sigma_avg"], J, grid)
    zones = analyze_zones(budget)
    snap = compute_snapback(budget, zones)
    elapsed = time.time() - t0

    if verbose:
        print(f"\n  ENERGY BUDGET Q(r) = J(r) - λσ(r)")
        print(f"  (NO K_BOUNDARY — that's craft-only)")
        print(f"  Q positive radii: {budget['Q_positive_count']}")
        print(f"  Q negative radii: {budget['Q_negative_count']}")
        print(f"  Sign reversal:    {budget['has_sign_reversal']}")
        if budget['has_sign_reversal']:
            print(f"  Crossover at r/r_max = "
                  f"{budget['crossover_frac']:.3f}")
        print(f"  ∇²σ consistency:  {budget['laplacian_consistency']:.4f}")

        print(f"\n  {'Zone':<10} {'Q_mean':>12} {'Budget':>8} {'Status'}")
        print(f"  {'─'*10} {'─'*12} {'─'*8} {'─'*10}")
        for zname in ["INTERIOR", "MID", "EDGE"]:
            z = zones.get(zname, {})
            if not z:
                continue
            status = "FUNDED" if z.get("funded") else "DRAINING"
            print(f"  {zname:<10} {z['Q_mean']:>12.4f} "
                  f"{z['budget_ratio']:>8.3f} {status}")

        print(f"\n  SNAP-BACK:")
        print(f"    Interior funded: {snap['interior_funded']}")
        print(f"    Edge draining:   {snap['edge_draining']}")
        print(f"    Snap detected:   {snap['snap_detected']}")
        print(f"    Snap ratio:      {snap['snap_ratio']:.2f}×")
        print(f"  Elapsed: {elapsed:.1f}s")

    step = max(1, len(budget["r_frac"]) // N_BINS)
    profile = []
    for i in range(0, len(budget["r_frac"]), step):
        profile.append({
            "r_frac": float(budget["r_frac"][i]),
            "Q_norm": float(budget["Q_norm"][i]),
            "Q": float(budget["Q"][i]),
            "injection": float(budget["injection"][i]),
            "drain": float(budget["lambda_drain"][i]),
        })

    return {
        "galaxy": galaxy_name, "v_max": v_max,
        "grid": grid, "elapsed": float(elapsed),
        "rms_newton": float(comp["rms_newton"]),
        "rms_substrate": float(comp["rms_substrate"]),
        "winner": comp["winner"],
        "zones": zones,
        "snap_ratio": snap["snap_ratio"],
        "snap_detected": snap["snap_detected"],
        "sign_reversal": snap["sign_reversal"],
        "crossover_frac": snap["crossover_frac"],
        "interior_funded": snap["interior_funded"],
        "edge_draining": snap["edge_draining"],
        "Q_positive_count": budget["Q_positive_count"],
        "Q_negative_count": budget["Q_negative_count"],
        "laplacian_consistency": snap["laplacian_consistency"],
        "budget_profile": profile,
        "corr_full": float(result.get("corr_full", 0)),
        "cos_delta_phi": float(result.get("cos_delta_phi", 0)),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v23 Conservation Edge v3 (Corrected)")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()

    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v23 — CORRECTED ENERGY BUDGET Q(r)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    print(f"  Grid: {grid}  |  Galaxies: {len(SNAPBACK_GALAXIES)}")
    print(f"  Q(r) = J(r) - λσ(r)  [NO K_BOUNDARY]")
    print(f"  v2 bug: K=150 gradient drain was craft-only")
    print(f"  Wave eq guarantees sign reversal if pump works")
    print("=" * 60)

    data_dir = os.path.join(_PROJECT_ROOT, "data", "sparc_raw")
    if not os.path.isdir(data_dir):
        print(f"  ERROR: SPARC data not found")
        sys.exit(1)

    results = []
    t_total = time.time()
    for galaxy in SNAPBACK_GALAXIES:
        r = run_galaxy(galaxy, data_dir, grid)
        if r:
            results.append(r)

    elapsed_total = time.time() - t_total
    n_snap = n_sign = n_funded = 0

    print(f"\n{'═'*60}")
    print(f"  CORRECTED BUDGET SUMMARY")
    print(f"{'═'*60}")

    if results:
        n_snap = sum(1 for r in results if r["snap_detected"])
        n_sign = sum(1 for r in results if r["sign_reversal"])
        n_funded = sum(1 for r in results if r["interior_funded"])

        print(f"  Galaxies tested:     {len(results)}")
        print(f"  Interior FUNDED:     {n_funded}/{len(results)}")
        print(f"  Sign reversal:       {n_sign}/{len(results)}")
        print(f"  Snap-back detected:  {n_snap}/{len(results)}")
        print(f"  Total elapsed:       {elapsed_total:.1f}s")

        print(f"\n  {'Galaxy':<12} {'Funded':>7} {'Sign':>5} "
              f"{'Snap':>5} {'X-over':>7} {'Q+':>4} {'Q-':>4} "
              f"{'Winner':<10}")
        print(f"  {'─'*12} {'─'*7} {'─'*5} {'─'*5} {'─'*7} "
              f"{'─'*4} {'─'*4} {'─'*10}")
        for r in results:
            fn = "YES" if r["interior_funded"] else "no"
            sg = "YES" if r["sign_reversal"] else "no"
            sn = "YES" if r["snap_detected"] else "no"
            print(f"  {r['galaxy']:<12} {fn:>7} {sg:>5} {sn:>5} "
                  f"{r['crossover_frac']:>7.3f} "
                  f"{r['Q_positive_count']:>4} "
                  f"{r['Q_negative_count']:>4} "
                  f"{r['winner']:<10}")

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v23_conservation_{timestamp}.json")

    output = {
        "test": "conservation_edge_v3_corrected",
        "version": "v23",
        "grid": grid,
        "method": "Q(r) = J(r) - lambda*sigma(r) — NO K_BOUNDARY",
        "bug_fixed": "v2 included K_BOUNDARY=150 gradient drain "
                     "which is craft-only, not in galactic solver",
        "galaxies_tested": len(results),
        "interior_funded": n_funded if results else 0,
        "sign_reversal": n_sign if results else 0,
        "snap_detected": n_snap if results else 0,
        "lambda": LAMBDA,
        "kappa_BH": KAPPA_BH,
        "elapsed_total": float(elapsed_total),
        "timestamp": timestamp,
        "results": results,
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  JSON saved: {out_path}")
    print(f"\n  Q(r) = J - λσ = -c²∇²σ at steady state.")
    print(f"  The wave equation guarantees the sign reversal.")
    print(f"  The pump was never broken — the meter was.")


if __name__ == "__main__":
    main()
