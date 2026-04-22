# -*- coding: utf-8 -*-
"""
BCM v26 Paper B Probe Test 5_19
Paper B Section 7.2 -- D-Diffusion Perturbation
                       (Second Kinetic-Axis Classification Test)

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-04-22

--------------------------------------------------------------------
PRIMACY STATEMENT
--------------------------------------------------------------------
All theoretical concepts, the Anchor Equation, Brucetron and
Psi_bruce, the two-axis kinetic-decoupling claim (after 5_18
demonstrated alpha is a kinetic-only axis that preserves the
topological four-field tensor), the D-diffusion perturbation
design testing whether D is a second kinetic axis with the same
decoupling property, the three-gate structure (D1 kinetic
modulation, D2 topological invariance, D3 baseline anchor), and
every originating insight in this file belong solely to Stephen
Justin Burdick Sr. Stephen Burdick is the sole discoverer and
theoretical originator of the BCM framework. Four AI systems
(Claude, ChatGPT, Gemini, Grok) assist the project as
computational tools and reviewers at the direction of the
Foreman. No AI system owns or co-owns any theoretical concept.
Emerald Entities LLC -- GIBUSH Systems.

--------------------------------------------------------------------
CONTEXT
--------------------------------------------------------------------
Probe stack so far (empirical, published):

  5_14 J-coupling audit:     xi numerically inactive; J at floor
  5_15 xi-response curve:    four-field tensor xi-invariant
  5_16 four-field decomposition: PASS, lambda_c != lambda_fold
  5_17 a-coefficient scan:   topology broken; lambda_c scales
                             linearly with a at ~0.0592 * (a/b)
  5_18 alpha scan:           alpha preserves topology (K2 PASS),
                             alpha does not cleanly modulate H
                             (K1 FAIL with 8% range), alpha IS a
                             strong kinetic parameter
                             (fwd_total_steps varies 5x)

After 5_18 the operator basis reads:

  a       -> topological (primary bifurcation control)
  alpha   -> kinetic convergence (preserves topology)
  xi      -> null in tested range [0.005, 0.07]

The diffusion coefficient D has not yet been perturbed. Test 5_19
tests whether D is:

  (a) a second kinetic axis preserving topology like alpha
  (b) a mixed axis with both kinetic and topological effects
  (c) a topological axis moving the four-field tensor

--------------------------------------------------------------------
SCOPE
--------------------------------------------------------------------
D values: [0.1, 0.25, 0.5, 1.0, 2.0]

  D = 0.1    slow diffusion (20x baseline reduction)
  D = 0.25   half baseline
  D = 0.5    5_15 baseline
  D = 1.0    twice baseline
  D = 2.0    4x baseline (still within forward-Euler stability;
             dt*D/dx^2 = 0.1 << 0.5 threshold)

D = 0.0 skipped: it decouples grid cells entirely (no spatial
propagation), producing a qualitatively different regime. If the
question of complete spatial decoupling becomes important, a
separate test is warranted.

All other parameters frozen at 5_15 baseline: a = 0.12, b = 0.12,
alpha = 0.8, xi = 0.035, pumps from 5_7, grid 128, sweep
[0.001, 0.30] 30 log-spaced dual, classifier v2.

Three gates:

  D1 D modulates kinetics: forward-sweep total steps have
     relative range >= 0.30 across D values. Expected: higher D
     converges faster (more aggressive smoothing), lower D
     converges slower.

  D2 D preserves topology: relative range of lambda_c across D
     < 0.01, AND same for lambda_fold AND lambda_cold. If D
     primarily enters the kinetic response (like alpha), the
     four-field tensor should be D-invariant.

  D3 baseline anchor: at D = 0.5, lambda_c reproduces the 5_15
     value 0.059165791 within 1e-6. Solver reproducibility.

PASS on all three registers H_PAPER_B_D_KINETIC_DECOUPLING with
primary evidence, confirming D as a second kinetic axis.

--------------------------------------------------------------------
HONEST PRE-RUN FLAG
--------------------------------------------------------------------
Unlike alpha (pure memory term), D enters the Laplacian
D * grad^2(sigma). Diffusion directly couples spatial points, so
a priori it could move lambda_c by changing the effective
source-decay balance at the basin edges. The prediction is not
as clean as alpha's was.

If D2 fails -- D shifts lambda_c -- that is an informative
finding: D is a mixed axis, and the operator basis needs to
account for it. Paper B Section 5 would then describe three
axes (a, D, alpha) each with different topological/kinetic
weights, not a clean single-topological / multi-kinetic split.

This file records what the data shows and does not commit to an
outcome.
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

D_VALUES = [0.1, 0.25, 0.5, 1.0, 2.0]

BASELINE_LAMBDA_C = 0.059165791
BASELINE_LAMBDA_FOLD = 0.112209954
BASELINE_LAMBDA_COLD = 0.136599578
BASELINE_H = 0.049870

CFG = {
    "dt": 0.05,
    "D_diffusion": 0.5,              # per-iteration override
    "alpha_regularization": 0.8,
    "ham_s_coeff_a": 0.12,
    "ham_s_coeff_b": 0.12,
    "xi_coupling": 0.035,

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

    "cold_phi_low_frac": 0.01,
    "cold_stay_dead_steps": 2,
    "fold_half_width_factor": 1.0,

    "basin_r2_threshold": 0.95,
    "cold_torus_max_phi_in_range": 0.01,

    "fold_width_high_frac": 0.9,
    "fold_width_low_frac": 0.1,

    # D-kinetic-decoupling gates
    "d1_kinetic_rel_range_min": 0.30,
    "d2_topology_rel_range_max": 0.01,
    "d3_baseline_tolerance": 1e-6,
}


# =====================================================================
# KERNEL PRIMITIVES (identical to 5_18)
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
        return {"success": False, "message": "scipy unavailable or too few points",
                "lambda_c": None, "k": None, "r_squared": None,
                "n_points": int(len(lambdas))}
    try:
        popt, _ = curve_fit(sigmoid_fn, lambdas, phis,
                            p0=[float(np.median(lambdas)), 20.0], maxfev=10000)
        lam_c = float(popt[0])
        k = float(popt[1])
        phi_pred = sigmoid_fn(lambdas, lam_c, k)
        ss_res = float(np.sum((phis - phi_pred) ** 2))
        ss_tot = float(np.sum((phis - np.mean(phis)) ** 2)) + 1e-30
        r2 = 1.0 - ss_res / ss_tot
        return {"success": True, "message": "OK",
                "lambda_c": lam_c, "k": k, "r_squared": float(r2),
                "n_points": int(len(lambdas))}
    except Exception as exc:
        return {"success": False, "message": f"fit failed: {exc}",
                "lambda_c": None, "k": None, "r_squared": None,
                "n_points": int(len(lambdas))}


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
        "lambda_fold_center_stiffness": lambda_fold_center_stiffness,
        "lambda_cold_entry": lambda_cold_entry,
        "active_region_sigmoid_fit": active_fit,
        "n_active_points": int(len(active_indices)),
    }


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


def kernel_validation(cfg):
    N = cfg["grid_N"]
    a = cfg["ham_s_coeff_a"]
    b = cfg["ham_s_coeff_b"]
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
        "D_at_validation": cfg["D_diffusion"],
        "validation_lambdas": validation_lambdas,
        "max_deviation": float(max_dev),
        "threshold": 1e-3,
        "faithful": bool(faithful),
        "per_lambda": comparisons,
    }


# =====================================================================
# PER-D DRIVER
# =====================================================================

def run_single_D(d_value, base_cfg):
    cfg = dict(base_cfg)
    cfg["D_diffusion"] = float(d_value)

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

    hyst_active = hysteresis_restricted(fwd_phi, ret_phi, regime["lambda_cold_entry"])

    fit = regime["active_region_sigmoid_fit"]
    lam_c = fit.get("lambda_c") if fit else None

    fwd_total_steps = sum(r["n_steps"] for r in fwd_phi)
    fwd_not_converged = sum(1 for r in fwd_phi if not r["converged"])
    ret_total_steps = sum(r["n_steps"] for r in ret_phi)
    ret_not_converged = sum(1 for r in ret_phi if not r["converged"])

    elapsed = time.time() - t0

    tensor_point = {
        "D": float(d_value),
        "a": float(cfg["ham_s_coeff_a"]),
        "b": float(cfg["ham_s_coeff_b"]),
        "alpha": float(cfg["alpha_regularization"]),
        "xi": float(cfg["xi_coupling"]),
        "lambda_c_spectral": lam_c,
        "lambda_fold_center_stiffness": regime["lambda_fold_center_stiffness"],
        "lambda_cold_entry": regime["lambda_cold_entry"],
        "H_D": hyst_active["area"],
        "sigmoid_r_squared": fit.get("r_squared") if fit else None,
        "sigmoid_k": fit.get("k") if fit else None,
        "n_active_points": regime["n_active_points"],
        "kernel_validation_faithful": kv["faithful"],
        "kernel_validation_max_dev": kv["max_deviation"],
        "forward_total_steps": int(fwd_total_steps),
        "forward_not_converged_count": int(fwd_not_converged),
        "return_total_steps": int(ret_total_steps),
        "return_not_converged_count": int(ret_not_converged),
        "elapsed_seconds": float(elapsed),
    }

    payload = {
        "D": float(d_value),
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
# GATE ANALYSIS
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


def relative_range(values):
    arr = [v for v in values if v is not None]
    if len(arr) < 2:
        return None
    arr = np.array(arr, dtype=float)
    mn, mx = float(np.min(arr)), float(np.max(arr))
    mean = float(np.mean(arr))
    denom = abs(mean) if abs(mean) > 1e-30 else 1e-30
    return {
        "n": int(len(arr)),
        "min": mn, "max": mx, "mean": mean,
        "range": float(mx - mn),
        "relative_range": float((mx - mn) / denom),
    }


def evaluate_d_gates(tensor, cfg):
    d_vals = [t["D"] for t in tensor]
    fwd_steps = [t["forward_total_steps"] for t in tensor]
    h_vals = [t["H_D"] for t in tensor]
    lambda_c_vals = [t["lambda_c_spectral"] for t in tensor]
    lambda_fold_vals = [t["lambda_fold_center_stiffness"] for t in tensor]
    lambda_cold_vals = [t["lambda_cold_entry"] for t in tensor]

    # D1: D modulates kinetics (forward total steps varies >= 30%)
    fwd_steps_range = relative_range(fwd_steps)
    d1_pass = (fwd_steps_range is not None
               and fwd_steps_range["relative_range"] >= cfg["d1_kinetic_rel_range_min"])

    # D2: topology invariant under D
    rr_lambda_c = relative_range(lambda_c_vals)
    rr_lambda_fold = relative_range(lambda_fold_vals)
    rr_lambda_cold = relative_range(lambda_cold_vals)
    tol = cfg["d2_topology_rel_range_max"]

    def inv_pass(rr):
        if rr is None:
            return False
        return bool(rr["relative_range"] < tol)

    d2_lambda_c_pass = inv_pass(rr_lambda_c)
    d2_lambda_fold_pass = inv_pass(rr_lambda_fold)
    d2_lambda_cold_pass = inv_pass(rr_lambda_cold)
    d2_pass = d2_lambda_c_pass and d2_lambda_fold_pass and d2_lambda_cold_pass

    # D3: baseline reproducibility at D = 0.5
    baseline_point = next(
        (t for t in tensor if abs(t["D"] - 0.5) < 1e-9), None
    )
    d3_pass = False
    d3_deviation = None
    if baseline_point is not None and baseline_point["lambda_c_spectral"] is not None:
        d3_deviation = abs(baseline_point["lambda_c_spectral"] - BASELINE_LAMBDA_C)
        d3_pass = bool(d3_deviation < cfg["d3_baseline_tolerance"])

    # Observational (not gated)
    h_corr = pearson_correlation(d_vals, h_vals)
    h_rel_range = relative_range(h_vals)
    fwd_steps_corr = pearson_correlation(d_vals, fwd_steps)

    gates = {
        "D1_D_modulates_kinetics": {
            "passed": d1_pass,
            "forward_steps_relative_range": fwd_steps_range,
            "threshold": cfg["d1_kinetic_rel_range_min"],
            "forward_steps_pearson_correlation": fwd_steps_corr,
        },
        "D2_D_preserves_topology": {
            "passed": d2_pass,
            "tolerance": tol,
            "lambda_c_invariant": d2_lambda_c_pass,
            "lambda_c_relative_range": rr_lambda_c,
            "lambda_fold_invariant": d2_lambda_fold_pass,
            "lambda_fold_relative_range": rr_lambda_fold,
            "lambda_cold_invariant": d2_lambda_cold_pass,
            "lambda_cold_relative_range": rr_lambda_cold,
        },
        "D3_baseline_anchor": {
            "passed": d3_pass,
            "baseline_lambda_c_5_15": BASELINE_LAMBDA_C,
            "measured_lambda_c_D_0_5": (
                baseline_point["lambda_c_spectral"] if baseline_point else None
            ),
            "deviation": d3_deviation,
            "tolerance": cfg["d3_baseline_tolerance"],
        },
    }

    observations = {
        "H_D_pearson_correlation": h_corr,
        "H_D_relative_range": h_rel_range,
    }

    all_pass = d1_pass and d2_pass and d3_pass
    passed_count = sum(1 for g in gates.values() if g["passed"])

    if all_pass:
        result = "PASS"
    elif passed_count >= 2:
        result = "PARTIAL"
    else:
        result = "INCONCLUSIVE"

    return gates, observations, result, passed_count


# =====================================================================
# OUTPUT
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


def main():
    print("=" * 76)
    print("BCM v26 Paper B Probe Test 5_19 -- D-Diffusion Perturbation")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC / GIBUSH Systems")
    print("=" * 76)
    print(f"D values        = {D_VALUES}")
    print(f"a, b (fixed)    = {CFG['ham_s_coeff_a']}, {CFG['ham_s_coeff_b']}")
    print(f"alpha (fixed)   = {CFG['alpha_regularization']}")
    print(f"xi (inactive)   = {CFG['xi_coupling']}")
    print(f"Objective       = test D as second kinetic axis")
    print(f"                  (D modulates kinetics but preserves topology?)")
    print()

    start_ts = datetime.now()
    start_wall = time.time()

    d_payloads = {}
    tensor = []
    for idx, d_val in enumerate(D_VALUES):
        print(f"[{idx + 1}/{len(D_VALUES)}] D = {d_val} ...")
        point, payload = run_single_D(d_val, CFG)
        tensor.append(point)
        d_payloads[f"D_{d_val}"] = payload
        print(f"  kernel_valid = {point['kernel_validation_faithful']}  "
              f"max_dev = {point['kernel_validation_max_dev']:.3e}")
        print(f"  lambda_c     = {point['lambda_c_spectral']}")
        print(f"  lambda_fold  = {point['lambda_fold_center_stiffness']}")
        print(f"  lambda_cold  = {point['lambda_cold_entry']}")
        print(f"  H(D)         = {point['H_D']}")
        print(f"  fwd total_steps = {point['forward_total_steps']}  "
              f"not_converged = {point['forward_not_converged_count']}")
        print(f"  ret total_steps = {point['return_total_steps']}  "
              f"not_converged = {point['return_not_converged_count']}")
        print(f"  elapsed = {point['elapsed_seconds']:.1f} s")
        print()

    print("=" * 76)
    print("D PERTURBATION TENSOR")
    print("=" * 76)
    header = (f"{'D':>6}  {'lambda_c':>12}  {'lambda_fold':>12}  "
              f"{'lambda_cold':>12}  {'H(D)':>10}  {'R^2':>7}  "
              f"{'fwd_steps':>10}")
    print(header)
    print("-" * len(header))
    for t in tensor:
        def fmt(v, spec):
            return format(v, spec) if v is not None else "        None"
        print(f"{t['D']:>6.3f}  "
              f"{fmt(t['lambda_c_spectral'], '12.9f')}  "
              f"{fmt(t['lambda_fold_center_stiffness'], '12.9f')}  "
              f"{fmt(t['lambda_cold_entry'], '12.9f')}  "
              f"{fmt(t['H_D'], '10.6f')}  "
              f"{fmt(t['sigmoid_r_squared'], '7.4f')}  "
              f"{t['forward_total_steps']:>10d}")
    print("=" * 76)
    print()

    gates, observations, result, passed_count = evaluate_d_gates(tensor, CFG)

    print("D-DECOUPLING GATES")
    print("-" * 76)
    for gname, gdata in gates.items():
        status = "PASS" if gdata["passed"] else "FAIL"
        print(f"  {gname:<30}  {status}")
        for key, val in gdata.items():
            if key == "passed":
                continue
            print(f"      {key}: {val}")
    print("-" * 76)
    print(f"Gates passed: {passed_count}/3")
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
    out_path = resolve_output_path(f"BCM_v26_Paper_B_Probes_5_19_{stamp}.json")

    hypotheses_tested = {
        "H_PAPER_B_D_KINETIC_DECOUPLING": {
            "statement": (
                "H-PaperB-DKinetic The D-diffusion coefficient is "
                "a second kinetic axis preserving topology like "
                "alpha. Three gates: (D1) D modulates kinetics, "
                "tested by forward-sweep total steps having "
                "relative range >= 0.30 across D in [0.1, 2.0]; "
                "(D2) D preserves topology, tested by lambda_c, "
                "lambda_fold, lambda_cold each having relative "
                "range < 1% across D; (D3) baseline anchor at "
                "D = 0.5 reproduces 5_15 lambda_c = 0.059165791 "
                "within 1e-6. PASS establishes D as a second "
                "kinetic axis, completing the operator basis: a "
                "topological, alpha and D kinetic, xi null."
            ),
            "result": result,
            "evidence_type": "primary" if result == "PASS" else "default",
            "pass_count": int(passed_count),
            "total_configs": 3,
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "section_7_2",
                "d_diffusion_perturbation",
                "second_kinetic_axis",
                "kinetic_topological_decoupling",
                "four_field_tensor",
                "operator_basis",
                "orthogonal_control_axes",
                "section_5_topology",
            ],
        },
    }

    payload = {
        "test_name": "BCM_v26_Paper_B_Probes_5_19",
        "test_number": 5,
        "test_sub_number": 19,
        "test_version": 1,
        "timestamp": start_ts.isoformat(),
        "elapsed_seconds": elapsed_total,
        "paper_b_section": "7.2",
        "paper_b_probe": "D-diffusion perturbation (second-kinetic-axis test)",
        "test_role": "primary_measurement",
        "grid": f"{CFG['grid_N']}x{CFG['grid_N']}",
        "notes": (
            "Test 5_19 varies D across [0.1, 0.25, 0.5, 1.0, 2.0] "
            "with all other parameters frozen at 5_15 baseline. "
            "Extracts four-field tensor per D and tests three "
            "gates: D1 D modulates kinetics, D2 D preserves "
            "topology, D3 baseline anchor at D = 0.5. Combined "
            "with 5_17 (a controls topology) and 5_18 (alpha is "
            "kinetic-only), this completes the operator basis "
            "characterization for Paper B Section 5."
        ),
        "D_values": D_VALUES,
        "baseline_references": {
            "baseline_lambda_c_5_15": BASELINE_LAMBDA_C,
            "baseline_lambda_fold_5_15": BASELINE_LAMBDA_FOLD,
            "baseline_lambda_cold_5_15": BASELINE_LAMBDA_COLD,
            "baseline_H_5_15": BASELINE_H,
        },
        "config_snapshot": {
            "dt": CFG["dt"],
            "alpha_regularization": CFG["alpha_regularization"],
            "ham_s_coeff_a": CFG["ham_s_coeff_a"],
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
            "d1_kinetic_rel_range_min": CFG["d1_kinetic_rel_range_min"],
            "d2_topology_rel_range_max": CFG["d2_topology_rel_range_max"],
            "d3_baseline_tolerance": CFG["d3_baseline_tolerance"],
        },
        "d_perturbation_tensor": tensor,
        "decoupling_gates": gates,
        "observations": observations,
        "overall_result": {
            "result": result,
            "gates_passed": int(passed_count),
            "gates_total": 3,
        },
        "per_D_payload": d_payloads,
        "hypotheses_tested": hypotheses_tested,
        "scope": (
            "Five-value D diffusion sweep with full dual-sweep "
            "per D and four-field tensor extraction. Compared "
            "against the 5_15 / 5_16 baseline at D = 0.5. Tests "
            "whether D is a second kinetic axis analogous to "
            "alpha (5_18), a mixed axis, or a topological axis. "
            "Combined with 5_17 and 5_18, establishes the "
            "complete operator basis for Paper B Section 5."
        ),
        "operator_basis_summary": {
            "topological_axis": "a (Taylor coefficient, 5_17 PASS)",
            "kinetic_axis_1": "alpha (memory regularization, 5_18 K2 PASS)",
            "kinetic_axis_2_candidate": "D (spatial diffusion, this test)",
            "null_axis": "xi (5_15 xi-plateau, tested range [0.005, 0.07])",
        },
        "keywords": [
            "paper_b",
            "section_7_2",
            "d_diffusion_perturbation",
            "second_kinetic_axis",
            "kinetic_topological_decoupling",
            "four_field_tensor",
            "operator_basis",
            "orthogonal_control_axes",
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
            "Brucetron and Psi_bruce, the two-axis kinetic-"
            "decoupling claim, the D-diffusion perturbation "
            "design, the three-gate structure (D1 kinetic "
            "modulation, D2 topological invariance, D3 baseline "
            "anchor), and every originating insight belong "
            "solely to Stephen Justin Burdick Sr. Four AI "
            "systems assist the project at the direction of the "
            "Foreman; no AI system owns or co-owns any "
            "theoretical concept. Emerald Entities LLC -- "
            "GIBUSH Systems."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"JSON written: {out_path}")


if __name__ == "__main__":
    main()
