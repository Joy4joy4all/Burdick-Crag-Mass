# -*- coding: utf-8 -*-
"""
BCM_v28_TEST27_CRAG_PHASE_STATE_CLASSIFIER.py

Hypothesis: H_V29_CRAG_PHASE_STATE

Statement
---------
Crags exist in phase states. Some primordial tares are still shearing
outward from the Bang-type rip, while others are exhausted and drawing
galaxies back toward the root. The observed peculiar velocity sign is a
first-order phase indicator. The full phase state requires four inputs:
crag capacity (C_I), substrate dependency (sub_frac), kinematic direction
(V_pec sign), and primordial scar alignment (A_CMB_full).

This is the synthesis test — all prior outputs from Tests 20-26 feed
a single unified classifier.

Phase state definitions (SJB 2026-05-11)
-----------------------------------------
ACTIVE_SHEAR_CRAG   : HIGH C_I + V_pec > 0
    Tare still propagating. Bang rip still pushing outward.
    Strong pump capacity (ROOT tier). Inter-crag shear channel active.

RETURNING_ROOT_CRAG : HIGH C_I + V_pec < 0
    Tare exhausting. ROOT crag drawing galaxies back toward node.
    Pump capacity high but tare is in return / draw phase.

DEPENDENT_BRANCH    : BRANCH/LEAF tier + HIGH sub_frac
    Primary substrate recipient. Close to ROOT in draw network.
    Most vulnerable to cascade loss when ROOT goes dark.

DRY_VOID_EDGE       : VOID-EDGE tier or LOW sub_frac past tare reach
    Disconnected. Tare depleted. Minimal substrate delivery.
    Last by delay in cascade (not because strong — because irrelevant).

CLUSTER_CONTAMINATED: V_pec signal dominated by cluster dynamics
    Cannot classify by primordial crag topology from V_pec alone.
    Requires Planck A_CMB only (kinematic proxy invalid).

Composite metrics (SJB 2026-05-11)
-----------------------------------
rip_energy_proxy    = C_I × (|V_pec| / V_SCALE) × (1 + |A_CMB_full|)
return_draw_proxy   = sub_frac × max(0, -sign(V_pec)) × (|V_pec| / V_SCALE)
shear_expansion_proxy = max(0, V_pec) / V_SCALE × (1 + |A_CMB_v3k|)
drying_index        = proxy_distance / (sub_frac + EPS)

Data sources (declared)
------------------------
C_I             : computed from Vmax (same formula as Tests 20-24)
A_CMB_planck    : real Planck nside=64 pixels (Test 22 JSON) or embedded fallback
A_CMB_v3k       : -tanh(V_pec / 500) (Test 21 convention)
A_CMB_full      : 0.60 × A_planck + 0.40 × A_v3k (w_t=0.60 LOCKED Test 23)
sub_frac        : tier-mean proxy from Test 24 (declared — PHANGS set lacks
                  BCM solver RMS output; real sub_frac pending SPARC extension)
proxy_distance  : log10(C_I_ROOT / C_I_galaxy) from ROOT pool (Test 25)

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

BATCH_JSON     = os.path.join(_DATA_RESULTS, "batch_20260327_140314.json")
BATCH_JSON_ALT = os.path.join(_SOLVER_ROOT,  "batch_20260327_140314.json")
PLANCK_JSON    = os.path.join(_SOLVER_ROOT, "data", "planck_map_CMB",
                              "bcm_planck_galaxy_pixels.json")

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST27_CRAG_PHASE_STATE_CLASSIFIER"
TEST_NUMBER = 27
HYP_ID      = "H_V29_CRAG_PHASE_STATE"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT  = 5.0e-4
J_REF       = 8.0
VMAX_REF    = 206.0
N_HALF      = 60
CI_ROOT     = 1.0e-1
CI_BRANCH   = 1.0e-2
CI_LEAF     = 1.0e-3
H0          = 70.0
V_SCALE     = 500.0
T_RMS_UK    = 70.0
W_T         = 0.60      # LOCKED Test 23
W_K         = 0.40      # LOCKED Test 23
C_NETWORK   = 1.0       # unfrozen (Test 25)
D_UNIT      = 1.0       # unfrozen (Test 25)
EPS         = 1.0e-12

# Test 24 tier-mean substrate fractions (declared proxy for PHANGS set)
TIER_SUB_FRAC = {
    "ROOT":      0.111,
    "BRANCH":    0.433,
    "LEAF":      0.459,
    "VOID-EDGE": 0.276,
}

# Phase classification thresholds
HIGH_CI_THRESHOLD  = CI_ROOT     # C_I > 0.1 = ROOT tier
HIGH_SF_THRESHOLD  = 0.30        # sub_frac > 0.30 = dependent

# Cluster members — kinematic proxy invalid
CLUSTER_MEMBERS = {"NGC 4254", "NGC 4321"}

# ============================================================================
# 20-GALAXY V_3K CATALOG (Test 21 source, SJB 2026-05-09)
# (name, vmax, j_amp_override, v_3k, d_mpc, dT_fallback_uK)
# ============================================================================
CATALOG = [
    ("NGC 5055",  206.0,  8.0,   654,   8.0,  +40),
    ("NGC 7496",  169.0,  7.0,  1404,  18.7,  -10),
    ("IC 5332",   119.0,  3.5,   455,   9.0,  -65),
    ("NGC 3137",  160.0, None,  1329,  19.0,  -66),
    ("NGC 3175",  185.0, None,  1328,  19.0,  -48),
    ("NGC 628",   217.0, None,   426,   9.8,  +32),
    ("NGC 1087",  136.0, None,  1357,  15.9,  -38),
    ("NGC 1300",  195.0, None,  1415,  19.0, +100),
    ("NGC 1365",  285.0, None,  1478,  18.1,  +71),
    ("NGC 1385",  140.0, None,  1335,  18.2,  +18),
    ("NGC 1433",  190.0, None,   915,   9.7,  -26),
    ("NGC 1566",  210.0, None,  1346,  17.7,  -19),
    ("NGC 1672",  230.0, None,  1175,  11.9,   +9),
    ("NGC 2835",  155.0, None,  1106,  12.2,  -30),
    ("NGC 3351",  192.0, None,  1075,   9.96, -18),
    ("NGC 3627",  215.0, None,  1027,  11.3,  +49),
    ("NGC 4254",  220.0, None,  2702,  13.1,  +17),
    ("NGC 4321",  230.0, None,  1856,  15.2, +127),
    ("NGC 5068",   95.0, None,   958,   5.2,  -34),
    ("M74",       217.0, None,   426,   9.8,  +32),
]


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax, override=None):
    if override is not None:
        return float(override)
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_ci(j_amp):
    return j_amp * float(SIGMA_CRIT * (j_amp / J_REF) * N_HALF)


def classify_tier(ci):
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def compute_vpec(v3k, d):
    return float(v3k - H0 * d)


def a_v3k_fn(vpec):
    return float(-np.tanh(vpec / V_SCALE))


def a_planck_fn(dT):
    return float(np.tanh(dT / T_RMS_UK))


def a_full_fn(ap, av):
    return float(W_T * ap + W_K * av)


def classify_alignment(a):
    if a < -0.7:  return "SUPER_GUTTER"
    if a >  0.7:  return "CROSS_SCAR"
    if -0.3 <= a <= 0.3: return "NEUTRAL"
    return "WEAK_GUTTER" if a < 0 else "WEAK_CROSS"


def proxy_dist_fn(ci_g, ci_r):
    return float(max(0.0, np.log10((ci_r + EPS) / (ci_g + EPS))) * D_UNIT)


def classify_phase(tier, v_pec, sub_frac, is_cluster):
    """
    Primary phase state classifier.
    """
    if is_cluster:
        return "CLUSTER_CONTAMINATED"
    if tier == "ROOT":
        return "ACTIVE_SHEAR_CRAG" if v_pec > 0 else "RETURNING_ROOT_CRAG"
    if tier in ("BRANCH", "LEAF") and sub_frac >= HIGH_SF_THRESHOLD:
        return "DEPENDENT_BRANCH"
    if tier == "VOID-EDGE" or sub_frac < 0.10:
        return "DRY_VOID_EDGE"
    # BRANCH/LEAF with low sub_frac — transitional
    return "DEPENDENT_BRANCH" if v_pec < 0 else "ACTIVE_SHEAR_CRAG"


def rip_energy(ci, vpec, a_cmb_full):
    return float(ci * (abs(vpec) / V_SCALE) * (1.0 + abs(a_cmb_full)))


def return_draw(sub_frac, vpec):
    """Positive = being drawn toward ROOT. Zero for outflow galaxies."""
    return float(sub_frac * max(0.0, -np.sign(vpec)) * (abs(vpec) / V_SCALE))


def shear_expansion(vpec, a_cmb_v3k):
    """Positive = still shearing outward. Zero for infalling galaxies."""
    return float(max(0.0, vpec) / V_SCALE * (1.0 + abs(a_cmb_v3k)))


def drying_index(proxy_d, sub_frac):
    """High = far from ROOT with depleted funding = most dried out."""
    return float(proxy_d / (sub_frac + EPS))


def spearman(a, b):
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

    # ------------------------------------------------------------------
    # LOAD ROOT POOL
    # ------------------------------------------------------------------
    batch_path = None
    for p in [BATCH_JSON, BATCH_JSON_ALT]:
        if os.path.isfile(p):
            batch_path = p
            break

    roots = []
    if batch_path:
        with open(batch_path, encoding="utf-8") as f:
            sparc_raw = json.load(f)
        for g in sparc_raw:
            j = compute_j_amp(g["v_max"])
            c = compute_ci(j)
            if c > CI_ROOT:
                roots.append({"name": g["galaxy"], "ci": c})
        roots.sort(key=lambda x: x["ci"], reverse=True)
    else:
        # Minimal fallback: embed apex only
        roots = [{"name": "UGC02487", "ci": 2.8677}]

    root_cis  = np.array([r["ci"] for r in roots])
    apex_name = roots[0]["name"]
    apex_ci   = roots[0]["ci"]

    # ------------------------------------------------------------------
    # LOAD PLANCK CACHE
    # ------------------------------------------------------------------
    planck_cache = {}
    if os.path.isfile(PLANCK_JSON):
        with open(PLANCK_JSON, encoding="utf-8") as f:
            pdata = json.load(f)
        planck_cache = {r["name"]: float(r["delta_T_uK"])
                        for r in pdata["extracted"]}
    planck_source = "real nside=64" if planck_cache else "embedded fallback"

    print("=" * 108)
    print(f"BCM v28 TEST {TEST_NUMBER} — CRAG PHASE STATE CLASSIFIER")
    print(f"Hypothesis : {HYP_ID}")
    print(f"Synthesis  : Tests 20 (C_I) + 22 (A_planck) + 23 (w_t locked) + "
          f"24 (sub_frac proxy) + 25 (proxy_d) + 26 (V_pec)")
    print(f"A_CMB_full : {W_T}×A_planck + {W_K}×A_v3k  (LOCKED Test 23)")
    print(f"ROOT pool  : {len(roots)} SPARC galaxies  (apex={apex_name})")
    print(f"Planck     : {planck_source}")
    print("=" * 108)

    # ------------------------------------------------------------------
    # BUILD GALAXY RECORDS
    # ------------------------------------------------------------------
    galaxies = []
    for row in CATALOG:
        name, vmax, j_ov, v3k, d_mpc, dT_fb = row

        j_amp  = compute_j_amp(vmax, j_ov)
        ci     = compute_ci(j_amp)
        tier   = classify_tier(ci)
        vpec   = compute_vpec(v3k, d_mpc)
        av     = a_v3k_fn(vpec)
        dT     = float(planck_cache.get(name, dT_fb))
        ap     = a_planck_fn(dT)
        af     = a_full_fn(ap, av)
        sf     = TIER_SUB_FRAC[tier]   # Test 24 tier-mean proxy

        # Nearest ROOT
        log_ci   = np.log10(ci + EPS)
        log_rcis = np.log10(root_cis + EPS)
        nr       = roots[int(np.argmin(np.abs(log_rcis - log_ci)))]
        d        = proxy_dist_fn(ci, nr["ci"])

        is_clus  = name in CLUSTER_MEMBERS
        phase    = classify_phase(tier, vpec, sf, is_clus)

        rip_e    = rip_energy(ci, vpec, af)
        ret_d    = return_draw(sf, vpec)
        shear_e  = shear_expansion(vpec, av)
        dry_i    = drying_index(d, sf)

        galaxies.append({
            "name":              name,
            "vmax":              vmax,
            "ci":                ci,
            "tier":              tier,
            "v_pec":             vpec,
            "infall":            vpec < 0,
            "a_cmb_v3k":         av,
            "a_cmb_planck":      ap,
            "a_cmb_full":        af,
            "alignment_class":   classify_alignment(af),
            "dT_uK":             dT,
            "sub_frac_proxy":    sf,
            "proxy_distance":    d,
            "nearest_root":      nr["name"],
            "is_cluster":        is_clus,
            "crag_phase_state":  phase,
            "rip_energy_proxy":  rip_e,
            "return_draw_proxy": ret_d,
            "shear_expansion_proxy": shear_e,
            "drying_index":      dry_i,
        })

    # ------------------------------------------------------------------
    # MAIN TABLE
    # ------------------------------------------------------------------
    print()
    print(
        f"  {'GALAXY':<14} {'TIER':<10} {'V_pec':>8} "
        f"{'A_full':>7} {'sf_proxy':>9} {'rip_E':>10} "
        f"{'ret_D':>8} {'shear':>8} {'dry_I':>8} "
        f"{'PHASE_STATE'}"
    )
    print("  " + "-" * 108)
    for g in sorted(galaxies, key=lambda x: x["rip_energy_proxy"], reverse=True):
        print(
            f"  {g['name']:<14} {g['tier']:<10} {g['v_pec']:>8.0f} "
            f"{g['a_cmb_full']:>7.3f} {g['sub_frac_proxy']:>9.4f} "
            f"{g['rip_energy_proxy']:>10.4e} "
            f"{g['return_draw_proxy']:>8.4f} {g['shear_expansion_proxy']:>8.4f} "
            f"{g['drying_index']:>8.3f} "
            f"{g['crag_phase_state']}"
        )

    # ------------------------------------------------------------------
    # PHASE STATE DISTRIBUTION
    # ------------------------------------------------------------------
    from collections import Counter, defaultdict
    phase_dist = Counter(g["crag_phase_state"] for g in galaxies)

    print()
    print("PHASE STATE DISTRIBUTION")
    print(f"  {'PHASE_STATE':<26} {'N':>4} {'mean_rip_E':>12} "
          f"{'mean_ret_D':>11} {'mean_shear':>11} {'mean_dry_I':>11}")
    print("  " + "-" * 80)
    phase_groups = defaultdict(list)
    for g in galaxies:
        phase_groups[g["crag_phase_state"]].append(g)

    phase_order = ["ACTIVE_SHEAR_CRAG", "RETURNING_ROOT_CRAG",
                   "DEPENDENT_BRANCH", "DRY_VOID_EDGE", "CLUSTER_CONTAMINATED"]
    for ph in phase_order:
        gs = phase_groups[ph]
        if not gs:
            continue
        print(
            f"  {ph:<26} {len(gs):>4} "
            f"{np.mean([g['rip_energy_proxy'] for g in gs]):>12.4e} "
            f"{np.mean([g['return_draw_proxy'] for g in gs]):>11.4f} "
            f"{np.mean([g['shear_expansion_proxy'] for g in gs]):>11.4f} "
            f"{np.mean([g['drying_index'] for g in gs]):>11.3f}"
        )

    # ------------------------------------------------------------------
    # 2×2 GRID: C_I level × V_pec sign (non-cluster only)
    # ------------------------------------------------------------------
    nc = [g for g in galaxies if not g["is_cluster"]]
    high_ci_out = [g for g in nc if g["tier"] == "ROOT" and not g["infall"]]
    high_ci_in  = [g for g in nc if g["tier"] == "ROOT" and g["infall"]]
    low_ci_out  = [g for g in nc if g["tier"] != "ROOT" and not g["infall"]]
    low_ci_in   = [g for g in nc if g["tier"] != "ROOT" and g["infall"]]

    print()
    print("2×2 PHASE GRID (non-cluster galaxies)")
    print(f"                       V_pec > 0 (outflow)     V_pec < 0 (infall)")
    print(f"  HIGH C_I (ROOT) :  "
          f"{[g['name'] for g in high_ci_out]}  →  ACTIVE_SHEAR")
    print(f"                     "
          f"{[g['name'] for g in high_ci_in]}  →  RETURNING_ROOT")
    print(f"  LOW C_I (BR/LF) :  "
          f"{[g['name'] for g in low_ci_out]}")
    print(f"                     "
          f"{[g['name'] for g in low_ci_in]}")

    # ------------------------------------------------------------------
    # RANKING TABLES
    # ------------------------------------------------------------------
    print()
    print("TOP 5 BY RIP ENERGY (highest primordial rip intensity)")
    for i, g in enumerate(sorted(galaxies, key=lambda x: x["rip_energy_proxy"],
                                  reverse=True)[:5]):
        print(f"  {i+1}. {g['name']:<14} rip_E={g['rip_energy_proxy']:.4e}  "
              f"{g['crag_phase_state']}")

    print()
    print("TOP 5 BY RETURN DRAW (most strongly in crag-return phase)")
    for i, g in enumerate(sorted(galaxies, key=lambda x: x["return_draw_proxy"],
                                  reverse=True)[:5]):
        print(f"  {i+1}. {g['name']:<14} ret_D={g['return_draw_proxy']:.4f}  "
              f"V_pec={g['v_pec']:.0f}  {g['crag_phase_state']}")

    print()
    print("TOP 5 BY DRYING INDEX (most depleted, past tare reach)")
    for i, g in enumerate(sorted(galaxies, key=lambda x: x["drying_index"],
                                  reverse=True)[:5]):
        print(f"  {i+1}. {g['name']:<14} dry_I={g['drying_index']:.3f}  "
              f"tier={g['tier']}  sub_frac={g['sub_frac_proxy']:.3f}  "
              f"{g['crag_phase_state']}")

    # ------------------------------------------------------------------
    # CORRELATIONS
    # ------------------------------------------------------------------
    rip_vals  = [g["rip_energy_proxy"]      for g in galaxies]
    ci_vals   = [g["ci"]                    for g in galaxies]
    vpec_vals = [g["v_pec"]                 for g in galaxies]
    af_vals   = [abs(g["a_cmb_full"])       for g in galaxies]

    rho_rip_ci   = spearman(rip_vals, ci_vals)
    rho_rip_vpec = spearman(rip_vals, [abs(v) for v in vpec_vals])
    rho_rip_af   = spearman(rip_vals, af_vals)

    # coherence: do phase states separate meaningfully on rip_energy?
    active_rip = [g["rip_energy_proxy"] for g in galaxies
                  if g["crag_phase_state"] == "ACTIVE_SHEAR_CRAG"]
    return_rip = [g["rip_energy_proxy"] for g in galaxies
                  if g["crag_phase_state"] == "RETURNING_ROOT_CRAG"]
    phases_separate = (
        len(active_rip) > 0 and len(return_rip) > 0 and
        np.mean(active_rip) != np.mean(return_rip)
    )

    print()
    print("=" * 108)
    print("CORRELATION SUMMARY")
    print(f"  Rank corr (rip_E vs C_I)          : {rho_rip_ci:+.4f}")
    print(f"  Rank corr (rip_E vs |V_pec|)       : {rho_rip_vpec:+.4f}")
    print(f"  Rank corr (rip_E vs |A_CMB_full|)  : {rho_rip_af:+.4f}")
    if active_rip and return_rip:
        print(f"  Mean rip_E ACTIVE_SHEAR     : {np.mean(active_rip):.4e}")
        print(f"  Mean rip_E RETURNING_ROOT   : {np.mean(return_rip):.4e}")
        print(f"  Phases separate on rip_E    : {phases_separate}")
    print(f"  Phase distribution          : {dict(phase_dist)}")
    print("=" * 108)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    coherence_score  = 1.0 if phases_separate else 0.5
    overlap_fraction = float(max(0, rho_rip_ci))

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"Crag phase state classifier over {len(galaxies)}-galaxy "
        f"PHANGS-JWST + BCM V_3K set. "
        f"Synthesis of Tests 20 (C_I), 22 (A_planck), 23 (w_t=0.60 locked), "
        f"24 (sub_frac proxy), 25 (proxy_d), 26 (V_pec). "
        f"Phase states: {dict(phase_dist)}. "
        f"rip_energy = C_I × (|V_pec|/500) × (1 + |A_CMB_full|). "
        f"Rank corr rip_E vs C_I: {rho_rip_ci:+.4f}. "
        f"Rank corr rip_E vs |V_pec|: {rho_rip_vpec:+.4f}. "
        f"Phases separate on rip_E: {phases_separate}. "
        f"sub_frac is tier-mean proxy from Test 24 (PHANGS lacks BCM RMS data). "
        f"coherence_score={coherence_score:.4f}, overlap_fraction={overlap_fraction:.4f}. "
        f"A_CMB locked: {W_T}×A_planck + {W_K}×A_v3k. "
        f"Planck source: {planck_source}."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if phases_separate else 0,
        "evidence_type": "primary",
        "pass_count":    int(phases_separate),
        "total_configs": len(galaxies),
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":          coherence_score,
            "overlap_fraction":         overlap_fraction,
            "n_galaxies":               len(galaxies),
            "phase_distribution":       dict(phase_dist),
            "rho_rip_vs_ci":            rho_rip_ci,
            "rho_rip_vs_vpec":          rho_rip_vpec,
            "rho_rip_vs_acmb":          rho_rip_af,
            "phases_separate_rip":      phases_separate,
            "mean_rip_active":          float(np.mean(active_rip)) if active_rip else 0.0,
            "mean_rip_returning":       float(np.mean(return_rip)) if return_rip else 0.0,
            "w_t_locked":               W_T,
            "w_k_locked":               W_K,
            "root_pool_size":           len(roots),
            "apex_galaxy":              apex_name,
            "planck_source":            planck_source,
            "sub_frac_note":            "Tier-mean proxy from Test 24. PHANGS set lacks BCM RMS output.",
            "formula_rip_energy":       "C_I × (|V_pec|/V_SCALE) × (1 + |A_CMB_full|)",
            "formula_return_draw":      "sub_frac × max(0, -sign(V_pec)) × (|V_pec|/V_SCALE)",
            "formula_shear_expansion":  "max(0, V_pec)/V_SCALE × (1 + |A_CMB_v3k|)",
            "formula_drying_index":     "proxy_distance / (sub_frac + EPS)",
        },
        "context": {
            "framework":   "crag_phase_state_classifier",
            "synthesis":   "Tests 20-26 all feed this classifier.",
            "data_sources": (
                "C_I from Vmax (inline). A_CMB_planck from Planck JSON (Test 22). "
                "A_CMB_v3k from V_3K (Test 21). A_CMB_full w_t=0.60 (locked Test 23). "
                "sub_frac tier proxy from Test 24. proxy_d log-C_I (Test 25). "
                "V_pec from V_3K - H0×d (Test 26)."
            ),
            "next_step": (
                "Extend to full 175 SPARC with real sub_frac from Test 24 "
                "and systemic velocities from NED/Cosmicflows-4. "
                "Replace proxy_distance with real 3D Mpc. "
                "Calibrate C_network, D_unit from observed group kinematics. "
                "This is the 17D root-ball logic starting to form (SJB 2026-05-11)."
            ),
        },
        "keywords": [
            "primordial_gutter",
            "crag_intensity",
            "cmb_prestrain",
            "a_cmb",
            "primordial_routing",
            "cascade_propagation",
            "cascade_score",
            "substrate_funding_fraction",
            "infall_crag_return",
            "dual_flow_crag",
            "tier_flip",
            "super_gutter",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "CRAG_PHASE_STATE_20_GALAXY_SYNTHESIS",
        "framework":         "crag_phase_state_classifier",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "galaxy_table":      sorted(galaxies,
                                    key=lambda x: x["rip_energy_proxy"],
                                    reverse=True),
        "phase_groups": {
            ph: [g["name"] for g in phase_groups[ph]]
            for ph in phase_order if phase_groups[ph]
        },
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Corrected crag law (SJB 2026-05-11):")
    print("  Crag phase = f(capacity, dependency, direction, primordial alignment)")
    print("  rip_energy = C_I × (|V_pec|/500) × (1 + |A_CMB_full|)")
    print("  This is the 17D root-ball logic starting to form.")
    print()
    print("Ingest sequence:")
    print("  Tests 19-23 → READY NOW (vocab locked 114)")
    print("  Tests 24-27 → READY after vocab update (vocab now 121)")
    print("  EPIC COLLECTOR → all 9 tests → INGEST → AUTO-10")

    return 0


if __name__ == "__main__":
    sys.exit(main())
