# -*- coding: utf-8 -*-
"""
BCM v26 Paper B Probe Test 5_15
Paper B Section 7.2 -- xi-Response Curve + Stiffness Manifold Detection

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-04-22

--------------------------------------------------------------------
PRIMACY STATEMENT
--------------------------------------------------------------------
All theoretical concepts, the Anchor Equation, the stiffness-
manifold reframing of the Paper B Section 5 transition topology,
the decision to convert fold-bifurcation detection into stiffness-
manifold detection based on the 5_14 audit finding, the three-
component stiffness functional (runtime slowing, J-squared
gradient structure, solver convergence delay), the six-value xi
response curve design, the Hemorrhage Line hysteresis threshold,
the chi_freeboard_mean target, and every originating insight in
this file belong solely to Stephen Justin Burdick Sr. AI systems
were used strictly as computational processing tools and code
executors at the direction of the Foreman. No AI system
contributed theoretical concepts. Emerald Entities LLC -- GIBUSH
Systems.

--------------------------------------------------------------------
5_14 AUDIT FINDING (RECORDED)
--------------------------------------------------------------------
Test 5_14 (xi = 0.015) produced sweep data numerically identical to
5_12 (xi = 0.035) to 10+ decimal places, with G(xi=0.015) /
G(xi=0.035) = 1.0000. The J-squared magnitude observed across 5_10
through 5_14 sits at floor level:

    basin lambdas:       |J|^2 ~ 1e-25 to 1e-26
    fold transition:     |J|^2 ~ 2.87e-24 to 1.45e-18  (peak)
    cold torus:          |J|^2 ~ 1e-34 to 1e-88

The PDE coupling term xi * |J|^2 * (1 - sigma) is therefore smaller
than machine-epsilon-relative-to-other-terms regardless of the xi
value used. The transition and hysteresis signatures observed in
5_10 through 5_14 are NOT J-mediated saddle-node fold
bifurcations. They are:

  - Phi-sigmoid transition at lambda_c = 0.0592: driven by the
    Taylor kernel equilibrium sigma_eq = (a - lambda) / b
    collapsing as lambda approaches a = 0.12, shaped by nonlinear
    saturation -b*sigma^2 into sigmoid form.

  - Hysteresis area 0.050 on the return sweep: driven by the
    alpha-regularization memory term alpha * (sigma - sigma_prev)
    preserving the dead-field state across the return traverse,
    not by J-back-reaction.

The root cause of inactive J is that Psi_bruce is currently
defined as the Gaussian-smoothed local RMS of sigma fluctuations.
For a settled sigma field in Taylor equilibrium, Psi_bruce ~ 0,
which drives P = pump_A * pump_B * Psi_bruce ~ 0 and therefore
|J|^2 = |grad P|^2 ~ 0. This is a theoretical formulation
question (Psi_bruce definition) and belongs to the Foreman and
Gemini, not to the code executor.

--------------------------------------------------------------------
SCOPE OF 5_15 (STIFFNESS MANIFOLD DETECTION)
--------------------------------------------------------------------
The Phi-sigmoid transition is real. The critical slowing near
lambda_c is real. The hysteresis is real. None of these require
J-coupling to be load-bearing. Test 5_15 reframes Paper B Section
5 topology evidence from "fold bifurcation" (J-mediated saddle-
node) to "stiffness manifold" (Taylor-kernel-origin numerical
delicacy near sigma_eq collapse).

A stiffness manifold is a region in (lambda, sigma) parameter
space where the PDE solver exhibits simultaneous:

  1. Elevated runtime (n_steps / baseline_steps >> 1)
  2. Non-trivial spatial gradient structure in |J|^2 (even if
     magnitude is at floor)
  3. Delayed solver convergence (many L^2 threshold crossings
     before the 20-consecutive-step stability streak)

All three are diagnostics of the Taylor kernel's own critical
slowdown near sigma_eq -> 0. They are measurable and real
independent of J activity.

The test runs the sweep at six xi values spanning two decades of
coupling strength and extracts for each:

    hysteresis_area(xi)
    fold_width_80_20(xi)          (reinterpreted: transition width)
    lambda_c(xi)                  (from active-region sigmoid fit)
    stiffness_peak(xi)            (three-component diagnostic)

Hypothesis being probed:

  - H_PAPER_B_STIFFNESS_MANIFOLD (new): the stiffness manifold at
    lambda_c is detectable at every xi. If its location and
    magnitude are invariant across xi, the manifold is Taylor-
    kernel-origin, not J-mediated.

  - H_PAPER_B_FOLD_BIFURCATION (existing, evidence 0): NOT emitted
    from this test. Direction stays 0 (no posterior move). The
    J-mediated saddle-node claim cannot be tested until the
    Psi_bruce definition question is resolved.

  - H_PAPER_B_1_PHI_SIGMOID, H_PAPER_B_COLD_TORUS_ABSORBING: both
    receive per-xi evidence emissions as in 5_12 / 5_14. The
    underlying phenomena are xi-independent and should validate
    consistently across the sweep.

--------------------------------------------------------------------
PREDICTIONS (FALSIFIABLE AT RUN TIME)
--------------------------------------------------------------------
  - All six xi values produce numerically near-identical Phi
    sweeps (confirming the 5_14 audit on more data points).

  - lambda_c(xi), fold_width_80_20(xi), and hysteresis_area(xi)
    are flat (within sweep-numerics noise) across xi.

  - stiffness_peak components (runtime, |grad J^2|, convergence
    delay) are also flat across xi -- the stiffness manifold is
    xi-independent, Taylor-kernel-origin.

  - If any metric shows non-trivial xi-dependence, the Psi_bruce
    coupling is doing something the 5_14 audit missed. That is a
    valuable positive finding and should be flagged for Foreman
    and Gemini review.
"""

import glob
import json
import os
import sys
import time
from datetime import datetime

import numpy as np

try:
    from scipy.ndimage import gaussian_filter, uniform_filter
    HAVE_SCIPY_NDIMAGE = True
except ImportError:
    HAVE_SCIPY_NDIMAGE = False

try:
    from scipy.optimize import curve_fit
    HAVE_SCIPY_OPT = True
except ImportError:
    HAVE_SCIPY_OPT = False


# =====================================================================
# CONFIGURATION
# =====================================================================

# Six-value xi sweep (Foreman-specified)
XI_VALUES = [0.005, 0.010, 0.015, 0.020, 0.035, 0.070]

CFG = {
    # PDE (frozen from 5_10 / 5_11 / 5_12 / 5_14)
    "dt": 0.05,
    "D_diffusion": 0.5,
    "alpha_regularization": 0.8,
    "ham_s_coeff_a": 0.12,
    "ham_s_coeff_b": 0.12,

    # xi gets set per-iteration from XI_VALUES (placeholder only)
    "xi_coupling": 0.015,

    "psi_bruce_window_radius": 6,
    "psi_bruce_smooth_sigma": 2.0,

    "pump_A_amplitude": 0.5,
    "pump_ratio": 0.25,
    "pump_A_width": 4.0,
    "pump_B_width": 3.0,
    "pump_separation": 15.0,

    "grid_N": 128,
    "blob_sigma_width": 5.0,
    "blob_default_amplitude": 1.0,
    "blob_noise_level": 0.01,
    "noise_seed": 19800601,
    "measure_radius": 15,

    "retardation_enabled": False,

    "lambda_min": 0.001,
    "lambda_max": 0.30,
    "n_points": 30,
    "log_spaced": True,
    "lambda_reference": 1e-6,

    "l2_threshold": 1e-6,
    "consecutive_required": 20,
    "hard_cap_steps": 5000,

    "perturbation_amplitudes": [0.5, 2.0],
    "run_perturbation_axis": False,

    # Classifier (inherited)
    "cold_phi_low_frac": 0.01,
    "cold_stay_dead_steps": 2,
    "fold_half_width_factor": 1.0,

    # Legacy fold-gate thresholds (retained for per-xi classifier
    # output parity with 5_12 / 5_14; NOT used as PASS gates in 5_15)
    "basin_r2_threshold": 0.95,
    "fold_slowing_inline_threshold": 2.0,
    "fold_perturbation_mass_split": 0.20,
    "fold_perturbation_slowing": 2.0,
    "fold_hysteresis_detection_floor": 0.001,
    "fold_hysteresis_hemorrhage_line": 0.0045,
    "fold_hysteresis_target": 0.0012,
    "fold_phi_min_threshold": 0.85,
    "cold_torus_max_phi_in_range": 0.01,

    # 80-20 fold width thresholds (same as 5_14)
    "fold_width_high_frac": 0.9,
    "fold_width_low_frac": 0.1,
}


# =====================================================================
# KERNEL PRIMITIVES (identical to 5_14)
# =====================================================================

def make_laplacian(field):
    lap = np.zeros_like(field)
    lap[1:-1, 1:-1] = (
        field[:-2, 1:-1] + field[2:, 1:-1]
        + field[1:-1, :-2] + field[1:-1, 2:]
        - 4.0 * field[1:-1, 1:-1]
    )
    return lap


def make_gaussian_blob(N, sigma_width, amplitude, noise_level=0.0, seed=0):
    cx = cy = N // 2
    xs = np.arange(N)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    r2 = (X - cx) ** 2 + (Y - cy) ** 2
    blob = amplitude * np.exp(-r2 / (2.0 * sigma_width ** 2))
    if noise_level > 0.0:
        rng = np.random.default_rng(seed)
        noise = noise_level * rng.standard_normal(blob.shape)
        blob = blob + amplitude * noise
        blob = np.maximum(blob, 0.0)
    return blob


def make_pump_profile(N, center, width, amplitude):
    cx, cy = center
    xs = np.arange(N)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    r2 = (X - cx) ** 2 + (Y - cy) ** 2
    return amplitude * np.exp(-r2 / (2.0 * width ** 2))


def make_pump_A_B(cfg):
    N = cfg["grid_N"]
    cx = N // 2
    cy = N // 2
    half_sep = cfg["pump_separation"] / 2.0
    pump_A = make_pump_profile(
        N, (cx - half_sep, cy), cfg["pump_A_width"], cfg["pump_A_amplitude"]
    )
    pump_B = make_pump_profile(
        N, (cx + half_sep, cy), cfg["pump_B_width"],
        cfg["pump_A_amplitude"] * cfg["pump_ratio"],
    )
    return pump_A, pump_B


def measure_sigma_plateau(field, measure_radius):
    N = field.shape[0]
    cx = cy = N // 2
    xs = np.arange(N)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    r2 = (X - cx) ** 2 + (Y - cy) ** 2
    mask = r2 <= measure_radius ** 2
    return float(np.mean(field[mask]))


def measure_gradient_max(field):
    gx = np.zeros_like(field)
    gy = np.zeros_like(field)
    gx[1:-1, :] = 0.5 * (field[2:, :] - field[:-2, :])
    gy[:, 1:-1] = 0.5 * (field[:, 2:] - field[:, :-2])
    mag = np.sqrt(gx ** 2 + gy ** 2)
    return float(np.max(mag))


def measure_rms(field):
    return float(np.sqrt(np.mean(field ** 2)))


def settle_relative_l2(sigma, sigma_prev):
    diff_norm = np.sqrt(np.sum((sigma - sigma_prev) ** 2))
    base_norm = np.sqrt(np.sum(sigma_prev ** 2)) + 1e-30
    return float(diff_norm / base_norm)


# =====================================================================
# PSI_BRUCE, J (identical to 5_14)
# =====================================================================

def compute_psi_bruce(sigma, cfg):
    r = cfg["psi_bruce_window_radius"]
    ss = cfg["psi_bruce_smooth_sigma"]
    size = 2 * r + 1
    if HAVE_SCIPY_NDIMAGE:
        local_mean = uniform_filter(sigma, size=size, mode="nearest")
        fluct = sigma - local_mean
        local_var = uniform_filter(fluct ** 2, size=size, mode="nearest")
        local_rms = np.sqrt(np.maximum(local_var, 0.0))
        psi = gaussian_filter(local_rms, sigma=ss, mode="nearest")
    else:
        from scipy.signal import convolve2d
        kernel = np.ones((size, size)) / (size * size)
        local_mean = convolve2d(sigma, kernel, mode="same", boundary="symm")
        fluct = sigma - local_mean
        local_var = convolve2d(fluct ** 2, kernel, mode="same", boundary="symm")
        local_rms = np.sqrt(np.maximum(local_var, 0.0))
        gsize = int(round(6 * ss)) | 1
        xs = np.arange(gsize) - gsize // 2
        g1d = np.exp(-xs ** 2 / (2.0 * ss ** 2))
        g1d /= g1d.sum()
        gkernel = np.outer(g1d, g1d)
        psi = convolve2d(local_rms, gkernel, mode="same", boundary="symm")
    return psi


def compute_J_magnitude_squared(sigma, pump_A, pump_B, cfg):
    psi = compute_psi_bruce(sigma, cfg)
    P = pump_A * pump_B * psi
    gx = np.zeros_like(P)
    gy = np.zeros_like(P)
    gx[1:-1, :] = 0.5 * (P[2:, :] - P[:-2, :])
    gy[:, 1:-1] = 0.5 * (P[:, 2:] - P[:, :-2])
    return gx ** 2 + gy ** 2, psi


# =====================================================================
# NEW IN 5_15: spatial gradient norm of a scalar field
# =====================================================================

def spatial_gradient_norm_max(field):
    """Max magnitude of spatial gradient of a scalar field over grid.

    Computes |grad F| = sqrt((dF/dx)^2 + (dF/dy)^2) via centered
    differences and returns the max.
    """
    gx = np.zeros_like(field)
    gy = np.zeros_like(field)
    gx[1:-1, :] = 0.5 * (field[2:, :] - field[:-2, :])
    gy[:, 1:-1] = 0.5 * (field[:, 2:] - field[:, :-2])
    mag = np.sqrt(gx ** 2 + gy ** 2)
    return float(np.max(mag))


# =====================================================================
# PDE STEP (identical to 5_14)
# =====================================================================

def pde_step(sigma, sigma_prev, lam, pump_A, pump_B, cfg, coupling_on=True):
    dt = cfg["dt"]
    D = cfg["D_diffusion"]
    alpha = cfg["alpha_regularization"]
    a = cfg["ham_s_coeff_a"]
    b = cfg["ham_s_coeff_b"]
    xi = cfg["xi_coupling"]

    lap = make_laplacian(sigma)
    source = a * sigma - b * sigma ** 2
    decay = lam * sigma
    rhs = D * lap + source - decay

    if coupling_on:
        J2, _ = compute_J_magnitude_squared(sigma, pump_A, pump_B, cfg)
        rhs = rhs + xi * J2 * (1.0 - sigma)

    sigma_new = sigma + dt * rhs + alpha * (sigma - sigma_prev)
    sigma_new = np.maximum(sigma_new, 0.0)
    return sigma_new


# =====================================================================
# INSTRUMENTED SETTLEMENT (adds convergence-delay tracking)
# =====================================================================

def run_single_lambda(initial_sigma, lam, pump_A, pump_B, cfg, coupling_on=True):
    """Run a single-lambda settlement with stiffness instrumentation.

    Additional fields versus 5_14:
      n_steps_first_below_threshold: step index at which L^2 first
        crosses below l2_threshold (None if never reached).
      stable_count_resets: number of times the stability streak was
        reset to zero (indicates L^2 oscillating near threshold).
      convergence_delay: n_steps_final - n_steps_first_below_threshold
        (None if no crossing occurred).
      grad_j_squared_max: max(|grad |J|^2|) on the settled field
        (spatial structure of J^2, independent of magnitude).
    """
    sigma = initial_sigma.copy()
    sigma_prev = sigma.copy()
    stable_count = 0
    stable_count_resets = 0
    n_steps = 0
    l2_last = None
    converged = False
    n_steps_first_below = None

    for step in range(cfg["hard_cap_steps"]):
        sigma_new = pde_step(sigma, sigma_prev, lam, pump_A, pump_B, cfg, coupling_on)
        l2 = settle_relative_l2(sigma_new, sigma)
        l2_last = l2
        if l2 < cfg["l2_threshold"]:
            if n_steps_first_below is None:
                n_steps_first_below = step + 1
            stable_count += 1
            if stable_count >= cfg["consecutive_required"]:
                n_steps = step + 1
                converged = True
                sigma_prev = sigma
                sigma = sigma_new
                break
        else:
            if stable_count > 0:
                stable_count_resets += 1
            stable_count = 0
        sigma_prev = sigma
        sigma = sigma_new
        n_steps = step + 1

    if coupling_on:
        J2_final, psi_final = compute_J_magnitude_squared(sigma, pump_A, pump_B, cfg)
        j2_max = float(np.max(J2_final))
        j2_mean = float(np.mean(J2_final))
        psi_mean = float(np.mean(psi_final))
        grad_j2_max = spatial_gradient_norm_max(J2_final)
    else:
        j2_max = j2_mean = psi_mean = 0.0
        grad_j2_max = 0.0

    if n_steps_first_below is not None:
        convergence_delay = int(n_steps - n_steps_first_below)
    else:
        convergence_delay = None

    return {
        "lambda": float(lam),
        "sigma_final": sigma,
        "sigma_plateau": measure_sigma_plateau(sigma, cfg["measure_radius"]),
        "mass_final": float(np.sum(sigma)),
        "gradient_max": measure_gradient_max(sigma),
        "rms": measure_rms(sigma),
        "j_squared_max": j2_max,
        "j_squared_mean": j2_mean,
        "psi_bruce_mean": psi_mean,
        "grad_j_squared_max": grad_j2_max,
        "n_steps": int(n_steps),
        "n_steps_first_below_threshold": (
            int(n_steps_first_below) if n_steps_first_below is not None else None
        ),
        "stable_count_resets": int(stable_count_resets),
        "convergence_delay": convergence_delay,
        "converged": bool(converged),
        "l2_final": float(l2_last) if l2_last is not None else None,
    }


def log_spaced_lambdas(lam_min, lam_max, n):
    return np.exp(np.linspace(np.log(lam_min), np.log(lam_max), n))


def run_sweep(initial_sigma, lambdas, pump_A, pump_B, cfg, label=""):
    results = []
    sigma_state = initial_sigma.copy()
    for idx, lam in enumerate(lambdas):
        t0 = time.time()
        r = run_single_lambda(sigma_state, lam, pump_A, pump_B, cfg, coupling_on=True)
        r["elapsed_seconds"] = time.time() - t0
        r["sweep_idx"] = idx
        r["sweep_label"] = label
        sigma_state = r.pop("sigma_final")
        results.append(r)
    return results, sigma_state


def compute_phi_from_sweep(results, phi_reference):
    out = []
    for r in results:
        phi = r["mass_final"] / phi_reference if phi_reference > 0 else 0.0
        entry = dict(r)
        entry["phi_normalized"] = float(phi)
        out.append(entry)
    return out


def sigmoid_fn(lam, lam_c, k):
    z = k * (lam / max(lam_c, 1e-12) - 1.0)
    z = np.clip(z, -500.0, 500.0)
    return 1.0 / (1.0 + np.exp(z))


def fit_sigmoid_on_subset(lambdas, phis):
    if len(lambdas) < 4 or not HAVE_SCIPY_OPT:
        return {
            "success": False, "message": "scipy unavailable or too few points",
            "lambda_c": None, "k": None, "r_squared": None,
            "n_points": int(len(lambdas)),
        }
    try:
        popt, _ = curve_fit(
            sigmoid_fn, lambdas, phis,
            p0=[float(np.median(lambdas)), 20.0], maxfev=10000,
        )
        lam_c = float(popt[0])
        k = float(popt[1])
        phi_pred = sigmoid_fn(lambdas, lam_c, k)
        ss_res = float(np.sum((phis - phi_pred) ** 2))
        ss_tot = float(np.sum((phis - np.mean(phis)) ** 2)) + 1e-30
        r2 = 1.0 - ss_res / ss_tot
        return {
            "success": True, "message": "OK",
            "lambda_c": lam_c, "k": k, "r_squared": float(r2),
            "n_points": int(len(lambdas)),
        }
    except Exception as exc:
        return {
            "success": False, "message": f"fit failed: {exc}",
            "lambda_c": None, "k": None, "r_squared": None,
            "n_points": int(len(lambdas)),
        }


# =====================================================================
# 80-20 fold width (from 5_14)
# =====================================================================

def fold_width_80_20(forward_phi, cfg):
    lambdas = [r["lambda"] for r in forward_phi]
    phis = [r["phi_normalized"] for r in forward_phi]
    if not lambdas or not phis:
        return {"lambda_hi": None, "lambda_lo": None, "width": None,
                "max_phi": None}

    max_phi = max(phis)
    hi_thr = cfg["fold_width_high_frac"] * max_phi
    lo_thr = cfg["fold_width_low_frac"] * max_phi

    def first_crossing(threshold):
        for i in range(len(phis)):
            if phis[i] < threshold:
                if i == 0:
                    return float(lambdas[i])
                p_prev, p_here = phis[i - 1], phis[i]
                l_prev, l_here = lambdas[i - 1], lambdas[i]
                if p_prev <= threshold:
                    return float(l_here)
                denom = (p_prev - p_here)
                if abs(denom) < 1e-30:
                    return float(l_here)
                frac = (p_prev - threshold) / denom
                return float(l_prev + frac * (l_here - l_prev))
        return None

    lam_hi = first_crossing(hi_thr)
    lam_lo = first_crossing(lo_thr)

    if lam_hi is None or lam_lo is None or lam_lo <= lam_hi:
        return {
            "lambda_hi": lam_hi, "lambda_lo": lam_lo, "width": None,
            "max_phi": float(max_phi),
            "high_frac": cfg["fold_width_high_frac"],
            "low_frac": cfg["fold_width_low_frac"],
        }
    return {
        "lambda_hi": lam_hi, "lambda_lo": lam_lo,
        "width": float(lam_lo - lam_hi),
        "max_phi": float(max_phi),
        "high_frac": cfg["fold_width_high_frac"],
        "low_frac": cfg["fold_width_low_frac"],
    }


# =====================================================================
# CLASSIFIER V2 (identical to 5_12 / 5_14)
# =====================================================================

def classify_regimes(forward_phi_results, cfg):
    lambdas = np.array([r["lambda"] for r in forward_phi_results])
    phis = np.array([r["phi_normalized"] for r in forward_phi_results])
    steps = np.array([r["n_steps"] for r in forward_phi_results])

    max_phi = float(np.max(phis)) if len(phis) > 0 else 0.0
    low_thr = cfg["cold_phi_low_frac"] * max_phi

    stay = cfg["cold_stay_dead_steps"]
    first_cold_idx = None
    for i in range(len(phis)):
        if phis[i] <= low_thr:
            still_dead = True
            for k in range(stay):
                j = i + k
                if j >= len(phis):
                    break
                if phis[j] > low_thr:
                    still_dead = False
                    break
            if still_dead:
                first_cold_idx = i
                break

    if first_cold_idx is not None:
        lambda_cold_entry = float(lambdas[first_cold_idx])
        active_indices = list(range(first_cold_idx))
    else:
        lambda_cold_entry = None
        active_indices = list(range(len(lambdas)))

    active_lam = lambdas[active_indices]
    active_phi = phis[active_indices]
    active_fit = fit_sigmoid_on_subset(active_lam, active_phi)
    lambda_c_sigmoid = active_fit.get("lambda_c")
    k_sigmoid = active_fit.get("k")

    labels = ["cold_torus"] * len(lambdas)
    lambda_fold_center = lambda_c_sigmoid
    lambda_fold_entry = None
    lambda_fold_exit = None

    if lambda_c_sigmoid is not None and k_sigmoid is not None and abs(k_sigmoid) > 1e-6:
        half_w = cfg["fold_half_width_factor"] / abs(k_sigmoid)
        fold_low = lambda_c_sigmoid - half_w
        fold_high = lambda_c_sigmoid + half_w
        for i in active_indices:
            if fold_low <= lambdas[i] <= fold_high:
                labels[i] = "fold_boundary"
            else:
                labels[i] = "sigmoid_basin"
        fold_active_idx = [i for i in active_indices if labels[i] == "fold_boundary"]
        if fold_active_idx:
            lambda_fold_entry = float(lambdas[fold_active_idx[0]])
            lambda_fold_exit = float(lambdas[fold_active_idx[-1]])
    else:
        for i in active_indices:
            labels[i] = "sigmoid_basin"

    third = max(1, len(active_indices) // 3)
    baseline_steps = float(np.median(steps[active_indices[:third]])) if third > 0 else 1.0

    fold_indices = [i for i, l in enumerate(labels) if l == "fold_boundary"]
    if fold_indices:
        max_fold_step = float(np.max(steps[fold_indices]))
    else:
        max_fold_step = baseline_steps
    inline_slowing_ratio = max_fold_step / max(baseline_steps, 1.0)

    return {
        "max_phi": max_phi,
        "cold_phi_threshold": float(low_thr),
        "baseline_n_steps": baseline_steps,
        "per_point_labels": labels,
        "regime_counts": {
            "sigmoid_basin": int(sum(1 for l in labels if l == "sigmoid_basin")),
            "fold_boundary": int(sum(1 for l in labels if l == "fold_boundary")),
            "cold_torus": int(sum(1 for l in labels if l == "cold_torus")),
        },
        "lambda_fold_entry": lambda_fold_entry,
        "lambda_fold_center": lambda_fold_center,
        "lambda_fold_exit": lambda_fold_exit,
        "lambda_cold_entry": lambda_cold_entry,
        "inline_slowing_ratio": float(inline_slowing_ratio),
        "active_region_sigmoid_fit": active_fit,
        "n_active_points": int(len(active_indices)),
    }


# =====================================================================
# HYSTERESIS (identical)
# =====================================================================

def hysteresis_area(forward_phi_list, forward_lambdas, return_phi_list, return_lambdas):
    fwd = sorted(zip(forward_lambdas, forward_phi_list))
    ret = sorted(zip(return_lambdas, return_phi_list))
    lam_arr = np.array([x[0] for x in fwd])
    fwd_arr = np.array([x[1] for x in fwd])
    ret_arr = np.array([x[1] for x in ret])
    diff = fwd_arr - ret_arr
    area = float(np.trapz(np.abs(diff), lam_arr))
    signed = float(np.trapz(diff, lam_arr))
    return {"area": area, "signed_area": signed}


def hysteresis_restricted(fwd_phi, ret_phi, lambda_upper):
    if lambda_upper is None:
        subset_fwd_l = [r["lambda"] for r in fwd_phi]
        subset_fwd_p = [r["phi_normalized"] for r in fwd_phi]
        subset_ret_l = [r["lambda"] for r in ret_phi]
        subset_ret_p = [r["phi_normalized"] for r in ret_phi]
    else:
        subset_fwd_l = [r["lambda"] for r in fwd_phi if r["lambda"] < lambda_upper]
        subset_fwd_p = [r["phi_normalized"] for r in fwd_phi if r["lambda"] < lambda_upper]
        subset_ret_l = [r["lambda"] for r in ret_phi if r["lambda"] < lambda_upper]
        subset_ret_p = [r["phi_normalized"] for r in ret_phi if r["lambda"] < lambda_upper]
    if len(subset_fwd_l) < 2 or len(subset_ret_l) < 2:
        return {"area": 0.0, "signed_area": 0.0, "n_lambdas": 0}
    h = hysteresis_area(subset_fwd_p, subset_fwd_l, subset_ret_p, subset_ret_l)
    h["n_lambdas"] = len(subset_fwd_l)
    return h


# =====================================================================
# STIFFNESS DIAGNOSTICS (new in 5_15)
# =====================================================================

def compute_stiffness_peak(forward_sweep, regime_info):
    """Three-component stiffness functional.

    Component 1: max(n_steps / baseline_steps) from classifier
        (inline_slowing_ratio). Captures runtime slowing.

    Component 2: max over sweep of grad_j_squared_max. Captures
        non-trivial spatial structure in |J|^2 independent of its
        magnitude. Floor-magnitude J^2 with uniform field gives ~0;
        floor-magnitude J^2 with sharp features gives finite value.

    Component 3: max over sweep of convergence_delay. Captures
        solver stall between first L^2 crossing and the 20-step
        confirmation streak. Large delay = oscillatory approach
        to equilibrium = delicate numerics.

    Also returns the lambdas where each component peaks, so the
    spatial co-location of the three diagnostics is visible.
    """
    if not forward_sweep:
        return {
            "inline_slowing_ratio": None,
            "max_grad_j_squared": None,
            "max_convergence_delay": None,
            "lambda_of_peak_slowing": None,
            "lambda_of_peak_grad_j2": None,
            "lambda_of_peak_delay": None,
        }

    # Component 1: runtime slowing (already computed in classifier)
    inline_slowing = regime_info.get("inline_slowing_ratio")
    baseline = regime_info.get("baseline_n_steps", 1.0)
    steps = [r["n_steps"] for r in forward_sweep]
    lambdas = [r["lambda"] for r in forward_sweep]
    max_step_idx = int(np.argmax(steps))
    lambda_slow_peak = float(lambdas[max_step_idx])

    # Component 2: max grad |J|^2 across sweep
    grads = [r.get("grad_j_squared_max", 0.0) for r in forward_sweep]
    max_grad_idx = int(np.argmax(grads))
    lambda_grad_peak = float(lambdas[max_grad_idx])

    # Component 3: max convergence delay across sweep
    delays = [
        r.get("convergence_delay") if r.get("convergence_delay") is not None else 0
        for r in forward_sweep
    ]
    max_delay_idx = int(np.argmax(delays))
    lambda_delay_peak = float(lambdas[max_delay_idx])

    return {
        "inline_slowing_ratio": float(inline_slowing) if inline_slowing is not None else None,
        "max_grad_j_squared": float(max(grads)) if grads else None,
        "max_convergence_delay": int(max(delays)) if delays else None,
        "baseline_n_steps": float(baseline),
        "lambda_of_peak_slowing": lambda_slow_peak,
        "lambda_of_peak_grad_j2": lambda_grad_peak,
        "lambda_of_peak_delay": lambda_delay_peak,
    }


# =====================================================================
# KERNEL VALIDATION (identical to 5_14, runs once with xi=0 coupling off)
# =====================================================================

def kernel_validation(cfg):
    N = cfg["grid_N"]
    a = cfg["ham_s_coeff_a"]
    b = cfg["ham_s_coeff_b"]
    validation_lambdas = [0.002, 0.02, 0.06, 0.10, 0.20]
    zero = np.zeros((N, N))
    blob = make_gaussian_blob(
        N, cfg["blob_sigma_width"], cfg["blob_default_amplitude"],
        noise_level=0.0, seed=cfg["noise_seed"],
    )
    comparisons = []
    max_dev = 0.0
    for lam in validation_lambdas:
        r = run_single_lambda(blob, lam, zero, zero, cfg, coupling_on=False)
        measured = r["sigma_plateau"]
        analytical = max(0.0, (a - lam) / b)
        dev = abs(measured - analytical)
        if dev > max_dev:
            max_dev = dev
        comparisons.append({
            "lambda": float(lam),
            "sigma_plateau_measured": float(measured),
            "sigma_plateau_analytical": float(analytical),
            "absolute_deviation": float(dev),
            "n_steps": int(r["n_steps"]),
            "converged": bool(r["converged"]),
        })
        r.pop("sigma_final", None)
    faithful = max_dev < 1e-3
    return {
        "validation_lambdas": validation_lambdas,
        "max_deviation": float(max_dev),
        "threshold": 1e-3,
        "faithful": bool(faithful),
        "per_lambda": comparisons,
    }


# =====================================================================
# PER-XI DRIVER
# =====================================================================

def run_single_xi(xi_value, base_cfg, kv_faithful):
    """Run reference + forward sweep + return sweep at a given xi.

    Returns a dict with the per-xi measurements needed for the
    xi-response table plus the full per-xi payload for the JSON.
    """
    cfg = dict(base_cfg)
    cfg["xi_coupling"] = float(xi_value)

    N = cfg["grid_N"]
    pump_A, pump_B = make_pump_A_B(cfg)
    blob = make_gaussian_blob(
        N, cfg["blob_sigma_width"], cfg["blob_default_amplitude"],
        cfg["blob_noise_level"], cfg["noise_seed"],
    )

    t0 = time.time()

    # Reference
    ref = run_single_lambda(
        blob, cfg["lambda_reference"], pump_A, pump_B, cfg, coupling_on=True
    )
    phi_reference_mass = ref["mass_final"]
    ref_sigma_state = ref.pop("sigma_final")

    # Forward sweep
    lambdas_fwd = log_spaced_lambdas(cfg["lambda_min"], cfg["lambda_max"], cfg["n_points"])
    fwd_raw, fwd_final_state = run_sweep(
        ref_sigma_state, lambdas_fwd, pump_A, pump_B, cfg, label="forward"
    )
    fwd_phi = compute_phi_from_sweep(fwd_raw, phi_reference_mass)

    # Classifier
    regime = classify_regimes(fwd_phi, cfg)

    # Return sweep
    lambdas_ret = lambdas_fwd[::-1].copy()
    ret_raw, _ = run_sweep(
        fwd_final_state, lambdas_ret, pump_A, pump_B, cfg, label="return"
    )
    ret_phi = compute_phi_from_sweep(ret_raw, phi_reference_mass)

    # Metrics
    hyst_active = hysteresis_restricted(
        fwd_phi, ret_phi, regime["lambda_cold_entry"]
    )
    width_info = fold_width_80_20(fwd_phi, cfg)
    stiffness = compute_stiffness_peak(fwd_phi, regime)

    fit = regime["active_region_sigmoid_fit"]
    lam_c = fit.get("lambda_c") if fit else None
    r2 = fit.get("r_squared") if fit else None
    basin_pass_gate = (r2 is not None and r2 >= cfg["basin_r2_threshold"])

    # Cold torus pass (same rule as 5_14)
    lam_cold = regime["lambda_cold_entry"]
    if lam_cold is not None:
        ret_in_cold = [r for r in ret_phi if r["lambda"] >= lam_cold]
        cold_max_phi = max((r["phi_normalized"] for r in ret_in_cold), default=0.0)
        cold_pass_gate = cold_max_phi <= cfg["cold_torus_max_phi_in_range"]
    else:
        cold_max_phi = None
        cold_pass_gate = False

    elapsed = time.time() - t0

    ref_entry = {
        "is_reference": True,
        "lambda": cfg["lambda_reference"],
        "mass_final": ref["mass_final"],
        "phi_normalized": 1.0,
        "n_steps": ref["n_steps"],
        "converged": ref["converged"],
        "sigma_plateau": ref["sigma_plateau"],
        "j_squared_max": ref["j_squared_max"],
        "j_squared_mean": ref["j_squared_mean"],
        "psi_bruce_mean": ref["psi_bruce_mean"],
        "grad_j_squared_max": ref["grad_j_squared_max"],
    }

    response_point = {
        "xi": float(xi_value),
        "lambda_c": lam_c,
        "sigmoid_r_squared": r2,
        "fold_width_80_20": width_info.get("width"),
        "hysteresis_restricted_area": hyst_active["area"],
        "stiffness_peak": stiffness,
        "basin_pass": bool(basin_pass_gate),
        "cold_torus_pass": bool(cold_pass_gate),
        "elapsed_seconds": float(elapsed),
    }

    payload = {
        "xi": float(xi_value),
        "elapsed_seconds": float(elapsed),
        "reference_run": ref_entry,
        "forward_sweep_results": [
            {**{k: v for k, v in r.items() if k != "sweep_idx"},
             "regime_label": regime["per_point_labels"][i]}
            for i, r in enumerate(fwd_phi)
        ],
        "return_sweep_results": [
            {k: v for k, v in r.items() if k != "sweep_idx"} for r in ret_phi
        ],
        "regime_classification": regime,
        "hysteresis_restricted": hyst_active,
        "fold_width_80_20": width_info,
        "stiffness_peak": stiffness,
        "basin_pass_gate": bool(basin_pass_gate),
        "cold_torus_pass_gate": bool(cold_pass_gate),
        "cold_max_phi_in_range": cold_max_phi,
    }

    return response_point, payload


# =====================================================================
# OUTPUT PATH
# =====================================================================

def resolve_output_path(filename):
    cwd_paper = os.path.join(os.getcwd(), "data", "paper_results")
    if os.path.isdir(cwd_paper):
        return os.path.join(cwd_paper, filename)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_paper = os.path.abspath(
        os.path.join(script_dir, "..", "..", "data", "paper_results")
    )
    if os.path.isdir(parent_paper):
        return os.path.join(parent_paper, filename)
    return os.path.join(script_dir, filename)


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 76)
    print("BCM v26 Paper B Probe Test 5_15 -- xi-Response + Stiffness Manifold")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC / GIBUSH Systems")
    print("=" * 76)
    print(f"xi values      = {XI_VALUES}")
    print(f"Sweep per xi   = [{CFG['lambda_min']}, {CFG['lambda_max']}], "
          f"{CFG['n_points']} log-spaced, dual, warm-start")
    print(f"Framing        = stiffness manifold detection (fold-bifurcation")
    print(f"                 reframed per 5_14 audit)")
    print(f"Stiffness diag = runtime slowing, grad(|J|^2) structure, "
          f"convergence delay")
    print()

    start_ts = datetime.now()
    start_wall = time.time()

    # --- Kernel validation (run once; xi-independent) ---
    print("Kernel validation (pumps OFF, non-degenerate lambdas)...")
    kv = kernel_validation(CFG)
    print(f"  max deviation = {kv['max_deviation']:.3e}  faithful = {kv['faithful']}")
    if not kv["faithful"]:
        print("  WARNING: validation failed. Measurements may be unreliable.")
    print()

    # --- Per-xi sweeps ---
    xi_payloads = {}
    response_curve = []
    for xi_idx, xi_value in enumerate(XI_VALUES):
        print(f"[{xi_idx + 1}/{len(XI_VALUES)}] xi = {xi_value} ...")
        point, payload = run_single_xi(xi_value, CFG, kv["faithful"])
        xi_payloads[f"xi_{xi_value}"] = payload
        response_curve.append(point)
        sp = point["stiffness_peak"]
        print(f"  lambda_c = {point['lambda_c']}  R^2 = {point['sigmoid_r_squared']}")
        print(f"  fold_width_80_20 = {point['fold_width_80_20']}")
        print(f"  hysteresis_restricted_area = {point['hysteresis_restricted_area']}")
        print(f"  stiffness: slow={sp['inline_slowing_ratio']}  "
              f"grad|J2|={sp['max_grad_j_squared']}  "
              f"delay={sp['max_convergence_delay']}")
        print(f"  basin_pass = {point['basin_pass']}  "
              f"cold_pass = {point['cold_torus_pass']}")
        print(f"  elapsed = {point['elapsed_seconds']:.1f} s")
        print()

    # --- Response-curve table ---
    print("=" * 76)
    print("XI RESPONSE CURVE")
    print("=" * 76)
    header = (f"{'xi':>7}  {'lambda_c':>9}  {'R^2':>7}  "
              f"{'fold_w80':>9}  {'H_area':>9}  "
              f"{'slow':>6}  {'|gJ2|':>10}  {'delay':>6}")
    print(header)
    print("-" * len(header))
    for pt in response_curve:
        sp = pt["stiffness_peak"]
        def fmt(v, spec):
            return format(v, spec) if v is not None else "    None"
        print(f"{pt['xi']:>7.4f}  "
              f"{fmt(pt['lambda_c'], '9.6f')}  "
              f"{fmt(pt['sigmoid_r_squared'], '7.4f')}  "
              f"{fmt(pt['fold_width_80_20'], '9.6f')}  "
              f"{fmt(pt['hysteresis_restricted_area'], '9.6f')}  "
              f"{fmt(sp['inline_slowing_ratio'], '6.3f')}  "
              f"{fmt(sp['max_grad_j_squared'], '10.3e')}  "
              f"{fmt(sp['max_convergence_delay'], '6d')}")
    print("=" * 76)
    print()

    # --- Variance diagnostic on the response curve ---
    def variance_stats(values):
        arr = np.array([v for v in values if v is not None], dtype=float)
        if len(arr) < 2:
            return {"n": len(arr), "min": None, "max": None, "range": None,
                    "relative_range": None, "mean": None}
        mn, mx = float(np.min(arr)), float(np.max(arr))
        mean = float(np.mean(arr))
        denom = abs(mean) if abs(mean) > 1e-30 else 1e-30
        return {
            "n": len(arr),
            "min": mn, "max": mx, "range": mx - mn,
            "relative_range": (mx - mn) / denom,
            "mean": mean,
        }

    variance = {
        "lambda_c": variance_stats([p["lambda_c"] for p in response_curve]),
        "fold_width_80_20": variance_stats([p["fold_width_80_20"] for p in response_curve]),
        "hysteresis_restricted_area": variance_stats([p["hysteresis_restricted_area"] for p in response_curve]),
        "sigmoid_r_squared": variance_stats([p["sigmoid_r_squared"] for p in response_curve]),
        "stiffness_inline_slowing_ratio": variance_stats(
            [p["stiffness_peak"]["inline_slowing_ratio"] for p in response_curve]
        ),
        "stiffness_max_grad_j_squared": variance_stats(
            [p["stiffness_peak"]["max_grad_j_squared"] for p in response_curve]
        ),
        "stiffness_max_convergence_delay": variance_stats(
            [p["stiffness_peak"]["max_convergence_delay"] for p in response_curve]
        ),
    }

    print("CROSS-XI VARIANCE (metric should be xi-invariant if coupling inactive)")
    print("-" * 76)
    for k, v in variance.items():
        if v.get("relative_range") is not None:
            print(f"  {k:<40} rel_range = {v['relative_range']:.3e}  "
                  f"(mean = {v['mean']:.6e})")
        else:
            print(f"  {k:<40} insufficient data")
    print()

    elapsed_total = time.time() - start_wall
    print(f"Total elapsed: {elapsed_total:.1f} s")
    print()

    # --- Stiffness manifold hypothesis evaluation ---
    # Stiffness manifold is "detected" if, at a given xi, all three
    # stiffness components are elevated versus the low-lambda baseline.
    # We encode a simple PASS condition: at xi = 0.035 (reference
    # point), stiffness_inline_slowing_ratio > 2.0 AND max_grad_j2
    # is finite (> 0) AND max_convergence_delay > consecutive_required.
    # This is PASS-only on one xi to avoid multiple emissions.
    stiffness_manifold_result = "INCONCLUSIVE"
    stiffness_manifold_reason = "Insufficient data for stiffness manifold evaluation."
    ref_point = next((p for p in response_curve if abs(p["xi"] - 0.035) < 1e-6), None)
    if ref_point is not None:
        sp = ref_point["stiffness_peak"]
        gate_slowing = (sp["inline_slowing_ratio"] is not None
                        and sp["inline_slowing_ratio"] > 2.0)
        gate_grad = (sp["max_grad_j_squared"] is not None
                     and sp["max_grad_j_squared"] > 0.0)
        gate_delay = (sp["max_convergence_delay"] is not None
                      and sp["max_convergence_delay"] > CFG["consecutive_required"])
        if gate_slowing and gate_grad and gate_delay:
            stiffness_manifold_result = "PASS"
            stiffness_manifold_reason = (
                f"Three-component stiffness peak detected at xi = "
                f"{ref_point['xi']}: slowing = {sp['inline_slowing_ratio']:.3f}, "
                f"grad|J^2| = {sp['max_grad_j_squared']:.3e}, "
                f"delay = {sp['max_convergence_delay']}"
            )
        else:
            stiffness_manifold_result = "INCONCLUSIVE"
            stiffness_manifold_reason = (
                f"Stiffness gates: slowing = {gate_slowing} "
                f"({sp['inline_slowing_ratio']}), grad|J^2| = {gate_grad} "
                f"({sp['max_grad_j_squared']}), delay = {gate_delay} "
                f"({sp['max_convergence_delay']})"
            )

    # --- Assemble JSON payload ---
    stamp = start_ts.strftime("%Y%m%d_%H%M%S")
    out_path = resolve_output_path(f"BCM_v26_Paper_B_Probes_5_15_{stamp}.json")

    hypotheses_tested = {
        "H_PAPER_B_STIFFNESS_MANIFOLD": {
            "statement": (
                "H-PaperB-Stiffness A stiffness manifold exists near "
                "lambda_c of the Phi-sigmoid transition, exhibiting "
                "elevated runtime slowing, non-trivial spatial "
                "structure in |J|^2 (even at floor magnitude), and "
                "solver convergence delay. Stiffness is measurable "
                "independent of J-coupling magnitude, originating in "
                "the Taylor kernel's own critical slowdown as "
                "sigma_eq = (a - lambda) / b collapses toward zero. "
                "This hypothesis replaces the earlier fold-"
                "bifurcation framing for Paper B Section 5 topology "
                "evidence, following the 5_14 audit finding that the "
                "sigma-J coupling term is numerically inactive under "
                "the current Psi_bruce definition."
            ),
            "result": stiffness_manifold_result,
            "evidence_type": "primary" if stiffness_manifold_result == "PASS" else "default",
            "pass_count": 1 if stiffness_manifold_result == "PASS" else 0,
            "total_configs": 1,
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "section_5_topology",
                "stiffness_manifold",
                "taylor_kernel_origin",
                "critical_slowing",
                "convergence_delay",
                "grad_j_squared_structure",
                "xi_response_surface",
                "classifier_v2",
                "section_7_2",
            ],
        },
        "H_PAPER_B_1_PHI_SIGMOID": {
            "statement": (
                "H-PaperB-1 Phi(lambda) sigmoid verified across the "
                "six-value xi response curve. Per-xi basin pass "
                "rate = "
                f"{sum(1 for p in response_curve if p['basin_pass'])}/"
                f"{len(response_curve)}."
            ),
            "result": (
                "PASS" if all(p["basin_pass"] for p in response_curve)
                else "INCONCLUSIVE"
            ),
            "evidence_type": (
                "primary" if all(p["basin_pass"] for p in response_curve)
                else "default"
            ),
            "pass_count": sum(1 for p in response_curve if p["basin_pass"]),
            "total_configs": len(response_curve),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "phi_sigmoid",
                "active_region_fit",
                "classifier_v2",
                "xi_response_surface",
                "xi_invariant",
                "section_3_evidence",
                "section_7_2",
            ],
        },
        "H_PAPER_B_COLD_TORUS_ABSORBING": {
            "statement": (
                "H-PaperB-Cold Cold-torus absorbing state verified "
                "across the six-value xi response curve. Per-xi cold "
                "pass rate = "
                f"{sum(1 for p in response_curve if p['cold_torus_pass'])}/"
                f"{len(response_curve)}."
            ),
            "result": (
                "PASS" if all(p["cold_torus_pass"] for p in response_curve)
                else "INCONCLUSIVE"
            ),
            "evidence_type": (
                "primary" if all(p["cold_torus_pass"] for p in response_curve)
                else "default"
            ),
            "pass_count": sum(1 for p in response_curve if p["cold_torus_pass"]),
            "total_configs": len(response_curve),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "cold_torus",
                "absorbing_state",
                "metastability",
                "xi_response_surface",
                "xi_invariant",
                "classifier_v2",
                "section_5_2_absorbing",
                "section_7_2",
            ],
        },
        # H_PAPER_B_FOLD_BIFURCATION intentionally NOT emitted in
        # 5_15. The 5_14 audit showed J-coupling is inactive under
        # the current Psi_bruce definition, so the J-mediated
        # saddle-node fold claim cannot be tested. The hypothesis
        # stays at posterior 0.500, evidence 0 in the cube until the
        # Psi_bruce definition is resolved by the Foreman / Gemini.
    }

    payload = {
        "test_name": "BCM_v26_Paper_B_Probes_5_15",
        "test_number": 5,
        "test_sub_number": 15,
        "test_version": 1,
        "timestamp": start_ts.isoformat(),
        "elapsed_seconds": elapsed_total,
        "paper_b_section": "7.2",
        "paper_b_probe": "xi-response curve + stiffness manifold",
        "test_role": "primary_measurement",
        "grid": f"{CFG['grid_N']}x{CFG['grid_N']}",
        "notes": (
            "Test 5_15 is the six-value xi response curve with "
            "stiffness-manifold diagnostics. It replaces the prior "
            "fold-bifurcation framing based on the 5_14 audit "
            "finding that xi has no numerical effect on the sweep "
            "(J is at floor magnitude under the current Psi_bruce "
            "definition). Stiffness is Taylor-kernel-origin, "
            "measurable, and load-bearing for Paper B Section 5 "
            "topology evidence. Per-xi metrics: lambda_c, fold_"
            "width_80_20, hysteresis_restricted_area, plus the "
            "three-component stiffness peak (runtime slowing, "
            "grad|J|^2 structure, convergence delay)."
        ),
        "xi_values": XI_VALUES,
        "config_snapshot": {
            "dt": CFG["dt"],
            "D_diffusion": CFG["D_diffusion"],
            "alpha_regularization": CFG["alpha_regularization"],
            "ham_s_coeff_a": CFG["ham_s_coeff_a"],
            "ham_s_coeff_b": CFG["ham_s_coeff_b"],
            "psi_bruce_window_radius": CFG["psi_bruce_window_radius"],
            "psi_bruce_smooth_sigma": CFG["psi_bruce_smooth_sigma"],
            "pump_A_amplitude": CFG["pump_A_amplitude"],
            "pump_ratio": CFG["pump_ratio"],
            "pump_A_width": CFG["pump_A_width"],
            "pump_B_width": CFG["pump_B_width"],
            "pump_separation": CFG["pump_separation"],
            "grid_N": CFG["grid_N"],
            "blob_sigma_width": CFG["blob_sigma_width"],
            "blob_default_amplitude": CFG["blob_default_amplitude"],
            "blob_noise_level": CFG["blob_noise_level"],
            "noise_seed": CFG["noise_seed"],
            "measure_radius": CFG["measure_radius"],
            "retardation_enabled": CFG["retardation_enabled"],
            "lambda_min": CFG["lambda_min"],
            "lambda_max": CFG["lambda_max"],
            "n_points": CFG["n_points"],
            "log_spaced": CFG["log_spaced"],
            "lambda_reference": CFG["lambda_reference"],
            "l2_threshold": CFG["l2_threshold"],
            "consecutive_required": CFG["consecutive_required"],
            "hard_cap_steps": CFG["hard_cap_steps"],
            "cold_phi_low_frac": CFG["cold_phi_low_frac"],
            "cold_stay_dead_steps": CFG["cold_stay_dead_steps"],
            "fold_half_width_factor": CFG["fold_half_width_factor"],
            "basin_r2_threshold": CFG["basin_r2_threshold"],
            "cold_torus_max_phi_in_range": CFG["cold_torus_max_phi_in_range"],
            "fold_width_high_frac": CFG["fold_width_high_frac"],
            "fold_width_low_frac": CFG["fold_width_low_frac"],
        },
        "kernel_validation": kv,
        "xi_response_curve": response_curve,
        "xi_cross_variance": variance,
        "per_xi_payload": xi_payloads,
        "stiffness_manifold_evaluation": {
            "result": stiffness_manifold_result,
            "reason": stiffness_manifold_reason,
            "reference_xi": 0.035,
        },
        "hypotheses_tested": hypotheses_tested,
        "scope": (
            "Test 5_15 is the six-value xi response curve + "
            "stiffness manifold probe. All physics primitives are "
            "identical to 5_12 / 5_14; only xi varies across six "
            "values. Stiffness diagnostics (runtime slowing, "
            "grad|J|^2 spatial structure, convergence delay) are "
            "added as three-component functional. The fold-"
            "bifurcation hypothesis is NOT emitted from this test "
            "due to the 5_14 audit (J inactive under current "
            "Psi_bruce). The Psi_bruce definition is a theoretical "
            "question reserved for the Foreman and Gemini."
        ),
        "audit_reference": (
            "5_14 audit: G(xi=0.015) / G(xi=0.035) = 1.0000 "
            "numerically exact across the full forward sweep. "
            "J^2 magnitudes at floor (1e-25 to 1e-18 peak). "
            "Coupling term xi * |J|^2 * (1-sigma) below machine-"
            "epsilon relative to Taylor kernel terms. Conclusion: "
            "fold-like signatures in 5_10 through 5_14 are Taylor-"
            "kernel transition + alpha-regularization memory, not "
            "J-mediated saddle-node bifurcations."
        ),
        "keywords": [
            "paper_b",
            "section_7_2",
            "xi_response_surface",
            "xi_response_curve",
            "stiffness_manifold",
            "stiffness_functional",
            "taylor_kernel_origin",
            "convergence_delay",
            "grad_j_squared",
            "fold_width_80_20",
            "classifier_v2",
            "active_region_fit",
            "sigmoid_inflection",
            "cold_torus",
            "absorbing_state",
            "audit_5_14",
            "psi_bruce_formulation",
            "coupling_inactive",
        ],
        "cube_coordinates": {
            "L": "L4_Operational",
            "OD": "OF_Flight_Operations",
            "cube": "Cube_7_Spectral_Fold",
        },
        "primacy_statement": (
            "All theoretical concepts, the Anchor Equation, the "
            "stiffness-manifold reframing of Paper B Section 5 "
            "topology evidence, the three-component stiffness "
            "functional (runtime slowing, grad|J|^2 spatial "
            "structure, solver convergence delay), the six-value "
            "xi response curve design, the Hemorrhage Line "
            "threshold, the chi_freeboard_mean target, and every "
            "originating insight belong solely to Stephen Justin "
            "Burdick Sr. AI systems were used strictly as "
            "computational processing tools at the direction of "
            "the Foreman. Emerald Entities LLC -- GIBUSH Systems."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"JSON written: {out_path}")


if __name__ == "__main__":
    main()
