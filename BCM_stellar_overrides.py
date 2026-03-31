# -*- coding: utf-8 -*-
"""
BCM Stellar Overrides — Stellar Test Case Runner
=================================================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
NSF I-Corps — Team GIBUSH

# === BCM MASTER BUILD ADDITION v2.2 | 2026-03-31 EST ===

Stellar-scale test cases for BCM wave equation scale-invariance.
Analogous to BCM_Substrate_overrides.py for galaxies.

Each star maps to a BCM galactic class analog:
    Class I   — Clean tachocline coupling (Sun, Alpha Cen A, Epsilon Eri, AB Dor)
    Class II  — Marginal / boundary (EV Lac)
    Class III — Ground state / quiescent (Tau Ceti)
    Class IV  — No substrate coupling (Vega — A-type, no convection zone)
    Class V-A — Substrate suppressed (Proxima, V374 Peg, TRAPPIST-1)
    Class VI  — Tidal bar channeling (HR 1099)
    Class ?   — Anomalous (Tabby, Betelgeuse)

Usage:
    python BCM_stellar_overrides.py              # run all 13 stars
    python BCM_stellar_overrides.py --vanguard   # run vanguard tier only
    python BCM_stellar_overrides.py --mystery    # run mystery tier only
    python BCM_stellar_overrides.py --solve-lambda

# === END ADDITION ===
"""

import numpy as np
import json
import os
import sys
import argparse
import time

# Import the stellar wave solver
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from BCM_stellar_wave import (
    compute_stellar_params,
    solve_lambda_stellar,
    STELLAR_REGISTRY as BASE_REGISTRY,
    LAM_GALACTIC,
    LAM_PLANETARY,
)

# ─────────────────────────────────────────
# EXTENDED STELLAR REGISTRY — 7 NEW STARS
# All parameters from peer-reviewed sources
# Where direct measurement unavailable:
#   - Solar-scaled estimates flagged [estimated]
#   - Estimation method documented in notes
# ─────────────────────────────────────────

EXTENDED_REGISTRY = {

    # ══════════════════════════════════════
    # VANGUARD TIER — BCM should nail these
    # ══════════════════════════════════════

    "Alpha_Cen_A": {
        "spectral_type":    "G2V",
        "mass_solar":       1.079,
        "radius_km":        854000.0,       # 1.2234 R_sun — Boyajian VLTI 2017
        "rotation_days":    22.0,           # Constellation Guide / spectroscopic
        "B_surface_gauss":  2.0,            # [estimated] Sun-like, similar activity level
        "B_tachocline_T":   1.2e-1,         # [estimated] scaled from Sun (10% more massive)
        "sigma_tach_sm":    1.1e4,          # [estimated] solar-scaled
        "conv_depth_frac":  0.27,           # asteroseismic ~6% below photosphere → ~27% of R
        "v_conv_ms":        320.0,          # [estimated] solar-scaled, slightly higher mass
        "m_observed":       4,              # [predicted] Sun twin — expect m=4 solar analog
        "bcm_class":        "Class I -- Stable Coupled (Sun Twin)",
        "pump_type":        "tachocline_dynamo",
        "notes":            "Sun twin at 1.34 pc. Nearly identical spectral type, similar "
                            "rotation. BCM prediction: m=4 reproducing solar 4-sector pattern. "
                            "If confirmed, this is reproducibility — not one data point.",
        "observable":       "Solar-like activity cycle. Coronal variability from starspots.",
        "tier":             "vanguard",
        "citations": {
            "radius":       "Boyajian et al. 2017, A&A -- VLTI/PIONIER interferometry",
            "mass":         "Star Facts / NASA SVS -- spectroscopic binary orbit",
            "rotation":     "Constellation Guide -- spectroscopic v*sin(i)",
        },
    },

    "Tau_Ceti": {
        "spectral_type":    "G8.5V",
        "mass_solar":       0.78,
        "radius_km":        551000.0,       # 0.793 R_sun
        "rotation_days":    34.0,           # slow rotator, nearly pole-on
        "B_surface_gauss":  0.17,           # ZDI mean surface-averaged — ESPaDOnS/CFHT
        "B_tachocline_T":   3.0e-2,         # [estimated] very weak — scaled from surface
        "sigma_tach_sm":    8.0e3,          # [estimated] solar-scaled for K-dwarf
        "conv_depth_frac":  0.33,           # [estimated] deeper than Sun for later type
        "v_conv_ms":        150.0,          # [estimated] slow rotator, moderate convection
        "m_observed":       0,              # ZDI: 92% dipolar, 88% axisymmetric — m=0 dominant
        "bcm_class":        "Class III -- Ground State (Quiescent)",
        "pump_type":        "tachocline_quiescent",
        "notes":            "Extremely quiet star. ZDI shows 92% dipolar, 88% axisymmetric "
                            "field — no active longitude structure. BCM prediction: substrate "
                            "in ground state. m=0 axisymmetric = no azimuthal standing wave. "
                            "Stellar equivalent of Class III galaxy — frozen substrate.",
        "observable":       "No active longitudes. Minimal chromospheric activity. Pole-on.",
        "tier":             "vanguard",
        "citations": {
            "B_field":      "ESPaDOnS/CFHT spectropolarimetry -- ZDI reconstruction",
            "rotation":     "Multiple studies -- 31-34 day range, pole-on complicates",
            "radius_mass":  "Teixeira et al. -- spectroscopic parameters",
        },
    },

    "AB_Dor": {
        "spectral_type":    "K0V",
        "mass_solar":       0.86,
        "radius_km":        670000.0,       # 0.96 R_sun — VLTI/AMBER
        "rotation_days":    0.514,          # ultra-fast rotator — Donati et al.
        "B_surface_gauss":  1000.0,         # ~1 kG at poles — Donati 1999
        "B_tachocline_T":   5.0e-1,         # [estimated] strong field, rapid rotator
        "sigma_tach_sm":    1.0e4,          # [estimated] solar-scaled
        "conv_depth_frac":  0.40,           # ~40% of radius — dynamo modeling
        "v_conv_ms":        800.0,          # [estimated] rapid rotation enhances convection
        "m_observed":       2,              # ZDI: two open-field regions ~180deg apart
        "bcm_class":        "Class I -- Extreme Coupled (Rapid Rotator)",
        "pump_type":        "tachocline_dynamo_rapid",
        "notes":            "Ultra-fast rotator (0.514 day). v*sin(i)=90 km/s. ZDI shows "
                            "12 alternating polarity regions, two dominant open-field zones "
                            "180deg apart = m=2. BCM test: does rapid rotation push to "
                            "higher m? If m_predicted > m_observed, rotation-rate dependence "
                            "is confirmed across scales.",
        "observable":       "12 polarity regions. Two dominant active longitudes. Polar spot.",
        "tier":             "vanguard",
        "citations": {
            "B_field":      "Donati et al. 1999, MNRAS 302:437 -- ZDI potential field",
            "rotation":     "Donati et al. -- secular variation 1988-1996",
            "radius":       "VLTI/AMBER interferometry",
            "mass":         "Andrae et al. 2017, A&A 607 -- dynamical mass",
            "topology":     "Johns-Krull et al. 2002, ApJ 575:1078 -- coronal topology",
        },
    },

    "V374_Peg": {
        "spectral_type":    "M4Ve",
        "mass_solar":       0.338,
        "radius_km":        233000.0,       # 0.335 R_sun — Mann et al. 2015 calibration
        "rotation_days":    0.44,           # rapid, rigid-body rotation — Vida 2016
        "B_surface_gauss":  5460.0,         # unsigned total — Bellotti 2025
        "B_tachocline_T":   2.0e-1,         # [estimated] no tachocline — surface-scaled
        "sigma_tach_sm":    5.0e3,          # [estimated] M dwarf fully convective
        "conv_depth_frac":  1.0,            # fully convective — no tachocline
        "v_conv_ms":        100.0,          # [estimated] rapid rotator but low mass
        "m_observed":       1,              # ZDI: dipolar axisymmetric l=1, m=0 → m=1 BCM
        "bcm_class":        "Class V-A -- Substrate Suppressed (Fully Convective)",
        "pump_type":        "fully_convective",
        "notes":            "Fully convective M4 dwarf near the 0.35 Msun boundary. "
                            "Despite 5.46 kG total field (strongest in registry), ZDI shows "
                            "purely dipolar axisymmetric topology. BCM prediction: no "
                            "tachocline = m=1 ceiling regardless of field strength. "
                            "If confirmed with Proxima, tachocline is the coupling gate.",
        "observable":       "Dipolar axisymmetric field. Rigid-body rotation. High flare rate.",
        "tier":             "vanguard",
        "citations": {
            "B_field":      "Bellotti et al. 2025, A&A 704:A298 -- unsigned 5.46 kG",
            "mass_radius":  "Vida et al. 2016, A&A 590:A11 -- Mann et al. calibrations",
            "rotation":     "Vida et al. 2016 -- rigid-body, negligible differential",
            "topology":     "Donati et al. 2006 -- stable dipolar field",
            "stability":    "Morin et al. 2008 -- field stability confirmation",
        },
    },

    # ══════════════════════════════════════
    # MYSTERY TIER — unexplained phenomena
    # ══════════════════════════════════════

    "Betelgeuse": {
        "spectral_type":    "M2Iab",
        "mass_solar":       17.0,
        "radius_km":        531500000.0,    # ~764 R_sun — 2020 measurement
        "rotation_days":    13140.0,        # ~36 years — ALMA 2018
        "B_surface_gauss":  1.0,            # NARVAL spectropolarimetry — Auriere 2010
        "B_tachocline_T":   5.0e-3,         # [estimated] weak — supergiant, no classical tachocline
        "sigma_tach_sm":    2.0e3,          # [estimated] partially ionized extended envelope
        "conv_depth_frac":  0.50,           # convective envelope ~50% of radius
        "v_conv_ms":        50000.0,        # 40-60 km/s — CO5BOLD 3D simulations
        "m_observed":       3,              # 2-4 giant convective cells — interferometry
        "bcm_class":        "Class ? -- Anomalous (Dying Supergiant)",
        "pump_type":        "supergiant_convective",
        "notes":            "Red supergiant. Transition from wave-dominated to convection-dominated "
                            "substrate regime: m=3 from giant convective cells (>60% stellar radius "
                            "each) confirmed by Hamiltonian H(m)=(c_s-Omega*R/m)^2 minimum. Great "
                            "Dimming 2019-2020: surface mass ejection from one of three azimuthal "
                            "nodes — substrate mode event, not random instability. Cell lifetime "
                            "~4 years = substrate relaxation time at supergiant scale.",
        "observable":       "Great Dimming 2019-2020. 2-4 giant convective cells. 36-year rotation.",
        "tier":             "mystery",
        "citations": {
            "B_field":      "Auriere et al. 2010, A&A 516:L2 -- NARVAL first detection",
            "rotation":     "ALMA 2018, A&A -- 36 +/- 8 years",
            "convection":   "CO5BOLD 3D simulations -- 40-60 km/s rising plasma",
            "cells":        "Lagrange et al. 2018, A&A -- spectropolarimetric imaging",
            "dimming":      "Dupree et al. 2022, ApJ 936:18 -- surface mass ejection",
        },
    },

    "TRAPPIST_1": {
        "spectral_type":    "M8V",
        "mass_solar":       0.089,
        "radius_km":        84000.0,        # 0.121 R_sun — van Grootel 2018
        "rotation_days":    3.295,          # Kepler K2 — Davenport 2017
        "B_surface_gauss":  600.0,          # Reiners & Basri 2010
        "B_tachocline_T":   5.0e-2,         # [estimated] no tachocline — surface-scaled
        "sigma_tach_sm":    3.0e3,          # [estimated] ultracool dwarf, low ionization
        "conv_depth_frac":  1.0,            # fully convective
        "v_conv_ms":        20.0,           # [estimated] very low mass, moderate rotation
        "m_observed":       1,              # [predicted] fully convective → dipole expected
        "bcm_class":        "Class V-A -- Substrate Suppressed (Ultracool)",
        "pump_type":        "fully_convective_tidal",
        "notes":            "Ultracool dwarf with 7 planets in resonant chain. Fully convective. "
                            "BCM test: does planetary tidal forcing break the m=1 ceiling? "
                            "If m_predicted=1 despite 7 close-in planets: tachocline is the "
                            "gate, tidal forcing cannot substitute. If m_predicted>1: "
                            "planetary tidal forcing acts as Class VI analog. "
                            "Either answer is a finding. No radio emission detected — "
                            "substrate may be below threshold.",
        "observable":       "7 resonant planets. No radio emission. ~25% spot coverage (JWST).",
        "tier":             "mystery",
        "citations": {
            "mass_radius":  "van Grootel et al. 2018, ApJ 853:30",
            "rotation":     "Davenport et al. 2017 -- Kepler K2",
            "B_field":      "Reiners & Basri 2010",
            "planets":      "Gillon et al. 2017, Nature 542:456",
            "no_radio":     "Pineda et al. 2018, ApJ 866:155 -- upper limit <8.1 uJy",
        },
    },

    "Vega": {
        "spectral_type":    "A0V",
        "mass_solar":       2.135,
        "radius_km":        1643000.0,      # polar radius 2.362 R_sun — CHARA
        "rotation_days":    0.52,           # ~12.5 hours — 236 km/s equatorial, pole-on
        "B_surface_gauss":  0.6,            # -0.6 +/- 0.3 G — Lignieres 2009 NARVAL
        "B_tachocline_T":   1.0e-3,         # [estimated] essentially no tachocline region
        "sigma_tach_sm":    1.0e3,          # [estimated] minimal — thin ionization layers
        "conv_depth_frac":  0.02,           # [estimated] A-type: H/He ionization layers only
        "v_conv_ms":        2000.0,         # microturbulence ~2 km/s — spectroscopic
        "m_observed":       0,              # no active longitudes — no substrate coupling
        "bcm_class":        "Class IV -- No Substrate Coupling (A-type)",
        "pump_type":        "radiative_no_tachocline",
        "notes":            "A0V rapid rotator viewed pole-on (i~5-7deg). 88% breakup velocity. "
                            "Essentially no convection zone — H/He ionization layers only. "
                            "BCM prediction: m=0, no substrate coupling. Stellar equivalent "
                            "of NGC0801 Class IV — baryonic mass present, substrate absent. "
                            "Debris disk confirmed (prototype Vega-like star). "
                            "If solver returns m=0 or very low mode: A-type stars are "
                            "substrate-dark. Their rotation is purely Keplerian.",
        "observable":       "Debris disk. Pole-on rapid rotator. Weak field 0.6 G.",
        "tier":             "mystery",
        "citations": {
            "B_field":      "Lignieres et al. 2009, A&A -- NARVAL first A-type detection",
            "radius":       "CHARA array interferometry -- oblate from rotation",
            "mass":         "Universe Guide / astronomical reference catalogs",
            "disk":         "IRAS 1983 discovery; JWST 2024 smooth structure",
        },
    },
}


# ─────────────────────────────────────────
# COMBINED REGISTRY
# Merges base (6) + extended (7) = 13 stars
# ─────────────────────────────────────────

def get_full_registry():
    """Return merged registry of all 13 stars."""
    full = {}
    # Base registry stars (from BCM_stellar_wave.py)
    for name, params in BASE_REGISTRY.items():
        entry = dict(params)
        # Tag base stars with tier
        if name in ("Sun", "Epsilon_Eri"):
            entry["tier"] = "vanguard"
        elif name == "Tabby":
            entry["tier"] = "mystery"
        elif name in ("Proxima", "EV_Lac", "HR_1099"):
            entry["tier"] = "vanguard"
        full[name] = entry
    # Extended registry
    full.update(EXTENDED_REGISTRY)
    return full


# ─────────────────────────────────────────
# STELLAR CLASS MAP
# Maps BCM galactic classes to stellar analogs
# ─────────────────────────────────────────

STELLAR_CLASS_MAP = {
    "Class I":   ["Sun", "Alpha_Cen_A", "Epsilon_Eri", "AB_Dor"],
    "Class II":  ["EV_Lac"],
    "Class III": ["Tau_Ceti"],
    "Class IV":  ["Vega"],
    "Class V-A": ["Proxima", "V374_Peg", "TRAPPIST_1"],
    "Class VI":  ["HR_1099"],
    "Class ?":   ["Tabby", "Betelgeuse"],
}


def run_stellar_test(star_name, params, solve_lambda=False, output_dir=None):
    """
    Run BCM stellar wave solver on a single star and print results.
    Returns result dict.
    """
    print(f"\n{'='*65}")
    print(f"  BCM STELLAR TEST -- {star_name}")
    print(f"  {params.get('spectral_type','')}  --  {params.get('bcm_class','')}")
    tier = params.get("tier", "base")
    print(f"  Tier: {tier.upper()}")
    print(f"{'='*65}")

    derived = compute_stellar_params(star_name, params)

    m_obs   = params.get("m_observed", 0)
    m_pred  = derived["m_predicted"]
    m_ro    = derived["m_rossby"]
    m_ro_int = int(round(m_ro))

    print(f"\n  PARAMETERS:")
    print(f"    R_star:          {params['radius_km']:.0f} km")
    print(f"    R_tachocline:    {derived['R_tach_m']/1e6:.3f} Mm")
    print(f"    Rotation:        {params['rotation_days']:.4f} days")
    print(f"    omega:           {derived['omega_rad_s']:.4e} rad/s")
    print(f"    B_tachocline:    {params['B_tachocline_T']:.3e} T")
    print(f"    sigma:           {params['sigma_tach_sm']:.3e} S/m")
    print(f"    v_conv:          {params['v_conv_ms']:.1f} m/s")
    print(f"    J_ind:           {derived['J_ind_SI']:.4e} A/m2")

    print(f"\n  BCM WAVE PREDICTION:")
    print(f"    m (Rossby):      {m_ro:.3f}")
    print(f"    m (Hamiltonian): {m_pred}")
    print(f"    m (observed):    {m_obs}")

    if m_obs > 0:
        h_match  = (m_pred == m_obs)
        ro_match = (m_ro_int == m_obs)
        print(f"    Hamiltonian:     {'YES <confirmed>' if h_match else 'NO'}")
        print(f"    Rossby:          {'YES <confirmed>' if ro_match else 'NO'}")
    else:
        h_match  = "N/A"
        ro_match = "N/A"
        print(f"    m_observed: UNKNOWN -- BCM prediction: m={m_pred}")

    # Lambda back-calculation
    lam_stellar = None
    lam_ratio   = None
    if solve_lambda and m_obs > 0:
        lam_stellar, lam_ratio = solve_lambda_stellar(star_name, params, derived)
        if lam_stellar:
            print(f"\n  LAMBDA:")
            print(f"    lam_stellar:     {lam_stellar:.4f}")
            print(f"    ratio to gal:    {lam_ratio:.4f}")
            verdict = ("SCALE INVARIANT" if 0.5 <= lam_ratio <= 2.0
                       else "SCALE DEPENDENT")
            print(f"    Verdict:         {verdict}")

    print(f"\n  NOTES: {params.get('notes','')}")
    print(f"{'='*65}")

    result = {
        "star":             star_name,
        "spectral_type":    params.get("spectral_type", ""),
        "bcm_class":        params.get("bcm_class", ""),
        "pump_type":        params.get("pump_type", ""),
        "tier":             params.get("tier", "base"),
        "m_observed":       m_obs,
        "m_predicted_H":    m_pred,
        "m_rossby":         round(m_ro, 3),
        "match_hamiltonian": h_match,
        "match_rossby":     ro_match,
        "J_ind_SI":         derived["J_ind_SI"],
        "L_rossby_m":       derived["L_rossby_m"],
        "cos_delta_phi":    derived["cos_delta_phi"],
        "decoupling_ratio": derived["decoupling_ratio"],
        "lambda_stellar":   lam_stellar,
        "lambda_ratio":     lam_ratio,
        "observable":       params.get("observable", ""),
        "notes":            params.get("notes", ""),
    }

    # Save individual result
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "results")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"BCM_{star_name}_stellar_wave.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def run_full_stellar_batch(tier_filter=None, solve_lambda=False, output_dir=None):
    """
    Run all 13 stars. Optionally filter by tier.
    Produces combined arms summary.
    """
    registry = get_full_registry()

    if tier_filter:
        registry = {k: v for k, v in registry.items()
                     if v.get("tier", "base") == tier_filter}

    n = len(registry)
    label = tier_filter.upper() if tier_filter else "ALL STARS"

    print(f"\n{'#'*65}")
    print(f"  BCM STELLAR OVERRIDES -- {label} -- {n} stars")
    print(f"  Combined Arms: Galactic (175) + Planetary (8) + Stellar ({n})")
    print(f"{'#'*65}")
    print(f"\n  {'Star':<14} {'Type':<8} {'m_obs':>5} {'m_Ro':>6} {'m_H':>4} "
          f"{'J_ind':>12} {'Class':<30} {'Match'}")
    print(f"  {'─'*95}")

    results = {}
    for name, params in registry.items():
        derived = compute_stellar_params(name, params)
        m_obs   = params.get("m_observed", 0)
        m_pred  = derived["m_predicted"]
        m_ro    = derived["m_rossby"]
        m_ro_int = int(round(m_ro))
        J_ind   = derived["J_ind_SI"]

        h_match  = (m_pred == m_obs) if m_obs > 0 else "N/A"
        ro_match = (m_ro_int == m_obs) if m_obs > 0 else "N/A"

        lam_stellar = None
        lam_ratio   = None
        if solve_lambda and m_obs > 0:
            lam_stellar, lam_ratio = solve_lambda_stellar(name, params, derived)

        match_str = ("H+Ro" if h_match is True and ro_match is True
                     else "H" if h_match is True
                     else "Ro" if ro_match is True
                     else "N/A" if h_match == "N/A"
                     else "--")

        cls = params.get("bcm_class", "")[:30]
        print(f"  {name:<14} {params.get('spectral_type',''):<8} {m_obs:>5} "
              f"{m_ro:>6.2f} {m_pred:>4} {J_ind:>12.3e} {cls:<30} {match_str}")

        results[name] = {
            "spectral_type":    params.get("spectral_type", ""),
            "bcm_class":        params.get("bcm_class", ""),
            "tier":             params.get("tier", "base"),
            "m_observed":       m_obs,
            "m_predicted_H":    m_pred,
            "m_rossby":         round(m_ro, 3),
            "match_hamiltonian": h_match,
            "match_rossby":     ro_match,
            "J_ind_SI":         J_ind,
            "lambda_stellar":   lam_stellar,
            "lambda_ratio":     lam_ratio,
        }

    # ── Summary ──
    matched_h  = sum(1 for r in results.values() if r["match_hamiltonian"] is True)
    matched_ro = sum(1 for r in results.values() if r["match_rossby"] is True)
    with_m     = sum(1 for r in results.values()
                     if isinstance(r["match_hamiltonian"], bool))
    ratios     = [r["lambda_ratio"] for r in results.values()
                  if r["lambda_ratio"] is not None]
    avg_ratio  = float(np.mean(ratios)) if ratios else None

    print(f"\n  {'='*65}")
    print(f"  COMBINED ARMS SUMMARY -- {n} stars")
    print(f"  {'='*65}")
    print(f"  Hamiltonian match: {matched_h}/{with_m}")
    print(f"  Rossby match:      {matched_ro}/{with_m}")
    if avg_ratio:
        print(f"  Avg lam ratio:     {avg_ratio:.4f}")
        verdict = ("SCALE INVARIANT" if 0.5 <= avg_ratio <= 2.0
                    else "SCALE DEPENDENT")
        print(f"  Scale verdict:     {verdict}")

    # ── Class Coverage ──
    print(f"\n  CLASS COVERAGE:")
    for cls, stars in STELLAR_CLASS_MAP.items():
        present = [s for s in stars if s in results]
        print(f"    {cls:<12} {len(present)}/{len(stars)} "
              f"  [{', '.join(present)}]")

    # ── Save ──
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "results")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "BCM_stellar_overrides_batch.json")

    batch = {
        "title":            "BCM Stellar Overrides -- Combined Arms Test",
        "author":           "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "date":             time.strftime("%Y-%m-%d"),
        "tier_filter":      tier_filter,
        "n_stars":          n,
        "hamiltonian_match": f"{matched_h}/{with_m}",
        "rossby_match":     f"{matched_ro}/{with_m}",
        "avg_lambda_ratio": avg_ratio,
        "lambda_galactic":  LAM_GALACTIC,
        "lambda_planetary": LAM_PLANETARY,
        "stars":            results,
        "class_map":        {k: v for k, v in STELLAR_CLASS_MAP.items()},
    }
    with open(out_path, "w") as f:
        json.dump(batch, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"{'#'*65}\n")
    return batch


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM Stellar Overrides -- 13-star combined arms test")
    parser.add_argument("--vanguard", action="store_true",
                        help="Run vanguard tier only")
    parser.add_argument("--mystery", action="store_true",
                        help="Run mystery tier only")
    parser.add_argument("--star", type=str, default=None,
                        help="Run single star by name")
    parser.add_argument("--solve-lambda", action="store_true",
                        help="Back-calculate lambda from observed m")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    if args.star:
        reg = get_full_registry()
        if args.star in reg:
            run_stellar_test(args.star, reg[args.star],
                             solve_lambda=args.solve_lambda,
                             output_dir=args.output_dir)
        else:
            print(f"Star '{args.star}' not found. Available: {list(reg.keys())}")
    elif args.vanguard:
        run_full_stellar_batch(tier_filter="vanguard",
                               solve_lambda=args.solve_lambda,
                               output_dir=args.output_dir)
    elif args.mystery:
        run_full_stellar_batch(tier_filter="mystery",
                               solve_lambda=args.solve_lambda,
                               output_dir=args.output_dir)
    else:
        run_full_stellar_batch(solve_lambda=args.solve_lambda,
                               output_dir=args.output_dir)
