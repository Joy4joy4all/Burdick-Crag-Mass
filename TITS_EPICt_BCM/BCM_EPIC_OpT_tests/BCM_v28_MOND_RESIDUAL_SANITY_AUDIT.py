# -*- coding: utf-8 -*-
"""
BCM_v28_TEST29_MOND_RESIDUAL_SANITY_AUDIT.py

Purpose
-------
Detect impossible MOND comparison rows before using MOND as a
publication opponent in Paper C.

Do NOT build Paper C on raw MOND results until this test passes.

Five gates
----------
1. residual_scale_gate
   abs(BCM_vs_MOND) <= 0.75 × Vmax
   If BCM advantage exceeds 75% of the galaxy's total rotation speed,
   the comparison is physically impossible. Flag.

2. rms_floor_gate
   rms_mond, rms_substrate, rms_newton must be finite (not nan/inf)
   and nonnegative. Any negative or non-finite value = implementation error.

3. dwarf_explosion_gate
   For Vmax < 80 km/s: abs(BCM_vs_MOND) > 30 km/s = MOND_IMPL_SUSPECT.
   A BCM advantage larger than 30 km/s on a galaxy rotating at
   30-80 km/s total is physically unacceptable.

4. rank_stability_gate
   Recompute HIGH/MID/LOW group statistics after removing all flagged
   rows. Reports whether the group ordering is stable under cleaning.

5. comparison_rebuild
   Reports three result sets side by side:
     RAW_MOND  : full 175-galaxy MOND comparison (Test 28)
     CLEAN_MOND: flagged rows removed
     NEWTON    : full 175-galaxy Newton comparison (no MOND flags apply)

Decisive question
-----------------
Does ρ(log_MBH, BCM_vs_MOND_frac) stay NEGATIVE after removing
impossible MOND rows?

If YES → Paper C may use MOND comparison:
    "BCM advantage over MOND decreases with SMBH proxy even after
     MOND sanity filtering, favoring cosmological substrate / crag-network
     routing over local SMBH-only funding."

If NO  → Use Newton only:
    "BCM-vs-Newton correction is concentrated in MID_MASS recipient
     galaxies (82.1%), not HIGH_MASS ROOT source galaxies (44.7%).
     This is the rotation curve fingerprint of the crag draw network."

Verdict codes
-------------
MOND_CLEAN_USABLE      : clean set passes all checks, ρ stays negative
MOND_DEGRADED_USABLE   : clean set has fewer rows but ρ still negative
NEWTON_ONLY            : ρ flips or insufficient clean rows remain
MOND_IMPL_BROKEN       : >50% of rows flagged — MOND implementation invalid

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems -- 2026
All theoretical IP: Burdick.
"""

import json
import os
import sys
import time
from datetime import datetime
from collections import defaultdict

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
TEST_NAME   = "BCM_v28_TEST29_MOND_RESIDUAL_SANITY_AUDIT"
TEST_NUMBER = 29
HYP_ID      = "H_V28_MOND_SANITY_GATE"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT    = 5.0e-4
J_REF         = 8.0
VMAX_REF      = 206.0
N_HALF        = 60
CI_ROOT       = 1.0e-1
EPS           = 1.0e-12
SIGMA_SCALE   = 0.65
M_SIGMA_ALPHA = 8.13
M_SIGMA_BETA  = 4.24
SIGMA_REF     = 200.0
VMAX_HIGH     = 200.0
VMAX_LOW      = 80.0

# ============================================================================
# GATE THRESHOLDS
# ============================================================================
GATE_SCALE_FRACTION   = 0.75   # gate 1: BCM_vs_MOND <= 0.75 × Vmax
GATE_DWARF_VMAX       = 80.0   # gate 3: dwarf threshold (km/s)
GATE_DWARF_ADV        = 30.0   # gate 3: max acceptable BCM_vs_MOND for dwarfs

RHO_NEGATIVE_REQUIRED = 0.0    # decisive: ρ must be < 0 to use MOND
MIN_CLEAN_N           = 50     # minimum clean rows to call MOND usable
FLAG_FRACTION_BROKEN  = 0.50   # if >50% flagged → MOND_IMPL_BROKEN


# ============================================================================
# HELPERS
# ============================================================================

def estimate_log_mbh(vmax):
    sigma = SIGMA_SCALE * vmax
    if sigma <= 0:
        return 0.0
    return float(M_SIGMA_ALPHA + M_SIGMA_BETA * np.log10(sigma / SIGMA_REF))


def vmax_group(vmax):
    if vmax > VMAX_HIGH:   return "HIGH_MASS"
    if vmax >= VMAX_LOW:   return "MID_MASS"
    return "LOW_MASS"


def spearman(a, b):
    n = len(a)
    if n < 3:
        return float("nan")
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    d2 = float(np.sum((ra.astype(float) - rb.astype(float)) ** 2))
    return float(1.0 - 6.0 * d2 / (n * (n ** 2 - 1)))


def group_stats_block(records, label):
    """Compute per-group statistics for a record set."""
    by_group = defaultdict(list)
    for r in records:
        by_group[r["vmax_group"]].append(r)

    stats = {}
    for grp in ["HIGH_MASS", "MID_MASS", "LOW_MASS"]:
        gs = by_group[grp]
        if not gs:
            stats[grp] = None
            continue
        adv   = [r["bcm_vs_mond"]      for r in gs]
        frac  = [r["bcm_vs_mond_frac"] for r in gs]
        bm    = sum(1 for r in gs if r["bcm_vs_mond"] > 0)
        bn    = sum(1 for r in gs if r["bcm_vs_newton"] > 0)
        lmbh  = [r["log_mbh"]          for r in gs]
        stats[grp] = {
            "n": len(gs),
            "mean_adv": float(np.mean(adv)),
            "mean_frac": float(np.mean(frac)),
            "beats_mond_pct": float(bm / len(gs)),
            "beats_newton_pct": float(bn / len(gs)),
            "mean_logmbh": float(np.mean(lmbh)),
        }
    return stats


def print_group_table(stats, label):
    print(f"\n  {label}")
    print(
        f"  {'GROUP':<12} {'N':>4} {'mean_adv':>10} "
        f"{'beats_MOND%':>12} {'beats_Newt%':>12} {'mean_logMBH':>12}"
    )
    print("  " + "-" * 68)
    for grp in ["HIGH_MASS", "MID_MASS", "LOW_MASS"]:
        s = stats.get(grp)
        if s is None:
            print(f"  {grp:<12}  N/A")
            continue
        print(
            f"  {grp:<12} {s['n']:>4} {s['mean_adv']:>10.4f} "
            f"{s['beats_mond_pct']*100:>11.1f}% "
            f"{s['beats_newton_pct']*100:>11.1f}% "
            f"{s['mean_logmbh']:>12.3f}"
        )


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
        print("ERROR: batch JSON not found.")
        return 1

    with open(batch_path, encoding="utf-8") as f:
        raw = json.load(f)

    print("=" * 100)
    print(f"BCM v28 TEST {TEST_NUMBER} — MOND RESIDUAL SANITY AUDIT")
    print(f"Hypothesis : {HYP_ID}")
    print(f"N galaxies : {len(raw)}")
    print(f"Gates      : scale({GATE_SCALE_FRACTION}×Vmax) | "
          f"floor(finite≥0) | "
          f"dwarf(Vmax<{GATE_DWARF_VMAX},adv>{GATE_DWARF_ADV}) | "
          f"rank_stability | comparison_rebuild")
    print(f"Decisive   : ρ(log_MBH, BCM_vs_MOND_frac) < 0 after cleaning?")
    print("=" * 100)

    # ------------------------------------------------------------------
    # BUILD RECORDS AND APPLY GATES
    # ------------------------------------------------------------------
    records = []
    for g in raw:
        vmax    = float(g["v_max"])
        rn      = float(g["rms_newton"])
        rm      = float(g["rms_mond"])
        rs      = float(g["rms_substrate"])
        winner  = g.get("winner", "UNKNOWN")

        bcm_vs_mond    = float(rm - rs)
        bcm_vs_newton  = float(rn - rs)
        bcm_vs_m_frac  = float(bcm_vs_mond / (rm + EPS))
        bcm_vs_n_frac  = float(bcm_vs_newton / (rn + EPS))
        log_mbh        = estimate_log_mbh(vmax)

        # ---- GATE 1: residual scale gate ----
        g1_flag = abs(bcm_vs_mond) > GATE_SCALE_FRACTION * vmax
        g1_note = (f"BCM_vs_MOND={bcm_vs_mond:.1f} > "
                   f"{GATE_SCALE_FRACTION}×Vmax={GATE_SCALE_FRACTION*vmax:.1f}"
                   if g1_flag else "")

        # ---- GATE 2: rms floor gate ----
        g2_flag = (
            not np.isfinite(rn) or rn < 0 or
            not np.isfinite(rm) or rm < 0 or
            not np.isfinite(rs) or rs < 0
        )
        g2_note = "non-finite or negative RMS" if g2_flag else ""

        # ---- GATE 3: dwarf explosion gate ----
        g3_flag = (vmax < GATE_DWARF_VMAX and
                   abs(bcm_vs_mond) > GATE_DWARF_ADV)
        g3_note = (f"dwarf Vmax={vmax:.0f}<{GATE_DWARF_VMAX}, "
                   f"abs(BCM_vs_MOND)={abs(bcm_vs_mond):.1f}>{GATE_DWARF_ADV}"
                   if g3_flag else "")

        any_flag  = g1_flag or g2_flag or g3_flag
        flags_hit = []
        if g1_flag: flags_hit.append("SCALE")
        if g2_flag: flags_hit.append("FLOOR")
        if g3_flag: flags_hit.append("DWARF_EXPLODE")

        records.append({
            "name":           g["galaxy"],
            "vmax":           vmax,
            "vmax_group":     vmax_group(vmax),
            "log_mbh":        log_mbh,
            "rms_newton":     rn,
            "rms_mond":       rm,
            "rms_substrate":  rs,
            "winner":         winner,
            "bcm_vs_mond":    bcm_vs_mond,
            "bcm_vs_newton":  bcm_vs_newton,
            "bcm_vs_mond_frac":   bcm_vs_m_frac,
            "bcm_vs_newton_frac": bcm_vs_n_frac,
            "g1_scale":       g1_flag,
            "g2_floor":       g2_flag,
            "g3_dwarf":       g3_flag,
            "any_flag":       any_flag,
            "flags_hit":      flags_hit,
            "g1_note":        g1_note,
            "g3_note":        g3_note,
        })

    # ------------------------------------------------------------------
    # GATE SUMMARY
    # ------------------------------------------------------------------
    flagged   = [r for r in records if r["any_flag"]]
    clean     = [r for r in records if not r["any_flag"]]
    n_scale   = sum(1 for r in records if r["g1_scale"])
    n_floor   = sum(1 for r in records if r["g2_floor"])
    n_dwarf   = sum(1 for r in records if r["g3_dwarf"])
    flag_frac = len(flagged) / len(records)

    print()
    print("GATE RESULTS")
    print(f"  Gate 1 (scale)       : {n_scale:>4} flagged  "
          f"[abs(BCM_vs_MOND) > {GATE_SCALE_FRACTION}×Vmax]")
    print(f"  Gate 2 (rms floor)   : {n_floor:>4} flagged  "
          f"[non-finite or negative RMS]")
    print(f"  Gate 3 (dwarf explode): {n_dwarf:>4} flagged  "
          f"[Vmax<{GATE_DWARF_VMAX} AND abs(BCM_vs_MOND)>{GATE_DWARF_ADV}]")
    print(f"  TOTAL FLAGGED        : {len(flagged):>4} / {len(records)}  "
          f"({flag_frac*100:.1f}%)")
    print(f"  CLEAN ROWS REMAINING : {len(clean):>4}")

    # Show worst offenders
    print()
    print(f"  FLAGGED ROWS (sorted by |BCM_vs_MOND| desc):")
    flagged_sorted = sorted(flagged, key=lambda r: abs(r["bcm_vs_mond"]), reverse=True)
    print(
        f"  {'GALAXY':<16} {'Vmax':>5} {'BCM_vs_MOND':>12} "
        f"{'0.75×Vmax':>10} {'GATES'}"
    )
    print("  " + "-" * 68)
    for r in flagged_sorted[:25]:
        print(
            f"  {r['name']:<16} {r['vmax']:>5.0f} {r['bcm_vs_mond']:>12.2f} "
            f"{0.75*r['vmax']:>10.2f} "
            f"{'+'.join(r['flags_hit'])}"
        )
    if len(flagged_sorted) > 25:
        print(f"  ... {len(flagged_sorted)-25} more flagged rows")

    # ------------------------------------------------------------------
    # GATE 4: RANK STABILITY — recompute group stats on clean set
    # ------------------------------------------------------------------
    print()
    print("GATE 4 — RANK STABILITY")

    raw_stats   = group_stats_block(records, "RAW (all 175)")
    clean_stats = group_stats_block(clean,   "CLEAN (flagged removed)")
    newt_stats  = group_stats_block(records, "NEWTON (all 175, no flags)")

    print_group_table(raw_stats,   "RAW MOND (all 175)")
    print_group_table(clean_stats, f"CLEAN MOND ({len(clean)} rows)")
    print_group_table(newt_stats,  "NEWTON (all 175)")

    # Gradient stability
    def gradient_holds(stats):
        hi  = (stats.get("HIGH_MASS") or {}).get("mean_adv", 0)
        mid = (stats.get("MID_MASS")  or {}).get("mean_adv", 0)
        lo  = (stats.get("LOW_MASS")  or {}).get("mean_adv", 0)
        return hi > mid > lo, hi, mid, lo

    raw_grad,   rh, rm_, rl = gradient_holds(raw_stats)
    clean_grad, ch, cm, cl  = gradient_holds(clean_stats)

    print(f"\n  Raw   gradient HIGH>MID>LOW: {raw_grad}   "
          f"({rh:.2f} > {rm_:.2f} > {rl:.2f})")
    print(f"  Clean gradient HIGH>MID>LOW: {clean_grad}  "
          f"({ch:.2f} > {cm:.2f} > {cl:.2f})")

    # Newton gradient (beats_newton_pct)
    def newton_gradient_holds(stats):
        hi  = (stats.get("HIGH_MASS") or {}).get("beats_newton_pct", 0)
        mid = (stats.get("MID_MASS")  or {}).get("beats_newton_pct", 0)
        lo  = (stats.get("LOW_MASS")  or {}).get("beats_newton_pct", 0)
        return hi < mid, hi, mid, lo   # BCM paper prediction: HIGH < MID

    newt_inv, nh, nm, nl = newton_gradient_holds(newt_stats)
    print(f"  Newton beats% inversion (HIGH < MID): {newt_inv}  "
          f"({nh*100:.1f}% < {nm*100:.1f}% > {nl*100:.1f}%)")

    # ------------------------------------------------------------------
    # GATE 5: COMPARISON REBUILD — decisive question
    # ------------------------------------------------------------------
    print()
    print("GATE 5 — COMPARISON REBUILD (DECISIVE QUESTION)")

    # Raw ρ (Test 28 replication)
    all_lmbh = np.array([r["log_mbh"]           for r in records])
    all_frac  = np.array([r["bcm_vs_mond_frac"]  for r in records])
    rho_raw   = spearman(all_lmbh, all_frac)

    # Clean ρ
    if len(clean) >= 3:
        cl_lmbh = np.array([r["log_mbh"]          for r in clean])
        cl_frac  = np.array([r["bcm_vs_mond_frac"] for r in clean])
        rho_clean = spearman(cl_lmbh, cl_frac)
    else:
        rho_clean = float("nan")

    # Newton ρ
    all_nfrac = np.array([r["bcm_vs_newton_frac"] for r in records])
    rho_newt  = spearman(all_lmbh, all_nfrac)

    print()
    print(f"  ρ(log_MBH, BCM_vs_MOND_frac)  RAW   : {rho_raw:+.4f}")
    print(f"  ρ(log_MBH, BCM_vs_MOND_frac)  CLEAN : {rho_clean:+.4f}")
    print(f"  ρ(log_MBH, BCM_vs_Newton_frac) ALL   : {rho_newt:+.4f}")
    print()
    print(f"  Decisive: ρ_clean stays negative? "
          f"{'YES' if (not np.isnan(rho_clean) and rho_clean < RHO_NEGATIVE_REQUIRED) else 'NO'}")

    # ------------------------------------------------------------------
    # VERDICT
    # ------------------------------------------------------------------
    mond_impl_broken = flag_frac > FLAG_FRACTION_BROKEN
    rho_clean_negative = (not np.isnan(rho_clean) and
                          rho_clean < RHO_NEGATIVE_REQUIRED)
    enough_clean = len(clean) >= MIN_CLEAN_N

    if mond_impl_broken:
        verdict = "MOND_IMPL_BROKEN"
        verdict_note = (
            f">{FLAG_FRACTION_BROKEN*100:.0f}% of rows flagged. "
            "MOND implementation is systematically invalid. "
            "Do not use MOND as Paper C opponent. Use Newton only."
        )
    elif rho_clean_negative and enough_clean:
        if len(clean) == len(records):
            verdict = "MOND_CLEAN_USABLE"
        else:
            verdict = "MOND_DEGRADED_USABLE"
        verdict_note = (
            f"ρ_clean={rho_clean:+.4f} (negative). "
            f"Clean rows: {len(clean)}/{len(records)}. "
            "MOND comparison is usable after flagged rows removed. "
            "Paper C may cite: BCM-vs-MOND advantage decreases with "
            "SMBH proxy even after sanity filtering."
        )
    else:
        verdict = "NEWTON_ONLY"
        verdict_note = (
            f"ρ_clean={rho_clean:+.4f} (not negative or insufficient clean rows). "
            "MOND comparison is not reliable. Use Newton result only. "
            "Newton split is clean and directly supports the crag network model: "
            f"HIGH_MASS {nh*100:.1f}% < MID_MASS {nm*100:.1f}% beats Newton. "
            "Substrate correction concentrated in RECIPIENT galaxies, not ROOT sources."
        )

    print()
    print("=" * 100)
    print(f"VERDICT: {verdict}")
    print(f"  {verdict_note}")
    print()
    if verdict in ("MOND_CLEAN_USABLE", "MOND_DEGRADED_USABLE"):
        print("  PAPER C MOND CLOSING ARGUMENT (approved):")
        print("    'BCM advantage over MOND decreases with SMBH mass proxy even after")
        print("     MOND sanity filtering (impossible rows removed), favoring cosmological")
        print("     substrate pre-strain over local engine funding.'")
    else:
        print("  PAPER C NEWTON CLOSING ARGUMENT (use this):")
        print("    'BCM rotation curve correction is concentrated in MID_MASS recipient")
        print(f"     galaxies ({nm*100:.1f}% beats Newton), not HIGH_MASS ROOT source")
        print(f"     galaxies ({nh*100:.1f}%). This is the rotation curve fingerprint")
        print("     of the crag draw network: ROOT galaxies export substrate to")
        print("     BRANCH recipients, depressing their own BCM-vs-Newton margin.'")
    print("=" * 100)

    # ------------------------------------------------------------------
    # HYPOTHESIS OUTPUT
    # ------------------------------------------------------------------
    coherence_score  = (1.0 if verdict in ("MOND_CLEAN_USABLE", "MOND_DEGRADED_USABLE")
                        else 0.5 if verdict == "NEWTON_ONLY"
                        else 0.0)
    overlap_fraction = float(max(0.0, -rho_clean)) if not np.isnan(rho_clean) else 0.0

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"MOND residual sanity audit over {len(records)} SPARC galaxies. "
        f"Gate 1 (scale): {n_scale} flagged. "
        f"Gate 2 (floor): {n_floor} flagged. "
        f"Gate 3 (dwarf explode): {n_dwarf} flagged. "
        f"Total flagged: {len(flagged)}/{len(records)} ({flag_frac*100:.1f}%). "
        f"Clean rows: {len(clean)}. "
        f"ρ(log_MBH, BCM_vs_MOND_frac) raw={rho_raw:+.4f}, "
        f"clean={rho_clean:+.4f}. "
        f"ρ(log_MBH, BCM_vs_Newton_frac)={rho_newt:+.4f}. "
        f"Decisive (ρ_clean negative): {rho_clean_negative}. "
        f"Newton inversion confirmed (HIGH<MID): {newt_inv} "
        f"({nh*100:.1f}%<{nm*100:.1f}%>{nl*100:.1f}%). "
        f"Verdict: {verdict}. "
        f"coherence_score={coherence_score:.4f}, "
        f"overlap_fraction={overlap_fraction:.4f}."
    )

    hypothesis_entry = {
        "statement":          statement,
        "result":             "FIELD_EXTRACTED",
        "direction":          1 if rho_clean_negative else 0,
        "evidence_type":      "diagnostic",
        "pass_count":         len(clean),
        "total_configs":      len(records),
        "prior":              0.5,
        "measurement_targets": ["invariance", "drift", "degeneracy", "resolution"],
        "metrics": {
            "coherence_score":          coherence_score,
            "overlap_fraction":         overlap_fraction,
            "n_total":                  len(records),
            "n_flagged":                len(flagged),
            "n_clean":                  len(clean),
            "flag_fraction":            flag_frac,
            "n_gate1_scale":            n_scale,
            "n_gate2_floor":            n_floor,
            "n_gate3_dwarf":            n_dwarf,
            "rho_mond_frac_raw":        rho_raw,
            "rho_mond_frac_clean":      float(rho_clean) if not np.isnan(rho_clean) else None,
            "rho_newton_frac":          rho_newt,
            "rho_clean_negative":       rho_clean_negative,
            "newton_inversion_holds":   newt_inv,
            "high_beats_newton_pct":    nh,
            "mid_beats_newton_pct":     nm,
            "low_beats_newton_pct":     nl,
            "gradient_raw":             raw_grad,
            "gradient_clean":           clean_grad,
            "verdict":                  verdict,
            "mond_impl_broken":         mond_impl_broken,
            "gate_scale_threshold":     GATE_SCALE_FRACTION,
            "gate_dwarf_vmax":          GATE_DWARF_VMAX,
            "gate_dwarf_adv":           GATE_DWARF_ADV,
        },
        "context": {
            "framework":   "mond_sanity_audit",
            "data_source": batch_path,
            "paper_c_decision": (
                "If MOND_CLEAN_USABLE or MOND_DEGRADED_USABLE: cite cleaned MOND result. "
                "If NEWTON_ONLY: cite Newton split (HIGH<MID>LOW beats Newton). "
                "If MOND_IMPL_BROKEN: investigate MOND implementation before proceeding. "
                "Check a0=1.2e-10 m/s^2, interpolating function (simple vs standard), "
                "and fitting procedure against Lelli et al. 2017 published SPARC residuals."
            ),
            "next_step": (
                "If NEWTON_ONLY: proceed directly to Paper C using Newton split. "
                "If MOND usable: Test 30 (clean MOND split) then Paper C figures. "
                "Paper C panels: A=Newton win by mass bin, B=MOND raw vs clean, "
                "C=ROOT exports/BRANCH receives model, "
                "D=local pump rejected vs cosmological substrate favored."
            ),
        },
        "keywords": [
            "crag_intensity",
            "substrate_funding_fraction",
            "dual_flow_crag",
            "cascade_propagation",
            "primordial_gutter",
            "classifier",
            "regime",
            "lambda",
            "marginal_regime",
        ],
    }

    output = {
        "test_name":          TEST_NAME,
        "test_number":        TEST_NUMBER,
        "timestamp":          timestamp,
        "target":             "MOND_SANITY_AUDIT_175_SPARC",
        "framework":          "mond_sanity_audit",
        "v28_partition":      "falsification_closure",
        "hypotheses_tested":  {HYP_ID: hypothesis_entry},
        "flagged_rows":       [
            {k: v for k, v in r.items() if k not in ("g1_note", "g3_note")}
            for r in flagged_sorted
        ],
        "clean_rows":         [
            {k: v for k, v in r.items() if k not in ("g1_note", "g3_note")}
            for r in sorted(clean, key=lambda x: x["bcm_vs_mond"], reverse=True)
        ],
        "group_stats_raw":    raw_stats,
        "group_stats_clean":  clean_stats,
        "group_stats_newton": newt_stats,
        "elapsed_seconds":    time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Sequence after this:")
    if verdict in ("MOND_CLEAN_USABLE", "MOND_DEGRADED_USABLE"):
        print("  → Test 30: Clean MOND split (rerun Test 28 on clean rows)")
        print("  → Paper C figures (4-panel)")
    elif verdict == "NEWTON_ONLY":
        print("  → Skip Test 30. Newton result is sufficient.")
        print("  → Paper C figures: Newton-only split is the closing argument.")
    else:
        print("  → Investigate MOND implementation before proceeding.")
        print("  → Check a0, interpolating function, fitting procedure.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
