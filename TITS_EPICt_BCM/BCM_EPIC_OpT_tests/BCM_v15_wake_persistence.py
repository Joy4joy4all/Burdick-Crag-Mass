# -*- coding: utf-8 -*-
"""
BCM v15 — Wake Persistence Test (Exhaust Model A)
====================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The ship moves through the substrate. Behind it, the
exhaust deposits energy into the lambda field. Two
questions:

  1. Does the wake PERSIST or does the substrate ripple
     back to baseline? If it cools rapidly, void is dark
     because exhausted substrate loses spin and returns
     to ground state. The absence of potential hidden
     particles that lose spin.

  2. What does the SHEETING look like in drag on aft?
     Is there a coherent pattern behind the ship, or
     does the wake dissolve isotropically?

METHOD:
  Phase 1 (0 to pump_off_step): Ship runs with full
    regulator. Lambda field is coupled — sigma deposits
    into lambda via exhaust term.

  Phase 2 (pump_off_step to end): Ship stops. Monitor
    the lambda field residuals. Measure:
    - Wake amplitude vs time (cooling curve)
    - Wake spatial extent (sheeting width)
    - Fore/aft asymmetry (drag signature)
    - Time to return to baseline (substrate memory)

  Phase 3: Snapshot the lambda field at multiple times
    after shutdown to see the sheeting dissolve.

Usage:
    python BCM_v15_wake_persistence.py
    python BCM_v15_wake_persistence.py --steps 3000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


def compute_com(field):
    total = np.sum(field)
    if total < 1e-15:
        return None
    nx, ny = field.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X * field) / total,
                     np.sum(Y * field) / total])


def compute_coherence(sigma, center, radius=8):
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    r2 = (X - center[0])**2 + (Y - center[1])**2
    inside = np.sum(sigma[r2 < radius**2])
    total = np.sum(sigma)
    if total < 1e-15:
        return 0.0
    return inside / total


def measure_wake(lam_field, lam_baseline, com_x, com_y, nx, ny):
    """
    Measure the wake behind the ship (aft of COM).

    Returns wake metrics:
    - aft_residual: mean lambda deviation behind ship
    - fore_residual: mean lambda deviation ahead of ship
    - wake_peak: maximum single-point deviation in aft
    - wake_width: how many columns show deviation > threshold
    - asymmetry: aft_residual / fore_residual ratio
    """
    delta_lam = lam_field - lam_baseline

    ix = int(round(com_x))
    ix = max(0, min(ix, nx - 1))
    iy = int(round(com_y))

    # Aft region: everything behind the ship (x < COM)
    # Fore region: everything ahead (x > COM)
    aft_mask = np.zeros((nx, ny), dtype=bool)
    fore_mask = np.zeros((nx, ny), dtype=bool)

    # Wake band: within 15 px of the centerline (y-axis)
    y = np.arange(ny)
    band = np.abs(y - iy) < 15

    for col in range(nx):
        if col < ix:
            aft_mask[col, band] = True
        elif col > ix:
            fore_mask[col, band] = True

    aft_pixels = delta_lam[aft_mask]
    fore_pixels = delta_lam[fore_mask]

    aft_residual = float(np.mean(np.abs(aft_pixels))) if len(aft_pixels) > 0 else 0
    fore_residual = float(np.mean(np.abs(fore_pixels))) if len(fore_pixels) > 0 else 0
    wake_peak = float(np.max(np.abs(aft_pixels))) if len(aft_pixels) > 0 else 0

    # Wake width: count columns behind ship with mean
    # deviation above threshold
    threshold = 0.0001
    wake_cols = 0
    for col in range(ix):
        col_dev = float(np.mean(np.abs(delta_lam[col, band])))
        if col_dev > threshold:
            wake_cols += 1

    # Asymmetry: how much stronger is aft vs fore
    if fore_residual > 1e-15:
        asymmetry = aft_residual / fore_residual
    else:
        asymmetry = float('inf') if aft_residual > 0 else 1.0

    return {
        "aft_residual": round(aft_residual, 10),
        "fore_residual": round(fore_residual, 10),
        "wake_peak": round(wake_peak, 10),
        "wake_width_cols": wake_cols,
        "asymmetry": round(asymmetry, 6),
    }


def extract_wake_profile(lam_field, lam_baseline, com_x, com_y, nx, ny):
    """
    Extract a 1D wake profile along the ship's path
    (x-axis, at the centerline y).
    Returns lambda deviation at each x position.
    """
    iy = int(round(com_y))
    iy = max(0, min(iy, ny - 1))

    # Average over a 5-pixel band around centerline
    y_lo = max(0, iy - 2)
    y_hi = min(ny, iy + 3)

    delta_lam = lam_field - lam_baseline
    profile = np.mean(delta_lam[:, y_lo:y_hi], axis=1)

    return [round(float(v), 10) for v in profile]


def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 Wake Persistence Test")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=128)
    parser.add_argument("--pump-off", type=int, default=1000,
                        help="Step at which pumps turn off")
    args = parser.parse_args()

    nx = ny = args.grid
    pump_off_step = args.pump_off

    print(f"\n{'='*65}")
    print(f"  BCM v15 — WAKE PERSISTENCE TEST")
    print(f"  Does the exhaust cool or persist?")
    print(f"  What does the sheeting look like on aft?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Total steps: {args.steps}")
    print(f"  Pumps ON: steps 0-{pump_off_step}")
    print(f"  Pumps OFF: steps {pump_off_step}-{args.steps}")

    # Parameters
    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    alpha = 0.80
    cv_strength = 0.2
    exhaust_coupling = 0.002  # how strongly sigma deposits into lambda

    # Regulator parameters
    base_ratio = 0.125
    target_lambda = 0.05
    min_sep = 8.0
    max_sep = 25.0

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Initial sigma packet
    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    # Lambda field — starts uniform
    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    lam_baseline = lam_field.copy()

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()
    shutdown_com = None

    # Tracking
    wake_timeline = []
    cooling_curve = []
    profiles = {}
    ship_path = []

    print(f"\n  Phase 1: PUMPS ON (building wake)")
    print(f"  {'─'*55}")

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            print(f"  DISSOLVED at step {step}")
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        pumps_on = step < pump_off_step

        if pumps_on:
            # Telescope
            v_norm = min(speed / 0.02, 1.0)
            sep = min_sep + (max_sep - min_sep) * v_norm

            # Governor
            ix_g = min(max(int(com[0]), 0), nx - 1)
            iy_g = min(max(int(com[1]), 0), ny - 1)
            local_lam = float(lam_field[ix_g, iy_g])
            error = local_lam - target_lambda
            if error > 0:
                boost = min(error * 5.0, 1.0)
                ratio = base_ratio + (0.50 - base_ratio) * boost
            else:
                ratio = max(0.03, base_ratio + error)

            # Apply pumps
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            bx = com[0] + sep
            r2_B = (X - bx)**2 + (Y - com[1])**2
            actual_B = pump_A * ratio
            pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

            # ── EXHAUST COUPLING ──
            # The ship's sigma field deposits energy into
            # the lambda field behind it. This is the wake.
            # Deposit is weighted by sigma intensity and
            # biased toward the aft (behind COM).
            aft_weight = np.ones((nx, ny))
            for col in range(nx):
                if col < int(com[0]):
                    # Behind ship: full deposit
                    aft_weight[col, :] = 1.0
                elif col < int(com[0]) + 5:
                    # At ship: partial
                    aft_weight[col, :] = 0.3
                else:
                    # Ahead: minimal
                    aft_weight[col, :] = 0.05

            exhaust = exhaust_coupling * sigma * aft_weight * dt
            lam_field = lam_field - exhaust  # reduce lambda = fund substrate
            lam_field = np.maximum(lam_field, 0.001)

        else:
            # Pumps off — record shutdown position once
            if shutdown_com is None:
                shutdown_com = com.copy()
                print(f"\n  Phase 2: PUMPS OFF at step {step}")
                print(f"  Ship position at shutdown: "
                      f"({com[0]:.2f}, {com[1]:.2f})")
                print(f"  Monitoring wake cooling...")
                print(f"  {'─'*55}")

        # Evolve PDE (always, even with pumps off)
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = sigma + D * laplacian * dt - lam_field * sigma * dt

        # Memory term
        if alpha > 0:
            sigma_new = sigma_new + alpha * (sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        # Check valve (only when pumps on)
        if pumps_on and cv_strength > 0:
            flow = sigma_new - sigma
            flow_grad_x = (np.roll(flow, -1, axis=0) -
                           np.roll(flow, 1, axis=0)) / 2.0
            backflow = flow_grad_x < 0
            valve = np.ones_like(sigma_new)
            valve[backflow] = 1.0 - cv_strength
            sigma_new = sigma_new * valve

        if float(np.max(sigma_new)) > 1e10:
            print(f"  BLOWUP at step {step}")
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Track ship path
        if step % 20 == 0:
            ship_path.append({
                "step": step,
                "x": round(float(com[0]), 4),
                "y": round(float(com[1]), 4),
                "speed": round(speed, 8),
            })

        # ── Wake measurements ──
        if step % 100 == 0 or step == args.steps - 1:
            wake = measure_wake(lam_field, lam_baseline,
                                float(com[0]), float(com[1]),
                                nx, ny)
            drift = float(np.linalg.norm(com - initial_com))
            coh = compute_coherence(sigma, com)

            wake_entry = {
                "step": step,
                "phase": "ON" if pumps_on else "OFF",
                "drift": round(drift, 4),
                "coherence": round(coh, 4),
                "speed": round(speed, 8),
            }
            wake_entry.update(wake)
            wake_timeline.append(wake_entry)

            if pumps_on:
                if step % 200 == 0:
                    print(f"  step {step:>5}  drift={drift:>8.2f}  "
                          f"aft={wake['aft_residual']:.8f}  "
                          f"wake_w={wake['wake_width_cols']:>3}")

        # Cooling curve: after pumps off, measure how
        # fast the wake returns to baseline
        if not pumps_on and step % 50 == 0:
            total_deviation = float(
                np.sum(np.abs(lam_field - lam_baseline)))
            max_deviation = float(
                np.max(np.abs(lam_field - lam_baseline)))
            steps_since_off = step - pump_off_step

            cooling_curve.append({
                "steps_since_off": steps_since_off,
                "total_deviation": round(total_deviation, 8),
                "max_deviation": round(max_deviation, 10),
            })

        # Snapshot profiles at key moments
        snapshot_steps = [pump_off_step - 1,
                         pump_off_step + 50,
                         pump_off_step + 200,
                         pump_off_step + 500,
                         pump_off_step + 1000,
                         args.steps - 1]
        if step in snapshot_steps:
            profile = extract_wake_profile(
                lam_field, lam_baseline,
                float(com[0]), float(com[1]), nx, ny)
            profiles[f"step_{step}"] = profile

        # Lambda field recovery: does it ripple back?
        # After pumps off, the PDE's lambda*sigma term
        # and diffusion should restore the field.
        # But lambda itself has no PDE — it was modified
        # by the exhaust. We need to add substrate
        # self-healing: lambda relaxes back to baseline.
        if not pumps_on:
            # Substrate relaxation: lambda drifts back
            # toward baseline at a rate proportional to
            # deviation. This is the "ripple back."
            relax_rate = 0.005  # slow relaxation
            lam_field = lam_field + relax_rate * (lam_baseline - lam_field) * dt

        prev_com = com

    # ── Final Analysis ──
    print(f"\n{'='*65}")
    print(f"  WAKE PERSISTENCE ANALYSIS")
    print(f"{'='*65}")

    # Cooling curve analysis
    if len(cooling_curve) > 1:
        initial_dev = cooling_curve[0]["total_deviation"]
        final_dev = cooling_curve[-1]["total_deviation"]
        if initial_dev > 0:
            retention = final_dev / initial_dev
        else:
            retention = 0

        # Find half-life
        half_target = initial_dev / 2.0
        half_life = None
        for c in cooling_curve:
            if c["total_deviation"] < half_target:
                half_life = c["steps_since_off"]
                break

        print(f"\n  COOLING CURVE:")
        print(f"  {'─'*50}")
        print(f"  Initial wake deviation: {initial_dev:.8f}")
        print(f"  Final wake deviation:   {final_dev:.8f}")
        print(f"  Retention ratio:        {retention:.6f}")
        if half_life is not None:
            print(f"  Wake half-life:         {half_life} steps")
        else:
            print(f"  Wake half-life:         > {cooling_curve[-1]['steps_since_off']} steps (did not reach 50%)")

        print(f"\n  Cooling samples:")
        print(f"  {'Steps OFF':>12} {'Total Dev':>14} {'Max Dev':>14}")
        print(f"  {'─'*12} {'─'*14} {'─'*14}")
        for c in cooling_curve[::2]:  # every other
            print(f"  {c['steps_since_off']:>12} "
                  f"{c['total_deviation']:>14.8f} "
                  f"{c['max_deviation']:>14.10f}")

    # Fore/aft asymmetry analysis
    print(f"\n  SHEETING ANALYSIS (Fore/Aft Asymmetry):")
    print(f"  {'─'*50}")
    print(f"  {'Step':>6} {'Phase':>5} {'Aft':>12} {'Fore':>12} "
          f"{'Asym':>8} {'Width':>6}")
    print(f"  {'─'*6} {'─'*5} {'─'*12} {'─'*12} {'─'*8} {'─'*6}")
    for w in wake_timeline[::2]:
        print(f"  {w['step']:>6} {w['phase']:>5} "
              f"{w['aft_residual']:>12.8f} "
              f"{w['fore_residual']:>12.8f} "
              f"{w['asymmetry']:>8.4f} "
              f"{w['wake_width_cols']:>6}")

    # Verdict
    print(f"\n  {'─'*50}")
    has_wake = any(w["aft_residual"] > 1e-6 for w in wake_timeline)
    has_asymmetry = any(w["asymmetry"] > 1.5 for w in wake_timeline
                        if w["phase"] == "ON")
    cools_down = retention < 0.5 if len(cooling_curve) > 1 else False

    if has_wake and has_asymmetry and cools_down:
        verdict = "WAKE EXISTS — COOLS RAPIDLY"
        interpretation = (
            "The exhaust creates a measurable aft-biased "
            "lambda distortion (sheeting). The substrate "
            "ripples back to baseline after shutdown. "
            "The wake is real but transient — consistent "
            "with Stephen's prediction that void is dark "
            "because exhausted substrate loses spin and "
            "returns to ground state.")
    elif has_wake and has_asymmetry and not cools_down:
        verdict = "WAKE EXISTS — PERSISTS"
        interpretation = (
            "The exhaust creates a persistent aft-biased "
            "distortion. The substrate does NOT ripple back. "
            "The wake is a permanent scar in the lambda field.")
    elif has_wake and not has_asymmetry:
        verdict = "WAKE EXISTS — NO SHEETING"
        interpretation = (
            "Lambda distortion detected but no fore/aft "
            "asymmetry. The wake is isotropic, not sheeted.")
    else:
        verdict = "NO WAKE"
        interpretation = (
            "No measurable lambda distortion. The exhaust "
            "coupling is too weak or the substrate is rigid.")

    print(f"  VERDICT: {verdict}")
    print(f"  {interpretation}")
    print(f"  {'─'*50}")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_wake_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v15 Wake Persistence Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Does the exhaust cool or persist? What does sheeting look like?",
        "grid": nx,
        "steps": args.steps,
        "pump_off_step": pump_off_step,
        "parameters": {
            "dt": dt, "D": D, "void_lambda": void_lambda,
            "pump_A": pump_A, "alpha": alpha,
            "cv_strength": cv_strength,
            "exhaust_coupling": exhaust_coupling,
            "relax_rate": 0.005,
        },
        "verdict": verdict,
        "interpretation": interpretation,
        "wake_timeline": wake_timeline,
        "cooling_curve": cooling_curve,
        "profiles": profiles,
        "ship_path": ship_path,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
