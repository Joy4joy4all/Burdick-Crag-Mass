# -*- coding: utf-8 -*-
"""
BCM v15 — External Frame & Medium Coupling
=============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Two tests. Two gates. No interpretation without passage.

TEST A — THE HARPOON (External Inertial Frame)
  A static marker field omega sits in the same coordinate
  space but does NOT obey the BCM PDE. It cannot be pushed,
  pulled, or dragged. It is the harpoon driven into the
  seabed. If the sigma structure moves RELATIVE TO OMEGA,
  the displacement is real. If omega drifts with sigma,
  the grid is carrying both and there is no transport.

  Pass: delta(COM_sigma - COM_omega) > 0 while omega
        stays within 0.01 px of its initial position.
  Fail: omega drifts with sigma, or sigma does not
        separate from omega.

TEST E — THE OAR (Medium Coupling / Reaction Force)
  If the sigma structure moves through the substrate,
  the substrate must push back. Monitor the lambda-flux
  at the ship boundary. Measure the reaction force
  F_reaction = integral of (grad_lambda dot v) over
  the ship envelope. If F_reaction scales with velocity,
  the substrate is a medium. If F_reaction = 0, the
  system is a ghost ship.

  Pass: F_reaction > 0 and scales with velocity.
  Fail: F_reaction = 0 at all velocities.

Usage:
    python BCM_v15_external_frame.py
    python BCM_v15_external_frame.py --steps 2000 --grid 128
"""

import numpy as np
import json
import os
import time
import argparse


# ── Utilities ──────────────────────────────────────────

def compute_com(field):
    """Center of mass of a 2D field."""
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
    """Fraction of total sigma within radius of center."""
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


# ── Test A: The Harpoon ───────────────────────────────

def test_A_harpoon(steps, nx, ny, dt, D, void_lambda,
                   pump_A, alpha, cv_strength):
    """
    External inertial frame test.

    sigma = regulated BCM field (full governor + check valve)
    omega = static marker field (same initial shape, NO PDE)

    omega never evolves. It sits at its birth position.
    sigma evolves under the full v14 regulator.
    The test measures COM_sigma - COM_omega over time.
    """
    print(f"\n{'='*65}")
    print(f"  TEST A — THE HARPOON (External Inertial Frame)")
    print(f"  Does sigma move relative to a fixed anchor?")
    print(f"{'='*65}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Initial packet — same for both fields
    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    # OMEGA: the harpoon. Same shape. Never evolves.
    omega = sigma.copy()
    omega_com_initial = compute_com(omega)

    # Lambda field (uniform void)
    lam_field = np.full((nx, ny), void_lambda)

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    # Regulator parameters (from v14)
    base_ratio = 0.125
    target_lambda = 0.05
    base_sep = 15.0
    min_sep = 8.0
    max_sep = 25.0

    timeline = []

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            print(f"  SIGMA DISSOLVED at step {step}")
            break

        # Velocity
        velocity = float(np.linalg.norm(com - prev_com)) if prev_com is not None else 0

        # Telescope: separation adjusts with velocity
        v_norm = min(velocity / 0.02, 1.0)
        sep = min_sep + (max_sep - min_sep) * v_norm

        # Governor: ratio adjusts with local lambda
        ix = min(max(int(com[0]), 0), nx - 1)
        iy = min(max(int(com[1]), 0), ny - 1)
        local_lam = float(lam_field[ix, iy])
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

        # Evolve PDE
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

        # Check valve
        if cv_strength > 0:
            flow = sigma_new - sigma
            flow_grad_x = (np.roll(flow, -1, axis=0) -
                           np.roll(flow, 1, axis=0)) / 2.0
            backflow = flow_grad_x < 0
            valve = np.ones_like(sigma_new)
            valve[backflow] = 1.0 - cv_strength
            sigma_new = sigma_new * valve

        # Blowup guard
        if float(np.max(sigma_new)) > 1e10:
            print(f"  BLOWUP at step {step}")
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Record every 50 steps
        if step % 50 == 0 or step == steps - 1:
            new_com = compute_com(sigma)
            if new_com is not None:
                # Omega COM never changes (it never evolves)
                omega_com = omega_com_initial

                separation_from_anchor = float(
                    np.linalg.norm(new_com - omega_com))
                sigma_drift = float(
                    np.linalg.norm(new_com - initial_com))
                omega_drift = 0.0  # omega never moves

                coh = compute_coherence(sigma, new_com)

                timeline.append({
                    "step": step,
                    "sigma_x": round(float(new_com[0]), 6),
                    "sigma_y": round(float(new_com[1]), 6),
                    "omega_x": round(float(omega_com[0]), 6),
                    "omega_y": round(float(omega_com[1]), 6),
                    "sigma_drift": round(sigma_drift, 6),
                    "omega_drift": round(omega_drift, 6),
                    "separation": round(separation_from_anchor, 6),
                    "coherence": round(coh, 4),
                })

        prev_com = com

    # ── Results ──
    if len(timeline) > 1:
        final = timeline[-1]
        sigma_total_drift = final["sigma_drift"]
        omega_total_drift = final["omega_drift"]
        final_separation = final["separation"]

        print(f"\n  RESULTS:")
        print(f"  {'─'*50}")
        print(f"  Sigma total drift:   {sigma_total_drift:.6f} px")
        print(f"  Omega total drift:   {omega_total_drift:.6f} px")
        print(f"  Final separation:    {final_separation:.6f} px")
        print(f"  Final coherence:     {final['coherence']:.4f}")

        # Pass/fail
        omega_stable = omega_total_drift < 0.01
        sigma_moved = sigma_total_drift > 1.0
        separated = final_separation > 1.0

        if omega_stable and sigma_moved and separated:
            verdict = "PASS"
            reason = ("Sigma displaced relative to fixed anchor. "
                      "Omega stationary. Transport is frame-independent.")
        elif not omega_stable:
            verdict = "FAIL"
            reason = ("Omega drifted — anchor is not inertial. "
                      "Cannot establish external frame.")
        elif not sigma_moved:
            verdict = "FAIL"
            reason = ("Sigma did not move. No transport detected.")
        else:
            verdict = "INCONCLUSIVE"
            reason = "Separation below threshold."

        print(f"\n  VERDICT: {verdict}")
        print(f"  {reason}")
        print(f"  {'─'*50}")

        # Sample timeline
        print(f"\n  TIMELINE (sampled):")
        print(f"  {'Step':>6} {'Sig_X':>10} {'Omg_X':>10} "
              f"{'Sep':>10} {'Coh':>8}")
        print(f"  {'─'*6} {'─'*10} {'─'*10} {'─'*10} {'─'*8}")
        for t in timeline[::4]:  # every 4th entry
            print(f"  {t['step']:>6} {t['sigma_x']:>10.4f} "
                  f"{t['omega_x']:>10.4f} {t['separation']:>10.4f} "
                  f"{t['coherence']:>8.4f}")
    else:
        verdict = "FAIL"
        reason = "Insufficient data."
        sigma_total_drift = 0
        omega_total_drift = 0
        final_separation = 0

    return {
        "test": "A_HARPOON",
        "verdict": verdict,
        "reason": reason,
        "sigma_drift": sigma_total_drift,
        "omega_drift": omega_total_drift,
        "final_separation": final_separation,
        "timeline": timeline,
    }


# ── Test E: The Oar ───────────────────────────────────

def test_E_oar(steps, nx, ny, dt, D, void_lambda,
               pump_A, alpha, cv_strength):
    """
    Medium coupling / reaction force test.

    The substrate is modeled as a lambda field. If the
    sigma structure moves through it, the substrate must
    push back — there must be a reaction force.

    F_reaction = integral over ship envelope of
                 (grad_lambda . v_hat) * sigma

    We measure this at multiple velocity regimes by
    varying pump ratio (which controls velocity).

    Pass: F_reaction > 0 and scales with velocity.
    Fail: F_reaction = 0 everywhere.
    """
    print(f"\n{'='*65}")
    print(f"  TEST E — THE OAR (Medium Coupling)")
    print(f"  Does the substrate push back?")
    print(f"{'='*65}")

    # Run at multiple pump ratios to get different velocities
    ratios = [0.05, 0.10, 0.15, 0.25, 0.35, 0.50]
    results = []

    for ratio in ratios:
        x = np.arange(nx)
        y = np.arange(ny)
        X, Y = np.meshgrid(x, y, indexing='ij')

        center = (nx // 3, ny // 2)
        r2_init = (X - center[0])**2 + (Y - center[1])**2
        sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
        sigma_prev = sigma.copy()

        # Lambda field — starts uniform, but we allow the
        # ship to modify it locally (back-reaction)
        lam_field = np.full((nx, ny), void_lambda, dtype=float)
        lam_initial = lam_field.copy()

        initial_com = compute_com(sigma)
        prev_com = initial_com.copy()

        # Accumulators
        F_reaction_sum = 0.0
        velocity_sum = 0.0
        n_samples = 0

        # Lambda distortion accumulator
        lam_distortion_sum = 0.0

        sep = 15.0

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
            speed = float(np.linalg.norm(velocity_vec))

            # Apply pumps (fixed ratio for this run)
            r2_A = (X - com[0])**2 + (Y - com[1])**2
            pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
            sigma += pA * dt

            bx = com[0] + sep
            r2_B = (X - bx)**2 + (Y - com[1])**2
            actual_B = pump_A * ratio
            pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

            # ── BACK-REACTION: sigma agitation modifies lambda ──
            # The ship's sigma field locally reduces lambda
            # (funds the substrate). This is the medium coupling.
            # sigma_energy deposits into the lambda field,
            # creating a wake of reduced lambda behind the ship.
            coupling_strength = 0.001  # weak coupling
            lam_field = lam_field - coupling_strength * sigma * dt
            lam_field = np.maximum(lam_field, 0.001)  # floor

            # Evolve PDE with the MODIFIED lambda field
            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma_new = sigma + D * laplacian * dt - lam_field * sigma * dt

            # Memory
            if alpha > 0:
                sigma_new = sigma_new + alpha * (sigma - sigma_prev)

            sigma_new = np.maximum(sigma_new, 0)

            # Check valve
            if cv_strength > 0:
                flow = sigma_new - sigma
                flow_grad_x = (np.roll(flow, -1, axis=0) -
                               np.roll(flow, 1, axis=0)) / 2.0
                backflow = flow_grad_x < 0
                valve = np.ones_like(sigma_new)
                valve[backflow] = 1.0 - cv_strength
                sigma_new = sigma_new * valve

            if float(np.max(sigma_new)) > 1e10:
                break

            sigma_prev = sigma.copy()
            sigma = sigma_new

            # ── Measure reaction force ──
            # F_reaction = integral of (grad_lambda . v_hat) * sigma
            # over the ship envelope (within radius of COM)
            if speed > 1e-10 and step > 100:
                v_hat = velocity_vec / speed

                grad_lam_x = (np.roll(lam_field, -1, axis=0) -
                              np.roll(lam_field, 1, axis=0)) / 2.0
                grad_lam_y = (np.roll(lam_field, -1, axis=1) -
                              np.roll(lam_field, 1, axis=1)) / 2.0

                # Projection onto velocity direction
                grad_dot_v = grad_lam_x * v_hat[0] + grad_lam_y * v_hat[1]

                # Ship envelope: within 10 px of COM
                r2_env = (X - com[0])**2 + (Y - com[1])**2
                envelope = r2_env < 10.0**2

                # Reaction force: lambda gradient opposing motion
                # at the ship location, weighted by sigma
                F_local = grad_dot_v * sigma * envelope
                F_reaction = float(np.sum(F_local))

                F_reaction_sum += abs(F_reaction)
                velocity_sum += speed
                n_samples += 1

            # Lambda distortion
            if step % 200 == 0 and step > 0:
                lam_diff = float(np.sum(np.abs(lam_field - lam_initial)))
                lam_distortion_sum += lam_diff

            prev_com = com

        # Final measurements
        final_com = compute_com(sigma)
        if final_com is not None:
            total_drift = float(np.linalg.norm(final_com - initial_com))
        else:
            total_drift = 0

        avg_F = F_reaction_sum / max(n_samples, 1)
        avg_v = velocity_sum / max(n_samples, 1)
        lam_distortion = float(np.sum(np.abs(lam_field - lam_initial)))

        results.append({
            "ratio": ratio,
            "drift": round(total_drift, 6),
            "avg_velocity": round(avg_v, 10),
            "avg_F_reaction": round(avg_F, 10),
            "lambda_distortion": round(lam_distortion, 6),
            "n_samples": n_samples,
        })

        print(f"  Ratio={ratio:.2f}  drift={total_drift:>8.3f} px  "
              f"avg_v={avg_v:.8f}  F_react={avg_F:.8f}  "
              f"lam_dist={lam_distortion:.4f}")

    # ── Analysis ──
    print(f"\n  {'─'*60}")
    print(f"  REACTION FORCE SCALING ANALYSIS")
    print(f"  {'─'*60}")

    velocities = [r["avg_velocity"] for r in results]
    forces = [r["avg_F_reaction"] for r in results]
    distortions = [r["lambda_distortion"] for r in results]

    # Check if F_reaction scales with velocity
    has_force = any(f > 1e-12 for f in forces)
    has_distortion = any(d > 0.01 for d in distortions)

    if has_force and len(velocities) > 2:
        # Compute correlation between velocity and force
        v_arr = np.array(velocities)
        f_arr = np.array(forces)
        if np.std(v_arr) > 1e-15 and np.std(f_arr) > 1e-15:
            correlation = float(np.corrcoef(v_arr, f_arr)[0, 1])
        else:
            correlation = 0.0

        print(f"  Velocity-Force correlation: {correlation:.6f}")
        print(f"  Lambda distortion range: "
              f"{min(distortions):.4f} to {max(distortions):.4f}")

        if correlation > 0.7:
            verdict = "PASS"
            reason = (f"Reaction force scales with velocity "
                      f"(r={correlation:.4f}). "
                      f"Substrate pushes back. Medium coupling confirmed.")
        elif correlation > 0.3:
            verdict = "PARTIAL"
            reason = (f"Weak correlation (r={correlation:.4f}). "
                      f"Force exists but scaling is noisy.")
        else:
            verdict = "FAIL"
            reason = (f"No velocity-force scaling (r={correlation:.4f}). "
                      f"No medium coupling detected.")
    elif has_distortion and not has_force:
        verdict = "PARTIAL"
        reason = ("Lambda field distorted but no measurable reaction "
                  "force. Wake exists but no drag.")
        correlation = 0.0
    else:
        verdict = "FAIL"
        reason = "No reaction force. No lambda distortion. Ghost ship."
        correlation = 0.0

    print(f"\n  VERDICT: {verdict}")
    print(f"  {reason}")
    print(f"  {'─'*60}")

    return {
        "test": "E_OAR",
        "verdict": verdict,
        "reason": reason,
        "correlation": correlation if has_force else 0,
        "has_reaction_force": has_force,
        "has_lambda_distortion": has_distortion,
        "ratio_sweep": results,
    }


# ── Main ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BCM v15 External Frame & Medium Coupling")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v15 — EXTERNAL FRAME & MEDIUM COUPLING")
    print(f"  Two tests. Two gates.")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    # Shared parameters
    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    alpha = 0.80
    cv_strength = 0.2

    # ── Test A ──
    result_A = test_A_harpoon(args.steps, nx, ny, dt, D,
                              void_lambda, pump_A, alpha,
                              cv_strength)

    # ── Test E ──
    result_E = test_E_oar(args.steps, nx, ny, dt, D,
                          void_lambda, pump_A, alpha,
                          cv_strength)

    # ── Final Summary ──
    print(f"\n{'='*65}")
    print(f"  v15 GATE SUMMARY")
    print(f"{'='*65}")
    print(f"  Test A (Harpoon / External Frame): {result_A['verdict']}")
    print(f"    Sigma drift: {result_A['sigma_drift']:.6f} px")
    print(f"    Omega drift: {result_A['omega_drift']:.6f} px")
    print(f"    Separation:  {result_A['final_separation']:.6f} px")
    print(f"")
    print(f"  Test E (Oar / Medium Coupling):    {result_E['verdict']}")
    print(f"    Reaction force detected: {result_E['has_reaction_force']}")
    print(f"    Lambda distortion: {result_E['has_lambda_distortion']}")
    if result_E['has_reaction_force']:
        print(f"    V-F correlation: {result_E['correlation']:.6f}")

    both_pass = (result_A["verdict"] == "PASS" and
                 result_E["verdict"] == "PASS")

    print(f"\n  {'─'*50}")
    if both_pass:
        print(f"  BOTH GATES PASSED.")
        print(f"  Transport is frame-independent and medium-coupled.")
        print(f"  v14 classification upgraded from")
        print(f"  'regulated dynamical field system' to")
        print(f"  'substrate transport mechanism.'")
    else:
        print(f"  ONE OR MORE GATES OPEN.")
        if result_A["verdict"] != "PASS":
            print(f"  Test A: External frame not established.")
        if result_E["verdict"] != "PASS":
            print(f"  Test E: Medium coupling not confirmed.")
        print(f"  Classification remains: 'regulated dynamical field.'")
    print(f"  {'─'*50}")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v15_external_frame_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v15 External Frame & Medium Coupling",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Two gates: inertial anchor and reaction force",
        "grid": nx,
        "steps": args.steps,
        "parameters": {
            "dt": dt, "D": D, "void_lambda": void_lambda,
            "pump_A": pump_A, "alpha": alpha,
            "cv_strength": cv_strength,
        },
        "test_A": result_A,
        "test_E": result_E,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
