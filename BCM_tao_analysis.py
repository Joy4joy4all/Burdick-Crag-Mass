# -*- coding: utf-8 -*-
"""
BCM v14 — Tao Number-Theoretic Analysis of Binary Pump States
================================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

WTcubed: What Would Terence Tao Think?

Applied frameworks:
  1. Weak/strong type classification of pump ratios
  2. Efficiency landscape — drift per unit B power
  3. Critical boundary analysis (blowup conditions)
  4. Rational state space — which ratios are optimal?
  5. Bootes Void extreme stress test
  6. Sparse sampling recovery — what the sweep implies
     about the full continuous parameter space

Usage:
    python BCM_tao_analysis.py
    python BCM_tao_analysis.py --steps 2000 --grid 128
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


def run_binary_pump(steps, nx, ny, dt, D,
                     pump_A, pump_B, separation,
                     void_lambda, label="TEST"):
    """Run a binary pump test. Returns drift, speed, peak, coherence."""
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    center = (nx // 3, ny // 2)
    r2 = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2 / (2 * 5.0**2))

    lam_field = np.full((nx, ny), void_lambda)
    initial_com = compute_com(sigma)
    speeds = []
    prev_com = initial_com.copy()

    for step in range(steps):
        com = compute_com(sigma)
        if com is None:
            break

        # Pump A (main, at ship)
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        # Pump B (forward)
        if pump_B > 0:
            bx = com[0] + separation
            by = com[1]
            r2_B = (X - bx)**2 + (Y - by)**2
            pB = pump_B * np.exp(-r2_B / (2 * 3.0**2))
            sigma += pB * dt

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

        new_com = compute_com(sigma)
        if new_com is not None and prev_com is not None:
            speeds.append(float(np.linalg.norm(new_com - prev_com)))
        prev_com = new_com

    final_com = compute_com(sigma)
    if final_com is not None and initial_com is not None:
        drift = float(np.linalg.norm(final_com - initial_com))
        peak = float(np.max(sigma))
        coh = compute_coherence(sigma, final_com)
    else:
        drift = 0
        peak = 0
        coh = 0

    mean_speed = float(np.mean(speeds)) if speeds else 0
    E_final = float(np.sum(sigma**2))

    return {
        "label": label,
        "ratio": round(pump_B / pump_A, 6) if pump_A > 0 else 0,
        "pump_A": pump_A,
        "pump_B": round(pump_B, 6),
        "drift": round(drift, 6),
        "speed": round(mean_speed, 10),
        "peak": round(peak, 4),
        "coherence": round(coh, 4),
        "E_final": round(E_final, 4),
        "survived": drift > 0 and coh > 0.1,
    }


# ============================================================
# TEST 1: FINE-GRAINED RATIO SWEEP (Tao: find the structure)
# ============================================================
def test_fine_sweep(steps=1500, nx=128, ny=128,
                     dt=0.05, D=0.5, pump_A=0.5,
                     separation=15, void_lambda=0.10):
    """
    Tao would want MANY more data points to see the
    true shape of the efficiency curve. Sweep 20 ratios
    from 0.01 to 0.90 to find structure.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 1: FINE-GRAINED RATIO SWEEP")
    print(f"  Tao: 'Show me the efficiency landscape'")
    print(f"  {'='*60}")

    ratios = [0.0, 0.01, 0.02, 0.05, 0.08, 0.10,
              0.125, 0.15, 0.20, 0.25, 0.30, 0.35,
              0.40, 0.50, 0.60, 0.70, 0.80, 0.90]

    results = []

    print(f"  {'Ratio':>8} {'B_pwr':>8} {'Drift':>10} "
          f"{'Speed':>12} {'Eff':>12} {'Coh':>8} {'Class':>8}")
    print(f"  {'─'*8} {'─'*8} {'─'*10} {'─'*12} {'─'*12} "
          f"{'─'*8} {'─'*8}")

    for ratio in ratios:
        pump_B = pump_A * ratio
        r = run_binary_pump(steps, nx, ny, dt, D,
                             pump_A, pump_B, separation,
                             void_lambda,
                             label=f"R={ratio:.3f}")

        # Efficiency: drift per unit B power
        if pump_B > 0:
            efficiency = r["drift"] / pump_B
        else:
            efficiency = 0

        r["efficiency"] = round(efficiency, 4)

        # Weak/Strong classification (Tao framework)
        # Strong: high drift AND high coherence AND high efficiency
        # Weak: low drift OR low coherence OR low efficiency
        if r["drift"] > 5 and r["coherence"] > 0.5 and efficiency > 50:
            r["class"] = "STRONG"
        elif r["drift"] > 1 and r["coherence"] > 0.3:
            r["class"] = "WEAK"
        elif r["drift"] > 0.01:
            r["class"] = "MARGINAL"
        else:
            r["class"] = "NULL"

        print(f"  {ratio:>8.3f} {pump_B:>8.4f} {r['drift']:>10.4f} "
              f"{r['speed']:>12.8f} {efficiency:>12.4f} "
              f"{r['coherence']:>8.4f} {r['class']:>8}")

        results.append(r)

    # Find optimal efficiency ratio
    with_eff = [r for r in results if r["efficiency"] > 0]
    if with_eff:
        best = max(with_eff, key=lambda r: r["efficiency"])
        print(f"\n  OPTIMAL EFFICIENCY RATIO: {best['ratio']:.3f}")
        print(f"    Drift: {best['drift']:.4f} px")
        print(f"    Efficiency: {best['efficiency']:.4f} drift/power")
        print(f"    Class: {best['class']}")

    # Strong ratios
    strong = [r for r in results if r["class"] == "STRONG"]
    weak = [r for r in results if r["class"] == "WEAK"]
    strong_ratios = [str(round(r["ratio"], 3)) for r in strong]
    weak_ratios = [str(round(r["ratio"], 3)) for r in weak]
    print(f"\n  STRONG ratios: {len(strong)} "
          f"({', '.join(strong_ratios)})")
    print(f"  WEAK ratios:   {len(weak)} "
          f"({', '.join(weak_ratios)})")

    # ── ELASTICITY ANALYSIS ──
    # E = (d_drift/drift) / (d_ratio/ratio)
    # High E: sensitive. Low E: inelastic. E~1: power law.
    print(f"\n  {'─'*60}")
    print(f"  ELASTICITY ANALYSIS")
    print(f"  E = (pct change drift) / (pct change ratio)")
    print(f"  E~1.0 = linear power law (invariant)")
    print(f"  E>1.0 = elastic (sensitive to ratio change)")
    print(f"  E<1.0 = inelastic (diminishing returns)")
    print(f"  {'─'*60}")

    non_zero = [r for r in results if r["ratio"] > 0 and r["drift"] > 0.001]
    elasticities = []

    print(f"  {'R1 to R2':>16} {'Elasticity':>12} {'Regime':>12} "
          f"{'Invariant':>10}")
    print(f"  {'─'*16} {'─'*12} {'─'*12} {'─'*10}")

    for i in range(len(non_zero) - 1):
        r1 = non_zero[i]
        r2 = non_zero[i + 1]

        dr_ratio = (r2["ratio"] - r1["ratio"]) / r1["ratio"]
        dr_drift = (r2["drift"] - r1["drift"]) / r1["drift"]

        if abs(dr_ratio) > 1e-10:
            elasticity = dr_drift / dr_ratio
        else:
            elasticity = 0

        if abs(elasticity - 1.0) < 0.15:
            regime = "LINEAR"
            invariant = "YES"
        elif elasticity > 1.0:
            regime = "ELASTIC"
            invariant = "NO"
        elif elasticity > 0:
            regime = "INELASTIC"
            invariant = "NO"
        else:
            regime = "INVERSE"
            invariant = "BREAK"

        r_label = f"{r1['ratio']:.3f}->{r2['ratio']:.3f}"
        print(f"  {r_label:>16} {elasticity:>12.4f} "
              f"{regime:>12} {invariant:>10}")

        elasticities.append({
            "ratio_from": r1["ratio"],
            "ratio_to": r2["ratio"],
            "elasticity": round(elasticity, 6),
            "regime": regime,
            "invariant": invariant == "YES",
        })

    # Invariant curve detection
    if elasticities:
        e_values = [e["elasticity"] for e in elasticities
                     if e["elasticity"] > 0]
        if e_values:
            e_mean = float(np.mean(e_values))
            e_std = float(np.std(e_values))
            e_cv = e_std / abs(e_mean) if abs(e_mean) > 0 else 0

            print(f"\n  Elasticity mean: {e_mean:.4f}")
            print(f"  Elasticity std:  {e_std:.4f}")
            print(f"  Elasticity CV:   {e_cv:.4f}")

            if e_cv < 0.15:
                print(f"  INVARIANT CURVE FOUND: E ~ {e_mean:.2f}")
                print(f"  Power law: v ~ R^{e_mean:.2f}")
            else:
                print(f"  NO SINGLE INVARIANT — regime transitions")
                for i in range(len(elasticities) - 1):
                    e1 = elasticities[i]["elasticity"]
                    e2 = elasticities[i + 1]["elasticity"]
                    if abs(e2 - e1) > 0.3:
                        print(f"    Transition at R="
                              f"{elasticities[i+1]['ratio_from']:.3f}"
                              f" (E: {e1:.3f} -> {e2:.3f})")

    # ── STRONG/WEAK INVERSE OPERATIONS ──
    # Cost of crossing from weak to strong regime
    print(f"\n  {'─'*60}")
    print(f"  STRONG/WEAK INVERSE OPERATIONS")
    print(f"  Cost to transition between regimes")
    print(f"  {'─'*60}")

    if strong and weak:
        for w in weak:
            nearest_s = min(strong,
                key=lambda s: abs(s["ratio"] - w["ratio"]))
            delta_r = abs(nearest_s["ratio"] - w["ratio"])
            delta_d = nearest_s["drift"] - w["drift"]
            delta_eff = (nearest_s.get("efficiency", 0) -
                          w.get("efficiency", 0))
            inv_cost = delta_r / delta_d if delta_d > 0 else float('inf')

            print(f"    WEAK R={w['ratio']:.3f} -> "
                  f"STRONG R={nearest_s['ratio']:.3f}")
            print(f"      dR={delta_r:.4f}  "
                  f"dDrift={delta_d:.4f}  "
                  f"inv_cost={inv_cost:.6f}")
            print(f"      dEfficiency={delta_eff:.4f}  "
                  f"(+ = strong more efficient)")

    # ── ELASTICITY RATIO OF THE MODEL ──
    # The overall elasticity of the BCM binary drive:
    # How responsive is the system to control input?
    if non_zero and len(non_zero) >= 2:
        total_dr = (non_zero[-1]["ratio"] - non_zero[0]["ratio"])
        total_dd = (non_zero[-1]["drift"] - non_zero[0]["drift"])
        if total_dr > 0 and non_zero[0]["drift"] > 0:
            global_E = ((total_dd / non_zero[0]["drift"]) /
                         (total_dr / non_zero[0]["ratio"]))
            print(f"\n  GLOBAL ELASTICITY: {global_E:.4f}")
            if global_E > 0.8 and global_E < 1.2:
                print(f"  System is UNIT ELASTIC — linear control")
            elif global_E > 1.2:
                print(f"  System is SUPER-ELASTIC — amplifying")
            else:
                print(f"  System is SUB-ELASTIC — damped response")

    # Store in results
    for r in results:
        r["_elasticity_data"] = elasticities

    return results


# ============================================================
# TEST 2: CRITICAL BOUNDARY (Tao: blowup conditions)
# ============================================================
def test_critical_boundary(steps=1500, nx=128, ny=128,
                             dt=0.05, D=0.5, pump_A=0.5,
                             separation=15):
    """
    Tao's Navier-Stokes work: where does the system cross
    from smooth (surviving) to singular (dissolving)?

    Sweep void_lambda at fixed ratio to find the exact
    survival boundary. The boundary IS the critical exponent.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 2: CRITICAL BOUNDARY (blowup analysis)")
    print(f"  Tao: 'Where is the singularity?'")
    print(f"  {'='*60}")
    print(f"  Fixed ratio=0.125 (1:8). Sweep void lambda.")
    print(f"  Find the EXACT boundary where transport fails.")
    print(f"  {'─'*60}")

    void_lambdas = [0.01, 0.02, 0.03, 0.05, 0.08,
                     0.10, 0.12, 0.15, 0.20, 0.25,
                     0.30, 0.40, 0.50, 0.60, 0.80, 1.00]

    results = []
    ratio = 0.125

    print(f"  {'Void_lam':>10} {'Drift':>10} {'Speed':>12} "
          f"{'Peak':>8} {'Coh':>8} {'Status':>10}")
    print(f"  {'─'*10} {'─'*10} {'─'*12} {'─'*8} {'─'*8} "
          f"{'─'*10}")

    for vl in void_lambdas:
        pump_B = pump_A * ratio
        r = run_binary_pump(steps, nx, ny, dt, D,
                             pump_A, pump_B, separation,
                             void_lambda=vl,
                             label=f"VL={vl:.2f}")

        status = "SURVIVED" if r["survived"] else "FAILED"
        print(f"  {vl:>10.2f} {r['drift']:>10.4f} "
              f"{r['speed']:>12.8f} {r['peak']:>8.4f} "
              f"{r['coherence']:>8.4f} {status:>10}")

        r["void_lambda"] = vl
        results.append(r)

    # Find critical boundary
    survived = [r for r in results if r["survived"]]
    failed = [r for r in results if not r["survived"]]

    if survived and failed:
        last_alive = max(survived, key=lambda r: r["void_lambda"])
        first_dead = min(failed, key=lambda r: r["void_lambda"])
        boundary = (last_alive["void_lambda"] +
                     first_dead["void_lambda"]) / 2

        print(f"\n  CRITICAL BOUNDARY:")
        print(f"    Last survived: lambda = "
              f"{last_alive['void_lambda']:.2f}")
        print(f"    First failed:  lambda = "
              f"{first_dead['void_lambda']:.2f}")
        print(f"    Boundary:      lambda ~ {boundary:.3f}")
    elif not failed:
        print(f"\n  ALL SURVIVED — boundary beyond lambda=1.00")
        boundary = None
    else:
        print(f"\n  ALL FAILED — check pump settings")
        boundary = None

    return results, boundary


# ============================================================
# TEST 3: BOOTES VOID STRESS TEST
# ============================================================
def test_bootes_void(steps=2000, nx=128, ny=128,
                      dt=0.05, D=0.5, pump_A=0.5,
                      separation=15):
    """
    Bootes Void: the largest known underdensity in the
    observable universe. ~250 million light years across.
    If lambda=0.12 is interstellar void, Bootes is the
    extreme case.

    Test at lambda=0.30, 0.50, 0.80, 1.00.
    At what void depth does the binary drive fail?

    Sweep multiple ratios at each depth to find the
    minimum power that crosses Bootes.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 3: BOOTES VOID STRESS TEST")
    print(f"  Tao: 'What survives the extreme?'")
    print(f"  {'='*60}")
    print(f"  The deepest void. The hardest test.")
    print(f"  {'─'*60}")

    void_depths = [0.30, 0.50, 0.80, 1.00]
    ratios_to_test = [0.125, 0.25, 0.50, 0.75]

    results = []

    print(f"  {'Void':>6} {'Ratio':>8} {'Drift':>10} "
          f"{'Speed':>12} {'Peak':>8} {'Coh':>8} {'Status':>10}")
    print(f"  {'─'*6} {'─'*8} {'─'*10} {'─'*12} {'─'*8} "
          f"{'─'*8} {'─'*10}")

    for vl in void_depths:
        for ratio in ratios_to_test:
            pump_B = pump_A * ratio
            r = run_binary_pump(steps, nx, ny, dt, D,
                                 pump_A, pump_B, separation,
                                 void_lambda=vl,
                                 label=f"BOO_{vl}_{ratio}")

            status = "SURVIVED" if r["survived"] else "FAILED"
            print(f"  {vl:>6.2f} {ratio:>8.3f} {r['drift']:>10.4f} "
                  f"{r['speed']:>12.8f} {r['peak']:>8.4f} "
                  f"{r['coherence']:>8.4f} {status:>10}")

            r["void_lambda"] = vl
            results.append(r)

    # Summary: which ratios survive Bootes?
    print(f"\n  BOOTES SURVIVAL MATRIX:")
    print(f"  {'':>8}", end="")
    for ratio in ratios_to_test:
        print(f" {ratio:>8.3f}", end="")
    print()

    for vl in void_depths:
        print(f"  λ={vl:.2f}", end="")
        for ratio in ratios_to_test:
            match = [r for r in results
                     if abs(r["void_lambda"] - vl) < 0.001
                     and abs(r["ratio"] - ratio) < 0.001]
            if match and match[0]["survived"]:
                print(f" {'ALIVE':>8}", end="")
            else:
                print(f" {'DEAD':>8}", end="")
        print()

    return results


# ============================================================
# TEST 4: RATIONAL STRUCTURE (Tao: number theory)
# ============================================================
def test_rational_structure(steps=1500, nx=128, ny=128,
                              dt=0.05, D=0.5, pump_A=0.5,
                              separation=15, void_lambda=0.10):
    """
    Tao would ask: do rational ratios (p/q with small q)
    produce qualitatively different transport than irrational
    approximations?

    Test simple fractions vs golden ratio vs sqrt(2) vs pi.
    If transport depends on the NUMBER THEORY of the ratio,
    that's deep structure.
    """
    print(f"\n  {'='*60}")
    print(f"  TEST 4: RATIONAL vs IRRATIONAL RATIOS")
    print(f"  Tao: 'Does number theory matter?'")
    print(f"  {'='*60}")

    test_ratios = [
        (1/2,   "1/2 (simple)"),
        (1/3,   "1/3 (simple)"),
        (1/4,   "1/4 (simple)"),
        (1/5,   "1/5 (simple)"),
        (1/7,   "1/7 (prime denom)"),
        (1/8,   "1/8 (power of 2)"),
        (1/11,  "1/11 (prime denom)"),
        (1/13,  "1/13 (prime denom)"),
        (2/7,   "2/7 (composite)"),
        (3/8,   "3/8 (composite)"),
        (1/np.e,         "1/e (transcendental)"),
        (1/np.pi,        "1/pi (transcendental)"),
        ((np.sqrt(5)-1)/2 * 0.5,  "phi/2 (golden)"),
        (1/np.sqrt(2),   "1/sqrt2 (algebraic)"),
    ]

    results = []

    print(f"  {'Ratio':>10} {'Label':>22} {'Drift':>10} "
          f"{'Eff':>10} {'Coh':>8}")
    print(f"  {'─'*10} {'─'*22} {'─'*10} {'─'*10} {'─'*8}")

    for ratio, label in test_ratios:
        pump_B = pump_A * ratio
        r = run_binary_pump(steps, nx, ny, dt, D,
                             pump_A, pump_B, separation,
                             void_lambda,
                             label=label)

        eff = r["drift"] / pump_B if pump_B > 0 else 0
        r["efficiency"] = round(eff, 4)

        print(f"  {ratio:>10.6f} {label:>22} {r['drift']:>10.4f} "
              f"{eff:>10.4f} {r['coherence']:>8.4f}")

        results.append(r)

    # Compare: do prime denominators outperform?
    simple = [r for r in results if "simple" in r["label"]]
    prime = [r for r in results if "prime" in r["label"]]
    trans = [r for r in results if "transcendental" in r["label"]
             or "golden" in r["label"]
             or "algebraic" in r["label"]]

    if simple:
        avg_simple = np.mean([r["efficiency"] for r in simple])
        print(f"\n  Simple fraction avg efficiency: {avg_simple:.4f}")
    if prime:
        avg_prime = np.mean([r["efficiency"] for r in prime])
        print(f"  Prime denominator avg efficiency: {avg_prime:.4f}")
    if trans:
        avg_trans = np.mean([r["efficiency"] for r in trans])
        print(f"  Transcendental avg efficiency:  {avg_trans:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="BCM v14 Tao Number-Theoretic Analysis")
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v14 — WTcubed: WHAT WOULD TAO THINK?")
    print(f"  Number-Theoretic Analysis of Binary Pump States")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC — GIBUSH Systems")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")
    print(f"{'='*65}")

    all_results = {}

    # Test 1: Fine sweep
    r1 = test_fine_sweep(steps=args.steps, nx=nx, ny=ny)
    all_results["fine_sweep"] = r1

    # Test 2: Critical boundary
    r2, boundary = test_critical_boundary(
        steps=args.steps, nx=nx, ny=ny)
    all_results["critical_boundary"] = {
        "results": r2, "boundary": boundary}

    # Test 3: Bootes Void
    r3 = test_bootes_void(steps=args.steps, nx=nx, ny=ny)
    all_results["bootes_void"] = r3

    # Test 4: Rational structure
    r4 = test_rational_structure(steps=args.steps, nx=nx, ny=ny)
    all_results["rational_structure"] = r4

    # Summary
    print(f"\n{'='*65}")
    print(f"  TAO ANALYSIS SUMMARY")
    print(f"{'='*65}")

    # Best efficiency from fine sweep
    with_eff = [r for r in r1 if r.get("efficiency", 0) > 0]
    if with_eff:
        best = max(with_eff, key=lambda r: r["efficiency"])
        print(f"  Optimal ratio: {best['ratio']:.3f} "
              f"(eff={best['efficiency']:.4f})")

    strong = [r for r in r1 if r.get("class") == "STRONG"]
    print(f"  Strong states: {len(strong)}")

    if boundary:
        print(f"  Critical boundary: lambda ~ {boundary:.3f}")

    # Bootes
    bootes_survived = [r for r in r3 if r["survived"]]
    print(f"  Bootes survivors: {len(bootes_survived)}/{len(r3)}")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_tao_analysis_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v14 Tao Number-Theoretic Analysis",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "WTcubed — weak/strong ratio classification, "
                   "critical boundaries, Bootes Void stress test, "
                   "rational vs irrational transport structure",
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
