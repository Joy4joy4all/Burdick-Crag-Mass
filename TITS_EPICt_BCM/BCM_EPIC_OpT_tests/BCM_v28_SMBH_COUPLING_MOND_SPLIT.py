# -*- coding: utf-8 -*-
"""
BCM_v28_TEST28_SMBH_COUPLING_MOND_SPLIT.py

Hypothesis: H_V28_SMBH_SUBSTRATE_COUPLING

Statement
---------
BCM's rotation curve advantage over MOND correlates positively with
estimated SMBH mass. If the substrate is funded by SMBH neutrino flux
(J-Vorticity), then larger central engines produce more substrate and
thus larger BCM-vs-MOND advantage. MOND has no mechanism to know the
SMBH is there. Dark matter halos have no dependence on the central engine.
Only BCM makes this prediction.

This is the falsification closure test for v28.

Two possible outcomes (both publishable)
-----------------------------------------
COUPLING_CONFIRMED:
    BCM-vs-MOND advantage scales with estimated M_BH.
    Interpretation: local J-Vorticity mechanism is the substrate source.
    Evidence: ρ(M_BH, BCM_vs_MOND) > 0.2 AND HIGH_MASS mean > MID_MASS > LOW_MASS.
    Paper C closing argument: "BCM advantage over MOND scales with SMBH mass —
    not predicted by MOND or dark matter models."

COSMOLOGICAL_MECHANISM:
    BCM-vs-MOND advantage is flat across Vmax/M_BH groups.
    Interpretation: substrate is NOT locally SMBH-funded — it is pre-strained
    at cosmological scale (Primordial Gutter Hypothesis). J-Vorticity is not
    the primary mechanism; σ_CMB is.
    Paper C closing argument: "BCM advantage over MOND is independent of SMBH
    mass, consistent with cosmological pre-strain rather than local engine funding."

Either outcome tightens the framework. Neither is a failure.

Key metric
----------
BCM_vs_MOND = rms_mond - rms_substrate    (positive = BCM beats MOND)
BCM_vs_MOND_frac = BCM_vs_MOND / rms_mond (fraction of MOND error closed by BCM)

M_BH proxy (M-sigma relation, declared ±0.5 dex uncertainty)
-------------------------------------------------------------
σ_proxy = 0.65 × Vmax   (asymmetric drift correction for spiral galaxies)
log10(M_BH / M_sun) = 8.13 + 4.24 × log10(σ_proxy / 200.0)
Source: Kormendy & Ho 2013, McConnell & Ma 2013

Vmax groups (SMBH mass proxy tiers)
-------------------------------------
HIGH_MASS : Vmax > 200 km/s  M_BH > ~10^8 M_sun   (BCM prediction: high advantage)
MID_MASS  : 80 ≤ Vmax ≤ 200  M_BH ~ 10^6–8 M_sun  (BCM prediction: moderate)
LOW_MASS  : Vmax < 80 km/s   M_BH < ~10^6 M_sun    (BCM prediction: low — no pump)

The LOW_MASS anomaly check
--------------------------
Test 24 showed VOID-EDGE SUBSTRATE win rate = 0.560 — higher than expected
for bulgeless galaxies without meaningful SMBHs. If BCM also beats MOND on
these galaxies, the J-Vorticity mechanism is not responsible for the win.
This test investigates which BCM term is driving the low-mass advantage.

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
TEST_NAME   = "BCM_v28_TEST28_SMBH_COUPLING_MOND_SPLIT"
TEST_NUMBER = 28
HYP_ID      = "H_V28_SMBH_SUBSTRATE_COUPLING"

# ============================================================================
# FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT = 5.0e-4
J_REF      = 8.0
VMAX_REF   = 206.0
N_HALF     = 60
CI_ROOT    = 1.0e-1
EPS        = 1.0e-12

# M-sigma relation (Kormendy & Ho 2013)
M_SIGMA_ALPHA = 8.13    # log10(M_BH/M_sun) at sigma=200
M_SIGMA_BETA  = 4.24    # power law index
SIGMA_REF     = 200.0   # km/s reference
SIGMA_SCALE   = 0.65    # Vmax -> sigma proxy (asymmetric drift)

# Vmax group thresholds
VMAX_HIGH     = 200.0   # km/s — estimated M_BH > 10^8 M_sun
VMAX_LOW      = 80.0    # km/s — estimated M_BH < 10^6 M_sun

# Coupling confirmation thresholds
RHO_COUPLING_MIN  = 0.20    # minimum rank correlation to call coupling confirmed
GRADIENT_REQUIRED = True    # HIGH > MID > LOW must hold

# ============================================================================
# PHYSICS
# ============================================================================

def estimate_log_mbh(vmax):
    """
    Estimate log10(M_BH/M_sun) from Vmax via M-sigma relation.
    σ_proxy = SIGMA_SCALE × Vmax (±0.5 dex uncertainty, declared).
    """
    sigma = SIGMA_SCALE * vmax
    if sigma <= 0:
        return 0.0
    return float(M_SIGMA_ALPHA + M_SIGMA_BETA * np.log10(sigma / SIGMA_REF))


def vmax_group(vmax):
    if vmax > VMAX_HIGH:
        return "HIGH_MASS"
    if vmax >= VMAX_LOW:
        return "MID_MASS"
    return "LOW_MASS"


def compute_ci(vmax):
    j = max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)
    return j * float(SIGMA_CRIT * (j / J_REF) * N_HALF)


def classify_crag(ci):
    if ci > CI_ROOT: return "ROOT"
    if ci > 1e-2:    return "BRANCH"
    if ci > 1e-3:    return "LEAF"
    return "VOID-EDGE"


def spearman(a, b):
    n = len(a)
    if n < 3:
        return 0.0
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
    # LOAD BATCH DATA
    # ------------------------------------------------------------------
    batch_path = None
    for p in [BATCH_JSON, BATCH_JSON_ALT]:
        if os.path.isfile(p):
            batch_path = p
            break
    if batch_path is None:
        print("ERROR: batch JSON not found.")
        return 1

    with open(batch_path, encoding="utf-8") as f:
        raw = json.load(f)

    print("=" * 100)
    print(f"BCM v28 TEST {TEST_NUMBER} — SMBH COUPLING vs MOND SPLIT")
    print(f"Hypothesis : {HYP_ID}")
    print(f"N galaxies : {len(raw)}")
    print(f"M-sigma    : log(M_BH) = {M_SIGMA_ALPHA} + {M_SIGMA_BETA}×log(σ/200)")
    print(f"σ proxy    : {SIGMA_SCALE}×Vmax  (±0.5 dex uncertainty, declared)")
    print(f"Vmax groups: HIGH>{VMAX_HIGH}  MID {VMAX_LOW}–{VMAX_HIGH}  LOW<{VMAX_LOW}")
    print("=" * 100)

    # ------------------------------------------------------------------
    # BUILD RECORDS
    # ------------------------------------------------------------------
    records = []
    for g in raw:
        vmax       = float(g["v_max"])
        rms_newton = float(g["rms_newton"])
        rms_mond   = float(g["rms_mond"])
        rms_sub    = float(g["rms_substrate"])
        winner     = g.get("winner", "UNKNOWN")

        log_mbh    = estimate_log_mbh(vmax)
        mbh_proxy  = float(10 ** log_mbh)   # M_sun
        group      = vmax_group(vmax)
        ci         = compute_ci(vmax)
        crag       = classify_crag(ci)

        # Core metric: BCM advantage over MOND
        bcm_vs_mond       = float(rms_mond  - rms_sub)
        bcm_vs_newton     = float(rms_newton - rms_sub)
        bcm_vs_mond_frac  = float(bcm_vs_mond / (rms_mond + EPS))
        bcm_beats_mond    = bcm_vs_mond > 0
        bcm_beats_newton  = bcm_vs_newton > 0

        # Pump efficiency: BCM advantage per unit estimated M_BH
        pump_efficiency   = float(bcm_vs_mond / (log_mbh + EPS)) if log_mbh > 0 else 0.0

        records.append({
            "name":              g["galaxy"],
            "vmax":              vmax,
            "log_mbh":           log_mbh,
            "mbh_proxy_msun":    mbh_proxy,
            "vmax_group":        group,
            "crag_tier":         crag,
            "rms_newton":        rms_newton,
            "rms_mond":          rms_mond,
            "rms_substrate":     rms_sub,
            "winner":            winner,
            "bcm_vs_mond":       bcm_vs_mond,
            "bcm_vs_newton":     bcm_vs_newton,
            "bcm_vs_mond_frac":  bcm_vs_mond_frac,
            "bcm_beats_mond":    bcm_beats_mond,
            "bcm_beats_newton":  bcm_beats_newton,
            "pump_efficiency":   pump_efficiency,
        })

    # ------------------------------------------------------------------
    # STEP 1: Group statistics — the gradient test
    # ------------------------------------------------------------------
    by_group = defaultdict(list)
    for r in records:
        by_group[r["vmax_group"]].append(r)

    group_order = ["HIGH_MASS", "MID_MASS", "LOW_MASS"]
    group_stats = {}

    print()
    print("STEP 1 — BCM-vs-MOND ADVANTAGE BY VMAX GROUP")
    print(
        f"  {'GROUP':<12} {'N':>4} {'mean_BCM_MOND':>14} {'mean_frac':>10} "
        f"{'beats_MOND%':>12} {'beats_Newt%':>12} {'mean_logMBH':>12}"
    )
    print("  " + "-" * 80)
    for grp in group_order:
        gs = by_group[grp]
        if not gs:
            continue
        adv    = [r["bcm_vs_mond"]      for r in gs]
        frac   = [r["bcm_vs_mond_frac"] for r in gs]
        bm     = sum(1 for r in gs if r["bcm_beats_mond"])
        bn     = sum(1 for r in gs if r["bcm_beats_newton"])
        lmbh   = [r["log_mbh"]          for r in gs]
        stats  = {
            "n":            len(gs),
            "mean_adv":     float(np.mean(adv)),
            "mean_frac":    float(np.mean(frac)),
            "beats_mond_pct": float(bm / len(gs)),
            "beats_newt_pct": float(bn / len(gs)),
            "mean_logmbh":  float(np.mean(lmbh)),
        }
        group_stats[grp] = stats
        print(
            f"  {grp:<12} {stats['n']:>4} {stats['mean_adv']:>14.4f} "
            f"{stats['mean_frac']:>10.4f} {stats['beats_mond_pct']*100:>11.1f}% "
            f"{stats['beats_newt_pct']*100:>11.1f}% {stats['mean_logmbh']:>12.3f}"
        )

    # Gradient check: HIGH > MID > LOW on BCM-vs-MOND advantage?
    hi  = group_stats.get("HIGH_MASS", {}).get("mean_adv", 0.0)
    mid = group_stats.get("MID_MASS",  {}).get("mean_adv", 0.0)
    lo  = group_stats.get("LOW_MASS",  {}).get("mean_adv", 0.0)
    gradient_holds = (hi > mid) and (mid > lo)

    print(f"\n  Gradient (HIGH>MID>LOW): {gradient_holds}  "
          f"({hi:.4f} > {mid:.4f} > {lo:.4f})")

    # ------------------------------------------------------------------
    # STEP 2: Rank correlation M_BH vs BCM advantage
    # ------------------------------------------------------------------
    all_logmbh = np.array([r["log_mbh"]      for r in records])
    all_adv    = np.array([r["bcm_vs_mond"]  for r in records])
    all_frac   = np.array([r["bcm_vs_mond_frac"] for r in records])

    rho_mbh_adv  = spearman(all_logmbh, all_adv)
    rho_mbh_frac = spearman(all_logmbh, all_frac)
    rho_vmax_adv = spearman(
        np.array([r["vmax"] for r in records]), all_adv)

    coupling_confirmed = (rho_mbh_adv > RHO_COUPLING_MIN) and gradient_holds

    print()
    print("STEP 2 — RANK CORRELATION: M_BH PROXY vs BCM ADVANTAGE")
    print(f"  ρ(log_MBH, BCM_vs_MOND)       : {rho_mbh_adv:+.4f}  "
          f"(need > {RHO_COUPLING_MIN} for coupling)")
    print(f"  ρ(log_MBH, BCM_vs_MOND_frac)  : {rho_mbh_frac:+.4f}")
    print(f"  ρ(Vmax, BCM_vs_MOND)           : {rho_vmax_adv:+.4f}")
    print(f"  Coupling confirmed             : {coupling_confirmed}")

    # ------------------------------------------------------------------
    # STEP 3: ROOT tier internal split — SUBSTRATE vs NEWTON winners
    # ------------------------------------------------------------------
    root_records  = [r for r in records if r["crag_tier"] == "ROOT"]
    root_sub_win  = [r for r in root_records if r["winner"] == "SUBSTRATE"]
    root_newt_win = [r for r in root_records if r["winner"] == "NEWTON"]

    sub_logmbh  = [r["log_mbh"] for r in root_sub_win]
    newt_logmbh = [r["log_mbh"] for r in root_newt_win]
    sub_adv     = [r["bcm_vs_mond"] for r in root_sub_win]
    newt_adv    = [r["bcm_vs_mond"] for r in root_newt_win]

    print()
    print("STEP 3 — ROOT TIER: SUBSTRATE vs NEWTON WINNERS")
    print(f"  {'GROUP':<22} {'N':>4} {'mean_logMBH':>12} {'mean_BCM_MOND':>14}")
    print("  " + "-" * 56)
    if sub_logmbh:
        print(f"  {'ROOT SUBSTRATE wins':<22} {len(sub_logmbh):>4} "
              f"{np.mean(sub_logmbh):>12.3f} {np.mean(sub_adv):>14.4f}")
    if newt_logmbh:
        print(f"  {'ROOT NEWTON wins':<22} {len(newt_logmbh):>4} "
              f"{np.mean(newt_logmbh):>12.3f} {np.mean(newt_adv):>14.4f}")
    root_split_holds = (
        len(sub_logmbh) > 0 and len(newt_logmbh) > 0 and
        np.mean(sub_logmbh) > np.mean(newt_logmbh)
    )
    print(f"  ROOT SUBSTRATE winners have higher M_BH: {root_split_holds}")

    # ------------------------------------------------------------------
    # STEP 4: LOW_MASS anomaly — does BCM beat MOND without an SMBH?
    # ------------------------------------------------------------------
    low_records = by_group.get("LOW_MASS", [])
    low_beats   = [r for r in low_records if r["bcm_beats_mond"]]
    low_adv     = [r["bcm_vs_mond"] for r in low_records]

    print()
    print("STEP 4 — LOW_MASS ANOMALY CHECK")
    print(f"  LOW_MASS galaxies (Vmax<{VMAX_LOW}): N={len(low_records)}")
    if low_records:
        print(f"  BCM beats MOND        : {len(low_beats)}/{len(low_records)} "
              f"({100*len(low_beats)/len(low_records):.1f}%)")
        print(f"  Mean BCM-vs-MOND adv  : {np.mean(low_adv):.4f}")
        print(f"  Mean log_MBH proxy    : "
              f"{np.mean([r['log_mbh'] for r in low_records]):.3f}  "
              f"(~{10**np.mean([r['log_mbh'] for r in low_records]):.2e} M_sun)")
        # Top 5 BCM-vs-MOND winners in LOW_MASS (the anomalous ones)
        low_sorted = sorted(low_records, key=lambda x: x["bcm_vs_mond"], reverse=True)
        print(f"  Top 5 LOW_MASS BCM-beats-MOND:")
        for r in low_sorted[:5]:
            print(f"    {r['name']:<16} Vmax={r['vmax']:.0f}  "
                  f"BCM_vs_MOND={r['bcm_vs_mond']:.4f}  "
                  f"log_MBH={r['log_mbh']:.2f}  winner={r['winner']}")
        low_anomaly = np.mean(low_adv) > 0.5 * mid   # anomalous if close to MID
        print(f"  LOW_MASS advantage anomalous (>50% of MID): {low_anomaly}")

    # ------------------------------------------------------------------
    # STEP 5: Verdict
    # ------------------------------------------------------------------
    if coupling_confirmed and root_split_holds:
        verdict        = "COUPLING_CONFIRMED"
        verdict_note   = (
            "BCM-vs-MOND advantage scales with estimated SMBH mass. "
            "ROOT SUBSTRATE winners have higher M_BH than ROOT NEWTON winners. "
            "Interpretation: local J-Vorticity mechanism is the substrate source. "
            "MOND and dark matter models cannot predict this SMBH dependence."
        )
    elif not coupling_confirmed and not gradient_holds:
        verdict        = "COSMOLOGICAL_MECHANISM"
        verdict_note   = (
            "BCM-vs-MOND advantage is flat across SMBH mass proxy groups. "
            "Substrate funding is NOT tied to local SMBH strength. "
            "Interpretation: substrate is cosmologically pre-strained "
            "(Primordial Gutter Hypothesis). J-Vorticity is not the primary source."
        )
    else:
        verdict        = "MIXED_SIGNAL"
        verdict_note   = (
            "Partial coupling signal. Gradient partially holds or correlation "
            "is below threshold. Both local J-Vorticity and cosmological "
            "pre-strain may contribute. Requires real M_BH data from NED "
            "(Reines & Volonteri 2015, Greene et al. 2020) to resolve."
        )

    print()
    print("=" * 100)
    print(f"VERDICT: {verdict}")
    print(f"  {verdict_note}")
    print()
    print("CORRELATION SUMMARY")
    print(f"  ρ(log_MBH, BCM_vs_MOND)     : {rho_mbh_adv:+.4f}")
    print(f"  Gradient HIGH>MID>LOW        : {gradient_holds}")
    print(f"  ROOT SUBSTRATE > NEWTON M_BH : {root_split_holds}")
    print(f"  Coupling threshold           : ρ > {RHO_COUPLING_MIN} AND gradient")
    print("=" * 100)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    coherence_score  = 1.0 if coupling_confirmed else (0.5 if root_split_holds else 0.0)
    overlap_fraction = float(max(0.0, rho_mbh_adv))

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"SMBH coupling vs MOND split over {len(records)} SPARC galaxies. "
        f"M_BH proxy from M-sigma: log(M_BH)={M_SIGMA_ALPHA}+"
        f"{M_SIGMA_BETA}×log(σ/200), σ={SIGMA_SCALE}×Vmax (±0.5 dex). "
        f"BCM_vs_MOND = rms_mond - rms_substrate. "
        f"Rank corr ρ(log_MBH, BCM_vs_MOND) = {rho_mbh_adv:+.4f}. "
        f"Gradient HIGH>MID>LOW: {gradient_holds} "
        f"({hi:.4f}>{mid:.4f}>{lo:.4f}). "
        f"ROOT split: SUBSTRATE winners mean log_MBH={np.mean(sub_logmbh):.3f} "
        f"vs NEWTON winners mean log_MBH={np.mean(newt_logmbh):.3f}. "
        f"ROOT split holds: {root_split_holds}. "
        f"Coupling confirmed: {coupling_confirmed}. "
        f"Verdict: {verdict}. "
        f"coherence_score={coherence_score:.4f}, "
        f"overlap_fraction={overlap_fraction:.4f}."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if coupling_confirmed else (0 if verdict == "COSMOLOGICAL_MECHANISM" else -1),
        "evidence_type": "primary",
        "pass_count":    int(coupling_confirmed) + int(root_split_holds),
        "total_configs": 2,
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            "coherence_score":          coherence_score,
            "overlap_fraction":         overlap_fraction,
            "n_galaxies":               len(records),
            "verdict":                  verdict,
            "rho_logmbh_bcm_vs_mond":   rho_mbh_adv,
            "rho_logmbh_bcm_vs_frac":   rho_mbh_frac,
            "rho_vmax_bcm_vs_mond":     rho_vmax_adv,
            "gradient_holds":           gradient_holds,
            "high_mass_mean_adv":       hi,
            "mid_mass_mean_adv":        mid,
            "low_mass_mean_adv":        lo,
            "root_split_holds":         root_split_holds,
            "root_substrate_mean_logmbh": float(np.mean(sub_logmbh)) if sub_logmbh else 0.0,
            "root_newton_mean_logmbh":    float(np.mean(newt_logmbh)) if newt_logmbh else 0.0,
            "root_substrate_n":         len(root_sub_win),
            "root_newton_n":            len(root_newt_win),
            "low_mass_beats_mond_rate":  float(len(low_beats)/len(low_records)) if low_records else 0.0,
            "coupling_threshold_rho":   RHO_COUPLING_MIN,
            "msigma_alpha":             M_SIGMA_ALPHA,
            "msigma_beta":              M_SIGMA_BETA,
            "sigma_scale":              SIGMA_SCALE,
            "vmax_high_threshold":      VMAX_HIGH,
            "vmax_low_threshold":       VMAX_LOW,
            "mbh_uncertainty_dex":      0.5,
            "verdict_note":             verdict_note,
        },
        "context": {
            "framework":   "smbh_coupling_mond_split",
            "data_source": batch_path,
            "falsification": (
                "COUPLING_CONFIRMED: BCM advantage tied to central engine — "
                "J-Vorticity mechanism validated. "
                "COSMOLOGICAL_MECHANISM: BCM advantage independent of SMBH — "
                "Primordial Gutter pre-strain is the substrate source. "
                "Both outcomes are publishable and tighten the framework."
            ),
            "mbh_proxy_note": (
                "M_BH estimated from M-sigma via Vmax proxy (±0.5 dex). "
                "For real M_BH: cross-reference Reines & Volonteri 2015, "
                "Greene et al. 2020, or direct sigma measurements from SDSS. "
                "NED has AGN/Seyfert classifications for most SPARC galaxies."
            ),
            "mond_note": (
                "MOND implementation in batch uses a0=1.2e-10 m/s^2 (standard). "
                "If MOND win rate (1/175) is anomalously low vs literature, "
                "investigate the interpolating function used before Paper C."
            ),
            "next_step": (
                "Cross-reference SPARC galaxies against NED AGN catalog. "
                "Replace Vmax-proxy M_BH with real sigma or direct M_BH where "
                "available. Re-run STEP 2 and STEP 3 with real M_BH data. "
                "Investigate LOW_MASS BCM-beats-MOND anomaly: which BCM term "
                "is responsible — Term 1 (Einstein recovery) or Term 5 (entropy sink)?"
            ),
        },
        "keywords": [
            "crag_intensity",
            "primordial_gutter",
            "gutter_depth",
            "dual_flow_crag",
            "substrate_funding_fraction",
            "cascade_propagation",
            "classifier",
            "regime",
            "marginal_regime",
            "lambda",
        ],
    }

    output = {
        "test_name":         TEST_NAME,
        "test_number":       TEST_NUMBER,
        "timestamp":         timestamp,
        "target":            "SMBH_COUPLING_MOND_175_SPARC",
        "framework":         "smbh_coupling_mond_split",
        "v28_partition":     "falsification_closure",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "group_stats":       group_stats,
        "all_records":       sorted(records,
                                    key=lambda r: r["bcm_vs_mond"],
                                    reverse=True),
        "elapsed_seconds":   time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    if verdict == "COUPLING_CONFIRMED":
        print("PAPER C CLOSING ARGUMENT (draft):")
        print("  'BCM rotation curve advantage over MOND scales with estimated")
        print("   SMBH mass. This dependence on the central engine is not predicted")
        print("   by MOND or dark matter halo models. It is the specific signature")
        print("   of BCM's J-Vorticity substrate funding mechanism.'")
    elif verdict == "COSMOLOGICAL_MECHANISM":
        print("PAPER C CLOSING ARGUMENT (draft):")
        print("  'BCM advantage over MOND is independent of SMBH mass proxy,")
        print("   consistent with cosmological substrate pre-strain (Primordial")
        print("   Gutter Hypothesis) as the funding source rather than local")
        print("   engine activity. The substrate is inherited from the Bang,")
        print("   not generated by the current central engine.'")
    else:
        print("MIXED — cross-reference with real M_BH before Paper C conclusion.")
    print()
    print("Ingest after confirmation. This is the v28 closing test.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
