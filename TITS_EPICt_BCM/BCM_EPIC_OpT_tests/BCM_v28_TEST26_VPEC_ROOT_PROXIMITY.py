# -*- coding: utf-8 -*-
"""
BCM_v28_TEST26_VPEC_ROOT_PROXIMITY.py

Hypothesis: H_V29_INFALL_AS_CRAG_RETURN

Statement
---------
Galaxies with negative peculiar velocity (infalling relative to Hubble
flow) are on crag-return trajectories toward the nearest ROOT draw node.
Galaxies with positive peculiar velocity (outflowing) are in inter-crag
void channels riding the expansion pressure between crags.

If the crag-return interpretation is correct:
    V_pec < 0  (infall)  → short proxy_distance to nearest ROOT
                          → higher cascade_score (closer to draw zone)
    V_pec > 0  (outflow) → long proxy_distance or VOID-EDGE classification
                          → lower cascade_score (inter-crag gutter channel)

Data sources
------------
    ROOT pool  : 53 ROOT-tier galaxies from SPARC batch (Test 25 source)
                 These define the backbone of the crag draw network.
    V_3K set   : 20 galaxies with real CMB-frame velocities (Test 21 source)
                 These are the PHANGS-JWST survey set — different from SPARC.
                 For each, cascade metrics are computed using the ROOT pool
                 as the network reference frame.

V_pec = V_3K - H0 × d_mpc    (H0 = 70 km/s/Mpc)
A_CMB_v3k = -tanh(V_pec / 500)   (from Test 21 convention)

Key prediction
--------------
Rank correlation: V_pec vs proxy_distance should be POSITIVE.
    V_pec < 0 (infall) → short proxy_distance → closer to ROOT
    V_pec > 0 (outflow) → long proxy_distance → farther from ROOT

The Virgo cluster members (NGC 4254, NGC 4321) are expected exceptions:
their V_pec is cluster-dynamics-driven, not primordial crag topology.

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

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST26_VPEC_ROOT_PROXIMITY"
TEST_NUMBER = 26
HYP_ID      = "H_V29_INFALL_AS_CRAG_RETURN"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT     = 5.0e-4
J_REF          = 8.0
VMAX_REF       = 206.0
N_HALF         = 60
LAMBDA         = 0.1
KILL_THRESHOLD = 0.15
T_SURVIVAL     = float(-np.log(KILL_THRESHOLD) / 0.1)   # 18.97

CI_ROOT        = 1.0e-1
CI_BRANCH      = 1.0e-2
CI_LEAF        = 1.0e-3

H0             = 70.0     # km/s/Mpc
V_SCALE        = 500.0    # V_pec normalization (km/s)
T_RMS_UK       = 70.0     # Planck SMICA RMS (μK)
C_NETWORK      = 1.0      # unfrozen (from Test 25)
D_UNIT         = 1.0      # unfrozen (from Test 25)
EPS            = 1.0e-12

# Cluster membership flag — expected exceptions to infall=crag-return
CLUSTER_MEMBERS = {"NGC 4254", "NGC 4321"}   # Virgo cluster dynamics

# ============================================================================
# V_3K CATALOG (from Test 21 — SJB provided 2026-05-09)
# (name, ra_deg, dec_deg, vmax_kms, j_amp_override, v_3k, d_mpc, dT_planck_uK)
# dT_planck from bcm_planck_galaxy_pixels.json (Test 22)
# ============================================================================
V3K_CATALOG = [
    ("NGC 5055",  198.96, +42.03, 206.0,  8.0,   654,   8.0,  +40),
    ("NGC 7496",  347.45, -43.43, 169.0,  7.0,  1404,  18.7,  -10),
    ("IC 5332",   350.85, -36.10, 119.0,  3.5,   455,   9.0,  -65),
    ("NGC 3137",  151.57, -29.00, 160.0, None,  1329,  19.0,  -66),
    ("NGC 3175",  153.35, -28.87, 185.0, None,  1328,  19.0,  -48),
    ("NGC 628",    24.17, +15.78, 217.0, None,   426,   9.8,  +32),
    ("NGC 1087",   41.51,  -0.50, 136.0, None,  1357,  15.9,  -38),
    ("NGC 1300",   49.92, -19.41, 195.0, None,  1415,  19.0, +100),
    ("NGC 1365",   53.40, -36.14, 285.0, None,  1478,  18.1,  +71),
    ("NGC 1385",   54.37, -24.50, 140.0, None,  1335,  18.2,  +18),
    ("NGC 1433",   55.51, -47.22, 190.0, None,   915,   9.7,  -26),
    ("NGC 1566",   65.00, -54.94, 210.0, None,  1346,  17.7,  -19),
    ("NGC 1672",   71.43, -59.25, 230.0, None,  1175,  11.9,   +9),
    ("NGC 2835",  139.47, -22.35, 155.0, None,  1106,  12.2,  -30),
    ("NGC 3351",  160.99, +11.70, 192.0, None,  1075,   9.96, -18),
    ("NGC 3627",  170.06, +12.99, 215.0, None,  1027,  11.3,  +49),
    ("NGC 4254",  184.71, +14.42, 220.0, None,  2702,  13.1,  +17),
    ("NGC 4321",  185.73, +15.82, 230.0, None,  1856,  15.2, +127),
    ("NGC 5068",  199.73, -21.04,  95.0, None,   958,   5.2,  -34),
    ("M74",        24.17, +15.78, 217.0, None,   426,   9.8,  +32),
]

# Try loading real Planck pixels if available
_PLANCK_JSON = os.path.join(_SOLVER_ROOT, "data", "planck_map_CMB",
                            "bcm_planck_galaxy_pixels.json")


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax, override=None):
    if override is not None:
        return float(override)
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_ci(j_amp):
    return j_amp * float(SIGMA_CRIT * (j_amp / J_REF) * N_HALF)


def classify_crag(ci):
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def proxy_dist(ci_galaxy, ci_root):
    if ci_root <= 0 or ci_galaxy <= 0:
        return 0.0
    return float(max(0.0, np.log10((ci_root + EPS) / (ci_galaxy + EPS))) * D_UNIT)


def cascade_s(sub_frac_val, d):
    return float(sub_frac_val * np.exp(-d / C_NETWORK))


def compute_vpec(v3k, d_mpc):
    return float(v3k - H0 * d_mpc)


def compute_a_v3k(vpec):
    return float(-np.tanh(vpec / V_SCALE))


def compute_a_planck(dT_uK):
    return float(np.tanh(dT_uK / T_RMS_UK))


def classify_alignment(a):
    if a < -0.7:  return "SUPER_GUTTER"
    if a >  0.7:  return "CROSS_SCAR"
    if -0.3 <= a <= 0.3: return "NEUTRAL"
    return "WEAK_GUTTER" if a < 0 else "WEAK_CROSS"


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
    # LOAD ROOT POOL FROM SPARC BATCH
    # ------------------------------------------------------------------
    batch_path = None
    for p in [BATCH_JSON, BATCH_JSON_ALT]:
        if os.path.isfile(p):
            batch_path = p
            break
    if batch_path is None:
        print("ERROR: SPARC batch JSON not found.")
        return 1

    with open(batch_path, encoding="utf-8") as f:
        sparc_raw = json.load(f)

    roots = []
    for g in sparc_raw:
        j  = compute_j_amp(g["v_max"])
        ci = compute_ci(j)
        if ci > CI_ROOT:
            roots.append({"name": g["galaxy"], "vmax": g["v_max"], "ci": ci})
    roots.sort(key=lambda x: x["ci"], reverse=True)
    root_cis  = np.array([r["ci"]  for r in roots])
    apex_ci   = roots[0]["ci"]
    apex_name = roots[0]["name"]

    # Load Planck pixel cache if available
    planck_cache = {}
    if os.path.isfile(_PLANCK_JSON):
        with open(_PLANCK_JSON, encoding="utf-8") as f:
            pdata = json.load(f)
        planck_cache = {r["name"]: float(r["delta_T_uK"])
                        for r in pdata["extracted"]}

    print("=" * 108)
    print(f"BCM v28 TEST {TEST_NUMBER} — V_PECULIAR SIGN vs ROOT PROXIMITY")
    print(f"Hypothesis : {HYP_ID}")
    print(f"ROOT pool  : {len(roots)} galaxies from SPARC (apex={apex_name}, "
          f"C_I={apex_ci:.4e})")
    print(f"V_3K set   : {len(V3K_CATALOG)} galaxies (PHANGS-JWST + BCM corpus)")
    print(f"Planck cache: {'YES' if planck_cache else 'NO (using embedded fallback)'}")
    print("=" * 108)

    # ------------------------------------------------------------------
    # BUILD GALAXY RECORDS
    # ------------------------------------------------------------------
    galaxies = []
    for row in V3K_CATALOG:
        name, ra, dec, vmax, j_ov, v3k, d_mpc, dT_fb = row

        j_amp   = compute_j_amp(vmax, j_ov)
        ci      = compute_ci(j_amp)
        tier    = classify_crag(ci)

        v_pec   = compute_vpec(v3k, d_mpc)
        a_v3k   = compute_a_v3k(v_pec)
        infall  = v_pec < 0   # True = infalling toward attractor

        dT      = float(planck_cache.get(name, dT_fb))
        a_plan  = compute_a_planck(dT)

        # Find nearest ROOT in log(C_I) space
        log_ci   = np.log10(ci + EPS)
        log_rcis = np.log10(root_cis + EPS)
        nr_idx   = int(np.argmin(np.abs(log_rcis - log_ci)))
        nr       = roots[nr_idx]

        d    = proxy_dist(ci, nr["ci"])
        scor = cascade_s(abs(a_v3k), d)   # use |A_CMB_v3k| as kinematic sub-frac proxy
        t_del = T_SURVIVAL + d / C_NETWORK

        is_cluster = name in CLUSTER_MEMBERS

        galaxies.append({
            "name":             name,
            "vmax":             vmax,
            "ci":               ci,
            "tier":             tier,
            "v_3k":             v3k,
            "d_mpc":            d_mpc,
            "v_pec":            v_pec,
            "infall":           infall,
            "a_cmb_v3k":        a_v3k,
            "a_cmb_planck":     a_plan,
            "v3k_class":        classify_alignment(a_v3k),
            "planck_class":     classify_alignment(a_plan),
            "nearest_root":     nr["name"],
            "nearest_root_ci":  nr["ci"],
            "proxy_distance":   d,
            "cascade_score":    scor,
            "predicted_delay":  t_del,
            "is_cluster":       is_cluster,
            "dT_uK":            dT,
        })

    # ------------------------------------------------------------------
    # PRINT TABLE
    # ------------------------------------------------------------------
    print()
    print(
        f"  {'GALAXY':<14} {'TIER':<10} {'V_pec':>8} "
        f"{'INFALL':>7} {'A_v3k':>7} {'d_net':>7} "
        f"{'score':>10} {'v3k_class':<16} {'CLUSTER?'}"
    )
    print("  " + "-" * 90)
    for g in sorted(galaxies, key=lambda x: x["v_pec"]):
        print(
            f"  {g['name']:<14} {g['tier']:<10} {g['v_pec']:>8.0f} "
            f"{'YES' if g['infall'] else 'NO':>7} {g['a_cmb_v3k']:>7.3f} "
            f"{g['proxy_distance']:>7.3f} {g['cascade_score']:>10.4e} "
            f"{g['v3k_class']:<16} {'CLUSTER' if g['is_cluster'] else ''}"
        )

    # ------------------------------------------------------------------
    # SPLIT: INFALL vs OUTFLOW
    # ------------------------------------------------------------------
    infall_g  = [g for g in galaxies if g["infall"] and not g["is_cluster"]]
    outflow_g = [g for g in galaxies if not g["infall"] and not g["is_cluster"]]
    cluster_g = [g for g in galaxies if g["is_cluster"]]

    def group_stats(gs, label):
        if not gs:
            return
        d_vals = [g["proxy_distance"] for g in gs]
        s_vals = [g["cascade_score"]  for g in gs]
        v_vals = [g["v_pec"]          for g in gs]
        print(f"\n  {label} (N={len(gs)})")
        print(f"    mean_V_pec       : {np.mean(v_vals):+.0f} km/s")
        print(f"    mean_proxy_dist  : {np.mean(d_vals):.4f}")
        print(f"    mean_casc_score  : {np.mean(s_vals):.4e}")
        print(f"    mean_tier dist   : " +
              " | ".join(f"{g['name']}={g['tier']}" for g in gs))

    print("\nGROUP COMPARISON")
    group_stats(infall_g,  "INFALL (V_pec < 0, non-cluster)")
    group_stats(outflow_g, "OUTFLOW (V_pec > 0, non-cluster)")
    group_stats(cluster_g, "CLUSTER MEMBERS (kinematically contaminated)")

    # ------------------------------------------------------------------
    # CORRELATION ANALYSIS
    # ------------------------------------------------------------------
    # Primary: does V_pec correlate with proxy_distance?
    # Secondary: does |V_pec| correlate with cascade_score?
    all_vpec = np.array([g["v_pec"]          for g in galaxies])
    all_d    = np.array([g["proxy_distance"]  for g in galaxies])
    all_sc   = np.array([g["cascade_score"]   for g in galaxies])
    all_ci   = np.array([g["ci"]              for g in galaxies])

    rho_vpec_d  = spearman(all_vpec, all_d)
    rho_vpec_sc = spearman(all_vpec, all_sc)
    rho_vpec_ci = spearman(all_vpec, all_ci)

    # Without cluster members
    nc = [g for g in galaxies if not g["is_cluster"]]
    if nc:
        nc_vpec = np.array([g["v_pec"]         for g in nc])
        nc_d    = np.array([g["proxy_distance"] for g in nc])
        nc_sc   = np.array([g["cascade_score"]  for g in nc])
        rho_nc_vpec_d  = spearman(nc_vpec, nc_d)
        rho_nc_vpec_sc = spearman(nc_vpec, nc_sc)
    else:
        rho_nc_vpec_d = rho_nc_vpec_sc = 0.0

    # Infall vs outflow mean proxy distance comparison
    infall_d_mean  = float(np.mean([g["proxy_distance"] for g in infall_g])) if infall_g else 0.0
    outflow_d_mean = float(np.mean([g["proxy_distance"] for g in outflow_g])) if outflow_g else 0.0
    direction_confirmed = infall_d_mean < outflow_d_mean

    print()
    print("=" * 108)
    print("CORRELATION SUMMARY")
    print(f"  Rank corr V_pec vs proxy_distance (all 20)    : {rho_vpec_d:+.4f}")
    print(f"  Rank corr V_pec vs cascade_score  (all 20)    : {rho_vpec_sc:+.4f}")
    print(f"  Rank corr V_pec vs C_I            (all 20)    : {rho_vpec_ci:+.4f}")
    print(f"  Rank corr V_pec vs proxy_distance (ex cluster): {rho_nc_vpec_d:+.4f}")
    print(f"  Rank corr V_pec vs cascade_score  (ex cluster): {rho_nc_vpec_sc:+.4f}")
    print()
    print(f"  Mean proxy_distance — INFALL  (non-cluster): {infall_d_mean:.4f}")
    print(f"  Mean proxy_distance — OUTFLOW (non-cluster): {outflow_d_mean:.4f}")
    print(f"  Direction confirmed (infall < outflow d)    : {direction_confirmed}")
    print()
    infall_tiers  = [g["tier"] for g in infall_g]
    outflow_tiers = [g["tier"] for g in outflow_g]
    print(f"  Infall  tiers : {infall_tiers}")
    print(f"  Outflow tiers : {outflow_tiers}")
    print("=" * 108)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    coherence_score  = 1.0 if direction_confirmed else 0.0
    overlap_fraction = float(max(0.0, -rho_nc_vpec_d))  # positive if infall→short d

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"V_peculiar sign vs ROOT proximity over {len(galaxies)}-galaxy "
        f"PHANGS-JWST + BCM V_3K set. "
        f"ROOT pool: {len(roots)} SPARC ROOT galaxies (apex={apex_name}). "
        f"V_pec = V_3K - {H0}×d_mpc. "
        f"Proxy distance = log10(C_I_ROOT/C_I_galaxy). "
        f"Infall (V_pec<0, non-cluster): N={len(infall_g)}, "
        f"mean_d={infall_d_mean:.4f}. "
        f"Outflow (V_pec>0, non-cluster): N={len(outflow_g)}, "
        f"mean_d={outflow_d_mean:.4f}. "
        f"Direction confirmed (infall closer to ROOT): {direction_confirmed}. "
        f"Rank corr V_pec vs proxy_distance (ex cluster): {rho_nc_vpec_d:+.4f}. "
        f"Rank corr V_pec vs cascade_score (ex cluster): {rho_nc_vpec_sc:+.4f}. "
        f"Cluster members {list(CLUSTER_MEMBERS)} excluded from non-cluster stats. "
        f"coherence_score={coherence_score:.4f}, "
        f"overlap_fraction={overlap_fraction:.4f}. "
        f"Proxy distance upgrade to real 3D Mpc (NED/Cosmicflows-4) pending."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if direction_confirmed else 0,
        "evidence_type": "primary",
        "pass_count":    int(direction_confirmed),
        "total_configs": 2,   # infall vs outflow
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":              coherence_score,
            "overlap_fraction":             overlap_fraction,
            "n_galaxies":                   len(galaxies),
            "n_infall_non_cluster":         len(infall_g),
            "n_outflow_non_cluster":        len(outflow_g),
            "n_cluster":                    len(cluster_g),
            "mean_d_infall":                infall_d_mean,
            "mean_d_outflow":               outflow_d_mean,
            "direction_confirmed":          direction_confirmed,
            "rho_vpec_proxyD_all":          rho_vpec_d,
            "rho_vpec_proxyD_ex_cluster":   rho_nc_vpec_d,
            "rho_vpec_cascade_score_all":   rho_vpec_sc,
            "rho_vpec_cascade_ex_cluster":  rho_nc_vpec_sc,
            "rho_vpec_ci":                  rho_vpec_ci,
            "cluster_members_excluded":     list(CLUSTER_MEMBERS),
            "root_pool_size":               len(roots),
            "apex_galaxy":                  apex_name,
            "apex_ci":                      apex_ci,
            "c_network":                    C_NETWORK,
            "d_unit":                       D_UNIT,
            "proxy_note": (
                "Proxy distance = log10(C_I_ROOT/C_I_galaxy) in network hops. "
                "Upgrade to real 3D Mpc separation when NED/Cosmicflows-4 "
                "coordinates are available. C_network and D_unit remain unfrozen."
            ),
        },
        "context": {
            "framework":   "vpec_root_proximity",
            "data_source": "V_3K from NED/literature (SJB 2026-05-09) + SPARC ROOT pool",
            "infall_theory": (
                "SJB 2026-05-11: crag tares are draw structures. Galaxies "
                "near ROOT nodes may be on return trajectories (infall) "
                "rather than pure Hubble expansion. V_pec < 0 = crag-return. "
                "V_pec > 0 = inter-crag void channel (outflow, gutter). "
                "The dual-flow ROOT-ball: ROOT pumps outward to BRANCH/LEAF "
                "AND draws void substrate inward. The infall galaxies are "
                "in the draw zone of a ROOT crag."
            ),
            "cluster_note": (
                "NGC 4254 and NGC 4321 (Virgo cluster) are excluded from "
                "non-cluster statistics because their V_pec reflects cluster "
                "gravitational dynamics, not primordial crag topology. "
                "This was confirmed in Test 22: A_planck and A_v3k disagree "
                "maximally for these two galaxies."
            ),
            "next_step": (
                "Upgrade proxy distance to real 3D Mpc (NED/Cosmicflows-4). "
                "Test 27: full 175 SPARC + V_sys data → complete network map. "
                "Calibrate C_network and D_unit from observed group kinematics."
            ),
        },
        "keywords": [
            "primordial_gutter",
            "primordial_routing",
            "crag_intensity",
            "cmb_prestrain",
            "a_cmb",
            "super_gutter",
            "cross_scar",
            "tier_flip",
            "classifier",
            "gutter_depth",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "VPEC_ROOT_PROXIMITY_20_GALAXY",
        "framework":         "vpec_root_proximity",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "galaxy_table":      sorted(galaxies, key=lambda x: x["v_pec"]),
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("INGEST SEQUENCE (cube stops growing without these):")
    print("  READY NOW : Tests 19-23 (vocab locked, session complete)")
    print("  VOCAB FIRST: Tests 24, 25, 26 → vocabulary patch needed")
    print("    New terms: cascade_score, substrate_funding_fraction,")
    print("               intrinsic_battery, network_apex, dual_flow_crag,")
    print("               cascade_propagation, infall_crag_return")
    print()
    print("Next: vocabulary patch → ingest 24-26 → AUTO-10 → Test 27.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
