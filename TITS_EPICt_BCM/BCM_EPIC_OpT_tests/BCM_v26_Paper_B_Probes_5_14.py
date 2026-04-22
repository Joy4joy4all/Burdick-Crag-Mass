# -*- coding: utf-8 -*-
"""
BCM v26 Paper B Probe Test 5_14
Paper B Section 7.2 -- xi = 0.015 Under-Coupled Control + G(xi) Diagnostic

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-04-22

--------------------------------------------------------------------
PRIMACY STATEMENT
--------------------------------------------------------------------
All theoretical concepts, the Anchor Equation, the xi-hysteresis
response-surface strategy, the G(xi) = H_basin(xi) / fold_width(xi)
response-density metric, the xi = 0.015 under-coupled control
point, the identification of the three dynamical regimes
(sigmoid basin, fold boundary, cold torus), the classifier-v2
architecture (sigmoid-inflection fold center, active-region
basin fit), the Hemorrhage Line hysteresis threshold, the
chi_freeboard_mean target, the Phi_min bridge stability
criterion, and every originating insight in this file belong
solely to Stephen Justin Burdick Sr. AI systems were used
strictly as computational processing tools and code executors at
the direction of the Foreman. No AI system contributed
theoretical concepts. Emerald Entities LLC -- GIBUSH Systems.

--------------------------------------------------------------------
SCOPE
--------------------------------------------------------------------
Test 5_14 is the second data point on the H(xi) response surface
for Paper B Section 7.2 fold evidence. The Foreman-directed plan
runs three xi values:

    5_12  xi = 0.035  (primary / mid)           H area ~ 0.050
    5_14  xi = 0.015  (under-coupled control)   THIS FILE
    5_15  xi = 0.070  (upper-envelope control)  reserved

Physics is identical to 5_12 except for the single xi coefficient.
Same PDE, same pumps (locked to 5_7), same sweep range [0.001,
0.30] log-spaced 30 points, same classifier v2 (sigmoid-
inflection fold center, active-region basin fit), same six gates
per regime with identical thresholds. Hysteresis safety gate,
detection floor, and Hemorrhage Line are NOT relaxed.

New diagnostic added in 5_14:

  G(xi) = H_basin(xi) / fold_width_80_20(xi)

fold_width_80_20 is the data-grounded lambda span between
Phi = 0.9 * max_phi and Phi = 0.1 * max_phi on the forward sweep
(linear interpolation between bracketing points). This avoids
the classifier's k-dependent fold width, which breaks down when
k is small and 1/k exceeds the sweep range -- a condition that
afflicted 5_12's classifier outputs (basin_count = 0,
fold_count = 25, meaning the half-width window engulfed the
entire active region). 80-20 width is always well-defined
wherever Phi crosses the thresholds, regardless of k.

The 5_14 JSON additionally locates the latest 5_12 output in
data/paper_results/ and back-computes G(0.035) from it, so the
output file carries two points on the H(xi) curve side-by-side.
If 5_12 JSON is absent, reference comparison is skipped.

--------------------------------------------------------------------
PREDICTIONS (FALSIFIABLE AT RUN TIME)
--------------------------------------------------------------------
  - Hysteresis area drops from 0.050 (5_12 xi=0.035) to somewhere
    in [0.001, 0.020]. If it lands in the safe band [0.001,
    0.0045] AND perturbation confirms bifurcation, this is the
    first cube-evidence PASS for H_PAPER_B_FOLD_BIFURCATION.

  - G(0.015) lower than G(0.035) = 0.55 under the standard
    expectation that weaker coupling produces both smaller
    hysteresis and broader fold transition. If G stays flat or
    rises, memory is concentrating into a narrower fold even as
    coupling weakens -- an anomaly worth flagging.

  - Basin sigmoid R^2 stays >= 0.99. Taylor kernel unchanged.

  - Cold torus PASS continues (absorbing-state behavior is
    xi-independent in principle once the field is zero).

If hysteresis drops below detection floor (area < 0.001),
xi = 0.015 is effectively sigmoid-only at this coupling. That
is a valid data point, not a failure -- it establishes the
lower bound of xi for fold emergence.
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
# CONFIGURATION (5_12 frozen; xi lowered)
# =====================================================================

CFG = {
    # PDE (frozen from 5_10/5_11/5_12)
    "dt": 0.05,
    "D_diffusion": 0.5,
    "alpha_regularization": 0.8,
    "ham_s_coeff_a": 0.12,
    "ham_s_coeff_b": 0.12,

    # CHANGED in 5_14: xi = 0.015 (under-coupled control)
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

    # Classifier (inherited from 5_12)
    "cold_phi_low_frac": 0.01,
    "cold_stay_dead_steps": 2,
    "fold_half_width_factor": 1.0,

    # Gate thresholds (inherited from 5_12; NOT relaxed)
    "basin_r2_threshold": 0.95,
    "fold_slowing_inline_threshold": 2.0,
    "fold_perturbation_mass_split": 0.20,
    "fold_perturbation_slowing": 2.0,
    "fold_hysteresis_detection_floor": 0.001,
    "fold_hysteresis_hemorrhage_line": 0.0045,
    "fold_hysteresis_target": 0.0012,
    "fold_phi_min_threshold": 0.85,
    "cold_torus_max_phi_in_range": 0.01,

    # NEW in 5_14: 80-20 fold width thresholds for G(xi) denominator
    "fold_width_high_frac": 0.9,
    "fold_width_low_frac": 0.1,

    # Reference search for G comparison
    "reference_json_pattern": "BCM_v26_Paper_B_Probes_5_12_*.json",
}


# =====================================================================
# KERNEL PRIMITIVES (identical to 5_12)
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
# PSI_BRUCE, J (identical to 5_12)
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
# PDE STEP (identical to 5_12)
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


def run_single_lambda(initial_sigma, lam, pump_A, pump_B, cfg, coupling_on=True):
    sigma = initial_sigma.copy()
    sigma_prev = sigma.copy()
    stable_count = 0
    n_steps = 0
    l2_last = None
    converged = False

    for step in range(cfg["hard_cap_steps"]):
        sigma_new = pde_step(sigma, sigma_prev, lam, pump_A, pump_B, cfg, coupling_on)
        l2 = settle_relative_l2(sigma_new, sigma)
        l2_last = l2
        if l2 < cfg["l2_threshold"]:
            stable_count += 1
            if stable_count >= cfg["consecutive_required"]:
                n_steps = step + 1
                converged = True
                sigma_prev = sigma
                sigma = sigma_new
                break
        else:
            stable_count = 0
        sigma_prev = sigma
        sigma = sigma_new
        n_steps = step + 1

    if coupling_on:
        J2_final, psi_final = compute_J_magnitude_squared(sigma, pump_A, pump_B, cfg)
        j2_max = float(np.max(J2_final))
        j2_mean = float(np.mean(J2_final))
        psi_mean = float(np.mean(psi_final))
    else:
        j2_max = j2_mean = psi_mean = 0.0

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
        "n_steps": int(n_steps),
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
            "success": False,
            "message": "scipy unavailable or too few points",
            "lambda_c": None,
            "k": None,
            "r_squared": None,
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
            "success": True,
            "message": "OK",
            "lambda_c": lam_c,
            "k": k,
            "r_squared": float(r2),
            "n_points": int(len(lambdas)),
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"fit failed: {exc}",
            "lambda_c": None,
            "k": None,
            "r_squared": None,
            "n_points": int(len(lambdas)),
        }


# =====================================================================
# NEW IN 5_14: 80-20 fold width (data-grounded, k-independent)
# =====================================================================

def fold_width_80_20(forward_phi, cfg):
    """Lambda span between Phi = 0.9*max_phi and Phi = 0.1*max_phi.

    Linear interpolation between bracketing sweep points. Returns
    (lambda_hi, lambda_lo, width) where lambda_hi < lambda_lo (since
    Phi decreases with lambda); width = lambda_lo - lambda_hi.

    Returns None for any component that can't be bracketed.
    """
    lambdas = [r["lambda"] for r in forward_phi]
    phis = [r["phi_normalized"] for r in forward_phi]
    if not lambdas or not phis:
        return {"lambda_hi": None, "lambda_lo": None, "width": None,
                "max_phi": None}

    max_phi = max(phis)
    hi_thr = cfg["fold_width_high_frac"] * max_phi
    lo_thr = cfg["fold_width_low_frac"] * max_phi

    def first_crossing(threshold):
        """First lambda where Phi drops strictly below threshold,
        linearly interpolated between bracketing points."""
        for i in range(len(phis)):
            if phis[i] < threshold:
                if i == 0:
                    return float(lambdas[i])
                p_prev, p_here = phis[i - 1], phis[i]
                l_prev, l_here = lambdas[i - 1], lambdas[i]
                if p_prev <= threshold:
                    return float(l_here)  # already below
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
            "lambda_hi": lam_hi,
            "lambda_lo": lam_lo,
            "width": None,
            "max_phi": float(max_phi),
            "high_frac": cfg["fold_width_high_frac"],
            "low_frac": cfg["fold_width_low_frac"],
        }

    return {
        "lambda_hi": lam_hi,
        "lambda_lo": lam_lo,
        "width": float(lam_lo - lam_hi),
        "max_phi": float(max_phi),
        "high_frac": cfg["fold_width_high_frac"],
        "low_frac": cfg["fold_width_low_frac"],
    }


# =====================================================================
# REGIME CLASSIFIER (identical to 5_12)
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
        "fold_half_width_lambda": (
            float(cfg["fold_half_width_factor"] / abs(k_sigmoid))
            if (k_sigmoid is not None and abs(k_sigmoid) > 1e-6) else None
        ),
    }


# =====================================================================
# HYSTERESIS (identical to 5_12)
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
    return {
        "area": area,
        "signed_area": signed,
        "per_lambda": [
            {"lambda": float(l), "phi_fwd": float(f), "phi_ret": float(r),
             "diff": float(f - r)}
            for l, f, r in zip(lam_arr, fwd_arr, ret_arr)
        ],
    }


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


def hysteresis_density(area, lambda_low, lambda_high):
    span = max(lambda_high - lambda_low, 1e-12)
    return float(area / span)


def phi_at_lambda(sweep_with_phi, target_lambda):
    if target_lambda is None:
        return None
    lambdas = np.array([r["lambda"] for r in sweep_with_phi])
    phis = np.array([r["phi_normalized"] for r in sweep_with_phi])
    idx = int(np.argmin(np.abs(lambdas - target_lambda)))
    return float(phis[idx])


# =====================================================================
# PERTURBATION AXIS (identical to 5_12)
# =====================================================================

def perturbation_at_fold_center(lambda_fold_center, pump_A, pump_B, cfg):
    if lambda_fold_center is None:
        return {
            "lambda_tested": None,
            "reason": "No fold center (sigmoid fit did not succeed)",
            "bifurcation_signature": False,
            "mass_split_fraction": None,
            "slowing_ratio": None,
            "perturbation_runs": [],
        }

    N = cfg["grid_N"]
    baseline_ic = make_gaussian_blob(
        N, cfg["blob_sigma_width"], cfg["blob_default_amplitude"],
        cfg["blob_noise_level"], cfg["noise_seed"],
    )
    baseline = run_single_lambda(
        baseline_ic, lambda_fold_center, pump_A, pump_B, cfg
    )

    runs = []
    for amp in cfg["perturbation_amplitudes"]:
        ic = make_gaussian_blob(
            N, cfg["blob_sigma_width"], amp,
            cfg["blob_noise_level"],
            cfg["noise_seed"] + int(amp * 1000),
        )
        t0 = time.time()
        r = run_single_lambda(ic, lambda_fold_center, pump_A, pump_B, cfg)
        r["blob_amplitude"] = float(amp)
        r["elapsed"] = time.time() - t0
        r.pop("sigma_final", None)
        runs.append(r)

    masses = [baseline["mass_final"]] + [r["mass_final"] for r in runs]
    mean_mass = float(np.mean(masses))
    mass_split = (max(masses) - min(masses)) / max(abs(mean_mass), 1e-30)

    baseline_steps = baseline["n_steps"]
    slowing_ratio = max(r["n_steps"] for r in runs) / max(baseline_steps, 1)

    diff_attr = bool(mass_split > cfg["fold_perturbation_mass_split"])
    crit_slow = bool(slowing_ratio > cfg["fold_perturbation_slowing"])
    bifurcation = diff_attr or crit_slow

    baseline.pop("sigma_final", None)

    return {
        "lambda_tested": float(lambda_fold_center),
        "baseline_mass": float(baseline["mass_final"]),
        "baseline_steps": int(baseline_steps),
        "perturbation_runs": [
            {
                "blob_amplitude": r["blob_amplitude"],
                "lambda": r["lambda"],
                "mass_final": r["mass_final"],
                "sigma_plateau": r["sigma_plateau"],
                "j_squared_max": r["j_squared_max"],
                "n_steps": r["n_steps"],
                "converged": r["converged"],
                "elapsed": r["elapsed"],
            }
            for r in runs
        ],
        "mass_split_fraction": float(mass_split),
        "slowing_ratio": float(slowing_ratio),
        "different_attractors": diff_attr,
        "critical_slowing": crit_slow,
        "bifurcation_signature": bifurcation,
    }


# =====================================================================
# REGIME-SPECIFIC EVALUATION (identical structure to 5_12;
# G(xi) diagnostic added to fold evaluation)
# =====================================================================

def evaluate_basin(regime_info, cfg):
    fit = regime_info["active_region_sigmoid_fit"]
    if not fit.get("success"):
        return {
            "result": "INCONCLUSIVE",
            "reason": f"Active-region sigmoid fit failed: {fit.get('message')}",
            "paper_b_section_3_evidence": False,
            "sigmoid_fit": fit,
            "n_active_points": regime_info["n_active_points"],
        }

    r2 = fit["r_squared"]
    passes = r2 is not None and r2 >= cfg["basin_r2_threshold"]

    return {
        "result": "PASS" if passes else "INCONCLUSIVE",
        "reason": (
            f"Active-region sigmoid R^2 = {r2:.6f}, threshold "
            f"{cfg['basin_r2_threshold']}. n_active = "
            f"{regime_info['n_active_points']}."
        ),
        "paper_b_section_3_evidence": bool(passes),
        "sigmoid_fit": fit,
        "n_active_points": regime_info["n_active_points"],
    }


def evaluate_fold(forward_phi, return_phi, regime_info, pump_A, pump_B, cfg):
    fold_count = regime_info["regime_counts"]["fold_boundary"]
    lam_fc = regime_info["lambda_fold_center"]

    if fold_count < 1 or lam_fc is None:
        return {
            "result": "INCONCLUSIVE",
            "reason": "No fold boundary detected or sigmoid fit failed",
            "paper_b_section_5_evidence": False,
        }

    inline_slow = regime_info["inline_slowing_ratio"]
    gate_inline_slowing = inline_slow >= cfg["fold_slowing_inline_threshold"]

    hyst_full = hysteresis_area(
        [r["phi_normalized"] for r in forward_phi],
        [r["lambda"] for r in forward_phi],
        [r["phi_normalized"] for r in return_phi],
        [r["lambda"] for r in return_phi],
    )
    hyst_active = hysteresis_restricted(
        forward_phi, return_phi, regime_info["lambda_cold_entry"]
    )
    lam_low = min(r["lambda"] for r in forward_phi)
    lam_high = regime_info["lambda_cold_entry"] if regime_info["lambda_cold_entry"] is not None else max(r["lambda"] for r in forward_phi)
    hyst_density_val = hysteresis_density(hyst_active["area"], lam_low, lam_high)

    # NEW in 5_14: 80-20 fold width + G(xi)
    width_info = fold_width_80_20(forward_phi, cfg)
    fold_w = width_info.get("width")
    if fold_w is not None and fold_w > 0:
        g_xi = float(hyst_active["area"] / fold_w)
    else:
        g_xi = None

    area = hyst_full["area"]
    gate_hyst_detected = area > cfg["fold_hysteresis_detection_floor"]
    gate_hyst_safe = area < cfg["fold_hysteresis_hemorrhage_line"]
    gate_hyst_at_target = area <= cfg["fold_hysteresis_target"]

    pert = perturbation_at_fold_center(lam_fc, pump_A, pump_B, cfg)
    gate_perturbation = pert["bifurcation_signature"]

    phi_fwd_fc = phi_at_lambda(forward_phi, lam_fc)
    phi_ret_fc = phi_at_lambda(return_phi, lam_fc)
    phi_min = (
        min(phi_fwd_fc, phi_ret_fc)
        if phi_fwd_fc is not None and phi_ret_fc is not None
        else None
    )
    gate_phi_min = (
        phi_min is not None and phi_min >= cfg["fold_phi_min_threshold"]
    )

    core_inline_pass = gate_inline_slowing and gate_hyst_detected
    if core_inline_pass and gate_hyst_safe and gate_perturbation:
        result = "PASS"
    elif core_inline_pass and gate_perturbation and not gate_hyst_safe:
        result = "PARTIAL_EXCESS_HYSTERESIS"
    elif core_inline_pass and gate_hyst_safe and not gate_perturbation:
        result = "PARTIAL_NO_PERTURBATION"
    else:
        result = "INCONCLUSIVE"

    reasons = []
    if not gate_inline_slowing:
        reasons.append(
            f"inline slowing {inline_slow:.3f} < {cfg['fold_slowing_inline_threshold']}"
        )
    if not gate_hyst_detected:
        reasons.append(
            f"hysteresis area {area:.6f} < detection floor "
            f"{cfg['fold_hysteresis_detection_floor']}"
        )
    if not gate_hyst_safe:
        reasons.append(
            f"hysteresis area {area:.6f} >= Hemorrhage Line "
            f"{cfg['fold_hysteresis_hemorrhage_line']} (excess memory)"
        )
    if not gate_perturbation:
        reasons.append(
            f"perturbation axis did not confirm "
            f"(mass_split={pert.get('mass_split_fraction')}, "
            f"slowing={pert.get('slowing_ratio')})"
        )
    reason = "; ".join(reasons) if reasons else "All fold gates pass."

    return {
        "result": result,
        "reason": reason,
        "paper_b_section_5_evidence": (result == "PASS"),
        "inline_slowing_ratio": float(inline_slow),
        "inline_slowing_gate": bool(gate_inline_slowing),
        "hysteresis_full_area": float(hyst_full["area"]),
        "hysteresis_full_signed_area": float(hyst_full["signed_area"]),
        "hysteresis_restricted_area": float(hyst_active["area"]),
        "hysteresis_restricted_n_lambdas": int(hyst_active.get("n_lambdas", 0)),
        "hysteresis_density": float(hyst_density_val),
        "fold_width_80_20": width_info,
        "G_xi": g_xi,
        "hysteresis_detected": bool(gate_hyst_detected),
        "hysteresis_safe": bool(gate_hyst_safe),
        "hysteresis_at_target": bool(gate_hyst_at_target),
        "hysteresis_per_lambda": hyst_full["per_lambda"],
        "perturbation": pert,
        "perturbation_bifurcation_gate": bool(gate_perturbation),
        "phi_fwd_at_fold_center": phi_fwd_fc,
        "phi_ret_at_fold_center": phi_ret_fc,
        "phi_min_at_fold_center": phi_min,
        "phi_min_gate_informational": bool(gate_phi_min),
    }


def evaluate_cold_torus(forward_phi, return_phi, regime_info, cfg):
    cold_count = regime_info["regime_counts"]["cold_torus"]
    lam_cold = regime_info["lambda_cold_entry"]
    lam_fold_entry = regime_info["lambda_fold_entry"]

    if cold_count < 1 or lam_cold is None:
        return {
            "result": "INCONCLUSIVE",
            "reason": "No cold torus region detected on forward sweep",
            "paper_b_section_5_absorbing_evidence": False,
        }

    ret_in_cold = [r for r in return_phi if r["lambda"] >= lam_cold]
    cold_max_phi = (
        max((r["phi_normalized"] for r in ret_in_cold), default=0.0)
    )
    cold_stays_dead = cold_max_phi <= cfg["cold_torus_max_phi_in_range"]

    recovery_lambda = None
    if lam_fold_entry is not None:
        ret_sorted_desc = sorted(return_phi, key=lambda r: -r["lambda"])
        for r in ret_sorted_desc:
            if r["lambda"] < lam_fold_entry and r["phi_normalized"] > cfg["cold_torus_max_phi_in_range"]:
                recovery_lambda = float(r["lambda"])
                break

    recovery_correct_side = (
        recovery_lambda is None or
        (lam_fold_entry is not None and recovery_lambda < lam_fold_entry)
    )

    passes = cold_stays_dead and recovery_correct_side

    return {
        "result": "PASS" if passes else "INCONCLUSIVE",
        "reason": (
            f"cold_stays_dead={cold_stays_dead} (max Phi in cold="
            f"{cold_max_phi:.6f}, thr={cfg['cold_torus_max_phi_in_range']}); "
            f"recovery_lambda={recovery_lambda}, fold_entry={lam_fold_entry}"
        ),
        "paper_b_section_5_absorbing_evidence": bool(passes),
        "cold_max_phi_in_range": float(cold_max_phi),
        "cold_stays_dead": bool(cold_stays_dead),
        "recovery_lambda": recovery_lambda,
        "recovery_below_fold_entry": bool(recovery_correct_side),
    }


# =====================================================================
# KERNEL VALIDATION (identical to 5_12)
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
        "description": (
            "Pumps-OFF Taylor-equilibrium validation at non-degenerate "
            "lambdas (lambda = a = 0.12 excluded; settlement artifact)."
        ),
        "validation_lambdas": validation_lambdas,
        "max_deviation": float(max_dev),
        "threshold": 1e-3,
        "faithful": bool(faithful),
        "per_lambda": comparisons,
    }


# =====================================================================
# NEW IN 5_14: Reference comparison against 5_12 output
# =====================================================================

def find_reference_json(cfg):
    """Locate most recent 5_12 output for G(xi) comparison."""
    search_dirs = [
        os.path.join(os.getcwd(), "data", "paper_results"),
        os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "data", "paper_results"
        )),
    ]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        matches = glob.glob(os.path.join(d, cfg["reference_json_pattern"]))
        if matches:
            matches.sort(key=os.path.getmtime, reverse=True)
            return matches[0]
    return None


def load_reference_metrics(ref_path):
    """Extract G(xi), hysteresis, and fold width from a source JSON.

    Works on 5_12 outputs; falls back gracefully if fields are absent.
    """
    try:
        with open(ref_path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as exc:
        return {"available": False, "reason": f"load failed: {exc}"}

    pde = d.get("pde_spec", {})
    xi = pde.get("xi_coupling")
    fold = d.get("fold_evaluation", {})
    hyst_active_area = fold.get("hysteresis_restricted_area")

    # If the reference JSON doesn't have 80-20 fold width (5_12 doesn't),
    # compute it from the forward sweep.
    width_info = fold.get("fold_width_80_20")
    if width_info is None:
        fwd = d.get("forward_sweep_results") or d.get("sweep_results") or []
        if fwd:
            cfg_stub = {
                "fold_width_high_frac": 0.9,
                "fold_width_low_frac": 0.1,
            }
            width_info = fold_width_80_20(fwd, cfg_stub)

    fold_w = width_info.get("width") if width_info else None
    g_ref = None
    if hyst_active_area is not None and fold_w is not None and fold_w > 0:
        g_ref = float(hyst_active_area / fold_w)

    return {
        "available": True,
        "reference_path": ref_path,
        "reference_test": d.get("test_name"),
        "reference_timestamp": d.get("timestamp"),
        "xi": xi,
        "hysteresis_restricted_area": hyst_active_area,
        "fold_width_80_20": width_info,
        "G_xi": g_ref,
    }


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
    print("=" * 68)
    print("BCM v26 Paper B Probe Test 5_14 -- xi = 0.015 Under-Coupled")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC / GIBUSH Systems")
    print("=" * 68)
    print(f"xi coupling    = {CFG['xi_coupling']} (under-coupled; reference 0.035 at 5_12)")
    print(f"Sweep          = [{CFG['lambda_min']}, {CFG['lambda_max']}], "
          f"{CFG['n_points']} log-spaced, dual, warm-start")
    print(f"Classifier v2  + 80-20 fold width + G(xi) diagnostic")
    print()

    start_ts = datetime.now()
    start_wall = time.time()

    print("Kernel validation (pumps OFF, non-degenerate lambdas)...")
    kv = kernel_validation(CFG)
    print(f"  max deviation = {kv['max_deviation']:.3e}  faithful = {kv['faithful']}")
    if not kv["faithful"]:
        print("  WARNING: validation failed. Measurements below may be unreliable.")
    print()

    N = CFG["grid_N"]
    pump_A, pump_B = make_pump_A_B(CFG)
    blob = make_gaussian_blob(
        N, CFG["blob_sigma_width"], CFG["blob_default_amplitude"],
        CFG["blob_noise_level"], CFG["noise_seed"],
    )

    print(f"Reference run at lambda = {CFG['lambda_reference']:g}...")
    t0 = time.time()
    ref = run_single_lambda(
        blob, CFG["lambda_reference"], pump_A, pump_B, CFG, coupling_on=True
    )
    ref["elapsed_seconds"] = time.time() - t0
    phi_reference_mass = ref["mass_final"]
    ref_sigma_state = ref.pop("sigma_final")
    print(f"  mass_final = {ref['mass_final']:.6f}  n_steps = {ref['n_steps']}")
    print()

    lambdas_fwd = log_spaced_lambdas(CFG["lambda_min"], CFG["lambda_max"], CFG["n_points"])
    print(f"Forward sweep ({len(lambdas_fwd)} points)...")
    fwd_raw, fwd_final_state = run_sweep(
        ref_sigma_state, lambdas_fwd, pump_A, pump_B, CFG, label="forward"
    )
    fwd_phi = compute_phi_from_sweep(fwd_raw, phi_reference_mass)

    print()
    print("Regime classification (v2)...")
    regime = classify_regimes(fwd_phi, CFG)
    for i, r in enumerate(fwd_phi):
        lbl = regime["per_point_labels"][i]
        print(f"  lam={r['lambda']:.5f}  phi={r['phi_normalized']:.6f}  "
              f"steps={r['n_steps']:5d}  J2={r['j_squared_max']:.2e}  ->  {lbl}")
    print()
    fit = regime["active_region_sigmoid_fit"]
    print(f"Active-region sigmoid fit (n={regime['n_active_points']}):")
    if fit.get("success"):
        print(f"  lambda_c = {fit['lambda_c']:.6f}  k = {fit['k']:.4f}  "
              f"R^2 = {fit['r_squared']:.6f}")
    else:
        print(f"  FAILED: {fit.get('message')}")
    print(f"lambda_fold_center = {regime['lambda_fold_center']}")
    print(f"lambda_cold_entry  = {regime['lambda_cold_entry']}")
    print()

    lambdas_ret = lambdas_fwd[::-1].copy()
    print(f"Return sweep ({len(lambdas_ret)} points, warm-start)...")
    ret_raw, _ = run_sweep(
        fwd_final_state, lambdas_ret, pump_A, pump_B, CFG, label="return"
    )
    ret_phi = compute_phi_from_sweep(ret_raw, phi_reference_mass)
    for r in ret_phi:
        print(f"  lam={r['lambda']:.5f}  phi={r['phi_normalized']:.6f}  "
              f"steps={r['n_steps']}")
    print()

    print("Regime-specific evaluation + G(xi) diagnostic...")
    basin_eval = evaluate_basin(regime, CFG)
    fold_eval = evaluate_fold(fwd_phi, ret_phi, regime, pump_A, pump_B, CFG)
    cold_eval = evaluate_cold_torus(fwd_phi, ret_phi, regime, CFG)

    # Reference comparison (5_12 xi=0.035)
    ref_path = find_reference_json(CFG)
    if ref_path:
        ref_metrics = load_reference_metrics(ref_path)
    else:
        ref_metrics = {"available": False, "reason": "No 5_12 JSON found in data/paper_results/"}

    print("-" * 68)
    print(f"BASIN  (Paper B Section 3): {basin_eval['result']}")
    print(f"  {basin_eval['reason']}")
    print(f"FOLD   (Paper B Section 5 topology): {fold_eval['result']}")
    print(f"  inline slowing ratio = {fold_eval['inline_slowing_ratio']:.3f}  "
          f"gate={fold_eval['inline_slowing_gate']}")
    print(f"  hysteresis full area       = {fold_eval['hysteresis_full_area']:.6f}")
    print(f"  hysteresis restricted area = {fold_eval['hysteresis_restricted_area']:.6f}")
    print(f"  hysteresis density         = {fold_eval['hysteresis_density']:.6f}")
    print(f"  80-20 fold width           = {fold_eval['fold_width_80_20'].get('width')}")
    print(f"  G(xi = {CFG['xi_coupling']})           = {fold_eval['G_xi']}")
    print(f"  hyst detected={fold_eval['hysteresis_detected']}  "
          f"safe={fold_eval['hysteresis_safe']}  "
          f"at_target={fold_eval['hysteresis_at_target']}")
    if fold_eval["perturbation"]["lambda_tested"] is not None:
        p = fold_eval["perturbation"]
        print(f"  perturbation at fold_center = {p['lambda_tested']:.5f}: "
              f"mass_split={p['mass_split_fraction']:.4f}  "
              f"slowing={p['slowing_ratio']:.3f}  "
              f"bifurcation={p['bifurcation_signature']}")
    print(f"  {fold_eval['reason']}")
    print(f"COLD   (Paper B Section 5 absorbing): {cold_eval['result']}")
    print(f"  {cold_eval['reason']}")
    print("-" * 68)
    if ref_metrics.get("available"):
        print(f"REFERENCE (5_12, xi = {ref_metrics['xi']}):")
        print(f"  hysteresis_restricted_area = {ref_metrics['hysteresis_restricted_area']}")
        ri = ref_metrics['fold_width_80_20'] or {}
        print(f"  80-20 fold width           = {ri.get('width')}")
        print(f"  G(xi = {ref_metrics['xi']})          = {ref_metrics['G_xi']}")
        this_g = fold_eval.get("G_xi")
        ref_g = ref_metrics.get("G_xi")
        if this_g is not None and ref_g is not None:
            if ref_g > 1e-12:
                ratio = this_g / ref_g
                print(f"  G(xi=0.015) / G(xi=0.035)  = {ratio:.4f}")
    else:
        print(f"REFERENCE: not available ({ref_metrics.get('reason')})")
    print("-" * 68)

    elapsed = time.time() - start_wall

    stamp = start_ts.strftime("%Y%m%d_%H%M%S")
    out_path = resolve_output_path(f"BCM_v26_Paper_B_Probes_5_14_{stamp}.json")

    basin_pass = basin_eval.get("paper_b_section_3_evidence", False)
    fold_pass = fold_eval.get("paper_b_section_5_evidence", False)
    cold_pass = cold_eval.get("paper_b_section_5_absorbing_evidence", False)
    loop_pass_count = sum(1 for r in fwd_phi + ret_phi if r["converged"])

    hypotheses_tested = {
        "H_PAPER_B_1_PHI_SIGMOID": {
            "statement": (
                "H-PaperB-1 Phi(lambda) sigmoid validated via active-"
                "region fit at xi = 0.015 (under-coupled control)."
            ),
            "result": basin_eval["result"],
            "evidence_type": "primary" if basin_pass else "default",
            "pass_count": regime["n_active_points"],
            "total_configs": int(CFG["n_points"]),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "phi_sigmoid",
                "active_region_fit",
                "classifier_v2",
                "xi_under_coupled",
                "xi_response_surface",
                "section_3_evidence",
                "section_7_2",
            ],
        },
        "H_PAPER_B_2_J_VORTICITY": {
            "statement": (
                "H-PaperB-2 J as active dynamical driver at xi = 0.015 "
                "under-coupled regime. Evidence strength tracks fold "
                "evaluation."
            ),
            "result": "PASS" if fold_pass else "INCONCLUSIVE",
            "evidence_type": "primary" if fold_pass else "secondary",
            "pass_count": int(CFG["n_points"]),
            "total_configs": int(CFG["n_points"]),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "j_vorticity",
                "sigma_j_coupling",
                "xi_under_coupled",
                "xi_response_surface",
                "classifier_v2",
                "section_7_2",
            ],
        },
        "H_PAPER_B_3_LOOP_CONVERGES": {
            "statement": (
                "H-PaperB-3 Loop convergence at xi = 0.015 dual sweep."
            ),
            "result": "PASS" if loop_pass_count == 2 * CFG["n_points"] else "INCONCLUSIVE",
            "evidence_type": "secondary",
            "pass_count": int(loop_pass_count),
            "total_configs": int(2 * CFG["n_points"]),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "loop_convergence",
                "dual_sweep",
                "xi_response_surface",
                "section_7_2",
            ],
        },
        "H_PAPER_B_FOLD_BIFURCATION": {
            "statement": (
                "H-PaperB-Fold Saddle-node fold bifurcation at "
                "xi = 0.015 (under-coupled control). Gates: inline "
                "slowing, hysteresis detected within safe band "
                "[detection_floor, Hemorrhage_Line), perturbation-"
                "axis bifurcation signature at sigmoid inflection. "
                "Second data point on the H(xi) response surface."
            ),
            "result": fold_eval["result"],
            "evidence_type": "primary" if fold_pass else "secondary",
            "pass_count": regime["regime_counts"]["fold_boundary"],
            "total_configs": int(CFG["n_points"]),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "fold_bifurcation",
                "saddle_node",
                "sigmoid_inflection",
                "critical_slowing",
                "hysteresis",
                "hysteresis_density",
                "fold_width_80_20",
                "G_xi_response_metric",
                "xi_under_coupled",
                "xi_response_surface",
                "classifier_v2",
                "section_5_topology",
                "section_7_2",
            ],
        },
        "H_PAPER_B_COLD_TORUS_ABSORBING": {
            "statement": (
                "H-PaperB-Cold Cold torus absorbing state at xi = "
                "0.015. Return sweep stays dead in cold region; "
                "recovery only below lambda_fold_entry."
            ),
            "result": cold_eval["result"],
            "evidence_type": "primary" if cold_pass else "secondary",
            "pass_count": regime["regime_counts"]["cold_torus"],
            "total_configs": int(CFG["n_points"]),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "cold_torus",
                "absorbing_state",
                "metastability",
                "xi_response_surface",
                "classifier_v2",
                "section_5_2_absorbing",
                "section_7_2",
            ],
        },
    }

    payload = {
        "test_name": "BCM_v26_Paper_B_Probes_5_14",
        "test_number": 5,
        "test_sub_number": 14,
        "test_version": 1,
        "timestamp": start_ts.isoformat(),
        "elapsed_seconds": elapsed,
        "paper_b_section": "7.2",
        "paper_b_probe": "xi = 0.015 under-coupled control + G(xi) diagnostic",
        "test_role": "primary_measurement",
        "grid": f"{CFG['grid_N']}x{CFG['grid_N']}",
        "notes": (
            "Test 5_14 is the under-coupled data point (xi = 0.015) "
            "on the H(xi) response surface. Physics is identical to "
            "5_12 except for xi. Classifier v2 from 5_12 reused. "
            "Gates NOT relaxed. New diagnostics: 80-20 fold width "
            "(data-grounded, k-independent) and G(xi) = H_basin / "
            "fold_width_80_20 response-density metric."
        ),
        "pde_spec": {
            "dt": CFG["dt"],
            "D_diffusion": CFG["D_diffusion"],
            "alpha_regularization": CFG["alpha_regularization"],
            "ham_s_form": "a*sigma - b*sigma^2 + xi*|J|^2*(1 - sigma)",
            "ham_s_coeff_a": CFG["ham_s_coeff_a"],
            "ham_s_coeff_b": CFG["ham_s_coeff_b"],
            "xi_coupling": CFG["xi_coupling"],
            "psi_bruce_window_radius": CFG["psi_bruce_window_radius"],
            "psi_bruce_smooth_sigma": CFG["psi_bruce_smooth_sigma"],
            "retardation_enabled": CFG["retardation_enabled"],
            "blob_sigma_width": CFG["blob_sigma_width"],
            "blob_default_amplitude": CFG["blob_default_amplitude"],
            "blob_noise_level": CFG["blob_noise_level"],
            "noise_seed": CFG["noise_seed"],
            "measure_radius": CFG["measure_radius"],
        },
        "pump_spec": {
            "pump_A_amplitude": CFG["pump_A_amplitude"],
            "pump_B_amplitude": CFG["pump_A_amplitude"] * CFG["pump_ratio"],
            "pump_ratio": CFG["pump_ratio"],
            "pump_A_width": CFG["pump_A_width"],
            "pump_B_width": CFG["pump_B_width"],
            "pump_separation": CFG["pump_separation"],
            "locked_to_test": "5_7",
        },
        "sweep_spec": {
            "lambda_min": CFG["lambda_min"],
            "lambda_max": CFG["lambda_max"],
            "n_points": CFG["n_points"],
            "log_spaced": CFG["log_spaced"],
            "lambda_reference": CFG["lambda_reference"],
            "dual_sweep": True,
            "warm_start": True,
        },
        "settlement_spec": {
            "l2_threshold": CFG["l2_threshold"],
            "consecutive_required": CFG["consecutive_required"],
            "hard_cap_steps": CFG["hard_cap_steps"],
        },
        "classifier_spec": {
            "version": "v2_5_12",
            "cold_phi_low_frac": CFG["cold_phi_low_frac"],
            "cold_stay_dead_steps": CFG["cold_stay_dead_steps"],
            "fold_half_width_factor": CFG["fold_half_width_factor"],
            "fold_center_definition": "sigmoid inflection (lambda_c from active-region fit)",
            "basin_fit_scope": "active_region (basin + fold, excluding cold_torus)",
            "fold_width_80_20_high_frac": CFG["fold_width_high_frac"],
            "fold_width_80_20_low_frac": CFG["fold_width_low_frac"],
        },
        "gate_spec_per_regime": {
            "basin_r2_threshold": CFG["basin_r2_threshold"],
            "fold_slowing_inline_threshold": CFG["fold_slowing_inline_threshold"],
            "fold_perturbation_mass_split": CFG["fold_perturbation_mass_split"],
            "fold_perturbation_slowing": CFG["fold_perturbation_slowing"],
            "fold_hysteresis_detection_floor": CFG["fold_hysteresis_detection_floor"],
            "fold_hysteresis_hemorrhage_line": CFG["fold_hysteresis_hemorrhage_line"],
            "fold_hysteresis_target": CFG["fold_hysteresis_target"],
            "fold_phi_min_threshold": CFG["fold_phi_min_threshold"],
            "cold_torus_max_phi_in_range": CFG["cold_torus_max_phi_in_range"],
        },
        "kernel_validation": kv,
        "reference_run": {
            "is_reference": True,
            "lambda": CFG["lambda_reference"],
            "mass_final": ref["mass_final"],
            "phi_normalized": 1.0,
            "n_steps": ref["n_steps"],
            "converged": ref["converged"],
            "sigma_plateau": ref["sigma_plateau"],
            "gradient_max": ref["gradient_max"],
            "rms": ref["rms"],
            "j_squared_max": ref["j_squared_max"],
            "j_squared_mean": ref["j_squared_mean"],
            "psi_bruce_mean": ref["psi_bruce_mean"],
            "elapsed_seconds": ref["elapsed_seconds"],
        },
        "forward_sweep_results": [
            {**{k: v for k, v in r.items() if k != "sweep_idx"},
             "regime_label": regime["per_point_labels"][i]}
            for i, r in enumerate(fwd_phi)
        ],
        "return_sweep_results": [
            {k: v for k, v in r.items() if k != "sweep_idx"} for r in ret_phi
        ],
        "sweep_results": [
            {k: v for k, v in r.items() if k != "sweep_idx"} for r in fwd_phi
        ],
        "regime_classification": regime,
        "basin_evaluation": basin_eval,
        "fold_evaluation": fold_eval,
        "cold_torus_evaluation": cold_eval,
        "xi_response_surface_point": {
            "xi": CFG["xi_coupling"],
            "hysteresis_restricted_area": fold_eval["hysteresis_restricted_area"],
            "fold_width_80_20": fold_eval["fold_width_80_20"],
            "G_xi": fold_eval["G_xi"],
            "reference_point": ref_metrics,
        },
        "overall_result": {
            "basin_pass": bool(basin_pass),
            "fold_pass": bool(fold_pass),
            "cold_pass": bool(cold_pass),
            "all_three_regimes_pass": bool(basin_pass and fold_pass and cold_pass),
            "fold_result_detail": fold_eval["result"],
        },
        "hypotheses_tested": hypotheses_tested,
        "scope": (
            "Test 5_14 is the xi = 0.015 under-coupled data point on "
            "the H(xi) response surface. Physics identical to 5_12 "
            "except xi. Classifier v2 from 5_12 reused. Gates "
            "unchanged and NOT relaxed. 80-20 fold width added as "
            "k-independent denominator for G(xi) response density "
            "metric. Reference comparison against 5_12 (xi = 0.035) "
            "included when available. Test 5_15 (xi = 0.07 upper "
            "envelope) reserved for the third data point."
        ),
        "next_test_reserved": {
            "5_15": "xi = 0.07 upper-envelope control (third H(xi) point)",
        },
        "keywords": [
            "paper_b",
            "section_7_2",
            "xi_response_surface",
            "xi_under_coupled",
            "G_xi_metric",
            "fold_width_80_20",
            "hysteresis_density",
            "classifier_v2",
            "active_region_fit",
            "sigmoid_inflection",
            "fold_bifurcation",
            "saddle_node",
            "cold_torus",
            "absorbing_state",
            "sigma_j_coupling",
            "topological_back_reaction",
            "hemorrhage_line",
            "chi_freeboard_mean",
            "dual_sweep",
        ],
        "cube_coordinates": {
            "L": "L4_Operational",
            "OD": "OF_Flight_Operations",
            "cube": "Cube_7_Spectral_Fold",
        },
        "primacy_statement": (
            "All theoretical concepts, the Anchor Equation, the "
            "xi-hysteresis response-surface strategy, the G(xi) = "
            "H_basin(xi) / fold_width(xi) response-density metric, "
            "the xi = 0.015 under-coupled control point, the three-"
            "regime classifier architecture, the Hemorrhage Line "
            "threshold, the chi_freeboard_mean target, the Phi_min "
            "bridge-stability criterion, and every originating "
            "insight belong solely to Stephen Justin Burdick Sr. AI "
            "systems were used strictly as computational processing "
            "tools at the direction of the Foreman. Emerald "
            "Entities LLC -- GIBUSH Systems."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"Overall: basin={basin_eval['result']}  fold={fold_eval['result']}  "
          f"cold={cold_eval['result']}")
    print(f"All three regimes pass: {payload['overall_result']['all_three_regimes_pass']}")
    print("-" * 68)
    print(f"JSON written: {out_path}")


if __name__ == "__main__":
    main()
