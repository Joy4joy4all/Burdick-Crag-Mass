# -*- coding: utf-8 -*-
"""
BCM v12 Lambda Drift Test — Kill Condition
============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
Test design: ChatGPT advisory

PURPOSE: Determine if spatial lambda gradients induce sustained
translation of a coherent sigma structure.

If YES → lambda drive hypothesis survives
If NO  → propulsion concept is dead, coherence physics survives

Two runs:
  A) Lambda gradient active (fore/aft asymmetry)
  B) Lambda constant (control — no gradient)

Compare trajectories. If no divergence, lambda does not
produce motion. Kill condition triggered.

Usage:
    python BCM_drift_test.py
    python BCM_drift_test.py --steps 3000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


def build_lambda_field(nx, ny, base_lam=0.1, delta_lam=0.05,
                        ship_pos=None, direction=(1, 0),
                        spread=10.0):
    """
    Creates a smooth lambda dipole centered on ship position:
    - lower lambda ahead (deeper substrate memory)
    - higher lambda behind (faster decay / shallower memory)

    Uses tanh profile for smooth transition.
    """
    if ship_pos is None:
        ship_pos = (nx // 2, ny // 2)

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - ship_pos[0]
    dy = Y - ship_pos[1]

    # Normalize direction
    d = np.array(direction, dtype=float)
    d /= (np.linalg.norm(d) + 1e-12)

    # Project position onto direction axis
    proj = dx * d[0] + dy * d[1]

    # Smooth dipole: positive proj = ahead = LOWER lambda
    # negative proj = behind = HIGHER lambda
    profile = np.tanh(proj / spread)

    lam_field = base_lam - delta_lam * profile

    return lam_field


def initialize_sigma_packet(nx, ny, center, amplitude=1.0,
                             width=5.0):
    """Create a Gaussian sigma packet (the 'ship')."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2

    sigma = amplitude * np.exp(-r2 / (2 * width**2))
    return sigma


def compute_center_of_mass(sigma):
    """Track the center of mass of the sigma field."""
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
    """Measure how much of the packet remains coherent."""
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


def run_drift_test(steps=2000, nx=128, ny=128, dt=0.05,
                    D=0.5, base_lam=0.1, delta_lam=0.05,
                    spread=10.0, use_gradient=True,
                    direction=(1, 0), label="ACTIVE"):
    """
    Run one drift test.

    use_gradient=True  → lambda dipole (test case)
    use_gradient=False → constant lambda (control)
    """
    # Initial ship position (center of grid)
    ship_pos = np.array([nx // 2, ny // 2], dtype=float)
    initial_pos = ship_pos.copy()

    # Initialize sigma packet
    sigma = initialize_sigma_packet(nx, ny, ship_pos,
                                     amplitude=1.0, width=5.0)
    initial_energy = np.sum(sigma**2)

    trajectory = []
    velocities = []
    coherences = []

    for step in range(steps):

        if use_gradient:
            # Build lambda field centered on CURRENT ship position
            lam_field = build_lambda_field(
                nx, ny, base_lam=base_lam,
                delta_lam=delta_lam,
                ship_pos=ship_pos,
                direction=direction,
                spread=spread)
        else:
            # Control: constant lambda everywhere
            lam_field = np.full((nx, ny), base_lam)

        # Diffusion (Laplacian)
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma += D * laplacian * dt

        # Lambda decay (THE CORE MECHANISM)
        sigma -= lam_field * sigma * dt

        # Clamp negatives
        sigma = np.maximum(sigma, 0)

        # Measure center of mass
        com = compute_center_of_mass(sigma)

        if com is None:
            print(f"    [{label}] Structure collapsed at step {step}")
            break

        # Velocity (pixel displacement per step)
        if len(trajectory) > 0:
            vel = com - trajectory[-1]
            velocities.append(vel.copy())

        # Coherence
        coh = compute_coherence(sigma, com, radius=10)
        coherences.append(coh)

        trajectory.append(com.copy())
        ship_pos = com

        # Periodic report
        if step % 500 == 0 or step == steps - 1:
            disp = com - initial_pos
            speed = np.linalg.norm(velocities[-1]) if velocities else 0
            energy = np.sum(sigma**2)
            print(f"    [{label}] step={step:>5}  "
                  f"pos=({com[0]:.2f},{com[1]:.2f})  "
                  f"disp=({disp[0]:+.4f},{disp[1]:+.4f})  "
                  f"speed={speed:.6f}  "
                  f"coh={coh:.4f}  "
                  f"E={energy:.4f}")

    trajectory = np.array(trajectory)
    velocities = np.array(velocities) if velocities else np.zeros((1, 2))

    return {
        "trajectory": trajectory,
        "velocities": velocities,
        "coherences": coherences,
        "initial_pos": initial_pos,
        "final_pos": trajectory[-1] if len(trajectory) > 0 else initial_pos,
        "initial_energy": initial_energy,
        "final_energy": float(np.sum(sigma**2)),
        "steps_completed": len(trajectory),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v12 Lambda Drift Kill Test")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--D", type=float, default=0.5,
                        help="Diffusion coefficient")
    parser.add_argument("--base-lam", type=float, default=0.1)
    parser.add_argument("--delta-lam", type=float, default=0.05)
    parser.add_argument("--spread", type=float, default=10.0)
    parser.add_argument("--reverse", action="store_true",
                        help="Add Run C: reversed gradient direction")
    args = parser.parse_args()

    drive_dir = (1, 0)  # +x

    print(f"\n{'='*65}")
    print(f"  BCM v12 LAMBDA DRIFT TEST — KILL CONDITION")
    print(f"  Grid: {args.grid}x{args.grid}  Steps: {args.steps}")
    print(f"  dt={args.dt}  D={args.D}")
    print(f"  base_lam={args.base_lam}  delta_lam={args.delta_lam}")
    print(f"  spread={args.spread}")
    print(f"  Drive direction: +x")
    if args.reverse:
        print(f"  REVERSAL TEST: will also run -x direction")
    print(f"{'='*65}")

    # RUN A: Lambda gradient active
    print(f"\n  RUN A: LAMBDA GRADIENT ACTIVE")
    print(f"  {'─'*50}")
    t0 = time.time()
    result_A = run_drift_test(
        steps=args.steps, nx=args.grid, ny=args.grid,
        dt=args.dt, D=args.D, base_lam=args.base_lam,
        delta_lam=args.delta_lam, spread=args.spread,
        use_gradient=True, label="LAMBDA")
    time_A = time.time() - t0

    # RUN B: Constant lambda (control)
    print(f"\n  RUN B: CONSTANT LAMBDA (CONTROL)")
    print(f"  {'─'*50}")
    t0 = time.time()
    result_B = run_drift_test(
        steps=args.steps, nx=args.grid, ny=args.grid,
        dt=args.dt, D=args.D, base_lam=args.base_lam,
        delta_lam=0.0, spread=args.spread,
        use_gradient=False, label="CONTROL")
    time_B = time.time() - t0

    # RUN C: Reversed gradient (if --reverse)
    result_C = None
    if args.reverse:
        print(f"\n  RUN C: REVERSED GRADIENT (-x)")
        print(f"  {'─'*50}")
        t0 = time.time()
        result_C = run_drift_test(
            steps=args.steps, nx=args.grid, ny=args.grid,
            dt=args.dt, D=args.D, base_lam=args.base_lam,
            delta_lam=args.delta_lam, spread=args.spread,
            use_gradient=True, direction=(-1, 0),
            label="REVERSE")
        time_C = time.time() - t0

    # COMPARISON
    print(f"\n  {'='*65}")
    print(f"  DRIFT TEST RESULTS")
    print(f"  {'='*65}")

    disp_A = result_A["final_pos"] - result_A["initial_pos"]
    disp_B = result_B["final_pos"] - result_B["initial_pos"]
    divergence = result_A["final_pos"] - result_B["final_pos"]

    mean_speed_A = float(np.mean(np.linalg.norm(
        result_A["velocities"], axis=1)))
    mean_speed_B = float(np.mean(np.linalg.norm(
        result_B["velocities"], axis=1)))
    final_speed_A = float(np.linalg.norm(
        result_A["velocities"][-1]))
    final_speed_B = float(np.linalg.norm(
        result_B["velocities"][-1]))

    print(f"\n  RUN A (Lambda gradient):")
    print(f"    Net displacement: ({disp_A[0]:+.6f}, "
          f"{disp_A[1]:+.6f})")
    print(f"    Total distance:   {np.linalg.norm(disp_A):.6f} px")
    print(f"    Mean speed:       {mean_speed_A:.8f} px/step")
    print(f"    Final speed:      {final_speed_A:.8f} px/step")
    print(f"    Final coherence:  "
          f"{result_A['coherences'][-1]:.4f}")
    print(f"    Energy ratio:     "
          f"{result_A['final_energy']/result_A['initial_energy']:.6f}")
    print(f"    Time: {time_A:.1f}s")

    print(f"\n  RUN B (Constant lambda — control):")
    print(f"    Net displacement: ({disp_B[0]:+.6f}, "
          f"{disp_B[1]:+.6f})")
    print(f"    Total distance:   {np.linalg.norm(disp_B):.6f} px")
    print(f"    Mean speed:       {mean_speed_B:.8f} px/step")
    print(f"    Final speed:      {final_speed_B:.8f} px/step")
    print(f"    Final coherence:  "
          f"{result_B['coherences'][-1]:.4f}")
    print(f"    Energy ratio:     "
          f"{result_B['final_energy']/result_B['initial_energy']:.6f}")
    print(f"    Time: {time_B:.1f}s")

    print(f"\n  DIVERGENCE (A - B):")
    print(f"    Position delta:   ({divergence[0]:+.6f}, "
          f"{divergence[1]:+.6f})")
    print(f"    Total divergence: "
          f"{np.linalg.norm(divergence):.6f} px")
    print(f"    Speed ratio A/B:  "
          f"{mean_speed_A/(mean_speed_B+1e-15):.4f}")

    # VERDICT
    print(f"\n  {'='*65}")
    drift_mag = np.linalg.norm(disp_A)
    div_mag = np.linalg.norm(divergence)

    if drift_mag > 0.1 and div_mag > 0.05:
        # Check if drift is in the drive direction (+x)
        if disp_A[0] > 0.05:
            print(f"  VERDICT: CASE C — SUSTAINED DRIFT DETECTED")
            print(f"  Direction: +x (aligned with drive)")
            print(f"  Lambda gradient PRODUCES translation.")
            print(f"  KILL CONDITION: SURVIVED")
        else:
            print(f"  VERDICT: DRIFT DETECTED but NOT aligned "
                  f"with drive direction")
            print(f"  May be artifact. Needs investigation.")
            print(f"  KILL CONDITION: INCONCLUSIVE")
    elif drift_mag > 0.01:
        print(f"  VERDICT: CASE B — TRANSIENT SHIFT")
        print(f"  Small displacement, not sustained propulsion.")
        print(f"  KILL CONDITION: PARTIAL FAIL")
    else:
        if div_mag < 0.01:
            print(f"  VERDICT: CASE A — NO MOVEMENT")
            print(f"  Lambda gradient does NOT produce drift.")
            print(f"  KILL CONDITION: TRIGGERED — drive hypothesis "
                  f"is dead")
        else:
            print(f"  VERDICT: CASE D — INSTABILITY")
            print(f"  Structure collapsed or oscillated.")
            print(f"  KILL CONDITION: TRIGGERED — coherence fails")

    print(f"  {'='*65}")

    # Reversal results
    if result_C is not None:
        disp_C = result_C["final_pos"] - result_C["initial_pos"]
        mean_speed_C = float(np.mean(np.linalg.norm(
            result_C["velocities"], axis=1)))

        print(f"\n  {'='*65}")
        print(f"  GRADIENT REVERSAL TEST")
        print(f"  {'='*65}")
        print(f"  Run A (+x): displacement = ({disp_A[0]:+.4f}, "
              f"{disp_A[1]:+.4f})")
        print(f"  Run C (-x): displacement = ({disp_C[0]:+.4f}, "
              f"{disp_C[1]:+.4f})")
        print(f"  Sum (should be ~0 if causal): "
              f"({disp_A[0]+disp_C[0]:+.4f}, "
              f"{disp_A[1]+disp_C[1]:+.4f})")
        ratio = abs(disp_C[0]) / (abs(disp_A[0]) + 1e-15)
        print(f"  Magnitude ratio |C|/|A|: {ratio:.4f} "
              f"(1.0 = perfect reversal)")

        if disp_C[0] < -0.05 and disp_A[0] > 0.05:
            print(f"\n  REVERSAL: CONFIRMED")
            print(f"  Drift direction is CAUSAL — tied to gradient")
            print(f"  The lambda drive steers. You point, it goes.")
        elif abs(disp_C[0]) < 0.01:
            print(f"\n  REVERSAL: FAILED — no drift in -x")
            print(f"  Drift may be a lattice artifact")
        else:
            print(f"\n  REVERSAL: PARTIAL — needs investigation")
        print(f"  {'='*65}")

    # Save results
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_drift_test_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v12 Lambda Drift Kill Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "test_design": "ChatGPT advisory",
        "grid": args.grid,
        "steps": args.steps,
        "dt": args.dt,
        "D": args.D,
        "base_lam": args.base_lam,
        "delta_lam": args.delta_lam,
        "spread": args.spread,
        "reversed": args.reverse,
        "run_A": {
            "label": "Lambda gradient active",
            "displacement": [float(disp_A[0]), float(disp_A[1])],
            "total_distance": float(np.linalg.norm(disp_A)),
            "mean_speed": mean_speed_A,
            "final_speed": final_speed_A,
            "final_coherence": result_A["coherences"][-1],
            "energy_ratio": result_A["final_energy"] /
                            result_A["initial_energy"],
            "steps_completed": result_A["steps_completed"],
        },
        "run_B": {
            "label": "Constant lambda (control)",
            "displacement": [float(disp_B[0]), float(disp_B[1])],
            "total_distance": float(np.linalg.norm(disp_B)),
            "mean_speed": mean_speed_B,
            "final_speed": final_speed_B,
            "final_coherence": result_B["coherences"][-1],
            "energy_ratio": result_B["final_energy"] /
                            result_B["initial_energy"],
            "steps_completed": result_B["steps_completed"],
        },
        "divergence": {
            "position_delta": [float(divergence[0]),
                                float(divergence[1])],
            "total_divergence": float(div_mag),
            "speed_ratio": mean_speed_A / (mean_speed_B + 1e-15),
        },
        "drift_magnitude": float(drift_mag),
        "verdict": (
            "CASE_C_SUSTAINED_DRIFT" if (drift_mag > 0.1 and
                div_mag > 0.05 and disp_A[0] > 0.05)
            else "CASE_B_TRANSIENT" if drift_mag > 0.01
            else "CASE_A_NO_MOVEMENT" if div_mag < 0.01
            else "CASE_D_INSTABILITY"
        ),
    }

    if result_C is not None:
        out_data["run_C"] = {
            "label": "Reversed gradient (-x)",
            "displacement": [float(disp_C[0]), float(disp_C[1])],
            "total_distance": float(np.linalg.norm(disp_C)),
            "mean_speed": mean_speed_C,
            "final_coherence": result_C["coherences"][-1],
            "steps_completed": result_C["steps_completed"],
        }
        out_data["reversal"] = {
            "sum_displacement": [float(disp_A[0]+disp_C[0]),
                                  float(disp_A[1]+disp_C[1])],
            "magnitude_ratio": float(ratio),
            "confirmed": bool(disp_C[0] < -0.05 and disp_A[0] > 0.05),
        }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Results saved: {out_path}")
    print(f"  Send this JSON to ChatGPT for analysis.")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
