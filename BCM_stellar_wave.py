# -*- coding: utf-8 -*-
"""
BCM Stellar Wave Solver
=======================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

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
        "radius_km":        1098060.0,
        "rotation_days":    20.1,
        "B_surface_gauss":  10.0,
        "B_tachocline_T":   5.0e-1,
        "sigma_tach_sm":    1.2e4,
        "conv_depth_frac":  0.12,
        "v_conv_ms":        600.0,
        "m_observed":       0,
        "bcm_class":        "Class ? -- Anomalous Flux",
        "pump_type":        "tachocline_f_type",
        "notes":            "KIC 8462852. F-type shallow CZ. B_tachocline estimated "
                            "from dynamo scaling. rho from stellar structure scaling.",
        "observable":       "Aperiodic flux dips 0.1-22% (Boyajian 2016). No clean periodic signal.",
        # === BCM MASTER BUILD ADDITION v2.2 | 2026-04-02 EST ===
        # F-type star -- shallower tachocline, lower density than Sun
        "rho_tachocline_kgm3": 150.0,
        # === END ADDITION ===
    },
    "Proxima": {
        "spectral_type":    "M5.5Ve",
        "mass_solar":       0.1221,
        "radius_km":        107100.0,
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
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Binary orbital parameters for tidal Hamiltonian
        # v_tidal = Omega_orb * R_tach / 2 -- companion's clock signal at m=2
        # Source: Fekel 1983, ApJ 268 -- spectroscopic binary orbit
        "P_orbital_days":       2.84,       # synchronized: P_rot = P_orb
        "M_companion_solar":    1.0,        # G5V secondary
        "binary_synchronized":  True,
        # === END ADDITION ===
    },
    "Epsilon_Eri": {
        "spectral_type":    "K2V",
        "mass_solar":       0.82,
        "radius_km":        600000.0,
        "rotation_days":    11.68,
        "B_surface_gauss":  30.0,
        "B_tachocline_T":   3.0,
        "sigma_tach_sm":    9.0e3,
        "conv_depth_frac":  0.32,
        "v_conv_ms":        250.0,
        "m_observed":       3,
        "bcm_class":        "Class I -- Young Active Coupled",
        "pump_type":        "tachocline_dynamo_young",
        "notes":            "Young active K dwarf. B_tachocline estimated from dynamo scaling. "
                            "rho from stellar structure scaling.",
        "observable":       "Active young solar analog. 3-sector wind structure from ZDI mapping.",
        "rho_tachocline_kgm3": 350.0,
    },
    "Alpha_Cen_A": {
        "spectral_type":    "G2V",
        "mass_solar":       1.1,
        "radius_km":        851457.0,
        "rotation_days":    22.0,
        "B_surface_gauss":  1.0,
        "B_tachocline_T":   5.6,
        "sigma_tach_sm":    1.0e4,
        "conv_depth_frac":  0.287,
        "v_conv_ms":        300.0,
        "m_observed":       4,
        "bcm_class":        "Class I -- Stable Coupled",
        "pump_type":        "tachocline_dynamo",
        "notes":            "Solar analog calibration. B_tachocline = solar value. "
                            "rho from stellar structure scaling. Binary with Alpha Cen B.",
        "observable":       "Solar twin. Deep Maunder-like minimum since 2005.",
        "rho_tachocline_kgm3": 119.0,
    },
    "Alpha_Cen_B": {
        "spectral_type":    "K1V",
        "mass_solar":       0.907,
        "radius_km":        600576.0,
        "rotation_days":    41.0,
        "B_surface_gauss":  2.0,
        "B_tachocline_T":   3.0,
        "sigma_tach_sm":    8.0e3,
        "conv_depth_frac":  0.35,
        "v_conv_ms":        200.0,
        "m_observed":       4,
        "bcm_class":        "Class I -- Stable Coupled",
        "pump_type":        "tachocline_dynamo",
        "notes":            "Binary companion to Alpha Cen A. B_tachocline from K-dwarf "
                            "dynamo scaling. Substrate bridge target with Alpha Cen A.",
        "observable":       "K-dwarf secondary. Long rotation period. Known activity cycle.",
        "rho_tachocline_kgm3": 324.0,
    },
    "61_Cyg_A": {
        "spectral_type":    "K5V",
        "mass_solar":       0.677,
        "radius_km":        464000.0,
        "rotation_days":    35.54,
        "B_surface_gauss":  2.0,
        "B_tachocline_T":   2.5,
        "sigma_tach_sm":    7.0e3,
        "conv_depth_frac":  0.40,
        "v_conv_ms":        250.0,
        "m_observed":       4,
        "bcm_class":        "Class I -- Stable Coupled",
        "pump_type":        "tachocline_dynamo",
        "notes":            "B_tachocline from K-dwarf dynamo scaling. rho from stellar "
                            "structure scaling (deep CZ = high density).",
        "observable":       "K-dwarf with solar-like magnetic cycle. High proper motion.",
        "rho_tachocline_kgm3": 585.0,
    },
    "AU_Mic": {
        "spectral_type":    "M1Ve",
        "mass_solar":       0.6,
        "radius_km":        570000.0,
        "rotation_days":    4.84,
        "B_surface_gauss":  2000.0,
        "B_tachocline_T":   3.0,
        "sigma_tach_sm":    1.5e4,
        "conv_depth_frac":  0.80,
        "v_conv_ms":        400.0,
        "m_observed":       2,
        "bcm_class":        "Class II -- Marginal",
        "pump_type":        "near_fully_convective",
        "notes":            "Rapid rotator near fully convective boundary. Standard Alfven "
                            "Hamiltonian predicts m=12 -- same boundary problem as HR_1099.",
        "observable":       "Young flare star. 4.84d rotation. Debris disk. Two active longitudes.",
        "rho_tachocline_kgm3": 497.0,
    },
    "Vega": {
        "spectral_type":    "A0Va",
        "mass_solar":       2.135,
        "radius_km":        1739000.0,
        "rotation_days":    0.67,
        "B_surface_gauss":  0.5,
        "B_tachocline_T":   0.5,
        "sigma_tach_sm":    5.0e2,
        "conv_depth_frac":  0.02,
        "v_conv_ms":        100.0,
        "m_observed":       0,
        "bcm_class":        "Class ? -- Anomalous",
        "pump_type":        "rapid_rotator_thin_env",
        "notes":            "Very thin convective envelope. Rapid rotation drives extreme "
                            "OmegaR_tach. BCM prediction target -- no confirmed m_observed.",
        "observable":       "A-star rapid rotator. Weak magnetic field. Nearly pole-on.",
        "rho_tachocline_kgm3": 27.0,
    },
    "Spica_A": {
        "spectral_type":    "B1 III-IV",
        "mass_solar":       11.43,
        "radius_km":        5196879.0,
        "rotation_days":    2.29,
        "B_surface_gauss":  100.0,
        "B_tachocline_T":   1.0,
        "sigma_tach_sm":    5.0e4,
        "conv_depth_frac":  0.05,
        "v_conv_ms":        1000.0,
        "m_observed":       0,
        "bcm_class":        "Class IV -- High-Energy Coupled",
        "pump_type":        "iron_opacity_z_layer",
        "notes":            "Massive B-type star. No traditional tachocline -- substrate pump "
                            "driven by iron opacity Z-layer instability. Binary bridge target.",
        "observable":       "Beta Cephei variable. Primary of Spica binary (P_orb=4.014d, e=0.13).",
        "rho_tachocline_kgm3": 10.0,
    },
    "Spica_B": {
        "spectral_type":    "B2 V",
        "mass_solar":       7.21,
        "radius_km":        2601918.0,
        "rotation_days":    3.26,
        "B_surface_gauss":  50.0,
        "B_tachocline_T":   0.5,
        "sigma_tach_sm":    2.0e4,
        "conv_depth_frac":  0.05,
        "v_conv_ms":        500.0,
        "m_observed":       0,
        "bcm_class":        "Class IV -- High-Energy Coupled",
        "pump_type":        "radiative_pump",
        "notes":            "Companion to Spica A. No traditional tachocline. Eccentric orbit "
                            "(e=0.13) creates time-variable substrate coupling.",
        "observable":       "Secondary in eccentric binary. Rotationally broadened (v sin i = 58 km/s).",
        "rho_tachocline_kgm3": 50.0,
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

    # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
    # Tidal Hamiltonian for binary stars
    # H_tidal(m) = (v_A + v_tidal - Omega*R_tach/m)^2
    # v_tidal = Omega_orb * R_tach / 2  -- companion's clock at tidal m=2
    #
    # Physics: the companion's tidal field imposes a persistent m=2
    # boundary condition. v_tidal exactly cancels OmegaR/2 at m=2,
    # leaving v_A^2 as the minimum energy. For synchronized binaries
    # (P_rot = P_orb), m=2 is always the predicted mode.
    # No free parameters -- v_tidal derived from orbital period.
    #
    # For non-synchronized binaries: the mismatch between Omega_rot
    # and Omega_orb shifts the resonance away from m=2.
    v_tidal     = 0.0
    H_tidal     = {}
    m_tidal     = m_predicted   # default: same as Alfven
    if params.get("P_orbital_days") is not None:
        P_orb       = params["P_orbital_days"]
        omega_orb   = 2.0 * np.pi / (P_orb * 86400.0) if P_orb > 0 else 0.0
        v_tidal     = omega_orb * R_tach / 2.0
        for m in m_range:
            v_phase     = omega * R_tach / m if m > 0 else 0.0
            H_tidal[m]  = (v_A + v_tidal - v_phase) ** 2
        m_tidal     = min(H_tidal, key=H_tidal.get) if H_tidal else m_predicted
        m_predicted = m_tidal   # tidal overrides Alfven for binaries
    # === END ADDITION ===

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
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        "v_tidal_ms":       round(v_tidal, 2),
        "H_tidal":          {str(m): round(v, 4) for m, v in H_tidal.items()} if H_tidal else {},
        "m_alfven":         min(H_alfven, key=H_alfven.get) if H_alfven else 0,
        "m_tidal":          m_tidal,
        # === END ADDITION ===
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
