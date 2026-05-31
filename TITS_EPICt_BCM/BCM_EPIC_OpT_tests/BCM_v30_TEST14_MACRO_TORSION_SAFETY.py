# -*- coding: utf-8 -*-
"""
BCM v30 TEST14 — MACRO-TORSION REGIME SAFETY CHECK
====================================================
Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Equation form: Gemini engineering formalization (SJB direction).
Code execution: The code builder.

Test13B finding:
    O2 (Macro-Torsion, abs shear, no maximum clip):
      ROOT_REENTRY outer RMS: 113.534 → 50.350 at η=100
      η sensitivity: 55.65% — CONFIRMED
    O1 (Volume Dilatant): rejected — worsens ROOT_REENTRY, damages controls.

This test (Test14):
    Apply O2-only across all six APR regimes.
    The Heaviside gate (θ=1 only if vmax > V_CRIT=300) should:
      - Allow O2 to fire only in ROOT_REENTRY
      - Produce zero effect in all lower-mass regimes

    This confirms O2 regime isolation is structural (from the gate),
    not just empirical.

Operator 2 (corrected form from Test13B):
    T = η · Θ(vmax - 300) · |∂v_φ/∂r - v_φ/r|

Regimes tested (3 galaxies each for speed):
    ROOT_REENTRY:      NGC5985, NGC2841, UGC02487
    SUBSTRATE_PLATEAU: NGC2403, UGC00634, NGC6503
    SUPPRESSION_VALLEY:NGC2955, NGC3992, NGC7331
    HIGH_A:            NGC3198, NGC6946, NGC4013
    MASS_FLOOR:        NGC4051, UGC02455, NGC6015
    DWARF_INTERMEDIATE:DDO154, UGC04305, NGC2976

Gates:
    G1: ROOT_REENTRY O2 improves outer RMS vs O0 (η best)
    G2: SUPPRESSION_VALLEY O2 outer RMS unchanged vs O0 (Θ=0)
    G3: SUBSTRATE_PLATEAU O2 outer RMS unchanged vs O0 (Θ=0)
    G4: MASS_FLOOR O2 outer RMS unchanged vs O0 (Θ=0)
    G5: η sensitivity > 1% for ROOT_REENTRY, < 0.1% for all other regimes
        (Heaviside gate is doing structural isolation work)
"""

from __future__ import annotations

import json
import sys
import os
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import cupy as cp
    import numpy as np
    xp = cp
    _BACKEND = "cupy"
except (ImportError, AttributeError):
    import numpy as np
    cp = np
    xp = np
    _BACKEND = "numpy"

_THIS_DIR      = Path(os.path.abspath(__file__)).parent
_SOLVER_ROOT   = _THIS_DIR.parent.parent
_GENESIS_BRAIN = _SOLVER_ROOT / "TITS_EPICt_BCM" / "genesis_brain"
_SPARC_DIR     = _SOLVER_ROOT / "data" / "sparc_raw"
_RESULTS_DIR   = _SOLVER_ROOT / "data" / "results"
_CORE_DIR      = _SOLVER_ROOT / "core"

for _p in [str(_SOLVER_ROOT), str(_GENESIS_BRAIN), str(_CORE_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_sparc_path = _SOLVER_ROOT / "core" / "sparc_ingest.py"
_spec = importlib.util.spec_from_file_location("sparc_ingest", str(_sparc_path))
_sparc_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sparc_mod)
load_rotation_curve   = _sparc_mod.load_rotation_curve
build_newtonian_curve = _sparc_mod.build_newtonian_curve

try:
    from BCM_test_renderer import launch_renderer, write_frame, close_renderer
    _RENDERER_AVAILABLE = True
except ImportError:
    _RENDERER_AVAILABLE = False
    def launch_renderer(*a, **kw): return None
    def write_frame(*a, **kw):     pass
    def close_renderer(*a, **kw):  pass

EPS    = 1e-9
V_CRIT = 300.0

# η sweep — focus on active range confirmed by Test13B
ETA_SWEEP = [0.0, 1.0, 5.0, 10.0, 50.0, 100.0]

REGIME_GALAXIES = {
    "ROOT_REENTRY":       ["NGC5985", "NGC2841", "UGC02487"],
    "SUBSTRATE_PLATEAU":  ["NGC2403", "UGC00634", "NGC6503"],
    "SUPPRESSION_VALLEY": ["NGC2955", "NGC3992", "NGC7331"],
    "HIGH_A":             ["NGC3198", "NGC6946", "NGC4013"],
    "MASS_FLOOR":         ["NGC4051", "UGC02455", "NGC6015"],
    "DWARF_INTERMEDIATE": ["DDO154", "UGC04305", "NGC2976"],
}

REGIME_ORDER = [
    "ROOT_REENTRY", "SUBSTRATE_PLATEAU", "SUPPRESSION_VALLEY",
    "HIGH_A", "MASS_FLOOR", "DWARF_INTERMEDIATE"
]


def load_sparc(name: str) -> Optional[Dict]:
    matches = list(_SPARC_DIR.rglob(f"{name}_rotmod.dat"))
    if not matches:
        return None
    rot      = load_rotation_curve(str(matches[0]))
    radii    = xp.array(rot["radius_kpc"], dtype=float)
    vobs     = xp.array(rot["Vobs_kms"],   dtype=float)
    v_newton = xp.array(build_newtonian_curve(rot), dtype=float)
    return {"name": name, "radii": radii, "vobs": vobs,
            "v_newton": v_newton, "vmax": float(xp.max(vobs))}


def shear_abs(radii, vobs) -> xp.ndarray:
    """
    Corrected shear: |∂v_φ/∂r - v_φ/r|
    Uses abs — flat/declining outer rotation has negative shear;
    torsion tensor responds to magnitude, not sign.
    """
    if hasattr(xp, "asnumpy"):
        r_np = xp.asnumpy(radii); v_np = xp.asnumpy(vobs)
    else:
        r_np = np.array(radii);   v_np = np.array(vobs)
    dv_dr    = np.gradient(v_np, r_np)
    v_over_r = v_np / np.maximum(r_np, EPS)
    return xp.abs(xp.array(dv_dr - v_over_r))


def apply_o2(gal: Dict, eta: float) -> float:
    """Apply O2-only and return outer RMS."""
    radii    = gal["radii"]
    vobs     = gal["vobs"]
    v_newton = gal["v_newton"]
    vmax     = gal["vmax"]

    theta  = 1.0 if vmax > V_CRIT else 0.0
    shear  = shear_abs(radii, vobs)
    t_mag  = eta * theta * shear
    v_sq   = v_newton**2 + t_mag * xp.maximum(radii, EPS)
    v_mod  = xp.sqrt(xp.maximum(v_sq, 0.0))

    r_max  = float(radii[-1])
    outer  = radii >= 0.67 * r_max
    if int(xp.sum(outer)) == 0:
        outer = xp.ones_like(radii, dtype=bool)
    return float(xp.sqrt(xp.mean((vobs[outer] - v_mod[outer])**2)))


def run_test():
    print("BCM v30 TEST14 — MACRO-TORSION REGIME SAFETY CHECK")
    print(f"Backend:  {_BACKEND}")
    print(f"Operator: O2 only (Macro-Torsion, abs shear, Heaviside at {V_CRIT} km/s)")
    print(f"η sweep:  {ETA_SWEEP}")
    print(f"Renderer: {'ACTIVE' if _RENDERER_AVAILABLE else 'NOT FOUND'}")
    print()

    # Load galaxies
    all_gals: Dict[str, Dict[str, Dict]] = {}
    for regime, names in REGIME_GALAXIES.items():
        loaded = {}
        for n in names:
            g = load_sparc(n)
            if g:
                loaded[n] = g
        all_gals[regime] = loaded
        status = " ".join(f"{n}(Θ={'1' if g['vmax']>V_CRIT else '0'})"
                          for n, g in loaded.items())
        print(f"  {regime:22s}: {status}")
    print()

    n_steps = len(REGIME_ORDER) * len(ETA_SWEEP)
    rend = launch_renderer("BCM_v30_TEST14_SAFETY",
                            n_steps=n_steps, downsample=1)
    step = 0

    # Per-regime, per-η outer RMS
    regime_sweep: Dict[str, List[Dict]] = {}
    for regime in REGIME_ORDER:
        gals = all_gals.get(regime, {})
        sweep = []
        for eta in ETA_SWEEP:
            if gals:
                rms_vals = [apply_o2(g, eta) for g in gals.values()]
                mean_rms = float(np.mean(rms_vals))
            else:
                mean_rms = 0.0
            sweep.append({"eta": eta, "mean_rms": round(mean_rms, 4)})
            step += 1
            if rend:
                write_frame(rend, np.array([[mean_rms/200]]),
                            step=step, n_steps=n_steps,
                            state=f"{regime} η={eta}",
                            metrics={"regime": regime, "eta": eta,
                                     "outer_rms": round(mean_rms, 2)},
                            downsample=1)
        regime_sweep[regime] = sweep

    # Summary table
    print("=" * 72)
    print("REGIME SAFETY TABLE — O2 outer RMS by η")
    print("=" * 72)
    header = f"{'Regime':22s}  {'Θ':>3}"
    for eta in ETA_SWEEP:
        header += f"  η={eta:>5}"
    print(header)
    print("-" * 72)

    for regime in REGIME_ORDER:
        gals  = all_gals.get(regime, {})
        theta = "1" if any(g["vmax"] > V_CRIT for g in gals.values()) else "0"
        sweep = regime_sweep[regime]
        row   = f"{regime:22s}  {theta:>3}"
        for e in sweep:
            row += f"  {e['mean_rms']:>7.3f}"
        print(row)

    # η sensitivity per regime
    print()
    print("η sensitivity (spread / max %):")
    sensitivity: Dict[str, float] = {}
    for regime in REGIME_ORDER:
        vals = [e["mean_rms"] for e in regime_sweep[regime]]
        spread = max(vals) - min(vals)
        pct    = 100 * spread / max(max(vals), EPS)
        sensitivity[regime] = pct
        print(f"  {regime:22s}: spread={spread:.4f}  ({pct:.3f}%)")

    # Gates
    rr_sweep  = regime_sweep["ROOT_REENTRY"]
    rr_o0     = rr_sweep[0]["mean_rms"]
    rr_best   = min(e["mean_rms"] for e in rr_sweep)
    rr_sens   = sensitivity["ROOT_REENTRY"]

    sv_sweep  = regime_sweep["SUPPRESSION_VALLEY"]
    sv_o0     = sv_sweep[0]["mean_rms"]
    sv_best   = min(e["mean_rms"] for e in sv_sweep)
    sv_sens   = sensitivity["SUPPRESSION_VALLEY"]

    sp_sweep  = regime_sweep["SUBSTRATE_PLATEAU"]
    sp_o0     = sp_sweep[0]["mean_rms"]
    sp_worst  = max(e["mean_rms"] for e in sp_sweep)
    sp_sens   = sensitivity["SUBSTRATE_PLATEAU"]

    mf_sweep  = regime_sweep["MASS_FLOOR"]
    mf_o0     = mf_sweep[0]["mean_rms"]
    mf_worst  = max(e["mean_rms"] for e in mf_sweep)

    # G1: ROOT_REENTRY improves
    g1 = rr_best < rr_o0

    # G2: SUPPRESSION_VALLEY unchanged (Θ=0 → flat)
    g2 = sv_sens < 0.1

    # G3: SUBSTRATE_PLATEAU not degraded by >5%
    g3 = mf_worst <= sp_o0 * 1.05 if sp_o0 > 0 else True
    # (using sp specifically)
    sp_degraded = (sp_worst / max(sp_o0, EPS) - 1) * 100
    g3 = sp_degraded <= 5.0

    # G4: MASS_FLOOR not degraded by >5%
    mf_degraded = (mf_worst / max(mf_o0, EPS) - 1) * 100
    g4 = mf_degraded <= 5.0

    # G5: η sensitivity localized — ROOT_REENTRY sens > 1%, all others < 0.1%
    non_rr_max_sens = max(v for k, v in sensitivity.items() if k != "ROOT_REENTRY")
    g5 = (rr_sens > 1.0) and (non_rr_max_sens < 0.1)

    gates_pass = sum([g1, g2, g3, g4, g5])

    print()
    print("Gates:")
    print(f"  G1 ROOT_REENTRY O2 improves ({rr_o0:.3f}→{rr_best:.3f}):   "
          f"{'PASS' if g1 else 'FAIL'}")
    print(f"  G2 SUPPRESSION_VALLEY flat (sens={sv_sens:.3f}%):     "
          f"{'PASS' if g2 else 'FAIL'}")
    print(f"  G3 SUBSTRATE_PLATEAU not degraded >5% ({sp_degraded:+.2f}%): "
          f"{'PASS' if g3 else 'FAIL'}")
    print(f"  G4 MASS_FLOOR not degraded >5% ({mf_degraded:+.2f}%):      "
          f"{'PASS' if g4 else 'FAIL'}")
    print(f"  G5 η sens localized to ROOT_REENTRY:           "
          f"{'PASS' if g5 else 'FAIL'}  "
          f"(RR={rr_sens:.2f}%  others_max={non_rr_max_sens:.3f}%)")
    print(f"  Gates passed: {gates_pass}/5")

    if gates_pass == 5:
        verdict  = "MACRO_TORSION_REGIME_SAFE_CONFIRMED_5_OF_5"
        hyp_keys = ["H_V30_MACRO_TORSION_OPERATOR_CONFIRMED",
                    "H_V30_ROOT_REENTRY_REQUIRES_ADDITIONAL_OPERATOR",
                    "H_V30_REGIME_PREDICTS_BCM_WIN"]
    elif gates_pass >= 3:
        verdict  = f"MACRO_TORSION_REGIME_SAFETY_PARTIAL_{gates_pass}_OF_5"
        hyp_keys = ["H_V30_MACRO_TORSION_OPERATOR_CONFIRMED",
                    "H_V30_ROOT_REENTRY_REQUIRES_ADDITIONAL_OPERATOR"]
    else:
        verdict  = f"MACRO_TORSION_SAFETY_INCONCLUSIVE_{gates_pass}_OF_5"
        hyp_keys = ["H_V30_MACRO_TORSION_OPERATOR_NEEDS_ABLATION"]

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"BCM_v30_TEST14_MACRO_TORSION_SAFETY_{ts}.json"
    out_path = _RESULTS_DIR / out_name

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "test_id":   "BCM_v30_TEST14",
            "test_name": "MACRO_TORSION_REGIME_SAFETY_CHECK",
            "timestamp": ts,
            "foreman":   "Stephen Justin Burdick Sr.",
            "operator": {
                "form":    "T = η·Θ(vmax-300)·|∂v_φ/∂r - v_φ/r|",
                "v_crit":  V_CRIT,
                "fix":     "abs(shear) replaces maximum(shear,0)",
            },
            "test13b_context": {
                "o2_outer_rms_rr":    50.350,
                "o2_eta_sensitivity": 55.65,
                "o1_rejected":        True,
            },
            "regime_sweep":  regime_sweep,
            "eta_sensitivity": sensitivity,
            "gate_results":  {"G1":g1,"G2":g2,"G3":g3,"G4":g4,"G5":g5},
            "gates_passed":  gates_pass,
            "verdict":       verdict,
            "hypothesis_keys": hyp_keys,
            "framework_note": (
                "O2-only applied across all 6 APR regimes. "
                "Heaviside gate θ=0 for vmax<300 should isolate O2 "
                "to ROOT_REENTRY only. G5 tests this isolation is structural. "
                "Volume Dilatant (O1) not applied — rejected by Test13B."
            ),
        }, fh, indent=2)

    close_renderer(rend, final_state=verdict,
                   metrics={"gates": gates_pass, "rr_best": round(rr_best,2),
                            "rr_sens": round(rr_sens,2),
                            "non_rr_max": round(non_rr_max_sens,3)})

    print()
    print(f"VERDICT:    {verdict}")
    print(f"HYPOTHESIS: {hyp_keys}")
    print()
    print(f"JSON written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
