# -*- coding: utf-8 -*-
"""
BCM v25 -- Cube 2 Phase Reconciliation Test 6
===============================================
Forced-Emission Sweep at 500-Anomaly Coordinates
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick. Claude is code executor only.

PRIMACY STATEMENT
-----------------
Burdick Crag Mass (BCM) is the sole theoretical framework of Stephen
Justin Burdick Sr. Built under his direction per contract
BCM_TEST_TEMPLATE_CONTRACT.py v1.1. Grok specified the forced-
emission strategy; Foreman Burdick locked the filename convention
(enumerate test number up within version). Claude implements.

PURPOSE
-------
Tests 3, 4, 5 surfaced 500 STABLE anomalies at Cube 2. The cube is
flagging the same classification mismatch repeatedly because the
test output is missing vocabulary the cube wants to see. This test
runs v19.4 pump-drain physics at the EXACT (lambda, config) points
where the 500 cluster, and forces emission of the five fields the
cube has been complaining about:

  1. guardian_strength         (crew-safety envelope metric)
  2. f_2_heartbeat_stability   (Fourier stability of bruce energy)
  3. chi_freeboard             (Baume floor level, v19 internal)
  4. brucetron_rms_vs_hemorrhage_line  (bruce_rms vs 0.0045)
  5. regime_classification_confidence  (distance from bin boundary)

LOCKED SCOPE
------------
  lambda sweep : 0.02, 0.04, 0.06, 0.08, 0.10, 0.12  (6 values)
  configs      : B: Drain only, C: Drain + Chi  (2 configs)
  total runs   : 12
  grid         : 256
  steps        : 5000
  physics      : v19.4 pump-drain (verbatim, unchanged)

No new hypotheses tested. This is vocabulary infill only. The cube
ingests these values and updates its formula surface; the next cube
report either tightens anomalies or surfaces a cleaner question.

OUTPUT: data/results/BCM_v25_cube2_phase_reconciliation_6_{ts}.json
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
# FROZEN CONSTANTS (v19.4 physics + cube emission thresholds)
# ============================================================================
KAPPA_DRAIN = 0.35
DT          = 0.05
D_DIFF      = 0.5
PUMP_A      = 0.5
RATIO       = 0.25
ALPHA       = 0.80
SEPARATION  = 15.0

GRID_PROD  = 256
GRID_QUICK = 128
STEPS_PROD = 5000
STEPS_FAST = 2000

# v24 regime thresholds (for classification + confidence metric)
REGIME_DIFFUSIVE_HEALING_MIN = 0.95
REGIME_COHERENCE_FAILURE_MIN = 0.74
REGIME_COHERENCE_FAILURE_MAX = 0.85
COHERENCE_YELLOW             = 0.85

# LOCKED anomaly-coordinate sweep (Grok spec)
LAMBDA_SWEEP = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12]

# LOCKED configs (two at the disagreement zone)
CONFIGS = [
    ("B: Drain only",   KAPPA_DRAIN, False),
    ("C: Drain + Chi",  KAPPA_DRAIN, True),
]

# Guardian hemorrhage line (Foreman-confirmed: bruce_rms threshold)
HEMORRHAGE_LINE_BRUCE_RMS = 0.0045


# ============================================================================
# V19.4 PHYSICS -- VERBATIM (Burdick source, do not modify)
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
    """
    v19.4 physics loop -- verbatim from Burdick source, with additional
    time-series tracking for Test 6 forced emission:
      - chi_freeboard_series : fl value per step (when use_chi)
      - bruce_rms_series     : bruce_rms per step
      - phi_rms_series       : phi_rms per step
      - hemorrhage_steps     : count of steps where bruce_rms > 0.0045
    """
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
    # Test 6 forced emission tracking
    chi_freeboard_series = []
    bruce_rms_series = []
    phi_rms_series = []
    hemorrhage_steps = 0

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

        # Test 6 forced emission: per-step tracking
        bruce_rms_step = float(np.sqrt(np.mean(bruce_field**2)))
        phi_rms_step = float(np.sqrt(np.mean(phi**2)))

        ts_bruce.append(float(np.sum(bruce_field**2)))
        chi_freeboard_series.append(chi_freeboard_step)
        bruce_rms_series.append(bruce_rms_step)
        phi_rms_series.append(phi_rms_step)
        if bruce_rms_step > HEMORRHAGE_LINE_BRUCE_RMS:
            hemorrhage_steps += 1

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
        # Standard v19 outputs (verbatim)
        "growth_rate":   round(rate, 8),
        "bruce_rms":     round(bruce_rms_final, 8),
        "phi_rms":       round(phi_rms_final, 8),
        "chi_op_late":   round(chi_op, 6),
        "xi_late":       round(xi, 4),
        "total_bled":    round(total_bled, 4),
        "final_sigma":   round(final_sigma, 4),
        "final_chi":     round(final_chi, 4),
        "total_system":  round(total_system, 4),
        # Test 6 time series (for downstream metrics)
        "ts_bruce":            ts_bruce,
        "chi_freeboard_series": chi_freeboard_series,
        "bruce_rms_series":    bruce_rms_series,
        "phi_rms_series":      phi_rms_series,
        "hemorrhage_steps":    hemorrhage_steps,
    }


# ============================================================================
# CLASSIFIERS (verbatim from prior tests)
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
# FORCED EMISSION METRICS (Grok spec: 5 fields)
# ============================================================================

def compute_guardian_strength(chi_field_final_sum, sigma_final_sum,
                                chi_op_late, bruce_rms):
    """
    Guardian crew-safety envelope metric.

    Construction (Foreman-confirmed principle):
      - chi field sum indicates 4D headspace absorption capacity
      - sigma sum indicates 3D substrate pressure
      - chi_op_late indicates structural curvature load
      - bruce_rms indicates active field disturbance

    Healthy envelope: high chi absorption, moderate sigma, low chi_op,
    low bruce_rms. Score scales [0, 1] where 1.0 = maximum protection.

    Formula: sigmoid-normalized composite.
    """
    # Higher chi absorption is protective
    chi_protection = chi_field_final_sum / max(sigma_final_sum, 1e-9)
    # Lower structural curvature is protective
    curv_load = 1.0 / (1.0 + chi_op_late)
    # Lower bruce disturbance is protective
    bruce_calm = 1.0 / (1.0 + bruce_rms / HEMORRHAGE_LINE_BRUCE_RMS)

    # Composite: geometric mean of protective factors, bounded
    raw = (chi_protection * curv_load * bruce_calm) ** (1.0 / 3.0)
    # Squash via tanh to [0, 1]
    guardian = math.tanh(raw)
    return float(guardian)


def compute_f2_heartbeat_stability(bruce_rms_series, skip=100):
    """
    f/2 heartbeat stability: stability of bruce_rms oscillation period.

    Method:
      - Discard first `skip` steps (transient)
      - Detrend linearly
      - Compute FFT; find dominant frequency
      - Stability = inverse of frequency spread (std of top-3
        frequency bins around peak, normalized by peak magnitude)

    Returns value in [0, 1]: 1.0 = perfect heartbeat, 0 = chaotic.
    """
    if len(bruce_rms_series) < skip + 50:
        return 0.0
    s = np.asarray(bruce_rms_series[skip:], dtype=float)
    n = len(s)
    # Detrend
    t = np.arange(n, dtype=float)
    coef = np.polyfit(t, s, 1)
    detrended = s - (coef[0] * t + coef[1])

    if float(np.std(detrended)) < 1e-15:
        # Flat series: perfectly stable (no oscillation to disrupt)
        return 1.0

    # FFT
    fft = np.fft.rfft(detrended)
    mag = np.abs(fft)
    # Skip DC bin
    if len(mag) < 5:
        return 0.0
    mag_nodc = mag[1:]
    peak_idx = int(np.argmax(mag_nodc))
    peak_mag = float(mag_nodc[peak_idx])
    if peak_mag < 1e-15:
        return 0.0

    # Spread in top-3 bins around peak
    lo = max(0, peak_idx - 1)
    hi = min(len(mag_nodc), peak_idx + 2)
    local = mag_nodc[lo:hi]
    local_mean = float(np.mean(local))
    spread = float(np.std(local)) / max(local_mean, 1e-15)

    # Lower spread = more stable. Map to [0,1] via exp decay
    stability = math.exp(-spread)
    return float(np.clip(stability, 0.0, 1.0))


def compute_chi_freeboard_statistics(chi_freeboard_series, use_chi,
                                       skip=100):
    """
    Chi freeboard statistics over the run.

    Returns mean and std of the Baume floor level during the run.
    If use_chi=False, chi freeboard was not computed -- returns zeros.
    """
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
    """
    Brucetron RMS vs 0.0045 hemorrhage line.

    Returns:
      bruce_rms_final          (the final RMS)
      hemorrhage_line          (0.0045, the threshold)
      ratio_to_hemorrhage      (bruce_rms_final / 0.0045)
      hemorrhage_fraction      (fraction of run above line)
      hemorrhage_state         (below / at / above)
    """
    ratio = bruce_rms_final / HEMORRHAGE_LINE_BRUCE_RMS
    fraction = (hemorrhage_steps / total_steps
                if total_steps > 0 else 0.0)

    if bruce_rms_final < 0.9 * HEMORRHAGE_LINE_BRUCE_RMS:
        state = "BELOW_LINE"
    elif bruce_rms_final > 1.1 * HEMORRHAGE_LINE_BRUCE_RMS:
        state = "ABOVE_LINE"
    else:
        state = "AT_LINE"

    return {
        "bruce_rms_final":        bruce_rms_final,
        "hemorrhage_line":        HEMORRHAGE_LINE_BRUCE_RMS,
        "ratio_to_hemorrhage":    float(ratio),
        "hemorrhage_fraction":    float(fraction),
        "hemorrhage_state":       state,
    }


def compute_regime_classification_confidence(coh_est):
    """
    Regime classification confidence: distance of coh_est from nearest
    regime bin boundary, normalized to bin half-width.

    Bins (from v24 thresholds):
      BOUNDARY_NONLINEAR : [0.00, 0.74)
      COHERENCE_FAILURE  : [0.74, 0.85)
      MARGINAL           : [0.85, 0.95)
      DIFFUSIVE_HEALING  : [0.95, 1.00]

    Returns value in [0, 1]:
      1.0 = coh_est is at center of its bin (high confidence)
      0.0 = coh_est is right at a bin boundary (low confidence)
    """
    if coh_est is None:
        return 0.0

    boundaries = [0.0, REGIME_COHERENCE_FAILURE_MIN,
                  COHERENCE_YELLOW,
                  REGIME_DIFFUSIVE_HEALING_MIN, 1.0]

    # Find which bin coh_est is in
    bin_lo, bin_hi = 0.0, 1.0
    for i in range(len(boundaries) - 1):
        if boundaries[i] <= coh_est <= boundaries[i + 1]:
            bin_lo = boundaries[i]
            bin_hi = boundaries[i + 1]
            break

    # Distance to nearest boundary
    dist_to_boundary = min(coh_est - bin_lo, bin_hi - coh_est)
    half_width = (bin_hi - bin_lo) / 2.0
    if half_width < 1e-9:
        return 0.0

    # Normalize: 0 at boundary, 1 at center
    confidence = dist_to_boundary / half_width
    return float(np.clip(confidence, 0.0, 1.0))


# ============================================================================
# CONFIG RUNNER
# ============================================================================

def run_reconciliation_config(nx, ny, steps, lam_val, config_name,
                               kappa_drain, use_chi, X, Y):
    """
    Run one (lambda, config) pair and emit all five forced fields.
    """
    print(f"    lambda={lam_val:.3f}  {config_name}")

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

    # Derived
    divergence_flag = 0 if agree else 1

    # ========= FORCED EMISSION: 5 fields =========

    # 1. guardian_strength
    guardian = compute_guardian_strength(
        r["final_chi"], r["final_sigma"], chi_op, bruce_rms)

    # 2. f/2 heartbeat stability
    f2_stability = compute_f2_heartbeat_stability(r["bruce_rms_series"])

    # 3. chi freeboard statistics
    chi_fb_stats = compute_chi_freeboard_statistics(
        r["chi_freeboard_series"], use_chi)

    # 4. brucetron rms at hemorrhage line (0.0045)
    hemorrhage = compute_brucetron_rms_at_hemorrhage_line(
        bruce_rms, r["hemorrhage_steps"], len(r["bruce_rms_series"]))

    # 5. regime classification confidence
    regime_conf = compute_regime_classification_confidence(coh)

    # ========= END FORCED EMISSION =========

    print(f"      growth={growth:+.8f}  coh={coh:.3f}  "
          f"chi_op={chi_op:.4f}  bruce_rms={bruce_rms:.6f}")
    print(f"      test_zone={tz}  regime={rg}  "
          f"{'AGREE' if agree else 'DIVERGE'}")
    print(f"      FORCED EMIT:")
    print(f"        guardian_strength:    {guardian:.4f}")
    print(f"        f_2_heartbeat_stab:   {f2_stability:.4f}")
    print(f"        chi_freeboard_mean:   "
          f"{chi_fb_stats['chi_freeboard_mean']:.6f}")
    print(f"        bruce vs hemorrhage:  "
          f"{hemorrhage['hemorrhage_state']}  "
          f"(ratio={hemorrhage['ratio_to_hemorrhage']:.3f})")
    print(f"        regime_confidence:    {regime_conf:.4f}")
    print(f"        (elapsed {elapsed:.1f}s)")

    return {
        "config_name":        f"{config_name} :: lambda={lam_val:.3f}",
        "config_name_short":  config_name,
        "lambda_val":         lam_val,
        "kappa_drain":        kappa_drain,
        "use_chi":            use_chi,
        # v19 physics outputs (verbatim)
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
        # FORCED EMISSION: 5 fields the cube was asking for
        "guardian_strength":               float(guardian),
        "f_2_heartbeat_stability":         float(f2_stability),
        "chi_freeboard_mean":              float(
            chi_fb_stats["chi_freeboard_mean"]),
        "chi_freeboard_std":               float(
            chi_fb_stats["chi_freeboard_std"]),
        "chi_freeboard_max":               float(
            chi_fb_stats["chi_freeboard_max"]),
        "brucetron_rms_final":             float(
            hemorrhage["bruce_rms_final"]),
        "hemorrhage_line":                 float(
            hemorrhage["hemorrhage_line"]),
        "brucetron_ratio_to_hemorrhage":   float(
            hemorrhage["ratio_to_hemorrhage"]),
        "hemorrhage_fraction":             float(
            hemorrhage["hemorrhage_fraction"]),
        "hemorrhage_state":                hemorrhage["hemorrhage_state"],
        "regime_classification_confidence": float(regime_conf),
        # Meta
        "elapsed":  float(elapsed),
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=("BCM v25 -- Cube 2 Phase Reconciliation Test 6 "
                     "(forced emission at 500-anomaly coordinates)"))
    parser.add_argument("--quick", action="store_true",
                        help="grid=128, steps=2000")
    parser.add_argument("--fast", action="store_true",
                        help="3 lambdas x 2 configs (6 runs) proxy")
    parser.add_argument("--grid", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    args = parser.parse_args()

    nx = ny = args.grid or (GRID_QUICK if args.quick else GRID_PROD)
    steps = args.steps or (STEPS_FAST if args.quick else STEPS_PROD)

    if args.fast:
        lambda_sweep = [0.02, 0.08, 0.12]
    else:
        lambda_sweep = LAMBDA_SWEEP

    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    total_configs = len(lambda_sweep) * len(CONFIGS)

    print("=" * 65)
    print("  BCM v25 -- CUBE 2 PHASE RECONCILIATION TEST 6")
    print("  FORCED EMISSION SWEEP (500-anomaly coordinates)")
    print("  Physics: v19.4 pump-drain (Burdick source, verbatim)")
    print("  Stephen Justin Burdick Sr. -- GIBUSH Systems")
    print("=" * 65)
    print(f"  Grid: {nx}x{ny}  Steps: {steps}")
    print(f"  Lambda sweep: {lambda_sweep}")
    print(f"  Configs: {[c[0] for c in CONFIGS]}")
    print(f"  Total runs: {total_configs}")
    print(f"  Hemorrhage line (bruce_rms): {HEMORRHAGE_LINE_BRUCE_RMS}")
    print(f"  Forced emission fields: 5")
    print(f"    1. guardian_strength")
    print(f"    2. f_2_heartbeat_stability")
    print(f"    3. chi_freeboard_mean/std/max")
    print(f"    4. brucetron_rms vs hemorrhage_line")
    print(f"    5. regime_classification_confidence")
    print("=" * 65)

    all_results = []
    t_total = time.time()

    for lam_val in lambda_sweep:
        print(f"\n  -- lambda = {lam_val:.3f} --")
        for config_name, kappa_drain, use_chi in CONFIGS:
            r = run_reconciliation_config(
                nx, ny, steps, lam_val, config_name,
                kappa_drain, use_chi, X, Y)
            all_results.append(r)

    elapsed_total = time.time() - t_total

    # Summary
    n_diverge = sum(1 for r in all_results if r["divergence_flag"] == 1)
    n_hemorrhage_above = sum(1 for r in all_results
                             if r["hemorrhage_state"] == "ABOVE_LINE")
    n_hemorrhage_at = sum(1 for r in all_results
                          if r["hemorrhage_state"] == "AT_LINE")
    guardian_avg = (sum(r["guardian_strength"] for r in all_results)
                    / len(all_results))
    f2_avg = (sum(r["f_2_heartbeat_stability"] for r in all_results)
              / len(all_results))
    regime_conf_avg = (sum(r["regime_classification_confidence"]
                           for r in all_results)
                       / len(all_results))

    print(f"\n{'=' * 65}")
    print(f"  TEST 6 FORCED EMISSION SUMMARY")
    print(f"{'=' * 65}")
    print(f"  Total runs:              {len(all_results)}")
    print(f"  Elapsed total:           {elapsed_total:.1f}s")
    print(f"  Divergent (tz != rg):    {n_diverge}/{len(all_results)}")
    print(f"  Hemorrhage ABOVE line:   "
          f"{n_hemorrhage_above}/{len(all_results)}")
    print(f"  Hemorrhage AT line:      "
          f"{n_hemorrhage_at}/{len(all_results)}")
    print(f"  Avg guardian_strength:   {guardian_avg:.4f}")
    print(f"  Avg f/2 heartbeat stab:  {f2_avg:.4f}")
    print(f"  Avg regime confidence:   {regime_conf_avg:.4f}")

    # Output JSON
    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(
        results_dir,
        f"BCM_v25_cube2_phase_reconciliation_6_{timestamp}.json")

    output = {
        "test":              "cube2_phase_reconciliation_6",
        "version":           "v25",
        "test_type":         "forced_emission",
        "physics_version":   "v19.4",
        "predecessors":      [
            "BCM_v25_cube2_phase_reconciliation_3",
            "BCM_v25_cube2_phase_reconciliation_4",
            "BCM_v25_cube2_phase_reconciliation_5",
        ],
        "grid":              nx,
        "steps":             steps,
        "system":            "v19.4_pump_drain_HR1099",
        "lambda_sweep":      lambda_sweep,
        "configs_tested":    [c[0] for c in CONFIGS],
        "total_runs":        len(all_results),
        "divergent_count":   n_diverge,
        "timestamp":         timestamp,
        "elapsed_total":     float(elapsed_total),
        "forced_emission_fields": [
            "guardian_strength",
            "f_2_heartbeat_stability",
            "chi_freeboard_mean",
            "chi_freeboard_std",
            "chi_freeboard_max",
            "brucetron_rms_final",
            "hemorrhage_line",
            "brucetron_ratio_to_hemorrhage",
            "hemorrhage_fraction",
            "hemorrhage_state",
            "regime_classification_confidence",
        ],
        "emission_constants": {
            "HEMORRHAGE_LINE_BRUCE_RMS":    HEMORRHAGE_LINE_BRUCE_RMS,
            "REGIME_DIFFUSIVE_HEALING_MIN": REGIME_DIFFUSIVE_HEALING_MIN,
            "REGIME_COHERENCE_FAILURE_MIN": REGIME_COHERENCE_FAILURE_MIN,
            "REGIME_COHERENCE_FAILURE_MAX": REGIME_COHERENCE_FAILURE_MAX,
            "COHERENCE_YELLOW":             COHERENCE_YELLOW,
        },
        "summary_metrics": {
            "divergent_count":        n_diverge,
            "hemorrhage_above_count": n_hemorrhage_above,
            "hemorrhage_at_count":    n_hemorrhage_at,
            "guardian_strength_avg":  float(guardian_avg),
            "f_2_heartbeat_avg":      float(f2_avg),
            "regime_confidence_avg":  float(regime_conf_avg),
        },
        "hypotheses_tested": {},  # No new hypotheses; vocab infill only
        "foreman_note": (
            "Test 6: forced-emission sweep at the exact "
            "(lambda, config) coordinates where the 500 STABLE "
            "anomalies cluster. Physics is v19.4 pump-drain unchanged. "
            "Five fields the cube was asking for are now emitted per "
            "run. Goal: fill vocabulary gaps and let the cube either "
            "tighten its formulas or surface a cleaner question on "
            "the next report. No new hypotheses tested here -- this "
            "is vocabulary infill only."),
        "results":            all_results,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")


if __name__ == "__main__":
    main()
