# -*- coding: utf-8 -*-
"""
BCM v24 — BOUNDARY STABILITY TEST
===================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

ChatGPT identified the critical question: is the boundary
dissolution (38× flood) real physics or a missing term?

The current solver has no boundary-restoring mechanism.
The ring is thin because of absorbing edge conditions.
When perturbed, diffusion from the funded interior floods
the ring to bulk levels because nothing opposes it.

This test applies four boundary treatments via callback
to determine what type of physics produces a stable edge:

  Config 0: BASELINE — no treatment (expect 38× flood)
  Config 1: HIGH DECAY — λ_edge = λ × K_mult at ring
            (edge dissipates faster, Jasper Beach amplified)
  Config 2: SATURATION CLAMP — σ clamped to σ_crit at ring
            (nonlinear impedance barrier)
  Config 3: EDGE INJECTION — small J_edge added at ring
            (the edge has its own maintenance funding)

If any config produces:
  - σ_ring returns to thin baseline (~3)
  - σ_ring stays < 2× baseline
  - Ring oscillation (restoring torque)
Then that config identifies the missing boundary physics.

If ALL configs flood to bulk → the solver genuinely has
no stable boundary regime and the edge is not a physical
structure under this wave equation.

Output JSON → data/results/BCM_v24_boundary_stability_YYYYMMDD_HHMMSS.json
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
MEASURE    = 6000


class BoundaryCallback:
    """
    Shears the ring at trigger_step, then applies a
    boundary treatment at every callback (every 1000 steps)
    for the remainder of the run.

    Treatments:
      "none"       — no post-shear treatment (baseline)
      "high_decay" — multiply σ in ring by decay factor
      "clamp"      — cap σ in ring at σ_crit
      "injection"  — add J_edge to rho in ring

    Records ring σ time series for analysis.
    """
    def __init__(self, trigger_step, ring_mask, core_mask,
                 treatment="none", **params):
        self.trigger_step = trigger_step
        self.ring_mask = ring_mask
        self.core_mask = core_mask
        self.treatment = treatment
        self.params = params
        self.sheared = False

        # K multiplier for high_decay
        self.k_mult = params.get("k_mult", 5.0)
        # Critical σ for clamp
        self.sigma_crit = params.get("sigma_crit", 10.0)
        # Injection amplitude for edge funding
        self.j_edge = params.get("j_edge", 0.5)

        # Time series
        self.steps = []
        self.ring_sigma = []
        self.core_sigma = []

    def __call__(self, step, total, rho, sigma):
        # Shear event
        if not self.sheared and step >= self.trigger_step:
            for i in range(sigma.shape[0]):
                sigma[i][self.ring_mask] = 0.0
                rho[i][self.ring_mask] = 0.0
            self.sheared = True

        # Apply boundary treatment after shear
        if self.sheared and self.treatment != "none":
            if self.treatment == "high_decay":
                # Amplified decay in ring: σ *= (1 - K_mult * λ * dt)
                decay = 1.0 - self.k_mult * LAMBDA * 0.01
                decay = max(decay, 0.0)
                for i in range(sigma.shape[0]):
                    sigma[i][self.ring_mask] *= decay

            elif self.treatment == "clamp":
                # Hard cap: σ cannot exceed σ_crit in ring
                for i in range(sigma.shape[0]):
                    mask = sigma[i] > self.sigma_crit
                    combined = mask & self.ring_mask
                    sigma[i][combined] = self.sigma_crit

            elif self.treatment == "injection":
                # Small injection at ring boundary
                for i in range(rho.shape[0]):
                    rho[i][self.ring_mask] += self.j_edge

        # Record
        if step >= self.trigger_step - 2000:
            sig_2d = np.mean(sigma, axis=0) if sigma.ndim == 3 \
                else sigma
            ring_val = float(np.mean(np.abs(sig_2d[self.ring_mask])))
            core_val = float(np.mean(np.abs(sig_2d[self.core_mask])))
            self.steps.append(int(step))
            self.ring_sigma.append(ring_val)
            self.core_sigma.append(core_val)


def build_binary_J(grid, m1=1.0, m2=1.3, sep=1.0,
                   activity=15.0):
    """Binary source field (HR 1099)."""
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


def run_config(config_name, treatment, grid, J_net, R,
               ring_mask, core_mask, verbose=True, **params):
    """Run one boundary configuration."""
    if verbose:
        print(f"\n  ── CONFIG: {config_name} ──")
        if params:
            print(f"     Params: {params}")

    shear_step = SETTLE - 3000
    cb = BoundaryCallback(
        trigger_step=shear_step,
        ring_mask=ring_mask,
        core_mask=core_mask,
        treatment=treatment,
        **params)

    t0 = time.time()
    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    res = solver.run(J_net, verbose=False, callback=cb)
    elapsed = time.time() - t0

    # Analyze
    steps = np.array(cb.steps)
    ring = np.array(cb.ring_sigma)
    core = np.array(cb.core_sigma)

    # Pre-shear baseline
    pre_mask = steps < shear_step
    if np.any(pre_mask):
        baseline = float(np.mean(ring[pre_mask]))
    else:
        baseline = float(ring[0]) if len(ring) > 0 else 1.0

    # Post-shear metrics
    post_mask = steps >= shear_step
    post_ring = ring[post_mask]
    post_core = core[post_mask]

    final_ring = float(post_ring[-1]) if len(post_ring) > 0 else 0.0
    final_core = float(post_core[-1]) if len(post_core) > 0 else 0.0
    peak_ring = float(np.max(post_ring)) if len(post_ring) > 0 else 0.0

    # Did it return to baseline?
    if baseline > 0:
        final_ratio = final_ring / baseline
        peak_ratio = peak_ring / baseline
    else:
        final_ratio = final_ring
        peak_ratio = peak_ring

    # Is it stable? (within 2× of baseline)
    stable = final_ratio <= 2.0

    # Did it oscillate? (any decrease after increase)
    oscillated = False
    if len(post_ring) > 3:
        for i in range(2, len(post_ring)):
            if post_ring[i] < post_ring[i-1] * 0.95:
                oscillated = True
                break

    # Classification
    if stable and oscillated:
        verdict = "ELASTIC — restoring torque with oscillation"
    elif stable and not oscillated:
        verdict = "DAMPED STABLE — thin edge maintained"
    elif not stable and oscillated:
        verdict = "UNSTABLE OSCILLATION — floods with ringing"
    else:
        verdict = "BULK FLOOD — edge dissolved"

    if verbose:
        print(f"     Baseline σ_ring:  {baseline:.4f}")
        print(f"     Final σ_ring:     {final_ring:.4f}")
        print(f"     Final ratio:      {final_ratio:.2f}×")
        print(f"     Peak ratio:       {peak_ratio:.2f}×")
        print(f"     Oscillated:       {oscillated}")
        print(f"     Stable:           {stable}")
        print(f"     VERDICT: {verdict}")
        print(f"     Elapsed: {elapsed:.1f}s")

    # Sampled profile
    profile = []
    step_size = max(1, len(cb.steps) // 15)
    for i in range(0, len(cb.steps), step_size):
        profile.append({
            "step": int(cb.steps[i]),
            "ring_sigma": float(cb.ring_sigma[i]),
        })

    return {
        "config": config_name,
        "treatment": treatment,
        "params": {k: float(v) if isinstance(v, (int, float))
                   else v for k, v in params.items()},
        "baseline": baseline,
        "final_ring": final_ring,
        "final_core": final_core,
        "final_ratio": float(final_ratio),
        "peak_ratio": float(peak_ratio),
        "oscillated": oscillated,
        "stable": stable,
        "verdict": verdict,
        "elapsed": float(elapsed),
        "profile": profile,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v24 Boundary Stability Test")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v24 — BOUNDARY STABILITY TEST")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)
    print(f"  Grid: {grid}  |  4 boundary configs")
    print(f"  Question: can a stable thin edge exist?")
    print("=" * 60)

    np.random.seed(42)  # Reproducible grind noise
    J_net, R = build_binary_J(grid)
    r_max = np.max(R)
    ring_mask = (R > 0.75 * r_max) & (R < 0.85 * r_max)
    core_mask = R < 0.33 * r_max

    configs = [
        ("BASELINE (no treatment)", "none", {}),
        ("HIGH DECAY (K×5)", "high_decay", {"k_mult": 5.0}),
        ("HIGH DECAY (K×10)", "high_decay", {"k_mult": 10.0}),
        ("HIGH DECAY (K×50)", "high_decay", {"k_mult": 50.0}),
        ("CLAMP (σ_crit=10)", "clamp", {"sigma_crit": 10.0}),
        ("CLAMP (σ_crit=5)", "clamp", {"sigma_crit": 5.0}),
        ("EDGE INJECTION (J=0.5)", "injection", {"j_edge": 0.5}),
        ("EDGE INJECTION (J=2.0)", "injection", {"j_edge": 2.0}),
    ]

    all_results = []
    t_total = time.time()

    for name, treatment, params in configs:
        r = run_config(name, treatment, grid, J_net, R,
                       ring_mask, core_mask, **params)
        all_results.append(r)

    elapsed_total = time.time() - t_total

    # Summary
    print(f"\n{'═'*60}")
    print(f"  BOUNDARY STABILITY SUMMARY")
    print(f"{'═'*60}")
    print(f"  {'Config':<28} {'Final':>6} {'Peak':>6} "
          f"{'Osc':>4} {'Stable':>6} {'Verdict'}")
    print(f"  {'─'*28} {'─'*6} {'─'*6} {'─'*4} {'─'*6} {'─'*20}")
    for r in all_results:
        osc = "Y" if r["oscillated"] else "N"
        stb = "YES" if r["stable"] else "no"
        print(f"  {r['config']:<28} {r['final_ratio']:>6.1f}× "
              f"{r['peak_ratio']:>6.1f}× {osc:>4} {stb:>6}  "
              f"{r['verdict']}")

    n_stable = sum(1 for r in all_results if r["stable"])
    n_osc = sum(1 for r in all_results if r["oscillated"])

    if n_stable > 0:
        print(f"\n  RESULT: {n_stable}/{len(all_results)} configs "
              f"maintain stable boundary.")
        print(f"  The edge CAN be stabilized — identifies the "
              f"missing physics term.")
    else:
        print(f"\n  RESULT: 0/{len(all_results)} configs stable.")
        print(f"  The solver has no stable boundary regime.")
        print(f"  The edge is not a physical structure under "
              f"this wave equation.")

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v24_boundary_stability_{timestamp}.json")
    output = {
        "test": "boundary_stability_sweep",
        "version": "v24",
        "grid": grid,
        "configs_tested": len(all_results),
        "stable_count": n_stable,
        "oscillation_count": n_osc,
        "timestamp": timestamp,
        "elapsed_total": float(elapsed_total),
        "results": all_results,
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")

if __name__ == "__main__":
    main()
