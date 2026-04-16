# -*- coding: utf-8 -*-
"""
BCM v24 — BARYONIC GRIND TEST (WINCHESTER LOGIC)
=================================================
Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

The Jasper Beach Paradox: the big stones (neutrinos) are the pump,
but the sand (baryons/mesons/quarks) is the grind that determines
coherence.

Winchester T-400 Shot Shell logic:
  00 Buck (neutrinos)  = the pump (J_base)
  4 Buck  (protons)    = mid-scale displacement
  8 Buck  (quarks/dust) = fine-scale damping

Two solver runs:
  LAMINAR: clean J (pure pump, no grind)
  TURBULENT: J + baryonic grind noise weighted by throat mask

Metrics:
  R_ex = injection flux / grind flux (exchange rate)
  Coherence = correlation between laminar and turbulent σ
  Spike ratio = turbulent bill / laminar bill

Target: HR 1099 (V711 Tau) — high-activity RS CVn binary.
Output JSON → data/results/BCM_v24_baryonic_grind_YYYYMMDD_HHMMSS.json
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
MEASURE    = 5000

HR_1099 = {
    "name": "HR 1099",
    "m1": 1.0, "m2": 1.3,
    "sep": 1.0,
    "activity": 15.0,
}


def run_grind_test(system, grid, verbose=True):
    """Laminar vs turbulent: does the grind kill coherence?"""
    if verbose:
        print(f"\n{'═'*60}")
        print(f"  {system['name']} — BARYONIC GRIND TEST")
        print(f"{'═'*60}")

    x = np.linspace(-5, 5, grid)
    y = np.linspace(-5, 5, grid)
    X, Y = np.meshgrid(x, y)

    # Binary gravitational footprint
    r1 = np.sqrt((X + system['sep']/2)**2 + Y**2)
    r2 = np.sqrt((X - system['sep']/2)**2 + Y**2)
    J_base = (system['m1'] / (r1 + 0.2)) + (system['m2'] / (r2 + 0.2))

    # Throat mask (interaction zone between stars)
    throat = np.exp(-(X**2 + Y**2) / 1.0)

    # ── LAMINAR RUN (clean pump, no grind) ──
    if verbose:
        print(f"  Running LAMINAR (clean pump)...")
    t0 = time.time()
    solver = SubstrateSolver(grid=grid, layers=LAYERS, lam=LAMBDA,
                             settle=SETTLE, measure=MEASURE)
    lam_res = solver.run(J_base, verbose=False)
    t_lam = time.time() - t0

    sig_lam = lam_res["sigma_avg"]
    if sig_lam.ndim == 3:
        sig_lam_2d = np.mean(sig_lam, axis=0)
    else:
        sig_lam_2d = sig_lam

    # ── BARYONIC GRIND (Winchester buckshot) ──
    # 4 Buck: proton-scale displacement
    grind_4b = np.random.normal(0, 0.5, (grid, grid)) * system['activity']
    # 8 Buck: quark/dust fine damping
    grind_8b = np.random.normal(0, 1.2, (grid, grid)) * system['activity']

    # Effective lambda spike (local maintenance increase from grind)
    lambda_eff = LAMBDA * (1.0 + np.abs(grind_8b) * 0.1 * throat)

    # Modified source (pump + 4-Buck displacement in throat)
    J_grind = J_base + grind_4b * 0.05 * throat

    # Net source: pump minus drain from baryonic load
    J_net = J_grind - lambda_eff * sig_lam_2d * 0.1

    # ── TURBULENT RUN (grind-loaded) ──
    if verbose:
        print(f"  Running TURBULENT (grind-loaded)...")
    t0 = time.time()
    turb_res = solver.run(J_net, verbose=False)
    t_turb = time.time() - t0

    sig_turb = turb_res["sigma_avg"]
    if sig_turb.ndim == 3:
        sig_turb_2d = np.mean(sig_turb, axis=0)
    else:
        sig_turb_2d = sig_turb

    # ── Metrics ──
    coherence = float(np.corrcoef(
        sig_lam_2d.flatten(), sig_turb_2d.flatten())[0, 1])

    # R_ex: injection / grind (exchange rate)
    inj_sum = float(np.sum(J_base))
    grind_sum = float(np.sum(np.abs(grind_4b + grind_8b) * throat))
    r_ex = inj_sum / grind_sum if grind_sum > 0 else 1.0

    # Electric bill comparison
    bill_lam = float(LAMBDA * np.sum(np.abs(sig_lam_2d)))
    bill_turb = float(np.sum(lambda_eff * np.abs(sig_turb_2d)))
    spike = bill_turb / bill_lam if bill_lam > 0 else 1.0

    # Throat-specific coherence
    throat_mask = throat > 0.5
    if np.any(throat_mask):
        throat_coh = float(np.corrcoef(
            sig_lam_2d[throat_mask],
            sig_turb_2d[throat_mask])[0, 1])
    else:
        throat_coh = coherence

    if verbose:
        print(f"\n  ── RESULTS ──")
        print(f"    R_ex (exchange rate):   {r_ex:.6f}")
        print(f"    Coherence (full):       {coherence:.6f}")
        print(f"    Coherence (throat):     {throat_coh:.6f}")
        print(f"    Bill laminar:           {bill_lam:.2e}")
        print(f"    Bill turbulent:         {bill_turb:.2e}")
        print(f"    Spike ratio:            {spike:.4f}×")
        print(f"    Elapsed: lam={t_lam:.1f}s  turb={t_turb:.1f}s")

        if coherence < 0.95:
            print(f"    VERDICT: PHASE SNAP — grind broke coherence")
        elif spike > 1.10:
            print(f"    VERDICT: BILL SPIKE — grind raised maintenance")
        else:
            print(f"    VERDICT: LAMINAR PERSISTENCE — substrate healed")

    return {
        "system": system["name"], "grid": grid,
        "r_ex": float(r_ex),
        "coherence": float(coherence),
        "throat_coherence": float(throat_coh),
        "spike_ratio": float(spike),
        "bill_laminar": bill_lam,
        "bill_turbulent": bill_turb,
        "elapsed_laminar": float(t_lam),
        "elapsed_turbulent": float(t_turb),
    }


def main():
    parser = argparse.ArgumentParser(
        description="BCM v24 Baryonic Grind Test")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--grid", type=int, default=None)
    args = parser.parse_args()
    grid = args.grid or (GRID_QUICK if args.quick else GRID_PROD)

    print("=" * 60)
    print("  BCM v24 — BARYONIC GRIND TEST (WINCHESTER LOGIC)")
    print("  Stephen Justin Burdick Sr. — GIBUSH Systems")
    print("=" * 60)

    t0 = time.time()
    result = run_grind_test(HR_1099, grid)
    elapsed = time.time() - t0

    results_dir = os.path.join(_PROJECT_ROOT, "data", "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(results_dir,
                            f"BCM_v24_baryonic_grind_{timestamp}.json")
    output = {
        "test": "baryonic_grind_hr1099",
        "version": "v24", "grid": grid,
        "timestamp": timestamp,
        "elapsed": float(elapsed),
        "results": result,
        "foreman_note": "The sand grinds the wave. "
                        "Spherical sediment is damping (lambda).",
    }
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  JSON saved: {out_path}")

if __name__ == "__main__":
    main()
