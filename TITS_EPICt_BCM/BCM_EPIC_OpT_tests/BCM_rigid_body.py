# -*- coding: utf-8 -*-
"""
BCM v13 — Rigid Body Transport & Decay Isolation
===================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Two kill tests from ChatGPT:

  TEST 1: RIGID BODY — freeze sigma shape, only allow
  translation. Compute net gradient force across the
  rigid kernel. Does it produce a translation vector?

  If YES: geometric transport (the ship sails)
  If NO: deformation drift (the dune erodes)

  TEST 2: REMOVE DECAY — keep gradient + diffusion,
  remove lambda*sigma decay term entirely. Does drift
  still occur?

  If YES: drift is NOT dissipation-driven
  If NO: drift is 100% dissipation-driven

Usage:
    python BCM_rigid_body.py
    python BCM_rigid_body.py --steps 2000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


def compute_com(sigma):
    total = np.sum(sigma)
    if total < 1e-15:
        return None
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X * sigma) / total,
                      np.sum(Y * sigma) / total])


# ============================================================
# TEST 1: RIGID BODY TRANSLATION
# ============================================================
def test_rigid_body(steps=2000, nx=128, ny=128,
                     dt=0.05, D=0.5, delta_lam=0.025,
                     void_lambda=0.10):
    """
    Rigid body test:
    1. Create a fixed Gaussian kernel (the 'ship')
    2. At each step, compute the NET gradient force
       across the kernel's footprint
    3. Translate the kernel by that force (no deformation)
    4. Track position over time

    The kernel CANNOT deform. It cannot spread. It cannot
    erode. It can only translate as a rigid body.

    The 'force' is: integral of (sigma * nabla_lambda)
    over the kernel footprint.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: RIGID BODY TRANSLATION")
    print(f"  {'='*60}")
    print(f"  Frozen shape. No deformation. No erosion.")
    print(f"  Only rigid translation from net gradient force.")
    print(f"  delta_lam={delta_lam}  void_lam={void_lambda}")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Fixed kernel shape (never changes)
    kernel_width = 5.0
    kernel = np.exp(-((x - nx//2)**2) / (2 * kernel_width**2))
    kernel_y = np.exp(-((y - ny//2)**2) / (2 * kernel_width**2))
    kernel_2d = np.outer(kernel, kernel_y)
    kernel_2d /= np.sum(kernel_2d)  # normalize

    # Ship position (floating point, sub-pixel)
    ship_x = float(nx // 2)
    ship_y = float(ny // 2)
    initial_x = ship_x
    initial_y = ship_y

    trajectory = []
    forces = []
    speeds = []

    # Mobility coefficient
    mu = 1.0

    print(f"  {'Step':>6} {'Ship_x':>10} {'Ship_y':>10} "
          f"{'Force_x':>12} {'Drift':>10} {'Speed':>10}")
    print(f"  {'─'*6} {'─'*10} {'─'*10} {'─'*12} {'─'*10} "
          f"{'─'*10}")

    for step in range(steps):
        # Place kernel at current ship position
        # (using sub-pixel interpolation via shift)
        ix = int(round(ship_x))
        iy = int(round(ship_y))

        # Compute lambda field at ship location
        # Static gradient centered on GRID center (not ship)
        lam_field = np.full((nx, ny), void_lambda)
        proj = (X - nx//2) * 1.0  # gradient relative to grid
        drive = -delta_lam * np.tanh(proj / 6.0)
        lam_field = np.maximum(lam_field + drive, 0.005)

        # Compute gradient of lambda at each point
        # grad_lam_x = d(lam)/dx
        grad_lam_x = (np.roll(lam_field, -1, axis=0) -
                       np.roll(lam_field, 1, axis=0)) / 2.0
        grad_lam_y = (np.roll(lam_field, -1, axis=1) -
                       np.roll(lam_field, 1, axis=1)) / 2.0

        # Place rigid kernel centered at ship position
        # Shift kernel to ship location
        shift_x = ix - nx // 2
        shift_y = iy - ny // 2
        sigma_placed = np.roll(np.roll(kernel_2d, shift_x, axis=0),
                                shift_y, axis=1)

        # Net force = integral of (sigma * grad_lambda)
        # This is the "gradient pressure" on the rigid body
        force_x = float(np.sum(sigma_placed * grad_lam_x)) * mu
        force_y = float(np.sum(sigma_placed * grad_lam_y)) * mu

        # Translate rigid body
        ship_x += force_x * dt
        ship_y += force_y * dt

        # Track
        drift = np.sqrt((ship_x - initial_x)**2 +
                          (ship_y - initial_y)**2)
        speed = np.sqrt(force_x**2 + force_y**2) * dt

        trajectory.append((ship_x, ship_y))
        forces.append((force_x, force_y))
        speeds.append(speed)

        if step % 200 == 0 or step < 10:
            print(f"  {step:>6} {ship_x:>10.4f} {ship_y:>10.4f} "
                  f"{force_x:>12.8f} {drift:>10.6f} "
                  f"{speed:>10.8f}")

    total_drift = np.sqrt((ship_x - initial_x)**2 +
                            (ship_y - initial_y)**2)
    mean_speed = float(np.mean(speeds))
    mean_force = float(np.mean([f[0] for f in forces]))

    print(f"\n  RIGID BODY RESULTS:")
    print(f"    Total drift: {total_drift:.6f} px")
    print(f"    Mean speed:  {mean_speed:.10f} px/step")
    print(f"    Mean force_x: {mean_force:.10f}")
    print(f"    Final pos:   ({ship_x:.4f}, {ship_y:.4f})")

    if total_drift > 0.001:
        print(f"\n    RIGID BODY MOVES.")
        print(f"    Transport is GEOMETRIC — not deformation.")
        print(f"    The gradient exerts net force on rigid shape.")
        print(f"    The ship SAILS. It is not an eroding dune.")
    else:
        print(f"\n    RIGID BODY DOES NOT MOVE.")
        print(f"    Transport is deformation-driven.")
        print(f"    The dune erodes. The ship does not sail.")

    return {
        "total_drift": round(total_drift, 8),
        "mean_speed": round(mean_speed, 12),
        "mean_force_x": round(mean_force, 12),
        "final_x": round(ship_x, 6),
        "final_y": round(ship_y, 6),
        "steps": steps,
        "moved": total_drift > 0.001,
    }


# ============================================================
# TEST 2: REMOVE DECAY — DOES DRIFT REQUIRE DISSIPATION?
# ============================================================
def test_no_decay(steps=2000, nx=128, ny=128,
                   dt=0.05, D=0.5, delta_lam=0.025,
                   void_lambda=0.10):
    """
    Remove the lambda*sigma decay term entirely.
    Keep diffusion. Keep gradient field (but it only
    shapes the field, doesn't cause decay).

    If drift still occurs: transport is NOT dissipation-driven.
    If drift disappears: transport IS 100% dissipation-driven.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: REMOVE DECAY — DIFFUSION + GRADIENT ONLY")
    print(f"  {'='*60}")
    print(f"  No lambda*sigma decay. Only diffusion.")
    print(f"  Gradient field present but passive.")
    print(f"  {'─'*60}")

    center = (nx // 2, ny // 2)
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    # Lambda gradient field (present but NOT used for decay)
    lam_bg = np.full((nx, ny), void_lambda)
    proj = (X - center[0]) * 1.0
    drive = -delta_lam * np.tanh(proj / 6.0)
    lam_field = np.maximum(lam_bg + drive, 0.005)

    initial_com = compute_com(sigma)
    E_initial = float(np.sum(sigma**2))
    prev_com = initial_com.copy()

    # Run with NO DECAY TERM
    print(f"  Running with diffusion only (no decay)...")

    displacements = []

    for step in range(steps):
        # ONLY diffusion — no decay
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt
        # NO: sigma -= lam_field * sigma * dt  (removed!)
        sigma = np.maximum(sigma, 0)

        com = compute_com(sigma)
        if com is not None and prev_com is not None:
            displacements.append(float(np.linalg.norm(com - prev_com)))
        prev_com = com

    final_com = compute_com(sigma)
    E_final = float(np.sum(sigma**2))
    no_decay_drift = 0
    if final_com is not None:
        no_decay_drift = float(np.linalg.norm(
            final_com - initial_com))

    print(f"    No-decay drift: {no_decay_drift:.6f} px")
    print(f"    E_initial: {E_initial:.4f}")
    print(f"    E_final:   {E_final:.4f}")

    # Run WITH decay for comparison
    print(f"\n  Running with decay (normal)...")
    sigma2 = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    prev_com2 = compute_com(sigma2)

    for step in range(steps):
        laplacian = (
            np.roll(sigma2, 1, axis=0) +
            np.roll(sigma2, -1, axis=0) +
            np.roll(sigma2, 1, axis=1) +
            np.roll(sigma2, -1, axis=1) -
            4 * sigma2
        )
        sigma2 += D * laplacian * dt
        sigma2 -= lam_field * sigma2 * dt  # decay active
        sigma2 = np.maximum(sigma2, 0)

    final_com2 = compute_com(sigma2)
    with_decay_drift = 0
    if final_com2 is not None:
        with_decay_drift = float(np.linalg.norm(
            final_com2 - initial_com))

    print(f"    With-decay drift: {with_decay_drift:.6f} px")

    print(f"\n  COMPARISON:")
    print(f"    No decay:   {no_decay_drift:.6f} px")
    print(f"    With decay: {with_decay_drift:.6f} px")

    if no_decay_drift < 0.01 and with_decay_drift > 0.1:
        print(f"\n    DRIFT REQUIRES DECAY.")
        print(f"    Transport is 100% dissipation-driven.")
        print(f"    The mechanism is selective survival —")
        print(f"    asymmetric decay shifts the COM.")
    elif no_decay_drift > 0.1:
        print(f"\n    DRIFT EXISTS WITHOUT DECAY.")
        print(f"    Transport has a non-dissipative component.")
    else:
        print(f"\n    Both minimal — inconclusive.")

    return {
        "no_decay_drift": round(no_decay_drift, 6),
        "with_decay_drift": round(with_decay_drift, 6),
        "E_initial": round(E_initial, 4),
        "E_final_no_decay": round(E_final, 4),
        "decay_required": no_decay_drift < 0.01 and with_decay_drift > 0.1,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 Rigid Body & Decay Isolation")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v13 RIGID BODY & DECAY ISOLATION")
    print(f"  The Eroding Dune or the Sailing Ship?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    # Test 1: Rigid body
    r1 = test_rigid_body(steps=args.steps, nx=nx, ny=ny)

    # Test 2: No decay
    r2 = test_no_decay(steps=args.steps, nx=nx, ny=ny)

    # Summary
    print(f"\n{'='*65}")
    print(f"  THE VERDICT")
    print(f"{'='*65}")
    print(f"  Rigid body drift:    {r1['total_drift']:.8f} px "
          f"({'MOVES' if r1['moved'] else 'STATIC'})")
    print(f"  No-decay drift:     {r2['no_decay_drift']:.6f} px")
    print(f"  With-decay drift:   {r2['with_decay_drift']:.6f} px")

    print(f"\n  MECHANISM:")
    if r1['moved'] and not r2['decay_required']:
        print(f"  GEOMETRIC TRANSPORT — rigid body moves,")
        print(f"  decay not required. The ship sails.")
    elif r1['moved'] and r2['decay_required']:
        print(f"  MIXED — rigid body moves but decay amplifies.")
        print(f"  Geometric component + dissipation component.")
    elif not r1['moved'] and r2['decay_required']:
        print(f"  SELECTIVE SURVIVAL — no rigid translation,")
        print(f"  decay is required. The dune erodes.")
    else:
        print(f"  INCONCLUSIVE — further testing needed.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_rigid_body_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 Rigid Body & Decay Isolation",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Eroding dune or sailing ship?",
        "grid": nx,
        "steps": args.steps,
        "results": {
            "rigid_body": r1,
            "decay_isolation": r2,
        },
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
