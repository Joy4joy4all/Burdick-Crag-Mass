# -*- coding: utf-8 -*-
"""
BCM v13 SPINE — Interstellar Coherence Backbone
==================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

The SPINE determines:
  1. Coherence survival threshold — minimum sigma that
     sustains a 3D event (the interstellar floor)
  2. Coherence decay rate vs background sigma density
  3. Star-to-star bridge feasibility at interstellar scale
  4. Time-cost reduction in low-sigma transit
  5. SMBH gradient navigation at galactic scale

This is not propulsion. This is the physics of whether
you survive the trip at all.

Usage:
    python BCM_spine.py
    python BCM_spine.py --grid 128 --steps 3000
"""

import numpy as np
import json
import os
import time
import argparse


def init_sigma_packet(nx, ny, center, amplitude=1.0, width=5.0):
    """Create a coherent sigma packet (the 'ship')."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    dx = X - center[0]
    dy = Y - center[1]
    r2 = dx**2 + dy**2
    return amplitude * np.exp(-r2 / (2 * width**2))


def compute_com(sigma):
    """Center of mass."""
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


def compute_peak(sigma):
    """Peak sigma value — the 'brightness' of the event."""
    return float(np.max(sigma))


def compute_energy(sigma):
    """Total field energy."""
    return float(np.sum(sigma**2))


# ============================================================
# TEST 1: COHERENCE SURVIVAL THRESHOLD
# ============================================================
def run_survival_threshold(steps=3000, nx=128, ny=128,
                            dt=0.05, D=0.5):
    """
    Place a sigma packet in environments with decreasing
    background lambda (increasing substrate funding).
    Find the minimum background level that sustains coherence.

    High lambda = low funding = void (interstellar)
    Low lambda = high funding = near a star

    Sweep lambda from 0.01 (well-funded) to 0.50 (void).
    Measure: does the packet survive 3000 steps?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: COHERENCE SURVIVAL THRESHOLD")
    print(f"  {'='*60}")
    print(f"  Sweeping background lambda from 0.01 to 0.50")
    print(f"  High lambda = unfunded void (interstellar)")
    print(f"  Low lambda = funded space (near star)")
    print(f"  Question: at what lambda does the event dissolve?")
    print(f"  {'─'*60}")
    print(f"  {'lambda':>8} {'Peak_0':>8} {'Peak_end':>10} "
          f"{'Coh_end':>10} {'Energy%':>10} {'Survived':>10} "
          f"{'Half-life':>10}")
    print(f"  {'─'*8} {'─'*8} {'─'*10} {'─'*10} {'─'*10} "
          f"{'─'*10} {'─'*10}")

    lam_values = [0.01, 0.02, 0.05, 0.08, 0.10, 0.15,
                   0.20, 0.25, 0.30, 0.40, 0.50]
    results = []

    for lam in lam_values:
        center = (nx // 2, ny // 2)
        sigma = init_sigma_packet(nx, ny, center)
        lam_field = np.full((nx, ny), lam)

        peak_0 = compute_peak(sigma)
        energy_0 = compute_energy(sigma)
        half_life = None

        for step in range(steps):
            # Diffusion
            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma += D * laplacian * dt
            sigma -= lam_field * sigma * dt
            sigma = np.maximum(sigma, 0)

            # Track half-life
            if half_life is None and compute_peak(sigma) < peak_0 * 0.5:
                half_life = step

        com = compute_com(sigma)
        if com is not None:
            coh = compute_coherence(sigma, com)
        else:
            coh = 0.0

        peak_end = compute_peak(sigma)
        energy_end = compute_energy(sigma)
        energy_pct = (energy_end / energy_0) * 100 if energy_0 > 0 else 0
        survived = peak_end > peak_0 * 0.001  # 0.1% threshold

        hl_str = str(half_life) if half_life else ">%d" % steps

        print(f"  {lam:>8.2f} {peak_0:>8.4f} {peak_end:>10.6f} "
              f"{coh:>10.4f} {energy_pct:>10.6f} "
              f"{'YES' if survived else 'DEAD':>10} {hl_str:>10}")

        results.append({
            "lambda": lam,
            "peak_start": round(peak_0, 6),
            "peak_end": round(peak_end, 10),
            "coherence_end": round(coh, 6),
            "energy_pct": round(energy_pct, 8),
            "survived": survived,
            "half_life_steps": half_life,
        })

    # Find threshold
    threshold = None
    for r in results:
        if not r["survived"]:
            threshold = r["lambda"]
            break

    print(f"\n  SURVIVAL THRESHOLD: lambda = "
          f"{threshold if threshold else '>0.50'}")
    if threshold:
        prev = [r for r in results
                if r["lambda"] < threshold and r["survived"]]
        if prev:
            print(f"  Last surviving lambda: {prev[-1]['lambda']}")
            print(f"  Interstellar floor: lambda < "
                  f"{threshold} for structural coherence")

    return results, threshold


# ============================================================
# TEST 2: COHERENCE DECAY RATE
# ============================================================
def run_decay_rate(steps=3000, nx=128, ny=128,
                    dt=0.05, D=0.5):
    """
    Measure how FAST coherence drops at different lambda levels.
    This gives the maximum transit time through unfunded regions.

    A ship entering a void (high lambda) has a countdown.
    How many steps until coherence drops below the survival floor?
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: COHERENCE DECAY RATE")
    print(f"  {'='*60}")
    print(f"  How fast does coherence drop in unfunded space?")
    print(f"  This is the countdown timer for void transit.")
    print(f"  {'─'*60}")

    lam_values = [0.05, 0.10, 0.15, 0.20, 0.30]
    coh_floor = 0.20  # minimum for structural integrity
    results = []

    print(f"  {'lambda':>8} {'Steps to':>10} {'Steps to':>10} "
          f"{'Decay rate':>12}")
    print(f"  {'':>8} {'coh<0.50':>10} {'coh<0.20':>10} "
          f"{'(coh/step)':>12}")
    print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*12}")

    for lam in lam_values:
        center = (nx // 2, ny // 2)
        sigma = init_sigma_packet(nx, ny, center)
        lam_field = np.full((nx, ny), lam)

        step_half = None
        step_floor = None
        coh_log = []

        for step in range(steps):
            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma += D * laplacian * dt
            sigma -= lam_field * sigma * dt
            sigma = np.maximum(sigma, 0)

            com = compute_com(sigma)
            if com is None:
                if step_half is None:
                    step_half = step
                if step_floor is None:
                    step_floor = step
                break

            coh = compute_coherence(sigma, com)
            coh_log.append(coh)

            if step_half is None and coh < 0.50:
                step_half = step
            if step_floor is None and coh < coh_floor:
                step_floor = step

        # Decay rate (linear approx from first 500 steps)
        if len(coh_log) > 100:
            rate = (coh_log[0] - coh_log[min(500, len(coh_log)-1)]) / min(500, len(coh_log))
        else:
            rate = 0

        sh = str(step_half) if step_half else ">%d" % steps
        sf = str(step_floor) if step_floor else ">%d" % steps

        print(f"  {lam:>8.2f} {sh:>10} {sf:>10} {rate:>12.6f}")

        results.append({
            "lambda": lam,
            "steps_to_half": step_half,
            "steps_to_floor": step_floor,
            "decay_rate": round(rate, 8),
            "coh_samples": len(coh_log),
        })

    return results


# ============================================================
# TEST 3: STAR-TO-STAR BRIDGE FEASIBILITY
# ============================================================
def run_bridge_test(steps=3000, nx=256, ny=64,
                     dt=0.05, D=0.5):
    """
    Two pump sources at opposite ends of a long grid.
    Background lambda = 'void' level.
    Question: does a substrate bridge form between them?

    If yes: interstellar corridors exist.
    If no: ships must carry their own coherence budget.

    Uses 256x64 grid to simulate long-distance corridor.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: STAR-TO-STAR BRIDGE FEASIBILITY")
    print(f"  {'='*60}")
    print(f"  Grid: {nx}x{ny} (elongated corridor)")
    print(f"  Star A at x=20, Star B at x=236")
    print(f"  Background: void lambda")
    print(f"  Question: does a bridge form?")
    print(f"  {'─'*60}")

    bg_lambdas = [0.05, 0.10, 0.15, 0.20]
    results = []

    for bg_lam in bg_lambdas:
        # Two stellar pumps
        x = np.arange(nx)
        y = np.arange(ny)
        X, Y = np.meshgrid(x, y, indexing='ij')

        star_A = (20, ny // 2)
        star_B = (nx - 20, ny // 2)

        # Stars as low-lambda wells in a high-lambda void
        r_A = np.sqrt((X - star_A[0])**2 + (Y - star_A[1])**2)
        r_B = np.sqrt((X - star_B[0])**2 + (Y - star_B[1])**2)

        lam_field = np.full((nx, ny), bg_lam)
        lam_field -= 0.08 * np.exp(-r_A**2 / (2 * 8**2))
        lam_field -= 0.08 * np.exp(-r_B**2 / (2 * 8**2))
        lam_field = np.maximum(lam_field, 0.01)

        # Source field (continuous pump)
        J = np.zeros((nx, ny))
        J += 5.0 * np.exp(-r_A**2 / (2 * 5**2))
        J += 5.0 * np.exp(-r_B**2 / (2 * 5**2))

        # Initialize sigma from sources
        sigma = J.copy() * 0.1

        # Evolve with continuous pumping
        for step in range(steps):
            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma += D * laplacian * dt
            sigma -= lam_field * sigma * dt
            sigma += J * dt * 0.1  # continuous pumping
            sigma = np.maximum(sigma, 0)

        # Measure bridge: sigma along the midline
        midline = sigma[:, ny // 2]
        mid_x = nx // 2
        bridge_sigma = float(midline[mid_x])
        star_A_sigma = float(midline[star_A[0]])
        star_B_sigma = float(midline[star_B[0]])

        # Bridge exists if midpoint sigma > 1% of star sigma
        bridge_ratio = bridge_sigma / max(star_A_sigma, 0.001)
        bridge_exists = bridge_ratio > 0.01

        # Corridor profile: sample every 10 pixels
        corridor = []
        for cx in range(0, nx, 10):
            corridor.append({
                "x": cx,
                "sigma": round(float(midline[cx]), 6),
            })

        print(f"  bg_lam={bg_lam:.2f}: star_A={star_A_sigma:.4f} "
              f"mid={bridge_sigma:.6f} "
              f"ratio={bridge_ratio:.6f} "
              f"bridge={'YES' if bridge_exists else 'NO'}")

        results.append({
            "bg_lambda": bg_lam,
            "star_A_sigma": round(star_A_sigma, 6),
            "star_B_sigma": round(star_B_sigma, 6),
            "bridge_sigma": round(bridge_sigma, 8),
            "bridge_ratio": round(bridge_ratio, 8),
            "bridge_exists": bridge_exists,
            "corridor": corridor,
        })

    return results


# ============================================================
# TEST 4: TIME-COST IN LOW SIGMA
# ============================================================
def run_time_cost(steps=2000, nx=128, ny=128,
                   dt=0.05, D=0.5):
    """
    If time = maintenance cost, then transit through low-sigma
    regions costs LESS time per distance. The ship ages slower
    in the void because the substrate spends less to maintain
    the 3D event.

    Measure: total energy expenditure (integral of sigma^2)
    across different background lambda levels. Lower total
    energy = less time experienced.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 4: TIME-COST IN LOW SIGMA")
    print(f"  {'='*60}")
    print(f"  If time = maintenance cost, low-sigma transit")
    print(f"  costs LESS time. The ship ages slower in the void.")
    print(f"  {'─'*60}")

    lam_values = [0.05, 0.10, 0.15, 0.20, 0.30]
    results = []

    print(f"  {'lambda':>8} {'Total cost':>12} {'Cost ratio':>12} "
          f"{'Interpretation':>20}")
    print(f"  {'─'*8} {'─'*12} {'─'*12} {'─'*20}")

    baseline_cost = None

    for lam in lam_values:
        center = (nx // 2, ny // 2)
        sigma = init_sigma_packet(nx, ny, center)
        lam_field = np.full((nx, ny), lam)

        # Add a drive (moving lambda dipole)
        total_cost = 0.0

        for step in range(steps):
            com = compute_com(sigma)
            if com is None:
                break

            # Drive: lambda dipole following the packet
            d = np.array([1.0, 0.0])
            xx = np.arange(nx)
            yy = np.arange(ny)
            X, Y = np.meshgrid(xx, yy, indexing='ij')
            proj = (X - com[0]) * d[0] + (Y - com[1]) * d[1]
            drive_field = lam - 0.03 * np.tanh(proj / 10.0)
            drive_field = np.maximum(drive_field, 0.01)

            laplacian = (
                np.roll(sigma, 1, axis=0) +
                np.roll(sigma, -1, axis=0) +
                np.roll(sigma, 1, axis=1) +
                np.roll(sigma, -1, axis=1) -
                4 * sigma
            )
            sigma += D * laplacian * dt
            sigma -= drive_field * sigma * dt
            sigma = np.maximum(sigma, 0)

            # Time cost = total energy maintained this step
            total_cost += compute_energy(sigma)

        if baseline_cost is None:
            baseline_cost = total_cost

        ratio = total_cost / baseline_cost if baseline_cost > 0 else 0

        if ratio < 0.8:
            interp = "FAST aging"
        elif ratio < 1.2:
            interp = "Normal"
        else:
            interp = "SLOW aging"

        print(f"  {lam:>8.2f} {total_cost:>12.2f} "
              f"{ratio:>12.4f} {interp:>20}")

        results.append({
            "lambda": lam,
            "total_cost": round(total_cost, 4),
            "cost_ratio": round(ratio, 6),
        })

    return results


# ============================================================
# TEST 5: GALACTIC GRADIENT — SMBH FUNDING MAP
# ============================================================
def run_galactic_gradient(nx=256, ny=256):
    """
    Build a simplified galactic sigma field showing the
    SMBH-funded substrate gradient from core to edge.
    This is the interstellar navigation chart.

    The gradient determines:
    - Which corridors between stars are navigable
    - Where coherence is naturally maintained
    - Where void regions create transit hazards
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 5: GALACTIC GRADIENT — SMBH FUNDING MAP")
    print(f"  {'='*60}")
    print(f"  Central SMBH funds the substrate.")
    print(f"  Gradient falls off with distance.")
    print(f"  Stars are local funding boosts.")
    print(f"  Voids are unfunded gaps.")
    print(f"  {'─'*60}")

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # SMBH at center
    center = (nx // 2, ny // 2)
    r = np.sqrt((X - center[0])**2 + (Y - center[1])**2)

    # SMBH funding: inverse-square falloff
    smbh_sigma = 100.0 / (1 + r**2 / 500.0)

    # Add spiral arm structure (simplified)
    theta = np.arctan2(Y - center[1], X - center[0])
    spiral = 0.3 * np.sin(2 * theta + r / 20) * smbh_sigma

    # Total galactic field
    galactic = smbh_sigma + spiral

    # Sample radial profile
    profile = []
    for ri in range(0, nx // 2, 5):
        val = float(galactic[center[0] + ri, center[1]])
        profile.append({"r_px": ri, "sigma": round(val, 4)})

    # Navigability zones
    core = float(np.mean(galactic[r < 20]))
    mid = float(np.mean(galactic[(r > 40) & (r < 80)]))
    edge = float(np.mean(galactic[r > 100]))

    print(f"  Core (r<20):     sigma = {core:.2f} (well funded)")
    print(f"  Mid (40<r<80):   sigma = {mid:.2f} (navigable)")
    print(f"  Edge (r>100):    sigma = {edge:.2f} (marginal)")
    print(f"  Gradient ratio:  core/edge = {core/max(edge,0.01):.1f}x")

    return {
        "core_sigma": round(core, 4),
        "mid_sigma": round(mid, 4),
        "edge_sigma": round(edge, 4),
        "gradient_ratio": round(core / max(edge, 0.01), 2),
        "profile": profile,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v13 SPINE — Interstellar Backbone")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"  BCM v13 SPINE — INTERSTELLAR COHERENCE BACKBONE")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"  Grid: {args.grid}  Steps: {args.steps}")
    print(f"{'='*65}")

    all_results = {}

    # Test 1: Survival threshold
    t1, threshold = run_survival_threshold(
        steps=args.steps, nx=args.grid, ny=args.grid)
    all_results["survival_threshold"] = {
        "results": t1, "threshold_lambda": threshold}

    # Test 2: Decay rate
    t2 = run_decay_rate(steps=args.steps,
                         nx=args.grid, ny=args.grid)
    all_results["decay_rate"] = t2

    # Test 3: Bridge feasibility
    t3 = run_bridge_test(steps=args.steps, nx=256, ny=64)
    all_results["bridge_feasibility"] = t3

    # Test 4: Time cost
    t4 = run_time_cost(steps=min(2000, args.steps),
                        nx=args.grid, ny=args.grid)
    all_results["time_cost"] = t4

    # Test 5: Galactic gradient
    t5 = run_galactic_gradient()
    all_results["galactic_gradient"] = t5

    # Summary
    print(f"\n{'='*65}")
    print(f"  SPINE SUMMARY")
    print(f"{'='*65}")
    print(f"  Survival threshold: lambda = {threshold}")
    print(f"  Bridge feasibility: "
          f"{'YES' if any(r['bridge_exists'] for r in t3) else 'NO'}"
          f" at some background levels")
    print(f"  Galactic gradient: core/edge = "
          f"{t5['gradient_ratio']}x")
    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_spine_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v13 SPINE — Interstellar Coherence Backbone",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "grid": args.grid,
        "steps": args.steps,
        "results": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
