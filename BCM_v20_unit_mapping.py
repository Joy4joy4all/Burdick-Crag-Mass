# -*- coding: utf-8 -*-
"""
BCM v20 -- Physical Unit Mapping
===================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Maps every solver quantity from pixels/steps to SI units.
Two scale regimes:

GALACTIC SCALE (SPARC rotation curves):
  - Grid 256 covers galaxy disk
  - SPARC provides radii in kpc
  - dx_galactic derived from galaxy extent

CRAFT SCALE (interstellar transit):
  - CMB-locked dt = 1.25e-13 s/step (v17)
  - Probe cycle = 50 steps = 6.25e-12 s
  - dx_craft derived from c_wave scaling

TIME ANCHOR (both scales):
  dt_physical = 1.25e-13 s/step

This file does NOT modify any solver. It is a pure
translation layer that converts frozen constants and
test results to physical units.

Usage:
    python BCM_v20_unit_mapping.py
"""

import numpy as np
import json
import os
import time

# ============================================================
# FUNDAMENTAL ANCHORS
# ============================================================

# Time anchor: CMB-locked (v17, confirmed crew-safe)
DT_PHYSICAL = 1.25e-13  # seconds per solver step

# Speed of light
C_LIGHT = 2.998e8  # m/s

# Gravitational constant
G_NEWTON = 6.674e-11  # m^3 kg^-1 s^-2

# Solar mass
M_SUN = 1.989e30  # kg

# Parsec
PC = 3.086e16  # meters
KPC = 3.086e19  # meters


# ============================================================
# GALACTIC SCALE MAPPING
# ============================================================

def galactic_scale(grid=256, galaxy_radius_kpc=35.0):
    """
    Map solver grid to galactic physical scale.

    Uses SPARC rotation curve extents. NGC2841 extends
    to ~35 kpc in the SPARC dataset. Grid=256 covers
    the full diameter (2 * radius).

    Returns dict of scale factors.
    """
    galaxy_diameter_kpc = 2 * galaxy_radius_kpc
    galaxy_diameter_m = galaxy_diameter_kpc * KPC

    dx_galactic = galaxy_diameter_m / grid  # m per pixel
    dx_galactic_kpc = galaxy_diameter_kpc / grid

    # Solver dt for galactic runs
    # substrate_solver.py uses dt=0.005, but physical
    # time per step is the CMB anchor
    dt = DT_PHYSICAL

    # Solver c_wave = 1.0 in solver units
    # Physical: c_wave * dx / dt
    c_wave_physical = 1.0 * dx_galactic / dt  # m/s

    # Lambda (decay rate) in physical units
    # lambda has units of 1/time in the PDE
    # lambda_solver * (1/dt) = lambda_physical
    lambda_phys_per_s = 0.10 / dt  # baseline lambda=0.10

    return {
        "regime": "GALACTIC",
        "grid": grid,
        "galaxy_radius_kpc": galaxy_radius_kpc,
        "dx_m": dx_galactic,
        "dx_kpc": dx_galactic_kpc,
        "dt_s": dt,
        "c_wave_ms": c_wave_physical,
        "lambda_baseline_per_s": lambda_phys_per_s,
    }


# ============================================================
# CRAFT SCALE MAPPING
# ============================================================

def craft_scale(grid=256):
    """
    Map solver grid to craft physical scale.

    The craft operates on a much smaller grid than a galaxy.
    The physical scale is set by the requirement that the
    substrate wave speed c_wave is physically meaningful.

    From v13 SPINE: the substrate phase speed in void is
    approximately the speed at which lambda gradients produce
    drift. Burdick's Transport Law: v_drift = mu * grad(lambda).

    The craft grid represents the local substrate field
    around the ship — perhaps 1-100 AU scale for
    interstellar navigation.

    Anchor: c_wave = 1.0 px/step (solver)
    Physical c_wave must be subluminal for substrate waves.
    Using c_wave_physical ~ 0.01 * c_light (neutrino-substrate
    coupling speed) gives the spatial scale.
    """
    dt = DT_PHYSICAL

    # Substrate wave speed: superluminal in 2D substrate
    # 2D phase velocity not bound by 3D light cone.
    # 800c baseline from independent source, bracketed
    # by CMB-locked solver output.
    c_substrate = 12000.0 * C_LIGHT  # m/s

    # dx = c_substrate * dt / c_wave_solver
    # c_wave_solver = 1.0
    dx_craft = c_substrate * dt  # m per pixel

    # Craft field extent
    field_extent_m = grid * dx_craft
    field_extent_au = field_extent_m / 1.496e11  # AU

    # Probe cycle in physical time
    probe_cycle_s = 50 * dt

    # Separation (15 px in solver)
    separation_m = 15.0 * dx_craft

    return {
        "regime": "CRAFT",
        "grid": grid,
        "dx_m": dx_craft,
        "dx_au": dx_craft / 1.496e11,
        "dt_s": dt,
        "c_substrate_ms": c_substrate,
        "field_extent_m": field_extent_m,
        "field_extent_au": field_extent_au,
        "probe_cycle_s": probe_cycle_s,
        "pump_separation_m": separation_m,
    }


# ============================================================
# FROZEN CONSTANTS IN PHYSICAL UNITS
# ============================================================

def frozen_constants_physical(craft):
    """
    Convert all frozen constants to physical units.
    """
    dt = craft["dt_s"]
    dx = craft["dx_m"]

    # kappa_drain = 0.35 (dimensionless fraction per cycle)
    # Already dimensionless — fraction of payload bled
    kappa_drain = 0.35
    kappa_drain_unit = "dimensionless (fraction per deposit)"

    # chi_decay_rate = 0.997 per step
    # Physical decay time: tau = -dt / ln(0.997)
    chi_decay_tau = -dt / np.log(0.997)
    chi_halflife = chi_decay_tau * np.log(2)

    # chi_c = 0.002582 (solver units)
    # chi_op has units of phi * grad(Xi) / dx^3
    # In physical units: needs field amplitude calibration
    chi_c_solver = 0.002582

    # alpha = 0.80 (dimensionless memory coefficient)
    alpha = 0.80
    alpha_unit = "dimensionless (memory retention per step)"

    # Probe cycle = 50 steps
    probe_cycle_s = 50 * dt
    probe_freq_hz = 1.0 / probe_cycle_s

    # f/2 heartbeat
    heartbeat_s = 100 * dt  # f/2 = half the probe frequency
    heartbeat_hz = 1.0 / heartbeat_s

    # Pump frequency = 1/5 steps
    pump_freq_hz = 1.0 / (5 * dt)

    # Hemorrhage threshold: BruceRMS = 0.012
    # Maps to acceleration via substrate coupling
    bruce_threshold = 0.012

    # GREEN corridor: lambda [0.02, 0.08] in solver units
    # Physical: lambda / dt
    green_low_per_s = 0.02 / dt
    green_high_per_s = 0.08 / dt

    return {
        "kappa_drain": {
            "value": kappa_drain,
            "unit": kappa_drain_unit,
        },
        "chi_decay_rate": {
            "value": 0.997,
            "unit": "per step",
            "tau_s": chi_decay_tau,
            "halflife_s": chi_halflife,
        },
        "chi_c": {
            "value_solver": chi_c_solver,
            "note": "Requires field amplitude calibration "
                    "for SI conversion",
        },
        "alpha": {
            "value": alpha,
            "unit": alpha_unit,
        },
        "probe_cycle": {
            "steps": 50,
            "period_s": probe_cycle_s,
            "frequency_hz": probe_freq_hz,
        },
        "heartbeat_f2": {
            "steps": 100,
            "period_s": heartbeat_s,
            "frequency_hz": heartbeat_hz,
        },
        "pump_frequency": {
            "steps": 5,
            "period_s": 5 * dt,
            "frequency_hz": pump_freq_hz,
        },
        "bruce_hemorrhage_threshold": {
            "value_solver": bruce_threshold,
            "note": "Acceleration mapping requires "
                    "substrate-to-inertia coupling factor",
        },
        "green_corridor": {
            "lambda_low_solver": 0.02,
            "lambda_high_solver": 0.08,
            "decay_rate_low_per_s": green_low_per_s,
            "decay_rate_high_per_s": green_high_per_s,
        },
    }


# ============================================================
# CORRIDOR FLIGHT METRICS IN PHYSICAL UNITS
# ============================================================

def flight_metrics_physical(craft):
    """
    Convert v19 corridor flight results to physical units.
    """
    dt = craft["dt_s"]
    dx = craft["dx_m"]

    # Flight duration
    flight_steps = 20000
    flight_s = flight_steps * dt
    flight_hours = flight_s / 3600

    # Total bled (3122.52 solver units)
    # Sigma has units of field amplitude — needs mass
    # calibration for kg conversion
    total_bled_solver = 3122.52

    # System total (1088.55 solver units)
    system_total_solver = 1088.55

    # Max BruceRMS
    max_bruce = 0.00665

    # Phi RMS (heartbeat)
    phi_rms = 0.00142

    return {
        "flight_duration": {
            "steps": flight_steps,
            "seconds": flight_s,
            "hours": flight_hours,
            "note": "At CMB-locked dt, 20k steps is "
                    "extremely short in human time. "
                    "Physical transit requires ~10^18+ "
                    "steps for interstellar distances.",
        },
        "total_bled_solver": total_bled_solver,
        "system_total_solver": system_total_solver,
        "max_bruce_rms": max_bruce,
        "phi_rms_heartbeat": phi_rms,
    }


# ============================================================
# BIOLOGICAL HARM BAND CHECK (physical)
# ============================================================

def biological_check(craft):
    """
    Verify all craft frequencies are clear of biological
    harm bands. From v17.
    """
    dt = craft["dt_s"]

    bands = {
        "vestibular": (0.5, 3.0),
        "organ_resonance": (4.0, 8.0),
        "spinal": (8.0, 12.0),
        "head_neck": (15.0, 20.0),
        "eyeball": (20.0, 80.0),
        "cellular_membrane": (100.0, 200.0),
    }

    # Craft frequencies in Hz
    f_probe = 1.0 / (50 * dt)
    f_pump = 1.0 / (5 * dt)
    f_heartbeat = 1.0 / (100 * dt)

    craft_freqs = {
        "probe_fundamental": f_probe,
        "pump_mode": f_pump,
        "heartbeat_f2": f_heartbeat,
    }

    results = {}
    all_clear = True
    for fname, fval in craft_freqs.items():
        status = "CLEAR"
        for bname, (blow, bhigh) in bands.items():
            if blow <= fval <= bhigh:
                status = f"*** VIOLATION: {bname} ***"
                all_clear = False
                break
        results[fname] = {
            "frequency_hz": fval,
            "status": status,
        }

    return {
        "frequencies": results,
        "all_clear": all_clear,
        "harm_bands": bands,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"\n{'='*65}")
    print(f"  BCM v20 -- PHYSICAL UNIT MAPPING")
    print(f"  Pixels to meters. Steps to seconds.")
    print(f"  The spec sheet.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")

    # ---- TIME ANCHOR ----
    print(f"\n  TIME ANCHOR")
    print(f"  {'─'*50}")
    print(f"  dt = {DT_PHYSICAL:.2e} s/step (CMB-locked)")
    print(f"  Probe cycle = 50 steps = "
          f"{50*DT_PHYSICAL:.2e} s")
    print(f"  f/2 heartbeat = 100 steps = "
          f"{100*DT_PHYSICAL:.2e} s")

    # ---- GALACTIC SCALE ----
    print(f"\n  GALACTIC SCALE")
    print(f"  {'─'*50}")
    gal = galactic_scale()
    print(f"  Galaxy: NGC2841-class (~{gal['galaxy_radius_kpc']} kpc)")
    print(f"  Grid: {gal['grid']}x{gal['grid']}")
    print(f"  dx = {gal['dx_m']:.3e} m "
          f"({gal['dx_kpc']:.4f} kpc)")
    print(f"  c_wave = {gal['c_wave_ms']:.3e} m/s "
          f"({gal['c_wave_ms']/C_LIGHT:.2e} c)")
    print(f"  lambda_baseline = {gal['lambda_baseline_per_s']:.3e} /s")

    # ---- CRAFT SCALE ----
    print(f"\n  CRAFT SCALE")
    print(f"  {'─'*50}")
    craft = craft_scale()
    print(f"  c_substrate = {craft['c_substrate_ms']:.3e} m/s "
          f"({craft['c_substrate_ms']/C_LIGHT:.4f} c)")
    print(f"  dx = {craft['dx_m']:.3e} m")
    print(f"  Field extent = {craft['field_extent_m']:.3e} m "
          f"({craft['field_extent_au']:.4f} AU)")
    print(f"  Probe cycle = {craft['probe_cycle_s']:.3e} s")
    print(f"  Pump separation = {craft['pump_separation_m']:.3e} m")

    # ---- FROZEN CONSTANTS ----
    print(f"\n  FROZEN CONSTANTS (PHYSICAL)")
    print(f"  {'─'*50}")
    fc = frozen_constants_physical(craft)

    print(f"  kappa_drain = {fc['kappa_drain']['value']} "
          f"({fc['kappa_drain']['unit']})")
    print(f"  chi_decay tau = {fc['chi_decay_rate']['tau_s']:.3e} s")
    print(f"  chi_decay halflife = "
          f"{fc['chi_decay_rate']['halflife_s']:.3e} s")
    print(f"  alpha = {fc['alpha']['value']} "
          f"({fc['alpha']['unit']})")

    print(f"\n  Probe: {fc['probe_cycle']['period_s']:.3e} s "
          f"({fc['probe_cycle']['frequency_hz']:.3e} Hz)")
    print(f"  Heartbeat: {fc['heartbeat_f2']['period_s']:.3e} s "
          f"({fc['heartbeat_f2']['frequency_hz']:.3e} Hz)")
    print(f"  Pump: {fc['pump_frequency']['period_s']:.3e} s "
          f"({fc['pump_frequency']['frequency_hz']:.3e} Hz)")

    print(f"\n  GREEN corridor (physical decay rates):")
    print(f"    Low:  {fc['green_corridor']['decay_rate_low_per_s']:.3e} /s")
    print(f"    High: {fc['green_corridor']['decay_rate_high_per_s']:.3e} /s")

    # ---- BIOLOGICAL CHECK ----
    print(f"\n  BIOLOGICAL HARM BAND CHECK")
    print(f"  {'─'*50}")
    bio = biological_check(craft)
    for fname, fdata in bio["frequencies"].items():
        print(f"  {fname:>20}: "
              f"{fdata['frequency_hz']:.3e} Hz "
              f"[{fdata['status']}]")
    if bio["all_clear"]:
        print(f"\n  ALL FREQUENCIES CLEAR OF BIOLOGICAL BANDS")
    else:
        print(f"\n  *** BIOLOGICAL VIOLATION DETECTED ***")

    # ---- FLIGHT METRICS ----
    print(f"\n  CORRIDOR FLIGHT (PHYSICAL)")
    print(f"  {'─'*50}")
    fm = flight_metrics_physical(craft)
    print(f"  Duration: {fm['flight_duration']['steps']} steps "
          f"= {fm['flight_duration']['seconds']:.3e} s")
    print(f"  Note: {fm['flight_duration']['note']}")

    # ---- SCALE INVARIANCE ----
    print(f"\n  SCALE INVARIANCE CHECK")
    print(f"  {'─'*50}")
    ratio = gal["dx_m"] / craft["dx_m"]
    print(f"  Galactic dx / Craft dx = {ratio:.3e}")
    print(f"  (12+ orders of magnitude separation)")
    print(f"  Same solver, same constants, same physics.")
    print(f"  lambda_stellar/lambda_galactic = 0.977 (v4)")

    # ---- OPEN CALIBRATIONS ----
    print(f"\n  OPEN CALIBRATIONS (require external data)")
    print(f"  {'─'*50}")
    print(f"  1. c_substrate: assumed 0.01c. Refineable with")
    print(f"     IceCube neutrino propagation measurements.")
    print(f"  2. sigma -> kg: field amplitude to mass requires")
    print(f"     SPARC M/L ratio calibration at known radius.")
    print(f"  3. BruceRMS -> acceleration: requires substrate-")
    print(f"     to-inertia coupling factor from SMSD benchtop")
    print(f"     test (v5, $225 Taylor-Couette cell).")
    print(f"  4. chi_c in SI: requires field amplitude in SI")
    print(f"     (depends on calibration #2).")

    print(f"\n{'='*65}")

    # ---- SAVE ----
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v20_unit_mapping_"
        f"{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v20 Physical Unit Mapping",
        "author": ("Stephen Justin Burdick Sr. -- "
                    "Emerald Entities LLC"),
        "purpose": "Map solver units to SI. The spec sheet.",
        "time_anchor": {
            "dt_s": DT_PHYSICAL,
            "source": "CMB-locked (v17)",
            "crew_safe": True,
        },
        "galactic_scale": gal,
        "craft_scale": craft,
        "frozen_constants_physical": fc,
        "biological_check": bio,
        "flight_metrics": fm,
        "open_calibrations": [
            "c_substrate (assumed 0.01c)",
            "sigma to kg (M/L calibration)",
            "BruceRMS to acceleration (SMSD test)",
            "chi_c in SI (depends on sigma calibration)",
        ],
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
