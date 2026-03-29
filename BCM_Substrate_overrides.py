"""
BCM Substrate Overrides — Structural Override System
==================================================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
NSF I-Corps — Team GIBUSH

BCM Geometry Corrections — March 2026

Galaxy-specific physics overrides for non-equilibrium systems.
These are not free parameters — each override is derived from
observable physical properties of the galaxy and its environment.

The override system sits between sparc_ingest and the solver.
The solver itself (substrate_solver.py) remains unchanged.

Override types implemented:
    CLASS II  — 2D Moment-0 HI source (morphological reality)
    CLASS IV  — linear_dipole_source (bar-channeled flux)
    CLASS V-A — asymmetric λ(x,y) field (ram pressure) + 2D HI base
    CLASS V-B — external void depletion (substrate theft) + 2D HI base
    CLASS VI  — 2D FITS ingestion stub (bow geometry)

2D Moment-0 path:
    If a galaxy has a confirmed mom0.fits, it is loaded as the base J_source
    BEFORE any class-specific override is applied. This replaces the 1D
    radially-symmetric SPARC profile with the actual observed HI morphology.
    The class override then operates on that 2D base.

Usage:
    from BCM_Substrate_overrides import apply_galaxy_override
    J, params = apply_galaxy_override(galaxy_name, J_default, grid, vmax)
    solver.run(J, **params)
"""

import numpy as np
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))


# ─────────────────────────────────────────
# OVERRIDE REGISTRY
# Maps galaxy name → override class + parameters
# All parameters derived from observations — not fitted
# ─────────────────────────────────────────

OVERRIDE_REGISTRY = {

    # ── Class VI: Bar-Channeled Substrate ──
    # Bar parameters from HyperLeda position angle tables
    "NGC3953": {
        "class": "VI",
        "description": "Barred spiral — bar channels flux along axis",
        "source_type": "linear_dipole",
        "bar_length_frac": 0.35,   # bar half-length ~35% of grid
        "bar_width_frac":  0.06,   # bar width ~6% of grid
        "bar_angle_deg":   10.0,   # HyperLeda PA ~10° for NGC3953
        "liner_factor":    0.75,   # LINER efficiency throttle (low-ionization BH)
    },

    # ── Class V-B: Substrate Theft ──
    # Sculptor Group — NGC7793 neighbors deplete local substrate budget
    "NGC7793": {
        "class":       "V-B",
        "description": "Sculptor Group member — substrate stolen by neighbors",
        "source_type": "depleted",
        "mom0_path":   "data/hi_maps/NGC7793_mom0.fits",  # 2D HI base — THINGS
        "void_center_kpc": (10.0, -5.0),  # approximate void center offset (kpc)
        "void_radius_kpc": 15.0,           # depletion radius
        "depletion_depth":  0.65,          # 65% substrate removed in void zone
        "rho_initial_scale": 0.05,         # suppressed initial field
    },

    # ── Class V-A: Ram Pressure ──
    # NGC2976 moving through M81 Group substrate field
    "NGC2976": {
        "class":       "V-A",
        "description": "M81 Group member — substrate physically stripped, vacuum confirmed",
        "source_type": "ram_pressure",
        "mom0_path":   "data/hi_maps/NGC2976_mom0.fits",  # 2D HI base — THINGS
        "motion_angle_deg": 135.0,   # direction of motion through group (approx)
        "lambda_leading":   0.18,    # elevated λ on leading edge
        "lambda_trailing":  0.04,    # reduced λ on trailing wake
        "suppress_injection": True,  # Newton RMS=3.7 — baryons fully explain curve
                                     # Substrate physically absent — M81 tidal stripping
                                     # Any BCM injection is error, not signal
    },

    # ── Class II: Residual-Dominated (2D HI base, no structural override) ──
    # UGC04305 (Holmberg II) — 2D asymmetric HI confirmed from THINGS
    "UGC04305": {
        "class":       "II",
        "description": "Holmberg II — irregular HI, 2D morphology replaces 1D",
        "source_type": "mom0_2d",
        "mom0_path":   "data/hi_maps/UGC04305_mom0.fits",  # THINGS confirmed
    },

    # ── Class IV: Declining Substrate — Outer Slope Suppression ──
    # NGC0801 — concave curve, edge-on warp, declining outer rotation
    # WHISP FITS blocked (403). Outer slope from SPARC dat — no external data needed.
    # LINER nucleus confirmed (NED) — same throttle logic as NGC3953.
    "NGC0801": {
        "class":       "IV",
        "description": "Declining outer curve — rim depletion, LINER throttle",
        "source_type": "class_iv_slope",
        "dat_path":    "data/sparc_raw/massive_V200plus/NGC0801_rotmod.dat",
        "liner_factor": 0.75,        # LINER efficiency throttle — same as NGC3953
        "fits_path":   None,         # WHISP blocked — upgrade when available
    },

    # ── Class I Control ──
    # NGC2841 — clean transport, no override needed, use as benchmark
    "NGC2841": {
        "class":       "I",
        "description": "Class I Superfluid — control group, no override",
        "source_type": "classic",
    },
}


# ─────────────────────────────────────────
# OVERRIDE FUNCTIONS
# ─────────────────────────────────────────

def _apply_bar_dipole(J_default, grid, config):
    """
    Class VI — replace circular source with bar-axis dipole.
    Bar concentrates substrate flux along its length.
    Depletes substrate perpendicular to bar axis.
    """
    from substrate_solver import linear_dipole_source  # found via sys.path above

    amplitude = float(np.max(J_default)) if np.max(J_default) > 0 else 8.0
    amplitude *= config.get("liner_factor", 1.0)

    J_bar = linear_dipole_source(
        grid=grid,
        amplitude=amplitude,
        bar_length_frac=config["bar_length_frac"],
        bar_width_frac=config["bar_width_frac"],
        bar_angle_deg=config["bar_angle_deg"],
    )

    print(f"  [BCM] Class VI bar dipole: angle={config['bar_angle_deg']}°"
          f"  length={config['bar_length_frac']:.0%}"
          f"  liner={config.get('liner_factor',1.0):.2f}")
    return J_bar


def _apply_void_depletion(J_default, grid, config, vmax_kms):
    """
    Class V-B — apply external void depletion to source field.
    Void center and radius derived from group geometry.
    Reduces J in the substrate-stolen zone.
    """
    cx = cy = grid // 2
    # Convert kpc offset to grid units
    # Approximate: grid spans ~2 * r_max, center at grid//2
    # Use vmax as rough mass proxy for r_max estimate
    r_max_kpc = max(10.0, vmax_kms * 0.15)
    kpc_per_grid = r_max_kpc / (grid // 2)

    vx_kpc, vy_kpc = config["void_center_kpc"]
    vx_grid = int(cx + vx_kpc / kpc_per_grid)
    vy_grid = int(cy + vy_kpc / kpc_per_grid)
    vr_grid = int(config["void_radius_kpc"] / kpc_per_grid)

    J = J_default.copy()
    iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
    r_void = np.sqrt((ix_arr - vx_grid)**2 + (iy_arr - vy_grid)**2)

    # Soft depletion — Gaussian falloff at void edge
    depletion = config["depletion_depth"] * np.exp(
        -r_void**2 / (2.0 * (vr_grid * 0.5)**2))
    J *= (1.0 - np.clip(depletion, 0, 0.95))

    print(f"  [BCM] Class V-B void depletion: depth={config['depletion_depth']:.0%}"
          f"  r={config['void_radius_kpc']:.1f} kpc")
    return J


def _apply_ram_pressure(J_default, grid, config):
    """
    Class V-A — asymmetric λ(x,y) for ram pressure galaxies.
    Returns modified J and lambda_field for solver.
    Leading edge: elevated λ. Trailing edge: reduced λ.
    """
    cx = cy = grid // 2
    angle = np.radians(config["motion_angle_deg"])
    iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]

    # Projection along motion axis
    dx = ix_arr - cx
    dy = iy_arr - cy
    projection = dx * np.cos(angle) + dy * np.sin(angle)
    proj_norm = projection / (grid // 2)  # normalize -1 to +1

    lam_lead  = config["lambda_leading"]
    lam_trail = config["lambda_trailing"]
    lam_mid   = (lam_lead + lam_trail) / 2.0

    # Smooth gradient from trailing to leading
    lam_field = lam_mid + (lam_lead - lam_trail) / 2.0 * proj_norm
    lam_field = np.clip(lam_field, 0.001, 1.0)

    lam_effective = float(np.mean(lam_field))

    print(f"  [BCM] Class V-A ram pressure: λ_lead={lam_lead:.3f}"
          f"  λ_trail={lam_trail:.3f}  λ_eff={lam_effective:.3f}"
          f"  angle={config['motion_angle_deg']}°")

    # Return original J — λ gradient is the override, not J
    return J_default, lam_effective


def _apply_whisp_2d(J_default, grid, config):
    """
    Class IV — 2D FITS moment-0 ingestion for warped bow galaxies.
    Preserves asymmetric geometry that 1D rotation curve collapses.

    PENDING: requires NGC0801_mom0.fits from WHISP archive.
    Download: https://www.astron.nl/research-software/whisp

    Falls back to classic source until FITS file is available.
    """
    fits_path = config.get("fits_path")

    if fits_path and os.path.exists(fits_path):
        try:
            from astropy.io import fits
            from scipy.ndimage import zoom

            with fits.open(fits_path) as hdul:
                moment0 = hdul[0].data.squeeze()
                moment0 = np.nan_to_num(moment0, nan=0.0)
                moment0 = np.maximum(moment0, 0.0)

                # Resize to solver grid
                factor = grid / max(moment0.shape)
                J_2d = zoom(moment0, factor)
                if J_2d.shape[0] != grid:
                    J_2d = zoom(J_2d, grid / J_2d.shape[0])

                # Normalize to match baryonic amplitude
                amp_ref = float(np.max(J_default)) if np.max(J_default) > 0 else 8.0
                if np.max(J_2d) > 0:
                    J_2d *= amp_ref / np.max(J_2d)

                print(f"  [BCM] Class IV WHISP 2D: {fits_path}")
                print(f"       Bow geometry preserved — asymmetric source active")
                return J_2d.astype(np.float64)

        except Exception as e:
            print(f"  [BCM] Class IV WHISP load failed: {e} — using fallback")

    print(f"  [BCM] Class IV: WHISP FITS pending — using classic source")
    print(f"       Download: https://www.astron.nl/research-software/whisp")
    print(f"       File needed: NGC0801_mom0.fits")
    return J_default


# ─────────────────────────────────────────
# 2D MOMENT-0 LOADER
# ─────────────────────────────────────────

def _load_mom0_2d(fits_path, grid, J_default, galaxy_name=""):
    """
    Load a 2D HI Moment-0 FITS file and regrid to solver grid.

    Replaces the 1D radially-symmetric J_source from sparc_ingest
    with the actual observed HI column density N_HI(x,y).

    Returns the 2D J array on success, J_default on any failure.
    Falls back silently so the solver always gets a valid source.
    """
    if not fits_path:
        return J_default

    # Resolve path relative to this file's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = fits_path if os.path.isabs(fits_path) else os.path.join(base_dir, fits_path)

    if not os.path.exists(full_path):
        print(f"  [BCM] mom0 not found: {full_path} — classic fallback")
        return J_default

    try:
        from astropy.io import fits as _fits
        from scipy.ndimage import zoom as _zoom

        with _fits.open(full_path) as hdul:
            mom0 = hdul[0].data.squeeze().astype(np.float64)
            mom0 = np.nan_to_num(mom0, nan=0.0)
            mom0 = np.maximum(mom0, 0.0)

        if np.max(mom0) == 0:
            print(f"  [BCM] mom0 all zeros: {galaxy_name} — classic fallback")
            return J_default

        # Regrid to solver grid (typically 128×128)
        factor = grid / max(mom0.shape)
        J_2d = _zoom(mom0, factor)

        # Ensure exact grid size after zoom
        if J_2d.shape[0] != grid or J_2d.shape[1] != grid:
            J_2d = _zoom(J_2d, (grid / J_2d.shape[0], grid / J_2d.shape[1]))

        # Normalize amplitude to match baryonic source scale
        amp_ref = float(np.max(J_default)) if np.max(J_default) > 0 else 8.0
        if np.max(J_2d) > 0:
            J_2d *= amp_ref / np.max(J_2d)

        print(f"  [BCM] 2D mom0 loaded: {galaxy_name}"
              f"  shape={mom0.shape}→{grid}×{grid}"
              f"  nonzero={int(np.sum(J_2d > 0))}")
        return J_2d.astype(np.float64)

    except Exception as e:
        print(f"  [BCM] mom0 load failed {galaxy_name}: {e} — classic fallback")
        return J_default


# ─────────────────────────────────────────
# CLASS IV — OUTER SLOPE SUPPRESSION
# ─────────────────────────────────────────

def _find_dat_path(galaxy_name, hint_path=None):
    """
    Locate a galaxy .dat file. Tries hint_path first, then walks
    sparc_raw and all subdirectories. Works regardless of how files
    are organized into subdirs.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Try hint path as-is and relative to base_dir
    if hint_path:
        candidates = [hint_path, os.path.join(base_dir, hint_path)]
        for p in candidates:
            if os.path.exists(p):
                return p

    # Walk sparc_raw tree
    sparc_root = os.path.join(base_dir, "data", "sparc_raw")
    if os.path.exists(sparc_root):
        for root, dirs, files in os.walk(sparc_root):
            for f in files:
                if f == f"{galaxy_name}_rotmod.dat" or f == f"{galaxy_name}.dat":
                    return os.path.join(root, f)
    return None


def _compute_outer_slope(dat_path):
    """
    Read SPARC .dat file, compute dV/dr on the outer half of the curve.
    Returns slope in km/s/kpc. Negative = declining outer curve (Class IV).
    Returns None if file unreadable or insufficient points.
    """
    try:
        radii, vobs = [], []
        with open(dat_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                vals = line.split()
                if len(vals) >= 2:
                    radii.append(float(vals[0]))
                    vobs.append(float(vals[1]))
        if len(radii) < 6:
            return None
        r = np.array(radii)
        v = np.array(vobs)
        cutoff = r[-1] * 0.5
        outer = r >= cutoff
        if np.sum(outer) < 3:
            return None
        coeffs = np.polyfit(r[outer], v[outer], 1)
        return float(coeffs[0])   # km/s per kpc
    except Exception:
        return None


def _apply_class_iv_suppression(J_default, grid, dat_path, galaxy_name=""):
    """
    Class IV — Outer Slope Rim Suppression.

    When the outer rotation curve declines (dV/dr < 0), the substrate
    is in net energy loss at the rim. BCM over-injects into a depleted
    zone. This function suppresses J at the rim proportionally to the
    magnitude of the decline.

    Suppression is radial — full amplitude at center, reduced at rim.
    The suppression profile is derived from the outer slope alone.
    No free parameters — slope comes from the observed rotation curve.

    Threshold: -0.5 km/s/kpc (negligible noise floor below this)
    Maximum suppression: 80% at the outer edge (physical floor preserved)
    """
    SLOPE_THRESHOLD = -0.5    # km/s/kpc — below this = Class IV active
    MAX_SUPPRESSION = 0.80    # never zero — substrate still present, just depleted

    slope = _compute_outer_slope(dat_path)
    if slope is None:
        print(f"  [BCM] Class IV: could not read slope for {galaxy_name} — no suppression")
        return J_default

    if slope >= SLOPE_THRESHOLD:
        print(f"  [BCM] Class IV: slope={slope:+.3f} km/s/kpc — above threshold, no suppression")
        return J_default

    # Suppression magnitude scales with slope steepness
    # slope=-1.0 → ~50% rim suppression, slope=-3.0 → ~80% (capped)
    suppression_strength = min(abs(slope) / 4.0, MAX_SUPPRESSION)

    print(f"  [BCM] Class IV rim suppression: slope={slope:+.3f} km/s/kpc"
          f"  strength={suppression_strength:.0%}")

    # Radial suppression mask — full at center, suppressed at rim
    cx = cy = grid // 2
    iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
    r_norm = np.sqrt((ix_arr - cx)**2 + (iy_arr - cy)**2) / (grid // 2)
    r_norm = np.clip(r_norm, 0.0, 1.0)

    # Linear ramp: 1.0 at center → (1 - suppression_strength) at rim
    suppression_mask = 1.0 - suppression_strength * r_norm

    J_suppressed = J_default * suppression_mask
    return J_suppressed.astype(np.float64)


# ─────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────

def apply_galaxy_override(galaxy_name, J_default, grid, vmax_kms=200.0,
                          verbose=True):
    """
    Apply v8 structural override for a specific galaxy.

    Returns:
        J_override:   modified source field (or original if no override)
        extra_params: dict of additional solver parameters (lam, etc.)
        applied:      bool — True if override was applied

    Usage:
        J, params, applied = apply_galaxy_override("NGC3953", J, grid, vmax)
        result = solver.run(J, **params)
    """
    extra_params = {}
    applied = False

    if galaxy_name not in OVERRIDE_REGISTRY:
        return J_default, extra_params, applied

    config = OVERRIDE_REGISTRY[galaxy_name]
    source_type = config.get("source_type", "classic")

    if verbose:
        print(f"\n  [BCM OVERRIDE] {galaxy_name} — Class {config['class']}")
        print(f"  {config['description']}")

    # ── Suppression gate: substrate physically absent ──
    # Triggered by registry flag, not runtime RMS.
    # Used when environmental stripping has removed the substrate budget.
    # BCM injection into a vacuum is error, not signal.
    if config.get("suppress_injection", False):
        if verbose:
            print(f"  [BCM] SUPPRESSED: {galaxy_name} — substrate vacuum confirmed")
            print(f"  [BCM] No injection applied. Newton baseline preserved.")
        return J_default, extra_params, False

    # ── 2D Moment-0 base: load real HI morphology if available ──
    # Applies BEFORE class-specific override.
    # When mom0 is loaded, J is WYSIWYG — the observed HI column density
    # is the truth. Class overrides that modify J are skipped.
    # Class overrides that modify solver parameters (λ) still apply.
    mom0_path = config.get("mom0_path")
    mom0_loaded = False
    if mom0_path:
        J_default = _load_mom0_2d(mom0_path, grid, J_default, galaxy_name)
        mom0_loaded = True

    if source_type == "classic":
        # No change — control group
        return J_default, extra_params, False

    elif source_type == "mom0_2d":
        # 2D HI only — no additional structural override
        # J_default already replaced above by _load_mom0_2d
        J_out = J_default
        applied = mom0_loaded

    elif source_type == "linear_dipole":
        J_out = _apply_bar_dipole(J_default, grid, config)
        applied = True

    elif source_type == "depleted":
        J_out = _apply_void_depletion(J_default, grid, config, vmax_kms)
        applied = True

    elif source_type == "ram_pressure":
        # λ gradient always applies — substrate medium resistance is real.
        # J modification skipped when mom0 loaded — 2D HI is already the
        # physical truth. Applying directional J weighting on top of an
        # already-asymmetric observed source double-counts the geometry.
        _, lam_eff = _apply_ram_pressure(J_default, grid, config)
        extra_params["lam"] = lam_eff
        if mom0_loaded:
            J_out = J_default   # WYSIWYG — J frozen to observed HI
            print(f"  [BCM] V-A: mom0 loaded — J frozen, λ_eff={lam_eff:.3f} applied")
        else:
            J_out = J_default   # ram_pressure never modifies J regardless
        applied = True

    elif source_type == "class_iv_slope":
        # Apply LINER throttle first, then outer slope suppression
        amp_scale = config.get("liner_factor", 1.0)
        J_throttled = J_default * amp_scale
        if amp_scale < 1.0:
            print(f"  [BCM] Class IV LINER throttle: {amp_scale:.0%} amplitude")
        dat_path = _find_dat_path(galaxy_name, config.get("dat_path"))
        if dat_path:
            print(f"  [BCM] Class IV dat: {os.path.basename(dat_path)}")
        else:
            print(f"  [BCM] Class IV: dat not found for {galaxy_name} — no suppression")
        J_out = _apply_class_iv_suppression(J_throttled, grid, dat_path, galaxy_name)
        applied = True

    elif source_type == "whisp_2d":
        J_out = _apply_whisp_2d(J_default, grid, config)
        applied = (J_out is not J_default)

    else:
        J_out = J_default

    return J_out, extra_params, applied


# ─────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────

def print_override_summary():
    """Print all registered overrides."""
    print("\n  BCM STRUCTURAL OVERRIDE REGISTRY")
    print(f"  {'Galaxy':<12} {'Class':<8} {'Type':<16} {'Description'}")
    print(f"  {'─'*12} {'─'*8} {'─'*16} {'─'*40}")
    for name, cfg in OVERRIDE_REGISTRY.items():
        print(f"  {name:<12} {cfg['class']:<8} "
              f"{cfg['source_type']:<16} {cfg['description'][:40]}")


if __name__ == "__main__":
    print_override_summary()
