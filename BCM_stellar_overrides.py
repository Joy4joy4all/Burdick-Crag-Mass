# -*- coding: utf-8 -*-
"""
BCM Stellar Overrides — Binary Coupling System
===============================================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
Emerald Entities LLC — GIBUSH Systems

Binary pair definitions and dual-pump source field builder for the
BCM stellar substrate solver. Mirrors the architecture of
BCM_Substrate_overrides.py at galactic scale.

Architecture:
    BCM_stellar_registry.json → individual stars, physical parameters
    BCM_stellar_overrides.py  → binary coupling: pairs, separation,
                                eccentricity, synchronization, source builder

The registry stays clean — single stars with tachocline parameters.
The overrides define the relationship between them.
A star can exist in the registry without being in a pair.
A pair can't exist without both stars being in the registry.

Physics:
    Each star is a substrate pump. In a binary, their fields overlap.
    The override builds a dual-pump source field J(x,y) on a single grid.
    The solver runs on that combined field. The delta_phi(x,y) spatial
    field shows the coupling structure between the two pumps.

    H_tidal(m) = (v_A + v_tidal - Omega*R_tach/m)^2
    v_tidal = Omega_orb * R_tach / 2  — companion clock signal at m=2

Usage:
    from BCM_stellar_overrides import build_binary_source, BINARY_REGISTRY
    pair = BINARY_REGISTRY["Alpha_Cen"]
    J, info = build_binary_source(pair, grid=256, registry=stellar_registry)
    solver.run(J, ...)
"""

import numpy as np
import os
import json


# ─────────────────────────────────────────
# BINARY PAIR REGISTRY
# Maps system name → component stars + orbital parameters
# All parameters from published observations — not fitted
# ─────────────────────────────────────────

BINARY_REGISTRY = {

    # ── Alpha Centauri A+B ──
    # Solar twin + K dwarf. Mode-matched (both m=4 observed).
    # Substrate bridge target. Binary habitability test case.
    "Alpha_Cen": {
        "description":      "Solar twin + K dwarf binary. Substrate bridge target.",
        "star_A":           "Alpha_Cen_A",
        "star_B":           "Alpha_Cen_B",
        "P_orbital_days":   29157.5,        # 79.762 years
        "eccentricity":     0.5179,
        "a_semimajor_AU":   23.4,           # semi-major axis
        "periastron_AU":    11.2,           # closest approach (Sun-Saturn distance)
        "apastron_AU":      35.6,           # farthest (Sun-Pluto distance)
        "synchronized":     False,          # NOT tidally locked
        "m_A_observed":     4,
        "m_B_observed":     4,
        "mode_matched":     True,
        "bcm_class":        "Class I — Mode-Matched Bridge",
        "notes":            "Both stars m=4. GCD=4. Coherent substrate bridge predicted. "
                            "Binary habitability metric test case. Proxima Cen (m=1) is "
                            "gravitationally bound third body at ~13000 AU.",
        "citations": {
            "orbital": "Pourbaix & Boffin 2016 — revised dynamical masses",
            "separation": "Kervella et al. 2016 — interferometric orbit",
        },
    },

    # ── HR 1099 (V711 Tau) ──
    # RS CVn binary. Tidally synchronized. Stellar Class VI.
    # First binary solved by tidal Hamiltonian (m_alfven=12 → m_tidal=2).
    "HR_1099": {
        "description":      "RS CVn binary. Tidally synchronized Class VI.",
        "star_A":           "HR_1099",
        "star_B":           None,           # G5V secondary not in registry yet
        "star_B_proxy": {
            "spectral_type":    "G5V",
            "mass_solar":       1.0,
            "radius_km":        650000.0,
            "rotation_days":    2.84,       # synchronized
        },
        "P_orbital_days":   2.84,
        "eccentricity":     0.0,            # circular orbit (synchronized)
        "a_semimajor_AU":   0.05,           # very close binary
        "synchronized":     True,
        "m_A_observed":     2,
        "bcm_class":        "Class VI — Tidal Bar Channel",
        "notes":            "Tidal Hamiltonian confirmed: m_alfven=12 → m_tidal=2 → "
                            "MATCH. Companion's m=2 tidal field imposes persistent "
                            "boundary condition. First stellar Class VI solved.",
        "citations": {
            "orbital": "Fekel 1983, ApJ 268",
            "active_long": "Berdyugina & Tuominen 1998, A&A 336",
        },
    },

    # ── Spica (Alpha Virginis) ──
    # Massive B-type binary. Non-synchronized. High-energy coupling.
    # Z-layer pump — standard Alfven Hamiltonian does not apply.
    "Spica": {
        "description":      "Massive B-type binary. Z-layer pump. Non-synchronized.",
        "star_A":           "Spica_A",
        "star_B":           "Spica_B",
        "P_orbital_days":   4.014,
        "eccentricity":     0.13,
        "a_semimajor_AU":   0.12,
        "synchronized":     False,          # P_rot_A=2.29d ≠ P_orb=4.014d
        "m_A_observed":     0,
        "m_B_observed":     0,
        "mode_matched":     False,          # unknown — both m_obs=0
        "bcm_class":        "Class IV — High-Energy Non-Synchronous",
        "notes":            "Non-synchronous: P_rot_A=2.29d ≠ P_orb=4.014d. "
                            "Eccentric orbit (e=0.13) creates time-variable substrate "
                            "coupling — analog to variable SMBH torque at galactic scale. "
                            "Z-layer pump — standard Alfven Hamiltonian does not apply. "
                            "Tidal Hamiltonian predicts m=4 for Spica A (untested).",
        "citations": {
            "orbital": "Herbison-Evans et al. 1971, MNRAS 151",
            "pulsation": "Shobbrook et al. 1969 — Beta Cephei classification",
        },
    },
}


# ─────────────────────────────────────────
# SOURCE FIELD BUILDERS
# ─────────────────────────────────────────

def _gaussian_pump(grid, cx, cy, amplitude, sigma_frac=0.08):
    """Single stellar pump as gaussian source on the grid."""
    sigma = grid * sigma_frac
    iy, ix = np.mgrid[0:grid, 0:grid]
    r2 = (ix - cx)**2 + (iy - cy)**2
    return amplitude * np.exp(-r2 / (2 * sigma**2))


def _stellar_amplitude(star_params):
    """
    Compute pump amplitude from tachocline induction current.
    J_ind = sigma * v_conv * B — same as BCM_stellar_wave.py
    Normalized to [0, 10] range for solver stability.
    """
    sigma = star_params.get("sigma_tach_sm", 1.0e4)
    v_conv = star_params.get("v_conv_ms", 300.0)
    B = star_params.get("B_tachocline_T", 1.0)
    J_ind = sigma * v_conv * B

    # Normalize: Sun J_ind ~ 1.68e7 → amplitude 8.0
    J_sun = 1.0e4 * 300.0 * 5.6  # 1.68e7
    amp = 8.0 * (J_ind / J_sun) if J_sun > 0 else 8.0
    return max(1.0, min(amp, 20.0))  # clamp to reasonable range


def build_binary_source(pair_config, grid=128, registry=None,
                         orbital_phase=0.5,
                         amp_A_override=None, amp_B_override=None,
                         corridor_width_frac=None):
    """
    Build dual-pump source field J(x,y) for a binary star system.

    Parameters:
        pair_config:    dict from BINARY_REGISTRY
        grid:           solver grid size
        registry:       dict of star parameters (from BCM_stellar_registry.json)
        orbital_phase:  0.0 = periastron, 0.5 = mean separation, 1.0 = apastron
        amp_A_override: force pump A amplitude (bypasses tachocline calc)
        amp_B_override: force pump B amplitude (bypasses tachocline calc)
        corridor_width_frac: override corridor width fraction (default 0.06)

    Returns:
        J:      2D source field (grid x grid)
        info:   dict with pump locations, amplitudes, L1 coordinates
    """
    # ── Get star parameters ──
    star_A_name = pair_config["star_A"]
    star_B_name = pair_config.get("star_B")

    if registry is None:
        registry = _load_registry()

    star_A = registry.get(star_A_name, {})
    if star_B_name and star_B_name in registry:
        star_B = registry[star_B_name]
    elif "star_B_proxy" in pair_config:
        star_B = pair_config["star_B_proxy"]
    else:
        star_B = star_A.copy()  # self-symmetric fallback

    # ── Compute amplitudes from tachocline induction ──
    amp_A = _stellar_amplitude(star_A)
    amp_B = _stellar_amplitude(star_B)
    if amp_A_override is not None:
        amp_A = float(amp_A_override)
    if amp_B_override is not None:
        amp_B = float(amp_B_override)

    # ── Compute separation on grid ──
    # Scale: separation_frac = fraction of grid between pumps
    # Use periastron/apastron interpolated by orbital_phase
    peri = pair_config.get("periastron_AU",
                           pair_config.get("a_semimajor_AU", 1.0) *
                           (1 - pair_config.get("eccentricity", 0.0)))
    apo = pair_config.get("apastron_AU",
                          pair_config.get("a_semimajor_AU", 1.0) *
                          (1 + pair_config.get("eccentricity", 0.0)))
    sep_AU = peri + (apo - peri) * orbital_phase
    # Map to grid: max separation = 60% of grid
    a_max = max(peri, apo)
    sep_frac = 0.6 * (sep_AU / a_max) if a_max > 0 else 0.3
    sep_frac = max(0.15, min(sep_frac, 0.7))

    # ── Place pumps ──
    cx, cy = grid // 2, grid // 2
    sep_px = int(grid * sep_frac / 2)
    pump_A = (cx - sep_px, cy)
    pump_B = (cx + sep_px, cy)

    # ── Build combined source ──
    J_A = _gaussian_pump(grid, pump_A[0], pump_A[1], amp_A)
    J_B = _gaussian_pump(grid, pump_B[0], pump_B[1], amp_B)
    J = J_A + J_B

    # ── L1 point (center of mass weighted) ──
    m_A = star_A.get("mass_solar", 1.0)
    m_B = star_B.get("mass_solar", 1.0)
    q = m_B / (m_A + m_B) if (m_A + m_B) > 0 else 0.5
    l1_x = pump_A[0] + int((pump_B[0] - pump_A[0]) * (1 - q * 0.5))
    l1_y = cy

    # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
    # L1 coupling corridor — the substrate bridge channel
    cwf = corridor_width_frac if corridor_width_frac is not None else 0.06
    iy, ix = np.mgrid[0:grid, 0:grid]
    dx_ab = pump_B[0] - pump_A[0]
    dy_ab = pump_B[1] - pump_A[1]
    bridge_len = np.sqrt(dx_ab**2 + dy_ab**2)
    if bridge_len > 0:
        bx_hat = dx_ab / bridge_len
        by_hat = dy_ab / bridge_len
        px = ix - pump_A[0]
        py = iy - pump_A[1]
        along = px * bx_hat + py * by_hat
        perp = -px * by_hat + py * bx_hat
        t = along / bridge_len
        in_corridor = (t > 0.1) & (t < 0.9)
        taper = 1.0 - 0.6 * np.exp(-((t - 0.5)**2) / 0.08)
        corridor_width = grid * cwf * taper
        corridor_amp = min(amp_A, amp_B) * 0.4
        corridor_profile = np.exp(-perp**2 / (2 * corridor_width**2 + 1e-9))
        along_profile = np.exp(-((t - 0.5)**2) / 0.18) * 0.3 + 0.7
        J_corridor = corridor_amp * corridor_profile * along_profile
        J_corridor[~in_corridor] = 0.0
        J += J_corridor

        # L1 heatsink
        l1_r = np.sqrt((ix - l1_x)**2 + (iy - l1_y)**2)
        l1_sigma = grid * 0.03
        l1_amp = min(amp_A, amp_B) * 0.2
        J_l1 = l1_amp * np.exp(-l1_r**2 / (2 * l1_sigma**2))
        J += J_l1
    # === END ADDITION ===

    info = {
        "star_A":       star_A_name,
        "star_B":       star_B_name or "proxy",
        "amp_A":        round(amp_A, 2),
        "amp_B":        round(amp_B, 2),
        "pump_A":       pump_A,
        "pump_B":       pump_B,
        "L1":           (l1_x, l1_y),
        "sep_frac":     round(sep_frac, 3),
        "sep_AU":       round(sep_AU, 2),
        "orbital_phase": orbital_phase,
        "grid":         grid,
        "eccentricity": pair_config.get("eccentricity", 0.0),
        "synchronized": pair_config.get("synchronized", False),
        "bcm_class":    pair_config.get("bcm_class", "unknown"),
        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Alfvén physics per star for resonance ring rendering
        "m_pred_A":     star_A.get("m_observed", 4),
        "m_pred_B":     star_B.get("m_observed", 4) if isinstance(star_B, dict) else 4,
        "corridor_width_frac": cwf,
        # === END ADDITION ===
    }

    print(f"  [BCM] Binary source: {star_A_name} + {star_B_name or 'proxy'}")
    print(f"    amp_A={amp_A:.1f}  amp_B={amp_B:.1f}  sep={sep_frac:.2f}  "
          f"phase={orbital_phase:.2f}")
    print(f"    L1=({l1_x},{l1_y})  class={pair_config.get('bcm_class','')}")

    return J, info


def run_binary(pair_name, grid=128, orbital_phase=0.5,
               settle=15000, measure=5000, verbose=True, callback=None):
    """
    Run full binary substrate solver and return results with phase field.

    Parameters:
        pair_name:      key from BINARY_REGISTRY
        grid:           solver grid size
        orbital_phase:  0.0=periastron, 0.5=mean, 1.0=apastron
        settle:         solver settle steps
        measure:        solver measurement steps
        callback:       optional callback(step, total, rho, sigma) for live view

    Returns:
        result:     solver output including delta_phi_field
        J:          source field used
        info:       binary configuration info
    """
    from core.substrate_solver import SubstrateSolver

    if pair_name not in BINARY_REGISTRY:
        raise ValueError(f"Binary '{pair_name}' not in registry. "
                         f"Available: {list(BINARY_REGISTRY.keys())}")

    pair = BINARY_REGISTRY[pair_name]
    J, info = build_binary_source(pair, grid=grid,
                                   orbital_phase=orbital_phase)

    solver = SubstrateSolver(grid=grid, layers=6, lam=0.1,
                              settle=settle, measure=measure)
    result = solver.run(J, verbose=verbose, callback=callback)

    # ── L1 region diagnostics ──
    l1x, l1y = info["L1"]
    r = min(8, grid // 16)
    dpf = result.get("delta_phi_field")
    cpf = result.get("cos_delta_phi_field")

    if dpf is not None:
        l1_region = cpf[max(0,l1y-r):l1y+r, max(0,l1x-r):l1x+r]
        l1_active = l1_region[l1_region > 0]
        grad_y, grad_x = np.gradient(dpf)
        curl = np.gradient(grad_y, axis=1) - np.gradient(grad_x, axis=0)
        l1_curl = curl[max(0,l1y-r):l1y+r, max(0,l1x-r):l1x+r]

        info["L1_cos_mean"] = float(np.mean(l1_active)) if len(l1_active) > 0 else 0.0
        info["L1_cos_std"] = float(np.std(l1_active)) if len(l1_active) > 0 else 0.0
        info["L1_curl_max"] = float(np.max(np.abs(l1_curl)))
        info["L1_curl_mean"] = float(np.mean(np.abs(l1_curl)))

        if verbose:
            print(f"\n  [BCM] BINARY DIAGNOSTICS — {pair_name}")
            print(f"    L1 cos(Δφ) mean: {info['L1_cos_mean']:+.4f}")
            print(f"    L1 cos(Δφ) std:  {info['L1_cos_std']:.4f}")
            print(f"    L1 curl max:     {info['L1_curl_max']:.6f}")
            if info['L1_curl_max'] > 0.001:
                print(f"    >>> SUBSTRATE POOLING detected at L1")
            else:
                print(f"    >>> Laminar bridge (no vorticity)")

    return result, J, info


def list_binaries():
    """Print all registered binary pairs."""
    print(f"\n{'='*65}")
    print(f"  BCM BINARY PAIR REGISTRY")
    print(f"{'='*65}")
    for name, pair in BINARY_REGISTRY.items():
        sync = "SYNC" if pair.get("synchronized") else "ASYNC"
        star_b = pair.get("star_B") or "proxy"
        print(f"  {name:<16} {pair['star_A']:<14} + {star_b:<14} "
              f"P={pair['P_orbital_days']:.2f}d  e={pair.get('eccentricity',0):.3f}  "
              f"{sync}")
        print(f"    {pair.get('bcm_class', '')}")
    print(f"{'='*65}\n")


def _load_registry():
    """Load stellar registry JSON."""
    base = os.path.dirname(os.path.abspath(__file__))
    reg_path = os.path.join(base, "data", "results",
                             "BCM_stellar_registry.json")
    if os.path.exists(reg_path):
        with open(reg_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stars", {})
    return {}


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    list_binaries()
