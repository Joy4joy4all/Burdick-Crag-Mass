# -*- coding: utf-8 -*-
"""
BCM v25 TEST 1 — GUARDIAN FIELD EMISSION
=========================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

TARGET ANOMALY (Tab 9, 11D CUBE STACK):
  Cube 6 (Guardians) shows 68 UNKNOWN projections across the
  244-test corpus because v17-v19 test JSONs do not emit the
  crew-safety fields Cube 6 needs to classify. The cube cannot
  report RESOLVED or ANOMALY for these configs — only UNKNOWN.

  Additionally, 13 Cube 6 GREEN/RED mismatches exist where
  test_zone was tagged GREEN but formula_zone computed RED
  based on brucetron_rms exceeding BRUCETRON_HEMORRHAGE.

HYPOTHESIS SERVED:
  H2 (HUMAN) — does the 3D passenger survive?
  H4 (CREW SURVIVAL) — end-to-end mission integration.

WHAT THIS TEST DOES:
  Runs the v19 combined_drain_chi physics pattern (binary pump,
  lambda sweep, 2000-step drain windows) with NO NEW PHYSICS.
  Same constants (LAMBDA=0.1, GRID=256, LAYERS=8). Same solver.
  Same binary system (HR 1099).

  The ONLY change: emit the fields Cube 6 needs as time-series:
    - guardian_strength(step) — twin guardian hold integrity
    - f2_heartbeat_stability(step) — f/2 frequency lock
    - phi_integrity(step) — 1 - phi_rms/PHI_SAFETY
    - chi_buffer_depth(step) — headroom against overflow
    - brucetron_rms_series(step) — sustained vs spike detection
    - test_zone (self-classified GREEN/YELLOW/RED)
    - formula_zone (computed from constants)
    - sustained_violation (bool — was bruce > HEMORRHAGE for
      > 10% of measurement window?)

EXPECTED OUTCOME:
  JSON emits per-lambda config with the fields Cube 6 needs.
  When ingested via EPIC Collector, Tab 9 Cube 6 should shift
  from UNKNOWN to either RESOLVED or ANOMALY for each config.

  Also answers: when test_zone=GREEN, is sustained brucetron
  actually below hemorrhage? If yes, zone tagging is defensible.
  If no, prior tests were optimistic.

DOES NOT:
  - Change any frozen constant
  - Introduce new physics
  - Test a new system (HR 1099 per v19 baseline)
  - Resolve Cube 5 sigma_crit (separate test)

Output JSON → data/results/BCM_v25_guardian_field_emission_YYYYMMDD_HHMMSS.json
"""

import numpy as np
import os
import sys
import json
import time
import argparse

# Bootstrap path chain (v24 pattern)
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.solver_select import SubstrateSolver

# ============================================================================
# FROZEN CONSTANTS (v15-v25 — NONE CHANGED)
# ============================================================================
LAMBDA_BASE = 0.1          # default decay rate
GRID_PROD   = 256
GRID_QUICK  = 128
LAYERS      = 8
SETTLE      = 18000
MEASURE     = 6000

# Crew-safety thresholds (v17-v25, frozen)
BRUCETRON_HEMORRHAGE = 0.0045   # v17 hemorrhage threshold
PHI_SAFETY           = 0.10     # v17 phase safety ceiling
CHI_C                = 0.002582 # v17 chi critical
GUARDIAN_MIN         = 0.85     # v20 hold minimum
GUARDIAN_FLOOR       = 0.68     # v20 absolute floor
CHI_DECAY            = 0.997    # v19 chi decay rate
OM_SYNC_FREQ         = 0.010    # v22 1D sync reference (f/2 reference)

# Lambda sweep (v19 navigational_drain_chi pattern)
LAMBDA_SWEEP = [0.02, 0.04, 0.06, 0.08]

# Drain pair configs (A:B sigma_crit ratios per v19)
DRAIN_PAIRS = [
    ("A: Baseline",     {"j_mult_a": 1.0, "j_mult_b": 1.0}),
    ("B: A-heavy",      {"j_mult_a": 1.3, "j_mult_b": 0.7}),
    ("C: B-heavy",      {"j_mult_a": 0.7, "j_mult_b": 1.3}),
    ("D: Symmetric hot", {"j_mult_a": 1.2, "j_mult_b": 1.2}),
]

# HR 1099 binary baseline per v19
HR_1099 = {
    "name": "HR 1099",
    "m1": 1.0, "m2": 1.3, "sep": 1.0, "activity": 15.0,
}


# ============================================================================
# HYPOTHESES DECLARED BY THIS TEST (per BCM_TEST_TEMPLATE_CONTRACT.py)
# ============================================================================
#
# Each hypothesis is what this test asks the data. The cube reads
# HYPOTHESES, evaluates each against observed values, and routes the
# result through the Bayesian hypothesis engine.
#
# These three hypotheses derive from what Cube 4/6 already flagged in
# prior runs of this test:
#   - bruce stayed well below hemorrhage threshold every config
#   - guardian stayed above 0.998 every config
#   - phi_integrity sat in the 0.25-0.28 band across every lambda
#
# So this retrofit asks: "does that pattern hold again, and does the
# cube agree with the test's self-classification?"

HYPOTHESES = {
    "BRUCETRON_SUBCRITICAL": {
        "statement":      "brucetron stays below hemorrhage across lambda sweep",
        "keywords":       ["brucetron", "hemorrhage", "crew_safety"],
        "cube_target":    6,
        "metric":         "brucetron_rms",
        "pass_condition": f"brucetron_rms < {BRUCETRON_HEMORRHAGE}",
        "bucket":         "ANOMALY",
        "context_vary":   ["lambda", "drain_pair"],
        "context_hold":   ["grid", "system", "settle", "measure"],
        "prior":          0.50,
        "evidence_type":  "explicit_validate",
    },
    "GUARDIAN_HOLD_INTEGRITY": {
        "statement":      "guardian_strength remains >= GUARDIAN_MIN across sweep",
        "keywords":       ["guardian", "crew_safety"],
        "cube_target":    6,
        "metric":         "guardian_strength",
        "pass_condition": f"guardian_strength >= {GUARDIAN_MIN}",
        "bucket":         "POSSIBLE_INVARIANT",
        "context_vary":   ["lambda", "drain_pair"],
        "context_hold":   ["grid", "system", "settle", "measure"],
        "prior":          0.50,
        "evidence_type":  "explicit_validate",
    },
    "PHI_INTEGRITY_PERSISTENT_BAND": {
        "statement":      "phi_integrity holds 0.20-0.35 band across all configs",
        "keywords":       ["phi", "phi_integrity", "invariance"],
        "cube_target":    4,
        "metric":         "phi_integrity",
        "pass_condition": "0.20 <= phi_integrity <= 0.35",
        "bucket":         "POSSIBLE_INVARIANT",
        "context_vary":   ["lambda", "drain_pair"],
        "context_hold":   ["grid", "system", "settle", "measure"],
        "prior":          0.50,
        "evidence_type":  "explicit_validate",
    },
}


def evaluate_hypothesis(hyp_key, observed_values):
    """
    Evaluate one hypothesis against the list of observed metric values
    from each config. Returns dict with:
      observed_values, pass_count, fail_count, total_configs,
      result (PASS/FAIL/PARTIAL), direction (+1/-1/0), confidence
    """
    hyp = HYPOTHESES[hyp_key]
    metric = hyp["metric"]
    condition = hyp["pass_condition"]
    total = len(observed_values)
    if total == 0:
        return {"observed_values": [], "pass_count": 0, "fail_count": 0,
                "total_configs": 0, "result": "INDETERMINATE",
                "direction": 0, "confidence": "LOW"}

    # Evaluate each config against the pass_condition string.
    # Build a minimal, safe evaluator — only allow numeric comparisons.
    pass_count = 0
    fail_count = 0
    for v in observed_values:
        # Substitute metric name with value, then eval with restricted globals
        try:
            expr = condition.replace(metric, str(float(v)))
            ok = bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            ok = False
        if ok:
            pass_count += 1
        else:
            fail_count += 1

    if pass_count == total:
        result = "PASS"
        direction = +1
    elif fail_count == total:
        result = "FAIL"
        direction = -1
    else:
        result = "PARTIAL"
        direction = 0

    if total >= 8:
        confidence = "HIGH"
    elif total >= 4:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "observed_values": [float(v) for v in observed_values],
        "pass_count":      pass_count,
        "fail_count":      fail_count,
        "total_configs":   total,
        "result":          result,
        "direction":       direction,
        "confidence":      confidence,
    }


# ============================================================================
# GUARDIAN FIELD EMISSION CALLBACK
# ============================================================================

class GuardianFieldCallback:
    """
    Samples the solver state every callback (every 1000 steps) and
    derives crew-safety fields from raw sigma/rho data.

    All derivations use ONLY v15-v24 established relationships.
    No new physics introduced.

    Per 1000-step sample, records:
      step, sigma_ring_rms, sigma_core_rms, phi_rms_proxy,
      bruce_rms_proxy, chi_value_proxy, guardian_strength_proxy,
      f2_stability_proxy, phi_integrity, chi_buffer_depth,
      sustained_violation flag.
    """
    def __init__(self, ring_mask, core_mask, throat_mask):
        self.ring_mask = ring_mask
        self.core_mask = core_mask
        self.throat_mask = throat_mask

        self.steps = []
        self.sigma_ring_rms = []
        self.sigma_core_rms = []
        self.phi_rms_series = []
        self.bruce_rms_series = []
        self.chi_value_series = []
        self.guardian_strength_series = []
        self.f2_stability_series = []
        self.phi_integrity_series = []
        self.chi_buffer_depth_series = []

        # Temporal tracking for phi_rms proxy (v25 fix):
        # phi is a TEMPORAL phase signature — oscillation over time
        # at a fixed location. Keeps rolling window of recent throat
        # sigma mean values to measure temporal RMS.
        self._throat_mean_history = []
        self._phi_window_size = 5  # 5 samples = ~5000 steps

        # Tracking for sustained_violation flag
        self._violation_steps = 0
        self._total_measurement_steps = 0

    def __call__(self, step, total, rho, sigma):
        # Collapse multi-layer sigma to 2D (mean across layers)
        sigma_2d = np.mean(sigma, axis=0) if sigma.ndim == 3 else sigma

        # --- sigma_ring_rms (boundary layer signal) ---
        sigma_ring = float(np.sqrt(np.mean(sigma_2d[self.ring_mask]**2)))

        # --- sigma_core_rms (interior signal) ---
        sigma_core = float(np.sqrt(np.mean(sigma_2d[self.core_mask]**2)))

        # --- phi_rms_proxy (v25 REBUILD) ---
        # v17/v18: phi is the OBSERVABLE PHASE — a temporal oscillation
        # measured at fixed location over time, not a spatial snapshot.
        # Old proxy used spatial std/mean which saturated at the cap.
        # New proxy: track rolling window of throat mean sigma across
        # recent callbacks. phi_rms = RMS of normalized deltas from
        # the window mean. This measures how much the throat is
        # oscillating in time — which is what v17 observed.
        throat_sigma = sigma_2d[self.throat_mask]
        if len(throat_sigma) > 0:
            throat_mean_now = float(np.mean(throat_sigma))
            self._throat_mean_history.append(throat_mean_now)
            # keep rolling window
            if len(self._throat_mean_history) > self._phi_window_size:
                self._throat_mean_history.pop(0)

            if len(self._throat_mean_history) >= 3:
                hist = np.array(self._throat_mean_history)
                window_mean = float(np.mean(hist))
                if abs(window_mean) > 1e-12:
                    # RMS of normalized deltas (temporal phase RMS)
                    phi_rms = float(np.sqrt(np.mean(
                        ((hist - window_mean) / window_mean) ** 2)))
                else:
                    phi_rms = 0.0
            else:
                phi_rms = 0.0
        else:
            phi_rms = 0.0

        # Honest cap at PHI_SAFETY × 2 (so we can still see breach)
        phi_rms = min(phi_rms, PHI_SAFETY * 2.0)

        # --- bruce_rms_proxy ---
        # v17: brucetron is high-freq residue measured as RMS of local
        # sigma fluctuation. Proxy: stddev of sigma in throat region,
        # scaled to ingested-test observed range (~0.005-0.015).
        if len(throat_sigma) > 0:
            bruce_raw = float(np.std(throat_sigma))
            # Scale to observed bruce range in v19 tests
            # (v19 JSONs report bruce 0.005-0.015 for this physics)
            bruce_rms = bruce_raw / (abs(throat_sigma.mean()) * 1e3 + 1e-9)
            bruce_rms = min(max(bruce_rms, 0.0), 0.025)
        else:
            bruce_rms = 0.0

        # --- chi_value_proxy ---
        # v17/v19: chi is 4D headspace spill. Proxy: magnitude of
        # sigma gradient at throat, normalized.
        dy, dx = np.gradient(sigma_2d)
        grad_mag = np.sqrt(dx**2 + dy**2)
        if np.any(self.throat_mask):
            chi_value = float(np.mean(grad_mag[self.throat_mask]))
            chi_value = min(chi_value / 100.0, 1.0)  # scale to v19 chi range
        else:
            chi_value = 0.0

        # --- guardian_strength_proxy ---
        # v20 Twin Guardians hold f/2 heartbeat at L1. Strength
        # derived from: how stable is the ring structure against the
        # core? If ring/core ratio oscillates, guardians weaken.
        # Proxy: 1.0 - (|ring/core anomaly| normalized)
        if sigma_core > 0 and len(self.steps) >= 3:
            current_ratio = sigma_ring / sigma_core
            recent_ratios = [self.sigma_ring_rms[-i] / self.sigma_core_rms[-i]
                             for i in range(1, min(4, len(self.sigma_ring_rms)+1))
                             if self.sigma_core_rms[-i] > 0]
            if recent_ratios:
                ratio_std = float(np.std(recent_ratios))
                guardian_strength = max(0.0, 1.0 - ratio_std * 5.0)
            else:
                guardian_strength = 1.0
        else:
            guardian_strength = 1.0
        guardian_strength = min(guardian_strength, 1.0)

        # --- f2_stability_proxy ---
        # v22 Om_sync freq reference = 0.010. f/2 heartbeat stability
        # measured as consistency of sigma_ring RMS across last ~3
        # samples (low std = high stability).
        if len(self.sigma_ring_rms) >= 3:
            recent = self.sigma_ring_rms[-3:]
            mean_recent = np.mean(recent) + 1e-9
            f2_stability = max(0.0, 1.0 - float(np.std(recent) / mean_recent))
        else:
            f2_stability = 1.0
        f2_stability = min(f2_stability, 1.0)

        # --- phi_integrity ---
        phi_integrity = max(0.0, 1.0 - phi_rms / PHI_SAFETY)

        # --- chi_buffer_depth ---
        # Headroom against overflow. v17: chi_c is the threshold.
        # Buffer depth = (chi_c - chi) / chi_c when chi < chi_c,
        # otherwise negative (overflow).
        chi_buffer_depth = (CHI_C - chi_value) / CHI_C if CHI_C > 0 else 0.0

        # --- sustained violation tracking ---
        if step >= SETTLE:  # only count during measurement window
            self._total_measurement_steps += 1
            if bruce_rms > BRUCETRON_HEMORRHAGE:
                self._violation_steps += 1

        # Append
        self.steps.append(int(step))
        self.sigma_ring_rms.append(sigma_ring)
        self.sigma_core_rms.append(sigma_core)
        self.phi_rms_series.append(float(phi_rms))
        self.bruce_rms_series.append(float(bruce_rms))
        self.chi_value_series.append(float(chi_value))
        self.guardian_strength_series.append(float(guardian_strength))
        self.f2_stability_series.append(float(f2_stability))
        self.phi_integrity_series.append(float(phi_integrity))
        self.chi_buffer_depth_series.append(float(chi_buffer_depth))

    def sustained_violation(self):
        """True if bruce > HEMORRHAGE for > 10% of measurement window."""
        if self._total_measurement_steps == 0:
            return False
        return (self._violation_steps / self._total_measurement_steps) > 0.10

    def violation_fraction(self):
        """Fraction of measurement window where bruce > HEMORRHAGE."""
        if self._total_measurement_steps == 0:
            return 0.0
        return self._violation_steps / self._total_measurement_steps


# ============================================================================
# SOURCE FIELD CONSTRUCTION (v19 PATTERN)
# ============================================================================

def build_binary_J(grid, system, j_mult_a=1.0, j_mult_b=1.0):
    """HR 1099 binary source with pump ratio adjustment (v19 pattern)."""
    x = np.linspace(-5, 5, grid)
    y = np.linspace(-5, 5, grid)
    X, Y = np.meshgrid(x, y)

    sep = system['sep']
    r1 = np.sqrt((X + sep/2)**2 + Y**2)
    r2 = np.sqrt((X - sep/2)**2 + Y**2)
    J_base = (j_mult_a * system['m1'] / (r1 + 0.2)) + \
             (j_mult_b * system['m2'] / (r2 + 0.2))

    throat = np.exp(-(X**2 + Y**2) / 1.0)
    grind = np.random.normal(0, 1.2, (grid, grid)) * system['activity']
    J_net = J_base + grind * 0.05 * throat

    R = np.sqrt(X**2 + Y**2)
    return J_net, R


# ============================================================================
# ZONE CLASSIFICATION
# ============================================================================

def classify_test_zone(lam):
    """
    Self-classification based on lambda band (v19 convention).
    This is what prior v19 tests tagged themselves as.
    """
    if lam < 0.03:
        return "GREEN"       # corridor
    elif lam < 0.06:
        return "YELLOW"      # marginal
    else:
        return "RED"         # resonant / dense


def classify_formula_zone(bruce_mean, phi_integrity_mean,
                          guardian_mean, sustained_violation):
    """
    Formula-based classification using frozen constants.
    This is what Cube 6 computes from the emitted fields.
    """
    if sustained_violation:
        return "RED"
    if bruce_mean > BRUCETRON_HEMORRHAGE:
        return "RED"
    if guardian_mean < GUARDIAN_FLOOR:
        return "RED"
    if phi_integrity_mean < 0.5:
        return "YELLOW"
    if guardian_mean < GUARDIAN_MIN:
        return "YELLOW"
    return "GREEN"


# ============================================================================
# CONFIG RUNNER
# ============================================================================

def run_config(system, grid, lam, drain_label, j_mult_a, j_mult_b,
               verbose=True):
    """Run one (lambda, drain_pair) config with field emission."""
    if verbose:
        print(f"    λ={lam:.2f}  {drain_label}  "
              f"(A×{j_mult_a:.1f}, B×{j_mult_b:.1f})")

    # Reproducible grind per config
    np.random.seed(42 + int(lam * 100))

    # Build source
    J_net, R = build_binary_J(grid, system,
                              j_mult_a=j_mult_a, j_mult_b=j_mult_b)

    r_max = np.max(R)
    ring_mask = (R > 0.75 * r_max) & (R < 0.85 * r_max)
    core_mask = R < 0.33 * r_max
    throat_mask = R < 0.50 * r_max  # wider throat region for crew metrics

    # Emission callback
    cb = GuardianFieldCallback(ring_mask, core_mask, throat_mask)

    # Run solver with current lambda
    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=lam,
                             settle=SETTLE, measure=MEASURE)
    t0 = time.time()
    res = solver.run(J_net, verbose=False, callback=cb)
    elapsed = time.time() - t0

    # Measurement window (post-settle samples only for classification)
    measurement_indices = [i for i, s in enumerate(cb.steps)
                           if s >= SETTLE]
    if not measurement_indices:
        # Fallback — use all samples
        measurement_indices = list(range(len(cb.steps)))

    def _window_mean(series):
        vals = [series[i] for i in measurement_indices]
        return float(np.mean(vals)) if vals else 0.0

    bruce_mean = _window_mean(cb.bruce_rms_series)
    bruce_peak = float(np.max([cb.bruce_rms_series[i]
                               for i in measurement_indices])) \
                 if measurement_indices else 0.0
    phi_integrity_mean = _window_mean(cb.phi_integrity_series)
    guardian_mean = _window_mean(cb.guardian_strength_series)
    f2_stab_mean = _window_mean(cb.f2_stability_series)
    chi_buffer_mean = _window_mean(cb.chi_buffer_depth_series)
    chi_value_mean = _window_mean(cb.chi_value_series)

    sustained = cb.sustained_violation()
    viol_frac = cb.violation_fraction()

    test_zone = classify_test_zone(lam)
    formula_zone = classify_formula_zone(bruce_mean, phi_integrity_mean,
                                         guardian_mean, sustained)

    zones_match = (test_zone == formula_zone)

    if verbose:
        match_tag = "✓" if zones_match else "✗"
        print(f"      bruce_mean={bruce_mean:.6f}  peak={bruce_peak:.6f}  "
              f"viol_frac={viol_frac:.2f}")
        print(f"      guardian={guardian_mean:.3f}  "
              f"phi_int={phi_integrity_mean:.3f}  "
              f"f2_stab={f2_stab_mean:.3f}")
        print(f"      test_zone={test_zone}  formula_zone={formula_zone}  "
              f"{match_tag}  (elapsed {elapsed:.1f}s)")

    # Sampled profile (20 points for JSON compactness)
    n = len(cb.steps)
    step_size = max(1, n // 20)
    profile = []
    for i in range(0, n, step_size):
        profile.append({
            "step": cb.steps[i],
            "sigma_ring_rms": cb.sigma_ring_rms[i],
            "bruce_rms": cb.bruce_rms_series[i],
            "phi_rms": cb.phi_rms_series[i],
            "chi_value": cb.chi_value_series[i],
            "guardian_strength": cb.guardian_strength_series[i],
            "f2_stability": cb.f2_stability_series[i],
            "phi_integrity": cb.phi_integrity_series[i],
            "chi_buffer_depth": cb.chi_buffer_depth_series[i],
        })

    return {
        "config_name": f"{drain_label} :: lambda={lam:.2f}",
        "lambda_val": float(lam),
        "drain_label": drain_label,
        "j_mult_a": float(j_mult_a),
        "j_mult_b": float(j_mult_b),
        "grid": grid,
        "elapsed": float(elapsed),
        # --- measurement window means (what Cube 6 reads) ---
        "brucetron_rms": bruce_mean,
        "brucetron_rms_peak": bruce_peak,
        "phi_rms": float(np.mean([cb.phi_rms_series[i]
                                   for i in measurement_indices])) \
                   if measurement_indices else 0.0,
        "chi_value": chi_value_mean,
        "guardian_strength": guardian_mean,
        "f2_heartbeat_stability": f2_stab_mean,
        "phi_integrity": phi_integrity_mean,
        "chi_buffer_depth": chi_buffer_mean,
        # --- zone classifications ---
        "test_zone": test_zone,
        "formula_zone": formula_zone,
        "zones_match": zones_match,
        # --- violation flags ---
        "sustained_violation": sustained,
        "violation_fraction": float(viol_frac),
        # --- time series (sampled) ---
        "profile": profile,
        # --- threshold references (for downstream ingestion) ---
        "thresholds_used": {
            "BRUCETRON_HEMORRHAGE": BRUCETRON_HEMORRHAGE,
            "PHI_SAFETY": PHI_SAFETY,
            "CHI_C": CHI_C,
            "GUARDIAN_MIN": GUARDIAN_MIN,
            "GUARDIAN_FLOOR": GUARDIAN_FLOOR,
        },
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="BCM v25 Test 1 — Guardian Field Emission")
    parser.add_argument("--quick", action="store_true",
                        help="Use grid=128 instead of grid=256")
    parser.add_argument("--fast", action="store_true",
                        help="Run only 2 lambdas × 2 drain pairs (4 configs) "
                             "for rapid proxy validation")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    # --fast trims the sweep to 4 configs for proxy validation
    if args.fast:
        lambda_sweep = [0.02, 0.06]       # one GREEN, one RED
        drain_pairs  = DRAIN_PAIRS[:2]    # Baseline + A-heavy
    else:
        lambda_sweep = LAMBDA_SWEEP
        drain_pairs  = DRAIN_PAIRS

    print("=" * 60)
    print("  BCM v25 TEST 1 — GUARDIAN FIELD EMISSION")
    print("  Target: Cube 6 UNKNOWN reduction + GREEN/RED reconciliation")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    if args.fast:
        print(f"  MODE: --fast (4 configs for proxy validation)")
    print(f"  Grid: {grid}  |  Layers: {LAYERS}")
    print(f"  Lambda sweep: {lambda_sweep}")
    print(f"  Drain pairs: {len(drain_pairs)}")
    print(f"  Total configs: {len(lambda_sweep) * len(drain_pairs)}")
    print(f"  System: {HR_1099['name']}")
    print(f"  Hemorrhage threshold: bruce > {BRUCETRON_HEMORRHAGE}")
    print(f"  Guardian min: {GUARDIAN_MIN}")
    print("=" * 60)

    all_results = []
    t_total = time.time()

    for lam in lambda_sweep:
        print(f"\n  ── λ = {lam:.2f} ──")
        for drain_label, drain_params in drain_pairs:
            r = run_config(
                HR_1099, grid, lam, drain_label,
                drain_params["j_mult_a"],
                drain_params["j_mult_b"],
            )
            all_results.append(r)

    elapsed_total = time.time() - t_total

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  GUARDIAN FIELD EMISSION SUMMARY")
    print(f"{'=' * 60}")
    match_count = sum(1 for r in all_results if r["zones_match"])
    viol_count = sum(1 for r in all_results if r["sustained_violation"])
    print(f"  Total configs:         {len(all_results)}")
    print(f"  Zones match:           {match_count}/{len(all_results)}")
    print(f"  Sustained violations:  {viol_count}")
    print()
    print(f"  {'Config':<34} {'test':>6} {'form':>6} {'bruce':>8} "
          f"{'guard':>6} {'viol%':>6}")
    print(f"  {'-'*34} {'-'*6} {'-'*6} {'-'*8} {'-'*6} {'-'*6}")
    for r in all_results:
        match_tag = "✓" if r["zones_match"] else "✗"
        print(f"  {r['config_name']:<34} {r['test_zone']:>6} "
              f"{r['formula_zone']:>6} {r['brucetron_rms']:>8.5f} "
              f"{r['guardian_strength']:>6.3f} "
              f"{r['violation_fraction']*100:>5.1f}%  {match_tag}")

    # Key findings
    print(f"\n  KEY FINDINGS:")
    green_but_viol = [r for r in all_results
                      if r["test_zone"] == "GREEN"
                      and r["sustained_violation"]]
    if green_but_viol:
        print(f"  ⚠  {len(green_but_viol)} configs tagged GREEN but had "
              f"sustained bruce > hemorrhage.")
        print(f"     (Prior v19 zone tagging was optimistic for these.)")
    else:
        print(f"  ✓  No GREEN-tagged configs had sustained bruce violations.")
        print(f"     (Prior v19 zone tagging is defensible for this sweep.)")

    # Output
    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(
        results_dir,
        f"BCM_v25_guardian_field_emission_{timestamp}.json")

    # Evaluate each declared hypothesis against collected results
    # (per BCM_TEST_TEMPLATE_CONTRACT.py)
    hypotheses_tested = {}
    for hkey, hdecl in HYPOTHESES.items():
        metric = hdecl["metric"]
        observed = [r.get(metric) for r in all_results
                    if r.get(metric) is not None]
        eval_result = evaluate_hypothesis(hkey, observed)
        hypotheses_tested[hkey] = {**hdecl, **eval_result}
        print(f"  Hypothesis {hkey}: "
              f"{eval_result['result']} "
              f"({eval_result['pass_count']}/"
              f"{eval_result['total_configs']})")

    output = {
        "test": "guardian_field_emission",
        "version": "v25",
        "grid": grid,
        "system": HR_1099["name"],
        # v25 context fields — needed by AnchorState for cube comparisons
        "settle": SETTLE,
        "measure": MEASURE,
        "layers": LAYERS,
        "lambda_sweep": LAMBDA_SWEEP,
        "drain_pairs_tested": [d[0] for d in DRAIN_PAIRS],
        "configs_tested": len(all_results),
        "zones_match_count": match_count,
        "sustained_violation_count": viol_count,
        "timestamp": timestamp,
        "elapsed_total": float(elapsed_total),
        "thresholds_used": {
            "LAMBDA_BASE": LAMBDA_BASE,
            "BRUCETRON_HEMORRHAGE": BRUCETRON_HEMORRHAGE,
            "PHI_SAFETY": PHI_SAFETY,
            "CHI_C": CHI_C,
            "GUARDIAN_MIN": GUARDIAN_MIN,
            "GUARDIAN_FLOOR": GUARDIAN_FLOOR,
            "CHI_DECAY": CHI_DECAY,
            "OM_SYNC_FREQ": OM_SYNC_FREQ,
        },
        # Hypothesis declarations + evaluation results
        # (Read by Tab 9 / hypothesis_engine for Bayesian updating)
        "hypotheses_tested": hypotheses_tested,
        "foreman_note": (
            "Test 1 of v25: guardian field emission retrofit of v19 "
            "combined_drain_chi pattern. Adds crew-safety field time-series "
            "to resolve 68 Cube 6 UNKNOWN projections. No new physics."
        ),
        "results": all_results,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")


if __name__ == "__main__":
    main()
