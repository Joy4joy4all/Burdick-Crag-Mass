# -*- coding: utf-8 -*-
"""
BCM v14 — Propulsion Regulator
=================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

From satellite to locomotive. Three mill-engineering
controls solve ChatGPT's symmetry problem:

  1. TELESCOPIC BRIDGE: Variable separation between pumps.
     Responds to velocity. Short = high torque. Long = cruise.

  2. PNEUMATIC GOVERNOR: Pump ratio adjusts based on local
     lambda. Substrate thins → governor throttles B down
     to maintain gradient.

  3. CHECK VALVE: Nonlinear rectifier. Energy flows INTO
     the sigma structure but cannot wash back out
     symmetrically. Breaks the symmetry that killed
     Phase C transport.

Usage:
    python BCM_propulsion_regulator.py
    python BCM_propulsion_regulator.py --steps 1500 --grid 128
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


class PropulsionRegulator:
    """
    Mill-engineering control system for binary pump drive.

    Telescopic bridge: separation adjusts with velocity.
    Pneumatic governor: ratio adjusts with local lambda.
    Check valve: rectifies energy flow (asymmetric decay).
    """

    def __init__(self, base_separation=15.0,
                  min_separation=8.0, max_separation=25.0,
                  base_ratio=0.125,
                  min_ratio=0.03, max_ratio=0.50,
                  target_lambda=0.05,
                  check_valve_strength=0.3,
                  alpha=0.80):
        # Telescopic bridge
        self.base_sep = base_separation
        self.min_sep = min_separation
        self.max_sep = max_separation
        self.current_sep = base_separation

        # Pneumatic governor
        self.base_ratio = base_ratio
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.current_ratio = base_ratio
        self.target_lambda = target_lambda

        # Check valve
        self.cv_strength = check_valve_strength

        # Memory
        self.alpha = alpha

        # Telemetry
        self.log = []

    def update_telescope(self, velocity, max_velocity=0.02):
        """
        Adjust bridge length based on velocity.
        Low velocity → short bridge (high torque, maneuvering)
        High velocity → long bridge (cruise efficiency)
        """
        v_norm = min(velocity / max_velocity, 1.0)

        # Linear interpolation: slow=short, fast=long
        self.current_sep = (self.min_sep +
                             (self.max_sep - self.min_sep) * v_norm)

        return self.current_sep

    def update_governor(self, local_lambda):
        """
        Adjust pump ratio based on local substrate density.
        High lambda (void) → increase ratio (more B power)
        Low lambda (funded) → decrease ratio (less B needed)
        """
        # Error signal: how far are we from target?
        error = local_lambda - self.target_lambda

        if error > 0:
            # Substrate thinner than target — boost B
            boost = min(error * 5.0, 1.0)
            self.current_ratio = self.base_ratio + (
                self.max_ratio - self.base_ratio) * boost
        else:
            # Substrate funded — reduce B
            self.current_ratio = max(self.min_ratio,
                                       self.base_ratio + error)

        return self.current_ratio

    def apply_check_valve(self, sigma, sigma_prev, direction):
        """
        Rectification: allow energy to flow in the drive
        direction but resist backflow.

        The check valve applies asymmetric damping:
        - Forward flow (in drive direction): pass through
        - Backward flow (against drive): attenuate

        This breaks the symmetry that killed transport.
        """
        nx, ny = sigma.shape
        x = np.arange(nx)
        y = np.arange(ny)
        X, Y = np.meshgrid(x, y, indexing='ij')

        # Compute flow direction at each point
        flow = sigma - sigma_prev

        # Project flow onto drive direction
        d = np.array(direction, dtype=float)
        d /= (np.linalg.norm(d) + 1e-12)

        # Gradient of flow in drive direction
        flow_grad_x = (np.roll(flow, -1, axis=0) -
                         np.roll(flow, 1, axis=0)) / 2.0
        flow_grad_y = (np.roll(flow, -1, axis=1) -
                         np.roll(flow, 1, axis=1)) / 2.0

        # Projection onto drive direction
        proj = flow_grad_x * d[0] + flow_grad_y * d[1]

        # Check valve: attenuate BACKWARD flow
        # (negative projection = backward)
        backflow_mask = proj < 0
        valve = np.ones_like(sigma)
        valve[backflow_mask] = 1.0 - self.cv_strength

        return sigma * valve

    def record(self, step, sep, ratio, velocity, coh):
        self.log.append({
            "step": step,
            "separation": round(sep, 4),
            "ratio": round(ratio, 6),
            "velocity": round(velocity, 10),
            "coherence": round(coh, 4),
        })


def run_regulated(steps, nx, ny, dt, D, pump_A,
                    void_lambda, regulator,
                    pump_on_steps=None,
                    label="REGULATED"):
    """
    Run binary pump with full regulation:
    telescopic bridge + pneumatic governor + check valve.
    """
    if pump_on_steps is None:
        pump_on_steps = steps  # always on

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    lam_field = np.full((nx, ny), void_lambda)
    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    speeds = []
    speeds_on = []
    speeds_off = []
    direction = np.array([1.0, 0.0])

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Measure velocity
        velocity = 0
        if prev_com is not None:
            velocity = float(np.linalg.norm(com - prev_com))
        speeds.append(velocity)

        # Measure local lambda at ship position
        ix = min(max(int(com[0]), 0), nx - 1)
        iy = min(max(int(com[1]), 0), ny - 1)
        local_lam = float(lam_field[ix, iy])

        pumps_active = step < pump_on_steps

        if pumps_active:
            # Update regulators
            sep = regulator.update_telescope(velocity)
            ratio = regulator.update_governor(local_lam)

            # Pump A at COM
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            # Pump B at telescopic distance
            bx = com[0] + sep
            r2_B = (X - bx)**2 + (Y - com[1])**2
            pump_B = pump_A * ratio
            pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

        # Evolve
        laplacian = (
            np.roll(sigma, 1, axis=0) +
            np.roll(sigma, -1, axis=0) +
            np.roll(sigma, 1, axis=1) +
            np.roll(sigma, -1, axis=1) -
            4 * sigma
        )
        sigma_new = (sigma + D * laplacian * dt
                      - lam_field * sigma * dt)

        # Memory term
        if regulator.alpha > 0:
            sigma_new = sigma_new + regulator.alpha * (
                sigma - sigma_prev)

        sigma_new = np.maximum(sigma_new, 0)

        # Check valve (rectification)
        if pumps_active and regulator.cv_strength > 0:
            sigma_new = regulator.apply_check_valve(
                sigma_new, sigma, direction)

        # Blowup check
        if float(np.max(sigma_new)) > 1e10:
            return {
                "stable": False, "blowup_step": step,
                "label": label,
            }

        sigma_prev = sigma.copy()
        sigma = sigma_new

        new_com = compute_com(sigma)
        if new_com is not None:
            spd = float(np.linalg.norm(new_com - com))
            if pumps_active:
                speeds_on.append(spd)
            else:
                speeds_off.append(spd)

            coh = compute_coherence(sigma, new_com)
            if step % 100 == 0:
                regulator.record(step,
                    regulator.current_sep,
                    regulator.current_ratio,
                    velocity, coh)
        prev_com = new_com

    final_com = compute_com(sigma)
    drift = 0
    if final_com is not None and initial_com is not None:
        drift = float(np.linalg.norm(final_com - initial_com))

    avg_on = float(np.mean(speeds_on)) if speeds_on else 0
    avg_off = float(np.mean(speeds_off)) if speeds_off else 0
    retention = avg_off / avg_on if avg_on > 0 else 0
    J = sum(speeds_off)

    return {
        "label": label,
        "stable": True,
        "drift": round(drift, 6),
        "avg_on": round(avg_on, 10),
        "avg_off": round(avg_off, 10),
        "retention": round(retention, 8),
        "transport_J": round(J, 6),
        "telemetry": regulator.log,
    }


# ============================================================
# TEST 1: REGULATED vs UNREGULATED
# ============================================================
def test_regulated_vs_fixed(steps=1500, nx=128, ny=128,
                              dt=0.05, D=0.5, pump_A=0.5,
                              void_lambda=0.10):
    """
    Compare: fixed parameters vs full regulation.
    Both with memory (alpha=0.80).
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: REGULATED vs FIXED PARAMETERS")
    print(f"  {'='*60}")

    # Fixed (old way)
    reg_fixed = PropulsionRegulator(
        base_separation=15.0, min_separation=15.0,
        max_separation=15.0,
        base_ratio=0.125, min_ratio=0.125, max_ratio=0.125,
        check_valve_strength=0.0, alpha=0.80)

    r_fixed = run_regulated(steps, nx, ny, dt, D, pump_A,
                              void_lambda, reg_fixed,
                              label="FIXED")

    # Regulated (new way)
    reg_full = PropulsionRegulator(
        base_separation=15.0, min_separation=8.0,
        max_separation=25.0,
        base_ratio=0.125, min_ratio=0.03, max_ratio=0.50,
        check_valve_strength=0.3, alpha=0.80)

    r_full = run_regulated(steps, nx, ny, dt, D, pump_A,
                             void_lambda, reg_full,
                             label="REGULATED")

    if not r_fixed.get("stable") or not r_full.get("stable"):
        print(f"  One or both BLEW UP")
        return r_fixed, r_full

    print(f"  {'':>16} {'FIXED':>14} {'REGULATED':>14}")
    print(f"  {'─'*16} {'─'*14} {'─'*14}")
    print(f"  {'Drift':>16} {r_fixed['drift']:>14.4f} "
          f"{r_full['drift']:>14.4f}")
    print(f"  {'Speed':>16} {r_fixed['avg_on']:>14.8f} "
          f"{r_full['avg_on']:>14.8f}")
    print(f"  {'Stable':>16} {'YES' if r_fixed['stable'] else 'NO':>14} "
          f"{'YES' if r_full['stable'] else 'NO':>14}")

    if r_full["drift"] > r_fixed["drift"]:
        ratio = r_full["drift"] / r_fixed["drift"]
        print(f"\n  REGULATION IMPROVES DRIFT by {ratio:.2f}x")
    else:
        print(f"\n  Fixed outperforms regulation.")

    return r_fixed, r_full


# ============================================================
# TEST 2: CHECK VALVE STRENGTH SWEEP
# ============================================================
def test_check_valve(steps=1500, nx=128, ny=128,
                       dt=0.05, D=0.5, pump_A=0.5,
                       void_lambda=0.10):
    """
    Sweep check valve strength from 0 to 0.9.
    Does rectification produce transport after pumps off?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: CHECK VALVE STRENGTH SWEEP")
    print(f"  {'='*60}")
    print(f"  Pumps ON 400 steps, OFF remainder.")
    print(f"  Does rectification retain transport?")
    print(f"  {'─'*60}")

    cv_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    results = []
    pump_on_steps = 400

    print(f"  {'CV':>6} {'Drift':>10} {'Retention':>12} "
          f"{'J_off':>12} {'Status':>8}")
    print(f"  {'─'*6} {'─'*10} {'─'*12} {'─'*12} {'─'*8}")

    for cv in cv_values:
        reg = PropulsionRegulator(
            check_valve_strength=cv, alpha=0.80)

        r = run_regulated(steps, nx, ny, dt, D, pump_A,
                            void_lambda, reg,
                            pump_on_steps=pump_on_steps,
                            label=f"CV={cv}")

        if not r.get("stable"):
            print(f"  {cv:>6.1f} {'BLOWUP':>10}")
            results.append({"cv": cv, "stable": False})
            continue

        status = "RETAIN" if r["retention"] > 0.01 else "LOST"
        print(f"  {cv:>6.1f} {r['drift']:>10.4f} "
              f"{r['retention']*100:>11.4f}% "
              f"{r['transport_J']:>12.6f} {status:>8}")

        r["cv"] = cv
        results.append(r)

    return results


# ============================================================
# TEST 3: VOID LAMBDA SWEEP WITH GOVERNOR
# ============================================================
def test_governor_adaptation(steps=1500, nx=128, ny=128,
                                dt=0.05, D=0.5, pump_A=0.5):
    """
    Sweep void lambda from 0.05 to 0.50.
    Does the pneumatic governor maintain transport
    across varying substrate density?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: GOVERNOR ADAPTATION vs VOID DEPTH")
    print(f"  {'='*60}")
    print(f"  Does the governor maintain transport in deep void?")
    print(f"  {'─'*60}")

    void_lambdas = [0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50]
    results_fixed = []
    results_governed = []

    print(f"  {'Void_lam':>10} {'Fixed Drift':>12} "
          f"{'Gov Drift':>12} {'Improvement':>12}")
    print(f"  {'─'*10} {'─'*12} {'─'*12} {'─'*12}")

    for vl in void_lambdas:
        # Fixed
        reg_f = PropulsionRegulator(
            base_separation=15.0, min_separation=15.0,
            max_separation=15.0,
            base_ratio=0.125, min_ratio=0.125,
            max_ratio=0.125,
            check_valve_strength=0.0, alpha=0.80)

        r_f = run_regulated(steps, nx, ny, dt, D, pump_A,
                              vl, reg_f, label="FIXED")

        # Governed
        reg_g = PropulsionRegulator(
            base_separation=15.0, min_separation=8.0,
            max_separation=25.0,
            base_ratio=0.125, min_ratio=0.03,
            max_ratio=0.50,
            target_lambda=0.05,
            check_valve_strength=0.3, alpha=0.80)

        r_g = run_regulated(steps, nx, ny, dt, D, pump_A,
                              vl, reg_g, label="GOVERNED")

        d_f = r_f.get("drift", 0) if r_f.get("stable") else 0
        d_g = r_g.get("drift", 0) if r_g.get("stable") else 0
        imp = d_g / d_f if d_f > 0 else 0

        print(f"  {vl:>10.2f} {d_f:>12.4f} {d_g:>12.4f} "
              f"{imp:>11.2f}x")

        results_fixed.append({"void_lambda": vl, "drift": d_f,
                                "stable": r_f.get("stable")})
        results_governed.append({"void_lambda": vl, "drift": d_g,
                                   "stable": r_g.get("stable")})

    return results_fixed, results_governed


def main():
    parser = argparse.ArgumentParser(
        description="BCM v14 Propulsion Regulator")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v14 — PROPULSION REGULATOR")
    print(f"  Telescopic bridge + Pneumatic governor + Check valve")
    print(f"  From satellite to locomotive.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")

    all_results = {}

    # Test 1
    r1_f, r1_g = test_regulated_vs_fixed(
        steps=args.steps, nx=nx, ny=ny)
    all_results["regulated_vs_fixed"] = {
        "fixed": r1_f, "regulated": r1_g}

    # Test 2
    r2 = test_check_valve(steps=args.steps, nx=nx, ny=ny)
    all_results["check_valve_sweep"] = r2

    # Test 3
    r3_f, r3_g = test_governor_adaptation(
        steps=args.steps, nx=nx, ny=ny)
    all_results["governor_adaptation"] = {
        "fixed": r3_f, "governed": r3_g}

    # Summary
    print(f"\n{'='*65}")
    print(f"  PROPULSION REGULATOR SUMMARY")
    print(f"{'='*65}")

    if r1_f.get("stable") and r1_g.get("stable"):
        print(f"  Fixed drift:     {r1_f.get('drift',0):.4f}")
        print(f"  Regulated drift: {r1_g.get('drift',0):.4f}")

    # Best check valve
    valid_cv = [r for r in r2 if r.get("stable") and r.get("retention", 0) > 0]
    if valid_cv:
        best_cv = max(valid_cv, key=lambda r: r.get("transport_J", 0))
        print(f"  Best check valve: CV={best_cv.get('cv',0)} "
              f"(J={best_cv.get('transport_J',0):.6f})")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_propulsion_reg_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v14 Propulsion Regulator",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Telescopic bridge + governor + check valve",
        "grid": nx,
        "steps": args.steps,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
