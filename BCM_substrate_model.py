# -*- coding: utf-8 -*-
"""
BCM Substrate Model — Shared Physics Core
============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC

The physics engine shared by Navigator, Flight Computer,
and AI Engine. Implements:
  - Lambda field construction (dipole modulator)
  - Sigma packet propagation
  - Drift computation
  - Coherence measurement
  - Bridge tension calculation
  - Saddle point detection

All three layers use these functions. None modify them.
The physics is the physics. The substrate is the substrate.
"""

import numpy as np

# Constants
AU_KM = 149597870.7
MU_SUN = 132712440018.0  # km^3/s^2


def build_lambda_dipole(nx, ny, ship_pos, direction=(1, 0),
                         base_lam=0.1, delta_lam=0.05,
                         spread=10.0):
    """
    Build fore/aft lambda dipole centered on ship.
    Lower lambda ahead (deep memory), higher behind (fast decay).
    """
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - ship_pos[0]
    dy = Y - ship_pos[1]

    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)

    proj = dx * d[0] + dy * d[1]
    profile = np.tanh(proj / spread)

    return base_lam - delta_lam * profile


def build_gaussian_well(nx, ny, center, depth=0.08,
                          width=15.0, base_lam=0.15):
    """Build a Gaussian lambda well (gravity analog)."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2

    return base_lam - depth * np.exp(-r2 / (2 * width**2))


def init_sigma_packet(nx, ny, center, amplitude=1.0, width=5.0):
    """Create a Gaussian sigma packet (the 'ship')."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2

    return amplitude * np.exp(-r2 / (2 * width**2))


def step_substrate(sigma, lam_field, D=0.5, dt=0.05):
    """
    One timestep of substrate evolution.
    Diffusion + lambda decay. Core PDE:
      d_sigma/dt = D * laplacian(sigma) - lambda(x,y) * sigma
    """
    laplacian = (
        np.roll(sigma, 1, axis=0) +
        np.roll(sigma, -1, axis=0) +
        np.roll(sigma, 1, axis=1) +
        np.roll(sigma, -1, axis=1) -
        4 * sigma
    )
    sigma = sigma + D * laplacian * dt - lam_field * sigma * dt
    return np.maximum(sigma, 0)


def compute_com(sigma):
    """Center of mass of sigma field."""
    total = np.sum(sigma)
    if total < 1e-15:
        return None

    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    cx = np.sum(X * sigma) / total
    cy = np.sum(Y * sigma) / total

    return np.array([cx, cy])


def compute_coherence(sigma, center, radius=10):
    """Fraction of sigma within radius of center."""
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2

    inside = np.sum(sigma[r2 < radius**2])
    total = np.sum(sigma)

    if total < 1e-15:
        return 0.0
    return inside / total


def compute_bridge_tension(pos1, pos2, mass1, mass2):
    """
    Substrate bridge tension between two bodies.
    Proportional to mass product / distance^2.
    """
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    dist = np.sqrt(dx**2 + dy**2)
    if dist < 0.01:
        return 0.0
    return (mass1 * mass2) / (dist * dist)


def compute_sigma_shadow(ship_pos, body_pos, body_radius_au):
    """Check if ship is within sigma shadow of a body."""
    dx = ship_pos[0] - body_pos[0]
    dy = ship_pos[1] - body_pos[1]
    dist = np.sqrt(dx**2 + dy**2)
    return dist < body_radius_au


def compute_drift_velocity(sigma, lam_field, D=0.5, dt=0.05,
                            n_steps=10):
    """
    Measure instantaneous drift velocity of a sigma packet
    in a given lambda field over n_steps.
    Returns velocity vector (px/step).
    """
    com_start = compute_com(sigma)
    if com_start is None:
        return np.zeros(2)

    s = sigma.copy()
    for _ in range(n_steps):
        s = step_substrate(s, lam_field, D, dt)

    com_end = compute_com(s)
    if com_end is None:
        return np.zeros(2)

    return (com_end - com_start) / n_steps


def find_l1_point(pos_A, pos_B, mass_A, mass_B):
    """
    Approximate L1 Lagrange point between two bodies.
    Located where gravitational pulls balance.
    """
    ratio = np.sqrt(mass_B / (3 * mass_A))
    frac = 1.0 - ratio

    l1_x = pos_A[0] + (pos_B[0] - pos_A[0]) * frac
    l1_y = pos_A[1] + (pos_B[1] - pos_A[1]) * frac

    return np.array([l1_x, l1_y])


def perihelion_velocity(perihelion_au, destination_au):
    """Vis-viva velocity at perihelion for a transfer orbit."""
    a_exit = (perihelion_au + destination_au) / 2
    peri_km = perihelion_au * AU_KM
    a_km = a_exit * AU_KM
    v_sq = MU_SUN * (2 / peri_km - 1 / a_km)
    return np.sqrt(max(0, v_sq))
