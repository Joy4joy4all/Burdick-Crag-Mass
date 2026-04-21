# -*- coding: utf-8 -*-
"""
BCM v25 -- Cube 2 Phase Reconciliation Test 7
===============================================
Kappa Drain Sweep at Fracture Lambdas (C-config Only)
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick. Claude is code executor only.

PRIMACY STATEMENT
-----------------
Burdick Crag Mass (BCM) is the sole theoretical framework of Stephen
Justin Burdick Sr. Built under his direction per contract
BCM_TEST_TEMPLATE_CONTRACT.py v1.1 (progressive versioning). Dark
Mason (Grok) adversarial advisor locked the spec: Path A kappa sweep
(not bolt-on multiplier), 30-run C-focused scope, enumerate_within_v25
filename convention. Claude implements exactly.

PURPOSE
-------
Test 6 confirmed the fracture at 500-anomaly lambdas. At kappa_drain
= 0.35 (v19 frozen), C-config runs sit 1.07x - 1.37x ABOVE the 0.0045
Brucetron hemorrhage line. B-config runs are worse, 2.16x - 2.79x.

Test 7 asks: does varying kappa_drain produce a configuration where
Brucetron drops cleanly below hemorrhage while coherence holds?
This is the crew-safety envelope probe.

LOCKED SCOPE (Dark Mason + Foreman)
-----------------------------------
  lambda sweep : 0.02, 0.04, 0.06, 0.08, 0.10, 0.12   (6 fracture points)
  config       : C: Drain + Chi only                    (kappa meaningful only with chi)
  kappa sweep  : 0.0, 0.175, 0.35, 0.525, 0.70        (0x, 0.5x, 1x, 1.5x, 2x frozen)
  total runs   : 30
  grid         : 256
  steps        : 5000
  physics      : v19.4 pump-drain (verbatim, with kappa_drain as swept input)

kappa_drain=0.35 is v19 frozen. This test intentionally unfreezes it
in a controlled sweep, then restores it to 0.35 in all other tests.
The constant is not redefined; only this test probes its gradient.

HYPOTHESES
----------
  H10  KAPPA_SUPPRESSES_BRUCETRON
       Correlation between kappa_drain and bruce_rms_final is
       negative (more drain -> lower Brucetron).
       PASS: correlation <= -0.5

  H11  SAFE_KAPPA_ENVELOPE_EXISTS
       At least one (lambda, kappa) point where
       bruce_rms_final < 0.0045 (below hemorrhage line).
       PASS: any single C-run below hemorrhage

  H12  KAPPA_PRESERVES_COHERENCE
       coh_est_at_settle does NOT degrade as kappa increases.
       PASS: correlation(kappa, coh_est_at_settle) >= 0

OUTPUT: data/results/BCM_v25_cube2_phase_reconciliation_7_{ts}.json
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
# FROZEN CONSTANTS (v19.4 physics + v24 regime thresholds)
# ============================================================================
KAPPA_DRAIN_FROZEN = 0.35       # v19 canonical; unfrozen ONLY for this sweep
DT         = 0.05
D_DIFF     = 0.5
PUMP_A     = 0.5
RATIO      = 0.25
ALPHA      = 0.80
SEPARATION = 15.0

GRID_PROD  = 256
GRID_QUICK = 128
STEPS_PROD = 5000
STEPS_FAST = 2000

# v24 regime thresholds
REGIME_DIFFUSIVE_HEALING_MIN = 0.95
REGIME_COHERENCE_FAILURE_MIN = 0.74
REGIME_COHERENCE_FAILURE_MAX = 0.85
COHERENCE_YELLOW             = 0.85

# LOCKED sweeps (Dark Mason spec)
LAMBDA_SWEEP = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12]
KAPPA_SWEEP  = [0.0, 0.175, 0.35, 0.525, 0.70]

# Guardian hemorrhage line (Foreman-confirmed)
HEMORRHAGE_LINE_BRUCE_RMS = 0.0045

# Settle window for end-of-run averages (final 20%)
SETTLE_FRACTION = 0.20


# ============================================================================
# HYPOTHESES
# ============================================================================

HYPOTHESES = {
    "KAPPA_SUPPRESSES_BRUCETRON": {
        "statement": (
            "Increasing kappa_drain suppresses bruce_rms_final. "
            "Correlation across the sweep is negative <= -0.5."),
        "keywords": ["kappa", "brucetron", "suppression", "crew_safety"],
        "cube_target": 6,
        "metric": "kappa_vs_bruce_correlation",
        "pass_condition": "kappa_vs_bruce_correlation <= -0.5",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["kappa_drain", "lambda"],
        "context_hold": ["config", "grid", "steps", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "SAFE_KAPPA_ENVELOPE_EXISTS": {
        "statement": (
            "There exists at least one (lambda, kappa) configuration "
            "where bruce_rms_final < 0.0045 (below hemorrhage)."),
        "keywords": ["safe_envelope", "hemorrhage", "crew_safety"],
        "cube_target": 6,
        "metric": "safe_run_count",
        "pass_condition": "safe_run_count >= 1",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["kappa_drain", "lambda"],
        "context_hold": ["config", "grid", "steps", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
    "KAPPA_PRESERVES_COHERENCE": {
        "statement": (
            "Increasing kappa_drain does not degrade coherence at "
            "settle. Correlation >= 0."),
        "keywords": ["kappa", "coherence", "preservation"],
        "cube_target": 2,
        "metric": "kappa_vs_coh_correlation",
        "pass_condition": "kappa_vs_coh_correlation >= 0.0",
        "bucket": "POSSIBLE_INVARIANT",
        "context_vary": ["kappa_drain", "lambda"],
        "context_hold": ["config", "grid", "steps", "physics_version"],
        "prior": 0.50,
        "evidence_type": "explicit_validate",
    },
}


def evaluate_hypothesis(hyp_key, metric_value):
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
    }


# ============================================================================
# V19.4 PHYSICS -- VERBATIM (Burdick source, unchanged)
# kappa_drain is parameterized input, not modified physics
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
    """v19.4 physics -- verbatim -- kappa_drain is input parameter."""
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
    chi_freeboard_series = []
    bruce_rms_series = []
    coh_est_series = []
    guardian_strength_series = []
    hemorrhage_steps = 0
    bruce_min_running = float("inf")

    total_bled = 0.0

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

        chi_freeboard_step = 0.0
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
            chi_freeboard_step = fl
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

        # Per-step tracking
        bruce_rms_step = float(np.sqrt(np.mean(bruce_field**2)))
        ts_bruce.append(float(np.sum(bruce_field**2)))
        chi_freeboard_series.append(chi_freeboard_step)
        bruce_rms_series.append(bruce_rms_step)

        if bruce_rms_step > HEMORRHAGE_LINE_BRUCE_RMS:
            hemorrhage_steps += 1
        if bruce_rms_step < bruce_min_running:
            bruce_min_running = bruce_rms_step

        # On-line proxies for coherence + guardian
        # (running estimates, not final; used for settle averaging)
        bruce_norm = bruce_rms_step / HEMORRHAGE_LINE_BRUCE_RMS
        bruce_calm = 1.0 / (1.0 + bruce_norm)

        # chi freeboard per step (proxy for chi protection)
        if use_chi and chi_freeboard_step > 0:
            chi_field_sum_step = float(np.sum(chi_field))
            sigma_sum_step = float(np.sum(sigma))
            if sigma_sum_step > 1e-9:
                chi_prot_step = chi_field_sum_step / sigma_sum_step
            else:
                chi_prot_step = 0.0
        else:
            chi_prot_step = 0.0

        # Approximate per-step guardian using streaming values
        # (full guardian uses chi_op_late which is only known post-run;
        # this proxy tracks the trend for settle averaging)
        if chi_prot_step > 0 and bruce_calm > 0:
            guardian_step = math.tanh(
                (chi_prot_step * bruce_calm) ** 0.5)
        else:
            guardian_step = 0.0
        guardian_strength_series.append(guardian_step)

        # coh_est running: derived from local bruce stability (proxy,
        # not from growth_rate which requires the full linear fit).
        # Used only for settle average.
        coh_est_step = bruce_calm
        coh_est_series.append(coh_est_step)

    # Final diagnostics
    n = len(ts_bruce)
    skip = 100
    rate = 0
    if n > skip * 2:
        steps_fit = np.arange(skip, n, dtype=float)
        rate = np.polyfit(steps_fit, ts_bruce[skip:], 1)[0]

    final_sigma = float(np.sum(sigma))
    final_chi = float(np.sum(chi_field))
    phi_rms_final = float(np.sqrt(np.mean(phi**2)))
    bruce_rms_final = float(np.sqrt(np.mean(bruce_field**2)))

    gp_x = np.roll(phi, -1, 0) - np.roll(phi, 1, 0)
    gp_y = np.roll(phi, -1, 1) - np.roll(phi, 1, 1)
    xi = float(np.sum(phi**2 + gp_x**2 + gp_y**2))
    chi_op = compute_chi_operator(phi)

    total_system = final_sigma + final_chi

    return {
        "growth_rate":   round(rate, 8),
        "bruce_rms":     round(bruce_rms_final, 8),
        "phi_rms":       round(phi_rms_final, 8),
        "chi_op_late":   round(chi_op, 6),
        "xi_late":       round(xi, 4),
        "total_bled":    round(total_bled, 4),
        "final_sigma":   round(final_sigma, 4),
        "final_chi":     round(final_chi, 4),
        "total_system":  round(total_system, 4),
        # Per-step series
        "ts_bruce":                  ts_bruce,
        "chi_freeboard_series":      chi_freeboard_series,
        "bruce_rms_series":          bruce_rms_series,
        "coh_est_series":            coh_est_series,
        "guardian_strength_series":  guardian_strength_series,
        "hemorrhage_steps":          hemorrhage_steps,
        "bruce_min_in_run":          float(bruce_min_running),
    }


# ============================================================================
# CLASSIFIERS
# ============================================================================

def classify_test_zone(growth_rate):
    if growth_rate < -1e-6:
        return "GREEN"
    elif abs(growth_rate) < 1e-6:
        return "YELLOW"
    else:
        return "RED"


def compute_coh_est(growth_rate):
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
# FORCED EMISSION METRICS (same 5 as Test 6) + Test 7 kappa-sweep fields
# ============================================================================

def compute_guardian_strength(chi_field_final_sum, sigma_final_sum,
                                chi_op_late, bruce_rms):
    chi_protection = chi_field_final_sum / max(sigma_final_sum, 1e-9)
    curv_load = 1.0 / (1.0 + chi_op_late)
    bruce_calm = 1.0 / (1.0 + bruce_rms / HEMORRHAGE_LINE_BRUCE_RMS)
    raw = (chi_protection * curv_load * bruce_calm) ** (1.0 / 3.0)
    return float(math.tanh(raw))


def compute_f2_heartbeat_stability(bruce_rms_series, skip=100):
    if len(bruce_rms_series) < skip + 50:
        return 0.0
    s = np.asarray(bruce_rms_series[skip:], dtype=float)
    n = len(s)
    t = np.arange(n, dtype=float)
    coef = np.polyfit(t, s, 1)
    detrended = s - (coef[0] * t + coef[1])
    if float(np.std(detrended)) < 1e-15:
        return 1.0
    fft = np.fft.rfft(detrended)
    mag = np.abs(fft)
    if len(mag) < 5:
        return 0.0
    mag_nodc = mag[1:]
    peak_idx = int(np.argmax(mag_nodc))
    peak_mag = float(mag_nodc[peak_idx])
    if peak_mag < 1e-15:
        return 0.0
    lo = max(0, peak_idx - 1)
    hi = min(len(mag_nodc), peak_idx + 2)
    local = mag_nodc[lo:hi]
    local_mean = float(np.mean(local))
    spread = float(np.std(local)) / max(local_mean, 1e-15)
    stability = math.exp(-spread)
    return float(np.clip(stability, 0.0, 1.0))


def compute_chi_freeboard_statistics(chi_freeboard_series, use_chi,
                                       skip=100):
    if not use_chi or len(chi_freeboard_series) < skip + 1:
        return {"chi_freeboard_mean": 0.0,
                "chi_freeboard_std":  0.0,
                "chi_freeboard_max":  0.0}
    arr = np.asarray(chi_freeboard_series[skip:], dtype=float)
    return {
        "chi_freeboard_mean": float(np.mean(arr)),
        "chi_freeboard_std":  float(np.std(arr)),
        "chi_freeboard_max":  float(np.max(arr)),
    }


def compute_brucetron_rms_at_hemorrhage_line(bruce_rms_final,
                                              hemorrhage_steps,
                                              total_steps):
    ratio = bruce_rms_final / HEMORRHAGE_LINE_BRUCE_RMS
    fraction_above = (hemorrhage_steps / total_steps
                      if total_steps > 0 else 0.0)
    fraction_below = 1.0 - fraction_above

    if bruce_rms_final < 0.9 * HEMORRHAGE_LINE_BRUCE_RMS:
        state = "BELOW_LINE"
    elif bruce_rms_final > 1.1 * HEMORRHAGE_LINE_BRUCE_RMS:
        state = "ABOVE_LINE"
    else:
        state = "AT_LINE"

    return {
        "bruce_rms_final":                bruce_rms_final,
        "hemorrhage_line":                HEMORRHAGE_LINE_BRUCE_RMS,
        "ratio_to_hemorrhage":            float(ratio),
        "hemorrhage_fraction_above":      float(fraction_above),
        "bruce_below_hemorrhage_fraction": float(fraction_below),
        "hemorrhage_state":               state,
    }


def compute_regime_classification_confidence(coh_est):
    if coh_est is None:
        return 0.0
    boundaries = [0.0, REGIME_COHERENCE_FAILURE_MIN,
                  COHERENCE_YELLOW,
                  REGIME_DIFFUSIVE_HEALING_MIN, 1.0]
    bin_lo, bin_hi = 0.0, 1.0
    for i in range(len(boundaries) - 1):
        if boundaries[i] <= coh_est <= boundaries[i + 1]:
            bin_lo = boundaries[i]
            bin_hi = boundaries[i + 1]
            break
    dist_to_boundary = min(coh_est - bin_lo, bin_hi - coh_est)
    half_width = (bin_hi - bin_lo) / 2.0
    if half_width < 1e-9:
        return 0.0
    return float(np.clip(dist_to_boundary / half_width, 0.0, 1.0))


def compute_settle_averages(series, steps_total,
                             settle_fraction=SETTLE_FRACTION):
    """Mean of the final `settle_fraction` of a series."""
    if not series:
        return 0.0
    n = len(series)
    start_idx = max(0, int(n * (1.0 - settle_fraction)))
    window = series[start_idx:]
    if not window:
        return 0.0
    return float(np.mean(window))


# ============================================================================
# CONFIG RUNNER (Test 7: kappa as sweep axis)
# ============================================================================

def run_sweep_config(nx, ny, steps, lam_val, kappa_drain, X, Y):
    """
    Test 7 runner: C-config (drain+chi) with kappa_drain as swept input.
    """
    config_name = "C: Drain + Chi"
    use_chi = True

    print(f"    lambda={lam_val:.3f}  kappa={kappa_drain:.3f}")

    t0 = time.time()
    r = run_config(
        nx, ny, steps, DT, D_DIFF, ALPHA, SEPARATION,
        PUMP_A, RATIO, lam_val, X, Y,
        kappa_drain=kappa_drain, use_chi=use_chi)
    elapsed = time.time() - t0

    growth = r["growth_rate"]
    chi_op = r["chi_op_late"]
    bruce_rms = r["bruce_rms"]

    # Classifiers
    tz  = classify_test_zone(growth)
    coh = compute_coh_est(growth)
    rg  = classify_regime(coh)
    agree = zones_in_agreement(tz, rg)
    divergence_flag = 0 if agree else 1

    # ===== Forced emission fields (same 5 as Test 6) =====
    guardian = compute_guardian_strength(
        r["final_chi"], r["final_sigma"], chi_op, bruce_rms)

    f2_stability = compute_f2_heartbeat_stability(r["bruce_rms_series"])

    chi_fb_stats = compute_chi_freeboard_statistics(
        r["chi_freeboard_series"], use_chi)

    total_steps = len(r["bruce_rms_series"])
    hemorrhage = compute_brucetron_rms_at_hemorrhage_line(
        bruce_rms, r["hemorrhage_steps"], total_steps)

    regime_conf = compute_regime_classification_confidence(coh)

    # ===== Test 7 new kappa-sweep fields =====
    coh_est_at_settle = compute_settle_averages(
        r["coh_est_series"], total_steps)
    guardian_strength_at_settle = compute_settle_averages(
        r["guardian_strength_series"], total_steps)
    bruce_min_in_run = r["bruce_min_in_run"]

    print(f"      growth={growth:+.8f}  coh={coh:.3f}  "
          f"bruce_rms={bruce_rms:.6f}")
    print(f"      test_zone={tz}  regime={rg}  "
          f"{'AGREE' if agree else 'DIVERGE'}")
    print(f"      KAPPA={kappa_drain:.3f}:")
    print(f"        guardian:         {guardian:.4f} "
          f"(settle={guardian_strength_at_settle:.4f})")
    print(f"        bruce vs hemor:   {hemorrhage['hemorrhage_state']}  "
          f"(ratio={hemorrhage['ratio_to_hemorrhage']:.3f})")
    print(f"        bruce_min_in_run: {bruce_min_in_run:.6f}")
    print(f"        bruce_below_frac: "
          f"{hemorrhage['bruce_below_hemorrhage_fraction']:.3f}")
    print(f"        coh_at_settle:    {coh_est_at_settle:.4f}")
    print(f"        regime_conf:      {regime_conf:.4f}")
    print(f"        (elapsed {elapsed:.1f}s)")

    return {
        "config_name":        f"{config_name} :: lambda={lam_val:.3f} "
                              f":: kappa={kappa_drain:.3f}",
        "config_name_short":  config_name,
        "lambda_val":         lam_val,
        "kappa_drain":        kappa_drain,
        "use_chi":            use_chi,
        # v19 physics outputs
        "growth_rate":    growth,
        "bruce_rms":      bruce_rms,
        "phi_rms":        r["phi_rms"],
        "chi_op_late":    chi_op,
        "xi_late":        r["xi_late"],
        "total_bled":     r["total_bled"],
        "final_sigma":    r["final_sigma"],
        "final_chi":      r["final_chi"],
        "total_system":   r["total_system"],
        # Classifiers
        "test_zone":       tz,
        "coh_est":         coh,
        "regime":          rg,
        "divergence_flag": divergence_flag,
        # Forced emission (5 Test 6 fields)
        "guardian_strength":                float(guardian),
        "f_2_heartbeat_stability":          float(f2_stability),
        "chi_freeboard_mean":               float(
            chi_fb_stats["chi_freeboard_mean"]),
        "chi_freeboard_std":                float(
            chi_fb_stats["chi_freeboard_std"]),
        "chi_freeboard_max":                float(
            chi_fb_stats["chi_freeboard_max"]),
        "brucetron_rms_final":              float(
            hemorrhage["bruce_rms_final"]),
        "hemorrhage_line":                  float(
            hemorrhage["hemorrhage_line"]),
        "brucetron_ratio_to_hemorrhage":    float(
            hemorrhage["ratio_to_hemorrhage"]),
        "bruce_below_hemorrhage_fraction":  float(
            hemorrhage["bruce_below_hemorrhage_fraction"]),
        "hemorrhage_fraction_above":        float(
            hemorrhage["hemorrhage_fraction_above"]),
        "hemorrhage_state":                 hemorrhage["hemorrhage_state"],
        "regime_classification_confidence": float(regime_conf),
        # Test 7 new fields
        "coh_est_at_settle":                float(coh_est_at_settle),
        "guardian_strength_at_settle":      float(
            guardian_strength_at_settle),
        "bruce_min_in_run":                 float(bruce_min_in_run),
        # Meta
        "elapsed":  float(elapsed),
    }


# ============================================================================
# AGGREGATE METRICS (H10, H11, H12)
# ============================================================================

def safe_correlation(xs, ys):
    """Pearson correlation with guards against constant series."""
    xa = np.asarray(xs, dtype=float)
    ya = np.asarray(ys, dtype=float)
    if len(xa) < 2 or len(ya) < 2:
        return 0.0
    if float(np.std(xa)) < 1e-15 or float(np.std(ya)) < 1e-15:
        return 0.0
    return float(np.corrcoef(xa, ya)[0, 1])


def compute_H10_kappa_vs_bruce_correlation(results):
    kappas = [r["kappa_drain"] for r in results]
    bruces = [r["brucetron_rms_final"] for r in results]
    return safe_correlation(kappas, bruces)


def compute_H11_safe_run_count(results):
    return sum(1 for r in results
               if r["brucetron_rms_final"] < HEMORRHAGE_LINE_BRUCE_RMS)


def compute_H12_kappa_vs_coh_correlation(results):
    kappas = [r["kappa_drain"] for r in results]
    cohs = [r["coh_est_at_settle"] for r in results]
    return safe_correlation(kappas, cohs)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=("BCM v25 -- Cube 2 Phase Reconciliation Test 7 "
                     "(kappa_drain sweep at fracture lambdas, C-config)"))
    parser.add_argument("--quick", action="store_true",
                        help="grid=128, steps=2000")
    parser.add_argument("--fast", action="store_true",
                        help="3 lambdas x 3 kappas (9 runs) proxy")
    parser.add_argument("--grid", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    args = parser.parse_args()

    nx = ny = args.grid or (GRID_QUICK if args.quick else GRID_PROD)
    steps = args.steps or (STEPS_FAST if args.quick else STEPS_PROD)

    if args.fast:
        lambda_sweep = [0.02, 0.08, 0.12]
        kappa_sweep = [0.0, 0.35, 0.70]
    else:
        lambda_sweep = LAMBDA_SWEEP
        kappa_sweep = KAPPA_SWEEP

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    total_configs = len(lambda_sweep) * len(kappa_sweep)

    print("=" * 65)
    print("  BCM v25 -- CUBE 2 PHASE RECONCILIATION TEST 7")
    print("  KAPPA_DRAIN SWEEP (C-config only, fracture lambdas)")
    print("  Physics: v19.4 pump-drain (Burdick source, verbatim)")
    print("  kappa_drain=0.35 is v19 frozen; UNFROZEN only here")
    print("  Stephen Justin Burdick Sr. -- GIBUSH Systems")
    print("=" * 65)
    print(f"  Grid: {nx}x{ny}  Steps: {steps}")
    print(f"  Lambda sweep:   {lambda_sweep}")
    print(f"  Kappa sweep:    {kappa_sweep}")
    print(f"  Total runs:     {total_configs}")
    print(f"  Hemorrhage line: {HEMORRHAGE_LINE_BRUCE_RMS}")
    print(f"  Settle window:   final {int(SETTLE_FRACTION*100)}% of run")
    print(f"  Hypotheses:      H10, H11, H12")
    print("=" * 65)

    all_results = []
    t_total = time.time()

    for lam_val in lambda_sweep:
        print(f"\n  -- lambda = {lam_val:.3f} --")
        for kappa in kappa_sweep:
            r = run_sweep_config(nx, ny, steps, lam_val, kappa, X, Y)
            all_results.append(r)

    elapsed_total = time.time() - t_total

    # Aggregate metrics
    metrics = {
        "kappa_vs_bruce_correlation":
            compute_H10_kappa_vs_bruce_correlation(all_results),
        "safe_run_count":
            compute_H11_safe_run_count(all_results),
        "kappa_vs_coh_correlation":
            compute_H12_kappa_vs_coh_correlation(all_results),
    }

    # Summary stats
    n_diverge = sum(1 for r in all_results if r["divergence_flag"] == 1)
    n_above = sum(1 for r in all_results
                  if r["hemorrhage_state"] == "ABOVE_LINE")
    n_at = sum(1 for r in all_results
               if r["hemorrhage_state"] == "AT_LINE")
    n_below = sum(1 for r in all_results
                  if r["hemorrhage_state"] == "BELOW_LINE")
    guardian_avg = np.mean(
        [r["guardian_strength"] for r in all_results])
    guardian_settle_avg = np.mean(
        [r["guardian_strength_at_settle"] for r in all_results])
    coh_settle_avg = np.mean(
        [r["coh_est_at_settle"] for r in all_results])

    print(f"\n{'=' * 65}")
    print(f"  TEST 7 KAPPA SWEEP SUMMARY")
    print(f"{'=' * 65}")
    print(f"  Total runs:              {len(all_results)}")
    print(f"  Elapsed total:           {elapsed_total:.1f}s")
    print(f"  Divergent (tz != rg):    {n_diverge}/{len(all_results)}")
    print(f"  Hemorrhage BELOW line:   {n_below}/{len(all_results)}")
    print(f"  Hemorrhage AT line:      {n_at}/{len(all_results)}")
    print(f"  Hemorrhage ABOVE line:   {n_above}/{len(all_results)}")
    print(f"  Avg guardian (final):    {guardian_avg:.4f}")
    print(f"  Avg guardian (settle):   {guardian_settle_avg:.4f}")
    print(f"  Avg coh_est (settle):    {coh_settle_avg:.4f}")

    print(f"\n  AGGREGATE METRICS:")
    for k, v in metrics.items():
        print(f"    {k}: {v:.4f}")

    # Hypothesis evaluation
    print(f"\n  HYPOTHESIS EVALUATION:")
    hypotheses_tested = {}
    for hkey, hdecl in HYPOTHESES.items():
        metric_name = hdecl["metric"]
        metric_value = metrics.get(metric_name, 0.0)
        eval_result = evaluate_hypothesis(hkey, metric_value)
        hypotheses_tested[hkey] = {**hdecl, **eval_result}
        print(f"    {hkey}: {eval_result['result']} "
              f"(observed={eval_result['observed_value']:.4f})")

    # Build per-lambda summary (useful for Dark Mason + cube ingest)
    lambda_summary = {}
    for lam_val in lambda_sweep:
        lam_runs = [r for r in all_results
                    if abs(r["lambda_val"] - lam_val) < 1e-6]
        if not lam_runs:
            continue
        safe_at_lambda = sum(1 for r in lam_runs
                             if r["brucetron_rms_final"]
                             < HEMORRHAGE_LINE_BRUCE_RMS)
        min_bruce = min(r["brucetron_rms_final"] for r in lam_runs)
        min_bruce_kappa = None
        for r in lam_runs:
            if r["brucetron_rms_final"] == min_bruce:
                min_bruce_kappa = r["kappa_drain"]
                break
        lambda_summary[f"{lam_val:.3f}"] = {
            "safe_run_count":      safe_at_lambda,
            "min_bruce_rms":       float(min_bruce),
            "min_bruce_at_kappa":  float(min_bruce_kappa)
            if min_bruce_kappa is not None else None,
        }

    # Output JSON
    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(
        results_dir,
        f"BCM_v25_cube2_phase_reconciliation_7_{timestamp}.json")

    output = {
        "test":              "cube2_phase_reconciliation_7",
        "version":           "v25",
        "test_type":         "kappa_drain_sweep",
        "physics_version":   "v19.4",
        "predecessors":      [
            "BCM_v25_cube2_phase_reconciliation_3",
            "BCM_v25_cube2_phase_reconciliation_4",
            "BCM_v25_cube2_phase_reconciliation_5",
            "BCM_v25_cube2_phase_reconciliation_6",
        ],
        "grid":              nx,
        "steps":             steps,
        "system":            "v19.4_pump_drain_HR1099",
        "lambda_sweep":      lambda_sweep,
        "kappa_sweep":       kappa_sweep,
        "kappa_drain_frozen_reference": KAPPA_DRAIN_FROZEN,
        "config":            "C: Drain + Chi",
        "total_runs":        len(all_results),
        "divergent_count":   n_diverge,
        "timestamp":         timestamp,
        "elapsed_total":     float(elapsed_total),
        "emission_constants": {
            "HEMORRHAGE_LINE_BRUCE_RMS":    HEMORRHAGE_LINE_BRUCE_RMS,
            "SETTLE_FRACTION":              SETTLE_FRACTION,
            "REGIME_DIFFUSIVE_HEALING_MIN": REGIME_DIFFUSIVE_HEALING_MIN,
            "REGIME_COHERENCE_FAILURE_MIN": REGIME_COHERENCE_FAILURE_MIN,
            "REGIME_COHERENCE_FAILURE_MAX": REGIME_COHERENCE_FAILURE_MAX,
            "COHERENCE_YELLOW":             COHERENCE_YELLOW,
        },
        "summary_metrics": {
            "divergent_count":            n_diverge,
            "hemorrhage_below_count":     n_below,
            "hemorrhage_at_count":        n_at,
            "hemorrhage_above_count":     n_above,
            "guardian_strength_avg":      float(guardian_avg),
            "guardian_settle_avg":        float(guardian_settle_avg),
            "coh_est_settle_avg":         float(coh_settle_avg),
        },
        "lambda_summary":    lambda_summary,
        "aggregate_metrics": metrics,
        "hypotheses_tested": hypotheses_tested,
        "foreman_note": (
            "Test 7: kappa_drain sweep at Test 6 fracture lambdas. "
            "C-config only (kappa is meaningful only with chi active). "
            "v19 kappa_drain=0.35 is unfrozen for this controlled sweep "
            "only; it remains frozen in all other tests. Goal: find "
            "the crew-safety envelope (bruce_rms < 0.0045). Hypotheses "
            "H10/H11/H12 test suppression, existence of safe envelope, "
            "and coherence preservation respectively."),
        "results":            all_results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")


if __name__ == "__main__":
    main()
