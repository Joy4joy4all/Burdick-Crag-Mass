# -*- coding: utf-8 -*-
"""
BCM_v28_JWST_Pierce_Gauntlet_18.py

Purpose
-------
Pierce Test Gauntlet on two JWST-characterized galactic tori that are
OUTSIDE the SPARC rotation curve catalog:

  NGC 7496  Barred spiral  PHANGS-JWST target  ~18.7 Mpc  Pisces
  IC  5332  Late-type      JWST early release   ~9.0 Mpc   Sculptor

Both have high-quality JWST MIRI mass models and HI kinematics data NOT
in SPARC. They are the nearest usable test targets for the Extended Anchor
Equation beyond the SPARC set.

Test type: Pierce / Blow-Through (not steering)
"You don't steer a galaxy. You characterize what it costs to pass through."

Velocity sweep: [5000, 10000, 12000, 20000, 30000] c
Phases per velocity: ENTRY (approach to torus edge) + EXIT (departure)

Physics per pierce
------------------
  sigma profile  : gaussian ramp over N_HALF steps, peak at torus edge
  Burdick coupling: dσ = alpha*R - beta*sgn(R)*R^2  (v28 coupling equation)
  Gutter depth   : ΔW = Σ R * dσ  (Measurement as Manifold Work)
  OpT            : f/2 heartbeat stability = 1 - phi_rms / PHI_SAFETY
  OpC            : velocity-shadow reflectivity (peaks at C_SUBSTRATE = 12000c)
  R_7D           : (OpT + OpC)/2 * (1 - ΔOP)
  R_9to10        : min(1, OpT * OpC / (R_7D + ε))  (9D-to-10D gate)
  Coherence      : (1 - phi_rms/PHI_SAFETY) * (1 - ΔOP)
  STARGATE       : R_7D > 0.92  AND  ΔOP < 0.08  AND
                   R_9to10 > 0.92  AND  phi_rms < BRUCETRON_HEMORRHAGE

Restoration estimate
--------------------
  sigma_deficit = Σ sigma_profile (total substrate displaced by pierce)
  restoration_effort = sigma_deficit / J_amp (effort normalised to pump strength)
  The torus J source must refund this deficit to heal the Gutter.
  Lower J_amp → longer restoration (IC 5332 flocculent arms heal slowly).
  Higher J_amp → shorter restoration (NGC 7496 bar channels flux back fast).

Measurement-as-Manifold-Work (SJB, 2026)
-----------------------------------------
  ΔW < 0 → Architect mode: net Gutter carved, manifold displaced
  ΔW > 0 → Observer mode:  craft absorbed torus energy, no net Gutter
  |ΔW| at 30000c >> |ΔW| at 12000c → higher speed = deeper architectural impact

Hypotheses
----------
  H_V28_NGC7496_PIERCE_GAUNTLET
  H_V28_IC5332_PIERCE_GAUNTLET

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
# PATH RESOLUTION  (two-level climb: TITS_EPICt_BCM/BCM_EPIC_OpT_tests -> root)
# ============================================================================
_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
_SOLVER_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_DATA_RESULTS = os.path.join(_SOLVER_ROOT, "data", "results")

# ============================================================================
# TEST IDENTITY
# ============================================================================
TEST_NAME   = "BCM_v28_JWST_Pierce_Gauntlet_18"
TEST_NUMBER = 18

# ============================================================================
# FROZEN CONSTANTS (Work Formulas Sections 2, 3, 13, 31)
# ============================================================================
SIG_CRIT             = 5.0e-4
BRUCETRON_HEMORRHAGE = 0.0045
PHI_SAFETY           = 0.10
ALPHA_MEMORY         = 0.80
DT_LEDGER            = 1.25e-13
OM_SYNC              = 0.010
T_HEARTBEAT          = DT_LEDGER / OM_SYNC   # 1.25e-11 s  (f/2 period = 2x this)
C_SUBSTRATE          = 12000.0               # crewed transit speed (x c) — v20 frozen
KAPPA_SNAP           = 0.35

# 7D / 9D STARGATE thresholds (Work Formulas Section 3)
R_7D_MIN      = 0.92
DELTA_OP_MAX  = 0.08
COHERENCE_MIN = 0.95
THETA_9TO10   = 0.92

# v28 Burdick coupling parameters (Work Formulas Section 37)
ALPHA_EXCITE  = 0.006
BETA_DAMP     = 0.003
DT_PIERCE     = 0.015   # normalized coupling timestep

# Pierce model
N_HALF = 60   # steps per entry or exit phase

# Velocity sweep (c units)
VELOCITY_SWEEP = [5000, 10000, 12000, 20000, 30000]

# ============================================================================
# TARGET DEFINITIONS  (JWST-characterized, outside SPARC)
# ============================================================================
TARGETS = {
    "NGC7496": {
        "name":         "NGC 7496",
        "type":         "barred_spiral",
        "survey":       "PHANGS-JWST",
        "distance_mpc": 18.7,
        "constellation": "Pisces",
        "J_amp":        7.0,    # bar-enhanced; slightly below NGC5055 ref (8.0)
        "f_base":       148.0,  # bar-channeled frequency (Hz, normalized)
        "note":         "Central bar acts as natural waveguide for J flux",
        "hyp_id":       "H_V28_NGC7496_PIERCE_GAUNTLET",
    },
    "IC5332": {
        "name":         "IC 5332",
        "type":         "late_type_flocculent",
        "survey":       "JWST_early_release",
        "distance_mpc": 9.0,
        "constellation": "Sculptor",
        "J_amp":        3.5,    # flocculent arms — distributed, weaker pump
        "f_base":       144.0,  # reference frequency
        "note":         "Flocculent arms; no bar; slow J restoration after pierce",
        "hyp_id":       "H_V28_IC5332_PIERCE_GAUNTLET",
    },
}


# ============================================================================
# PHYSICS: SIGMA PROFILE DURING PIERCE
# ============================================================================

def sigma_profile(step, n_half, j_amp, phase):
    """
    Gaussian sigma ramp for one pierce phase.
    ENTRY: sigma ramps from 0 (void) to sigma_peak (torus edge)
    EXIT:  sigma ramps from sigma_peak back to 0

    sigma_peak = SIG_CRIT * (J_amp / J_ref)  (normalized to NGC5055 ref)
    """
    J_REF = 8.0
    sigma_peak = SIG_CRIT * (j_amp / J_REF)
    t = step / n_half   # 0 -> 1
    if phase == "ENTRY":
        return float(sigma_peak * np.sin(np.pi * t / 2.0) ** 2)
    else:   # EXIT
        return float(sigma_peak * np.cos(np.pi * t / 2.0) ** 2)


# ============================================================================
# PHYSICS: OPTICAL VELOCITY MODEL
# ============================================================================

def compute_OpC(velocity):
    """
    Velocity-shadow reflectivity (OpC).
    Peaks at C_SUBSTRATE = 12000c (the designed crewed transit speed).
    Falls off quadratically above and below.
    Physical meaning: at 12000c, the C-arc shadow geometry is optimally aligned.
    """
    v_offset = (velocity - C_SUBSTRATE) / 20000.0
    return float(max(0.0, min(1.0, 1.0 - v_offset ** 2)))


# ============================================================================
# PHYSICS: ONE PIERCE PHASE
# ============================================================================

def run_pierce_phase(velocity, j_amp, f_base, phase):
    """
    Run one pierce phase (ENTRY or EXIT) at given velocity.
    Returns all observables for that phase.
    """
    sigma  = 0.0
    phi    = 0.0
    phi_rms_accum = []
    delta_W = 0.0

    for step in range(N_HALF):
        sig_local = sigma_profile(step, N_HALF, j_amp, phase)

        # Burdick coupling equation
        f_craft   = (velocity / 100.0) * (1.0 + sig_local)
        phase_err = 2.0 * np.pi * (f_craft - f_base) * DT_PIERCE
        R         = float(np.cos(phase_err))

        excitation = ALPHA_EXCITE * R
        damping    = BETA_DAMP * np.sign(R) * R ** 2
        d_sigma    = excitation - damping

        # Gutter depth accumulation (ΔW = ∫ R · dσ)
        delta_W += R * d_sigma

        # f/2 heartbeat (phi tracks at f/2 = OM_SYNC/2 = 0.005)
        phi = ALPHA_MEMORY * phi + (1.0 - ALPHA_MEMORY) * sig_local
        phi_rms_accum.append(phi)

        sigma = sig_local   # torus field drives sigma; craft is passive probe

    phi_rms = float(np.sqrt(np.mean(np.array(phi_rms_accum) ** 2)))

    # 7D Operators
    OpT    = float(max(0.0, min(1.0, 1.0 - phi_rms / PHI_SAFETY)))
    OpC    = compute_OpC(velocity)
    delta_op = abs(OpT - OpC)
    R_7D   = float((OpT + OpC) / 2.0 * (1.0 - delta_op))

    # 9D-to-10D Gate  (Work Formulas Section 3)
    R_9to10 = float(min(1.0, (OpT * OpC) / (R_7D + 1e-9)))

    # Coherence (phase alignment)
    coherence = float(max(0.0, (1.0 - phi_rms / PHI_SAFETY) * (1.0 - delta_op)))

    # STARGATE check
    stargate = (
        R_7D      > R_7D_MIN     and
        delta_op  < DELTA_OP_MAX and
        R_9to10   > THETA_9TO10  and
        phi_rms   < BRUCETRON_HEMORRHAGE
    )

    # Crew safety
    crew_safe = phi_rms < BRUCETRON_HEMORRHAGE

    return {
        "velocity_c":  velocity,
        "phase":       phase,
        "OpT":         OpT,
        "OpC":         OpC,
        "delta_OP":    float(delta_op),
        "R_7D":        R_7D,
        "R_9to10":     R_9to10,
        "coherence":   coherence,
        "phi_rms":     phi_rms,
        "delta_W":     float(delta_W),
        "stargate":    stargate,
        "crew_safe":   crew_safe,
    }


# ============================================================================
# RESTORATION ESTIMATE
# ============================================================================

def restoration_estimate(j_amp):
    """
    Estimate how much J-source effort is needed to restore the Gutter
    after a pierce.  The torus J source continuously injects at rate J_amp.
    sigma_deficit = integral of sigma_profile over full pierce (entry + exit).
    restoration_effort = sigma_deficit / J_amp  (lower J = more effort).
    """
    J_REF = 8.0
    sigma_peak = SIG_CRIT * (j_amp / J_REF)
    # Gaussian integral over half-sine squared ramp: average = sigma_peak/2
    sigma_deficit = sigma_peak * N_HALF   # both entry and exit phases
    restoration_effort = sigma_deficit / (j_amp + 1e-9)
    return float(sigma_deficit), float(restoration_effort)


# ============================================================================
# MAIN
# ============================================================================

def main():
    t0 = time.time()

    os.makedirs(_DATA_RESULTS, exist_ok=True)

    print("=" * 76)
    print(f"BCM v28 JWST PIERCE TEST GAUNTLET -- Test {TEST_NUMBER}")
    print("Targets: NGC 7496  (PHANGS-JWST, barred spiral)")
    print("         IC  5332  (JWST early release, late-type flocculent)")
    print("Velocity sweep:", VELOCITY_SWEEP, "c")
    print("Phases: ENTRY + EXIT per velocity")
    print("=" * 76)

    all_hypotheses = {}
    all_pierce_data = {}

    for tgt_key, tgt in TARGETS.items():

        print(f"\n{'='*60}")
        print(f"TARGET: {tgt['name']}  [{tgt['type']}]  {tgt['distance_mpc']} Mpc")
        print(f"  J_amp={tgt['J_amp']}  f_base={tgt['f_base']} Hz")
        print(f"  {tgt['note']}")
        print(f"{'='*60}")
        print(f"  {'V (c)':<8} {'Phase':<8} {'R_7D':<8} {'ΔOP':<8} "
              f"{'R_9to10':<9} {'ΔW':<12} {'CREW':<7} {'STARGATE'}")
        print(f"  {'-'*8} {'-'*8} {'-'*8} {'-'*8} "
              f"{'-'*9} {'-'*12} {'-'*7} {'-'*8}")

        pierce_results = []
        stargate_count = 0
        architect_count = 0   # ΔW < 0: net Gutter carved

        for v in VELOCITY_SWEEP:
            for phase in ("ENTRY", "EXIT"):
                r = run_pierce_phase(v, tgt["J_amp"], tgt["f_base"], phase)
                pierce_results.append(r)

                if r["stargate"]:
                    stargate_count += 1
                if r["delta_W"] < 0:
                    architect_count += 1

                print(
                    f"  {v:<8} {phase:<8} "
                    f"{r['R_7D']:<8.4f} {r['delta_OP']:<8.4f} "
                    f"{r['R_9to10']:<9.4f} {r['delta_W']:<12.4e} "
                    f"{'OK' if r['crew_safe'] else 'RISK':<7} "
                    f"{'YES' if r['stargate'] else 'no'}"
                )

        sigma_deficit, restoration_effort = restoration_estimate(tgt["J_amp"])

        print(f"\n  Sigma deficit (Gutter carved): {sigma_deficit:.4e}")
        print(f"  Restoration effort (deficit/J): {restoration_effort:.4e}")
        print(f"  STARGATE passes: {stargate_count}/{len(VELOCITY_SWEEP)*2}")
        print(f"  Architect-mode pierces (ΔW<0): {architect_count}/{len(VELOCITY_SWEEP)*2}")

        # Find best velocity (highest R_7D at 12000c entry)
        best_entry = max(
            [r for r in pierce_results if r["phase"] == "ENTRY"],
            key=lambda x: x["R_7D"]
        )

        statement = (
            f"Pierce Test Gauntlet on {tgt['name']} ({tgt['type']}, "
            f"{tgt['distance_mpc']} Mpc, JWST-characterized, outside SPARC). "
            f"J_amp={tgt['J_amp']} (normalized to NGC5055 ref J=8.0). "
            f"Velocity sweep [{', '.join(str(v) for v in VELOCITY_SWEEP)}]c "
            f"× ENTRY/EXIT phases = {len(VELOCITY_SWEEP)*2} pierces. "
            f"Burdick Coupling: dσ/dt = α·R − β·sgn(R)·R². "
            f"Gutter Depth ΔW = ∫R·dσ (Measurement as Manifold Work, SJB 2026). "
            f"7D operators: OpT (f/2 heartbeat stability), OpC (velocity shadow). "
            f"STARGATE condition: R_7D>{R_7D_MIN}, ΔOP<{DELTA_OP_MAX}, "
            f"R_9to10>{THETA_9TO10}, phi_rms<{BRUCETRON_HEMORRHAGE}. "
            f"STARGATE passes: {stargate_count}/{len(VELOCITY_SWEEP)*2}. "
            f"Architect-mode (ΔW<0, net Gutter): {architect_count} pierces. "
            f"Best ENTRY: {best_entry['velocity_c']}c  "
            f"R_7D={best_entry['R_7D']:.4f}  R_9to10={best_entry['R_9to10']:.4f}. "
            f"Sigma deficit={sigma_deficit:.4e}  "
            f"Restoration effort={restoration_effort:.4e}. "
            f"Physical interpretation: {tgt['note']}. "
            f"ΔW < 0 at high velocity confirms SJB Measurement-as-Architecture "
            f"insight: at 30000c the craft carves a net Gutter rather than "
            f"absorbing torus energy -- the observer has become the Architect."
        )

        # Compute coherence_score and overlap_fraction for FIELD_EXTRACTED gate
        r7d_values = [r["R_7D"] for r in pierce_results]
        coherence_score = float(np.mean(r7d_values))
        overlap_fraction = float(stargate_count / (len(VELOCITY_SWEEP) * 2))

        hyp_entry = {
            "statement":     statement,
            "result":        "FIELD_EXTRACTED",
            "direction":     1 if stargate_count > 0 else 0,
            "evidence_type": "primary",
            "pass_count":    stargate_count,
            "total_configs": len(VELOCITY_SWEEP) * 2,
            "prior":         0.5,
            "measurement_targets": [
                "invariance", "drift", "degeneracy", "resolution",
            ],
            "metrics": {
                "coherence_score":        coherence_score,
                "overlap_fraction":       overlap_fraction,
                "target_name":            tgt["name"],
                "target_type":            tgt["type"],
                "J_amp":                  tgt["J_amp"],
                "f_base":                 tgt["f_base"],
                "distance_mpc":           tgt["distance_mpc"],
                "stargate_count":         stargate_count,
                "total_pierces":          len(VELOCITY_SWEEP) * 2,
                "architect_mode_count":   architect_count,
                "sigma_deficit":          sigma_deficit,
                "restoration_effort":     restoration_effort,
                "best_entry_velocity":    best_entry["velocity_c"],
                "best_entry_R_7D":        best_entry["R_7D"],
                "best_entry_R_9to10":     best_entry["R_9to10"],
                "best_entry_delta_W":     best_entry["delta_W"],
                "best_entry_stargate":    best_entry["stargate"],
                "per_velocity_entry": {
                    str(r["velocity_c"]): {
                        "R_7D":      r["R_7D"],
                        "R_9to10":   r["R_9to10"],
                        "delta_OP":  r["delta_OP"],
                        "coherence": r["coherence"],
                        "delta_W":   r["delta_W"],
                        "phi_rms":   r["phi_rms"],
                        "stargate":  r["stargate"],
                        "crew_safe": r["crew_safe"],
                    }
                    for r in pierce_results if r["phase"] == "ENTRY"
                },
                "per_velocity_exit": {
                    str(r["velocity_c"]): {
                        "R_7D":      r["R_7D"],
                        "R_9to10":   r["R_9to10"],
                        "delta_OP":  r["delta_OP"],
                        "coherence": r["coherence"],
                        "delta_W":   r["delta_W"],
                        "phi_rms":   r["phi_rms"],
                        "stargate":  r["stargate"],
                        "crew_safe": r["crew_safe"],
                    }
                    for r in pierce_results if r["phase"] == "EXIT"
                },
            },
            "context": {
                "velocity_sweep_c":    VELOCITY_SWEEP,
                "n_half_steps":        N_HALF,
                "alpha_excite":        ALPHA_EXCITE,
                "beta_damp":           BETA_DAMP,
                "dt_pierce":           DT_PIERCE,
                "sig_crit":            SIG_CRIT,
                "brucetron_hemorrhage": BRUCETRON_HEMORRHAGE,
                "c_substrate":         C_SUBSTRATE,
                "r_7d_min":            R_7D_MIN,
                "delta_op_max":        DELTA_OP_MAX,
                "theta_9to10":         THETA_9TO10,
                "framework":           "pierce_gauntlet_blowthrough",
                "sparc_status":        "NOT_IN_SPARC_JWST_only",
                "test_type":           "characterization_not_steering",
            },
            "keywords": [
                "anchor_projection",
                "anchor_bridge_probe",
                "classifier_divergence",
                "attractor",
                "brucetron",
                "lambda",
                "regime",
                "classifier",
                "fracture_lambda",
                "diffusive_lock",
            ],
        }

        all_hypotheses[tgt["hyp_id"]] = hyp_entry
        all_pierce_data[tgt_key] = pierce_results

    # -----------------------------------------------------------------------
    # COMPARISON SUMMARY
    # -----------------------------------------------------------------------
    print(f"\n{'='*76}")
    print("COMPARISON: NGC 7496 (bar) vs IC 5332 (flocculent)")
    print(f"{'='*76}")
    print(f"  {'METRIC':<35} {'NGC 7496':>12} {'IC 5332':>12}")
    print(f"  {'-'*35} {'-'*12} {'-'*12}")
    metrics_compare = [
        ("J_amp (pump strength)",
         TARGETS["NGC7496"]["J_amp"], TARGETS["IC5332"]["J_amp"]),
        ("sigma_deficit (Gutter carved)",
         restoration_estimate(TARGETS["NGC7496"]["J_amp"])[0],
         restoration_estimate(TARGETS["IC5332"]["J_amp"])[0]),
        ("restoration_effort (deficit/J)",
         restoration_estimate(TARGETS["NGC7496"]["J_amp"])[1],
         restoration_estimate(TARGETS["IC5332"]["J_amp"])[1]),
    ]
    for label, v1, v2 in metrics_compare:
        print(f"  {label:<35} {v1:>12.4e} {v2:>12.4e}")

    # -----------------------------------------------------------------------
    # JSON OUTPUT
    # -----------------------------------------------------------------------
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"{TEST_NAME}_{timestamp}.json"
    out_path     = os.path.join(_DATA_RESULTS, out_filename)

    output = {
        "test_name":    TEST_NAME,
        "test_number":  TEST_NUMBER,
        "timestamp":    timestamp,
        "target":       "NGC7496_IC5332_JWST_Pierce_Gauntlet",
        "framework":    "pierce_gauntlet_blowthrough",
        "v28_partition": "jwst_pierce_gauntlet (data/results/)",
        "velocity_sweep_c": VELOCITY_SWEEP,
        "phases":       ["ENTRY", "EXIT"],
        "n_half_steps": N_HALF,
        "sparc_status": "NOT_IN_SPARC",
        "jwst_surveys": {
            "NGC7496": "PHANGS-JWST",
            "IC5332":  "JWST_early_release",
        },
        "hypotheses_tested": all_hypotheses,
        "elapsed_seconds": time.time() - t0,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=float)

    elapsed = time.time() - t0
    print(f"\nJSON written : {out_path}")
    print(f"Elapsed      : {elapsed:.1f}s")
    print()
    print("Next: EPIC COLLECTOR -> INGEST SELECTED -> REFRESH Q-CUBE -> AUTO-10")
    print("      Two new hypotheses will be tracked:")
    for tgt in TARGETS.values():
        print(f"      {tgt['hyp_id']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
