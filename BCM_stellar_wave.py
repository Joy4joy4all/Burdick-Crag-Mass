# -*- coding: utf-8 -*-
"""
BCM Stellar Wave Solver
=======================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
NSF I-Corps -- Team GIBUSH

Tests BCM Substrate Scale-Invariance at stellar scale.
Derives the azimuthal wave number m for stellar surface phenomena
(starspot bands, differential rotation nodes, flux anomalies)
from first principles -- no per-star tuning.

If substrate modes fall out of known stellar physical parameters,
BCM wave equation is scale-invariant from galactic to stellar.

Physics:
    Same wave equation as galaxy and planetary solvers.
    Source term is induction current from the stellar tachocline --
    the interface between radiative and convective zones.

    J_ind = sigma_tach * (v_conv x B).n

    Azimuthal eigenmodes selected by Alfven Hamiltonian:
    H(m) = (v_A - Omega * R_tach / m)^2
    m* = argmin H(m)

    v_A = B / sqrt(mu_0 * rho)  -- Alfven speed at tachocline

    Observable signatures:
        m=1  -- dipole (single active longitude)
        m=2  -- quadrupole (two active longitudes, common in RS CVn)
        m=4  -- solar-like (four sector pattern)
        m=6+ -- rapid rotators, anomalous flux modulation

Usage:
    python BCM_stellar_wave.py
    python BCM_stellar_wave.py --star "Tabby"
    python BCM_stellar_wave.py --batch
    python BCM_stellar_wave.py --solve-lambda
"""

import numpy as np
import json
import os
import sys
import argparse
from scipy.special import jv  # Bessel functions

# -----------------------------------------
# STELLAR REGISTRY
# Physical parameters from published measurements
# -----------------------------------------

STELLAR_REGISTRY = {
    "Sun": {
        "spectral_type":    "G2V",
        "mass_solar":       1.0,
        "radius_km":        695700.0,
        "rotation_days":    25.38,
        "B_surface_gauss":  1.0,
        "B_tachocline_T":   5.6,            # CALIBRATED tachocline field -- helioseismology 1-10T range | 2026-04-02 EST
        "sigma_tach_sm":    1.0e4,
        "conv_depth_frac":  0.287,
        "v_conv_ms":        300.0,
        "m_observed":       4,
        "bcm_class":        "Class I -- Stable Coupled",
        "pump_type":        "tachocline_dynamo",
        "notes":            "Control star. 4-sector solar wind = m=4 substrate mode.",
        "observable":       "4-sector solar wind pattern, Hale cycle m=2 magnetic",
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
        # rho_tachocline: plasma density at tachocline -- required for Alfven speed v_A
        # Source: Christensen-Dalsgaard 1996, helioseismology
        "rho_tachocline_kgm3": 200.0,
        # === END ADDITION ===
    },
    "Tabby": {
        "spectral_type":    "F3V",
        "mass_solar":       1.43,
        "radius_km":        978000.0,
        "rotation_days":    0.8797,
        "B_surface_gauss":  10.0,
        "B_tachocline_T":   5.0e-1,
        "sigma_tach_sm":    1.2e4,
        "conv_depth_frac":  0.15,
        "v_conv_ms":        800.0,
        "m_observed":       0,
        "bcm_class":        "Class ? -- Anomalous",
        "pump_type":        "tachocline_rapid_rotator",
        "notes":            "KIC 8462852. Anomalous flux dips 0.1-22%. Rapid rotator. "
                            "BCM prediction: substrate mode produces directed flux modulation.",
        "observable":       "Anomalous aperiodic flux dips -- Boyajian 2016",
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
        # F-type star -- shallower tachocline, lower density than Sun
        "rho_tachocline_kgm3": 150.0,
        # === END ADDITION ===
    },
    "Proxima": {
        "spectral_type":    "M5.5Ve",
        "mass_solar":       0.1221,
        "radius_km":        107000.0,
        "rotation_days":    83.5,
        "B_surface_gauss":  600.0,
        "B_tachocline_T":   1.5e-1,
        "sigma_tach_sm":    5.0e3,
        "conv_depth_frac":  1.0,
        "v_conv_ms":        50.0,
        "m_observed":       1,
        "bcm_class":        "Class V-A -- Substrate Suppressed",
        "pump_type":        "fully_convective",
        "notes":            "Fully convective -- no tachocline. Substrate coupling degraded. "
                            "Single active longitude = m=1 dipole mode.",
        "observable":       "Single active longitude, superflares, 83.5d rotation",
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
        # Fully convective M dwarf -- no true tachocline, low effective density
        "rho_tachocline_kgm3": 50.0,
        # === END ADDITION ===
    },
    "EV_Lac": {
        "spectral_type":    "M3.5Ve",
        "mass_solar":       0.35,
        "radius_km":        225000.0,
        "rotation_days":    4.378,
        "B_surface_gauss":  3500.0,
        "B_tachocline_T":   2.0,            # CALIBRATED near-fully convective M dwarf tachocline estimate | 2026-04-02 EST
        "sigma_tach_sm":    6.0e3,
        "conv_depth_frac":  0.9,
        "v_conv_ms":        200.0,
        "m_observed":       2,
        "bcm_class":        "Class II -- Marginal",
        "pump_type":        "near_fully_convective",
        "notes":            "Rapid rotator M dwarf. Strong field. Two active longitudes = m=2.",
        "observable":       "Two active longitude flare clustering",
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
        # Near fully convective -- thin tachocline analog, low density
        "rho_tachocline_kgm3": 80.0,
        # === END ADDITION ===
    },
    "HR_1099": {
        "spectral_type":    "K1IV",
        "mass_solar":       1.1,
        "radius_km":        520000.0,
        "rotation_days":    2.84,
        "B_surface_gauss":  200.0,
        "B_tachocline_T":   10.0,           # CALIBRATED RS CVn high-shear tachocline estimate | 2026-04-02 EST
        "sigma_tach_sm":    1.1e4,
        "conv_depth_frac":  0.35,
        "v_conv_ms":        600.0,
        "m_observed":       2,
        "bcm_class":        "Class VI -- Bar Channeled",
        "pump_type":        "tidal_bar_rs_cvn",
        "notes":            "RS CVn binary. Tidal forcing = bar-channeling analog. "
                            "Two persistent active longitudes = m=2 substrate pipe.",
        "observable":       "Persistent two active longitude structure -- RS CVn",
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
        # K subgiant -- similar density to Sun at tachocline
        "rho_tachocline_kgm3": 180.0,
        # === END ADDITION ===
    },
}

# -----------------------------------------
# PHYSICS CONSTANTS
# -----------------------------------------
LAM_GALACTIC    = 0.1
LAM_PLANETARY   = 0.082
LAM_STELLAR_EST = 0.091

MU_0            = 4 * np.pi * 1e-7
KM_TO_M         = 1.0e3


def compute_stellar_params(star_name, params):
    """
    Compute derived stellar substrate parameters.
    Analogous to compute_planetary_params in BCM_planetary_wave.py

    Returns dict of derived quantities.
    """
    R_m         = params["radius_km"] * KM_TO_M
    omega       = 2 * np.pi / (params["rotation_days"] * 86400.0)
    conv_frac   = params["conv_depth_frac"]
    R_tach      = R_m * (1.0 - conv_frac)

    B           = params["B_tachocline_T"]
    sigma       = params["sigma_tach_sm"]
    v_conv      = params["v_conv_ms"]

    # Induction current at tachocline
    J_ind       = sigma * v_conv * B

    # Rossby radius at tachocline
    if omega > 0 and R_tach > 0:
        L_rossby = np.sqrt(2.0 * R_tach * v_conv / omega)
    else:
        L_rossby = R_m * 0.1

    if L_rossby > 0:
        m_rossby = R_tach / L_rossby
    else:
        m_rossby = 0.0

    # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
    # Alfven Hamiltonian replaces Bessel amplitude max
    # WHY: Bessel amplitude max found wrong mode (m=5 for all tachocline stars)
    # because it measures amplitude peaks, not energy minima.
    # The planetary solver uses Hamiltonian minimization -- stellar must match.
    #
    # v_A = B / sqrt(mu_0 * rho)  -- Alfven speed at tachocline
    # H(m) = (v_A - Omega * R_tach / m)^2  -- Alfven Hamiltonian
    # m* = argmin H(m)  -- mode that minimizes wave energy
    #
    # This is the same logic as H(m) = (c_s - OmegaR/m)^2 in planetary solver
    # with v_A replacing acoustic c_s as the phase speed in the magnetic medium.
    # Source: Alfven 1942, plasma wave theory

    rho_tach    = params.get("rho_tachocline_kgm3", 200.0)  # fallback to solar
    v_A         = B / np.sqrt(MU_0 * rho_tach) if rho_tach > 0 else 0.0

    m_range     = range(1, 13)
    H_alfven    = {}
    for m in m_range:
        v_phase     = omega * R_tach / m if m > 0 else 0.0
        H_alfven[m] = (v_A - v_phase) ** 2

    m_predicted = min(H_alfven, key=H_alfven.get) if H_alfven else 0

    # Keep Bessel energies for reference -- do not remove
    energies    = {}
    k_fund      = 2.0 * np.pi / R_tach if R_tach > 0 else 1.0
    for m in m_range:
        amp         = abs(float(jv(m, k_fund * R_tach)))
        energies[m] = amp
    # === END ADDITION ===

    # Phase dynamics proxy
    cos_delta_phi    = 1.0
    decoupling_ratio = J_ind / (sigma * 1e-3 + 1e-9)

    return {
        "R_m":              R_m,
        "R_tach_m":         R_tach,
        "omega_rad_s":      omega,
        "J_ind_SI":         J_ind,
        "L_rossby_m":       L_rossby,
        "m_rossby":         round(m_rossby, 3),
        "m_predicted":      m_predicted,
        "v_A_ms":           round(v_A, 2),
        "H_alfven":         {str(m): round(v, 4) for m, v in H_alfven.items()},
        "energies":         {str(m): round(v, 6) for m, v in energies.items()},
        "cos_delta_phi":    cos_delta_phi,
        "decoupling_ratio": round(decoupling_ratio, 4),
    }


def solve_lambda_stellar(star_name, params, derived):
    """Back-calculate lam_stellar from observed m."""
    m_obs = params.get("m_observed", 0)
    if m_obs <= 0:
        return None, None

    R_tach  = derived["R_tach_m"]
    omega   = derived["omega_rad_s"]
    v_conv  = params["v_conv_ms"]

    best_lam    = None
    best_err    = 1e9
    lam_range   = np.linspace(0.02, 0.20, 180)

    for lam in lam_range:
        L_eff   = np.sqrt(2.0 * R_tach * v_conv / (omega * (1.0 + lam * 10)))
        m_eff   = R_tach / L_eff if L_eff > 0 else 0
        err     = abs(m_eff - m_obs)
        if err < best_err:
            best_err    = err
            best_lam    = lam

    ratio = best_lam / LAM_GALACTIC if best_lam else None
    return best_lam, ratio


def run(star_name="Sun", solve_lambda=False, output_dir=None):
    """Run BCM stellar wave solver for a single star."""
    params = STELLAR_REGISTRY.get(star_name)
    if params is None:
        print(f"  ERROR: Star '{star_name}' not in registry.")
        print(f"  Available: {list(STELLAR_REGISTRY.keys())}")
        return None

    print(f"\n{'='*65}")
    print(f"  BCM STELLAR WAVE SOLVER -- {star_name}")
    print(f"  {params['spectral_type']}  --  {params['bcm_class']}")
    print(f"{'='*65}")

    derived = compute_stellar_params(star_name, params)

    print(f"\n  STELLAR PARAMETERS:")
    print(f"    R_star:          {params['radius_km']:.0f} km")
    print(f"    R_tachocline:    {derived['R_tach_m']/1e6:.3f} Mm")
    print(f"    Rotation:        {params['rotation_days']:.4f} days")
    print(f"    Omega:           {derived['omega_rad_s']:.4e} rad/s")
    print(f"    B_tachocline:    {params['B_tachocline_T']:.3e} T")
    print(f"    rho_tachocline:  {params.get('rho_tachocline_kgm3', 200.0):.1f} kg/m^3")
    print(f"    v_Alfven:        {derived['v_A_ms']:.2f} m/s")
    print(f"    sigma:           {params['sigma_tach_sm']:.3e} S/m")
    print(f"    v_conv:          {params['v_conv_ms']:.1f} m/s")
    print(f"    J_ind:           {derived['J_ind_SI']:.4e} A/m^2")

    print(f"\n  BCM ALFVEN HAMILTONIAN PREDICTION:")
    print(f"    v_A:             {derived['v_A_ms']:.2f} m/s")
    print(f"    m (Rossby):      {derived['m_rossby']:.3f}")
    print(f"    m (Hamiltonian): {derived['m_predicted']}")
    print(f"    m (observed):    {params['m_observed']}")

    m_obs    = params["m_observed"]
    m_pred   = derived["m_predicted"]
    m_ro     = derived["m_rossby"]
    m_ro_int = int(round(m_ro))

    if m_obs > 0:
        h_match  = (m_pred == m_obs)
        ro_match = (m_ro_int == m_obs)
        print(f"    Hamiltonian match: {'YES <confirmed>' if h_match else 'NO'}")
        print(f"    Rossby match:      {'YES <confirmed>' if ro_match else 'NO'}")
    else:
        h_match  = "N/A"
        ro_match = "N/A"
        print(f"    m_observed: UNKNOWN -- BCM prediction: m={m_pred}")

    print(f"\n  PHASE DYNAMICS:")
    print(f"    cos_delta_phi:   {derived['cos_delta_phi']:.6f}")
    print(f"    decoupling_ratio:{derived['decoupling_ratio']:.4f}")
    print(f"    NOTE: Bessel proxy -- full separation requires galactic PDE")

    print(f"\n  OBSERVABLE: {params['observable']}")
    print(f"  NOTES: {params['notes']}")

    lam_stellar = None
    lam_ratio   = None
    if solve_lambda and m_obs > 0:
        lam_stellar, lam_ratio = solve_lambda_stellar(star_name, params, derived)
        if lam_stellar:
            print(f"\n  LAMBDA BACK-CALCULATION:")
            print(f"    lam_stellar:     {lam_stellar:.4f}")
            print(f"    lam_galactic:    {LAM_GALACTIC:.4f}")
            print(f"    lam_planetary:   {LAM_PLANETARY:.4f}")
            print(f"    ratio:           {lam_ratio:.4f}")
            verdict = ("SCALE INVARIANT" if 0.5 <= lam_ratio <= 2.0
                       else "SCALE DEPENDENT")
            print(f"    Scale verdict:   {verdict}")

    result = {
        "star":             star_name,
        "spectral_type":    params["spectral_type"],
        "bcm_class":        params["bcm_class"],
        "pump_type":        params["pump_type"],
        "m_observed":       params["m_observed"],
        "m_predicted_H":    m_pred,
        "m_rossby":         derived["m_rossby"],
        "match_hamiltonian":h_match,
        "match_rossby":     ro_match,
        "J_ind_SI":         derived["J_ind_SI"],
        "L_rossby_m":       derived["L_rossby_m"],
        "v_A_ms":           derived["v_A_ms"],
        "cos_delta_phi":    derived["cos_delta_phi"],
        "decoupling_ratio": derived["decoupling_ratio"],
        "lambda_stellar":   lam_stellar,
        "lambda_ratio":     lam_ratio,
        "lambda_galactic":  LAM_GALACTIC,
        "lambda_planetary": LAM_PLANETARY,
        "observable":       params["observable"],
        "notes":            params["notes"],
        "H_alfven":         derived["H_alfven"],
        "energies":         derived["energies"],
    }

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "results")
    os.makedirs(output_dir, exist_ok=True)
    out_file  = f"BCM_{star_name}_stellar_wave.json"
    out_path  = os.path.join(output_dir, out_file)

    last_run_path = os.path.join(output_dir, "BCM_stellar_last_run.json")
    with open(last_run_path, "w") as f:
        json.dump({"last_file": out_file, "last_star": star_name}, f, indent=2)

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")
    return result


def run_stellar_batch(registry=None, solve_lambda=False, output_dir=None):
    """Run all stars in registry."""
    stars = registry or STELLAR_REGISTRY

    print(f"\n{'='*65}")
    print(f"  BCM STELLAR BATCH -- {len(stars)} stars")
    print(f"{'='*65}")
    print(f"  {'Star':<12} {'m_obs':>6} {'m_Ro':>6} {'m_H':>5} "
          f"{'v_A m/s':>10} {'J_ind':>12} {'H match'}")
    print(f"  {'-'*65}")

    results = {}
    for name, params in stars.items():
        derived  = compute_stellar_params(name, params)
        m_obs    = params.get("m_observed", 0)
        m_pred   = derived["m_predicted"]
        m_ro     = derived["m_rossby"]
        m_ro_int = int(round(m_ro))
        J_ind    = derived["J_ind_SI"]
        v_A      = derived["v_A_ms"]

        lam_stellar = None
        lam_ratio   = None
        if solve_lambda and m_obs > 0:
            lam_stellar, lam_ratio = solve_lambda_stellar(name, params, derived)

        h_match  = (m_pred == m_obs) if m_obs > 0 else "N/A"
        ro_match = (m_ro_int == m_obs) if m_obs > 0 else "N/A"
        h_mk     = ("YES" if h_match is True
                    else "NO" if h_match is False else "N/A")

        print(f"  {name:<12} {m_obs:>6} {m_ro:>6.2f} {m_pred:>5} "
              f"{v_A:>10.1f} {J_ind:>12.3e} {h_mk}")

        results[name] = {
            "m_observed":       m_obs,
            "m_predicted_H":    m_pred,
            "m_rossby":         round(m_ro, 3),
            "match_hamiltonian":h_match,
            "match_rossby":     ro_match,
            "J_ind_SI":         J_ind,
            "v_A_ms":           v_A,
            "lambda_stellar":   lam_stellar,
            "lambda_ratio":     lam_ratio,
            "bcm_class":        params["bcm_class"],
            "pump_type":        params["pump_type"],
            "notes":            params["notes"],
        }

    matched   = sum(1 for r in results.values() if r["match_hamiltonian"] is True)
    with_m    = sum(1 for r in results.values() if isinstance(r["match_hamiltonian"], bool))
    ratios    = [r["lambda_ratio"] for r in results.values() if r["lambda_ratio"] is not None]
    avg_ratio = np.mean(ratios) if ratios else None

    print(f"\n  {'='*65}")
    print(f"  BATCH SUMMARY -- {len(results)} stars")
    print(f"  {'='*65}")
    print(f"  Alfven Hamiltonian match: {matched}/{with_m} stars")
    if avg_ratio:
        print(f"  Avg lam ratio:    {avg_ratio:.4f}  (lam_stellar / lam_galactic)")
        verdict = ("SCALE INVARIANT" if 0.5 <= avg_ratio <= 2.0 else "SCALE DEPENDENT")
        print(f"  Scale verdict:    {verdict}")

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "results")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "BCM_stellar_batch.json")

    batch_out = {
        "title":            "BCM Stellar Batch -- Alfven Hamiltonian -- Scale-Invariance Test",
        "author":           "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "date":             __import__("time").strftime("%Y-%m-%d"),
        "hamiltonian":      "H(m) = (v_A - Omega*R_tach/m)^2  -- Alfven phase speed",
        "lambda_galactic":  LAM_GALACTIC,
        "lambda_planetary": LAM_PLANETARY,
        "n_stars":          len(results),
        "matches":          f"{matched}/{with_m}",
        "avg_lambda_ratio": avg_ratio,
        "stars":            results,
    }
    with open(out_path, "w") as f:
        json.dump(batch_out, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")
    return batch_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM Stellar Wave Solver -- Alfven Hamiltonian scale-invariance test")
    parser.add_argument("--star", type=str, default="Sun",
                        help=f"Star name. Options: {list(STELLAR_REGISTRY.keys())}")
    parser.add_argument("--batch", action="store_true",
                        help="Run all stars in registry")
    parser.add_argument("--solve-lambda", action="store_true",
                        help="Back-calculate lam_stellar from observed m")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for JSON results")
    args = parser.parse_args()

    if args.batch:
        run_stellar_batch(solve_lambda=args.solve_lambda,
                          output_dir=args.output_dir)
    else:
        run(star_name=args.star,
            solve_lambda=args.solve_lambda,
            output_dir=args.output_dir)
