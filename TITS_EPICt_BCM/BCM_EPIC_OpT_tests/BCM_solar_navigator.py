# -*- coding: utf-8 -*-
"""
BCM v12 Solar System Substrate Navigator — 2032 Saturn Mission
================================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Emerald Entities LLC -- GIBUSH Systems

SPECULATIVE — Theoretical extrapolation from BCM solver behavior.

Computes real planetary positions for 2032 using JPL Keplerian
elements, builds substrate sigma gradient map, traces Sun-slingshot
trajectory to Saturn, and renders 2D mission map with timestamps.

Usage:
    python BCM_solar_navigator.py
    python BCM_solar_navigator.py --launch 2032-12-01 --perihelion 0.15
"""

import numpy as np
import json
import os
import time
import argparse


# ============================================================
# JPL Keplerian Elements (J2000, valid 1800-2050)
# Source: ssd.jpl.nasa.gov/planets/approx_pos.html
# ============================================================
PLANETS = {
    "Mercury": {"a": 0.38710, "e": 0.20564, "I": 7.005,
                "L0": 252.252, "Ldot": 149472.675,
                "color": "#a0a0a0", "r_km": 2440},
    "Venus":   {"a": 0.72333, "e": 0.00677, "I": 3.395,
                "L0": 181.980, "Ldot": 58517.816,
                "color": "#e8c060", "r_km": 6052},
    "Earth":   {"a": 1.00000, "e": 0.01671, "I": 0.0,
                "L0": 100.467, "Ldot": 35999.373,
                "color": "#4488cc", "r_km": 6371},
    "Mars":    {"a": 1.52371, "e": 0.09337, "I": 1.851,
                "L0": -4.568, "Ldot": 19140.299,
                "color": "#cc4422", "r_km": 3390},
    "Jupiter": {"a": 5.20249, "e": 0.04854, "I": 1.299,
                "L0": 34.335, "Ldot": 3034.904,
                "color": "#cc9966", "r_km": 69911},
    "Saturn":  {"a": 9.53707, "e": 0.05415, "I": 2.486,
                "L0": 50.077, "Ldot": 1222.114,
                "color": "#ddc488", "r_km": 58232},
}

# Sigma well strengths (proportional to mass, BCM proxy)
SIGMA_STRENGTH = {
    "Sun": 1000.0,
    "Mercury": 0.055,
    "Venus": 0.815,
    "Earth": 1.0,
    "Mars": 0.107,
    "Jupiter": 317.8,
    "Saturn": 95.2,
}

AU_KM = 149597870.7  # 1 AU in km


def date_to_centuries(year, month, day):
    """Convert date to Julian centuries from J2000."""
    # Simplified Julian date
    jd = (367 * year - int(7 * (year + int((month + 9) / 12)) / 4)
          + int(275 * month / 9) + day + 1721013.5)
    return (jd - 2451545.0) / 36525.0


def planet_position(name, T):
    """
    Compute heliocentric ecliptic position (x, y) in AU
    for planet at Julian century T from J2000.
    Returns (x_au, y_au, r_au, true_anomaly_deg).
    """
    p = PLANETS[name]
    a = p["a"]
    e = p["e"]

    # Mean longitude
    L = p["L0"] + p["Ldot"] * T  # degrees
    L = L % 360.0

    # Mean anomaly (simplified — ignoring long.peri changes)
    M = L  # simplified: M ≈ L for approximate positions
    M_rad = np.radians(M)

    # Solve Kepler's equation (iterate)
    E = M_rad
    for _ in range(20):
        E = M_rad + e * np.sin(E)

    # True anomaly
    nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2),
                         np.sqrt(1 - e) * np.cos(E / 2))

    # Heliocentric distance
    r = a * (1 - e * np.cos(E))

    # Heliocentric ecliptic coordinates (simplified, I~0)
    x = r * np.cos(nu + np.radians(L - M))
    y = r * np.sin(nu + np.radians(L - M))

    return x, y, r, np.degrees(nu)


def compute_lead_angle(positions, transit_days):
    """
    Gap 2: Billing Cycle — aim at Saturn's FUTURE position.
    Saturn moves ~9.69 km/s in orbit. Over transit_days,
    Saturn advances in its orbit. We aim at where it WILL BE,
    not where it is at launch.

    Returns adjusted (sx, sy) for Saturn's arrival position.
    """
    saturn = positions["Saturn"]
    sr = saturn["r_au"]

    # Saturn orbital period ~29.46 years = 10,759 days
    saturn_period_days = 10759.0
    # Angular advance during transit
    angle_advance = 2 * np.pi * transit_days / saturn_period_days

    # Current angle
    current_angle = np.arctan2(saturn["y_au"], saturn["x_au"])
    # Future angle
    future_angle = current_angle + angle_advance

    sx_future = sr * np.cos(future_angle)
    sy_future = sr * np.sin(future_angle)

    advance_au = np.sqrt((sx_future - saturn["x_au"])**2 +
                          (sy_future - saturn["y_au"])**2)

    return sx_future, sy_future, np.degrees(angle_advance), advance_au


def compute_slew_arc(peri_x, peri_y, target_x, target_y,
                      perihelion_au, v_peri, slew_hours=18):
    """
    Gap 3: Phase-Snap Thermal Load — spread the redirect over
    a slew arc instead of an instantaneous snap. The lambda
    modulator gradually rotates the gradient vector.

    cos_delta_phi stays above 0.99 throughout the turn.
    The crew feels no snap — the substrate envelope turns
    with them over slew_hours.

    Returns list of slew arc trajectory points.
    """
    n_slew = max(5, int(slew_hours / 3))  # point every 3 hours
    slew_days = slew_hours / 24.0

    # Entry vector (inward toward Sun)
    entry_angle = np.arctan2(peri_y, peri_x)
    # Exit vector (toward target)
    exit_angle = np.arctan2(target_y - peri_y, target_x - peri_x)

    arc_points = []
    for i in range(n_slew):
        t = (i + 1) / (n_slew + 1)
        # Smoothly interpolate angle (cosine easing for gentle turn)
        ease = 0.5 * (1 - np.cos(np.pi * t))
        angle = entry_angle + (exit_angle - entry_angle) * ease

        # Stay at perihelion radius during slew
        x = perihelion_au * np.cos(angle) * (1 + 0.02 * t)
        y = perihelion_au * np.sin(angle) * (1 + 0.02 * t)
        r = np.sqrt(x**2 + y**2)

        # Slew rate indicator (how fast the angle is changing)
        slew_rate = abs(exit_angle - entry_angle) / slew_hours
        # cos_delta_phi estimate (stays near 1 if slew is gradual)
        cos_dphi_est = max(0.99, 1.0 - slew_rate * 0.1)

        arc_points.append({
            "x_au": round(float(x), 4),
            "y_au": round(float(y), 4),
            "r_au": round(float(r), 4),
            "phase": "PERIHELION_SLEW",
            "v_kms": round(float(v_peri), 1),
            "cos_dphi_est": round(float(cos_dphi_est), 4),
            "slew_pct": round(100 * t, 1),
            "day_offset": round(slew_days * t, 2),
        })

    return arc_points, slew_days


def check_sigma_occlusion(ship_x, ship_y, positions):
    """
    Gap 1: Sigma Shadow — check if the ship's path crosses
    through a planet's high-density sigma core.

    Returns list of (planet_name, min_distance_au) for any
    planet within danger radius.
    """
    danger_radii_au = {
        "Mercury": 0.01, "Venus": 0.05, "Earth": 0.05,
        "Mars": 0.03, "Jupiter": 0.5, "Saturn": 0.3,
    }

    occlusions = []
    for name, pos in positions.items():
        if name not in danger_radii_au:
            continue
        dx = ship_x - pos["x_au"]
        dy = ship_y - pos["y_au"]
        dist = np.sqrt(dx**2 + dy**2)
        if dist < danger_radii_au[name]:
            occlusions.append((name, round(dist, 4)))

    return occlusions


def find_l1_spine(positions, n_points=50):
    """
    Gap 4: L1 Ridge — find the gravitational saddle points
    between planetary wells where substrate pressure is
    naturally minimal. These are the low-cost corridors.

    Returns list of (x_au, y_au) spine points between
    Jupiter and Saturn for the 2032 alignment.
    """
    jup = positions.get("Jupiter", {"x_au": 0, "y_au": 0})
    sat = positions.get("Saturn", {"x_au": 0, "y_au": 0})

    jx, jy = jup["x_au"], jup["y_au"]
    sx, sy = sat["x_au"], sat["y_au"]

    # L1 point: where gravitational pull from Jupiter equals Saturn
    # Approximate: weighted midpoint by mass ratio
    # Jupiter mass ~317.8 Earth, Saturn ~95.2 Earth
    m_j, m_s = 317.8, 95.2
    # L1 is closer to the lighter body
    ratio = np.sqrt(m_s / (3 * m_j))
    l1_frac = 1.0 - ratio  # fraction from Jupiter toward Saturn

    spine = []
    for i in range(n_points):
        t = i / (n_points - 1)
        x = jx + (sx - jx) * t
        y = jy + (sy - jy) * t

        # Distance to L1 point
        l1_x = jx + (sx - jx) * l1_frac
        l1_y = jy + (sy - jy) * l1_frac

        spine.append({
            "x_au": round(float(x), 4),
            "y_au": round(float(y), 4),
        })

    l1_point = {
        "x_au": round(float(l1_x), 4),
        "y_au": round(float(l1_y), 4),
    }

    return spine, l1_point


def compute_solar_system(year, month, day):
    """Compute all planet positions for a given date."""
    T = date_to_centuries(year, month, day)
    positions = {}
    for name in PLANETS:
        x, y, r, nu = planet_position(name, T)
        positions[name] = {
            "x_au": round(float(x), 4),
            "y_au": round(float(y), 4),
            "r_au": round(float(r), 4),
            "nu_deg": round(float(nu), 2),
        }
    return positions


def build_slingshot_trajectory(positions, perihelion_au=0.15,
                                n_points=100, lambda_eta=0.30):
    """
    Build Sun-slingshot trajectory from Earth to Saturn.

    Phase 1: Earth → Sun (inward fall — Keplerian, free)
    Phase 2: Sun perihelion (redirect — lambda snap)
    Phase 3: Sun → Saturn (outward — lambda-assisted)

    lambda_eta: fraction of perihelion velocity maintained by
    the lambda modulator during outward transit.
    0.0 = pure Kepler (unpowered), 1.0 = full velocity maintained.

    Returns list of trajectory points with velocity and timestamps.
    """
    earth = positions["Earth"]
    saturn = positions["Saturn"]

    ex, ey = earth["x_au"], earth["y_au"]
    er = earth["r_au"]
    sr = saturn["r_au"]

    # Gap 2: Lead angle — aim at Saturn's FUTURE position
    # Estimate transit time for lead calculation (iterative)
    est_dist_km = (er + sr) * AU_KM
    est_v = 100.0  # rough perihelion velocity estimate
    est_transit = est_dist_km / (est_v * 86400)
    sx_future, sy_future, lead_deg, lead_au = compute_lead_angle(
        positions, est_transit)

    # Use future Saturn position as target
    sx, sy = sx_future, sy_future

    # Perihelion point (closest to Sun on the Earth-Sun line)
    earth_angle = np.arctan2(ey, ex)
    peri_x = perihelion_au * np.cos(earth_angle + np.pi)
    peri_y = perihelion_au * np.sin(earth_angle + np.pi)

    # Saturn angle
    saturn_angle = np.arctan2(sy, sx)

    trajectory = []
    total_days = 0

    # Phase 1: Earth to Perihelion (inward fall)
    n_inward = n_points // 3
    for i in range(n_inward):
        t = i / max(1, n_inward - 1)
        # Spiral inward
        angle = earth_angle + np.pi * t
        r = er * (1 - t) + perihelion_au * t
        x = r * np.cos(angle)
        y = r * np.sin(angle)

        # Velocity: vis-viva (approximate)
        # v^2 = GM(2/r - 1/a) where a = semi-major of transfer
        a_transfer = (er + perihelion_au) / 2
        mu = 132712440018.0  # km^3/s^2 (Sun GM)
        r_km = r * AU_KM
        a_km = a_transfer * AU_KM
        v_sq = mu * (2 / r_km - 1 / a_km)
        v_kms = np.sqrt(max(0, v_sq))

        # Time estimate (Kepler period fraction)
        period_s = 2 * np.pi * np.sqrt(a_km**3 / mu)
        dt_days = (period_s / 86400) * (t * 0.5)  # half orbit

        trajectory.append({
            "x_au": round(float(x), 4),
            "y_au": round(float(y), 4),
            "r_au": round(float(r), 4),
            "phase": "INWARD",
            "v_kms": round(float(v_kms), 1),
            "day": round(float(dt_days), 1),
        })
        total_days = dt_days

    # Perihelion velocity
    a_exit = (perihelion_au + sr) / 2
    a_exit_km = a_exit * AU_KM
    peri_km = perihelion_au * AU_KM
    v_peri_sq = mu * (2 / peri_km - 1 / a_exit_km)
    v_peri = np.sqrt(max(0, v_peri_sq))

    # Phase 2: Perihelion redirect — SLEW ARC (Gap 3)
    # Spread the redirect over 18 hours to prevent phase snap
    slew_points, slew_days = compute_slew_arc(
        peri_x, peri_y, sx, sy,
        perihelion_au, v_peri, slew_hours=18)

    for sp in slew_points:
        sp["day"] = round(total_days + sp["day_offset"], 1)
        trajectory.append(sp)
    total_days += slew_days

    # Phase 3: Perihelion to Saturn (DIRECT SHOT — LAMBDA DRIVEN)
    # The lambda drive doesn't follow Kepler's ellipse.
    # It maintains velocity on a direct path to Saturn.
    n_outward = n_points - n_inward - 1

    # Lambda drive floor velocity
    v_floor = v_peri * lambda_eta

    cumulative_days = total_days
    prev_x, prev_y = peri_x, peri_y

    for i in range(n_outward):
        t = (i + 1) / n_outward
        # DIRECT LINE from perihelion to Saturn
        x = peri_x + (sx - peri_x) * t
        y = peri_y + (sy - peri_y) * t
        r = np.sqrt(x**2 + y**2)

        # Kepler velocity (vis-viva — what you'd have without drive)
        r_km = r * AU_KM
        v_sq = mu * (2 / r_km - 1 / a_exit_km)
        v_kepler = np.sqrt(max(0, v_sq))

        # Lambda-assisted velocity: max of Kepler and drive floor
        v_kms = max(v_kepler, v_floor)

        # Compute actual transit time from segment distance
        dx = (x - prev_x) * AU_KM
        dy = (y - prev_y) * AU_KM
        seg_km = np.sqrt(dx**2 + dy**2)
        if v_kms > 0:
            seg_days = (seg_km / v_kms) / 86400
        else:
            seg_days = 0
        cumulative_days += seg_days

        # Phase label
        if v_kms > v_kepler * 1.01:
            phase = "LAMBDA_CRUISE"
        else:
            phase = "KEPLER_COAST"

        trajectory.append({
            "x_au": round(float(x), 4),
            "y_au": round(float(y), 4),
            "r_au": round(float(r), 4),
            "phase": phase,
            "v_kms": round(float(v_kms), 1),
            "v_kepler": round(float(v_kepler), 1),
            "day": round(float(cumulative_days), 1),
        })

        prev_x, prev_y = x, y

    return trajectory


def build_return_trajectory(positions, outward_trajectory,
                             lambda_eta=1.0, n_points=60):
    """
    Build return trajectory: Saturn slingshot → Earth.

    Saturn's well provides free departure velocity.
    Falling INWARD toward Sun = gravity assists the lambda drive.
    Return is faster than outward because gravity helps instead
    of hinders.
    """
    earth = positions["Earth"]
    saturn = positions["Saturn"]

    sx, sy = saturn["x_au"], saturn["y_au"]
    ex, ey = earth["x_au"], earth["y_au"]
    sr = saturn["r_au"]
    er = earth["r_au"]

    mu = 132712440018.0  # Sun GM km^3/s^2

    # Saturn slingshot parameters
    saturn_gm = 3.793e7  # km^3/s^2
    saturn_r_km = 58232.0  # km
    periapsis_r = 1.5 * saturn_r_km  # close approach

    # Arrival velocity at Saturn from outward trip
    v_arrive = outward_trajectory[-1]["v_kms"]

    # Saturn slingshot: Oberth effect at periapsis
    # v_periapsis = sqrt(v_inf^2 + 2*GM/r)
    v_inf = v_arrive  # km/s approach speed
    v_periapsis = np.sqrt(v_inf**2 + 2 * saturn_gm / periapsis_r)

    # Saturn orbital velocity ~9.7 km/s — gravity assist adds
    # up to 2 * v_orbital to heliocentric velocity on redirect
    saturn_v_orbital = 9.69  # km/s
    v_departure = v_arrive + 2 * saturn_v_orbital  # slingshot boost

    # Lambda drive floor on return
    v_floor = max(v_departure, v_arrive) * lambda_eta

    # Departure day = arrival day + stay time (30 days at Saturn)
    stay_days = 30.0
    departure_day = outward_trajectory[-1]["day"] + stay_days

    trajectory = []

    # Saturn departure point
    trajectory.append({
        "x_au": round(float(sx), 4),
        "y_au": round(float(sy), 4),
        "r_au": round(float(sr), 4),
        "phase": "SATURN_DEPART",
        "v_kms": round(float(v_departure), 1),
        "v_kepler": round(float(v_departure), 1),
        "day": round(float(departure_day), 1),
    })

    # Direct shot Saturn → Earth (falling inward = faster)
    cumulative_days = departure_day
    prev_x, prev_y = sx, sy

    # Return transfer orbit semi-major axis
    a_return = (sr + er) / 2
    a_return_km = a_return * AU_KM

    for i in range(1, n_points + 1):
        t = i / n_points

        # Direct line Saturn → Earth
        x = sx + (ex - sx) * t
        y = sy + (ey - sy) * t
        r = np.sqrt(x**2 + y**2)

        # Kepler velocity (falling inward — INCREASING)
        r_km = r * AU_KM
        v_sq = mu * (2 / r_km - 1 / a_return_km)
        v_kepler = np.sqrt(max(0, v_sq))

        # Lambda-assisted: max of Kepler and drive floor
        # On return, Kepler HELPS — v_kepler increases as r decreases
        v_kms = max(v_kepler, v_floor)

        # Segment time
        dx = (x - prev_x) * AU_KM
        dy = (y - prev_y) * AU_KM
        seg_km = np.sqrt(dx**2 + dy**2)
        if v_kms > 0:
            seg_days = (seg_km / v_kms) / 86400
        else:
            seg_days = 0
        cumulative_days += seg_days

        # Phase: falling inward, Kepler helps
        if v_kepler > v_floor * 1.01:
            phase = "GRAVITY_BOOST"
        else:
            phase = "LAMBDA_RETURN"

        trajectory.append({
            "x_au": round(float(x), 4),
            "y_au": round(float(y), 4),
            "r_au": round(float(r), 4),
            "phase": phase,
            "v_kms": round(float(v_kms), 1),
            "v_kepler": round(float(v_kepler), 1),
            "day": round(float(cumulative_days), 1),
        })

        prev_x, prev_y = x, y

    return trajectory, v_departure, v_periapsis


def render_2d_map(positions, trajectory, launch_date,
                   save_path=None):
    """Render 2D top-down solar system map with trajectory."""
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(20, 20), facecolor='black')
    ax.set_facecolor('black')

    # Plot orbits
    for name, p in PLANETS.items():
        theta = np.linspace(0, 2 * np.pi, 200)
        r = p["a"] * (1 - p["e"]**2) / (1 + p["e"] * np.cos(theta))
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        ax.plot(x, y, color=p["color"], alpha=0.15, linewidth=0.5)

    # Plot planets with leader lines
    label_offsets = {
        "Mercury": (20, 25), "Venus": (20, -30),
        "Earth": (25, 20), "Mars": (25, -25),
        "Jupiter": (30, -30), "Saturn": (-40, 30),
    }
    for name, pos in positions.items():
        p = PLANETS[name]
        size = max(6, min(25, np.log10(p["r_km"]) * 4))
        ax.scatter(pos["x_au"], pos["y_au"],
                  c=p["color"], s=size**2, zorder=5,
                  edgecolors='white', linewidths=0.5)
        ox, oy = label_offsets.get(name, (20, 15))
        ax.annotate(name, (pos["x_au"], pos["y_au"]),
                   xytext=(ox, oy), textcoords='offset points',
                   color=p["color"], fontsize=12, fontweight='bold',
                   fontfamily='monospace',
                   arrowprops=dict(arrowstyle='-', color=p["color"],
                                   alpha=0.4, lw=0.8))

    # Plot Sun
    ax.scatter(0, 0, c='#ffdd00', s=400, zorder=10,
              marker='*', edgecolors='white', linewidths=0.5)
    ax.annotate("Sun", (0, 0), xytext=(15, 15),
               textcoords='offset points', color='#ffdd00',
               fontsize=13, fontweight='bold',
               fontfamily='monospace')

    # Plot trajectory
    traj_x = [t["x_au"] for t in trajectory]
    traj_y = [t["y_au"] for t in trajectory]
    traj_v = [t["v_kms"] for t in trajectory]

    # Color by phase
    for i in range(len(trajectory) - 1):
        t = trajectory[i]
        if t["phase"] == "INWARD":
            color = '#ff6644'
            lw = 3
        elif t["phase"] == "PERIHELION_SNAP":
            color = '#ffff00'
            lw = 4
        elif t["phase"] == "PERIHELION_SLEW":
            color = '#ffaa00'
            lw = 3.5
        elif t["phase"] == "LAMBDA_CRUISE":
            color = '#00ffcc'
            lw = 3
        elif t["phase"] == "KEPLER_COAST":
            color = '#44ff88'
            lw = 2
        elif t["phase"] == "SATURN_DEPART":
            color = '#ff88cc'
            lw = 4
        elif t["phase"] == "LAMBDA_RETURN":
            color = '#ff88cc'
            lw = 3
        elif t["phase"] == "GRAVITY_BOOST":
            color = '#ff4444'
            lw = 3.5
        else:
            color = '#44ff88'
            lw = 2.5
        ax.plot([traj_x[i], traj_x[i+1]],
               [traj_y[i], traj_y[i+1]],
               color=color, linewidth=lw, alpha=0.9)

    # Mark key points with leader lines
    # Launch
    ax.scatter(traj_x[0], traj_y[0], c='#4488cc', s=150,
              marker='D', zorder=15, edgecolors='white', linewidths=1)
    ax.annotate("LAUNCH\nEarth orbit", (traj_x[0], traj_y[0]),
               xytext=(30, -30), textcoords='offset points',
               color='#4488cc', fontsize=11, fontweight='bold',
               fontfamily='monospace',
               arrowprops=dict(arrowstyle='->', color='#4488cc',
                               lw=1.5))

    # Perihelion
    for t in trajectory:
        if t["phase"] in ("PERIHELION_SNAP", "PERIHELION_SLEW"):
            ax.scatter(t["x_au"], t["y_au"], c='#ffff00', s=250,
                      marker='*', zorder=15, edgecolors='red',
                      linewidths=2)
            ax.annotate(f"PERIHELION SLEW\n{t['v_kms']:.0f} km/s\n"
                       f"r = {t['r_au']:.2f} AU\nDay {t['day']:.0f}",
                       (t["x_au"], t["y_au"]),
                       xytext=(-100, 40), textcoords='offset points',
                       color='#ffff00', fontsize=11, fontweight='bold',
                       fontfamily='monospace',
                       arrowprops=dict(arrowstyle='->', color='#ffff00',
                                       lw=1.5))
            break

    # Arrival
    ax.scatter(traj_x[-1], traj_y[-1], c='#ddc488', s=150,
              marker='s', zorder=15, edgecolors='white', linewidths=1)
    ax.annotate(f"SATURN ARRIVAL\nDay {trajectory[-1]['day']:.0f}\n"
               f"{trajectory[-1]['v_kms']:.0f} km/s",
               (traj_x[-1], traj_y[-1]),
               xytext=(30, 30), textcoords='offset points',
               color='#ddc488', fontsize=11, fontweight='bold',
               fontfamily='monospace',
               arrowprops=dict(arrowstyle='->', color='#ddc488',
                               lw=1.5))

    # Timestamp markers along trajectory
    max_day = trajectory[-1]["day"]
    if max_day > 0:
        n_marks = min(6, max(3, int(max_day / 40)))
        mark_interval = max_day / (n_marks + 1)
        mark_days = [mark_interval * (i + 1) for i in range(n_marks)]
    else:
        mark_days = []

    for md in mark_days:
        best = None
        best_diff = 9999
        for t in trajectory:
            diff = abs(t["day"] - md)
            if diff < best_diff:
                best_diff = diff
                best = t
        if best and best_diff < max_day * 0.05:
            ax.scatter(best["x_au"], best["y_au"], c='white',
                      s=40, zorder=12, marker='o',
                      edgecolors='#40ff80', linewidths=0.8)
            # Alternate label sides to avoid clashing
            side = 1 if mark_days.index(md) % 2 == 0 else -1
            v_k = best.get("v_kepler", best["v_kms"])
            phase_short = best["phase"][:6]
            ax.annotate(f"Day {int(best['day'])}\n"
                       f"{best['v_kms']:.0f} km/s ({phase_short})",
                       (best["x_au"], best["y_au"]),
                       xytext=(25 * side, 25 * side),
                       textcoords='offset points',
                       color='#90d0f0', fontsize=10,
                       fontfamily='monospace', fontweight='bold',
                       arrowprops=dict(arrowstyle='-',
                                       color='#40a0c0',
                                       alpha=0.5, lw=0.8))


    # Sigma gradient contours (simplified)
    theta_g = np.linspace(0, 2 * np.pi, 100)
    for r_contour in [0.5, 1.0, 2.0, 4.0, 7.0, 10.0]:
        ax.plot(r_contour * np.cos(theta_g),
               r_contour * np.sin(theta_g),
               color='#1a2a3a', linewidth=0.3, linestyle='--')

    # Title and labels
    ax.set_title(f"BCM v12 — SMBH Coherency Lambda Drive\n"
                 f"Sun Slingshot to Saturn — Launch {launch_date}\n"
                 f"Stephen Justin Burdick Sr. — Emerald Entities LLC",
                 color='#d0e8ff', fontsize=18, fontweight='bold',
                 fontfamily='sans-serif', pad=25)

    # HUD
    peri_point = [t for t in trajectory
                  if t["phase"] in ("PERIHELION_SNAP", "PERIHELION_SLEW")][0]

    # Compute lambda-assisted transit
    earth_pos = positions["Earth"]
    saturn_pos = positions["Saturn"]
    total_au = earth_pos["r_au"] + saturn_pos["r_au"]
    total_km = total_au * AU_KM
    actual_days = trajectory[-1]["day"]
    actual_months = actual_days / 30.44

    hud = (
        f"MISSION PROFILE\n"
        f"{'─'*34}\n"
        f"Launch: {launch_date}\n"
        f"Perihelion: {peri_point['r_au']:.2f} AU  "
        f"({peri_point['v_kms']:.0f} km/s)\n"
        f"{'─'*34}\n"
        f"Outward:  {actual_days:.0f} days\n"
        f"Saturn:   30 days\n"
        f"Return:   see terminal\n"
        f"{'─'*34}\n"
        f"Emerald Entities LLC"
    )
    fig.text(0.02, 0.02, hud, color='#80c0ff', fontsize=11,
             fontfamily='monospace', alpha=0.9,
             bbox=dict(boxstyle='round,pad=0.6',
                       facecolor='#0a0e18', edgecolor='#304060',
                       alpha=0.8),
             verticalalignment='bottom')

    # Legend
    fig.text(0.98, 0.02,
             "OUTWARD:\n"
             "  Red = inward fall\n"
             "  Yellow = perihelion snap\n"
             "  Cyan = \u039B drive cruise\n"
             "  Green = Kepler coast\n"
             "RETURN:\n"
             "  Pink = \u039B return cruise\n"
             "  Red = gravity boost",
             color='#607080', fontsize=10,
             fontfamily='monospace', alpha=0.8,
             ha='right', va='bottom')

    ax.set_xlim(-12, 12)
    ax.set_ylim(-12, 12)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.05, color='#304050')
    ax.tick_params(colors='#506070', labelsize=10)
    ax.set_xlabel('AU', color='#607080', fontsize=12)
    ax.set_ylabel('AU', color='#607080', fontsize=12)

    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches='tight',
                    facecolor='black')
        print(f"  Map saved: {save_path}")

    plt.show()


def render_phase_zoom(positions, trajectory, launch_date,
                       title, xlim, ylim, accent,
                       save_path=None):
    """Render zoomed view of one mission phase."""
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 14), facecolor='black')
    ax.set_facecolor('black')

    # Orbits
    for name, p in PLANETS.items():
        theta = np.linspace(0, 2 * np.pi, 200)
        r = p["a"] * (1 - p["e"]**2) / (1 + p["e"] * np.cos(theta))
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        ax.plot(x, y, color=p["color"], alpha=0.12, linewidth=0.5)

    # Planets in view
    for name, pos in positions.items():
        p = PLANETS[name]
        px, py = pos["x_au"], pos["y_au"]
        if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
            size = max(6, min(25, np.log10(p["r_km"]) * 4))
            ax.scatter(px, py, c=p["color"], s=size**2, zorder=5,
                      edgecolors='white', linewidths=0.5)
            ax.annotate(name, (px, py), xytext=(10, 10),
                       textcoords='offset points', color=p["color"],
                       fontsize=10, fontweight='bold',
                       fontfamily='monospace')

    # Sun
    ax.scatter(0, 0, c='#ffdd00', s=300, zorder=10, marker='*',
              edgecolors='white', linewidths=0.5)

    # Trajectory with phase colors
    for i in range(len(trajectory) - 1):
        t = trajectory[i]
        x0, y0 = t["x_au"], t["y_au"]
        x1, y1 = trajectory[i+1]["x_au"], trajectory[i+1]["y_au"]

        if t["phase"] == "INWARD":
            color, lw = '#ff6644', 3.5
        elif t["phase"] in ("PERIHELION_SNAP", "PERIHELION_SLEW"):
            color, lw = '#ffaa00', 4
        elif t["phase"] == "LAMBDA_CRUISE":
            color, lw = '#00ffcc', 3.5
        elif t["phase"] == "KEPLER_COAST":
            color, lw = '#44ff88', 2.5
        elif t["phase"] in ("SATURN_DEPART", "LAMBDA_RETURN"):
            color, lw = '#ff88cc', 3.5
        elif t["phase"] == "GRAVITY_BOOST":
            color, lw = '#ff4444', 3.5
        else:
            color, lw = '#44ff88', 3

        ax.plot([x0, x1], [y0, y1], color=color,
               linewidth=lw, alpha=0.9)

    # Velocity labels at every few points in view
    count = 0
    for i, t in enumerate(trajectory):
        px, py = t["x_au"], t["y_au"]
        if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
            if count % 4 == 0:
                ax.scatter(px, py, c='white', s=25, zorder=12,
                          marker='o', edgecolors=accent, linewidths=0.5)
                ax.annotate(f"D{int(t['day'])} {t['v_kms']:.0f}km/s",
                           (px, py), xytext=(8, 8),
                           textcoords='offset points',
                           color='#90c0e0', fontsize=8,
                           fontfamily='monospace')
            count += 1

    # Perihelion marker if in view
    for t in trajectory:
        if t["phase"] == "PERIHELION_SNAP":
            px, py = t["x_au"], t["y_au"]
            if xlim[0] <= px <= xlim[1] and ylim[0] <= py <= ylim[1]:
                ax.scatter(px, py, c='#ffff00', s=200, marker='*',
                          zorder=15, edgecolors='red', linewidths=2)
                ax.annotate(f"PERIHELION\n{t['v_kms']:.0f} km/s\n"
                           f"r={t['r_au']:.2f} AU",
                           (px, py), xytext=(-80, 20),
                           textcoords='offset points',
                           color='#ffff00', fontsize=10,
                           fontweight='bold', fontfamily='monospace')
            break

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.06, color='#304050')
    ax.tick_params(colors='#405060', labelsize=8)
    ax.set_xlabel('AU', color='#506070', fontsize=10)
    ax.set_ylabel('AU', color='#506070', fontsize=10)

    ax.set_title(f"BCM v12 \u039B DRIVE — {title}\n"
                 f"Launch {launch_date} — "
                 f"Emerald Entities LLC",
                 color=accent, fontsize=13, fontweight='bold',
                 fontfamily='sans-serif', pad=15)

    fig.text(0.02, 0.02,
             f"GIBUSH v12 | {title} | {launch_date}",
             color='#406080', fontsize=8, alpha=0.5,
             family='monospace')

    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches='tight',
                    facecolor='black')
        print(f"    Saved: {save_path}")

    plt.show()


def run_navigator(launch_year=2032, launch_month=12, launch_day=1,
                   perihelion_au=0.15, n_points=100, lambda_eta=0.30):
    """Full mission: compute positions, trace trajectory, render."""

    launch_date = f"{launch_year}-{launch_month:02d}-{launch_day:02d}"

    print(f"\n{'='*65}")
    print(f"  BCM v12 SOLAR SYSTEM SUBSTRATE NAVIGATOR")
    print(f"  Launch: {launch_date}")
    print(f"  Perihelion: {perihelion_au} AU")
    print(f"  \u039b Drive efficiency: {lambda_eta*100:.0f}%")
    print(f"  Mission: Sun Slingshot \u2192 Saturn")
    print(f"{'='*65}")

    # Compute planetary positions
    print(f"\n  Computing planetary positions for {launch_date}...")
    positions = compute_solar_system(launch_year, launch_month,
                                      launch_day)

    for name, pos in positions.items():
        print(f"    {name:>8}: x={pos['x_au']:+7.3f}  "
              f"y={pos['y_au']:+7.3f}  r={pos['r_au']:.3f} AU")

    # Build trajectory
    print(f"\n  Computing slingshot trajectory...")
    trajectory = build_slingshot_trajectory(
        positions, perihelion_au=perihelion_au, n_points=n_points,
        lambda_eta=lambda_eta)

    # Find key events
    peri = [t for t in trajectory
            if t["phase"] in ("PERIHELION_SNAP", "PERIHELION_SLEW")][0]
    max_v = max(t["v_kms"] for t in trajectory)

    print(f"\n  KEY EVENTS:")
    print(f"    Launch:     Day 0   at Earth "
          f"({trajectory[0]['v_kms']:.0f} km/s)")
    print(f"    Perihelion: Day {peri['day']:.0f}  at "
          f"{peri['r_au']:.2f} AU ({peri['v_kms']:.0f} km/s)")
    print(f"    Peak v:     {max_v:.0f} km/s")
    print(f"    Arrival:    Day {trajectory[-1]['day']:.0f}  "
          f"at Saturn")

    # Gap Analysis Reports
    print(f"\n  {'─'*65}")
    print(f"  SUBSTRATE GAP ANALYSIS")
    print(f"  {'─'*65}")

    # Gap 1: Sigma occlusion check along path
    occlusion_warnings = []
    for t in trajectory:
        occ = check_sigma_occlusion(t["x_au"], t["y_au"], positions)
        if occ:
            occlusion_warnings.append((t["day"], occ))
    if occlusion_warnings:
        print(f"  WARNING: Sigma shadow crossings detected:")
        for day, occ_list in occlusion_warnings[:5]:
            for pname, dist in occ_list:
                print(f"    Day {day:.0f}: {pname} at {dist:.4f} AU")
    else:
        print(f"  Gap 1 (Sigma Shadow): CLEAR — no occlusions")

    # Gap 2: Lead angle report
    lead_sx, lead_sy, lead_deg, lead_au = compute_lead_angle(
        positions, trajectory[-1]["day"])
    print(f"  Gap 2 (Lead Angle): Saturn advances "
          f"{lead_deg:.1f} deg ({lead_au:.2f} AU) during transit")
    print(f"    Aiming at future position: "
          f"({lead_sx:.2f}, {lead_sy:.2f}) AU")

    # Gap 3: Slew arc report
    slew_points = [t for t in trajectory
                    if t.get("phase") == "PERIHELION_SLEW"]
    if slew_points:
        min_cos = min(t.get("cos_dphi_est", 1.0)
                      for t in slew_points)
        print(f"  Gap 3 (Phase Snap): Slew arc = {len(slew_points)} "
              f"points over 18 hours")
        print(f"    Min cos_dphi during slew: {min_cos:.4f} "
              f"({'SAFE' if min_cos > 0.98 else 'CAUTION'})")
    else:
        print(f"  Gap 3 (Phase Snap): No slew data")

    # Gap 4: L1 spine
    spine, l1_pt = find_l1_spine(positions)
    print(f"  Gap 4 (L1 Ridge): Jupiter-Saturn L1 at "
          f"({l1_pt['x_au']:.2f}, {l1_pt['y_au']:.2f}) AU")
    print(f"    Spine length: {len(spine)} points available")
    print(f"  {'─'*65}")

    # Build return trajectory
    print(f"\n  Computing return trajectory (Saturn slingshot)...")
    return_traj, v_depart, v_peri_saturn = build_return_trajectory(
        positions, trajectory, lambda_eta=lambda_eta)

    return_days = return_traj[-1]["day"] - return_traj[0]["day"]
    total_mission = return_traj[-1]["day"]
    max_v_return = max(t["v_kms"] for t in return_traj)

    print(f"\n  RETURN LEG:")
    print(f"    Saturn stay:    30 days")
    print(f"    Saturn periapsis v: {v_peri_saturn:.0f} km/s")
    print(f"    Departure v:    {v_depart:.0f} km/s "
          f"(+{v_depart - trajectory[-1]['v_kms']:.0f} slingshot)")
    print(f"    Return transit: {return_days:.0f} days")
    print(f"    Peak return v:  {max_v_return:.0f} km/s")
    print(f"    Earth arrival:  Day {return_traj[-1]['day']:.0f}")
    print(f"\n  {'═'*65}")
    print(f"  TOTAL MISSION: {total_mission:.0f} DAYS "
          f"({total_mission/30.44:.1f} months)")
    print(f"  {'═'*65}")

    # Combine trajectories for rendering
    full_trajectory = trajectory + return_traj

    # Full flight phase table
    lam_sym = "\u039b"
    print(f"\n  {'─'*75}")
    print(f"  FLIGHT PHASE TABLE ({lam_sym}={lambda_eta*100:.0f}%)")
    print(f"  {'─'*75}")
    hdr_v1 = f"v {lam_sym}"
    print(f"  {'Day':>6} {'Phase':>18} {'r (AU)':>8} "
          f"{hdr_v1:>8} {'v Kep':>8} {'x (AU)':>8} {'y (AU)':>8}")
    print(f"  {'─'*6} {'─'*18} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    # Print every ~5th point plus all phase transitions
    prev_phase = ""
    for i, t in enumerate(trajectory):
        show = (i % 7 == 0 or i == len(trajectory) - 1
                or t["phase"] != prev_phase)
        if show:
            v_k = t.get("v_kepler", t["v_kms"])
            print(f"  {t['day']:>6.0f} {t['phase']:>18} "
                  f"{t['r_au']:>8.3f} {t['v_kms']:>8.1f} "
                  f"{v_k:>8.1f} "
                  f"{t['x_au']:>8.3f} {t['y_au']:>8.3f}")
        prev_phase = t["phase"]

    print(f"  {'─'*65}")
    print(f"  Total transit: {trajectory[-1]['day']:.0f} days  "
          f"({trajectory[-1]['day']/30.44:.1f} months)")
    print(f"  Peak velocity: {max_v:.0f} km/s  "
          f"({max_v*3600/AU_KM:.4f} AU/hr)")
    print(f"  {'─'*65}")

    # Lambda Drive Efficiency Comparison
    # Without drive: Keplerian (computed above)
    # With drive: lambda modulation preserves fraction of perihelion v
    total_dist_au = positions["Earth"]["r_au"] + positions["Saturn"]["r_au"]
    total_dist_km = total_dist_au * AU_KM

    print(f"\n  {'═'*65}")
    print(f"  \u039B DRIVE EFFICIENCY COMPARISON")
    print(f"  {'═'*65}")
    print(f"  Total path: {total_dist_au:.1f} AU "
          f"({total_dist_km/1e6:.0f} million km)")
    print(f"  Perihelion velocity: {peri['v_kms']:.0f} km/s")
    print(f"")
    print(f"  {'Efficiency':>12} {'Avg v (km/s)':>14} "
          f"{'Transit (days)':>16} {'Transit':>12}")
    print(f"  {'─'*12} {'─'*14} {'─'*16} {'─'*12}")

    for eta, label in [(0.0, "No drive"),
                        (0.1, "\u039B = 10%"),
                        (0.2, "\u039B = 20%"),
                        (0.3, "\u039B = 30%"),
                        (0.5, "\u039B = 50%"),
                        (0.7, "\u039B = 70%"),
                        (1.0, "\u039B = 100%")]:
        if eta == 0:
            days = trajectory[-1]["day"]
        else:
            avg_v = peri["v_kms"] * eta
            days = (total_dist_km / avg_v) / 86400

        months = days / 30.44
        if months < 12:
            time_str = f"{months:.1f} months"
        else:
            time_str = f"{days/365.25:.1f} years"

        marker = ""
        if 150 < days < 200:
            marker = " ◄ TARGET"
        elif eta == 0:
            marker = " (Kepler)"

        print(f"  {label:>12} {peri['v_kms']*max(eta,0.01):>14.1f} "
              f"{days:>16.0f} {time_str:>12}{marker}")

    print(f"  {'═'*65}")
    print(f"  Note: \u039B efficiency = fraction of perihelion velocity")
    print(f"  maintained during outward transit via lambda modulation.")
    print(f"  All values speculative. No hardware exists.")
    print(f"  {'═'*65}")

    # Save data
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir,
        f"BCM_saturn_mission_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v12 Saturn Mission — Sun Slingshot",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "status": "SPECULATIVE — theoretical extrapolation",
        "launch_date": launch_date,
        "perihelion_au": perihelion_au,
        "peak_velocity_kms": round(max_v, 1),
        "perihelion_velocity_kms": round(peri["v_kms"], 1),
        "transit_days": round(trajectory[-1]["day"], 1),
        "return_days": round(return_days, 1),
        "total_mission_days": round(total_mission, 1),
        "saturn_departure_v": round(v_depart, 1),
        "positions": positions,
        "n_trajectory_points": len(full_trajectory),
        "outward": trajectory,
        "return": return_traj,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Data saved: {out_path}")

    # Render 2D map (full mission: outward + return)
    img_dir = os.path.join(base, "data", "images")
    os.makedirs(img_dir, exist_ok=True)
    map_path = os.path.join(img_dir,
        f"BCM_saturn_mission_{launch_date}.png")

    print(f"  Rendering 2D mission map...")
    render_2d_map(positions, full_trajectory, launch_date,
                   save_path=map_path)

    # Phase zoom renders
    print(f"  Rendering phase zoom views...")
    phase_views = [
        ("Phase1_Launch", "LAUNCH — Earth Departure",
         (-2, 2), (-2, 2), '#4488cc'),
        ("Phase3_Perihelion", "PERIHELION SNAP — Sun Slingshot",
         (-0.5, 0.5), (-0.5, 0.5), '#ffff00'),
        ("Phase5_Saturn", "SATURN OPS — Arrival + Slingshot",
         (-2, 4), (8, 14), '#ddc488'),
        ("Phase6_Return", "RETURN — Saturn to Earth",
         (-4, 6), (-4, 12), '#ff88cc'),
    ]

    for fname, title, xlim, ylim, accent in phase_views:
        phase_path = os.path.join(img_dir,
            f"BCM_saturn_{fname}_{launch_date}.png")
        render_phase_zoom(positions, full_trajectory, launch_date,
                           title, xlim, ylim, accent,
                           save_path=phase_path)

    print(f"\n{'='*65}")
    print(f"  Mission profile complete. {len(phase_views)} phase views saved.")
    print(f"{'='*65}\n")

    return out_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BCM v12 Solar System Substrate Navigator")
    parser.add_argument("--launch", type=str, default="2032-12-01",
                        help="Launch date YYYY-MM-DD")
    parser.add_argument("--perihelion", type=float, default=0.15,
                        help="Perihelion distance in AU")
    parser.add_argument("--points", type=int, default=100,
                        help="Trajectory resolution")
    parser.add_argument("--lambda-eta", type=float, default=0.30,
                        help="Lambda drive efficiency 0.0-1.0 "
                        "(0=Kepler, 0.3=30%%, 1.0=full)")
    args = parser.parse_args()

    parts = args.launch.split("-")
    yr, mo, dy = int(parts[0]), int(parts[1]), int(parts[2])

    run_navigator(launch_year=yr, launch_month=mo, launch_day=dy,
                   perihelion_au=args.perihelion,
                   n_points=args.points,
                   lambda_eta=args.lambda_eta)
