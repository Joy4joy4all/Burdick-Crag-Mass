# -*- coding: utf-8 -*-
"""
BCM_v28_TEST20_CRAG_INTENSITY_TABLE_SCANNER.py

Hypothesis: H_V28_VARIABLE_CRAG_GALAXY_EXPULSION

Statement
---------
Galaxy velocity, morphology, and restoration burden are correlated
with variable primordial crag intensity. Barred galaxies represent
stronger substrate-current organized restoration structures (ROOT /
BRANCH crag nodes). Flocculent and late-type galaxies represent
lower-coherence distributed restoration (LEAF / VOID-EDGE nodes).
Each galaxy is not formed randomly after expansion — it is a
restoration artifact organized around a primordial crag tare.

Crag Intensity Index
--------------------
C_I = J_amp × σ_deficit

Where:
    J_amp         = substrate injection amplitude (normalized to NGC 5055 = 8.0)
    σ_deficit     = total substrate displaced per pierce
                  = SIGMA_CRIT × (J_amp / J_REF) × N_HALF

J_amp estimation from Vmax (no per-galaxy tuning):
    J_amp = (Vmax_kms / VMAX_REF)^2 × J_REF
    VMAX_REF = 206 km/s (NGC 5055 Test 13 reference)
    J_REF    = 8.0

Classification
--------------
C_I > 1e-1         : ROOT CRAG     (high-velocity organized restoration)
1e-2 < C_I ≤ 1e-1 : BRANCH CRAG   (intermediate restoration structure)
1e-3 < C_I ≤ 1e-2 : LEAF CRAG     (distributed low-coherence restoration)
C_I ≤ 1e-3         : VOID-EDGE     (substrate healing primordial void boundary)

Galaxy catalog
--------------
PHANGS-JWST survey (19 targets) + BCM established (Tests 13-18) + SPARC anchors.
A_CMB is placeholder 0.0 for all entries — Planck gradient data not yet ingested.

ΔW computed from pierce model at 12,000c (STARGATE velocity, peak resonance).

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
# PATH RESOLUTION  (two-level climb: TITS_EPICt_BCM/BCM_EPIC_OpT_tests → root)
# ============================================================================
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_SOLVER_ROOT  = os.path.dirname(os.path.dirname(_THIS_DIR))
_DATA_RESULTS = os.path.join(_SOLVER_ROOT, "data", "results")

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_TEST20_CRAG_INTENSITY_TABLE_SCANNER"
TEST_NUMBER = 20
HYP_ID      = "H_V28_VARIABLE_CRAG_GALAXY_EXPULSION"

# ============================================================================
# BCM FROZEN CONSTANTS
# ============================================================================
SIGMA_CRIT  = 5.0e-4
J_REF       = 8.0          # NGC 5055 Test 13 reference amplitude
VMAX_REF    = 206.0         # NGC 5055 peak circular velocity (km/s)
N_HALF      = 60            # pierce steps per phase (Test 18 value)

# Pierce model (12,000c ENTRY, peak STARGATE resonance)
V_PIERCE    = 12000.0       # c units
F_REF       = 144.0         # reference torus frequency (Hz)
ALPHA_EX    = 0.006
BETA_DM     = 0.003
DT_P        = 0.015

# Crag classification thresholds (SJB 2026)
CI_ROOT     = 1.0e-1
CI_BRANCH   = 1.0e-2
CI_LEAF     = 1.0e-3

# ============================================================================
# GALAXY CATALOG
# ============================================================================
# Fields: name, morphology, distance_mpc, vmax_kms, sparc, jwst_survey, notes
#
# vmax_kms: peak circular velocity from literature or estimated from morphology
# sparc:    True if in the 175-galaxy SPARC rotation curve catalog
# jwst:     JWST program that has characterized this galaxy
# ============================================================================
CATALOG = [
    # ---- BCM ESTABLISHED TARGETS ----------------------------------------
    {   "name": "NGC 5055",  "morphology": "SAbc",       "distance_mpc":  8.0,
        "vmax_kms": 206.0,   "sparc": True,  "jwst": "PHANGS-JWST",
        "notes": "Test 13 baseline (J_amp=8.0); Sunflower Galaxy",
        "j_amp_override": 8.0  },
    {   "name": "Bootes Void", "morphology": "void",     "distance_mpc": 700.0,
        "vmax_kms":   8.0,   "sparc": False, "jwst": "none",
        "notes": "Test 14 M-suppressed anchor; unfunded substrate",
        "j_amp_override": 0.5  },
    {   "name": "NGC 7496",  "morphology": "SBbc",       "distance_mpc": 18.7,
        "vmax_kms": 169.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "Test 18; bar = natural waveguide; J_amp=7.0",
        "j_amp_override": 7.0  },
    {   "name": "IC 5332",   "morphology": "SABcd",      "distance_mpc":  9.0,
        "vmax_kms": 119.0,   "sparc": False, "jwst": "JWST-ERS",
        "notes": "Test 18; flocculent; J_amp=3.5",
        "j_amp_override": 3.5  },
    {   "name": "NGC 3137",  "morphology": "SABc",       "distance_mpc": 53.0,
        "vmax_kms": 160.0,   "sparc": False, "jwst": "none",
        "notes": "Test 15 target; Antlia Group; 2x NGC5055 distance",
        "j_amp_override": None },
    {   "name": "NGC 3175",  "morphology": "SABab",      "distance_mpc": 53.0,
        "vmax_kms": 185.0,   "sparc": False, "jwst": "none",
        "notes": "Test 16 paired target; Antlia Group anchor",
        "j_amp_override": None },

    # ---- PHANGS-JWST SURVEY (remaining 14 targets not yet in BCM) --------
    {   "name": "NGC 628",   "morphology": "SAc",        "distance_mpc":  9.8,
        "vmax_kms": 217.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "M74 / Phantom Galaxy; grand design spiral",
        "j_amp_override": None },
    {   "name": "NGC 1087",  "morphology": "SABc",       "distance_mpc": 15.9,
        "vmax_kms": 136.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "PHANGS target",
        "j_amp_override": None },
    {   "name": "NGC 1300",  "morphology": "SBbc",       "distance_mpc": 19.0,
        "vmax_kms": 195.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "Grand barred spiral",
        "j_amp_override": None },
    {   "name": "NGC 1365",  "morphology": "SBb",        "distance_mpc": 18.1,
        "vmax_kms": 285.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "Fornax cluster; massive barred spiral; Seyfert AGN",
        "j_amp_override": None },
    {   "name": "NGC 1385",  "morphology": "SBcd",       "distance_mpc": 18.2,
        "vmax_kms": 140.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "PHANGS target",
        "j_amp_override": None },
    {   "name": "NGC 1433",  "morphology": "SBab",       "distance_mpc":  9.7,
        "vmax_kms": 190.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "PHANGS target; inner ring structure",
        "j_amp_override": None },
    {   "name": "NGC 1566",  "morphology": "SABbc",      "distance_mpc": 17.7,
        "vmax_kms": 210.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "Spanish Dancer; Dorado group",
        "j_amp_override": None },
    {   "name": "NGC 1672",  "morphology": "SBb",        "distance_mpc": 11.9,
        "vmax_kms": 230.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "Starburst barred; strong bar; JWST early science",
        "j_amp_override": None },
    {   "name": "NGC 2835",  "morphology": "SABc",       "distance_mpc": 12.2,
        "vmax_kms": 155.0,   "sparc": True,  "jwst": "PHANGS-JWST",
        "notes": "In SPARC; PHANGS target",
        "j_amp_override": None },
    {   "name": "NGC 3351",  "morphology": "SBb",        "distance_mpc":  9.96,
        "vmax_kms": 192.0,   "sparc": True,  "jwst": "PHANGS-JWST",
        "notes": "M95; Leo group barred; in SPARC",
        "j_amp_override": None },
    {   "name": "NGC 3627",  "morphology": "SABb",       "distance_mpc": 11.3,
        "vmax_kms": 215.0,   "sparc": True,  "jwst": "PHANGS-JWST",
        "notes": "M66; Leo Triplet; in SPARC",
        "j_amp_override": None },
    {   "name": "NGC 4254",  "morphology": "SAc",        "distance_mpc": 13.1,
        "vmax_kms": 220.0,   "sparc": True,  "jwst": "PHANGS-JWST",
        "notes": "M99; Virgo cluster; in SPARC",
        "j_amp_override": None },
    {   "name": "NGC 4321",  "morphology": "SABbc",      "distance_mpc": 15.2,
        "vmax_kms": 230.0,   "sparc": True,  "jwst": "PHANGS-JWST",
        "notes": "M100; Virgo cluster grand design; in SPARC",
        "j_amp_override": None },
    {   "name": "NGC 5068",  "morphology": "SBd",        "distance_mpc":  5.2,
        "vmax_kms":  95.0,   "sparc": False, "jwst": "PHANGS-JWST",
        "notes": "Late-type low-mass; nearest PHANGS target",
        "j_amp_override": None },
    {   "name": "M74",       "morphology": "SAc",        "distance_mpc":  9.8,
        "vmax_kms": 217.0,   "sparc": False, "jwst": "JWST-ERS",
        "notes": "Phantom Galaxy; same as NGC 628 — JWST ERS observation",
        "j_amp_override": None },
]


# ============================================================================
# PIERCE MODEL (12,000c single-velocity)
# ============================================================================

def estimate_f_base(morphology):
    """Torus base frequency from morphology (BCM proxy)."""
    morph = morphology.upper()
    if "SB" in morph and morph not in ("SBD", "SBdm"):
        return 148.0    # barred: bar channels flux → elevated
    if morph in ("SAc", "SABc", "SABbc", "SAbc", "SAb"):
        return 146.0
    return 144.0        # late-type / flocculent / void


def run_pierce_12kc(j_amp, f_base):
    """
    Burdick Coupling pierce at 12,000c ENTRY phase.
    Returns ΔW (proxy) and sigma_deficit.
    """
    sigma_peak = SIGMA_CRIT * (j_amp / J_REF)

    delta_W_accum = 0.0

    for step in range(N_HALF):
        t = step / N_HALF
        sig_local = float(sigma_peak * np.sin(np.pi * t / 2.0) ** 2)

        f_craft   = (V_PIERCE / 100.0) * (1.0 + sig_local)
        phase_err = 2.0 * np.pi * (f_craft - f_base) * DT_P
        R         = float(np.cos(phase_err))

        d_sigma    = ALPHA_EX * R - BETA_DM * np.sign(R) * R ** 2
        delta_W_accum += R * d_sigma

    sigma_deficit = sigma_peak * N_HALF   # total substrate displaced
    return float(delta_W_accum), float(sigma_deficit)


# ============================================================================
# CRAG CLASSIFIER
# ============================================================================

def classify_crag(c_i, void_adjacent=False):
    if void_adjacent and c_i <= CI_LEAF:
        return "VOID-EDGE"
    if c_i > CI_ROOT:
        return "ROOT"
    if c_i > CI_BRANCH:
        return "BRANCH"
    if c_i > CI_LEAF:
        return "LEAF"
    return "VOID-EDGE"


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()

    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 108)
    print(f"BCM v28 TEST {TEST_NUMBER} — CRAG INTENSITY TABLE SCANNER")
    print(f"Hypothesis : {HYP_ID}")
    print(f"Galaxies   : {len(CATALOG)}")
    print(f"Pierce velocity: {V_PIERCE:.0f}c  (STARGATE peak)")
    print(f"C_I = J_amp × σ_deficit")
    print("=" * 108)

    header = (
        f"{'GALAXY':<14} {'MORPH':<10} {'Vmax':>5} {'dist':>6} "
        f"{'J_amp':>6} {'σ_def':>10} {'ΔW':>12} "
        f"{'restore':>10} {'C_I':>12} {'A_CMB':>7} {'CLASS':<12} {'SPARC'}"
    )
    print()
    print(header)
    print("-" * 108)

    rows = []

    root_count   = 0
    branch_count = 0
    leaf_count   = 0
    void_count   = 0

    for g in CATALOG:
        name     = g["name"]
        morph    = g["morphology"]
        dist     = g["distance_mpc"]
        vmax     = g["vmax_kms"]
        sparc    = g["sparc"]
        notes    = g["notes"]
        override = g.get("j_amp_override")

        # J_amp: use override if set, else derive from Vmax
        if override is not None:
            j_amp = float(override)
        else:
            j_amp = max(0.1, (vmax / VMAX_REF) ** 2 * J_REF)

        f_base = estimate_f_base(morph)

        delta_W, sigma_deficit = run_pierce_12kc(j_amp, f_base)

        restoration_effort = sigma_deficit / (j_amp + 1e-9)
        c_i                = j_amp * sigma_deficit

        # A_CMB placeholder — Planck data not yet ingested
        a_cmb  = 0.0
        void_adj = "void" in morph.lower() or name == "Bootes Void"
        crag_class = classify_crag(c_i, void_adjacent=void_adj)

        if crag_class == "ROOT":      root_count   += 1
        elif crag_class == "BRANCH":  branch_count += 1
        elif crag_class == "LEAF":    leaf_count   += 1
        else:                         void_count   += 1

        row = {
            "name":               name,
            "morphology":         morph,
            "distance_mpc":       dist,
            "vmax_kms":           vmax,
            "j_amp":              round(j_amp, 4),
            "f_base_hz":          f_base,
            "sigma_deficit":      sigma_deficit,
            "delta_W_12kc":       delta_W,
            "restoration_effort": restoration_effort,
            "crag_intensity":     c_i,
            "A_CMB":              a_cmb,
            "A_CMB_status":       "placeholder_Planck_not_ingested",
            "crag_class":         crag_class,
            "sparc":              sparc,
            "notes":              notes,
        }
        rows.append(row)

        print(
            f"{name:<14} {morph:<10} {vmax:>5.0f} {dist:>6.1f} "
            f"{j_amp:>6.3f} {sigma_deficit:>10.4e} {delta_W:>12.4e} "
            f"{restoration_effort:>10.4e} {c_i:>12.4e} "
            f"{a_cmb:>7.3f} {crag_class:<12} {'Y' if sparc else 'N'}"
        )

    # Sort by C_I descending for summary
    rows_sorted = sorted(rows, key=lambda r: r["crag_intensity"], reverse=True)

    print()
    print("=" * 108)
    print("CRAG CLASSIFICATION SUMMARY")
    print(f"  ROOT    (C_I > {CI_ROOT:.0e}): {root_count}")
    print(f"  BRANCH  (C_I > {CI_BRANCH:.0e}): {branch_count}")
    print(f"  LEAF    (C_I > {CI_LEAF:.0e}): {leaf_count}")
    print(f"  VOID-EDGE               : {void_count}")
    print()
    print("TOP 5 CRAG INTENSITY:")
    for r in rows_sorted[:5]:
        print(f"  {r['name']:<14} C_I={r['crag_intensity']:.4e}  {r['crag_class']}")
    print()
    print("BOTTOM 5 (weakest restoration signal):")
    for r in rows_sorted[-5:]:
        print(f"  {r['name']:<14} C_I={r['crag_intensity']:.4e}  {r['crag_class']}")
    print("=" * 108)

    # Hypothesis metrics
    c_i_values     = [r["crag_intensity"] for r in rows]
    c_i_barred     = [r["crag_intensity"] for r in rows
                      if "SB" in r["morphology"].upper()
                      and r["morphology"].upper() not in ("SBCD", "SBD")]
    c_i_flocculent = [r["crag_intensity"] for r in rows
                      if r["morphology"].upper() in ("SABC", "SABCD", "SABcd",
                                                      "SBD", "SABc", "SAc")]

    mean_barred     = float(np.mean(c_i_barred))     if c_i_barred     else 0.0
    mean_flocculent = float(np.mean(c_i_flocculent)) if c_i_flocculent else 0.0
    ratio_bar_floc  = mean_barred / (mean_flocculent + 1e-30)

    # coherence_score: fraction of barred galaxies that are ROOT or BRANCH
    barred_rows = [r for r in rows
                   if "SB" in r["morphology"].upper()
                   and r["morphology"].upper() not in ("SBCD", "SBD")]
    barred_high = sum(1 for r in barred_rows
                      if r["crag_class"] in ("ROOT", "BRANCH"))
    coherence_score  = float(barred_high / len(barred_rows)) if barred_rows else 0.0

    # overlap_fraction: fraction of all galaxies correctly classified
    # (ROOT/BRANCH = barred/grand-design; LEAF/VOID = late/flocculent/void)
    correct = sum(
        1 for r in rows
        if (r["crag_class"] in ("ROOT", "BRANCH")
            and ("SB" in r["morphology"].upper() or r["vmax_kms"] > 190))
        or (r["crag_class"] in ("LEAF", "VOID-EDGE")
            and r["vmax_kms"] < 130)
    )
    overlap_fraction = float(correct / len(rows))

    print(f"coherence_score  (barred → ROOT/BRANCH rate): {coherence_score:.4f}")
    print(f"overlap_fraction (morphology/class agreement): {overlap_fraction:.4f}")
    print(f"mean C_I barred     : {mean_barred:.4e}")
    print(f"mean C_I flocculent : {mean_flocculent:.4e}")
    print(f"ratio bar/floc C_I  : {ratio_bar_floc:.2f}×")

    # -----------------------------------------------------------------------
    # HYPOTHESIS OUTPUT (Test 13 pattern)
    # -----------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    statement = (
        f"Crag Intensity Table Scanner over {len(CATALOG)} galaxies "
        f"(PHANGS-JWST + BCM established + SPARC anchors). "
        f"C_I = J_amp × σ_deficit where J_amp ∝ (Vmax/Vmax_ref)^2. "
        f"Pierce at {V_PIERCE:.0f}c (STARGATE velocity). "
        f"Classification: ROOT (C_I>{CI_ROOT:.0e}), "
        f"BRANCH (C_I>{CI_BRANCH:.0e}), LEAF (C_I>{CI_LEAF:.0e}), VOID-EDGE. "
        f"ROOT={root_count}, BRANCH={branch_count}, "
        f"LEAF={leaf_count}, VOID-EDGE={void_count}. "
        f"Mean C_I barred={mean_barred:.4e}, "
        f"flocculent={mean_flocculent:.4e}, "
        f"ratio={ratio_bar_floc:.2f}×. "
        f"coherence_score (barred→ROOT/BRANCH rate)={coherence_score:.4f}. "
        f"overlap_fraction (morphology/class agreement)={overlap_fraction:.4f}. "
        f"Top crag: {rows_sorted[0]['name']} "
        f"C_I={rows_sorted[0]['crag_intensity']:.4e} ({rows_sorted[0]['crag_class']}). "
        f"A_CMB is placeholder 0.0 for all entries — "
        f"Planck gradient overlay is the next step for this table. "
        f"Hypothesis: barred galaxies are organized ROOT/BRANCH crag nodes "
        f"of a primordial substrate restoration network; "
        f"flocculent and late-type galaxies are LEAF or VOID-EDGE nodes."
    )

    hypothesis_entry = {
        "statement":     statement,
        "result":        "FIELD_EXTRACTED",
        "direction":     1 if coherence_score > 0.5 else 0,
        "evidence_type": "primary",
        "pass_count":    barred_high,
        "total_configs": len(CATALOG),
        "prior":         0.5,
        "measurement_targets": [
            "invariance", "drift", "degeneracy", "resolution",
        ],
        "metrics": {
            # Dual-gate
            "coherence_score":        coherence_score,
            "overlap_fraction":       overlap_fraction,
            # Crag statistics
            "n_galaxies":             len(CATALOG),
            "n_root":                 root_count,
            "n_branch":               branch_count,
            "n_leaf":                 leaf_count,
            "n_void_edge":            void_count,
            "mean_ci_barred":         mean_barred,
            "mean_ci_flocculent":     mean_flocculent,
            "ratio_barred_flocculent": ratio_bar_floc,
            "top_crag_galaxy":        rows_sorted[0]["name"],
            "top_crag_ci":            rows_sorted[0]["crag_intensity"],
            "top_crag_class":         rows_sorted[0]["crag_class"],
            # Thresholds
            "ci_root_threshold":      CI_ROOT,
            "ci_branch_threshold":    CI_BRANCH,
            "ci_leaf_threshold":      CI_LEAF,
            # Model parameters
            "j_ref":                  J_REF,
            "vmax_ref_kms":           VMAX_REF,
            "sigma_crit":             SIGMA_CRIT,
            "pierce_velocity_c":      V_PIERCE,
            "n_half_steps":           N_HALF,
            # A_CMB status
            "a_cmb_status":           "placeholder_all_zero_Planck_not_ingested",
        },
        "context": {
            "framework":      "crag_intensity_table_scanner",
            "sparc_overlap":  sum(1 for r in rows if r["sparc"]),
            "jwst_targets":   sum(1 for r in rows if r["sparc"] is False
                                  and "PHANGS" in r.get("notes", "")),
            "next_step":      (
                "Overlay Planck CMB gradient map → compute real A_CMB per galaxy. "
                "Test whether ROOT crags cluster in CMB hot-spot regions "
                "(high primordial strain) vs LEAF crags in cold-spot / void regions."
            ),
        },
        "keywords": [
            "primordial_gutter",
            "gutter_depth",
            "pierce_gauntlet",
            "cmb_prestrain",
            "a_cmb",
            "sigma_eff",
            "anchor_projection",
            "classifier",
            "regime",
            "lambda",
        ],
    }

    output = {
        "test_name":    TEST_NAME,
        "test_number":  TEST_NUMBER,
        "timestamp":    timestamp,
        "target":       "JWST_SPARC_Crag_Network_Survey",
        "framework":    "crag_intensity_table_scanner",
        "v28_partition": "primordial_gutter (data/results/)",
        "hypotheses_tested": {HYP_ID: hypothesis_entry},
        "catalog":      rows_sorted,   # sorted by C_I descending
        "elapsed_seconds": time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    print()
    print(f"JSON written : {out_path}")
    print(f"Elapsed      : {time.time() - t0:.1f}s")
    print()
    print("Next: EPIC COLLECTOR → INGEST SELECTED → REFRESH Q-CUBE → AUTO-10")
    print(f"      {HYP_ID} will be tracked.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
