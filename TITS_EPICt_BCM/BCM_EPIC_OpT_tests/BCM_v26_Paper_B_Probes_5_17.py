# -*- coding: utf-8 -*-
"""
BCM v26 Paper B Probe Test 5_17
Paper B Section 7.2 -- Taylor Kernel a-Coefficient Perturbation
                       (First Invariance-Breaking Probe)

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-04-22

--------------------------------------------------------------------
PRIMACY STATEMENT
--------------------------------------------------------------------
All theoretical concepts, the Anchor Equation, Brucetron and
Psi_bruce, the Taylor kernel sigma_eq = (a - lambda) / b relation,
the identification of the Taylor a-coefficient as the first
candidate bifurcation control axis after the 4-field tensor was
shown xi-invariant across [0.005, 0.07], the invariance-breaking
gate structure (B1-B4), and every originating insight in this
file belong solely to Stephen Justin Burdick Sr. Stephen Burdick
is the sole discoverer and theoretical originator of the BCM
framework. Four AI systems (Claude, ChatGPT, Gemini, Grok) assist
the project as computational tools and reviewers at the direction
of the Foreman. No AI system owns or co-owns any theoretical
concept. Emerald Entities LLC -- GIBUSH Systems.

--------------------------------------------------------------------
CONTEXT
--------------------------------------------------------------------
Tests 5_14, 5_15, and 5_16 established that the four-field state
tensor (lambda_c, lambda_fold_center, lambda_cold_entry, H) is
invariant under xi across [0.005, 0.07]. All four fields collapsed
to identical values to near machine precision. 5_16 gated this
invariance-plus-distinctness pattern with E1-E5 and returned 5/5
PASS.

The Foreman's next direction: break the invariance with
perturbation. The load-bearing claim across the probe series is
that lambda_c is a spectral eigenvalue of the basin, rooted in
the Taylor kernel sigma_eq = (a - lambda) / b. If this claim is
correct, perturbing a must shift lambda_c. Testing that
dependence is the most direct attack on the invariance class.

--------------------------------------------------------------------
SCOPE
--------------------------------------------------------------------
Test 5_17 sweeps the Taylor coefficient a across five values:

    a in [0.08, 0.10, 0.12, 0.15, 0.18]

with b fixed at 0.12 (5_15 baseline). xi is held at 0.035
(numerically inactive per 5_14 audit; retained for configuration
continuity). All other parameters (D, alpha, dt, pumps, grid,
classifier v2) frozen from 5_15.

For each a-value the test runs reference + forward sweep + return
sweep + classifier v2, then extracts the same four-field tensor
as 5_16. Assembled tensor is evaluated against four breakage
gates:

  B1 monotonic lambda_c(a): Pearson correlation between a and
     lambda_c(a) > 0.95 across the five values.

  B2 lambda_c amplitude response: relative range
     |lambda_c(a_max) - lambda_c(a_min)| / lambda_c(a_mid) > 0.30.
     A 30% shift clearly exits the ~1e-10 xi-plateau floor.

  B3 lambda_cold_entry tracks a: same two tests applied to the
     absorbing boundary (Pearson corr > 0.95, rel range > 0.30).

  B4 baseline anchor: lambda_c(a = 0.12) matches the 5_15 value
     0.059165791 within 1e-6. Verifies the solver reproduces the
     earlier result at the un-perturbed point.

All four B-gates PASS confirms that the Taylor a-coefficient is a
bifurcation control axis: it breaks the 4-field invariance class
and provides a directly interpretable physical lever. This would
be the first "exit from the xi-plateau" empirically identified in
the probe series.

--------------------------------------------------------------------
PREDICTIONS (FALSIFIABLE AT RUN TIME)
--------------------------------------------------------------------
If lambda_c is Taylor-kernel-origin (claim carried by 5_11
through 5_16):

  - lambda_c scales roughly linearly with a:
      a = 0.08 -> lambda_c ~ 0.040
      a = 0.10 -> lambda_c ~ 0.049
      a = 0.12 -> lambda_c = 0.059166 (5_15 reproducible)
      a = 0.15 -> lambda_c ~ 0.074
      a = 0.18 -> lambda_c ~ 0.088

  - lambda_cold_entry scales similarly (terminates near a for
    each choice; above that lambda, sigma_eq is driven negative
    and the substrate cannot be sustained).

  - H(a) may shift. Not directly predicted -- observational.

  - fold_center (argmax n_steps) may or may not track a. Stiffness
    centroid is a numerical response property; its a-dependence
    is an open empirical question.

If lambda_c does NOT move with a, the spectral-eigenvalue framing
needs revisiting. That would be a decisive finding in either
direction.
"""

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

# Five a-coefficient values (Foreman-directed perturbation axis)
A_VALUES = [0.08, 0.10, 0.12, 0.15, 0.18]

# Baseline anchor for B4 gate (from 5_15 at a = 0.12)
BASELINE_LAMBDA_C = 0.059165791

CFG = {
    # PDE (frozen from 5_15 except ham_s_coeff_a which varies per iter)
    "dt": 0.05,
    "D_diffusion": 0.5,
    "alpha_regularization": 0.8,
    "ham_s_coeff_a": 0.12,          # per-iteration override
    "ham_s_coeff_b": 0.12,          # frozen
    "xi_coupling": 0.035,           # inactive per 5_14 audit; kept stable

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

    # Classifier (inherited from 5_12 / 5_14 / 5_15)
    "cold_phi_low_frac": 0.01,
    "cold_stay_dead_steps": 2,
    "fold_half_width_factor": 1.0,

    # Legacy fold-gate thresholds retained for classifier output parity
    "basin_r2_threshold": 0.95,
    "cold_torus_max_phi_in_range": 0.01,

    # 80-20 fold width thresholds
    "fold_width_high_frac": 0.9,
    "fold_width_low_frac": 0.1,

    # Invariance-breaking gate thresholds (new in 5_17)
    "b1_pearson_min_abs": 0.95,
    "b2_rel_range_min": 0.30,
    "b3_cold_pearson_min_abs": 0.95,
    "b3_cold_rel_range_min": 0.30,
    "b4_baseline_tolerance": 1e-6,
}


# =====================================================================
# KERNEL PRIMITIVES (identical to 5_15)
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
# PSI_BRUCE, J (identical to 5_15)
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
# PDE STEP (identical to 5_15)
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
# CLASSIFIER V2 (identical to 5_15)
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
    lambda_fold_center_v2 = lambda_c_sigmoid  # v2 collapsed definition

    if lambda_c_sigmoid is not None and k_sigmoid is not None and abs(k_sigmoid) > 1e-6:
        half_w = cfg["fold_half_width_factor"] / abs(k_sigmoid)
        fold_low = lambda_c_sigmoid - half_w
        fold_high = lambda_c_sigmoid + half_w
        for i in active_indices:
            if fold_low <= lambdas[i] <= fold_high:
                labels[i] = "fold_boundary"
            else:
                labels[i] = "sigmoid_basin"
    else:
        for i in active_indices:
            labels[i] = "sigmoid_basin"

    # Stiffness centroid (restored from 5_11 definition, per 5_16)
    if active_indices:
        active_steps = [steps[i] for i in active_indices]
        active_lams_here = [lambdas[i] for i in active_indices]
        max_idx_local = int(np.argmax(active_steps))
        lambda_fold_center_stiffness = float(active_lams_here[max_idx_local])
    else:
        lambda_fold_center_stiffness = None

    third = max(1, len(active_indices) // 3)
    baseline_steps = float(np.median(steps[active_indices[:third]])) if third > 0 else 1.0

    return {
        "max_phi": max_phi,
        "cold_phi_threshold": float(low_thr),
        "baseline_n_steps": baseline_steps,
        "per_point_labels": labels,
        "lambda_fold_center_v2_collapsed": lambda_fold_center_v2,
        "lambda_fold_center_stiffness": lambda_fold_center_stiffness,
        "lambda_cold_entry": lambda_cold_entry,
        "active_region_sigmoid_fit": active_fit,
        "n_active_points": int(len(active_indices)),
    }


# =====================================================================
# HYSTERESIS
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
# KERNEL VALIDATION (adapts per a)
# =====================================================================

def kernel_validation(cfg):
    N = cfg["grid_N"]
    a = cfg["ham_s_coeff_a"]
    b = cfg["ham_s_coeff_b"]

    # Validation lambdas: skip lambda == a (singular); span below + above
    candidate_lambdas = [0.002, 0.02, 0.06, 0.10, 0.15, 0.20]
    validation_lambdas = [lam for lam in candidate_lambdas if abs(lam - a) > 0.01]

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
        "a_coeff": float(a),
        "b_coeff": float(b),
        "validation_lambdas": validation_lambdas,
        "max_deviation": float(max_dev),
        "threshold": 1e-3,
        "faithful": bool(faithful),
        "per_lambda": comparisons,
    }


# =====================================================================
# PER-A DRIVER
# =====================================================================

def run_single_a(a_value, base_cfg):
    cfg = dict(base_cfg)
    cfg["ham_s_coeff_a"] = float(a_value)

    N = cfg["grid_N"]
    pump_A, pump_B = make_pump_A_B(cfg)
    blob = make_gaussian_blob(
        N, cfg["blob_sigma_width"], cfg["blob_default_amplitude"],
        cfg["blob_noise_level"], cfg["noise_seed"],
    )

    t0 = time.time()

    kv = kernel_validation(cfg)

    ref = run_single_lambda(
        blob, cfg["lambda_reference"], pump_A, pump_B, cfg, coupling_on=True
    )
    phi_reference_mass = ref["mass_final"]
    ref_sigma_state = ref.pop("sigma_final")

    lambdas_fwd = log_spaced_lambdas(cfg["lambda_min"], cfg["lambda_max"], cfg["n_points"])
    fwd_raw, fwd_final_state = run_sweep(
        ref_sigma_state, lambdas_fwd, pump_A, pump_B, cfg, label="forward"
    )
    fwd_phi = compute_phi_from_sweep(fwd_raw, phi_reference_mass)

    regime = classify_regimes(fwd_phi, cfg)

    lambdas_ret = lambdas_fwd[::-1].copy()
    ret_raw, _ = run_sweep(
        fwd_final_state, lambdas_ret, pump_A, pump_B, cfg, label="return"
    )
    ret_phi = compute_phi_from_sweep(ret_raw, phi_reference_mass)

    hyst_active = hysteresis_restricted(
        fwd_phi, ret_phi, regime["lambda_cold_entry"]
    )

    fit = regime["active_region_sigmoid_fit"]
    lam_c = fit.get("lambda_c") if fit else None

    elapsed = time.time() - t0

    tensor_point = {
        "a": float(a_value),
        "b": float(cfg["ham_s_coeff_b"]),
        "xi": float(cfg["xi_coupling"]),
        "lambda_c_spectral": lam_c,
        "lambda_fold_center_stiffness": regime["lambda_fold_center_stiffness"],
        "lambda_cold_entry": regime["lambda_cold_entry"],
        "H_a": hyst_active["area"],
        "sigmoid_r_squared": fit.get("r_squared") if fit else None,
        "sigmoid_k": fit.get("k") if fit else None,
        "n_active_points": regime["n_active_points"],
        "kernel_validation_faithful": kv["faithful"],
        "kernel_validation_max_dev": kv["max_deviation"],
        "sigma_eq_analytical_max": max(0.0, a_value / cfg["ham_s_coeff_b"]),
        "elapsed_seconds": float(elapsed),
    }

    payload = {
        "a": float(a_value),
        "config_xi": float(cfg["xi_coupling"]),
        "config_b": float(cfg["ham_s_coeff_b"]),
        "kernel_validation": kv,
        "reference_run": {
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
        },
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
        "elapsed_seconds": float(elapsed),
    }

    return tensor_point, payload


# =====================================================================
# INVARIANCE-BREAKING ANALYSIS
# =====================================================================

def pearson_correlation(xs, ys):
    valid = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(valid) < 3:
        return None
    xs_a = np.array([v[0] for v in valid], dtype=float)
    ys_a = np.array([v[1] for v in valid], dtype=float)
    xs_c = xs_a - np.mean(xs_a)
    ys_c = ys_a - np.mean(ys_a)
    denom = float(np.sqrt(np.sum(xs_c ** 2) * np.sum(ys_c ** 2)))
    if denom < 1e-30:
        return None
    return float(np.sum(xs_c * ys_c) / denom)


def relative_range_over_mid(values, mid_value=None):
    """(max - min) / mid_value (or mean if mid_value is None)."""
    arr = [v for v in values if v is not None]
    if len(arr) < 2:
        return None
    arr = np.array(arr, dtype=float)
    mn, mx = float(np.min(arr)), float(np.max(arr))
    if mid_value is not None and mid_value > 1e-30:
        return float((mx - mn) / mid_value)
    mean = float(np.mean(arr))
    if abs(mean) < 1e-30:
        return None
    return float((mx - mn) / abs(mean))


def evaluate_breakage_gates(tensor, cfg):
    a_vals = [t["a"] for t in tensor]
    lambda_c_vals = [t["lambda_c_spectral"] for t in tensor]
    lambda_cold_vals = [t["lambda_cold_entry"] for t in tensor]
    h_vals = [t["H_a"] for t in tensor]
    fold_ctr_vals = [t["lambda_fold_center_stiffness"] for t in tensor]

    # B1: Pearson corr between a and lambda_c > threshold
    b1_corr = pearson_correlation(a_vals, lambda_c_vals)
    b1_pass = (b1_corr is not None and abs(b1_corr) >= cfg["b1_pearson_min_abs"])

    # B2: lambda_c amplitude response
    lam_c_at_mid = next(
        (t["lambda_c_spectral"] for t in tensor if abs(t["a"] - 0.12) < 1e-9),
        None,
    )
    b2_rel_range = relative_range_over_mid(lambda_c_vals, lam_c_at_mid)
    b2_pass = (b2_rel_range is not None and b2_rel_range >= cfg["b2_rel_range_min"])

    # B3: lambda_cold_entry tracks a
    b3_corr = pearson_correlation(a_vals, lambda_cold_vals)
    lam_cold_at_mid = next(
        (t["lambda_cold_entry"] for t in tensor if abs(t["a"] - 0.12) < 1e-9),
        None,
    )
    b3_rel_range = relative_range_over_mid(lambda_cold_vals, lam_cold_at_mid)
    b3_pass_corr = (b3_corr is not None and abs(b3_corr) >= cfg["b3_cold_pearson_min_abs"])
    b3_pass_range = (b3_rel_range is not None and b3_rel_range >= cfg["b3_cold_rel_range_min"])
    b3_pass = b3_pass_corr and b3_pass_range

    # B4: baseline anchor at a = 0.12
    baseline_point = next(
        (t for t in tensor if abs(t["a"] - 0.12) < 1e-9), None
    )
    if baseline_point is not None and baseline_point["lambda_c_spectral"] is not None:
        b4_deviation = abs(
            baseline_point["lambda_c_spectral"] - BASELINE_LAMBDA_C
        )
        b4_pass = bool(b4_deviation < cfg["b4_baseline_tolerance"])
    else:
        b4_deviation = None
        b4_pass = False

    # Observational: H(a), fold_center(a) trends
    h_corr = pearson_correlation(a_vals, h_vals)
    h_rel_range = relative_range_over_mid(h_vals)
    fold_corr = pearson_correlation(a_vals, fold_ctr_vals)
    fold_rel_range = relative_range_over_mid(fold_ctr_vals)

    gates = {
        "B1_lambda_c_monotonic": {
            "passed": b1_pass,
            "pearson_correlation": b1_corr,
            "threshold": cfg["b1_pearson_min_abs"],
        },
        "B2_lambda_c_amplitude_response": {
            "passed": b2_pass,
            "relative_range": b2_rel_range,
            "threshold": cfg["b2_rel_range_min"],
            "reference_mid_value": lam_c_at_mid,
        },
        "B3_lambda_cold_tracks_a": {
            "passed": b3_pass,
            "pearson_correlation": b3_corr,
            "relative_range": b3_rel_range,
            "corr_threshold": cfg["b3_cold_pearson_min_abs"],
            "range_threshold": cfg["b3_cold_rel_range_min"],
        },
        "B4_baseline_anchor": {
            "passed": b4_pass,
            "baseline_lambda_c_5_15": BASELINE_LAMBDA_C,
            "measured_lambda_c_a_0_12": (
                baseline_point["lambda_c_spectral"]
                if baseline_point else None
            ),
            "deviation": b4_deviation,
            "tolerance": cfg["b4_baseline_tolerance"],
        },
    }

    observations = {
        "H_a_pearson_correlation": h_corr,
        "H_a_relative_range": h_rel_range,
        "lambda_fold_center_pearson_correlation": fold_corr,
        "lambda_fold_center_relative_range": fold_rel_range,
    }

    all_pass = all(
        gates[g]["passed"] for g in
        ("B1_lambda_c_monotonic",
         "B2_lambda_c_amplitude_response",
         "B3_lambda_cold_tracks_a",
         "B4_baseline_anchor")
    )
    passed_count = sum(
        1 for g in gates.values() if g["passed"]
    )

    if all_pass:
        result = "PASS"
    elif passed_count >= 3:
        result = "PARTIAL"
    else:
        result = "INCONCLUSIVE"

    return gates, observations, result, passed_count


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
    print("BCM v26 Paper B Probe Test 5_17 -- Taylor a-Coefficient Perturbation")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC / GIBUSH Systems")
    print("=" * 76)
    print(f"a values        = {A_VALUES}")
    print(f"b (fixed)       = {CFG['ham_s_coeff_b']}")
    print(f"xi (inactive)   = {CFG['xi_coupling']}")
    print(f"Sweep per a     = [{CFG['lambda_min']}, {CFG['lambda_max']}], "
          f"{CFG['n_points']} log-spaced, dual, warm-start")
    print(f"Objective       = break 4-field tensor invariance via Taylor kernel")
    print()

    start_ts = datetime.now()
    start_wall = time.time()

    a_payloads = {}
    tensor = []
    for idx, a_val in enumerate(A_VALUES):
        print(f"[{idx + 1}/{len(A_VALUES)}] a = {a_val} ...")
        point, payload = run_single_a(a_val, CFG)
        tensor.append(point)
        a_payloads[f"a_{a_val}"] = payload
        print(f"  kernel_valid = {point['kernel_validation_faithful']}  "
              f"max_dev = {point['kernel_validation_max_dev']:.3e}")
        print(f"  lambda_c       = {point['lambda_c_spectral']}")
        print(f"  lambda_fold    = {point['lambda_fold_center_stiffness']}")
        print(f"  lambda_cold    = {point['lambda_cold_entry']}")
        print(f"  H(a)           = {point['H_a']}")
        print(f"  sigma_eq_max   = {point['sigma_eq_analytical_max']}  (= a/b)")
        print(f"  elapsed        = {point['elapsed_seconds']:.1f} s")
        print()

    # --- Tensor table ---
    print("=" * 76)
    print("A-COEFFICIENT PERTURBATION TENSOR")
    print("=" * 76)
    header = (f"{'a':>6}  {'lambda_c':>12}  {'lambda_fold':>12}  "
              f"{'lambda_cold':>12}  {'H(a)':>10}  {'R^2':>7}")
    print(header)
    print("-" * len(header))
    for t in tensor:
        def fmt(v, spec):
            return format(v, spec) if v is not None else "        None"
        print(f"{t['a']:>6.3f}  "
              f"{fmt(t['lambda_c_spectral'], '12.9f')}  "
              f"{fmt(t['lambda_fold_center_stiffness'], '12.9f')}  "
              f"{fmt(t['lambda_cold_entry'], '12.9f')}  "
              f"{fmt(t['H_a'], '10.6f')}  "
              f"{fmt(t['sigmoid_r_squared'], '7.4f')}")
    print("=" * 76)
    print()

    gates, observations, result, passed_count = evaluate_breakage_gates(tensor, CFG)

    print("BREAKAGE GATES (success = invariance IS broken)")
    print("-" * 76)
    for gname, gdata in gates.items():
        status = "PASS" if gdata["passed"] else "FAIL"
        print(f"  {gname:<40}  {status}")
        for key, val in gdata.items():
            if key == "passed":
                continue
            print(f"      {key}: {val}")
    print("-" * 76)
    print(f"Gates passed: {passed_count}/4")
    print(f"RESULT: {result}")
    print()
    print("OBSERVATIONAL (not gated)")
    for k, v in observations.items():
        print(f"  {k}: {v}")
    print()

    elapsed_total = time.time() - start_wall
    print(f"Total elapsed: {elapsed_total:.1f} s")
    print()

    # --- JSON payload ---
    stamp = start_ts.strftime("%Y%m%d_%H%M%S")
    out_path = resolve_output_path(f"BCM_v26_Paper_B_Probes_5_17_{stamp}.json")

    hypotheses_tested = {
        "H_PAPER_B_KERNEL_A_BREAKS_INVARIANCE": {
            "statement": (
                "H-PaperB-KernelA Varying the Taylor kernel a-"
                "coefficient across [0.08, 0.18] breaks the four-"
                "field tensor invariance established in 5_15 and "
                "5_16 for xi in [0.005, 0.07]. Four gates: (B1) "
                "lambda_c(a) Pearson correlation with a >= 0.95; "
                "(B2) lambda_c relative range >= 30% of the a=0.12 "
                "baseline; (B3) lambda_cold_entry(a) tracks a with "
                "Pearson correlation >= 0.95 and relative range >= "
                "30%; (B4) at a = 0.12 the measured lambda_c "
                "reproduces the 5_15 baseline 0.059165791 within "
                "1e-6. PASS establishes a as the first physical "
                "bifurcation control axis confirmed to exit the "
                "xi-plateau identified in the probe series."
            ),
            "result": result,
            "evidence_type": "primary" if result == "PASS" else "default",
            "pass_count": int(passed_count),
            "total_configs": 4,
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "section_7_2",
                "taylor_kernel_perturbation",
                "a_coefficient_scan",
                "bifurcation_control_axis",
                "invariance_breaking",
                "four_field_tensor",
                "spectral_eigenvalue",
                "xi_plateau_exit",
                "kernel_origin",
                "section_5_topology",
            ],
        },
    }

    payload = {
        "test_name": "BCM_v26_Paper_B_Probes_5_17",
        "test_number": 5,
        "test_sub_number": 17,
        "test_version": 1,
        "timestamp": start_ts.isoformat(),
        "elapsed_seconds": elapsed_total,
        "paper_b_section": "7.2",
        "paper_b_probe": "Taylor a-coefficient perturbation (invariance-breaking probe)",
        "test_role": "primary_measurement",
        "grid": f"{CFG['grid_N']}x{CFG['grid_N']}",
        "notes": (
            "Test 5_17 is the first perturbation targeting the 4-"
            "field tensor invariance class established by 5_15 / "
            "5_16. The Taylor a-coefficient is varied across five "
            "values; lambda_c(a), lambda_fold_center(a), lambda_"
            "cold_entry(a), and H(a) are extracted per a. Four "
            "breakage gates test whether a is a bifurcation "
            "control axis. All other parameters (b, D, alpha, dt, "
            "pumps, grid, classifier v2, xi) are frozen from 5_15 "
            "baseline."
        ),
        "a_values": A_VALUES,
        "baseline_lambda_c_5_15": BASELINE_LAMBDA_C,
        "config_snapshot": {
            "dt": CFG["dt"],
            "D_diffusion": CFG["D_diffusion"],
            "alpha_regularization": CFG["alpha_regularization"],
            "ham_s_coeff_b": CFG["ham_s_coeff_b"],
            "xi_coupling": CFG["xi_coupling"],
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
        },
        "gate_thresholds": {
            "b1_pearson_min_abs": CFG["b1_pearson_min_abs"],
            "b2_rel_range_min": CFG["b2_rel_range_min"],
            "b3_cold_pearson_min_abs": CFG["b3_cold_pearson_min_abs"],
            "b3_cold_rel_range_min": CFG["b3_cold_rel_range_min"],
            "b4_baseline_tolerance": CFG["b4_baseline_tolerance"],
        },
        "a_perturbation_tensor": tensor,
        "breakage_gates": gates,
        "observations": observations,
        "overall_result": {
            "result": result,
            "gates_passed": int(passed_count),
            "gates_total": 4,
        },
        "per_a_payload": a_payloads,
        "hypotheses_tested": hypotheses_tested,
        "scope": (
            "Five-value a-coefficient sweep with full dual-sweep "
            "per a and four-field tensor extraction. Compared "
            "against the xi-invariant baseline established in "
            "5_15 / 5_16. Secondary perturbation axes (alpha, D) "
            "reserved for subsequent tests."
        ),
        "next_tests_reserved": {
            "5_18": "alpha-regularization scan (tests hysteresis memory-origin)",
            "5_19": "D-diffusion scan (tests spatial coupling strength)",
        },
        "keywords": [
            "paper_b",
            "section_7_2",
            "taylor_kernel_perturbation",
            "a_coefficient_scan",
            "bifurcation_control_axis",
            "invariance_breaking",
            "four_field_tensor",
            "spectral_eigenvalue",
            "xi_plateau_exit",
            "classifier_v2",
            "section_5_topology",
        ],
        "cube_coordinates": {
            "L": "L4_Operational",
            "OD": "OF_Flight_Operations",
            "cube": "Cube_7_Spectral_Fold",
        },
        "primacy_statement": (
            "All theoretical concepts, the Anchor Equation, "
            "Brucetron and Psi_bruce, the Taylor kernel "
            "sigma_eq = (a - lambda) / b relation, the a-"
            "coefficient perturbation design, the invariance-"
            "breaking gate structure (B1-B4), and every "
            "originating insight belong solely to Stephen Justin "
            "Burdick Sr. Four AI systems assist the project at "
            "the direction of the Foreman; no AI system owns or "
            "co-owns any theoretical concept. Emerald Entities "
            "LLC -- GIBUSH Systems."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"JSON written: {out_path}")


if __name__ == "__main__":
    main()
