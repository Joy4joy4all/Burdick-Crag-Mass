# -*- coding: utf-8 -*-
"""
BCM_v28_TEST24_J_KILL_SWEEP_175.py

Hypothesis: H_V29_FUNDING_FRACTION_CRAG_TIER

Statement
---------
ROOT crag galaxies receive systematically higher substrate funding
fractions than BRANCH, LEAF, or VOID-EDGE galaxies. The J kill chain
reveals the intrinsic battery percentage and substrate funding fraction
for each of the 175 SPARC galaxies. These funding fractions, mapped
against crag tier, reveal the survival hierarchy of the BCM crag network
and identify the last ROOT crag to go dark when meta-substrate flux fails.

Physics
-------
Substrate funding fraction per galaxy:
    substrate_fraction = max(0, delta_rms) / rms_newton
    where delta_rms = rms_newton - rms_substrate
    (how much better substrate does than Newton, normalized to Newton)

This is the J-active contribution. When J is killed (J=0):
    sigma(t) = sigma_ss * exp(-lambda * t)    lambda = 0.1 (frozen)

The substrate contribution to rotation curve correction decays
exponentially. Survival time to 15% of sigma_ss (the "85% battery"
threshold from the null pump test):
    t_85 = ln(1/0.15) / lambda = ln(6.667) / 0.1 ≈ 19.0 time units

Crag classification (same as Test 20):
    C_I = J_amp * sigma_deficit
    J_amp = (Vmax / 206.0)^2 * 8.0
    sigma_deficit = SIGMA_CRIT * (J_amp / J_REF) * N_HALF

Data source
-----------
SPARC batch JSON: data produced by BCM solver v27 over all 175 SPARC
galaxies. Contains per-galaxy: name, v_max, rms_newton, rms_substrate,
sub_vs_newton, winner, corr_full.

Key outputs
-----------
1. substrate_fraction per galaxy (the actual measured BCM contribution)
2. Crag tier (ROOT/BRANCH/LEAF/VOID-EDGE from C_I)
3. survival_time to 85% battery threshold
4. last_survivor ranking (highest C_I * substrate_fraction = longest viable)
5. Correlation: does substrate_fraction increase with crag tier?
6. Root ball: top 10 ROOT crags by survival time

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

# SPARC batch JSON — produced by BCM v27 solver over 175 galaxies
BATCH_JSON = os.path.join(_SOLVER_ROOT, "data", "results",
                          "batch_20260327_140314.json")
# Fallback: check project root
BATCH_JSON_ALT = os.path.join(_SOLVER_ROOT, "batch_20260327_140314.json")

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST24_J_KILL_SWEEP_175"
TEST_NUMBER = 24
HYP_ID      = "H_V29_FUNDING_FRACTION_CRAG_TIER"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT  = 5.0e-4
J_REF       = 8.0
VMAX_REF    = 206.0      # NGC 5055 Test 13 reference
N_HALF      = 60
LAMBDA      = 0.1        # substrate decay rate (frozen v1)

CI_ROOT     = 1.0e-1
CI_BRANCH   = 1.0e-2
CI_LEAF     = 1.0e-3

# J kill chain threshold: sigma drops to this fraction → "85% battery"
KILL_THRESHOLD = 0.15    # 15% of sigma_ss remaining = 85% intrinsic battery
T_SURVIVAL     = np.log(1.0 / KILL_THRESHOLD) / LAMBDA  # ~19.0 time units


# ============================================================================
# PHYSICS
# ============================================================================

def compute_j_amp(vmax):
    return max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)


def compute_sigma_deficit(j_amp):
    return float(SIGMA_CRIT * (j_amp / J_REF) * N_HALF)


def compute_ci(j_amp):
    return j_amp * compute_sigma_deficit(j_amp)


def classify_crag(ci, is_void=False):
    if is_void and ci <= CI_LEAF:
        return "VOID-EDGE"
    if ci > CI_ROOT:   return "ROOT"
    if ci > CI_BRANCH: return "BRANCH"
    if ci > CI_LEAF:   return "LEAF"
    return "VOID-EDGE"


def substrate_fraction_from_rms(rms_newton, rms_substrate):
    """
    Estimate substrate funding fraction from RMS comparison.

    rms_substrate < rms_newton means substrate better explains the curve.
    delta_rms = rms_newton - rms_substrate: how much substrate improves fit.
    substrate_fraction = delta_rms / rms_newton: fractional improvement.

    Clamped to [0, 1]. Negative values (substrate worse than Newton)
    → substrate_fraction = 0 (Newton wins, no substrate contribution).
    """
    if rms_newton <= 0:
        return 0.0
    delta = rms_newton - rms_substrate
    frac  = delta / rms_newton
    return float(np.clip(frac, 0.0, 1.0))


def kill_chain_survival(j_amp, substrate_frac):
    """
    Simulate J kill: sigma decays exponentially from sigma_ss.
    Returns:
        t_survival : time to reach KILL_THRESHOLD * sigma_ss
        sigma_ss   : steady-state sigma with J active
        sigma_final: sigma at t_survival (should be ~KILL_THRESHOLD * sigma_ss)
        battery_pct: intrinsic battery fraction = 1 - substrate_frac
    """
    sigma_ss    = float(SIGMA_CRIT * (j_amp / J_REF))
    # sigma(t) = sigma_ss * exp(-LAMBDA * t)
    # Solve: KILL_THRESHOLD = exp(-LAMBDA * t_survival)
    t_survival  = float(-np.log(KILL_THRESHOLD) / LAMBDA)
    sigma_final = float(sigma_ss * KILL_THRESHOLD)
    battery_pct = float(1.0 - substrate_frac)
    return t_survival, sigma_ss, sigma_final, battery_pct


def last_survivor_score(ci, substrate_frac, t_survival):
    """
    Combined score for last-survivor ranking.
    Accounts for: crag intensity (J supply), substrate fraction (funding level),
    and sigma decay time. Higher = survives longer.
    """
    return float(ci * (1.0 + substrate_frac) * t_survival)


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()
    os.makedirs(_DATA_RESULTS, exist_ok=True)

    # ------------------------------------------------------------------
    # LOAD SPARC BATCH DATA
    # ------------------------------------------------------------------
    batch_path = None
    for p in [BATCH_JSON, BATCH_JSON_ALT]:
        if os.path.isfile(p):
            batch_path = p
            break

    if batch_path is None:
        print("ERROR: SPARC batch JSON not found.")
        print(f"  Checked: {BATCH_JSON}")
        print(f"  Checked: {BATCH_JSON_ALT}")
        return 1

    with open(batch_path, encoding="utf-8") as f:
        sparc_data = json.load(f)

    print("=" * 108)
    print(f"BCM v28 TEST {TEST_NUMBER} — J KILL CHAIN SWEEP (175 SPARC GALAXIES)")
    print(f"Hypothesis : {HYP_ID}")
    print(f"Data source: {batch_path}")
    print(f"N galaxies : {len(sparc_data)}")
    print(f"Kill threshold: sigma → {KILL_THRESHOLD:.0%} of sigma_ss")
    print(f"T_survival  : {T_SURVIVAL:.2f} time units (lambda={LAMBDA})")
    print("=" * 108)

    # ------------------------------------------------------------------
    # PROCESS EACH GALAXY
    # ------------------------------------------------------------------
    records = []

    for g in sparc_data:
        name        = g["galaxy"]
        vmax        = float(g["v_max"])
        rms_newton  = float(g["rms_newton"])
        rms_sub     = float(g["rms_substrate"])
        winner      = g.get("winner", "UNKNOWN")
        corr_full   = float(g.get("corr_full", 0.0))
        sub_vs_newt = float(g.get("sub_vs_newton", 0.0))

        j_amp       = compute_j_amp(vmax)
        ci          = compute_ci(j_amp)
        crag        = classify_crag(ci)

        sub_frac    = substrate_fraction_from_rms(rms_newton, rms_sub)
        t_surv, sigma_ss, sigma_fin, battery = kill_chain_survival(j_amp, sub_frac)
        score       = last_survivor_score(ci, sub_frac, t_surv)

        records.append({
            "name":              name,
            "vmax":              vmax,
            "j_amp":             round(j_amp, 4),
            "crag_tier":         crag,
            "ci":                ci,
            "rms_newton":        rms_newton,
            "rms_substrate":     rms_sub,
            "winner":            winner,
            "corr_full":         corr_full,
            "substrate_fraction": sub_frac,
            "intrinsic_battery": battery,
            "sigma_ss":          sigma_ss,
            "t_survival":        t_surv,
            "last_survivor_score": score,
        })

    # Sort by last_survivor_score descending
    records_ranked = sorted(records, key=lambda r: r["last_survivor_score"],
                            reverse=True)

    # ------------------------------------------------------------------
    # STEP 1: Crag tier distribution
    # ------------------------------------------------------------------
    from collections import Counter, defaultdict

    tier_counts  = Counter(r["crag_tier"] for r in records)
    tier_sub_frac = defaultdict(list)
    tier_ci       = defaultdict(list)
    tier_battery  = defaultdict(list)

    for r in records:
        tier_sub_frac[r["crag_tier"]].append(r["substrate_fraction"])
        tier_ci[r["crag_tier"]].append(r["ci"])
        tier_battery[r["crag_tier"]].append(r["intrinsic_battery"])

    print()
    print("CRAG TIER DISTRIBUTION AND MEAN SUBSTRATE FUNDING")
    print(f"  {'TIER':<12} {'N':>4} {'mean_sub_frac':>14} "
          f"{'mean_C_I':>12} {'mean_battery':>13}")
    print("  " + "-" * 60)
    tier_order = ["ROOT", "BRANCH", "LEAF", "VOID-EDGE"]
    for tier in tier_order:
        if tier_counts[tier] == 0:
            continue
        sf   = tier_sub_frac[tier]
        ci_t = tier_ci[tier]
        bt   = tier_battery[tier]
        print(
            f"  {tier:<12} {tier_counts[tier]:>4} "
            f"{np.mean(sf):>14.4f} "
            f"{np.mean(ci_t):>12.4e} "
            f"{np.mean(bt):>13.4f}"
        )

    # ------------------------------------------------------------------
    # STEP 2: Winner vs crag tier cross-tab
    # ------------------------------------------------------------------
    print()
    print("SUBSTRATE WINNER RATE BY CRAG TIER")
    print(f"  {'TIER':<12} {'N':>4} {'SUBSTRATE_wins':>14} {'NEWTON_wins':>12} {'win_rate':>10}")
    print("  " + "-" * 55)
    for tier in tier_order:
        tier_records = [r for r in records if r["crag_tier"] == tier]
        if not tier_records:
            continue
        n_sub  = sum(1 for r in tier_records if r["winner"] == "SUBSTRATE")
        n_newt = sum(1 for r in tier_records if r["winner"] == "NEWTON")
        rate   = n_sub / len(tier_records)
        print(f"  {tier:<12} {len(tier_records):>4} {n_sub:>14} "
              f"{n_newt:>12} {rate:>10.3f}")

    # ------------------------------------------------------------------
    # STEP 3: Last survivor ranking — top 20 ROOT BALL candidates
    # ------------------------------------------------------------------
    print()
    print("LAST SURVIVOR RANKING — TOP 20 (ROOT BALL CANDIDATES)")
    print(f"  {'RANK':<5} {'GALAXY':<16} {'TIER':<10} {'Vmax':>6} "
          f"{'C_I':>12} {'sub_frac':>9} {'battery':>8} {'score':>12} {'winner'}")
    print("  " + "-" * 90)
    for i, r in enumerate(records_ranked[:20]):
        print(
            f"  {i+1:<5} {r['name']:<16} {r['crag_tier']:<10} "
            f"{r['vmax']:>6.0f} {r['ci']:>12.4e} "
            f"{r['substrate_fraction']:>9.4f} {r['intrinsic_battery']:>8.4f} "
            f"{r['last_survivor_score']:>12.4e} {r['winner']}"
        )

    # ------------------------------------------------------------------
    # STEP 4: Bottom 10 — first to go dark
    # ------------------------------------------------------------------
    print()
    print("FIRST TO GO DARK — BOTTOM 10 (lowest survival score)")
    print(f"  {'RANK':<5} {'GALAXY':<16} {'TIER':<10} {'Vmax':>6} "
          f"{'C_I':>12} {'sub_frac':>9} {'score':>12} {'winner'}")
    print("  " + "-" * 80)
    for i, r in enumerate(reversed(records_ranked[-10:])):
        rank = len(records_ranked) - 9 + i
        print(
            f"  {rank:<5} {r['name']:<16} {r['crag_tier']:<10} "
            f"{r['vmax']:>6.0f} {r['ci']:>12.4e} "
            f"{r['substrate_fraction']:>9.4f} "
            f"{r['last_survivor_score']:>12.4e} {r['winner']}"
        )

    # ------------------------------------------------------------------
    # STEP 5: Correlation — does substrate_fraction track crag tier?
    # ------------------------------------------------------------------
    # Encode tier as ordinal: ROOT=3, BRANCH=2, LEAF=1, VOID-EDGE=0
    tier_ord = {"ROOT": 3, "BRANCH": 2, "LEAF": 1, "VOID-EDGE": 0}
    tier_vals = np.array([tier_ord[r["crag_tier"]] for r in records])
    sub_fracs = np.array([r["substrate_fraction"] for r in records])
    ci_vals   = np.array([r["ci"] for r in records])

    # Spearman rank correlation
    def spearman(a, b):
        n = len(a)
        ra = np.argsort(np.argsort(a))
        rb = np.argsort(np.argsort(b))
        d2 = float(np.sum((ra.astype(float) - rb.astype(float)) ** 2))
        return float(1.0 - 6.0 * d2 / (n * (n ** 2 - 1)))

    rho_tier_sf  = spearman(tier_vals, sub_fracs)
    rho_ci_sf    = spearman(ci_vals,   sub_fracs)
    rho_vmax_sf  = spearman(
        np.array([r["vmax"] for r in records]), sub_fracs)

    # Mean substrate fraction by winner type
    sf_substrate_winner = np.mean(
        [r["substrate_fraction"] for r in records if r["winner"] == "SUBSTRATE"])
    sf_newton_winner = np.mean(
        [r["substrate_fraction"] for r in records if r["winner"] == "NEWTON"])

    total_substrate_wins = tier_counts.get("ROOT", 0)   # all ROOT counts
    overall_sub_win_rate = sum(1 for r in records if r["winner"] == "SUBSTRATE") / len(records)

    print()
    print("=" * 108)
    print("CORRELATION SUMMARY")
    print(f"  Rank corr (crag_tier vs substrate_fraction): {rho_tier_sf:+.4f}")
    print(f"  Rank corr (C_I vs substrate_fraction)      : {rho_ci_sf:+.4f}")
    print(f"  Rank corr (Vmax vs substrate_fraction)     : {rho_vmax_sf:+.4f}")
    print()
    print(f"  Mean substrate_fraction — SUBSTRATE winners: {sf_substrate_winner:.4f}")
    print(f"  Mean substrate_fraction — NEWTON winners   : {sf_newton_winner:.4f}")
    print(f"  Overall SUBSTRATE win rate (175 galaxies)  : {overall_sub_win_rate:.3f}")
    print()
    print(f"  T_survival (all galaxies same, lambda frozen): {T_SURVIVAL:.2f} time units")
    print(f"  Last ROOT standing: {records_ranked[0]['name']} "
          f"(score={records_ranked[0]['last_survivor_score']:.4e})")
    print("=" * 108)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    coherence_score  = float(rho_ci_sf) if rho_ci_sf > 0 else 0.0
    overlap_fraction = float(overall_sub_win_rate)

    statement = (
        f"J kill chain sweep over {len(records)} SPARC galaxies. "
        f"substrate_fraction = (rms_newton - rms_substrate) / rms_newton "
        f"from BCM v27 solver output. "
        f"Crag classification: C_I = J_amp × σ_deficit. "
        f"Tier distribution: ROOT={tier_counts['ROOT']}, "
        f"BRANCH={tier_counts['BRANCH']}, LEAF={tier_counts['LEAF']}, "
        f"VOID-EDGE={tier_counts['VOID-EDGE']}. "
        f"Rank corr (crag_tier vs substrate_fraction): {rho_tier_sf:+.4f}. "
        f"Rank corr (C_I vs substrate_fraction): {rho_ci_sf:+.4f}. "
        f"Mean sub_frac ROOT={np.mean(tier_sub_frac['ROOT']):.4f}, "
        f"BRANCH={np.mean(tier_sub_frac['BRANCH']):.4f}. "
        f"Overall substrate win rate: {overall_sub_win_rate:.3f}. "
        f"Last ROOT standing: {records_ranked[0]['name']} "
        f"(Vmax={records_ranked[0]['vmax']:.0f}, "
        f"C_I={records_ranked[0]['ci']:.4e}). "
        f"T_survival = {T_SURVIVAL:.2f} time units for all galaxies "
        f"(lambda frozen, sigma decays uniformly — survival differentiated "
        f"by C_I magnitude, not decay rate)."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if rho_ci_sf > 0.1 else 0,
        "evidence_type": "primary",
        "pass_count":    sum(1 for r in records if r["winner"] == "SUBSTRATE"),
        "total_configs": len(records),
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":           coherence_score,
            "overlap_fraction":          overlap_fraction,
            "n_galaxies":                len(records),
            "tier_root":                 tier_counts["ROOT"],
            "tier_branch":               tier_counts["BRANCH"],
            "tier_leaf":                 tier_counts["LEAF"],
            "tier_void_edge":            tier_counts["VOID-EDGE"],
            "rho_tier_vs_subfrac":       rho_tier_sf,
            "rho_ci_vs_subfrac":         rho_ci_sf,
            "rho_vmax_vs_subfrac":       rho_vmax_sf,
            "mean_subfrac_root":         float(np.mean(tier_sub_frac["ROOT"])),
            "mean_subfrac_branch":       float(np.mean(tier_sub_frac["BRANCH"])),
            "mean_subfrac_leaf":         float(np.mean(tier_sub_frac["LEAF"])) if tier_sub_frac["LEAF"] else 0.0,
            "mean_battery_root":         float(np.mean(tier_battery["ROOT"])),
            "mean_battery_branch":       float(np.mean(tier_battery["BRANCH"])),
            "substrate_win_rate":        overall_sub_win_rate,
            "sf_substrate_winners":      float(sf_substrate_winner),
            "sf_newton_winners":         float(float(sf_newton_winner)),
            "t_survival_units":          T_SURVIVAL,
            "lambda_frozen":             LAMBDA,
            "kill_threshold":            KILL_THRESHOLD,
            "last_survivor":             records_ranked[0]["name"],
            "last_survivor_ci":          records_ranked[0]["ci"],
            "last_survivor_vmax":        records_ranked[0]["vmax"],
        },
        "context": {
            "framework":      "j_kill_chain_175_sparc",
            "data_source":    batch_path,
            "meta_theory":    (
                "SJB 2026-05-11: ROOT crags are the last to go dark when "
                "meta-substrate flux fails. The last survivor root ball "
                "is the network of ROOT crags with highest C_I and "
                "highest substrate_fraction. These are the final pump "
                "sources before universal sigma → 0."
            ),
            "next_step":      (
                "Map ROOT ball candidates spatially (3D sky positions). "
                "Cross with Planck CMB overlay (Test 22) — do last survivors "
                "cluster in CMB CROSS_SCAR regions (hot spots = densest "
                "substrate) or SUPER_GUTTER regions (void channels)? "
                "Extend C_I computation with BCM Class I-VI override system "
                "to test whether class assignment predicts substrate_fraction."
            ),
        },
        "keywords": [
            "crag_intensity",
            "primordial_gutter",
            "gutter_depth",
            "cmb_prestrain",
            "primordial_routing",
            "tier_flip",
            "classifier",
            "regime",
            "lambda",
            "marginal_regime",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "J_KILL_CHAIN_175_SPARC_GALAXIES",
        "framework":         "j_kill_chain_175_sparc",
        "v28_partition":     "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "ranked_galaxies":   records_ranked,
        "tier_summary": {
            tier: {
                "count":          tier_counts[tier],
                "mean_sub_frac":  float(np.mean(tier_sub_frac[tier])) if tier_sub_frac[tier] else 0.0,
                "mean_ci":        float(np.mean(tier_ci[tier])) if tier_ci[tier] else 0.0,
                "mean_battery":   float(np.mean(tier_battery[tier])) if tier_battery[tier] else 0.0,
            }
            for tier in tier_order
        },
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("ROOT BALL — top 5 last survivors:")
    for i, r in enumerate(records_ranked[:5]):
        print(f"  {i+1}. {r['name']:<16} Vmax={r['vmax']:>6.0f}  "
              f"C_I={r['ci']:.4e}  sub_frac={r['substrate_fraction']:.4f}  "
              f"{r['crag_tier']}  winner={r['winner']}")
    print()
    print("Ingest after vocabulary confirmation.")
    print("Next: spatial map of ROOT ball candidates + Planck CMB cross-check.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
