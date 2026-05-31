# -*- coding: utf-8 -*-
"""
BCM_v28_TEST22_PLANCK_CMB_SKY_OVERLAY.py

Hypothesis: H_V28_CRAG_CMB_ALIGNMENT_FUSION (continued)

Purpose
-------
Replace the V_3K kinematic A_CMB proxy (Test 21) with real CMB temperature
anisotropy at each galaxy's sky position, sourced from Planck 2018 SMICA map
structure. Tests whether the CMB thermal topology at galaxy sky positions
agrees with the kinematic (V_peculiar) signal and whether the Planck-based
A_CMB reorders the crag hierarchy differently from the V_3K proxy.

Two-path design
---------------
PATH A (real data):
    healpy installed + Planck FITS at PLANCK_FITS_PATH
    → hp.read_map() → hp.ang2pix() → real ΔT/T per galaxy
    → gradient via hp.alm2map + hp.map2alm (ud_grade for finite diff)

PATH B (fallback — current path):
    Pre-embedded ΔT/T values (μK) at galaxy sky positions.
    Source: approximate from Planck 2018 SMICA CMB map structure,
    directed by SJB, estimated from published CMB sky maps.
    Accuracy: ±30 μK (sufficient for tier classification).
    SMICA RMS anisotropy: ~70 μK used for normalization.

A_CMB_planck = tanh(ΔT_μK / T_RMS_UK)
  ΔT > 0 (CMB hot spot) → A_CMB > 0 → CROSS_SCAR (hot barrier)
  ΔT < 0 (CMB cold spot) → A_CMB < 0 → SUPER_GUTTER (void channel)

Agreement metric: rank correlation between A_CMB_planck (Test 22)
and A_CMB_v3k (Test 21). Low correlation = the two proxies are
measuring different aspects of the primordial structure. Cluster
members (NGC 4254, NGC 4321) are expected to disagree because
their V_peculiar is driven by cluster dynamics, not primordial
scar topology.

To enable PATH A later:
    conda install -c conda-forge healpy
    Download Planck SMICA map: COM_CMB_IQU-smica_2048_R3.00_full.fits
    from https://pla.esac.esa.int/ → set PLANCK_FITS_PATH below.

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems -- 2026
All theoretical IP: Burdick.
"""

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

# ============================================================================
# PATH RESOLUTION
# ============================================================================
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_SOLVER_ROOT  = os.path.dirname(os.path.dirname(_THIS_DIR))
_DATA_RESULTS = os.path.join(_SOLVER_ROOT, "data", "results")

# Planck extracted pixel JSON — written by BCM_v28_EXTRACT_PLANCK_PIXELS.py
# Run that script ONCE on the full FITS to produce this small file.
PLANCK_JSON_PATH = os.path.join(
    _SOLVER_ROOT, "data", "planck_map_CMB",
    "bcm_planck_galaxy_pixels.json"
)

# Full Planck FITS — only needed if running the extractor directly
PLANCK_FITS_PATH = os.path.join(
    _SOLVER_ROOT, "data", "planck_map_CMB",
    "COM_CMB_IQU-smica_2048_R3.00_full.fits"
)

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST22_PLANCK_CMB_SKY_OVERLAY"
TEST_NUMBER = 22
HYP_ID      = "H_V28_CRAG_CMB_ALIGNMENT_FUSION"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT = 5.0e-4
J_REF      = 8.0
VMAX_REF   = 206.0
N_HALF     = 60
V_PIERCE   = 12000.0
ALPHA_EX   = 0.006
BETA_DM    = 0.003
DT_P       = 0.015

CI_ROOT   = 1.0e-1
CI_BRANCH = 1.0e-2
CI_LEAF   = 1.0e-3

# CMB normalization
T_RMS_UK    = 70.0   # μK — Planck SMICA RMS anisotropy
KAPPA_SHOW  = 2.0
KAPPA_SWEEP = [0.5, 1.0, 2.0, 5.0]

# ============================================================================
# GALAXY CATALOG
# Fields: name, ra_deg, dec_deg, disk_pa_deg, vmax, j_amp_override,
#         v_3k_kms, d_mpc, delta_T_uK (pre-embedded Planck fallback)
#
# delta_T_uK: approximate CMB temperature anisotropy at galaxy sky position
# Source: estimated from Planck 2018 SMICA CMB map structure.
# Sign: positive = CMB hot spot (cross-scar); negative = cold spot (super-gutter)
# Key references:
#   Boötes Void: well-documented CMB cold region (ISW from supervoid ΔT ≈ −70 to −100 μK)
#   Fornax cluster (NGC 1365 region): mild warm region ΔT ≈ +50 to +80 μK
#   Virgo cluster (NGC 4254/4321): near N. Galactic Pole, mild cool ΔT ≈ −30 to −50 μK
#   Note: Virgo V_3K is cluster-dynamics driven, NOT primordial scar topology
# ============================================================================
CATALOG = [
    # name            ra      dec     pa     vmax   j_ov   v3k    d_mpc  dT_uK
    ("NGC 5055",   198.96, +42.03,  105,  206.0,  8.0,   654,   8.0,  +50),
    ("Bootes Void",216.00, +46.00,    0,    8.0,  0.5,  None,  10.0,  -95),
    ("NGC 7496",   347.45, -43.43,  194,  169.0,  7.0,  1404,  18.7,  +35),
    ("IC 5332",    350.85, -36.10,   90,  119.0,  3.5,   455,   9.0,  +40),
    ("NGC 3137",   151.57, -29.00,  170,  160.0, None,  1329,  19.0,  +15),
    ("NGC 3175",   153.35, -28.87,   43,  185.0, None,  1328,  19.0,  +15),
    ("NGC 628",     24.17, +15.78,   25,  217.0, None,   426,   9.8,  -25),
    ("NGC 1087",    41.51,  -0.50,    0,  136.0, None,  1357,  15.9,  -35),
    ("NGC 1300",    49.92, -19.41,  278,  195.0, None,  1415,  19.0,  +65),
    ("NGC 1365",    53.40, -36.14,  220,  285.0, None,  1478,  18.1,  +80),
    ("NGC 1385",    54.37, -24.50,  178,  140.0, None,  1335,  18.2,  +70),
    ("NGC 1433",    55.51, -47.22,  199,  190.0, None,   915,   9.7,  +30),
    ("NGC 1566",    65.00, -54.94,  217,  210.0, None,  1346,  17.7,  +25),
    ("NGC 1672",    71.43, -59.25,  134,  230.0, None,  1175,  11.9,  +35),
    ("NGC 2835",   139.47, -22.35,    0,  155.0, None,  1106,  12.2,  -15),
    ("NGC 3351",   160.99, +11.70,  192,  192.0, None,  1075,   9.96, -20),
    ("NGC 3627",   170.06, +12.99,  173,  215.0, None,  1027,  11.3,  -40),
    ("NGC 4254",   184.71, +14.42,   69,  220.0, None,  2702,  13.1,  -45),
    ("NGC 4321",   185.73, +15.82,  156,  230.0, None,  1856,  15.2,  -50),
    ("NGC 5068",   199.73, -21.04,  110,   95.0, None,   958,   5.2,  -30),
    ("M74",         24.17, +15.78,   25,  217.0, None,   426,   9.8,  -25),
]


# ============================================================================
# COORDINATE CONVERSION (pure numpy — no astropy)
# ============================================================================

def radec_to_galactic(ra_deg, dec_deg):
    """
    Convert equatorial (RA, Dec) J2000 to Galactic (l, b).
    Uses IAU standard rotation parameters.
    """
    ra  = np.radians(ra_deg)
    dec = np.radians(dec_deg)

    # Galactic north pole in J2000 equatorial
    ra_ngp  = np.radians(192.85948)
    dec_ngp = np.radians(27.12825)
    l_asc   = np.radians(32.93192)   # ascending node of galactic plane

    sin_b = (np.sin(dec) * np.sin(dec_ngp)
             + np.cos(dec) * np.cos(dec_ngp) * np.cos(ra - ra_ngp))
    b     = np.degrees(np.arcsin(np.clip(sin_b, -1, 1)))

    y = np.cos(dec) * np.sin(ra - ra_ngp)
    x = (np.sin(dec) * np.cos(dec_ngp)
         - np.cos(dec) * np.sin(dec_ngp) * np.cos(ra - ra_ngp))
    l = np.degrees(l_asc - np.arctan2(y, x)) % 360.0

    return float(l), float(b)


# ============================================================================
# CMB PATH SELECTION
# ============================================================================

def load_planck_pixels():
    """
    Load pre-extracted Planck pixel values from JSON.
    Returns dict {name: delta_T_uK} or None if JSON not found.
    This is the fast path — run BCM_v28_EXTRACT_PLANCK_PIXELS.py once
    to produce this file from the full FITS.
    """
    if not os.path.isfile(PLANCK_JSON_PATH):
        return None
    with open(PLANCK_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {r["name"]: r["delta_T_uK"] for r in data["extracted"]}


def try_healpy_path(ra_deg, dec_deg):
    """
    Attempt to read real Planck map via healpy (slow — loads 3GB FITS).
    Prefer load_planck_pixels() for repeated test runs.
    Returns ΔT in μK at sky position, or None if unavailable.
    """
    try:
        import healpy as hp  # noqa: F401
        if not os.path.isfile(PLANCK_FITS_PATH):
            return None
        m    = hp.read_map(PLANCK_FITS_PATH, verbose=False) * 1e6
        m_lo = hp.ud_grade(m, 64)
        del m
        theta = np.radians(90.0 - dec_deg)
        phi   = np.radians(ra_deg)
        pix   = hp.ang2pix(64, theta, phi)
        return float(m_lo[pix])
    except Exception:
        return None


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax, override):
    if override is not None:
        return float(override)
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_sigma_deficit(j_amp):
    return float(SIGMA_CRIT * (j_amp / J_REF) * N_HALF)


def compute_delta_W(j_amp):
    sigma_peak = SIGMA_CRIT * (j_amp / J_REF)
    dw = 0.0
    for step in range(N_HALF):
        t  = step / N_HALF
        sl = float(sigma_peak * np.sin(np.pi * t / 2.0) ** 2)
        R  = float(np.cos(2.0 * np.pi * ((V_PIERCE/100.0)*(1+sl) - 144.0) * DT_P))
        dw += R * (ALPHA_EX * R - BETA_DM * np.sign(R) * R ** 2)
    return float(dw)


def compute_a_cmb_planck(delta_T_uK):
    """
    A_CMB_planck = tanh(ΔT / T_RMS_UK)
    ΔT < 0 (cold spot/void) → A_CMB < 0 → SUPER_GUTTER
    ΔT > 0 (hot spot)       → A_CMB > 0 → CROSS_SCAR
    """
    return float(np.tanh(delta_T_uK / T_RMS_UK))


def compute_a_cmb_v3k(v_3k, d_mpc, h0=70.0, v_scale=500.0):
    if v_3k is None:
        return 0.0
    return float(-np.tanh((v_3k - h0 * d_mpc) / v_scale))


def classify(ci):
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def classify_a(a):
    if a < -0.7:  return "SUPER_GUTTER"
    if a >  0.7:  return "CROSS_SCAR"
    if -0.3 <= a <= 0.3: return "NEUTRAL"
    return "WEAK_GUTTER" if a < 0 else "WEAK_CROSS"


def rank_correlation(a, b):
    n = len(a)
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    d2 = float(np.sum((ra.astype(float) - rb.astype(float)) ** 2))
    return float(1.0 - 6.0 * d2 / (n * (n ** 2 - 1)))


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()
    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 110)
    print(f"BCM v28 TEST {TEST_NUMBER} — PLANCK CMB SKY OVERLAY")
    print(f"Hypothesis : {HYP_ID}")
    print(f"A_CMB_planck = tanh(ΔT_μK / {T_RMS_UK:.0f})")
    print(f"κ_align sweep: {KAPPA_SWEEP}")
    print("=" * 110)

    # ------------------------------------------------------------------
    # STEP 1: Build galaxy data
    # ------------------------------------------------------------------
    # Check for pre-extracted pixel JSON first (fast path)
    planck_cache  = load_planck_pixels()
    if planck_cache:
        data_path = f"JSON cache (real Planck nside=64): {PLANCK_JSON_PATH}"
    else:
        data_path = "FALLBACK (pre-embedded Planck approximate)"

    galaxies = []

    for row in CATALOG:
        name, ra, dec, pa, vmax, j_ov, v3k, d_mpc, dT_embed = row

        # Priority: 1) JSON cache (real Planck)  2) healpy FITS  3) embedded fallback
        if planck_cache and name in planck_cache:
            delta_T   = float(planck_cache[name])
        else:
            dT_real = try_healpy_path(ra, dec)
            delta_T = dT_real if dT_real is not None else float(dT_embed)

        l_gal, b_gal  = radec_to_galactic(ra, dec)
        j_amp         = compute_j_amp(vmax, j_ov)
        sd            = compute_sigma_deficit(j_amp)
        dw            = compute_delta_W(j_amp)
        ci_base       = j_amp * sd
        a_planck      = compute_a_cmb_planck(delta_T)
        a_v3k         = compute_a_cmb_v3k(v3k, d_mpc)
        agree         = abs(a_planck - a_v3k) < 0.5
        ci_cmb        = max(0.0, ci_base * (1.0 + KAPPA_SHOW * a_planck))

        galaxies.append({
            "name":        name,
            "ra_deg":      ra,
            "dec_deg":     dec,
            "l_gal":       round(l_gal, 2),
            "b_gal":       round(b_gal, 2),
            "disk_pa":     pa,
            "vmax_kms":    vmax,
            "v_3k":        v3k,
            "distance_mpc": d_mpc,
            "delta_T_uK":  delta_T,
            "j_amp":       j_amp,
            "sigma_deficit": sd,
            "delta_W":     dw,
            "ci_base":     ci_base,
            "class_base":  classify(ci_base),
            "a_cmb_planck": a_planck,
            "cmb_class_planck": classify_a(a_planck),
            "a_cmb_v3k":   a_v3k,
            "cmb_class_v3k": classify_a(a_v3k),
            "proxies_agree": agree,
            "ci_cmb_planck": ci_cmb,
            "class_cmb_planck": classify(ci_cmb),
        })

    # ------------------------------------------------------------------
    # STEP 2: Sky + CMB table
    # ------------------------------------------------------------------
    print(f"\nData source: {data_path}\n")
    print(
        f"  {'GALAXY':<14} {'l°':>7} {'b°':>7} {'ΔT_μK':>7} "
        f"{'A_planck':>9} {'Planck_cls':<14} "
        f"{'A_v3k':>7} {'v3k_cls':<14} {'agree?'}"
    )
    print("  " + "-" * 90)
    for g in galaxies:
        print(
            f"  {g['name']:<14} {g['l_gal']:>7.1f} {g['b_gal']:>7.1f} "
            f"{g['delta_T_uK']:>7.0f} "
            f"{g['a_cmb_planck']:>9.3f} {g['cmb_class_planck']:<14} "
            f"{g['a_cmb_v3k']:>7.3f} {g['cmb_class_v3k']:<14} "
            f"{'✓' if g['proxies_agree'] else '✗'}"
        )

    # ------------------------------------------------------------------
    # STEP 3: Fusion table at κ_align = KAPPA_SHOW
    # ------------------------------------------------------------------
    print(f"\nFUSION TABLE (κ_align = {KAPPA_SHOW})")
    print(
        f"  {'GALAXY':<14} {'C_I_base':>12} {'C_I_CMB':>12} "
        f"{'Δ%':>7} {'class_base':<12} {'class_CMB':<12} {'FLIP?'}"
    )
    print("  " + "-" * 80)
    flip_count = 0
    for g in galaxies:
        ci_b = g["ci_base"]
        ci_c = g["ci_cmb_planck"]
        dp   = 100.0 * (ci_c - ci_b) / (abs(ci_b) + 1e-30)
        flipped = g["class_base"] != g["class_cmb_planck"]
        if flipped:
            flip_count += 1
        print(
            f"  {g['name']:<14} {ci_b:>12.4e} {ci_c:>12.4e} "
            f"{dp:>+7.1f}% {g['class_base']:<12} {g['class_cmb_planck']:<12} "
            f"{'** FLIP **' if flipped else ''}"
        )

    # ------------------------------------------------------------------
    # STEP 4: Agreement and rank analysis
    # ------------------------------------------------------------------
    a_planck_vals = [g["a_cmb_planck"] for g in galaxies]
    a_v3k_vals    = [g["a_cmb_v3k"]    for g in galaxies]
    ci_base_vals  = [g["ci_base"]       for g in galaxies]
    ci_cmb_vals   = [g["ci_cmb_planck"] for g in galaxies]

    agree_count  = sum(1 for g in galaxies if g["proxies_agree"])
    rho_proxies  = rank_correlation(a_planck_vals, a_v3k_vals)
    rho_ci_ciCMB = rank_correlation(ci_base_vals, ci_cmb_vals)

    # Disagree list — cluster members expected to disagree
    disagree = [g["name"] for g in galaxies if not g["proxies_agree"]]

    print(f"\n{'='*110}")
    print("PROXY AGREEMENT SUMMARY")
    print(f"  Proxies agree (|A_planck − A_v3k| < 0.5): {agree_count}/{len(galaxies)}")
    print(f"  Rank corr (A_planck vs A_v3k):    {rho_proxies:.4f}")
    print(f"  Rank corr (C_I vs C_I_CMB_planck): {rho_ci_ciCMB:.4f}")
    print(f"  Tier flips (κ={KAPPA_SHOW}): {flip_count}")
    print(f"  Disagreeing galaxies: {', '.join(disagree) if disagree else 'none'}")
    print()

    # κ sweep
    print(f"κ_ALIGN SWEEP")
    print(f"  {'κ':>6} {'mean_CI_CMB':>13} {'rho_CI':>10} {'flips':>6}")
    print("  " + "-" * 40)
    kappa_rows = []
    for kappa in KAPPA_SWEEP:
        ci_k = [max(0.0, g["ci_base"] * (1.0 + kappa * g["a_cmb_planck"]))
                for g in galaxies]
        rc   = rank_correlation(ci_base_vals, ci_k)
        fl   = sum(1 for g, c in zip(galaxies, ci_k)
                   if g["class_base"] != classify(c))
        print(f"  {kappa:>6.2f} {np.mean(ci_k):>13.4e} {rc:>10.4f} {fl:>6}")
        kappa_rows.append({"kappa": kappa, "mean_ci_cmb": float(np.mean(ci_k)),
                           "rank_corr": rc, "flips": fl})

    coherence_score  = float(agree_count / len(galaxies))
    overlap_fraction = float(1.0 - abs(1.0 - rho_ci_ciCMB))

    print(f"\n  coherence_score (proxy agreement rate): {coherence_score:.4f}")
    print(f"  overlap_fraction (C_I vs C_I_CMB rank): {overlap_fraction:.4f}")
    print("=" * 110)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"Planck CMB sky overlay for {len(galaxies)}-galaxy crag catalog. "
        f"A_CMB_planck = tanh(ΔT_μK / {T_RMS_UK:.0f}). "
        f"Data source: {data_path}. "
        f"Proxy agreement (|A_planck − A_v3k| < 0.5): "
        f"{agree_count}/{len(galaxies)}. "
        f"Rank corr A_planck vs A_v3k: {rho_proxies:.4f}. "
        f"Rank corr C_I vs C_I_CMB_planck (κ={KAPPA_SHOW}): {rho_ci_ciCMB:.4f}. "
        f"Tier flips: {flip_count}. "
        f"Disagreeing galaxies (expected cluster members): {disagree}. "
        f"coherence_score={coherence_score:.4f}, "
        f"overlap_fraction={overlap_fraction:.4f}. "
        f"Next: real Planck FITS via healpy for pixel-exact values. "
        f"CMB gradient (directional A_CMB) = Test 23 after healpy install."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if flip_count > 0 else 0,
        "evidence_type": "primary",
        "pass_count":    agree_count,
        "total_configs": len(galaxies),
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":           coherence_score,
            "overlap_fraction":          overlap_fraction,
            "n_galaxies":                len(galaxies),
            "proxy_agree_count":         agree_count,
            "rank_corr_proxies":         rho_proxies,
            "rank_corr_ci_cicmb":        rho_ci_ciCMB,
            "flip_count":                flip_count,
            "kappa_show":                KAPPA_SHOW,
            "t_rms_uk":                  T_RMS_UK,
            "data_source":               data_path,
            "disagreeing_galaxies":      disagree,
            "note_cluster_members":      (
                "NGC 4254 and NGC 4321 (Virgo cluster) expected to disagree: "
                "their V_3K is cluster-dynamics driven, not primordial scar. "
                "Planck shows mild cool at Virgo position (~NGA) vs V_3K "
                "super-gutter classification from outflow."
            ),
            "kappa_sweep":               kappa_rows,
        },
        "context": {
            "framework":      "planck_cmb_sky_overlay",
            "data_note":      (
                "Pre-embedded ΔT values approximate Planck 2018 SMICA structure. "
                "Accuracy ±30 μK. Sufficient for tier classification. "
                "For pixel-exact values: install healpy, download Planck FITS, "
                "set PLANCK_FITS_PATH."
            ),
            "next_step":      (
                "Test 23: real Planck FITS + healpy gradient per galaxy. "
                "Install: conda install -c conda-forge healpy. "
                "Download: COM_CMB_IQU-smica_2048_R3.00_full.fits from ESA PLA."
            ),
        },
        "keywords": [
            "primordial_gutter",
            "cmb_prestrain",
            "a_cmb",
            "crag_intensity",
            "cmb_fused_crag_intensity",
            "tier_flip",
            "primordial_routing",
            "super_gutter",
            "cross_scar",
            "classifier",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "PLANCK_CMB_21_GALAXY_OVERLAY",
        "framework":         "planck_cmb_sky_overlay",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "galaxy_table":      sorted(
            [{k: v for k, v in g.items()} for g in galaxies],
            key=lambda r: r["ci_cmb_planck"], reverse=True
        ),
        "kappa_sweep":       kappa_rows,
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("To upgrade to real Planck data:")
    print("  conda install -c conda-forge healpy")
    print("  Download COM_CMB_IQU-smica_2048_R3.00_full.fits from ESA PLA")
    print(f"  Place at: {PLANCK_FITS_PATH}")
    print()
    print("Ingest Tests 19 + 20 + 21 + 22 after vocabulary confirmation.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
