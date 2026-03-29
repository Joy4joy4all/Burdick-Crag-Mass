"""
SPARC Galaxy Runner
===================
Stephen Justin Burdick, 2026

Connects SPARC galaxy rotation curves to the substrate solver.
Runs both control (λ→0) and real (λ≠0) regimes per galaxy.
Compares substrate-predicted rotation curve against observed.

Usage:
    python run_sparc.py                          # run all galaxies
    python run_sparc.py --galaxy NGC2403         # run one galaxy
    python run_sparc.py --layers 42 --grid 256   # customize solver
"""

import numpy as np
import os
import sys
import json
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.sparc_ingest import load_galaxy, load_multiple_galaxies, galaxy_summary
from core.substrate_solver import SubstrateSolver


# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

DEFAULT_CONFIG = {
    "grid": 128,
    "layers": 6,
    "gamma": 0.05,
    "entangle": 0.02,
    "settle": 15000,
    "measure": 4000,
    "control_lambda": 0.0001,
    "real_lambda": 0.1,
    "data_dir": os.path.join(os.path.dirname(__file__), "..", "data", "sparc_raw"),
    "results_dir": os.path.join(os.path.dirname(__file__), "..", "data", "results"),
}


# ─────────────────────────────────────────
# EXTRACT ROTATION CURVE FROM SOLVER RESULT
# ─────────────────────────────────────────

def extract_rotation_curve(solver_result, galaxy_data):
    """
    Convert the solver's radial potential profile back to
    a rotation velocity curve for comparison with observations.

    Physics:
        V²(r) = r · dΦ/dr  (circular orbit condition)
        Using finite difference on the radial potential profile.
    """
    r_ax, prof_psi = solver_result["radial_psi"]
    radii_kpc = galaxy_data["radii_kpc"]
    max_r_kpc = radii_kpc[-1] if len(radii_kpc) > 0 else 1.0

    # Scale grid radii to kpc
    grid = solver_result["config"]["grid"]
    center = grid // 2
    scale = max_r_kpc / (center - 1)

    # Compute dΨ/dr (finite difference)
    dr = scale  # kpc per grid unit
    dpsi_dr = np.gradient(prof_psi, dr)

    # V² = -r · dΨ/dr (negative because Ψ is negative potential)
    r_kpc = np.arange(len(prof_psi)) * scale
    v_sq = -r_kpc * dpsi_dr
    v_sq = np.maximum(v_sq, 0.0)  # physical constraint
    v_substrate = np.sqrt(v_sq)

    # Normalize to match observed velocity scale
    vobs_max = np.max(galaxy_data["vobs"])
    v_sub_max = np.max(v_substrate) if np.max(v_substrate) > 0 else 1.0
    v_substrate_scaled = v_substrate * (vobs_max / v_sub_max)

    return {
        "r_kpc": r_kpc,
        "v_substrate": v_substrate_scaled,
        "v_substrate_raw": v_substrate,
    }


# ─────────────────────────────────────────
# RUN ONE GALAXY
# ─────────────────────────────────────────

def run_galaxy(galaxy_data, config=None):
    """Run both regimes on a single galaxy."""
    if config is None:
        config = DEFAULT_CONFIG

    name = galaxy_data["name"]
    J = galaxy_data["source_field"]
    grid = config["grid"]

    # Resize source if needed
    if J.shape[0] != grid:
        from scipy.ndimage import zoom
        factor = grid / J.shape[0]
        J = zoom(J, factor)

    print(f"\n{'='*60}")
    print(f"  GALAXY: {name}")
    print(f"  Grid={grid} Layers={config['layers']}")
    print(f"{'='*60}")

    galaxy_summary(galaxy_data)

    results = {}

    for regime, lam, label in [
        ("control", config["control_lambda"], f"CONTROL λ→0"),
        ("real", config["real_lambda"], f"REAL λ={config['real_lambda']}"),
    ]:
        print(f"\n  ── {label} ──")
        solver = SubstrateSolver(
            grid=grid,
            layers=config["layers"],
            lam=lam,
            gamma=config["gamma"],
            entangle=config["entangle"],
            settle=config["settle"],
            measure=config["measure"],
        )

        result = solver.run(J)
        rot = extract_rotation_curve(result, galaxy_data)

        # Compare substrate rotation curve to observed
        # Interpolate substrate curve at observed radii
        vobs = galaxy_data["vobs"]
        radii = galaxy_data["radii_kpc"]

        v_interp = np.interp(radii, rot["r_kpc"], rot["v_substrate"])
        if np.std(v_interp) > 0 and np.std(vobs) > 0:
            rot_corr = np.corrcoef(v_interp, vobs)[0, 1]
        else:
            rot_corr = 0.0

        # Compare against Newtonian (baryonic only)
        v_newton = galaxy_data["newtonian_curve"]
        if np.std(v_newton) > 0 and np.std(vobs) > 0:
            newton_corr = np.corrcoef(v_newton, vobs)[0, 1]
        else:
            newton_corr = 0.0

        rms_sub = np.sqrt(np.mean((v_interp - vobs) ** 2))
        rms_newton = np.sqrt(np.mean((v_newton - vobs) ** 2))

        print(f"\n  ROTATION CURVE COMPARISON:")
        print(f"  Substrate vs Obs:  r={rot_corr:+.6f}  RMS={rms_sub:.2f} km/s")
        print(f"  Newton vs Obs:     r={newton_corr:+.6f}  RMS={rms_newton:.2f} km/s")
        if rms_sub < rms_newton:
            print(f"  >>> SUBSTRATE WINS by {rms_newton-rms_sub:.2f} km/s RMS")
        else:
            print(f"  >>> NEWTON WINS by {rms_sub-rms_newton:.2f} km/s RMS")

        results[regime] = {
            "solver_result": result,
            "rotation": rot,
            "v_interpolated": v_interp,
            "rot_correlation": rot_corr,
            "newton_correlation": newton_corr,
            "rms_substrate": rms_sub,
            "rms_newton": rms_newton,
        }

    return results


# ─────────────────────────────────────────
# SAVE RESULTS
# ─────────────────────────────────────────

def save_results(galaxy_name, results, results_dir):
    """Save key metrics to JSON."""
    os.makedirs(results_dir, exist_ok=True)

    summary = {
        "galaxy": galaxy_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    for regime in ["control", "real"]:
        r = results[regime]
        summary[regime] = {
            "corr_potential": float(r["solver_result"]["corr_full"]),
            "corr_rotation": float(r["rot_correlation"]),
            "corr_newton": float(r["newton_correlation"]),
            "rms_substrate": float(r["rms_substrate"]),
            "rms_newton": float(r["rms_newton"]),
            "substrate_wins": bool(r["rms_substrate"] < r["rms_newton"]),
            "config": r["solver_result"]["config"],
        }

    path = os.path.join(results_dir, f"{galaxy_name}_result.json")
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Saved: {path}")

    return summary


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run substrate solver on SPARC galaxies")
    parser.add_argument("--galaxy", type=str, default=None,
                        help="Run a specific galaxy (e.g. NGC2403)")
    parser.add_argument("--grid", type=int, default=DEFAULT_CONFIG["grid"])
    parser.add_argument("--layers", type=int, default=DEFAULT_CONFIG["layers"])
    parser.add_argument("--lambda-real", type=float, default=DEFAULT_CONFIG["real_lambda"])
    parser.add_argument("--settle", type=int, default=DEFAULT_CONFIG["settle"])
    parser.add_argument("--measure", type=int, default=DEFAULT_CONFIG["measure"])
    parser.add_argument("--max-galaxies", type=int, default=5)
    parser.add_argument("--data-dir", type=str, default=DEFAULT_CONFIG["data_dir"])
    parser.add_argument("--results-dir", type=str, default=DEFAULT_CONFIG["results_dir"])
    args = parser.parse_args()

    config = DEFAULT_CONFIG.copy()
    config.update({
        "grid": args.grid,
        "layers": args.layers,
        "real_lambda": args.lambda_real,
        "settle": args.settle,
        "measure": args.measure,
        "data_dir": args.data_dir,
        "results_dir": args.results_dir,
    })

    print("=" * 60)
    print("  SUBSTRATE SOLVER — SPARC GALAXY RUNNER")
    print("  Stephen Justin Burdick, 2026")
    print("=" * 60)
    print(f"  Config: grid={config['grid']} layers={config['layers']}"
          f" λ_real={config['real_lambda']}")

    if args.galaxy:
        # Single galaxy
        dat_path = os.path.join(config["data_dir"],
                                f"{args.galaxy}_rotmod.dat")
        if not os.path.exists(dat_path):
            # Try without _rotmod
            candidates = [f for f in os.listdir(config["data_dir"])
                          if args.galaxy in f and f.endswith(".dat")]
            if candidates:
                dat_path = os.path.join(config["data_dir"], candidates[0])
            else:
                print(f"  ERROR: Cannot find data for {args.galaxy}")
                sys.exit(1)

        galaxy = load_galaxy(dat_path, config["grid"])
        results = run_galaxy(galaxy, config)
        save_results(galaxy["name"], results, config["results_dir"])

    else:
        # All galaxies
        if not os.path.exists(config["data_dir"]):
            print(f"\n  Data directory not found: {config['data_dir']}")
            print(f"  Download SPARC data and place .dat files there.")
            print(f"  https://zenodo.org/record/16284118")
            sys.exit(1)

        galaxies = load_multiple_galaxies(
            config["data_dir"], config["grid"], args.max_galaxies
        )

        all_summaries = []
        for name, galaxy in galaxies.items():
            results = run_galaxy(galaxy, config)
            summary = save_results(name, results, config["results_dir"])
            all_summaries.append(summary)

        # Final report
        print(f"\n\n{'='*60}")
        print(f"  BATCH SUMMARY — {len(all_summaries)} galaxies")
        print(f"{'='*60}")
        print(f"  {'Galaxy':<16} {'Sub RMS':>10} {'New RMS':>10} {'Winner':>10}")
        print(f"  {'─'*16} {'─'*10} {'─'*10} {'─'*10}")

        sub_wins = 0
        for s in all_summaries:
            r = s["real"]
            winner = "SUBSTRATE" if r["substrate_wins"] else "NEWTON"
            if r["substrate_wins"]:
                sub_wins += 1
            print(f"  {s['galaxy']:<16} {r['rms_substrate']:>10.2f}"
                  f" {r['rms_newton']:>10.2f} {winner:>10}")

        print(f"\n  Substrate wins: {sub_wins}/{len(all_summaries)}")
