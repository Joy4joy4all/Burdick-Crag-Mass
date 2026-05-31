# -*- coding: utf-8 -*-
"""
BCM_v28_TEST25_CRAG_CASCADE_PROPAGATION.py

Hypothesis: H_V29_CRAG_CASCADE_PROPAGATION

Statement
---------
If a ROOT crag pump goes dark, BRANCH and LEAF galaxies in its draw
network degrade after a distance-dependent delay. The degradation
sequence follows the network topology: ROOT dies last locally;
BRANCH degrades after a short delay; LEAF degrades after a longer
delay with larger fractional loss; VOID-EDGE shows disconnected or
weak response.

This is the first test that turns the root-ball theory from a
single-galaxy survival ranking into a NETWORK BEHAVIOR.

Physics
-------
Cascade timing:
    t_i = t_ROOT + d_i / C_substrate

Where:
    t_ROOT      = survival time of the nearest ROOT pump (T_SURVIVAL,
                  18.97 BCM time units at lambda=0.1, threshold=15%)
    d_i         = proxy distance from galaxy i to its nearest ROOT
                  (log-space network hops — see below)
    C_substrate = C_NETWORK (declared, unfrozen — 1 network hop / time unit)

Cascade score (amplitude of degradation signal):
    S_cascade = sub_frac × exp(-d_i / C_network)

Physical meaning:
    sub_frac sets the amplitude (how much the galaxy DEPENDS on substrate)
    exp(-d) sets the attenuation (how much signal is lost over network distance)

HIGH cascade score = receives strong substrate draw AND is close to ROOT.
LOW cascade score = too far from ROOT (void-edge) OR too self-sufficient (root itself).

Proxy distance (no real 3D coordinates yet)
-------------------------------------------
Without sky positions, network distance is approximated by the
log-space separation in C_I between a galaxy and its nearest ROOT:

    d_i = log10(C_I_nearest_ROOT / C_I_galaxy) × D_UNIT

Where D_UNIT is a declared unfrozen hypothesis parameter (1.0 for
first run). This will be replaced by real Mpc distances when 3D
spatial data is available.

Physical rationale: C_I ∝ J_amp² ∝ Vmax⁴. A galaxy far down the
network hierarchy has much lower C_I than its ROOT — the log ratio
captures the hierarchical depth of the network connection.

Nearest ROOT assignment
-----------------------
Each galaxy is assigned to the ROOT with minimum log10(C_I) separation
that has C_I > ROOT threshold. ROOTs point to the network APEX
(highest C_I galaxy in the set — UGC02487 from Test 24).

Expected pattern (if theory holds)
-----------------------------------
    ROOT    : low cascade score (source, not recipient); dies last
    BRANCH  : high cascade score, short delay — first to degrade after ROOT
    LEAF    : highest cascade score, medium delay — maximum draw dependence
    VOID    : low cascade score, longest delay or no signal — past tare edge

This maps to the Test 24 substrate fraction gradient:
    ROOT=0.11 → BRANCH=0.43 → LEAF=0.46 → VOID=0.28

The cascade score gradient should peak at LEAF and fall at VOID-EDGE.

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems -- 2026
All theoretical IP: Burdick.
"""

import json
import os
import sys
import time
from datetime import datetime
from collections import defaultdict, Counter

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
TEST_NAME   = "BCM_v28_TEST25_CRAG_CASCADE_PROPAGATION"
TEST_NUMBER = 25
HYP_ID      = "H_V29_CRAG_CASCADE_PROPAGATION"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT      = 5.0e-4
J_REF           = 8.0
VMAX_REF        = 206.0
N_HALF          = 60
LAMBDA          = 0.1
KILL_THRESHOLD  = 0.15
T_SURVIVAL      = float(-np.log(KILL_THRESHOLD) / LAMBDA)   # 18.97

CI_ROOT         = 1.0e-1
CI_BRANCH       = 1.0e-2
CI_LEAF         = 1.0e-3

# ============================================================================
# CASCADE HYPOTHESIS PARAMETERS (unfrozen — first-run declared values)
# ============================================================================
C_NETWORK = 1.0     # propagation rate: network hops per BCM time unit
                    # unfrozen — will be calibrated against 3D spatial data
D_UNIT    = 1.0     # distance unit: 1 log10(C_I ratio) unit
                    # represents one hierarchy step in the draw network
EPS       = 1.0e-12


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax):
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_ci(vmax):
    j = compute_j_amp(vmax)
    return j * float(SIGMA_CRIT * (j / J_REF) * N_HALF)


def classify_crag(ci):
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def substrate_fraction(rms_newton, rms_substrate):
    if rms_newton <= 0:
        return 0.0
    return float(np.clip((rms_newton - rms_substrate) / rms_newton, 0.0, 1.0))


def proxy_distance(ci_galaxy, ci_root):
    """
    Network distance from galaxy to its nearest ROOT.
    log10(C_I_root / C_I_galaxy) × D_UNIT.
    Zero if galaxy IS the root (same C_I).
    """
    if ci_root <= 0 or ci_galaxy <= 0:
        return 0.0
    return float(max(0.0, np.log10((ci_root + EPS) / (ci_galaxy + EPS))) * D_UNIT)


def cascade_score(sub_frac, d):
    """S = sub_frac × exp(-d / C_NETWORK)"""
    return float(sub_frac * np.exp(-d / C_NETWORK))


def predicted_delay(t_root_survival, d):
    """t_i = t_ROOT + d_i / C_NETWORK"""
    return float(t_root_survival + d / C_NETWORK)


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()
    os.makedirs(_DATA_RESULTS, exist_ok=True)

    # ------------------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------------------
    batch_path = None
    for p in [BATCH_JSON, BATCH_JSON_ALT]:
        if os.path.isfile(p):
            batch_path = p
            break
    if batch_path is None:
        print(f"ERROR: batch JSON not found. Checked:\n  {BATCH_JSON}\n  {BATCH_JSON_ALT}")
        return 1

    with open(batch_path, encoding="utf-8") as f:
        sparc_raw = json.load(f)

    print("=" * 108)
    print(f"BCM v28 TEST {TEST_NUMBER} — CRAG CASCADE PROPAGATION")
    print(f"Hypothesis : {HYP_ID}")
    print(f"N galaxies : {len(sparc_raw)}")
    print(f"C_network  : {C_NETWORK}  (network hops / BCM time unit, unfrozen)")
    print(f"D_unit     : {D_UNIT}  (log10 C_I ratio per hop, unfrozen)")
    print(f"T_survival : {T_SURVIVAL:.2f}  (BCM time units at lambda={LAMBDA})")
    print("=" * 108)

    # ------------------------------------------------------------------
    # STEP 1: Compute base properties for all galaxies
    # ------------------------------------------------------------------
    galaxies = []
    for g in sparc_raw:
        vmax    = float(g["v_max"])
        ci      = compute_ci(vmax)
        tier    = classify_crag(ci)
        sf      = substrate_fraction(float(g["rms_newton"]),
                                     float(g["rms_substrate"]))
        galaxies.append({
            "name":               g["galaxy"],
            "vmax":               vmax,
            "ci":                 ci,
            "tier":               tier,
            "sub_frac":           sf,
            "rms_newton":         float(g["rms_newton"]),
            "rms_substrate":      float(g["rms_substrate"]),
            "winner":             g.get("winner", "UNKNOWN"),
        })

    # Sort by CI descending — network hierarchy order
    galaxies.sort(key=lambda x: x["ci"], reverse=True)

    # Network apex = highest CI galaxy
    apex_ci   = galaxies[0]["ci"]
    apex_name = galaxies[0]["name"]

    # Identify ROOT galaxies
    roots = [g for g in galaxies if g["tier"] == "ROOT"]
    root_cis = np.array([r["ci"] for r in roots])

    # ------------------------------------------------------------------
    # STEP 2: Assign nearest ROOT and compute cascade metrics
    # ------------------------------------------------------------------
    for g in galaxies:
        if g["tier"] == "ROOT":
            # ROOT points upward to the APEX
            d = proxy_distance(g["ci"], apex_ci)
            t_src = T_SURVIVAL   # all ROOTs share the same decay timescale
            # ROOT survival time scaled by its own C_I ratio to apex
            # Higher C_I ROOT = closer to apex = less delay before cascade
            t_own = T_SURVIVAL + d / C_NETWORK
            g["nearest_root"]      = apex_name
            g["nearest_root_ci"]   = apex_ci
            g["proxy_distance"]    = d
            g["t_root_survival"]   = T_SURVIVAL
            g["predicted_delay"]   = t_own
            g["cascade_score"]     = cascade_score(g["sub_frac"], d)
            g["cascade_type"]      = "ROOT_SOURCE"

        else:
            # Non-ROOT: find nearest ROOT in log(C_I) space
            # = ROOT with minimum |log10(C_I_root) - log10(C_I_galaxy)|
            # that has CI > CI_ROOT
            log_ci = np.log10(g["ci"] + EPS)
            log_root_cis = np.log10(root_cis + EPS)
            dists = np.abs(log_root_cis - log_ci)
            nearest_idx = int(np.argmin(dists))
            nr          = roots[nearest_idx]

            d = proxy_distance(g["ci"], nr["ci"])
            g["nearest_root"]      = nr["name"]
            g["nearest_root_ci"]   = nr["ci"]
            g["proxy_distance"]    = d
            g["t_root_survival"]   = T_SURVIVAL
            g["predicted_delay"]   = predicted_delay(T_SURVIVAL, d)
            g["cascade_score"]     = cascade_score(g["sub_frac"], d)
            g["cascade_type"]      = "RECIPIENT"

    # ------------------------------------------------------------------
    # STEP 3: Cascade ordering — full network sequence
    # ------------------------------------------------------------------
    galaxies_ordered = sorted(galaxies, key=lambda x: x["predicted_delay"])
    for i, g in enumerate(galaxies_ordered):
        g["cascade_order"] = i + 1

    # ------------------------------------------------------------------
    # STEP 4: Print cascade summary
    # ------------------------------------------------------------------
    print()
    print("CASCADE SEQUENCE — FIRST 30 TO DEGRADE")
    print(
        f"  {'ORD':>4} {'GALAXY':<16} {'TIER':<10} {'Vmax':>5} "
        f"{'C_I':>12} {'sub_frac':>9} {'d_net':>7} "
        f"{'t_delay':>8} {'score':>10} {'nearest_ROOT':<16} {'type'}"
    )
    print("  " + "-" * 110)
    for g in galaxies_ordered[:30]:
        print(
            f"  {g['cascade_order']:>4} {g['name']:<16} {g['tier']:<10} "
            f"{g['vmax']:>5.0f} {g['ci']:>12.4e} {g['sub_frac']:>9.4f} "
            f"{g['proxy_distance']:>7.3f} {g['predicted_delay']:>8.2f} "
            f"{g['cascade_score']:>10.4e} {g['nearest_root']:<16} {g['cascade_type']}"
        )

    print()
    print("CASCADE SEQUENCE — LAST 10 TO SURVIVE")
    print(
        f"  {'ORD':>4} {'GALAXY':<16} {'TIER':<10} {'Vmax':>5} "
        f"{'C_I':>12} {'sub_frac':>9} {'d_net':>7} {'t_delay':>8} {'score':>10}"
    )
    print("  " + "-" * 88)
    for g in galaxies_ordered[-10:]:
        print(
            f"  {g['cascade_order']:>4} {g['name']:<16} {g['tier']:<10} "
            f"{g['vmax']:>5.0f} {g['ci']:>12.4e} {g['sub_frac']:>9.4f} "
            f"{g['proxy_distance']:>7.3f} {g['predicted_delay']:>8.2f} "
            f"{g['cascade_score']:>10.4e}"
        )

    # ------------------------------------------------------------------
    # STEP 5: Tier-level cascade statistics
    # ------------------------------------------------------------------
    tier_order = ["ROOT", "BRANCH", "LEAF", "VOID-EDGE"]
    by_tier = defaultdict(list)
    for g in galaxies:
        by_tier[g["tier"]].append(g)

    print()
    print("CASCADE STATISTICS BY TIER")
    print(
        f"  {'TIER':<12} {'N':>4} {'mean_score':>12} {'mean_delay':>11} "
        f"{'mean_d':>8} {'first_order':>12} {'last_order':>11}"
    )
    print("  " + "-" * 70)
    for tier in tier_order:
        gs = by_tier[tier]
        if not gs:
            continue
        scores  = [g["cascade_score"]    for g in gs]
        delays  = [g["predicted_delay"]  for g in gs]
        dists   = [g["proxy_distance"]   for g in gs]
        orders  = [g["cascade_order"]    for g in gs]
        print(
            f"  {tier:<12} {len(gs):>4} {np.mean(scores):>12.4e} "
            f"{np.mean(delays):>11.2f} {np.mean(dists):>8.3f} "
            f"{min(orders):>12} {max(orders):>11}"
        )

    # ------------------------------------------------------------------
    # STEP 6: Peak cascade score — the maximum draw zone
    # ------------------------------------------------------------------
    peak_galaxy = max(galaxies, key=lambda x: x["cascade_score"])
    last_root   = galaxies_ordered[-1]

    print()
    print("KEY FINDINGS")
    print(f"  Peak cascade score  : {peak_galaxy['name']} "
          f"tier={peak_galaxy['tier']} score={peak_galaxy['cascade_score']:.4e} "
          f"sub_frac={peak_galaxy['sub_frac']:.4f} d={peak_galaxy['proxy_distance']:.3f}")
    print(f"  Last to survive     : {last_root['name']} "
          f"tier={last_root['tier']} delay={last_root['predicted_delay']:.2f} "
          f"(network apex, order={last_root['cascade_order']})")
    print(f"  Network apex        : {apex_name} (C_I={apex_ci:.4e})")

    # Does cascade score gradient match expected: ROOT < BRANCH < LEAF > VOID?
    tier_mean_score = {tier: np.mean([g["cascade_score"] for g in by_tier[tier]])
                       for tier in tier_order if by_tier[tier]}
    expected_peak = tier_mean_score.get("LEAF", 0) > tier_mean_score.get("BRANCH", 0)
    leaf_gt_void  = tier_mean_score.get("LEAF", 0) > tier_mean_score.get("VOID-EDGE", 0)
    root_lowest   = (tier_mean_score.get("ROOT", 1) <
                     min(tier_mean_score.get("BRANCH", 0),
                         tier_mean_score.get("LEAF", 0)))
    gradient_confirmed = expected_peak and leaf_gt_void and root_lowest

    print(f"  Gradient confirmed  : {gradient_confirmed} "
          f"(ROOT_low={root_lowest}, LEAF>BRANCH={expected_peak}, LEAF>VOID={leaf_gt_void})")

    # Spearman rank correlation: cascade_score vs sub_frac
    def spearman(a, b):
        n = len(a)
        ra = np.argsort(np.argsort(a))
        rb = np.argsort(np.argsort(b))
        d2 = float(np.sum((ra.astype(float) - rb.astype(float)) ** 2))
        return float(1.0 - 6.0 * d2 / (n * (n ** 2 - 1)))

    all_scores = [g["cascade_score"] for g in galaxies]
    all_sf     = [g["sub_frac"]      for g in galaxies]
    all_delays = [g["predicted_delay"] for g in galaxies]
    all_ci     = [g["ci"]             for g in galaxies]

    rho_score_sf  = spearman(all_scores, all_sf)
    rho_delay_ci  = spearman(all_delays, all_ci)

    print(f"  Rank corr (score vs sub_frac)   : {rho_score_sf:+.4f}")
    print(f"  Rank corr (delay vs C_I, neg)   : {rho_delay_ci:+.4f}  "
          f"(expect positive: high C_I → longer delay)")

    # ------------------------------------------------------------------
    # STEP 7: Hypothesis output
    # ------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    coherence_score  = 1.0 if gradient_confirmed else 0.0
    overlap_fraction = float(rho_score_sf) if rho_score_sf > 0 else 0.0

    statement = (
        f"Crag cascade propagation test over {len(galaxies)} SPARC galaxies. "
        f"Cascade score S = sub_frac × exp(-d/C_network). "
        f"Predicted delay t_i = T_survival + d_i/C_network. "
        f"Proxy distance = log10(C_I_ROOT/C_I_galaxy) × D_unit. "
        f"C_network={C_NETWORK} (unfrozen), D_unit={D_UNIT} (unfrozen). "
        f"Network apex: {apex_name} (C_I={apex_ci:.4e}). "
        f"Gradient confirmed (ROOT<BRANCH,LEAF peak,LEAF>VOID): {gradient_confirmed}. "
        f"Tier mean cascade scores: "
        f"ROOT={tier_mean_score.get('ROOT',0):.4e}, "
        f"BRANCH={tier_mean_score.get('BRANCH',0):.4e}, "
        f"LEAF={tier_mean_score.get('LEAF',0):.4e}, "
        f"VOID={tier_mean_score.get('VOID-EDGE',0):.4e}. "
        f"Peak cascade galaxy: {peak_galaxy['name']} ({peak_galaxy['tier']}, "
        f"score={peak_galaxy['cascade_score']:.4e}). "
        f"Last survivor: {last_root['name']} (delay={last_root['predicted_delay']:.2f}). "
        f"Rank corr score vs sub_frac: {rho_score_sf:+.4f}. "
        f"coherence_score={coherence_score:.4f}, overlap_fraction={overlap_fraction:.4f}. "
        f"NOTE: proxy distance is log(C_I) space — real 3D Mpc upgrade pending."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if gradient_confirmed else 0,
        "evidence_type": "primary",
        "pass_count":    int(gradient_confirmed),
        "total_configs": 4,   # four tiers tested
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":              coherence_score,
            "overlap_fraction":             overlap_fraction,
            "n_galaxies":                   len(galaxies),
            "gradient_confirmed":           gradient_confirmed,
            "root_mean_cascade_score":      float(tier_mean_score.get("ROOT",   0)),
            "branch_mean_cascade_score":    float(tier_mean_score.get("BRANCH", 0)),
            "leaf_mean_cascade_score":      float(tier_mean_score.get("LEAF",   0)),
            "void_mean_cascade_score":      float(tier_mean_score.get("VOID-EDGE", 0)),
            "peak_cascade_galaxy":          peak_galaxy["name"],
            "peak_cascade_tier":            peak_galaxy["tier"],
            "peak_cascade_score":           peak_galaxy["cascade_score"],
            "last_survivor":                last_root["name"],
            "last_survivor_delay":          last_root["predicted_delay"],
            "network_apex":                 apex_name,
            "network_apex_ci":              apex_ci,
            "rho_score_vs_subfrac":         rho_score_sf,
            "rho_delay_vs_ci":              rho_delay_ci,
            "t_survival_bcm_units":         T_SURVIVAL,
            "c_network":                    C_NETWORK,
            "d_unit":                       D_UNIT,
            "lambda_frozen":                LAMBDA,
            "proxy_note": (
                "Distance is log10(C_I ratio) — network hierarchy proxy. "
                "Replace with real Mpc separation when 3D coords available. "
                "C_network and D_unit are declared unfrozen parameters."
            ),
        },
        "context": {
            "framework":   "crag_cascade_network",
            "data_source": batch_path,
            "dual_flow":   (
                "ROOT = pump-and-draw junction: pumps substrate OUTWARD "
                "to BRANCH/LEAF while drawing INWARD from void. "
                "LEAF = maximum draw zone (peak cascade score). "
                "VOID-EDGE = past tare reach, signal falls off. "
                "This is the inner/outer torus dual-flow scaled to crag network."
            ),
            "infall_note": (
                "SJB 2026-05-11: galaxies in ROOT draw zones may be on "
                "infall trajectories (crag-return) superimposed on Hubble "
                "expansion. Negative V_peculiar galaxies (NGC 628, IC 5332) "
                "from Test 21 are candidates. Test 26 (spatial correlation "
                "of V_peculiar sign with ROOT proximity) is the next step."
            ),
            "next_step": (
                "Upgrade proxy distance to real 3D Mpc separation using "
                "NED/Cosmicflows-4 galaxy group coordinates. "
                "Calibrate C_network and D_unit from observed quenching "
                "timescales in known interacting galaxy groups."
            ),
        },
        "keywords": [
            "crag_intensity",
            "primordial_gutter",
            "primordial_routing",
            "cmb_prestrain",
            "gutter_depth",
            "tier_flip",
            "super_gutter",
            "classifier",
            "marginal_regime",
            "lambda",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "CRAG_CASCADE_175_SPARC",
        "framework":         "crag_cascade_network",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "cascade_sequence":  galaxies_ordered,
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Corrected crag law (SJB 2026-05-11):")
    print("  Crag tier is POSITION in a substrate draw network.")
    print("  ROOT = pump-and-draw junction.")
    print("  LEAF = maximum draw zone.")
    print("  VOID-EDGE = past tare reach, signal falls.")
    print()
    print("Next: Test 26 — V_peculiar sign vs ROOT proximity correlation.")
    print("      Upgrade proxy distance to real 3D Mpc (NED/Cosmicflows-4).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
