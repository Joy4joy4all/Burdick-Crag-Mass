"""
SPARC Ingestion Module for Substrate Solver
============================================
Stephen Justin Burdick, 2026

Datasets Used:
1) SPARC Rotation Curves (Lelli+2016, Zenodo DOI:10.5281/zenodo.16284118)
2) SPARC Photometric Profiles (3.6 μm)
3) SPARC Mass Models (Disk, Bulge, Gas)
4) Processed CSV rotations (DMF-SPARC)
5) Rotation Model Tables (Newtonian decomposition)

Credit: All datasets credited to original authors.
No alteration beyond unit/grid conversion.

Usage:
    from sparc_ingest import load_galaxy, load_multiple_galaxies
    galaxy = load_galaxy("data/sparc_raw/NGC2403_rotmod.dat")
    J = galaxy["source_field"]       # 2D source for solver
    df = galaxy["rotation_curve"]    # raw data
"""

import numpy as np
import os

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

DEFAULT_GRID = 256
DEFAULT_DX = 1.0


# ─────────────────────────────────────────
# LOAD ROTATION CURVE
# ─────────────────────────────────────────

def load_rotation_curve(dat_path):
    """
    Load a SPARC rotation curve .dat file.

    Expected columns (whitespace-delimited):
        radius_kpc  Vobs_kms  errV  Vgas  Vdisk  Vbul  SBdisk  SBbul

    Returns dict with arrays for each column.
    """
    data = {
        "radius_kpc": [],
        "Vobs_kms": [],
        "errV": [],
        "Vgas": [],
        "Vdisk": [],
        "Vbul": [],
        "SBdisk": [],
        "SBbul": [],
    }

    col_names = list(data.keys())

    with open(dat_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            # Handle variable column counts gracefully
            for i, col in enumerate(col_names):
                if i < len(parts):
                    try:
                        data[col].append(float(parts[i]))
                    except ValueError:
                        data[col].append(0.0)
                else:
                    data[col].append(0.0)

    for key in data:
        data[key] = np.array(data[key])

    return data


# ─────────────────────────────────────────
# BUILD 2D SOURCE FIELD FROM ROTATION CURVE
# ─────────────────────────────────────────

def build_source_field(rotation_data, grid=DEFAULT_GRID, scale_factor=1.0,
                       source_mode="classic", lam=0.1):
    """
    Convert baryonic rotation components into a 2D source field J(x,y).

    CRITICAL: Uses ONLY baryonic components (Vgas, Vdisk, Vbul).
    NOT Vobs. Feeding Vobs would be circular.

    source_mode="classic" (original):
        J(r) = V_bar²(r) / r
        Peaks at center. Standard gravitational field strength.

    source_mode="edge" (Burdick edge coupling):
        J(r) = |d(V_bar²)/dr|
        Peaks where baryonic energy density is changing fastest —
        the edge of the disk, where baryons end and substrate begins.
        This is where energy transfers in a 2D medium (2D Green's
        function is logarithmic — it lives at boundaries, not centers).

        Then Compton-smoothed with σ = 1/√λ grid units.
        σ is NOT a free parameter — it is set by λ, the same decay
        term already in the wave equation. Below the Compton length
        the field has no definite localization (Heisenberg). Smoothing
        over λ_C removes sub-Compton artifacts without tuning.

    Physics reference:
        Klein-Gordon mass term: λρ → Compton length λ_C = C/√λ
        2D Poisson Green's function: G(r) = ln(r)/2π  [not 1/r]
        Edge coupling: J couples where ∂(V_bar²)/∂r is maximum
    """
    center = grid // 2
    J = np.zeros((grid, grid))

    radii = rotation_data["radius_kpc"]
    vgas  = rotation_data["Vgas"]
    vdisk = rotation_data["Vdisk"]
    vbul  = rotation_data["Vbul"]

    if len(radii) == 0:
        return J
    max_r = radii[-1]
    if max_r <= 0:
        return J

    # Baryonic energy: V_bar² = Vgas² + Vdisk² + Vbul²
    v_bar_sq = vgas ** 2 + vdisk ** 2 + vbul ** 2

    if source_mode == "classic":
        # ── Original: V_bar²/r ──
        j_radial = np.zeros_like(radii)
        for i in range(len(radii)):
            if radii[i] > 0:
                j_radial[i] = v_bar_sq[i] / radii[i]

    elif source_mode == "edge":
        # ── Edge coupling: |d(V_bar²)/dr| ──
        # Gradient of baryonic energy density along radius.
        # Peaks at the disk edge — where baryonic field transitions
        # into the substrate-dominated regime.
        dv2_dr = np.gradient(v_bar_sq, radii)
        j_radial = np.abs(dv2_dr)

        # Compton smoothing: σ = 1/√λ in grid units.
        # Convert σ from grid units to radial sample units.
        # grid center-to-edge spans max_r kpc over (center-1) grid units.
        # Radial samples are irregularly spaced — work in sample index space.
        scale = max_r / (center - 1)          # kpc per grid unit
        sigma_grid = 1.0 / np.sqrt(max(lam, 1e-6))   # grid units
        sigma_kpc  = sigma_grid * scale        # kpc
        n = len(radii)

        # Gaussian kernel in sample space (irregular spacing handled by
        # computing weight from physical radial distance, not index)
        j_smoothed = np.zeros_like(j_radial)
        for i in range(n):
            weights = np.exp(-0.5 * ((radii - radii[i]) / sigma_kpc) ** 2)
            wsum = np.sum(weights)
            if wsum > 0:
                j_smoothed[i] = np.sum(weights * j_radial) / wsum
        j_radial = j_smoothed

        # Guard: zero out anything inside the innermost data point
        # (no data to define the edge there)
        j_radial[0] = 0.0

    else:
        raise ValueError(f"Unknown source_mode: {source_mode!r}. "
                         f"Use 'classic' or 'edge'.")

    # ── Map 1D radial profile to 2D grid ──
    scale = max_r / (center - 1)

    for iy in range(grid):
        for ix in range(grid):
            r_grid = np.sqrt((ix - center) ** 2 + (iy - center) ** 2)
            r_kpc  = r_grid * scale

            if r_kpc > max_r or r_kpc <= 0:
                continue

            idx = np.searchsorted(radii, r_kpc)
            if idx >= len(radii):
                idx = len(radii) - 1
            elif idx == 0:
                idx = 1

            r0, r1 = radii[idx - 1], radii[idx]
            v0, v1 = j_radial[idx - 1], j_radial[idx]

            if r1 > r0:
                frac = (r_kpc - r0) / (r1 - r0)
                J[iy, ix] = (v0 + frac * (v1 - v0)) * scale_factor
            else:
                J[iy, ix] = v0 * scale_factor

    return J


# ─────────────────────────────────────────
# BUILD NEWTONIAN REFERENCE FROM COMPONENTS
# ─────────────────────────────────────────

def build_newtonian_curve(rotation_data):
    """
    Compute the total Newtonian predicted velocity from
    the baryonic components (gas + disk + bulge).

    V_newton² = Vgas² + Vdisk² + Vbul²

    The difference between Vobs and V_newton is conventionally
    attributed to dark matter. Our model attributes it to
    substrate screening.
    """
    vgas = rotation_data["Vgas"]
    vdisk = rotation_data["Vdisk"]
    vbul = rotation_data["Vbul"]

    # Quadrature sum of components
    v_newton_sq = vgas ** 2 + vdisk ** 2 + vbul ** 2
    v_newton = np.sqrt(np.maximum(v_newton_sq, 0.0))

    return v_newton


# ─────────────────────────────────────────
# COMPUTE DISCREPANCY (what dark matter "explains")
# ─────────────────────────────────────────

def compute_discrepancy(rotation_data):
    """
    The gap between observed and Newtonian-predicted rotation.

    discrepancy² = Vobs² - (Vgas² + Vdisk² + Vbul²)

    Positive discrepancy = galaxies rotate faster than baryons predict.
    This is the "dark matter" signal. Our model says it's the substrate.
    """
    vobs = rotation_data["Vobs_kms"]
    v_newton = build_newtonian_curve(rotation_data)

    disc_sq = vobs ** 2 - v_newton ** 2
    # Keep sign information
    disc = np.sign(disc_sq) * np.sqrt(np.abs(disc_sq))

    return {
        "radius_kpc": rotation_data["radius_kpc"],
        "Vobs": vobs,
        "V_newton": v_newton,
        "discrepancy": disc,
        "disc_fraction": disc / np.maximum(vobs, 0.01),
    }


# ─────────────────────────────────────────
# LOAD SINGLE GALAXY — FULL PACKAGE
# ─────────────────────────────────────────

def load_galaxy(dat_path, grid=DEFAULT_GRID, scale_factor=1.0,
                source_mode="classic", lam=0.1):
    """
    Load a galaxy and prepare everything the solver needs.

    Returns dict with:
        name:            galaxy name
        rotation_curve:  raw data dict
        source_field:    2D J array for solver
        newtonian_curve: predicted V from baryons
        discrepancy:     Vobs vs V_newton gap
        radii_kpc:       radial axis
        vobs:            observed velocities
        source_mode:     which J construction was used
    """
    name = os.path.basename(dat_path).split("_")[0]
    rot = load_rotation_curve(dat_path)
    J = build_source_field(rot, grid, scale_factor,
                           source_mode=source_mode, lam=lam)
    v_newton = build_newtonian_curve(rot)
    disc = compute_discrepancy(rot)

    return {
        "name": name,
        "dat_path": dat_path,
        "rotation_curve": rot,
        "source_field": J,
        "newtonian_curve": v_newton,
        "discrepancy": disc,
        "radii_kpc": rot["radius_kpc"],
        "vobs": rot["Vobs_kms"],
        "source_mode": source_mode,
    }


# ─────────────────────────────────────────
# BATCH LOADER
# ─────────────────────────────────────────

def load_multiple_galaxies(dat_dir, grid=DEFAULT_GRID, max_files=None,
                           scale_factor=1.0):
    """
    Load all _rotmod.dat files from a directory.
    Returns dict keyed by galaxy name.
    """
    galaxies = {}
    files = sorted([
        f for f in os.listdir(dat_dir)
        if f.endswith("_rotmod.dat") or f.endswith(".dat")
    ])

    if max_files is not None:
        files = files[:max_files]

    for f in files:
        path = os.path.join(dat_dir, f)
        try:
            galaxy = load_galaxy(path, grid, scale_factor)
            galaxies[galaxy["name"]] = galaxy
            print(f"  Loaded {galaxy['name']}: "
                  f"{len(galaxy['radii_kpc'])} points, "
                  f"r_max={galaxy['radii_kpc'][-1]:.1f} kpc, "
                  f"V_max={np.max(galaxy['vobs']):.1f} km/s")
        except Exception as e:
            print(f"  SKIP {f}: {e}")

    return galaxies


# ─────────────────────────────────────────
# SUMMARY REPORT
# ─────────────────────────────────────────

def galaxy_summary(galaxy):
    """Print a summary of a loaded galaxy."""
    d = galaxy["discrepancy"]
    print(f"\n  Galaxy: {galaxy['name']}")
    print(f"  Data points:    {len(galaxy['radii_kpc'])}")
    print(f"  Radial range:   {galaxy['radii_kpc'][0]:.2f} — "
          f"{galaxy['radii_kpc'][-1]:.2f} kpc")
    print(f"  V_obs range:    {np.min(galaxy['vobs']):.1f} — "
          f"{np.max(galaxy['vobs']):.1f} km/s")
    print(f"  V_newton range: {np.min(galaxy['newtonian_curve']):.1f} — "
          f"{np.max(galaxy['newtonian_curve']):.1f} km/s")
    print(f"  Max discrepancy: {np.max(np.abs(d['discrepancy'])):.1f} km/s "
          f"({np.max(np.abs(d['disc_fraction']))*100:.1f}%)")
    print(f"  Source field:   {galaxy['source_field'].shape}, "
          f"max={np.max(galaxy['source_field']):.4f}")


# ─────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("SPARC Ingestion Module — Self Test")
    print("=" * 50)

    # Check if data directory exists
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sparc_raw")
    if os.path.exists(raw_dir):
        files = [f for f in os.listdir(raw_dir) if f.endswith(".dat")]
        if files:
            print(f"  Found {len(files)} .dat files in {raw_dir}")
            galaxies = load_multiple_galaxies(raw_dir, max_files=3)
            for name, g in galaxies.items():
                galaxy_summary(g)
        else:
            print(f"  No .dat files found in {raw_dir}")
            print(f"  Download SPARC data from:")
            print(f"  https://zenodo.org/record/16284118")
            print(f"  Place _rotmod.dat files in: {raw_dir}")
    else:
        print(f"  Data directory not found: {raw_dir}")
        print(f"  Create it and add SPARC .dat files")
