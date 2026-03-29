"""
Four-Observable Test — UGC05253
Stephen Justin Burdick, 2026

Same galaxy. Same solver. Four different Ψ mappings.
Which one collapses rotation RMS while keeping field correlation?

  1. psi = -sigma               (memory field — the 86-win version)
  2. psi = Poisson(rho^2)       (energy density — v7)
  3. psi = -(sigma * |rho|)     (hybrid, no free params)
  4. psi = Poisson(rho^2 + 0.1*lap(rho)^2)  (wave energy density)

Run: python test_observables.py
"""

import numpy as np
import sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.substrate_solver import SubstrateSolver
from core.sparc_ingest import load_galaxy

GRID = 128
LAYERS = 6
LAM = 0.01
SETTLE = 20000
MEASURE = 3000
GALAXY = "UGC05253"

# Find data file
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "sparc_raw")
dat_path = os.path.join(data_dir, f"{GALAXY}_rotmod.dat")
if not os.path.exists(dat_path):
    print(f"Not found: {dat_path}")
    sys.exit(1)

galaxy = load_galaxy(dat_path, GRID)
J = galaxy["source_field"]
r_kpc = galaxy["radii_kpc"]
v_obs = galaxy["vobs"]
v_newton = galaxy["newtonian_curve"]

print("=" * 65)
print(f"  FOUR-OBSERVABLE TEST: {GALAXY}")
print(f"  Grid={GRID} Layers={LAYERS} λ={LAM}")
print("=" * 65)

# Run solver ONCE — reuse rho and sigma for all four
print("\n  Running solver...")
solver = SubstrateSolver(grid=GRID, layers=LAYERS, lam=LAM,
                          settle=SETTLE, measure=MEASURE)
rho_avg, sigma_avg = solver.evolve(J, verbose=True)

rho0 = rho_avg[0]
sig0 = sigma_avg[0]
lap_rho = solver._laplacian(rho0)

print(f"\n  |ρ|_max = {np.max(np.abs(rho0)):.2f}")
print(f"  Σ_max  = {np.max(sig0):.2f}")

# ─────────────────────────────────────────
# Four observable mappings
# ─────────────────────────────────────────

observables = {
    "1. -Sigma": -sig0,
    "2. Poisson(rho^2)": None,  # computed below
    "3. -(Sigma*|rho|)": -(sig0 * np.abs(rho0)),
    "4. Poisson(rho^2+grad^2)": None,  # computed below
}

# Compute Poisson-based observables
rho_eff_2 = rho0 ** 2
observables["2. Poisson(rho^2)"] = solver.solve_poisson(rho_eff_2)

rho_eff_4 = rho0 ** 2 + 0.1 * lap_rho ** 2
observables["4. Poisson(rho^2+grad^2)"] = solver.solve_poisson(rho_eff_4)

# Newtonian reference
phi_newton = solver.solve_poisson(np.abs(rho0))

# ─────────────────────────────────────────
# Evaluate each observable
# ─────────────────────────────────────────

def extract_v(profile, r_kpc_axis):
    """V = sqrt(r * |dPsi/dr|), interpolated to physical radii."""
    if len(profile) < 3:
        return np.zeros_like(r_kpc_axis)
    dpdr = np.gradient(profile, 1.0)
    r_grid = np.arange(len(profile), dtype=float)
    v_grid = np.sqrt(np.maximum(r_grid * np.abs(dpdr), 0.0))
    max_rg = len(profile) - 1
    max_rk = r_kpc_axis[-1] if len(r_kpc_axis) > 0 else 1.0
    if max_rg <= 0 or max_rk <= 0:
        return np.zeros_like(r_kpc_axis)
    scale = max_rk / max_rg
    return np.interp(r_kpc_axis / scale, r_grid, v_grid, left=0, right=0)

print(f"\n{'='*65}")
print(f"  RESULTS")
print(f"{'='*65}")
print(f"\n  {'Observable':<28} {'Ψ~Φ':>8} {'∇²Ψ~ρ':>8} {'RMS':>8} {'Shape':>8} {'Winner':>8}")
print(f"  {'─'*28} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

best_rms = 999
best_name = ""

for name, psi in observables.items():
    # Field correlations
    corr_full = solver.correlation(psi, phi_newton)

    # ∇²Ψ vs source
    lap_psi = solver._laplacian(psi)
    if "Poisson" in name:
        # For Poisson-derived, check against the source used
        if "grad" in name:
            corr_lap = solver.correlation(lap_psi, rho_eff_4)
        else:
            corr_lap = solver.correlation(lap_psi, rho_eff_2)
    else:
        corr_lap = solver.correlation(lap_psi, np.abs(rho0))

    # Radial profile and velocity
    r_ax, prof = solver.radial_profile(psi)
    v_raw = extract_v(prof, r_kpc)

    # Scale to match observed peak
    v_max_raw = np.max(v_raw) if np.max(v_raw) > 0 else 1.0
    v_max_obs = np.max(v_obs) if np.max(v_obs) > 0 else 1.0
    v_model = v_raw * (v_max_obs / v_max_raw)

    # RMS and shape
    rms = np.sqrt(np.mean((v_model - v_obs) ** 2))
    if np.std(v_model) > 0 and np.std(v_obs) > 0:
        shape = np.corrcoef(v_model, v_obs)[0, 1]
    else:
        shape = 0.0

    winner = "SUB" if rms < 44.10 else "NEWT"

    if rms < best_rms:
        best_rms = rms
        best_name = name

    print(f"  {name:<28} {corr_full:>+8.4f} {corr_lap:>+8.4f}"
          f" {rms:>8.2f} {shape:>+8.4f} {winner:>8}")

    # Outer half
    n = len(r_kpc)
    o = slice(n // 2, n)
    if n > 4:
        outer_rms = np.sqrt(np.mean((v_model[o] - v_obs[o]) ** 2))
        outer_rms_n = np.sqrt(np.mean((v_newton[o] - v_obs[o]) ** 2))
        outer_winner = "SUB" if outer_rms < outer_rms_n else "NEWT"
        print(f"  {'  └ outer':<28} {'':>8} {'':>8}"
              f" {outer_rms:>8.2f} {'':>8} {outer_winner:>8}")

# Newton baseline
print(f"\n  {'Newton (baseline)':<28} {'':>8} {'':>8}"
      f" {44.10:>8.2f} {0.7575:>+8.4f} {'─':>8}")

print(f"\n  BEST OBSERVABLE: {best_name}")
print(f"  BEST RMS: {best_rms:.2f} vs Newton 44.10")

if best_rms < 44.10:
    print(f"\n  >>> SUBSTRATE WINS UGC05253 with {best_name}")
    print(f"  >>> Improvement: {44.10 - best_rms:+.2f} km/s")
else:
    print(f"\n  >>> NEWTON STILL WINS by {best_rms - 44.10:.2f} km/s")
    print(f"  >>> Closest observable: {best_name}")
