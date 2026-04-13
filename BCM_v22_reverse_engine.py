# -*- coding: utf-8 -*-
"""
BCM v22 — Reverse Calculation Engine
======================================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
GIBUSH Systems

The destination already exists in the pattern.
Transit is not travel. It is alignment.

v22 calculates BACKWARD from the destination galaxy's
substrate field to the required 9D entry state. The
navigation pre-check predicts R_9to10 BEFORE committing
to the fold. If the destination cannot support coherent
arrival, the fold does not open.

Field-Theory Foundation (Burdick):
  Action S = integral of Lagrangian density over spacetime
  Euler-Lagrange → existing wave equation
  Stress-energy tensor → gravity IS the substrate footprint
  Reverse calculation → variational principle (delta S = 0
  subject to boundary condition F(S_9D) = S_dest)

Usage:
    python BCM_v22_reverse_engine.py
    python BCM_v22_reverse_engine.py --quick
    python BCM_v22_reverse_engine.py --data-dir data/sparc_raw

Output: JSON with predicted R_9to10, go/no-go, arrival
profile, Lagrangian diagnostics for each SPARC galaxy.
Foreman runs, provides JSON. Agent reads results.
"""

import numpy as np
import os
import sys
import json
import time
import math
import argparse

# ── Path setup ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "core"))

from sparc_ingest import load_galaxy, build_newtonian_curve
from substrate_solver import SubstrateSolver

try:
    from Burdick_Crag_Mass import inject_crag_mass, KAPPA_BH_CALIBRATED
    _BCM_AVAILABLE = True
except ImportError:
    _BCM_AVAILABLE = False
    KAPPA_BH_CALIBRATED = 2.0

try:
    from BCM_Substrate_overrides import apply_galaxy_override
    _OVERRIDES_AVAILABLE = True
except ImportError:
    _OVERRIDES_AVAILABLE = False


# ═══════════════════════════════════════
# FROZEN CONSTANTS — ALL VERSIONS
# ═══════════════════════════════════════
LAMBDA          = 0.1
KAPPA           = 2.0
ALPHA           = 0.80
GRID            = 256
LAYERS          = 8
SETTLE          = 20000
MEASURE         = 5000

# v21 frozen
THETA_9TO10     = 0.92
K_BOUNDARY      = 150.0
PHI_SAFETY      = 0.10
GUARDIAN_STRENGTH   = 0.85
D_CLOAK_STRENGTH    = 0.90
D_OPERATION_STRENGTH = 0.75
FIB_RATIO       = 1.6180339887

# v22 frozen
REVERSE_ITER_MAX      = 50
LOSS_FIELD_WEIGHT     = 1.0
LOSS_COHERENCE_WEIGHT = 2.5
LOSS_7D_SURVIVAL_WEIGHT = 3.0
OM_SYNC_FREQ          = 0.010   # 1D heartbeat reference

# v22 arrival profile templates
ARRIVAL_PROFILES = {
    "gentle":   {"pump_max": 0.10, "lambda_min": 0.030},
    "standard": {"pump_max": 0.25, "lambda_min": 0.020},
    "hot":      {"pump_max": 0.50, "lambda_min": 0.015},
    "deep":     {"pump_max": 0.25, "lambda_min": 0.005},
}


# ═══════════════════════════════════════
# SUBSTRATE ACTION — FROZEN LAGRANGIAN
# (Burdick, 2026)
#
# S = integral [ L ] d²x dt
#
# L = (1/2)(d_mu sigma)(d^mu sigma)
#     - (lambda/2) sigma²
#     + J_crag * sigma
#     + (alpha/2)(sigma - sigma_prev)²
#
# Euler-Lagrange → d²sigma/dt² = c² laplacian(sigma)
#                   - lambda*sigma + J + alpha*(sigma - sigma_prev)
# This IS the wave equation already in the solver.
#
# Stress-Energy Tensor:
# T_mu_nu = partial_mu(sigma) * partial_nu(sigma)
#         - g_mu_nu * L
# Gravity = cumulative footprint of substrate agitation.
# ═══════════════════════════════════════


def compute_lagrangian_density(sigma, sigma_prev, J_source,
                               dx, dt, lam, alpha):
    """
    Compute the Lagrangian density L(x,y) at each grid point.

    L = (1/2)(grad sigma)² - (lambda/2) sigma²
        + J * sigma + (alpha/2)(sigma - sigma_prev)²

    Returns 2D field of L values.
    Stationary action (delta S = 0) confirmed when
    spatial integral is stable between timesteps.
    """
    # Kinetic: (1/2)|grad sigma|²
    grad_x = np.gradient(sigma, dx, axis=1)
    grad_y = np.gradient(sigma, dx, axis=0)
    kinetic = 0.5 * (grad_x ** 2 + grad_y ** 2)

    # Mass: -(lambda/2) sigma²
    mass = -0.5 * lam * sigma ** 2

    # Source: J * sigma
    source = J_source * sigma

    # Memory: (alpha/2)(sigma - sigma_prev)²
    memory = 0.5 * alpha * (sigma - sigma_prev) ** 2

    L = kinetic + mass + source + memory
    return L


def compute_stress_energy_trace(sigma, dx, lam, alpha,
                                 sigma_prev):
    """
    Trace of stress-energy tensor T^mu_mu.

    For the 2D+1 substrate field:
    T_00 = (1/2)(d_t sigma)² + (1/2)|grad sigma|²
           + (lambda/2) sigma²

    This is the energy density of the substrate.
    Integral over space = total substrate energy budget.
    """
    grad_x = np.gradient(sigma, dx, axis=1)
    grad_y = np.gradient(sigma, dx, axis=0)
    grad_sq = grad_x ** 2 + grad_y ** 2

    # Time derivative approximated from memory
    d_sigma_dt = (sigma - sigma_prev) / max(1e-15, 1.0)
    time_sq = d_sigma_dt ** 2

    T_00 = 0.5 * time_sq + 0.5 * grad_sq + 0.5 * lam * sigma ** 2
    return T_00


# ═══════════════════════════════════════
# 9D GATE OPERATORS — MAPPED FROM SOLVER
# ═══════════════════════════════════════

def build_psi9(phi_rms, coherence_7D, R_7D):
    """Build 9D state vector from substrate field diagnostics."""
    psi = np.array([
        1.0,                                  # 2D substrate
        0.95,                                 # 3D physical
        max(0.01, 1.0 - phi_rms * 10),        # 4D operational
        0.0,                                  # 5D buffer (set below)
        coherence_7D,                         # 6D field shape
        R_7D,                                 # 7D spectral fold
        R_7D * 0.95,                          # 8D hard point
        R_7D * 0.95 / FIB_RATIO,             # 9D circumpunct
    ])
    psi[3] = 0.5 * (psi[2] + psi[4])         # 5D = gauge
    norm = np.linalg.norm(psi)
    return psi / norm if norm > 1e-15 else psi


def compute_R_9to10(OpT_val, OpC_val, R_7D, phi_rms,
                     coherence_7D):
    """
    9D to 10D coherence gate scalar (v21 equation).

    R_9to10 = Tr(OpT_10 @ rho_9) * Re(<psi_9|OpC_10|psi_9>)
              / R_7D

    Threshold: THETA_9TO10 = 0.92
    """
    n = 8
    psi9 = build_psi9(phi_rms, coherence_7D, R_7D)
    rho9 = np.outer(psi9, psi9)

    # OpT10 matrix
    OpT10 = np.eye(n) * OpT_val
    c = (1.0 - OpT_val) * 0.1
    for i in range(n - 1):
        OpT10[i, i + 1] = c
        OpT10[i + 1, i] = c

    # OpC10 matrix
    OpC10 = np.eye(n) * OpC_val
    for i in range(n):
        for j in range(n):
            if i != j:
                OpC10[i, j] = OpC_val * np.exp(
                    -abs(i - j) * 0.5) * 0.05

    tr_OpT = float(np.real(np.trace(OpT10 @ rho9)))
    exp_OpC = float(np.real(np.dot(psi9, OpC10 @ psi9)))

    if R_7D > 1e-15:
        R = (tr_OpT * exp_OpC) / R_7D
    else:
        R = 0.0
    return float(R)


def map_solver_to_operators(solver_result):
    """
    Map substrate solver diagnostics to 7D dimensional
    operators for the 9D-to-10D gate.

    Solver output → Dimensional operators:
      corr_radial_full  → OpT (field self-consistency)
      cos_delta_phi     → OpC (phase alignment quality)
      layer_coherence   → Coherence (inter-layer coupling)
      (derived)         → R_7D, phi_rms
    """
    # OpT: substrate potential matches baryonic structure
    OpT = max(0.0, min(1.0,
        abs(solver_result.get("corr_radial_full", 0.0))))

    # OpC: phase alignment between memory and forcing
    cos_dphi = solver_result.get("cos_delta_phi", 0.0)
    OpC = max(0.0, min(1.0, abs(cos_dphi)))

    # Opacity divergence
    opacity_div = abs(OpT - OpC)

    # R_7D: mirror reflectivity
    R_7D = ((OpT + OpC) / 2.0) * (1.0 - opacity_div)

    # Coherence: layer coupling quality
    coherence = max(0.0, min(1.0,
        solver_result.get("layer_coherence", 0.0)))

    # phi_rms proxy: field disorder
    # Low corr_radial = high disorder = high phi_rms
    corr_inner = abs(solver_result.get("corr_radial_inner", 0.0))
    phi_rms = max(0.0, (1.0 - corr_inner) * 0.1)

    return {
        "OpT": OpT,
        "OpC": OpC,
        "opacity_div": opacity_div,
        "R_7D": R_7D,
        "coherence": coherence,
        "phi_rms": phi_rms,
    }


# ═══════════════════════════════════════
# LOSS FUNCTION — REVERSE OPTIMIZATION
# ═══════════════════════════════════════

def compute_loss(R_9to10, R_7D, field_match=0.0):
    """
    Reverse calculation loss (Burdick v22).

    L = w1 * ||F(S_9D) - S_dest||
      + w2 * (1 - R_9to10)
      + w3 * max(0, 0.92 - R_7D)

    Lower = better. L = 0 is perfect alignment.
    """
    L1 = LOSS_FIELD_WEIGHT * field_match
    L2 = LOSS_COHERENCE_WEIGHT * (1.0 - R_9to10)
    L3 = LOSS_7D_SURVIVAL_WEIGHT * max(0.0, THETA_9TO10 - R_7D)
    return L1 + L2 + L3, L1, L2, L3


# ═══════════════════════════════════════
# CLASS TEMPLATE & ARRIVAL RECOMMENDATION
# ═══════════════════════════════════════

def classify_destination(solver_result, chi2_bcm=None,
                          rms_bcm=None, v_max=0.0):
    """
    Classify destination galaxy by substrate interaction
    state. Uses solver diagnostics — no per-galaxy tuning.
    """
    cos_dphi = solver_result.get("cos_delta_phi", 0.0)
    corr_full = solver_result.get("corr_radial_full", 0.0)
    corr_inner = solver_result.get("corr_radial_inner", 0.0)
    layer_coh = solver_result.get("layer_coherence", 0.0)
    decoupling = solver_result.get("decoupling_ratio", 1.0)

    # Class determination from field diagnostics
    if abs(cos_dphi) > 0.99 and abs(corr_full) > 0.95:
        if v_max > 180:
            return "I"     # Transport-dominated
        else:
            return "II"    # Residual/hysteresis
    elif abs(cos_dphi) > 0.95 and abs(corr_full) > 0.80:
        if abs(corr_inner) > abs(corr_full):
            return "IV"    # Declining substrate
        else:
            return "III"   # Ground state
    elif abs(cos_dphi) < 0.80:
        return "V"         # Environmental (A or B)
    else:
        return "III"       # Default ground state


def recommend_arrival_profile(dest_class, R_9to10, R_7D):
    """
    Recommend arrival intensity based on destination class
    and gate pre-check.

    Gentle: Class I, III (stable substrate, easy match)
    Standard: Class II, IV (moderate coupling required)
    Hot: Class V (environmental disruption, need power)
    Deep: Class VI (bar geometry, precision required)
    """
    if R_9to10 < THETA_9TO10:
        return "NO-GO"

    if dest_class == "I":
        return "gentle"      # strong field, easy impedance match
    elif dest_class == "II":
        return "standard"
    elif dest_class == "III":
        return "gentle"      # weak field, minimal disruption
    elif dest_class == "IV":
        if R_7D > 0.98:
            return "standard"
        else:
            return "hot"     # declining field needs more energy
    elif dest_class in ("V", "V-A", "V-B"):
        return "hot"         # environmental noise
    elif dest_class == "VI":
        return "deep"        # bar geometry precision
    else:
        return "standard"


# ═══════════════════════════════════════
# FEATURE EXTRACTION — DESTINATION FIELD
# ═══════════════════════════════════════

def extract_destination_features(solver_result, galaxy_data):
    """
    Extract the substrate signature of the destination
    galaxy from the solver output.

    These features define what the craft must align WITH.
    The reverse calculation uses them to determine the
    required 9D entry state.
    """
    r_ax, prof_psi = solver_result["radial_psi"]
    _, prof_phi = solver_result["radial_phi"]

    # Dominant mode from substrate field FFT
    rho_layer0 = solver_result["rho_avg"][0]
    radial_mean = rho_layer0.mean(axis=0)
    fft_r = np.fft.fft(radial_mean)
    n_half = len(fft_r) // 2
    if n_half > 1:
        mode_amps = np.abs(fft_r[1:n_half])
        dominant_m = int(np.argmax(mode_amps)) + 1
        mode_purity = float(mode_amps[dominant_m - 1] /
                           (np.sum(mode_amps) + 1e-15))
    else:
        dominant_m = 1
        mode_purity = 0.0

    # Lambda gradient (torus curvature proxy)
    # Ratio of inner to outer substrate amplitude
    n_prof = len(prof_psi)
    if n_prof > 10:
        inner_amp = float(np.mean(np.abs(prof_psi[2:n_prof // 4])))
        outer_amp = float(np.mean(np.abs(prof_psi[3 * n_prof // 4:])))
        lambda_gradient = (inner_amp - outer_amp) / max(inner_amp, 1e-15)
    else:
        inner_amp = 0.0
        outer_amp = 0.0
        lambda_gradient = 0.0

    # Sigma distribution width
    sigma_field = solver_result["sigma_avg"].sum(axis=0)
    sigma_profile = sigma_field.mean(axis=0)
    if np.max(sigma_profile) > 0:
        half_max = np.max(sigma_profile) / 2.0
        above = np.where(sigma_profile > half_max)[0]
        sigma_width = float(len(above)) / len(sigma_profile)
    else:
        sigma_width = 0.0

    # 1D Om sync: base frequency from substrate field
    # The fundamental mode frequency that all registers
    # must align to during reverse calculation
    if n_half > 1:
        fund_freq = float(np.abs(fft_r[1]))
        om_sync = fund_freq * OM_SYNC_FREQ
    else:
        om_sync = OM_SYNC_FREQ

    return {
        "dominant_m":       dominant_m,
        "mode_purity":      mode_purity,
        "lambda_gradient":  lambda_gradient,
        "inner_amplitude":  inner_amp,
        "outer_amplitude":  outer_amp,
        "sigma_width":      sigma_width,
        "om_sync":          om_sync,
    }


# ═══════════════════════════════════════
# FIND GALAXY FILE
# ═══════════════════════════════════════

def find_dat_file(filename, data_dir):
    """Search data_dir and subdirectories for the .dat file."""
    direct = os.path.join(data_dir, filename)
    if os.path.exists(direct):
        return direct
    for root, dirs, files in os.walk(data_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


# ═══════════════════════════════════════
# GALAXY LIST — SAME AS CHI-SQUARED ENGINE
# ═══════════════════════════════════════

GALAXY_LIST = [
    "DDO154_rotmod.dat",
    "DDO064_rotmod.dat",
    "UGC07577_rotmod.dat",
    "NGC6789_rotmod.dat",
    "UGC04305_rotmod.dat",
    "D564-8_rotmod.dat",
    "NGC2976_rotmod.dat",
    "NGC0055_rotmod.dat",
    "IC2574_rotmod.dat",
    "NGC2366_rotmod.dat",
    "NGC3741_rotmod.dat",
    "UGC06667_rotmod.dat",
    "NGC2403_rotmod.dat",
    "NGC7793_rotmod.dat",
    "NGC6503_rotmod.dat",
    "NGC4559_rotmod.dat",
    "UGC06614_rotmod.dat",
    "NGC3726_rotmod.dat",
    "NGC5055_rotmod.dat",
    "NGC3198_rotmod.dat",
    "NGC2903_rotmod.dat",
    "NGC5033_rotmod.dat",
    "NGC6946_rotmod.dat",
    "NGC4013_rotmod.dat",
    "NGC2841_rotmod.dat",
    "NGC7331_rotmod.dat",
    "NGC3521_rotmod.dat",
    "NGC3953_rotmod.dat",
    "NGC5907_rotmod.dat",
    "NGC0891_rotmod.dat",
]


# ═══════════════════════════════════════
# PROCESS ONE GALAXY — REVERSE ENGINE
# ═══════════════════════════════════════

def process_galaxy(dat_path, grid, layers, verbose=True):
    """
    Full reverse calculation for one destination galaxy.

    1. Forward pass: run substrate solver
    2. Map solver output to dimensional operators
    3. Compute R_9to10 (navigation pre-check)
    4. Extract destination features
    5. Compute Lagrangian density (field-theory diagnostic)
    6. Evaluate loss function
    7. Classify destination & recommend arrival profile
    8. Return complete v22 diagnostic
    """
    galaxy_name = os.path.basename(dat_path).replace(
        "_rotmod.dat", "").replace(".dat", "")
    if verbose:
        print(f"\n{'='*60}")
        print(f"  DESTINATION: {galaxy_name}")
        print(f"{'='*60}")

    # ── 1. Load SPARC data ──
    galaxy = load_galaxy(dat_path, grid=grid, scale_factor=1.0,
                         source_mode="classic", lam=LAMBDA)
    r_kpc = galaxy["radii_kpc"]
    v_obs = galaxy["vobs"]
    v_newton = galaxy["newtonian_curve"]

    if len(r_kpc) < 5:
        if verbose:
            print(f"  SKIP: only {len(r_kpc)} data points")
        return None

    vmax = float(np.max(v_obs))

    # ── 2. Apply override if applicable ──
    J_source = galaxy["source_field"]
    override_class = "standard"

    if _OVERRIDES_AVAILABLE:
        try:
            J_override, override_params, was_applied = \
                apply_galaxy_override(galaxy_name, J_source,
                                      grid, vmax)
            if was_applied and J_override is not None:
                J_source = J_override
                override_class = override_params.get(
                    "class", "override")
                if verbose:
                    print(f"  Override: Class {override_class}")
        except Exception as e:
            if verbose:
                print(f"  Override skipped: {e}")

    # ── 3. Forward pass — substrate solver ──
    solver = SubstrateSolver(
        grid=grid, layers=layers, dx=1.0, dt=0.005,
        c_wave=1.0, gamma=0.05, lam=LAMBDA,
        epsilon=0.001, entangle=0.02,
        settle=SETTLE, measure=MEASURE, edge=10
    )

    result = solver.run(
        J_source, verbose=verbose,
        galaxy_name=galaxy_name, vmax_kms=vmax,
        use_crag=True, crag_kappa=KAPPA
    )

    # ── 4. Map to dimensional operators ──
    ops = map_solver_to_operators(result)
    OpT = ops["OpT"]
    OpC = ops["OpC"]
    R_7D = ops["R_7D"]
    phi_rms = ops["phi_rms"]
    coherence = ops["coherence"]

    # ── 5. Compute R_9to10 (NAVIGATION PRE-CHECK) ──
    R_9to10 = compute_R_9to10(OpT, OpC, R_7D, phi_rms,
                               coherence)
    gate_pass = R_9to10 >= THETA_9TO10

    # ── 6. Extract destination features ──
    features = extract_destination_features(result, galaxy)

    # ── 7. Lagrangian density diagnostic ──
    rho_layer0 = result["rho_avg"][0]
    sigma_layer0 = result["sigma_avg"][0]
    L_density = compute_lagrangian_density(
        sigma_layer0, sigma_layer0 * (1.0 - 0.005),
        J_source, 1.0, 0.005, LAMBDA, ALPHA)
    action_density = float(np.sum(L_density))
    L_mean = float(np.mean(L_density))
    L_std = float(np.std(L_density))

    # Stress-energy trace
    T_00 = compute_stress_energy_trace(
        sigma_layer0, 1.0, LAMBDA, ALPHA,
        sigma_layer0 * (1.0 - 0.005))
    energy_total = float(np.sum(T_00))
    energy_peak = float(np.max(T_00))

    # ── 8. Classify & recommend ──
    dest_class = classify_destination(result, v_max=vmax)
    profile = recommend_arrival_profile(dest_class, R_9to10,
                                         R_7D)

    # ── 9. Loss function ──
    loss_total, loss_field, loss_coh, loss_7d = compute_loss(
        R_9to10, R_7D, field_match=0.0)

    # ── 10. Go / No-Go decision ──
    go_nogo = "GO" if (gate_pass and R_7D > 0.5
                       and loss_total < 5.0) else "NO-GO"

    # ── 11. Confidence score ──
    # Based on gate margin, R_7D stability, mode purity
    gate_margin = max(0.0, R_9to10 - THETA_9TO10)
    confidence = min(1.0,
        0.4 * min(1.0, gate_margin / 0.2)
        + 0.3 * R_7D
        + 0.3 * features["mode_purity"])

    if verbose:
        print(f"\n  ── v22 REVERSE CALCULATION ──")
        print(f"  Destination class: {dest_class}")
        print(f"  OpT={OpT:.4f}  OpC={OpC:.4f}"
              f"  Delta_OP={ops['opacity_div']:.4f}")
        print(f"  R_7D={R_7D:.4f}  phi_rms={phi_rms:.6f}"
              f"  Coherence={coherence:.4f}")
        print(f"\n  R_9to10 = {R_9to10:.6f}"
              f"  (threshold={THETA_9TO10})"
              f"  {'PASS' if gate_pass else 'FAIL'}")
        print(f"\n  Loss: {loss_total:.4f}"
              f"  (field={loss_field:.4f}"
              f"  coh={loss_coh:.4f}"
              f"  7D={loss_7d:.4f})")
        print(f"\n  Lagrangian: S={action_density:.2e}"
              f"  <L>={L_mean:.2e}  std={L_std:.2e}")
        print(f"  T_00: total={energy_total:.2e}"
              f"  peak={energy_peak:.2e}")
        print(f"\n  Dominant mode: m={features['dominant_m']}"
              f"  purity={features['mode_purity']:.4f}")
        print(f"  Lambda gradient: {features['lambda_gradient']:.4f}")
        print(f"  Sigma width: {features['sigma_width']:.4f}")
        print(f"  Om sync: {features['om_sync']:.6f}")
        print(f"\n  Arrival profile: {profile}")
        print(f"  Confidence: {confidence:.4f}")
        print(f"  DECISION: {go_nogo}")

    return {
        "galaxy":           galaxy_name,
        "n_points":         len(r_kpc),
        "v_max_kms":        vmax,
        "override_class":   override_class,
        "dest_class":       dest_class,

        # Gate pre-check
        "OpT":              round(OpT, 6),
        "OpC":              round(OpC, 6),
        "opacity_div":      round(ops["opacity_div"], 6),
        "R_7D":             round(R_7D, 6),
        "phi_rms":          round(phi_rms, 8),
        "coherence":        round(coherence, 6),
        "R_9to10":          round(R_9to10, 6),
        "gate_pass":        gate_pass,

        # Loss
        "loss_total":       round(loss_total, 6),
        "loss_field":       round(loss_field, 6),
        "loss_coherence":   round(loss_coh, 6),
        "loss_7D":          round(loss_7d, 6),

        # Lagrangian diagnostics
        "action_density":   action_density,
        "L_mean":           L_mean,
        "L_std":            L_std,
        "T00_total":        energy_total,
        "T00_peak":         energy_peak,

        # Destination features
        "dominant_m":       features["dominant_m"],
        "mode_purity":      round(features["mode_purity"], 6),
        "lambda_gradient":  round(features["lambda_gradient"], 6),
        "sigma_width":      round(features["sigma_width"], 6),
        "om_sync":          round(features["om_sync"], 8),

        # Decision
        "arrival_profile":  profile,
        "confidence":       round(confidence, 4),
        "go_nogo":          go_nogo,

        # Solver diagnostics (carry forward)
        "cos_delta_phi":    result.get("cos_delta_phi"),
        "decoupling_ratio": result.get("decoupling_ratio"),
        "corr_radial_full": result.get("corr_radial_full"),
        "corr_radial_inner": result.get("corr_radial_inner"),
        "layer_coherence":  result.get("layer_coherence"),
        "elapsed_s":        round(result.get("elapsed", 0), 1),
    }


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v22 — Reverse Calculation Engine")
    parser.add_argument("--data-dir", type=str,
        default=os.path.join(SCRIPT_DIR, "data", "sparc_raw"),
        help="SPARC data directory")
    parser.add_argument("--output", type=str, default=None,
        help="Output JSON path")
    parser.add_argument("--quick", action="store_true",
        help="Quick mode: grid=128")
    args = parser.parse_args()

    grid = 128 if args.quick else GRID
    layers = LAYERS

    print("=" * 60)
    print("  BCM v22 — REVERSE CALCULATION ENGINE")
    print("  Stephen Justin Burdick Sr.")
    print("  Emerald Entities LLC — GIBUSH Systems")
    print("=" * 60)
    print(f"\n  The destination already exists in the pattern.")
    print(f"  Transit is alignment, not travel.")
    print(f"\n  Frozen constants:")
    print(f"    lambda={LAMBDA}  kappa={KAPPA}  grid={grid}"
          f"  layers={layers}")
    print(f"    THETA_9TO10={THETA_9TO10}"
          f"  K_BOUNDARY={K_BOUNDARY}")
    print(f"    Om_sync={OM_SYNC_FREQ}")
    print(f"    Loss weights: field={LOSS_FIELD_WEIGHT}"
          f"  coh={LOSS_COHERENCE_WEIGHT}"
          f"  7D={LOSS_7D_SURVIVAL_WEIGHT}")
    print(f"\n  BCM available: {_BCM_AVAILABLE}")
    print(f"  Overrides available: {_OVERRIDES_AVAILABLE}")
    print(f"  Data dir: {args.data_dir}")
    print(f"  Galaxies: {len(GALAXY_LIST)}")

    if not os.path.exists(args.data_dir):
        print(f"\n  ERROR: Data directory not found:"
              f" {args.data_dir}")
        sys.exit(1)

    # ── Run batch ──
    t_start = time.time()
    results = []
    skipped = []

    for filename in GALAXY_LIST:
        dat_path = find_dat_file(filename, args.data_dir)
        if dat_path is None:
            print(f"\n  NOT FOUND: {filename}")
            skipped.append(filename)
            continue
        try:
            r = process_galaxy(dat_path, grid, layers,
                               verbose=True)
            if r is not None:
                results.append(r)
        except Exception as e:
            print(f"\n  FAILED: {filename}: {e}")
            import traceback
            traceback.print_exc()
            skipped.append(filename)

    t_total = time.time() - t_start

    # ═══════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════

    print(f"\n{'='*60}")
    print(f"  v22 SUMMARY — {len(results)} destinations"
          f" in {t_total:.1f}s")
    print(f"{'='*60}")

    if skipped:
        print(f"  Skipped: {', '.join(skipped)}")

    if results:
        go_count = sum(1 for r in results
                       if r["go_nogo"] == "GO")
        nogo_count = sum(1 for r in results
                         if r["go_nogo"] == "NO-GO")

        print(f"\n  NAVIGATION PRE-CHECK:")
        print(f"    GO:    {go_count} / {len(results)}")
        print(f"    NO-GO: {nogo_count} / {len(results)}")

        # Gate statistics
        r_vals = [r["R_9to10"] for r in results]
        print(f"\n  R_9to10 STATISTICS:")
        print(f"    Min:    {min(r_vals):.6f}")
        print(f"    Max:    {max(r_vals):.6f}")
        print(f"    Mean:   {np.mean(r_vals):.6f}")
        print(f"    Median: {np.median(r_vals):.6f}")

        # Class distribution
        classes = {}
        for r in results:
            c = r["dest_class"]
            classes[c] = classes.get(c, 0) + 1
        print(f"\n  DESTINATION CLASSES:")
        for c in sorted(classes.keys()):
            print(f"    Class {c}: {classes[c]}")

        # Profile distribution
        profiles = {}
        for r in results:
            p = r["arrival_profile"]
            profiles[p] = profiles.get(p, 0) + 1
        print(f"\n  RECOMMENDED PROFILES:")
        for p in sorted(profiles.keys()):
            print(f"    {p}: {profiles[p]}")

        # Per-galaxy table
        print(f"\n  {'Galaxy':<16} {'Vmax':>5} {'Class':>6}"
              f" {'R_9to10':>8} {'R_7D':>6} {'Loss':>7}"
              f" {'Profile':>9} {'GO':>5}")
        print(f"  {'─'*16} {'─'*5} {'─'*6}"
              f" {'─'*8} {'─'*6} {'─'*7}"
              f" {'─'*9} {'─'*5}")
        for r in sorted(results,
                         key=lambda x: x["v_max_kms"]):
            print(f"  {r['galaxy']:<16} {r['v_max_kms']:>5.0f}"
                  f" {r['dest_class']:>6}"
                  f" {r['R_9to10']:>8.4f}"
                  f" {r['R_7D']:>6.4f}"
                  f" {r['loss_total']:>7.3f}"
                  f" {r['arrival_profile']:>9}"
                  f" {r['go_nogo']:>5}")

        # Failed pre-checks (if any)
        nogo_list = [r for r in results
                     if r["go_nogo"] == "NO-GO"]
        if nogo_list:
            print(f"\n  FAILED PRE-CHECKS:")
            for r in nogo_list:
                print(f"    {r['galaxy']}: R_9to10="
                      f"{r['R_9to10']:.4f}"
                      f"  R_7D={r['R_7D']:.4f}"
                      f"  loss={r['loss_total']:.3f}")

    # ═══════════════════════════════════════
    # SAVE JSON
    # ═══════════════════════════════════════

    out_path = args.output
    if out_path is None:
        out_dir = os.path.join(SCRIPT_DIR, "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir,
            f"BCM_v22_reverse_{time.strftime('%Y%m%d_%H%M%S')}.json")

    output = {
        "engine":     "BCM_v22_reverse_engine",
        "version":    "v22.0",
        "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_s":  t_total,
        "author":     "Stephen Justin Burdick Sr.",
        "entity":     "Emerald Entities LLC — GIBUSH Systems",
        "config": {
            "lambda":       LAMBDA,
            "kappa":        KAPPA,
            "alpha":        ALPHA,
            "grid":         grid,
            "layers":       layers,
            "settle":       SETTLE,
            "measure":      MEASURE,
            "THETA_9TO10":  THETA_9TO10,
            "K_BOUNDARY":   K_BOUNDARY,
            "Om_sync":      OM_SYNC_FREQ,
            "loss_weights": {
                "field":     LOSS_FIELD_WEIGHT,
                "coherence": LOSS_COHERENCE_WEIGHT,
                "7D":        LOSS_7D_SURVIVAL_WEIGHT,
            },
            "bcm_available":       _BCM_AVAILABLE,
            "overrides_available": _OVERRIDES_AVAILABLE,
        },
        "n_destinations": len(results),
        "n_skipped":      len(skipped),
        "skipped":        skipped,
        "summary": {
            "GO":    go_count if results else 0,
            "NO-GO": nogo_count if results else 0,
            "R_9to10_min":  float(min(r_vals)) if results else 0,
            "R_9to10_max":  float(max(r_vals)) if results else 0,
            "R_9to10_mean": float(np.mean(r_vals)) if results else 0,
            "classes":      classes if results else {},
            "profiles":     profiles if results else {},
        },
        "destinations": results,
    }

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n  Saved: {out_path}")
    print(f"\n  Done. {len(results)} destinations processed"
          f" in {t_total:.1f}s.")
    print(f"\n  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems — 2026")
    print(f"\n  The destination already exists in the pattern.")
    print(f"  The door works on both sides.")
