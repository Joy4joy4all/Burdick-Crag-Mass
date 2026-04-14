# -*- coding: utf-8 -*-
"""
BCM v16 -- Probe Bill of Materials & Tax Curve
================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

What does a probe need to exist?
How far can it go before the substrate tax kills it?
What does each cycle cost the reactor?

A probe is a sigma structure -- a funded coherent packet.
It has mass (sigma amplitude), size (sigma width), and
coherence (structural integrity). The substrate charges
rent (lambda * sigma * dt) every step.

The probe leaves the craft's funded bubble. Beyond the
bubble, lambda increases toward void baseline. The probe's
sigma decays faster. At some radius, the probe's sigma
drops below the dissolution threshold and it ceases to
exist. That radius is the operational limit.

BILL OF MATERIALS (what the probe needs):
  - Sigma mass: initial amplitude (how much fuel to create)
  - Sigma width: spatial extent (how big)
  - Binding energy: coherence threshold (how tough)
  - Telemetry: data carried in the sigma structure
  - Shielding: none -- the probe IS the substrate event

WEIGHT CLASSES:
  MICRO:  mass=0.1, width=2 -- minimal, cheap, fragile
  LIGHT:  mass=0.5, width=3 -- standard reconnaissance
  MEDIUM: mass=1.0, width=4 -- extended range
  HEAVY:  mass=2.0, width=5 -- deep void penetration

TAX CURVE: lambda as function of distance from craft
  Inside bubble: lambda ~ 0.02 (craft funds substrate)
  Bubble edge: lambda ~ 0.05 (transition)
  Open void: lambda ~ 0.10 (baseline)
  Dead zone: lambda > 0.10 (unfunded)

Usage:
    python BCM_v16_probe_bom.py
    python BCM_v16_probe_bom.py --grid 256
"""

import numpy as np
import json
import os
import time
import math
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


def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Probe BoM & Tax Curve")
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- PROBE BILL OF MATERIALS & TAX CURVE")
    print(f"  What does a probe need? How far can it go?")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10

    # Craft bubble: lambda decreases near craft center
    # This simulates the funded zone the pumps maintain
    craft_center = nx // 2
    x_arr = np.arange(nx)
    y_arr = np.arange(ny)
    X, Y = np.meshgrid(x_arr, y_arr, indexing='ij')

    # Lambda field: low near craft, rises to void baseline
    r2_craft = (X - craft_center)**2 + (Y - ny//2)**2
    bubble_radius = 30.0  # funded zone extent
    lam_field = void_lambda - 0.08 * np.exp(-r2_craft / (2 * bubble_radius**2))
    lam_field = np.maximum(lam_field, 0.001)

    # -- PROBE WEIGHT CLASSES --
    weight_classes = [
        {"name": "MICRO",  "mass": 0.1, "width": 2.0, "desc": "Minimal, cheap, fragile"},
        {"name": "LIGHT",  "mass": 0.5, "width": 3.0, "desc": "Standard recon"},
        {"name": "MEDIUM", "mass": 1.0, "width": 4.0, "desc": "Extended range"},
        {"name": "HEAVY",  "mass": 2.0, "width": 5.0, "desc": "Deep void penetration"},
    ]

    # -- TAX CURVE: measure lambda at distances from craft --
    print(f"\n  TAX CURVE (lambda vs distance from craft center)")
    print(f"  {'-'*50}")
    print(f"  {'Distance':>10} {'Lambda':>10} {'Zone':>15} {'Tax/step':>12}")
    print(f"  {'-'*10} {'-'*10} {'-'*15} {'-'*12}")

    tax_curve = []
    test_distances = [0, 5, 10, 15, 20, 25, 30, 35, 40,
                      50, 60, 70, 80, 100, 120]

    for d in test_distances:
        ix = min(craft_center + d, nx - 1)
        iy = ny // 2
        local_lam = float(lam_field[ix, iy])

        if local_lam < 0.03:
            zone = "FUNDED"
        elif local_lam < 0.05:
            zone = "TRANSITION"
        elif local_lam < 0.09:
            zone = "OPEN VOID"
        else:
            zone = "BASELINE"

        # Tax per step for a unit mass probe
        tax = local_lam * dt
        tax_curve.append({
            "distance": d,
            "lambda": round(local_lam, 6),
            "zone": zone,
            "tax_per_step": round(tax, 6),
        })

        print(f"  {d:>10} {local_lam:>10.6f} {zone:>15} {tax:>12.6f}")

    # -- PROBE SURVIVAL TEST --
    # For each weight class, launch a probe from craft center
    # outward along the +x axis. Track sigma decay step by step.
    # Find the maximum distance before sigma drops below
    # dissolution threshold.

    dissolution_threshold = 0.01  # below this = dead
    max_arc_steps = 200          # max steps on arc

    print(f"\n{'='*65}")
    print(f"  PROBE SURVIVAL TEST")
    print(f"  Dissolution threshold: {dissolution_threshold}")
    print(f"{'='*65}")

    all_results = []

    for wc in weight_classes:
        print(f"\n  --- {wc['name']} ({wc['desc']}) ---")
        print(f"  Initial mass: {wc['mass']}  Width: {wc['width']}")

        # Create the probe as a sigma packet
        probe_sigma = np.zeros((nx, ny))
        px = craft_center
        py = ny // 2
        r2_probe = (X - px)**2 + (Y - py)**2
        probe_sigma = wc["mass"] * np.exp(-r2_probe / (2 * wc["width"]**2))

        initial_mass = float(np.sum(probe_sigma))
        initial_peak = float(np.max(probe_sigma))

        # Track the probe moving outward step by step
        # Each step: advance 1 px in +x, apply substrate decay
        trajectory = []
        alive = True
        max_distance = 0
        total_tax_paid = 0.0

        for arc_step in range(max_arc_steps):
            # Current position (moves outward from craft)
            current_x = craft_center + arc_step

            if current_x >= nx - 5:
                break

            # Shift the probe sigma to current position
            probe_sigma_shifted = np.zeros((nx, ny))
            r2_shifted = (X - current_x)**2 + (Y - ny//2)**2
            current_peak = wc["mass"] * np.exp(
                -total_tax_paid / (wc["mass"] * 0.5 + 0.01))
            probe_sigma_shifted = current_peak * np.exp(
                -r2_shifted / (2 * wc["width"]**2))

            # Apply substrate tax at current position
            local_lam = float(lam_field[min(current_x, nx-1), ny//2])
            tax_this_step = local_lam * current_peak * dt
            total_tax_paid += tax_this_step

            # Remaining peak after tax
            remaining_peak = current_peak - tax_this_step
            remaining_mass = float(np.sum(
                remaining_peak * np.exp(-r2_shifted / (2 * wc["width"]**2))))

            # Diffusion decay
            diffusion_loss = D * dt * current_peak / (wc["width"]**2)
            remaining_peak -= diffusion_loss
            remaining_peak = max(0, remaining_peak)

            distance = arc_step
            mass_fraction = remaining_peak / wc["mass"] if wc["mass"] > 0 else 0

            trajectory.append({
                "distance": distance,
                "lambda": round(local_lam, 6),
                "peak": round(remaining_peak, 6),
                "mass_fraction": round(mass_fraction, 4),
                "tax_cumulative": round(total_tax_paid, 6),
            })

            if remaining_peak < dissolution_threshold:
                alive = False
                max_distance = distance
                break
            else:
                max_distance = distance

        # Reactor cost to create one probe
        creation_cost = initial_mass  # 1:1 from reactor

        # Reactor cost for one full cycle
        # (creation + tax paid during arc)
        cycle_cost = creation_cost + total_tax_paid

        # For 12 probes, 54 cycles each
        fleet_cost_per_cycle = cycle_cost * 12
        fleet_cost_total = fleet_cost_per_cycle * 54

        result = {
            "class": wc["name"],
            "mass": wc["mass"],
            "width": wc["width"],
            "initial_mass": round(initial_mass, 4),
            "max_distance": max_distance,
            "alive_at_max": alive,
            "total_tax_paid": round(total_tax_paid, 6),
            "creation_cost": round(creation_cost, 4),
            "cycle_cost": round(cycle_cost, 4),
            "fleet_cost_per_cycle": round(fleet_cost_per_cycle, 4),
            "fleet_cost_54_cycles": round(fleet_cost_total, 4),
            "trajectory_samples": trajectory[::10],  # every 10th
        }
        all_results.append(result)

        print(f"  Max distance:     {max_distance} px")
        print(f"  Alive at max:     {'YES' if alive else 'NO -- dissolved'}")
        print(f"  Total tax paid:   {total_tax_paid:.6f}")
        print(f"  Creation cost:    {creation_cost:.4f}")
        print(f"  Cycle cost:       {cycle_cost:.4f}")
        print(f"  Fleet/cycle (12): {fleet_cost_per_cycle:.4f}")
        print(f"  Fleet total (54): {fleet_cost_total:.4f}")

        # Trajectory samples
        print(f"\n  {'Dist':>6} {'Lambda':>8} {'Peak':>8} "
              f"{'Mass%':>8} {'Tax':>10}")
        print(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")
        for t in trajectory[::10]:
            print(f"  {t['distance']:>6} {t['lambda']:>8.4f} "
                  f"{t['peak']:>8.4f} {t['mass_fraction']:>8.2%} "
                  f"{t['tax_cumulative']:>10.6f}")

    # -- COMPARISON TABLE --
    print(f"\n{'='*65}")
    print(f"  PROBE WEIGHT CLASS COMPARISON")
    print(f"{'='*65}")

    print(f"\n  {'Class':>8} {'Mass':>6} {'MaxDist':>8} "
          f"{'Survived':>9} {'CycleCost':>10} {'FleetCost':>10} "
          f"{'Efficiency':>11}")
    print(f"  {'-'*8} {'-'*6} {'-'*8} {'-'*9} {'-'*10} "
          f"{'-'*10} {'-'*11}")

    for r in all_results:
        eff = r["max_distance"] / r["cycle_cost"] if r["cycle_cost"] > 0 else 0
        survived = "YES" if r["alive_at_max"] else "DEAD"
        print(f"  {r['class']:>8} {r['mass']:>6.1f} "
              f"{r['max_distance']:>8} {survived:>9} "
              f"{r['cycle_cost']:>10.4f} "
              f"{r['fleet_cost_54_cycles']:>10.2f} "
              f"{eff:>11.2f} px/$")

    # -- RECOMMENDATIONS --
    print(f"\n{'='*65}")
    print(f"  RECOMMENDATIONS")
    print(f"{'='*65}")

    # Find best efficiency
    best = max(all_results, key=lambda r: r["max_distance"] / max(r["cycle_cost"], 0.001))
    cheapest = min(all_results, key=lambda r: r["fleet_cost_54_cycles"])
    furthest = max(all_results, key=lambda r: r["max_distance"])

    print(f"\n  Best range:      {furthest['class']} "
          f"({furthest['max_distance']} px)")
    print(f"  Best efficiency: {best['class']} "
          f"({best['max_distance']} px at cost "
          f"{best['cycle_cost']:.4f})")
    print(f"  Cheapest fleet:  {cheapest['class']} "
          f"({cheapest['fleet_cost_54_cycles']:.2f} total)")

    # Budget check against reactor sizes from v15
    print(f"\n  REACTOR BUDGET CHECK:")
    reactor_sizes = [
        ("MICRO_CORE", 20),
        ("SMALL_CORE", 50),
        ("MEDIUM_CORE", 200),
        ("LARGE_CORE", 500),
    ]
    for rname, budget in reactor_sizes:
        for r in all_results:
            pct = (r["fleet_cost_54_cycles"] / budget) * 100
            feasible = "FEASIBLE" if pct < 30 else "MARGINAL" if pct < 60 else "INFEASIBLE"
            print(f"    {rname:>12} + {r['class']:>8} probes: "
                  f"{pct:>6.1f}% of budget  [{feasible}]")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_probe_bom_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Probe Bill of Materials & Tax Curve",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Probe weight classes, survival range, reactor cost",
        "grid": nx,
        "bubble_radius": bubble_radius,
        "void_lambda": void_lambda,
        "dissolution_threshold": dissolution_threshold,
        "tax_curve": tax_curve,
        "weight_classes": all_results,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
