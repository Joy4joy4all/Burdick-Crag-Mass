# -*- coding: utf-8 -*-
"""
BCM v24 — ARRIVAL TIMING TEST (SNAP-BACK RING-DOWN)
=====================================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

The snap-back test (v24 perturbation) showed 25× overshoot
when σ was zeroed in a ring at 80% r_max. The substrate
doesn't gently refill — it SLAMS into the void and rings.

This test measures the ring-down profile:
  - How many steps between overshoot peaks?
  - How fast does the amplitude decay?
  - What fraction of each cycle is safe for arrival?
  - When does OpT detect the snap-back from ahead?
  - What is the minimum lead time for the navigator?

At 12,000c the probes see 45 meters ahead. OpT sees the
entire funded region through the 7D spectral fold. The
question is: does OpT register the ring-down early enough
for the navigator to time the entry?

The craft enters the torus on the calm side of the
ring-down cycle, not during the slap.

Output JSON → data/results/BCM_v24_arrival_timing_YYYYMMDD_HHMMSS.json
"""

import numpy as np
import os
import sys
import json
import time
import argparse

_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_EPIC_DIR     = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_EPIC_DIR)
for p in [_SCRIPT_DIR, _EPIC_DIR, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.substrate_solver import SubstrateSolver

LAMBDA     = 0.1
GRID_PROD  = 256
GRID_QUICK = 128
LAYERS     = 8
SETTLE     = 18000
MEASURE    = 6000   # Extended measurement to capture full ring-down

# OpT/OpC thresholds (from v20-v21)
OPT_THRESHOLD   = 0.92
DELTA_OP_MAX    = 0.08
COHERENCE_MIN   = 0.95
SAFE_RATIO_MIN  = 0.5   # σ_ring within 2× of baseline = safe
SAFE_RATIO_MAX  = 2.0


class RingDownCallback:
    """
    Records σ in the shear ring at every sample_interval steps.
    Also zeros the ring at trigger_step (the shear event).

    Builds a time series of ring σ, core σ, and gradient
    for post-run analysis.

    Signature: (step, total, rho, sigma)
    """
    def __init__(self, trigger_step, ring_mask, core_mask,
                 sample_interval=100):
        self.trigger_step = trigger_step
        self.ring_mask = ring_mask
        self.core_mask = core_mask
        self.sample_interval = sample_interval
        self.applied = False

        # Time series storage
        self.steps = []
        self.ring_sigma = []
        self.core_sigma = []
        self.ring_gradient = []
        self.ring_max = []

    def __call__(self, step, total, rho, sigma):
        # Shear event
        if not self.applied and step >= self.trigger_step:
            for i in range(sigma.shape[0]):
                sigma[i][self.ring_mask] = 0.0
                rho[i][self.ring_mask] = 0.0
            self.applied = True

        # Sample the ring-down (every callback = every 1000 steps)
        if step >= self.trigger_step - 2000:
            sigma_2d = np.mean(sigma, axis=0) if sigma.ndim == 3 \
                else sigma
            ring_val = float(np.mean(np.abs(sigma_2d[self.ring_mask])))
            core_val = float(np.mean(np.abs(sigma_2d[self.core_mask])))
            ring_mx  = float(np.max(np.abs(sigma_2d[self.ring_mask])))

            # Gradient at ring (spatial rate of change)
            dy, dx = np.gradient(sigma_2d)
            grad_mag = np.sqrt(dx**2 + dy**2)
            ring_grad = float(np.mean(grad_mag[self.ring_mask]))

            self.steps.append(int(step))
            self.ring_sigma.append(ring_val)
            self.core_sigma.append(core_val)
            self.ring_gradient.append(ring_grad)
            self.ring_max.append(ring_mx)


def build_binary_J(grid, m1=1.0, m2=1.3, sep=1.0,
                   activity=15.0):
    """Binary source field with grind noise (HR 1099)."""
    x = np.linspace(-5, 5, grid)
    y = np.linspace(-5, 5, grid)
    X, Y = np.meshgrid(x, y)
    r1 = np.sqrt((X + sep/2)**2 + Y**2)
    r2 = np.sqrt((X - sep/2)**2 + Y**2)
    J_base = (m1 / (r1 + 0.2)) + (m2 / (r2 + 0.2))
    throat = np.exp(-(X**2 + Y**2) / 1.0)
    grind = np.random.normal(0, 1.2, (grid, grid)) * activity
    J_net = J_base + grind * 0.05 * throat
    R = np.sqrt(X**2 + Y**2)
    return J_net, R


def analyze_ringdown(cb):
    """
    Analyze the time series from the ring-down callback.

    Computes:
      - Pre-shear baseline (samples before shear)
      - Peak overshoot ratio
      - Ring-down decay
      - OpT proxy: ring/core ratio normalized to baseline
      - Safe arrival windows
      - ΔOP proxy: gradient spike relative to baseline
    """
    steps = np.array(cb.steps)
    ring = np.array(cb.ring_sigma)
    core = np.array(cb.core_sigma)
    grad = np.array(cb.ring_gradient)
    rmax = np.array(cb.ring_max)

    # Find shear point in time series
    shear_idx = None
    for i in range(1, len(ring)):
        if ring[i] < ring[i-1] * 0.1:  # Sharp drop = shear
            shear_idx = i
            break

    if shear_idx is None:
        # Shear might be at the very start of recording
        shear_idx = 0

    # Baseline: samples before shear (or first sample if shear at start)
    if shear_idx > 0:
        baseline_ring = float(np.mean(ring[:shear_idx]))
        baseline_core = float(np.mean(core[:shear_idx]))
        baseline_grad = float(np.mean(grad[:shear_idx]))
    else:
        # Use the pre-shear snapshot from the first callback
        baseline_ring = float(ring[0]) if ring[0] > 0 else 1.0
        baseline_core = float(core[0])
        baseline_grad = float(grad[0]) if grad[0] > 0 else 1.0

    # Post-shear time series
    post_steps = steps[shear_idx:]
    post_ring = ring[shear_idx:]
    post_core = core[shear_idx:]
    post_grad = grad[shear_idx:]
    post_rmax = rmax[shear_idx:]

    # Overshoot detection
    if baseline_ring > 0:
        overshoot_ratios = post_ring / baseline_ring
    else:
        overshoot_ratios = post_ring

    peak_ratio = float(np.max(overshoot_ratios)) if len(overshoot_ratios) > 0 else 0.0
    peak_idx = int(np.argmax(overshoot_ratios)) if len(overshoot_ratios) > 0 else 0
    peak_step = int(post_steps[peak_idx]) if peak_idx < len(post_steps) else 0

    # Steps from shear to peak
    steps_to_peak = peak_step - int(steps[shear_idx]) if shear_idx < len(steps) else 0

    # OpT proxy: ring/core ratio normalized to baseline ratio
    baseline_ratio = baseline_ring / baseline_core if baseline_core > 0 else 0.0
    opt_series = []
    for i in range(len(post_ring)):
        current_ratio = post_ring[i] / post_core[i] if post_core[i] > 0 else 0.0
        if baseline_ratio > 0:
            opt = 1.0 - abs(current_ratio - baseline_ratio) / baseline_ratio
            opt = max(0.0, min(1.0, opt))
        else:
            opt = 0.0
        opt_series.append(float(opt))

    # ΔOP proxy: gradient anomaly relative to baseline
    delta_op_series = []
    for i in range(len(post_grad)):
        if baseline_grad > 0:
            delta = abs(post_grad[i] - baseline_grad) / baseline_grad
        else:
            delta = 0.0
        delta_op_series.append(float(min(delta, 1.0)))

    # Safe window analysis
    safe_count = 0
    total_post = len(overshoot_ratios)
    for r in overshoot_ratios:
        if SAFE_RATIO_MIN <= r <= SAFE_RATIO_MAX:
            safe_count += 1
    safe_fraction = safe_count / total_post if total_post > 0 else 0.0

    # OpT first drop below threshold
    opt_first_drop = None
    for i, o in enumerate(opt_series):
        if o < OPT_THRESHOLD:
            opt_first_drop = int(post_steps[i])
            break

    # OpT recovery: when does it first return above threshold after drop
    opt_recovery = None
    if opt_first_drop is not None:
        drop_idx = next(i for i, o in enumerate(opt_series) if o < OPT_THRESHOLD)
        for i in range(drop_idx + 1, len(opt_series)):
            if opt_series[i] >= OPT_THRESHOLD:
                opt_recovery = int(post_steps[i])
                break

    # Lead time: steps between OpT drop and peak overshoot
    opt_lead_time = None
    if opt_first_drop is not None and peak_step > opt_first_drop:
        opt_lead_time = peak_step - opt_first_drop

    # Ring-down profile (sampled for JSON)
    profile = []
    step_size = max(1, len(post_steps) // 20)
    for i in range(0, len(post_steps), step_size):
        profile.append({
            "step": int(post_steps[i]),
            "ring_sigma": float(post_ring[i]),
            "overshoot_ratio": float(overshoot_ratios[i]),
            "opt_proxy": opt_series[i],
            "delta_op": delta_op_series[i],
        })

    return {
        "baseline_ring": baseline_ring,
        "baseline_core": baseline_core,
        "baseline_gradient": baseline_grad,
        "peak_overshoot_ratio": peak_ratio,
        "peak_step": peak_step,
        "steps_to_peak": steps_to_peak,
        "safe_fraction": float(safe_fraction),
        "safe_count": safe_count,
        "total_samples": total_post,
        "opt_first_drop_step": opt_first_drop,
        "opt_recovery_step": opt_recovery,
        "opt_lead_time_steps": opt_lead_time,
        "final_ring_sigma": float(post_ring[-1]) if len(post_ring) > 0 else 0.0,
        "final_overshoot": float(overshoot_ratios[-1]) if len(overshoot_ratios) > 0 else 0.0,
        "final_opt": opt_series[-1] if opt_series else 0.0,
        "profile": profile,
    }


def run_timing_test(grid, verbose=True):
    if verbose:
        print(f"\n{'═'*60}")
        print(f"  HR 1099 — ARRIVAL TIMING (RING-DOWN PROFILER)")
        print(f"{'═'*60}")
        print(f"  Grid: {grid}  |  Settle: {SETTLE}  |  "
              f"Measure: {MEASURE}")

    J_net, R = build_binary_J(grid)
    r_max = np.max(R)
    ring_mask = (R > 0.75 * r_max) & (R < 0.85 * r_max)
    core_mask = R < 0.33 * r_max

    shear_step = SETTLE - 3000

    if verbose:
        print(f"  Ring: 75-85% r_max  |  "
              f"{int(np.sum(ring_mask))} pixels")
        print(f"  Shear at step {shear_step}")
        print(f"  Recording from step {shear_step - 2000}")
        print(f"  Extended measurement: {MEASURE} steps "
              f"post-settle")

    # Single run with ring-down recording
    cb = RingDownCallback(
        trigger_step=shear_step,
        ring_mask=ring_mask,
        core_mask=core_mask)

    t0 = time.time()
    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    res = solver.run(J_net, verbose=False, callback=cb)
    elapsed = time.time() - t0

    if verbose:
        print(f"  Solver complete: {elapsed:.1f}s")
        print(f"  Samples recorded: {len(cb.steps)}")

    # Analyze ring-down
    analysis = analyze_ringdown(cb)

    if verbose:
        print(f"\n  ── RING-DOWN ANALYSIS ──")
        print(f"    Baseline σ_ring:     {analysis['baseline_ring']:.4f}")
        print(f"    Peak overshoot:      {analysis['peak_overshoot_ratio']:.2f}×")
        print(f"    Steps to peak:       {analysis['steps_to_peak']}")
        print(f"    Final overshoot:     {analysis['final_overshoot']:.2f}×")

        print(f"\n  ── SAFE ARRIVAL WINDOW ──")
        print(f"    Safe fraction:       {analysis['safe_fraction']:.3f} "
              f"({analysis['safe_fraction']*100:.1f}%)")
        print(f"    Safe samples:        {analysis['safe_count']}/"
              f"{analysis['total_samples']}")

        print(f"\n  ── OpT RESPONSE ──")
        if analysis['opt_first_drop_step'] is not None:
            print(f"    OpT first drop:      step "
                  f"{analysis['opt_first_drop_step']}")
            print(f"    OpT lead time:       "
                  f"{analysis['opt_lead_time_steps']} steps "
                  f"before peak")
        else:
            print(f"    OpT: never dropped below "
                  f"{OPT_THRESHOLD}")

        if analysis['opt_recovery_step'] is not None:
            print(f"    OpT recovery:        step "
                  f"{analysis['opt_recovery_step']}")
        print(f"    Final OpT:           "
              f"{analysis['final_opt']:.4f}")

        # Verdict
        sf = analysis['safe_fraction']
        if sf > 0.70:
            verdict = "WIDE SAFE WINDOW — standard arrival viable"
        elif sf > 0.40:
            verdict = "NARROW SAFE WINDOW — timing required"
        elif sf > 0.10:
            verdict = "SLIM WINDOW — precision timing mandatory"
        else:
            verdict = "NO SAFE WINDOW — gentle arrival only"
        print(f"\n    VERDICT: {verdict}")
        analysis["verdict"] = verdict

    return {
        "system": "HR 1099",
        "grid": grid,
        "shear_step": shear_step,
        "elapsed": float(elapsed),
        "n_samples": len(cb.steps),
        "analysis": analysis,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v24 Arrival Timing (Ring-Down)")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v24 — ARRIVAL TIMING TEST (RING-DOWN)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    print(f"  The craft enters on the calm side of the cycle.")
    print(f"  Not during the slap.")
    print("=" * 60)

    result = run_timing_test(grid)

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v24_arrival_timing_{timestamp}.json")
    output = {
        "test": "arrival_timing_ringdown",
        "version": "v24",
        "grid": grid,
        "timestamp": timestamp,
        "elapsed": result["elapsed"],
        "results": result,
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")

if __name__ == "__main__":
    main()
