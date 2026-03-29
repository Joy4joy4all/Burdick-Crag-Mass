"""
Rotation Curve Comparison - Four-Way Test (v2)
Stephen Justin Burdick, 2026

DECISIVE TEST. No per-galaxy scaling.
V = sqrt(r * |dPsi/dr|) — raw from the field.

One universal calibration constant C_cal determined from
the full dataset. If one constant works across 175 galaxies,
the model is making predictions, not fitting.

V_obs, V_newton, V_MOND, V_substrate on equal footing.
MOND: Milgrom 1983, a0 = 1.2e-10 m/s^2
"""

import numpy as np

A0_SI = 1.2e-10
KPC_TO_M = 3.0857e19
KMS_TO_MS = 1000.0

# ─────────────────────────────────────────
# Universal calibration constant.
# Set to None for auto-calibration on first galaxy.
# Once determined, fix across all galaxies.
# ─────────────────────────────────────────
_C_CAL = None
_C_CAL_VALUES = []


def reset_calibration():
    """Reset calibration for a new batch run."""
    global _C_CAL, _C_CAL_VALUES
    _C_CAL = None
    _C_CAL_VALUES = []


def get_calibration_stats():
    """Return statistics on calibration constants across galaxies."""
    if not _C_CAL_VALUES:
        return None
    vals = np.array(_C_CAL_VALUES)
    return {
        "n": len(vals),
        "mean": float(np.mean(vals)),
        "median": float(np.median(vals)),
        "std": float(np.std(vals)),
        "cv": float(np.std(vals) / np.mean(vals)) if np.mean(vals) > 0 else 0,
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
    }


def compute_mond_velocity(v_baryonic, r_kpc):
    """MOND velocity. mu(x) = x/(1+x), x = g_N/a0."""
    v_mond = np.zeros_like(v_baryonic)
    for i in range(len(v_baryonic)):
        v_n = v_baryonic[i] * KMS_TO_MS
        r = r_kpc[i] * KPC_TO_M
        if r <= 0 or v_n <= 0:
            v_mond[i] = v_baryonic[i]; continue
        g_n = (v_n ** 2) / r
        x = g_n / A0_SI
        if x > 100: mu = 1.0
        elif x < 0.01: mu = x
        else: mu = x / (1.0 + x)
        g_mond = g_n / mu if mu > 0 else g_n
        v_mond[i] = np.sqrt(g_mond * r) / KMS_TO_MS
    return v_mond


def extract_velocity_raw(radial_potential, r_axis, r_kpc_axis):
    """
    V = sqrt(r * |dPsi/dr|)

    No scaling. No normalization. Raw from the field.
    Returns velocity in solver units.
    """
    if len(radial_potential) < 3:
        return np.zeros_like(r_kpc_axis)

    # Gradient in grid units
    dpsi_dr = np.gradient(radial_potential, 1.0)

    # V^2 = r * |dPsi/dr|
    r_grid = np.arange(len(radial_potential), dtype=float)
    v_sq = r_grid * np.abs(dpsi_dr)
    v_sq = np.maximum(v_sq, 0.0)
    v_raw = np.sqrt(v_sq)

    # Map to physical radii
    max_r_grid = len(radial_potential) - 1
    max_r_kpc = r_kpc_axis[-1] if len(r_kpc_axis) > 0 else 1.0
    if max_r_grid <= 0 or max_r_kpc <= 0:
        return np.zeros_like(r_kpc_axis)

    scale = max_r_kpc / max_r_grid
    v_interp = np.interp(r_kpc_axis / scale, r_grid, v_raw,
                          left=0.0, right=0.0)
    return v_interp


def compare_rotation(solver_result, galaxy_data, use_universal_cal=True):
    """
    Four-way comparison. No per-galaxy scaling.

    If use_universal_cal=True:
        First galaxy sets C_cal. All subsequent galaxies use the same value.
        This tests whether one constant works universally.

    If use_universal_cal=False:
        Each galaxy gets its own C_cal (equivalent to old peak-matching).
        Use this to compare against the universal approach.
    """
    global _C_CAL, _C_CAL_VALUES

    r_kpc = galaxy_data["radii_kpc"]
    v_obs = galaxy_data["vobs"]
    v_newton = galaxy_data["newtonian_curve"]

    # MOND
    v_mond = compute_mond_velocity(v_newton, r_kpc)

    # Substrate: raw velocity from field gradient
    r_ax, prof_psi = solver_result["radial_psi"]
    v_raw = extract_velocity_raw(prof_psi, r_ax, r_kpc)

    # Compute what C_cal this galaxy would need
    v_raw_max = np.max(v_raw) if np.max(v_raw) > 0 else 1.0
    v_obs_max = np.max(v_obs) if np.max(v_obs) > 0 else 1.0
    galaxy_cal = v_obs_max / v_raw_max

    # Track all calibration values
    _C_CAL_VALUES.append(galaxy_cal)

    if use_universal_cal:
        if _C_CAL is None:
            # First galaxy sets the universal constant
            _C_CAL = galaxy_cal

        v_substrate = v_raw * _C_CAL
    else:
        # Per-galaxy scaling (old method, for comparison)
        v_substrate = v_raw * galaxy_cal

    # ── Metrics ──
    def rms(a, b):
        return np.sqrt(np.mean((a - b) ** 2))

    def corr(a, b):
        if np.std(a) > 0 and np.std(b) > 0:
            return np.corrcoef(a, b)[0, 1]
        return 0.0

    rms_newton = rms(v_newton, v_obs)
    rms_mond = rms(v_mond, v_obs)
    rms_substrate = rms(v_substrate, v_obs)

    corr_newton = corr(v_newton, v_obs)
    corr_mond = corr(v_mond, v_obs)
    corr_substrate = corr(v_substrate, v_obs)

    # Outer half
    n = len(r_kpc)
    o = slice(n // 2, n)
    if n > 4:
        orn = rms(v_newton[o], v_obs[o])
        orm = rms(v_mond[o], v_obs[o])
        ors = rms(v_substrate[o], v_obs[o])
    else:
        orn = rms_newton; orm = rms_mond; ors = rms_substrate

    # Winner
    ra = {"NEWTON": rms_newton, "MOND": rms_mond, "SUBSTRATE": rms_substrate}
    oa = {"NEWTON": orn, "MOND": orm, "SUBSTRATE": ors}
    winner = min(ra, key=ra.get)
    outer_winner = min(oa, key=oa.get)
    sr = sorted(ra.values())
    if len(sr) >= 2 and sr[1] - sr[0] < 0.5: winner = "TIE"
    so = sorted(oa.values())
    if len(so) >= 2 and so[1] - so[0] < 0.5: outer_winner = "TIE"

    return {
        "r_kpc": r_kpc, "v_obs": v_obs, "v_newton": v_newton,
        "v_mond": v_mond, "v_substrate": v_substrate,
        "v_raw": v_raw,
        "c_cal_galaxy": galaxy_cal,
        "c_cal_used": _C_CAL if use_universal_cal else galaxy_cal,

        "rms_newton": rms_newton, "rms_mond": rms_mond,
        "rms_substrate": rms_substrate,
        "corr_newton": corr_newton, "corr_mond": corr_mond,
        "corr_substrate": corr_substrate,
        "outer_rms_newton": orn, "outer_rms_mond": orm,
        "outer_rms_substrate": ors,
        "winner": winner, "outer_winner": outer_winner,
        "sub_vs_newton": rms_newton - rms_substrate,
        "sub_vs_mond": rms_mond - rms_substrate,
    }


def print_comparison(comp, galaxy_name=""):
    """Print four-way comparison."""
    nm = f": {galaxy_name}" if galaxy_name else ""
    print(f"\n  {'='*55}")
    print(f"  ROTATION CURVE{nm}")
    print(f"  {'='*55}")
    if len(comp['r_kpc']) > 0:
        print(f"  Points: {len(comp['r_kpc'])}  "
              f"R: {comp['r_kpc'][0]:.1f}-{comp['r_kpc'][-1]:.1f} kpc")
    print(f"  C_cal used: {comp['c_cal_used']:.4f}  "
          f"(galaxy would need: {comp['c_cal_galaxy']:.4f})")

    print(f"\n  {'Model':<12} {'RMS':>8} {'Shape r':>10}")
    print(f"  {'─'*12} {'─'*8} {'─'*10}")
    print(f"  {'Newton':<12} {comp['rms_newton']:>8.2f} {comp['corr_newton']:>+10.4f}")
    print(f"  {'MOND':<12} {comp['rms_mond']:>8.2f} {comp['corr_mond']:>+10.4f}")
    print(f"  {'Substrate':<12} {comp['rms_substrate']:>8.2f} {comp['corr_substrate']:>+10.4f}")
    print(f"  Winner: {comp['winner']}  (outer: {comp['outer_winner']})")
    print(f"  Sub vs Newton: {comp['sub_vs_newton']:+.2f}  "
          f"Sub vs MOND: {comp['sub_vs_mond']:+.2f}")

    # Calibration spread so far
    stats = get_calibration_stats()
    if stats and stats["n"] > 1:
        print(f"\n  Calibration spread ({stats['n']} galaxies):")
        print(f"    Mean: {stats['mean']:.4f}  Std: {stats['std']:.4f}  "
              f"CV: {stats['cv']:.2%}")
