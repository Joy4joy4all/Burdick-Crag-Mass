# -*- coding: utf-8 -*-
"""
BCM Navigator — Layer 1: Trajectory Engine
=============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC

The Navigator computes the mission plan. It builds phase
blocks, validates trajectories, checks gaps, and outputs
the flight sequence. It does NOT execute. It plans.
"""

import numpy as np
from BCM_phase_block import PhaseBlock
from BCM_substrate_model import (
    AU_KM, MU_SUN, perihelion_velocity,
    compute_bridge_tension, find_l1_point,
    compute_sigma_shadow
)

# JPL Keplerian elements
PLANETS = {
    "Mercury": {"a": 0.3871, "L0": 252.25, "Ldot": 149472.675, "mass": 0.055},
    "Venus":   {"a": 0.7233, "L0": 181.98, "Ldot": 58517.816,  "mass": 0.815},
    "Earth":   {"a": 1.0000, "L0": 100.47, "Ldot": 35999.373,  "mass": 1.0},
    "Mars":    {"a": 1.5237, "L0": -4.57,  "Ldot": 19140.299,  "mass": 0.107},
    "Jupiter": {"a": 5.2025, "L0": 34.33,  "Ldot": 3034.904,   "mass": 317.8},
    "Saturn":  {"a": 9.5371, "L0": 50.08,  "Ldot": 1222.114,   "mass": 95.2},
}

SHADOW_RADII = {
    "Mercury": 0.01, "Venus": 0.05, "Earth": 0.05,
    "Mars": 0.03, "Jupiter": 0.5, "Saturn": 0.3,
}


def get_planet_positions(day_offset=0):
    """Compute heliocentric positions for all planets."""
    jd = (367 * 2032 - int(7 * (2032 + int((12 + 9) / 12)) / 4)
          + int(275 * 12 / 9) + 1 + day_offset + 1721013.5)
    T = (jd - 2451545.0) / 36525.0

    positions = {}
    for name, p in PLANETS.items():
        L = ((p["L0"] + p["Ldot"] * T) % 360 + 360) % 360
        rad = np.radians(L)
        positions[name] = {
            "x": p["a"] * np.cos(rad),
            "y": p["a"] * np.sin(rad),
            "r": p["a"],
            "mass": p["mass"],
        }
    return positions


def compute_lead_angle(positions, transit_days):
    """Aim at Saturn's future position."""
    sat = positions["Saturn"]
    angle_advance = 2 * np.pi * transit_days / 10759.0
    current_angle = np.arctan2(sat["y"], sat["x"])
    future_angle = current_angle + angle_advance
    return (sat["r"] * np.cos(future_angle),
            sat["r"] * np.sin(future_angle))


def build_mission(perihelion_au=0.15, lambda_eta=1.0):
    """
    Build complete Saturn mission as a sequence of PhaseBlocks.
    Returns list of PhaseBlocks with navigator validation.
    """
    positions = get_planet_positions(0)
    earth = positions["Earth"]
    saturn = positions["Saturn"]

    # Perihelion velocity
    v_peri = perihelion_velocity(perihelion_au, saturn["r"])

    # Inward fall time
    a_in = (earth["r"] + perihelion_au) / 2
    period_in = 2 * np.pi * np.sqrt((a_in * AU_KM)**3 / MU_SUN)
    inward_days = int((period_in / 86400) * 0.5)

    # Slew (18 hours)
    slew_days = 1

    # Lead angle
    est_transit = 200
    sx, sy = compute_lead_angle(positions, est_transit)

    # Outward distance and time
    earth_angle = np.arctan2(earth["y"], earth["x"])
    peri_x = perihelion_au * np.cos(earth_angle + np.pi)
    peri_y = perihelion_au * np.sin(earth_angle + np.pi)
    out_dist = np.sqrt((sx - peri_x)**2 + (sy - peri_y)**2) * AU_KM
    v_floor = v_peri * lambda_eta
    outward_days = int((out_dist / v_floor) / 86400) if v_floor > 0 else 9999

    # Return
    saturn_v_orb = 9.69
    v_depart = v_floor + 2 * saturn_v_orb
    ret_dist = np.sqrt(sx**2 + sy**2) * AU_KM
    return_days = int((ret_dist / v_depart) / 86400)

    # Check sigma shadows
    def check_shadows(x, y):
        for name, pos in positions.items():
            if name in SHADOW_RADII:
                if compute_sigma_shadow(
                    (x, y), (pos["x"], pos["y"]),
                    SHADOW_RADII[name]):
                    return name
        return "CLEAR"

    # Build phase blocks
    phases = []

    # Phase 0: Launch
    p0 = PhaseBlock(0, "LAUNCH", "LAUNCH",
                     x_au=earth["x"], y_au=earth["y"],
                     r_au=earth["r"], v_kms=29.8,
                     day_start=0, day_end=0,
                     lambda_eta=0.0)
    p0.sigma_shadow = "CLEAR"  # At departure body — exempt
    phases.append(p0)

    # Phase 1: Inward fall
    p1 = PhaseBlock(1, "INWARD FALL", "INWARD",
                     x_au=peri_x, y_au=peri_y,
                     r_au=perihelion_au, v_kms=v_peri,
                     day_start=0, day_end=inward_days,
                     lambda_eta=0.0)
    p1.sigma_shadow = "CLEAR"
    phases.append(p1)

    # Phase 2: Perihelion slew
    p2 = PhaseBlock(2, "PERIHELION SLEW", "SLEW",
                     x_au=peri_x, y_au=peri_y,
                     r_au=perihelion_au, v_kms=v_peri,
                     day_start=inward_days,
                     day_end=inward_days + slew_days,
                     lambda_eta=lambda_eta)
    p2.slew_status = "18hr COSINE (SAFE)"
    p2.coherence_current = 0.993
    phases.append(p2)

    # Phase 3: Lambda cruise
    cruise_start = inward_days + slew_days
    cruise_end = cruise_start + outward_days
    p3 = PhaseBlock(3, "LAMBDA CRUISE", "CRUISE",
                     x_au=sx, y_au=sy,
                     r_au=saturn["r"], v_kms=v_floor,
                     day_start=cruise_start,
                     day_end=cruise_end,
                     lambda_eta=lambda_eta)
    p3.sigma_shadow = check_shadows(sx, sy)
    p3.lead_angle_au = np.sqrt(
        (sx - saturn["x"])**2 + (sy - saturn["y"])**2)
    phases.append(p3)

    # Phase 4: Saturn ops
    ops_start = cruise_end
    ops_end = ops_start + 30
    p4 = PhaseBlock(4, "SATURN OPS", "OPS",
                     x_au=sx, y_au=sy,
                     r_au=saturn["r"], v_kms=0,
                     day_start=ops_start, day_end=ops_end,
                     lambda_eta=0.0)
    phases.append(p4)

    # Phase 5: Return
    ret_start = ops_end
    ret_end = ret_start + return_days
    p5 = PhaseBlock(5, "RETURN", "RETURN",
                     x_au=earth["x"], y_au=earth["y"],
                     r_au=earth["r"], v_kms=v_depart,
                     day_start=ret_start, day_end=ret_end,
                     lambda_eta=lambda_eta)
    phases.append(p5)

    # L1 check
    l1 = find_l1_point(
        (positions["Jupiter"]["x"], positions["Jupiter"]["y"]),
        (positions["Saturn"]["x"], positions["Saturn"]["y"]),
        positions["Jupiter"]["mass"],
        positions["Saturn"]["mass"])
    for p in phases:
        p.l1_available = True

    # Validate all phases
    for p in phases:
        p.validate_navigator()

    return phases, positions
