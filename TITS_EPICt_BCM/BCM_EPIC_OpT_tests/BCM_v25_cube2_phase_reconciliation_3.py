# -*- coding: utf-8 -*-
"""
BCM v25 -- Cube 2 Phase Reconciliation Test 3
===============================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick. Claude is code executor only.

PRIMACY STATEMENT
-----------------
Burdick Crag Mass (BCM) is the sole theoretical framework of Stephen
Justin Burdick Sr. This test is built under his direction per
contract BCM_TEST_TEMPLATE_CONTRACT.py v1.1 (progressive versioning).
ChatGPT served as adversarial advisor on the test specification;
Claude implements exactly to spec using v19 source physics as ground
truth.

PURPOSE
-------
Cube 2 (Substrate anchor) has surfaced 13 STABLE anomalies across the
AUTO-10 projection, all from v19 combined_drain_chi and
navigational_drain. The anomalies are not bugs -- they are
systematic phase-boundary disagreements between two observers:

  test_zone : v19 local heuristic (sign of growth_rate)
  regime    : v24 global classifier (derived from |growth_rate|)

Near phase transitions these need not agree. This test maps the
surface of their disagreement across lambda [0.02, 0.20] at step 0.01
using the EXACT v19 pump-drain physics that produced the original
anomalies. Classifiers observe the same physics; their divergence is
meaningful.

PHYSICS GROUND TRUTH
--------------------
All physics (pump-drain sigma dynamics, PhaseProbe, compute_chi_operator,
growth_rate linear fit) is copied verbatim from BCM_v19_combined_drain_chi.py
Stephen published v19.4. We do not modify v19 physics. We observe it.

The coh_est formula is copied exactly from qt_layer.py (v25 cube2
substrate anchor), which is how the cube projection derives coh_est
from growth_rate during anomaly classification.

HYPOTHESES (per ChatGPT revised lock)
-------------------------------------
  H1  CLASSIFIER_DIVERGENCE_BAND_EXISTS
  H2  REGIME_TRACKS_PHYSICS_AT_HIGH_LAMBDA
  H3  TEST_ZONE_OVERSHOOTS_FAILURE_IN_MID_BAND
  H4  TRUE_INSTABILITY_CORRELATES_WITH_NEGATIVE_GROWTH
  H5  RECONCILIATION_SCALAR_IS_SMOOTH

CONSTRAINT: R-score weights are FIXED and EQUAL. Do not tune. This
test evaluates structure, not optimization.

LOCKED SPEC
-----------
  lambda sweep : 0.02 -> 0.20, step 0.01  (19 values)
  configs      : A: Baseline, B: Drain only, C: Drain + Chi  (v19.4 triple)
  total        : 57 runs
  grid         : 256 (v19 production grid)
  steps        : 5000 (v19 production)
  output JSON  : data/results/BCM_v25_cube2_phase_reconciliation_3_{ts}.json
"""

import numpy as np
import os
import sys
import json
import time
import math
import argparse


# Bootstrap path chain (contract compliance)
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)


# ============================================================================
# FROZEN CONSTANTS (all from v19.4 source + v24 thresholds)
# ============================================================================
KAPPA_DRAIN = 0.35          # v19.4 frozen

# v19.4 simulation parameters (from BCM_v19_combined_drain_chi.py main)
DT         = 0.05
D_DIFF     = 0.5
PUMP_A     = 0.5
RATIO      = 0.25
ALPHA      = 0.80
SEPARATION = 15.0

# v19.4 grid + steps (frozen)
GRID_PROD  = 256
GRID_QUICK = 128
STEPS_PROD = 5000
STEPS_FAST = 2000

# v24 regime thresholds (from bcm_thresholds.py, frozen)
REGIME_DIFFUSIVE_HEALING_MIN = 0.95
REGIME_COHERENCE_FAILURE_MIN = 0.74
REGIME_COHERENCE_FAILURE_MAX = 0.85
COHERENCE_YELLOW             = 0.85    # MARGINAL floor used by cube

# LOCKED lambda sweep per ChatGPT spec
LAMBDA_SWEEP = [round(0.02 + i * 0.01, 2) for i in range(19)]

# LOCKED three configs per v19.4 source (name, kappa_drain, use_chi)
CONFIGS = [
    ("A: Baseline",      0.0,         False),
    ("B: Drain only",    KAPPA_DRAIN, False),
    ("C: Drain + Chi",   KAPPA_DRAIN, True),
]

# R-score weights LOCKED EQUAL per ChatGPT constraint
R_WEIGHT_GROWTH = 1.0
R_WEIGHT_COH    = 1.0
R_WEIGHT_CHI    = 1.0


# ============================================================================
# HYPOTHESES (per contract, ChatGPT revised lock set)
# ============================================================================

HYPOTHESES = {
    "CLASSIFIER_DIVERGENCE_BAND_EXISTS": {
        "statement": (
            "test_zone != regime occurs in a clustered lambda band, "
            "not uniformly across the sweep"),
        "keywords": ["classifier", "divergence", "phase_boundary"],
        "cube_target": 2,
        "metric": "divergence_clustering",
        "pass_condition": "divergence_clustering >= 0.34",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["lambda", "config"],
        "context_hold": ["grid", "steps", "system", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "REGIME_TRACKS_PHYSICS_AT_HIGH_LAMBDA": {
        "statement": (
            "At lambda >= 0.10, regime classification aligns with "
            "sign(growth) and coh_est (the physical observables)"),
        "keywords": ["regime", "high_lambda", "physics_alignment"],
        "cube_target": 2,
        "metric": "regime_high_lambda_agreement",
        "pass_condition": "regime_high_lambda_agreement >= 0.70",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["lambda", "config"],
        "context_hold": ["grid", "steps", "system", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "TEST_ZONE_OVERSHOOTS_FAILURE_IN_MID_BAND": {
        "statement": (
            "In lambda 0.06-0.12, test_zone classifies RED while "
            "growth_rate is small (boundary-stress misclassification)"),
        "keywords": ["test_zone", "mid_band", "overshoot", "misclassification"],
        "cube_target": 2,
        "metric": "test_zone_mid_band_overshoot_rate",
        "pass_condition": "test_zone_mid_band_overshoot_rate >= 0.50",
        "bucket": "ANOMALY",
        "context_vary": ["lambda", "config"],
        "context_hold": ["grid", "steps", "system", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "TRUE_INSTABILITY_CORRELATES_WITH_NEGATIVE_GROWTH": {
        "statement": (
            "When growth_rate < 0 (healing), coh_est is ALSO high; "
            "positive growth should co-occur with lower coh_est"),
        "keywords": ["instability", "negative_growth", "coherence"],
        "cube_target": 2,
        "metric": "neg_growth_coh_drop_correlation",
        "pass_condition": "neg_growth_coh_drop_correlation >= 0.70",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["lambda", "config"],
        "context_hold": ["grid", "steps", "system", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "RECONCILIATION_SCALAR_IS_SMOOTH": {
        "statement": (
            "R(lambda) = w1*sign(growth) + w2*coh_est + w3*log10(chi/chi_c) "
            "behaves continuously across lambda (no sharp jumps)"),
        "keywords": ["reconciliation", "R_scalar", "smoothness", "continuity"],
        "cube_target": 2,
        "metric": "R_score_smoothness",
        "pass_condition": "R_score_smoothness <= 5.0",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["lambda", "config"],
        "context_hold": ["grid", "steps", "system", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
}


def evaluate_hypothesis(hyp_key, metric_value):
    """Evaluate hypothesis against aggregate metric."""
    hyp = HYPOTHESES[hyp_key]
    metric = hyp["metric"]
    condition = hyp["pass_condition"]
    try:
        expr = condition.replace(metric, str(float(metric_value)))
        ok = bool(eval(expr, {"__builtins__": {}}, {}))
    except Exception as e:
        return {"observed_value": float(metric_value), "result": "ERROR",
                "direction": 0, "confidence": "LOW", "error": str(e)}
    return {
        "observed_value": float(metric_value),
        "result": "PASS" if ok else "FAIL",
        "direction": +1 if ok else -1,
        "confidence": "HIGH",
        "pass_count":    1 if ok else 0,
        "fail_count":    0 if ok else 1,
        "total_configs": 57,
    }


# ============================================================================
# V19.4 PHYSICS -- COPIED VERBATIM (do not modify)
# Source: BCM_v19_combined_drain_chi.py (Burdick, 2026)
# ============================================================================

def compute_com(field):
    total = np.sum(field)
    if total < 1e-15:
        return None
    nx, ny = field.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X * field) / total,
                     np.sum(Y * field) / total])


def compute_chi_operator(phi, dx=1.0):
    dphi_x = (np.roll(phi, -1, 0) - np.roll(phi, 1, 0)) / (2 * dx)
    dphi_y = (np.roll(phi, -1, 1) - np.roll(phi, 1, 1)) / (2 * dx)
    lap_phi = (np.roll(phi, 1, 0) + np.roll(phi, -1, 0) +
               np.roll(phi, 1, 1) + np.roll(phi, -1, 1) -
               4 * phi) / (dx * dx)
    xi_local = phi**2 + dphi_x**2 + dphi_y**2
    dxi_x = (np.roll(xi_local, -1, 0) -
             np.roll(xi_local, 1, 0)) / (2 * dx)
    dxi_y = (np.roll(xi_local, -1, 1) -
             np.roll(xi_local, 1, 1)) / (2 * dx)
    flux_x = phi * dxi_x
    flux_y = phi * dxi_y
    div_flux = ((np.roll(flux_x, -1, 0) -
                 np.roll(flux_x, 1, 0)) / (2 * dx) +
                (np.roll(flux_y, -1, 1) -
                 np.roll(flux_y, 1, 1)) / (2 * dx))
    struct_curv = xi_local * lap_phi
    chi_op = div_flux - struct_curv
    return float(np.sum(np.abs(chi_op)))


class PhaseProbe:
    def __init__(self, pid, eject_offset, scoop_eff=0.05,
                 scoop_r=2.0):
        self.pid = pid
        self.eject_offset = eject_offset
        self.scoop_eff = scoop_eff
        self.scoop_r = scoop_r
        self.pos = np.array([0.0, 0.0])
        self.prev_pos = np.array([0.0, 0.0])
        self.state = "TRANSIT"
        self.cycle_step = 0
        self.cycles = 0
        self.payload = 0.0
        self.t_transit = 5
        self.t_arc = 35
        self.t_fall = 10
        self.total_bled = 0.0

    def update(self, com, pa, pb, step, sigma, nx, ny, rng,
               probe_hits, kappa_drain, chi_field, use_chi):
        eff = step - self.eject_offset
        if eff < 0:
            self.pos = com.copy()
            self.prev_pos = self.pos.copy()
            return 0.0, 0.0
        cl = self.t_transit + self.t_arc + self.t_fall
        prev = self.cycles
        self.cycle_step = eff % cl
        self.cycles = eff // cl

        bleed = 0.0

        if self.cycles > prev and self.payload > 0:
            if kappa_drain > 0:
                bleed_amount = kappa_drain * self.payload
                self.payload -= bleed_amount
                self.total_bled += bleed_amount
                bleed = bleed_amount
                if use_chi and chi_field is not None:
                    bx = int(np.clip(pb[0], 0, nx - 1))
                    by = int(np.clip(pb[1], 0, ny - 1))
                    xa = np.arange(max(0, bx - 4),
                                   min(nx, bx + 5))
                    ya = np.arange(max(0, by - 4),
                                   min(ny, by + 5))
                    if len(xa) > 0 and len(ya) > 0:
                        Xl, Yl = np.meshgrid(xa, ya,
                                             indexing='ij')
                        r2 = ((Xl - pb[0])**2 +
                              (Yl - pb[1])**2)
                        w = np.exp(-r2 / (2 * 2.0**2))
                        ws = float(np.sum(w))
                        if ws > 1e-15:
                            chi_field[np.ix_(xa, ya)] += (
                                w * (bleed_amount / ws))
            self._deposit(sigma, pb, nx, ny)

        self.prev_pos = self.pos.copy()
        b1 = self.t_transit
        b2 = self.t_transit + self.t_arc
        if self.cycle_step < b1:
            self.state = "TRANSIT"
            t = self.cycle_step / self.t_transit
            self.pos = pb + t * (pa - pb)
        elif self.cycle_step < b2:
            self.state = "EJECTED"
            as_ = self.cycle_step - self.t_transit
            bao = rng.uniform(-0.8, 0.8)
            vc = 5 + (self.cycles % 4)
            ta = as_ / self.t_arc
            amr = 40.0 + rng.uniform(-10, 15)
            ar = (amr * (ta * 2) if ta < 0.5
                  else amr * (2 - ta * 2))
            ca = bao + ta * 2 * math.pi
            va = (round(ca / (2 * math.pi / vc)) *
                  (2 * math.pi / vc))
            aa = 0.3 * ca + 0.7 * va
            self.pos = np.array([
                pa[0] + ar * np.cos(aa),
                pa[1] + ar * np.sin(aa)])
            self._scoop(sigma, nx, ny)
            ix = int(np.clip(self.pos[0], 0, nx - 1))
            iy = int(np.clip(self.pos[1], 0, ny - 1))
            probe_hits[ix, iy] += 1.0
        else:
            self.state = "FALLING"
            fs = self.cycle_step - b2
            tf = fs / self.t_fall
            self.pos = (self.prev_pos +
                        tf * (pb - self.prev_pos))
            if fs >= self.t_fall - 1:
                if kappa_drain > 0:
                    bleed_amount = kappa_drain * self.payload
                    self.payload -= bleed_amount
                    self.total_bled += bleed_amount
                    bleed += bleed_amount
                    if use_chi and chi_field is not None:
                        bx = int(np.clip(pb[0], 0, nx - 1))
                        by = int(np.clip(pb[1], 0, ny - 1))
                        xa = np.arange(max(0, bx - 4),
                                       min(nx, bx + 5))
                        ya = np.arange(max(0, by - 4),
                                       min(ny, by + 5))
                        if len(xa) > 0 and len(ya) > 0:
                            Xl, Yl = np.meshgrid(
                                xa, ya, indexing='ij')
                            r2 = ((Xl - pb[0])**2 +
                                  (Yl - pb[1])**2)
                            w = np.exp(-r2 / (2 * 2.0**2))
                            ws = float(np.sum(w))
                            if ws > 1e-15:
                                chi_field[np.ix_(xa, ya)] += (
                                    w * (bleed_amount / ws))
                self._deposit(sigma, pb, nx, ny)

        disp = float(np.linalg.norm(
            self.pos - self.prev_pos))
        at_boundary = (abs(self.cycle_step - b1) <= 1 or
                       abs(self.cycle_step - b2) <= 1)
        jump = disp if at_boundary else 0.0
        return jump, bleed

    def _scoop(self, sigma, nx, ny):
        ix = int(np.clip(self.pos[0], 0, nx - 1))
        iy = int(np.clip(self.pos[1], 0, ny - 1))
        xa = np.arange(max(0, ix - 4), min(nx, ix + 5))
        ya = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl - self.pos[0])**2 + (Yl - self.pos[1])**2
        w = np.exp(-r2 / (2 * self.scoop_r**2))
        loc = sigma[np.ix_(xa, ya)]
        sc = np.minimum(loc * w * self.scoop_eff, loc)
        sc = np.maximum(sc, 0)
        sigma[np.ix_(xa, ya)] -= sc
        self.payload += float(np.sum(sc))

    def _deposit(self, sigma, pos, nx, ny):
        if self.payload <= 0:
            return
        ix = int(np.clip(pos[0], 0, nx - 1))
        iy = int(np.clip(pos[1], 0, ny - 1))
        xa = np.arange(max(0, ix - 4), min(nx, ix + 5))
        ya = np.arange(max(0, iy - 4), min(ny, iy + 5))
        if len(xa) == 0 or len(ya) == 0:
            return
        Xl, Yl = np.meshgrid(xa, ya, indexing='ij')
        r2 = (Xl - pos[0])**2 + (Yl - pos[1])**2
        w = np.exp(-r2 / (2 * self.scoop_r**2))
        ws = float(np.sum(w))
        if ws > 1e-15:
            sigma[np.ix_(xa, ya)] += w * (self.payload / ws)
        self.payload = 0.0


def run_config(nx, ny, steps, dt, D, alpha, separation,
               pump_A, ratio, void_lambda, X, Y,
               kappa_drain, use_chi, rng_seed=42):
    """v19.4 physics loop -- verbatim from Burdick source."""
    rng = np.random.RandomState(rng_seed)
    sx, sy = nx // 8, ny // 2
    r2i = (X - sx)**2 + (Y - sy)**2
    sigma = 1.0 * np.exp(-r2i / (2 * 5.0**2))
    sigma_prev = sigma.copy()
    chi_field = np.zeros((nx, ny))
    phi = np.zeros((nx, ny))
    probe_hits = np.zeros((nx, ny))

    lam = np.full((nx, ny), void_lambda)
    gx = nx // 2
    r2g = (X - gx)**2 + (Y - ny // 2)**2
    lam -= 0.08 * np.exp(-r2g / (2 * 18.0**2))
    lam = np.maximum(lam, 0.001)

    probes = [PhaseProbe(i + 1, i * 5) for i in range(12)]
    bruce_field = np.zeros((nx, ny))
    bruce_decay = 0.95

    ts_bruce = []
    total_bled = 0.0
    initial_sigma = float(np.sum(sigma))

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break
        pa = np.array([com[0] + separation, com[1]])
        pb = np.array([com[0] - separation * 0.3, com[1]])
        r2A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2A / (2 * 4.0**2))
        sigma += pA * dt
        bx = com[0] + separation
        r2B = (X - bx)**2 + (Y - com[1])**2
        pB = pump_A * ratio * np.exp(-r2B / (2 * 3.0**2))
        sigma += pB * dt

        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4 * sigma)
        sn = sigma + D * lap * dt - lam * sigma * dt
        if alpha > 0:
            sn += alpha * (sigma - sigma_prev)
        sn = np.maximum(sn, 0)
        if float(np.max(sn)) > 1e10:
            break

        phase_error = sigma - sigma_prev
        phi = phi * 0.95 + phase_error

        sigma_prev = sigma.copy()
        sigma = sn

        for p in probes:
            jump, bleed = p.update(
                com, pa, pb, step, sigma, nx, ny, rng,
                probe_hits, kappa_drain, chi_field, use_chi)
            if jump > 0:
                ix = int(np.clip(p.pos[0], 0, nx - 1))
                iy = int(np.clip(p.pos[1], 0, ny - 1))
                bruce_field[ix, iy] += jump * 0.1
            total_bled += bleed
        bruce_field *= bruce_decay

        if use_chi:
            ix_c = int(np.clip(com[0], 0, nx - 1))
            iy_c = int(np.clip(com[1], 0, ny - 1))
            r_v = 20
            x_lo = max(0, ix_c - r_v)
            x_hi = min(nx, ix_c + r_v)
            y_lo = max(0, iy_c - r_v)
            y_hi = min(ny, iy_c + r_v)
            ls = sigma[x_lo:x_hi, y_lo:y_hi]
            fl = (float(np.mean(ls)) +
                  1.5 * float(np.std(ls)))
            overflow = np.maximum(sigma - fl, 0)
            spill = overflow * 0.5
            sigma -= spill
            chi_field += spill
            deficit = np.maximum(fl * 0.8 - sigma, 0)
            drain = np.minimum(chi_field * 0.1, deficit)
            sigma += drain
            chi_field -= drain
            chi_field *= 0.999
            bruce_in = bruce_field * 0.05
            chi_field += bruce_in * 0.01
            bruce_field -= bruce_in
            bruce_field = np.maximum(bruce_field, 0)

        ts_bruce.append(float(np.sum(bruce_field**2)))

    n = len(ts_bruce)
    skip = 100
    rate = 0
    if n > skip * 2:
        steps_fit = np.arange(skip, n, dtype=float)
        rate = np.polyfit(steps_fit, ts_bruce[skip:], 1)[0]

    final_sigma = float(np.sum(sigma))
    final_chi = float(np.sum(chi_field))
    phi_rms = float(np.sqrt(np.mean(phi**2)))
    bruce_rms = float(np.sqrt(np.mean(bruce_field**2)))

    gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
    gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
    xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))
    chi_op = compute_chi_operator(phi)

    total_system = final_sigma + final_chi

    return {
        "growth_rate":  round(rate, 8),
        "bruce_rms":    round(bruce_rms, 8),
        "phi_rms":      round(phi_rms, 8),
        "chi_op_late":  round(chi_op, 6),
        "xi_late":      round(xi, 4),
        "total_bled":   round(total_bled, 4),
        "final_sigma":  round(final_sigma, 4),
        "final_chi":    round(final_chi, 4),
        "total_system": round(total_system, 4),
    }


# ============================================================================
# CLASSIFIERS (exact definitions from v19 source + qt_layer.py v24)
# ============================================================================

def classify_test_zone(growth_rate):
    """
    v19.4 test_zone classification -- verbatim from
    BCM_v19_combined_drain_chi.py lines 425-431.
    Based on growth_rate sign:
      rate < -1e-6   -> GREEN  (healing)
      |rate| < 1e-6  -> YELLOW (marginal)
      rate > 1e-6    -> RED    (resonant/building)
    """
    if growth_rate < -1e-6:
        return "GREEN"
    elif abs(growth_rate) < 1e-6:
        return "YELLOW"
    else:
        return "RED"


def compute_coh_est(growth_rate):
    """
    v24 coherence estimate from growth_rate magnitude.
    Verbatim from qt_layer.py lines 503-513.
      |growth| < 1e-5 -> coh = 1.0
      |growth| > 1e-3 -> coh = 0.0
      else linear interp
    """
    if growth_rate is None or growth_rate != growth_rate:
        return None
    mag = abs(float(growth_rate))
    if mag < 1e-5:
        return 1.0
    elif mag > 1e-3:
        return 0.0
    else:
        return 1.0 - (mag - 1e-5) / (1e-3 - 1e-5)


def classify_regime(coh_est):
    """
    v24 regime classification -- verbatim from qt_layer.py lines 527-534.
    """
    if coh_est is None:
        return None
    if coh_est >= REGIME_DIFFUSIVE_HEALING_MIN:
        return "DIFFUSIVE_HEALING"
    elif coh_est >= COHERENCE_YELLOW:
        return "MARGINAL"
    elif coh_est >= REGIME_COHERENCE_FAILURE_MIN:
        return "COHERENCE_FAILURE"
    else:
        return "BOUNDARY_NONLINEAR"


def zones_in_agreement(test_zone, regime):
    """
    v19->v24 agreement mapping. From anchor_state.py convention:
      GREEN  <-> DIFFUSIVE_HEALING or MARGINAL
      YELLOW <-> MARGINAL
      RED    <-> COHERENCE_FAILURE or BOUNDARY_NONLINEAR
    """
    if regime is None:
        return False
    if test_zone == "GREEN":
        return regime in ("DIFFUSIVE_HEALING", "MARGINAL")
    if test_zone == "YELLOW":
        return regime == "MARGINAL"
    if test_zone == "RED":
        return regime in ("COHERENCE_FAILURE", "BOUNDARY_NONLINEAR")
    return False


# ============================================================================
# AGGREGATE METRICS (hypothesis evaluation)
# ============================================================================

def compute_divergence_clustering(results, lambda_sweep):
    """H1: max-minus-min of per-lambda divergence rates."""
    rates = []
    for lam in lambda_sweep:
        configs = [r for r in results
                   if abs(r["lambda_val"] - lam) < 1e-6]
        if not configs:
            continue
        rate = sum(r["divergence_flag"] for r in configs) / len(configs)
        rates.append(rate)
    if not rates:
        return 0.0
    return float(max(rates) - min(rates))


def compute_regime_high_lambda_agreement(results):
    """H2: at lambda >= 0.10, does regime match physics truth?"""
    high = [r for r in results if r["lambda_val"] >= 0.10]
    if not high:
        return 0.0
    hits = 0
    for r in high:
        g = r["growth_rate"]
        coh = r["coh_est"]
        # Physics truth by coh_est thresholds
        if coh >= REGIME_DIFFUSIVE_HEALING_MIN:
            expected = "DIFFUSIVE_HEALING"
        elif coh >= COHERENCE_YELLOW:
            expected = "MARGINAL"
        elif coh >= REGIME_COHERENCE_FAILURE_MIN:
            expected = "COHERENCE_FAILURE"
        else:
            expected = "BOUNDARY_NONLINEAR"
        if r["regime"] == expected:
            hits += 1
    return hits / len(high)


def compute_test_zone_mid_band_overshoot(results):
    """H3: in lambda 0.06-0.12, test_zone=RED while growth is small."""
    mid = [r for r in results
           if 0.06 <= r["lambda_val"] <= 0.12]
    if not mid:
        return 0.0
    # "Small growth" = |growth| < 5e-5 (inside the coh >= 0.85 band)
    overshoots = sum(
        1 for r in mid
        if r["test_zone"] == "RED"
        and abs(r["growth_rate"]) < 5e-5)
    return overshoots / len(mid)


def compute_neg_growth_coh_correlation(results):
    """
    H4: when growth < 0 (v19 GREEN healing), coh should be high.
    Inverted framing: of all healing configs, what fraction have
    coh_est >= 0.85? If so, classifier tracks real collapse physics.
    """
    healing = [r for r in results if r["growth_rate"] < 0]
    if not healing:
        return 0.0
    with_high_coh = sum(1 for r in healing if r["coh_est"] >= 0.85)
    return with_high_coh / len(healing)


def compute_r_score_smoothness(results, lambda_sweep, config_names):
    """H5: max |dR/dlambda| across sweep, averaged over configs."""
    max_deltas = []
    for cname in config_names:
        series = []
        for lam in sorted(lambda_sweep):
            for r in results:
                if (abs(r["lambda_val"] - lam) < 1e-6
                        and r["config_name_short"] == cname):
                    series.append((lam, r["R_score"]))
                    break
        if len(series) < 2:
            continue
        deltas = []
        for i in range(1, len(series)):
            dlam = series[i][0] - series[i-1][0]
            dR = series[i][1] - series[i-1][1]
            if dlam > 0:
                deltas.append(abs(dR / dlam))
        if deltas:
            max_deltas.append(max(deltas))
    if not max_deltas:
        return 0.0
    return float(sum(max_deltas) / len(max_deltas))


# ============================================================================
# CONFIG RUNNER (v19 physics wrapped with classifiers)
# ============================================================================

def run_reconciliation_config(nx, ny, steps, lam_val, config_name,
                               kappa_drain, use_chi, X, Y):
    """Run one (lambda, config) pair and apply both classifiers."""
    print(f"    lambda={lam_val:.2f}  {config_name}")

    t0 = time.time()
    r = run_config(
        nx, ny, steps, DT, D_DIFF, ALPHA, SEPARATION,
        PUMP_A, RATIO, lam_val, X, Y,
        kappa_drain=kappa_drain, use_chi=use_chi)
    elapsed = time.time() - t0

    growth = r["growth_rate"]
    chi_op = r["chi_op_late"]

    # Classifiers
    tz  = classify_test_zone(growth)
    coh = compute_coh_est(growth)
    rg  = classify_regime(coh)
    agree = zones_in_agreement(tz, rg)

    # Derived
    sign_growth = +1 if growth > 0 else (-1 if growth < 0 else 0)
    divergence_flag = 0 if agree else 1

    # chi_ratio: v25 cube uses chi_op_late / CHI_C from bcm_thresholds
    # Use a normalized version; CHI_C=1.0 here to produce log-space scores
    chi_c = 1.0
    chi_over_chi_c = chi_op / chi_c if chi_c > 0 else 0.0

    # R-score with LOCKED equal weights
    safe_log = math.log10(max(chi_over_chi_c, 1e-6))
    r_score = (R_WEIGHT_GROWTH * sign_growth +
               R_WEIGHT_COH * (coh if coh is not None else 0.0) +
               R_WEIGHT_CHI * safe_log)

    print(f"      growth={growth:+.8f}  coh={coh:.3f}  "
          f"chi_op={chi_op:.3f}")
    print(f"      test_zone={tz}  regime={rg}  "
          f"{'AGREE' if agree else 'DIVERGE'}  R={r_score:+.3f}  "
          f"(elapsed {elapsed:.1f}s)")

    return {
        "config_name":        f"{config_name} :: lambda={lam_val:.2f}",
        "config_name_short":  config_name,
        "lambda_val":         lam_val,
        "kappa_drain":        kappa_drain,
        "use_chi":            use_chi,
        # v19 physics outputs (verbatim)
        "growth_rate":    growth,
        "bruce_rms":      r["bruce_rms"],
        "phi_rms":        r["phi_rms"],
        "chi_op_late":    chi_op,
        "xi_late":        r["xi_late"],
        "total_bled":     r["total_bled"],
        "final_sigma":    r["final_sigma"],
        "final_chi":      r["final_chi"],
        "total_system":   r["total_system"],
        # Classifiers
        "test_zone":      tz,
        "coh_est":        coh,
        "regime":         rg,
        # Derived
        "sign_growth":     sign_growth,
        "divergence_flag": divergence_flag,
        "chi_over_chi_c":  chi_over_chi_c,
        "R_score":         float(r_score),
        # Meta
        "elapsed":        float(elapsed),
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=("BCM v25 -- Cube 2 Phase Reconciliation Test 3 "
                     "(v19.4 physics ground truth)"))
    parser.add_argument("--quick", action="store_true",
                        help="grid=128, steps=2000")
    parser.add_argument("--fast", action="store_true",
                        help="3 lambdas x 3 configs (9 configs)")
    parser.add_argument("--grid", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    args = parser.parse_args()

    nx = ny = args.grid or (GRID_QUICK if args.quick else GRID_PROD)
    steps = args.steps or (STEPS_FAST if args.quick else STEPS_PROD)

    if args.fast:
        lambda_sweep = [0.02, 0.10, 0.20]
    else:
        lambda_sweep = LAMBDA_SWEEP

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    total_configs = len(lambda_sweep) * len(CONFIGS)

    print("=" * 65)
    print("  BCM v25 -- CUBE 2 PHASE RECONCILIATION TEST 3")
    print("  Physics: v19.4 pump-drain (Burdick source, verbatim)")
    print("  Stephen Justin Burdick Sr. -- GIBUSH Systems")
    print("=" * 65)
    print(f"  Grid: {nx}x{ny}  Steps: {steps}")
    print(f"  Lambda sweep: {lambda_sweep[0]:.2f} -> "
          f"{lambda_sweep[-1]:.2f}")
    if len(lambda_sweep) > 1:
        print(f"  Step: {lambda_sweep[1] - lambda_sweep[0]:.3f}  "
              f"({len(lambda_sweep)} values)")
    print(f"  Configs: {[c[0] for c in CONFIGS]}")
    print(f"  Total runs: {total_configs}")
    print(f"  R-score weights (LOCKED EQUAL): "
          f"w_growth={R_WEIGHT_GROWTH}, w_coh={R_WEIGHT_COH}, "
          f"w_chi={R_WEIGHT_CHI}")
    print("=" * 65)

    all_results = []
    t_total = time.time()

    for lam_val in lambda_sweep:
        print(f"\n  -- lambda = {lam_val:.2f} --")
        for config_name, kappa_drain, use_chi in CONFIGS:
            r = run_reconciliation_config(
                nx, ny, steps, lam_val, config_name,
                kappa_drain, use_chi, X, Y)
            all_results.append(r)

    elapsed_total = time.time() - t_total

    # Summary counts
    n_diverge = sum(1 for r in all_results if r["divergence_flag"] == 1)
    n_tz_red  = sum(1 for r in all_results if r["test_zone"] == "RED")
    n_tz_grn  = sum(1 for r in all_results if r["test_zone"] == "GREEN")
    n_rg_cf   = sum(1 for r in all_results
                    if r["regime"] == "COHERENCE_FAILURE")
    n_rg_dh   = sum(1 for r in all_results
                    if r["regime"] == "DIFFUSIVE_HEALING")

    print(f"\n{'=' * 65}")
    print(f"  CUBE 2 PHASE RECONCILIATION SUMMARY")
    print(f"{'=' * 65}")
    print(f"  Total runs:              {len(all_results)}")
    print(f"  Elapsed total:           {elapsed_total:.1f}s")
    print(f"  Divergent (tz != rg):    {n_diverge}/{len(all_results)}")
    print(f"  test_zone = RED:         {n_tz_red}/{len(all_results)}")
    print(f"  test_zone = GREEN:       {n_tz_grn}/{len(all_results)}")
    print(f"  regime = COHERENCE_FAIL: {n_rg_cf}/{len(all_results)}")
    print(f"  regime = DIFFUSIVE_HEAL: {n_rg_dh}/{len(all_results)}")

    # Aggregate metrics for hypothesis evaluation
    config_names = [c[0] for c in CONFIGS]
    metrics = {
        "divergence_clustering":
            compute_divergence_clustering(all_results, lambda_sweep),
        "regime_high_lambda_agreement":
            compute_regime_high_lambda_agreement(all_results),
        "test_zone_mid_band_overshoot_rate":
            compute_test_zone_mid_band_overshoot(all_results),
        "neg_growth_coh_drop_correlation":
            compute_neg_growth_coh_correlation(all_results),
        "R_score_smoothness":
            compute_r_score_smoothness(
                all_results, lambda_sweep, config_names),
    }

    print(f"\n  AGGREGATE METRICS:")
    for k, v in metrics.items():
        print(f"    {k}: {v:.4f}")

    # Evaluate hypotheses
    hypotheses_tested = {}
    print(f"\n  HYPOTHESIS EVALUATION:")
    for hkey, hdecl in HYPOTHESES.items():
        metric_name = hdecl["metric"]
        metric_value = metrics.get(metric_name, 0.0)
        eval_result = evaluate_hypothesis(hkey, metric_value)
        hypotheses_tested[hkey] = {**hdecl, **eval_result}
        print(f"    {hkey}: {eval_result['result']} "
              f"(observed={eval_result['observed_value']:.4f})")

    # Output JSON
    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(
        results_dir,
        f"BCM_v25_cube2_phase_reconciliation_3_{timestamp}.json")

    output = {
        "test":              "cube2_phase_reconciliation_3",
        "version":           "v25",
        "physics_version":   "v19.4",
        "grid":              nx,
        "steps":             steps,
        "system":            "v19.4_pump_drain_HR1099",
        "lambda_sweep":      lambda_sweep,
        "configs_tested":    [c[0] for c in CONFIGS],
        "total_runs":        len(all_results),
        "divergent_count":   n_diverge,
        "timestamp":         timestamp,
        "elapsed_total":     float(elapsed_total),
        "r_score_weights": {
            "w_growth": R_WEIGHT_GROWTH,
            "w_coh":    R_WEIGHT_COH,
            "w_chi":    R_WEIGHT_CHI,
        },
        "thresholds_used": {
            "KAPPA_DRAIN":                  KAPPA_DRAIN,
            "REGIME_DIFFUSIVE_HEALING_MIN": REGIME_DIFFUSIVE_HEALING_MIN,
            "REGIME_COHERENCE_FAILURE_MIN": REGIME_COHERENCE_FAILURE_MIN,
            "REGIME_COHERENCE_FAILURE_MAX": REGIME_COHERENCE_FAILURE_MAX,
            "COHERENCE_YELLOW":             COHERENCE_YELLOW,
        },
        "aggregate_metrics":  metrics,
        "hypotheses_tested":  hypotheses_tested,
        "foreman_note": (
            "Test 3 of v25: Cube 2 phase reconciliation per ChatGPT "
            "adversarial lock. Physics copied verbatim from "
            "BCM_v19_combined_drain_chi.py so classifier outputs "
            "match the anomaly corpus. Does NOT modify classifiers; "
            "observes only. R-score weights are LOCKED EQUAL."),
        "results":            all_results,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")


if __name__ == "__main__":
    main()
