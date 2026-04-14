# -*- coding: utf-8 -*-
"""
BCM v23 — Neutrino Flux Prediction Engine
============================================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
GIBUSH Systems

The substrate maintenance cost lambda=0.1 must have a
physical equivalent in detectable particle counts. This
script maps the BCM rotation curve fits to predicted
neutrino luminosities and IceCube/KM3NeT flux thresholds.

Derivation chain (Burdick):
  1. sigma(r) = (v_bcm^2 - v_newton^2) / kappa
     Back-calculated from grid=256 production run.
  2. E_sub = integral[ (1/2) * Sigma_baryon(r) * sigma(r)
                        * 2*pi*r dr ]
     Total gravitational energy maintained by substrate.
  3. L_nu = lambda * E_sub
     Maintenance luminosity: power required to refill
     what decays each timestep. This IS the neutrino pump.
  4. Phi_nu = L_nu / (4*pi*D^2 * E_nu)
     Flux at Earth in neutrinos per cm^2 per second.
  5. nu_b = L_nu / v_max^4
     Burdick Constant: ratio of maintenance luminosity to
     rotational velocity. Should be constant across Class I
     galaxies if the model is correct.

Usage:
    python BCM_v23_neutrino_flux.py
    python BCM_v23_neutrino_flux.py --chi2-json path/to/json

Output: JSON with L_nu, Phi_nu, nu_b, IceCube detectability
for each galaxy. Foreman runs, provides JSON.
"""

import numpy as np
import os
import sys
import json
import time
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════
# PHYSICAL CONSTANTS
# ═══════════════════════════════════════
G_CGS       = 6.674e-8      # cm^3 g^-1 s^-2
M_SUN_G     = 1.989e33      # grams
KPC_CM      = 3.0857e21     # cm per kpc
MPC_CM      = 3.0857e24     # cm per Mpc
KMS_CMS     = 1.0e5         # cm/s per km/s
C_CMS       = 2.998e10      # cm/s
ERG_PER_GEV = 1.602e-3      # erg per GeV
GEV_PER_ERG = 624.15        # GeV per erg

# IceCube sensitivity (point source, 10 yr)
# ~10^-12 GeV cm^-2 s^-1 at 1-100 TeV
# ~10^-11 GeV cm^-2 s^-1 at 1-10 GeV
ICECUBE_SENS_TEV = 1.0e-12  # GeV cm^-2 s^-1
ICECUBE_SENS_GEV = 1.0e-11  # GeV cm^-2 s^-1
KM3NET_SENS      = 5.0e-13  # GeV cm^-2 s^-1 (projected)

# Characteristic SMBH neutrino energy
# SMBH accretion disk temperatures → 1-100 GeV range
# Use 10 GeV as fiducial (conservative, detectable)
E_NU_GEV    = 10.0          # GeV per neutrino
E_NU_ERG    = E_NU_GEV * ERG_PER_GEV

# BCM frozen constants
LAMBDA      = 0.1
KAPPA       = 2.0

# Disk scale height (thin disk approximation)
# Typical late-type galaxy: h ~ 0.3 kpc
H_DISK_KPC  = 0.3


# ═══════════════════════════════════════
# SPARC GALAXY DISTANCES (Lelli+2016)
# ═══════════════════════════════════════
DISTANCES_MPC = {
    "DDO154":   3.7,  "DDO064":   6.8,  "UGC07577":  2.5,
    "UGC04305": 3.4,  "D564-8":   8.8,  "NGC2976":   3.6,
    "NGC0055":  2.0,  "IC2574":   4.0,  "NGC2366":   3.4,
    "NGC3741":  3.2,  "UGC06667": 19.8, "NGC7793":   3.9,
    "NGC6503":  5.3,  "NGC4559":  6.98, "NGC2403":   3.2,
    "NGC3198": 13.8,  "NGC3726":  14.3, "NGC6946":   6.8,
    "NGC4013": 18.6,  "UGC06614": 86.2, "NGC5055":  10.1,
    "NGC2903":  8.9,  "NGC3521":  10.7, "NGC3953":  17.0,
    "NGC5033": 18.7,  "NGC0891":  10.0, "NGC5907":  17.3,
    "NGC7331": 14.7,  "NGC2841":  14.1,
}

# SMBH masses (log10 M_sun) — catalog + estimated
# From Burdick_Crag_Mass.py BH catalog + M-sigma
BH_CATALOG_LOG = {
    "NGC0891":  7.60, "NGC2683":  7.72, "NGC2841":  8.11,
    "NGC3521":  7.70, "NGC3953":  7.90, "NGC3992":  8.10,
    "NGC5005":  8.20, "NGC5371":  8.30, "NGC5907":  7.80,
    "NGC5985":  8.00, "NGC6674":  8.20, "NGC7331":  7.86,
    "NGC7814":  8.60,
}


def estimate_mbh(vmax_kms):
    """M_BH from M-sigma relation (Tremaine+2002)."""
    sigma = max(vmax_kms / np.sqrt(2.0), 1.0)
    return 10.0 ** (8.13 + 4.02 * np.log10(sigma / 200.0))


def get_mbh(galaxy_name, vmax_kms):
    """Get M_BH from catalog or estimate."""
    if galaxy_name in BH_CATALOG_LOG:
        return 10.0 ** BH_CATALOG_LOG[galaxy_name], "catalog"
    return estimate_mbh(vmax_kms), "estimated"


# ═══════════════════════════════════════
# SUBSTRATE ENERGY CALCULATION
# ═══════════════════════════════════════

def compute_substrate_energy(r_kpc, v_bcm, v_newton, vmax):
    """
    Compute the total gravitational energy maintained by
    the substrate field.

    sigma(r) = (v_bcm^2 - v_newton^2) / kappa
    This is the substrate contribution to the gravitational
    potential at each radius.

    The energy required to maintain this potential against
    lambda decay is:

    E_sub = integral[ (1/2) * rho_eff(r) * sigma(r)
                       * 2*pi*r*h dr ]

    where rho_eff is derived from the baryonic surface
    density needed to sustain the rotation.

    For a self-consistent estimate, we use:
    E_sub = integral[ (1/2) * v_excess^2 * M_shell(r) ] dr

    where M_shell(r) = v_obs^2(r) * r / G is the total
    dynamical mass enclosed, and v_excess is the BCM
    contribution.

    Returns E_sub in ergs.
    """
    r_cm = np.array(r_kpc) * KPC_CM
    v_bcm_cm = np.array(v_bcm) * KMS_CMS
    v_new_cm = np.array(v_newton) * KMS_CMS
    v_obs_cm = np.array(v_bcm) * KMS_CMS  # v_bcm is our model

    n = len(r_kpc)
    if n < 3:
        return 0.0, np.zeros(n), np.zeros(n)

    # Substrate velocity excess at each radius
    v_excess_sq = v_bcm_cm ** 2 - v_new_cm ** 2
    v_excess_sq = np.maximum(v_excess_sq, 0.0)

    # sigma(r) in physical units (cm^2/s^2)
    sigma_phys = v_excess_sq / KAPPA

    # Dynamical mass enclosed at each radius
    # M_dyn(r) = v^2 * r / G
    M_dyn = v_obs_cm ** 2 * r_cm / G_CGS
    M_dyn = np.maximum(M_dyn, 0.0)

    # Shell mass (differential)
    M_shell = np.zeros(n)
    for i in range(1, n):
        M_shell[i] = max(M_dyn[i] - M_dyn[i - 1], 0.0)
    M_shell[0] = M_dyn[0]

    # Substrate gravitational energy per shell
    # E = (1/2) * M_shell * v_excess^2
    E_shell = 0.5 * M_shell * v_excess_sq

    # Total substrate energy (sum over shells)
    # E_shell already represents energy in each discrete
    # shell — M_shell accounts for radial extent.
    E_sub = float(np.sum(E_shell))

    # Energy density per unit area (for radial profile)
    h_cm = H_DISK_KPC * KPC_CM
    energy_density = 0.5 * sigma_phys ** 2 / (C_CMS ** 2) * h_cm

    return E_sub, sigma_phys, energy_density


def compute_maintenance_luminosity(E_sub):
    """
    L_nu = lambda * E_sub

    The power required to continuously refill the substrate
    energy that decays at rate lambda. This is the SMBH
    neutrino pump output.

    Returns L_nu in erg/s.
    """
    # lambda is dimensionless in the solver (per timestep)
    # Physical decay timescale: t_decay = 1/lambda * dt_phys
    # dt_phys = 1.25e-13 s (CMB-locked)
    # But for the energy budget, lambda * E gives power
    # when E is already integrated over the physical volume

    # The decay rate in physical units:
    # In the solver: dsigma/dt = -lambda*sigma + ...
    # At steady state: J = lambda*sigma
    # Power = lambda * E_sub (energy replenished per
    # characteristic decay time)

    # The characteristic decay time is:
    # t_decay = 1/(lambda * omega) where omega is the
    # substrate oscillation frequency
    # For the galactic substrate: omega ~ v_max / r_max
    # Typical: 200 km/s / 10 kpc ~ 6.5e-16 rad/s
    # t_decay ~ 1/(0.1 * 6.5e-16) ~ 1.5e16 s ~ 500 Myr
    # This is the substrate replenishment timescale

    # Direct: L_nu = E_sub / t_decay = lambda * omega * E_sub
    # For now, parameterize as L_nu = E_sub / t_replenish
    # with t_replenish computed per galaxy from v_max/r_max

    return E_sub  # Return raw E, compute L per galaxy below


def compute_flux_at_earth(L_nu_erg_s, D_mpc):
    """
    Neutrino energy flux at Earth.

    Phi = L_nu / (4*pi*D^2)  [erg cm^-2 s^-1]
    Phi_gev = Phi * GeV_per_erg  [GeV cm^-2 s^-1]

    Returns flux in GeV cm^-2 s^-1 for IceCube comparison.
    """
    D_cm = D_mpc * MPC_CM
    if D_cm <= 0:
        return 0.0
    flux_erg = L_nu_erg_s / (4.0 * np.pi * D_cm ** 2)
    flux_gev = flux_erg * GEV_PER_ERG
    return flux_gev


# ═══════════════════════════════════════
# PROCESS ONE GALAXY
# ═══════════════════════════════════════

def process_galaxy(gdata, verbose=True):
    """
    Full neutrino flux calculation for one galaxy.

    1. Back-calculate sigma(r) from v_bcm, v_newton
    2. Compute substrate energy E_sub
    3. Compute maintenance luminosity L_nu
    4. Compute flux at Earth
    5. Derive Burdick Constant nu_b
    6. Compare to IceCube/KM3NeT sensitivity
    """
    name = gdata["galaxy"]
    r_kpc = np.array(gdata["r_kpc"])
    v_obs = np.array(gdata["v_obs"])
    v_newton = np.array(gdata["v_newton"])
    v_bcm = np.array(gdata["v_bcm"])
    vmax = gdata["v_max_kms"]
    n_pts = gdata["n_points"]

    if name not in DISTANCES_MPC:
        if verbose:
            print(f"  SKIP {name}: no distance")
        return None

    D_mpc = DISTANCES_MPC[name]
    M_bh, mbh_src = get_mbh(name, vmax)

    # ── 1. Substrate energy ──
    E_sub, sigma_phys, energy_density = compute_substrate_energy(
        r_kpc, v_bcm, v_newton, vmax)

    # ── 2. Replenishment timescale ──
    # t_replenish = r_max / v_max (dynamical time)
    # This is the natural timescale for the SMBH to
    # refill the substrate across the disk
    r_max_cm = r_kpc[-1] * KPC_CM
    v_max_cm = vmax * KMS_CMS
    t_dyn = r_max_cm / v_max_cm if v_max_cm > 0 else 1e16
    t_replenish = t_dyn / LAMBDA  # substrate decay timescale

    # ── 3. Maintenance luminosity ──
    L_nu = E_sub / t_replenish  # erg/s

    # ── 4. Flux at Earth ──
    flux_gev = compute_flux_at_earth(L_nu, D_mpc)

    # ── 5. Neutrino count rate ──
    # N_dot = Phi / E_nu (neutrinos per cm^2 per s)
    N_dot = flux_gev / E_NU_GEV if E_NU_GEV > 0 else 0.0

    # ── 6. Burdick Constant ──
    # nu_b = L_nu / v_max^4
    # Should be approximately constant for Class I galaxies
    # if maintenance scales with v^4 (gravitational binding)
    v4 = (vmax * KMS_CMS) ** 4
    nu_b = L_nu / v4 if v4 > 0 else 0.0

    # ── 7. Eddington neutrino fraction ──
    # What fraction of Eddington luminosity goes to
    # substrate maintenance?
    L_edd = 1.26e38 * (M_bh / M_SUN_G * M_SUN_G)  # erg/s
    L_edd = 1.26e38 * M_bh  # Eddington for M_bh in M_sun
    nu_edd_frac = L_nu / L_edd if L_edd > 0 else 0.0

    # ── 8. IceCube detectability ──
    detect_icecube_tev = flux_gev > ICECUBE_SENS_TEV
    detect_icecube_gev = flux_gev > ICECUBE_SENS_GEV
    detect_km3net = flux_gev > KM3NET_SENS

    # ── 9. Substrate excess profile (inner vs outer) ──
    # The gradient signature: Class IV should show inner
    # excess decaying to zero at outer radii
    n = len(r_kpc)
    half = n // 2
    v_excess_inner = np.mean(v_bcm[:half] ** 2 - v_newton[:half] ** 2)
    v_excess_outer = np.mean(v_bcm[half:] ** 2 - v_newton[half:] ** 2)
    gradient_ratio = (v_excess_inner / v_excess_outer
                      if v_excess_outer > 0 else float('inf'))

    if verbose:
        print(f"\n  {'='*55}")
        print(f"  {name}  (D={D_mpc:.1f} Mpc, V={vmax:.0f} km/s)")
        print(f"  {'='*55}")
        print(f"  M_BH = {M_bh:.2e} M_sun ({mbh_src})")
        print(f"  E_sub = {E_sub:.3e} erg")
        print(f"  t_replenish = {t_replenish:.3e} s"
              f" ({t_replenish/3.156e7:.1f} Myr)")
        print(f"  L_nu = {L_nu:.3e} erg/s"
              f" ({L_nu/3.846e33:.2e} L_sun)")
        print(f"  L_nu/L_edd = {nu_edd_frac:.2e}")
        print(f"  Flux = {flux_gev:.3e} GeV cm^-2 s^-1")
        print(f"  IceCube (TeV): {'DETECTABLE' if detect_icecube_tev else 'below'}")
        print(f"  IceCube (GeV): {'DETECTABLE' if detect_icecube_gev else 'below'}")
        print(f"  KM3NeT:        {'DETECTABLE' if detect_km3net else 'below'}")
        print(f"  nu_b = {nu_b:.3e} (Burdick Constant)")
        print(f"  Gradient: inner/outer = {gradient_ratio:.2f}")

    return {
        "galaxy":          name,
        "D_mpc":           D_mpc,
        "v_max_kms":       vmax,
        "n_points":        n_pts,
        "M_bh_solar":      M_bh,
        "mbh_source":      mbh_src,
        "chi2_bcm":        gdata.get("chi2_bcm", 0),
        "winner":          gdata.get("winner_chi2", ""),

        # Energy budget
        "E_sub_erg":       E_sub,
        "t_replenish_s":   t_replenish,
        "t_replenish_Myr": t_replenish / 3.156e7,
        "L_nu_erg_s":      L_nu,
        "L_nu_Lsun":       L_nu / 3.846e33,
        "L_nu_L_edd":      nu_edd_frac,

        # Flux at Earth
        "flux_gev_cm2_s":  flux_gev,
        "N_dot_cm2_s":     N_dot,

        # Detectability
        "detect_icecube_tev": bool(detect_icecube_tev),
        "detect_icecube_gev": bool(detect_icecube_gev),
        "detect_km3net":      bool(detect_km3net),

        # Burdick Constant
        "nu_b":            nu_b,

        # Gradient signature
        "v_excess_inner":  float(v_excess_inner),
        "v_excess_outer":  float(v_excess_outer),
        "gradient_ratio":  float(gradient_ratio)
            if not np.isinf(gradient_ratio) else -1.0,

        # Per-point data for plots
        "r_kpc":           r_kpc.tolist(),
        "sigma_phys":      sigma_phys.tolist(),
    }


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v23 — Neutrino Flux Prediction")
    parser.add_argument("--chi2-json", type=str,
        default=None,
        help="Path to grid=256 chi-squared JSON")
    parser.add_argument("--output", type=str, default=None,
        help="Output JSON path")
    args = parser.parse_args()

    # ── Find chi-squared JSON ──
    chi2_path = args.chi2_json
    if chi2_path is None:
        results_dir = os.path.join(SCRIPT_DIR, "data", "results")
        candidates = sorted([
            f for f in os.listdir(results_dir)
            if f.startswith("BCM_chi2_engine") and f.endswith(".json")
        ], reverse=True)
        if candidates:
            chi2_path = os.path.join(results_dir, candidates[0])
        else:
            print("  ERROR: No chi-squared JSON found.")
            print("  Run BCM_chi_squared_engine.py first.")
            sys.exit(1)

    print("=" * 60)
    print("  BCM v23 — NEUTRINO FLUX PREDICTION ENGINE")
    print("  Stephen Justin Burdick Sr.")
    print("  Emerald Entities LLC — GIBUSH Systems")
    print("=" * 60)
    print(f"\n  The substrate maintenance budget has a")
    print(f"  physical equivalent in detectable particles.")
    print(f"\n  Chi-squared source: {chi2_path}")
    print(f"  lambda = {LAMBDA}")
    print(f"  kappa = {KAPPA}")
    print(f"  E_nu = {E_NU_GEV} GeV (fiducial)")
    print(f"  IceCube sensitivity (TeV): {ICECUBE_SENS_TEV:.0e}")
    print(f"  IceCube sensitivity (GeV): {ICECUBE_SENS_GEV:.0e}")
    print(f"  KM3NeT sensitivity: {KM3NET_SENS:.0e}")

    # ── Load chi-squared results ──
    with open(chi2_path) as f:
        chi2_data = json.load(f)

    galaxies = chi2_data["galaxies"]
    grid = chi2_data["config"]["grid"]
    print(f"\n  Grid: {grid}")
    print(f"  Galaxies: {len(galaxies)}")

    # ── Process all galaxies ──
    t_start = time.time()
    results = []

    for gdata in galaxies:
        r = process_galaxy(gdata, verbose=True)
        if r is not None:
            results.append(r)

    t_total = time.time() - t_start

    # ═══════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  v23 SUMMARY — {len(results)} galaxies"
          f" in {t_total:.1f}s")
    print(f"{'='*60}")

    if results:
        # Luminosity statistics
        L_vals = [r["L_nu_erg_s"] for r in results]
        nu_b_vals = [r["nu_b"] for r in results]

        print(f"\n  MAINTENANCE LUMINOSITY:")
        print(f"    Min:    {min(L_vals):.3e} erg/s")
        print(f"    Max:    {max(L_vals):.3e} erg/s")
        print(f"    Mean:   {np.mean(L_vals):.3e} erg/s")

        # Detectability
        det_tev = sum(1 for r in results
                      if r["detect_icecube_tev"])
        det_gev = sum(1 for r in results
                      if r["detect_icecube_gev"])
        det_km3 = sum(1 for r in results
                      if r["detect_km3net"])

        print(f"\n  DETECTABILITY:")
        print(f"    IceCube (TeV band): {det_tev}/{len(results)}")
        print(f"    IceCube (GeV band): {det_gev}/{len(results)}")
        print(f"    KM3NeT (projected): {det_km3}/{len(results)}")

        # Burdick Constant
        # Filter to Class I galaxies (massive bracket winners)
        massive = [r for r in results if r["v_max_kms"] > 180]
        if massive:
            nu_b_massive = [r["nu_b"] for r in massive]
            print(f"\n  BURDICK CONSTANT (nu_b = L_nu / v_max^4):")
            print(f"    Massive bracket ({len(massive)} galaxies):")
            print(f"    Mean:   {np.mean(nu_b_massive):.3e}")
            print(f"    Std:    {np.std(nu_b_massive):.3e}")
            print(f"    CV:     {np.std(nu_b_massive)/np.mean(nu_b_massive)*100:.1f}%")
            print(f"    Range:  {min(nu_b_massive):.3e}"
                  f" — {max(nu_b_massive):.3e}")

        # Gradient signature (Class IV diagnostic)
        print(f"\n  GRADIENT SIGNATURE (inner/outer excess):")
        print(f"  {'Galaxy':<16} {'Vmax':>5} {'Gradient':>9}"
              f" {'Inner':>10} {'Outer':>10} {'Winner':>7}")
        print(f"  {'─'*16} {'─'*5} {'─'*9}"
              f" {'─'*10} {'─'*10} {'─'*7}")
        for r in sorted(results,
                         key=lambda x: x["v_max_kms"]):
            gr = r["gradient_ratio"]
            gr_str = f"{gr:.2f}" if gr > 0 else "INF"
            print(f"  {r['galaxy']:<16} {r['v_max_kms']:>5.0f}"
                  f" {gr_str:>9}"
                  f" {r['v_excess_inner']:>10.0f}"
                  f" {r['v_excess_outer']:>10.0f}"
                  f" {r['winner']:>7}")

        # Full table
        print(f"\n  {'Galaxy':<16} {'D':>5} {'Vmax':>5}"
              f" {'L_nu':>10} {'Flux':>10}"
              f" {'nu_b':>10} {'ICT':>4} {'ICG':>4}")
        print(f"  {'─'*16} {'─'*5} {'─'*5}"
              f" {'─'*10} {'─'*10}"
              f" {'─'*10} {'─'*4} {'─'*4}")
        for r in sorted(results,
                         key=lambda x: x["v_max_kms"]):
            ict = "YES" if r["detect_icecube_tev"] else "no"
            icg = "YES" if r["detect_icecube_gev"] else "no"
            print(f"  {r['galaxy']:<16} {r['D_mpc']:>5.1f}"
                  f" {r['v_max_kms']:>5.0f}"
                  f" {r['L_nu_erg_s']:>10.2e}"
                  f" {r['flux_gev_cm2_s']:>10.2e}"
                  f" {r['nu_b']:>10.2e}"
                  f" {ict:>4} {icg:>4}")

    # ═══════════════════════════════════════
    # SAVE JSON
    # ═══════════════════════════════════════
    out_path = args.output
    if out_path is None:
        out_dir = os.path.join(SCRIPT_DIR, "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir,
            f"BCM_v23_neutrino_{time.strftime('%Y%m%d_%H%M%S')}.json")

    output = {
        "engine":    "BCM_v23_neutrino_flux",
        "version":   "v23.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_s": t_total,
        "author":    "Stephen Justin Burdick Sr.",
        "entity":    "Emerald Entities LLC — GIBUSH Systems",
        "config": {
            "lambda":       LAMBDA,
            "kappa":        KAPPA,
            "E_nu_GeV":     E_NU_GEV,
            "H_disk_kpc":   H_DISK_KPC,
            "grid_source":  grid,
            "chi2_source":  os.path.basename(chi2_path),
            "icecube_sens_tev": ICECUBE_SENS_TEV,
            "icecube_sens_gev": ICECUBE_SENS_GEV,
            "km3net_sens":      KM3NET_SENS,
        },
        "n_galaxies": len(results),
        "summary": {
            "L_nu_min":   float(min(L_vals)) if results else 0,
            "L_nu_max":   float(max(L_vals)) if results else 0,
            "L_nu_mean":  float(np.mean(L_vals)) if results else 0,
            "detect_icecube_tev": det_tev if results else 0,
            "detect_icecube_gev": det_gev if results else 0,
            "detect_km3net":      det_km3 if results else 0,
            "nu_b_massive_mean":
                float(np.mean(nu_b_massive))
                if massive else 0,
            "nu_b_massive_std":
                float(np.std(nu_b_massive))
                if massive else 0,
            "nu_b_massive_cv_pct":
                float(np.std(nu_b_massive) /
                      np.mean(nu_b_massive) * 100)
                if massive and np.mean(nu_b_massive) > 0 else 0,
        },
        "galaxies": results,
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  Saved: {out_path}")
    print(f"\n  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems — 2026")
    print(f"\n  The maintenance budget has a meter reading.")
    print(f"  The glow is directional.")
    print(f"  IceCube has the data. Now they have the map.")
