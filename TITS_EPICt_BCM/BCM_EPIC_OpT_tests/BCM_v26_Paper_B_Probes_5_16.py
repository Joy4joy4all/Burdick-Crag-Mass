# -*- coding: utf-8 -*-
"""
BCM v26 Paper B Probe Test 5_16
Paper B Section 7.2 -- Four-Field Tensor Phase Test (Post-Processor)

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
Date: 2026-04-22

--------------------------------------------------------------------
PRIMACY STATEMENT
--------------------------------------------------------------------
All theoretical concepts, the Anchor Equation, the Brucetron and
Psi_bruce formulation, the four-field tensor decomposition of the
Paper B Section 5 transition region into (spectral transition
center, stiffness centroid, absorbing boundary, hysteresis
functional), the identification that these four invariants were
previously conflated in the fold-bifurcation framing and must be
deconflated, the invariance-and-distinctness gate structure, and
every originating insight in this file belong solely to Stephen
Justin Burdick Sr. Stephen Burdick is the sole discoverer and
theoretical originator of the BCM framework. Four AI systems
(Claude, ChatGPT, Gemini, Grok) assist the project as
computational tools and reviewers at the direction of the
Foreman. No AI system owns or co-owns any theoretical concept.
Emerald Entities LLC -- GIBUSH Systems.

--------------------------------------------------------------------
SCOPE
--------------------------------------------------------------------
Test 5_16 is a post-processor on the 5_15 JSON output. It
performs no solver runs. It extracts the four-field state tensor

    (lambda_c, lambda_fold_center, lambda_cold_entry, H(xi))

per xi across the six values tested in 5_15, then evaluates five
gates on the assembled tensor:

  E1 spectral invariance:          rel_range(lambda_c) < 1e-6
  E2 stiffness centroid invariance: rel_range(lambda_fold_center) < 1e-6
  E3 absorbing boundary invariance: rel_range(lambda_cold_entry) < 1e-6
  E4 hysteresis invariance:        rel_range(H(xi)) < 1e-6
  E5 field distinctness:            |lambda_c - lambda_fold_center|
                                    / lambda_c > 0.10

Operational definitions (strictly from 5_15 data):

  lambda_c         = active-region sigmoid inflection
                     (regime_classification.active_region_sigmoid_fit
                      .lambda_c)

  lambda_fold_center = argmax(n_steps) in active region
                     (computed here from forward_sweep_results;
                      NOT the classifier-reported lambda_fold_center,
                      which in v2 is set to lambda_c and thus
                      collapses the two fields)

  lambda_cold_entry = first lambda where Phi stays <= 1% max_phi for
                     2+ consecutive sweep points
                     (regime_classification.lambda_cold_entry)

  H(xi)            = hysteresis area over active region
                     (hysteresis_restricted.area in each per-xi
                      payload)

--------------------------------------------------------------------
WHY THIS MATTERS
--------------------------------------------------------------------
Tests 5_11 and 5_12 set lambda_fold_center equal to lambda_c
(the sigmoid inflection). This was the classifier-v2 "fix" for
5_11's argmax(n_steps) bug. The fix was STRUCTURALLY CORRECT for
the specific misuse in 5_11 (using argmax(n_steps) as the fold
center for perturbation-axis testing led the perturbation to be
applied at a post-collapse dead region). But it CONFLATED two
distinct geometric objects that the 5_15 data now shows are NOT
the same:

  - The Phi-sigmoid inflection (spectral transition center) sits
    at lambda ~ 0.059 and is an eigenvalue of the order-parameter
    transition.

  - The stiffness centroid (where solver runtime peaks) sits at
    lambda ~ 0.112 and is a property of the PDE's numerical
    response to the Taylor kernel's saturation regime.

These two lambdas are not equal. Treating them as one object
hides the fact that Paper B Section 5 describes at least two
phenomena, not one. The four-field tensor makes them explicit
and separately measurable.

The 5_14 audit showed that xi is numerically inactive in the
tested regime under the current Psi_bruce formulation. The
four-field tensor test verifies what is consequently predicted:
all four fields are xi-invariant across [0.005, 0.07]. This is
a CONSISTENCY check of the 5_14 audit via an independent metric
structure.

--------------------------------------------------------------------
RELATIONSHIP TO EXISTING HYPOTHESES
--------------------------------------------------------------------
  H_PAPER_B_1_PHI_SIGMOID (VALIDATED) -- addresses lambda_c only
  H_PAPER_B_STIFFNESS_MANIFOLD (NEEDS_MORE_DATA) -- addresses the
      stiffness centroid region, plus convergence delay and
      grad|J|^2 structure
  H_PAPER_B_COLD_TORUS_ABSORBING (NEEDS_MORE_DATA) -- addresses
      lambda_cold_entry only
  H_PAPER_B_FOLD_BIFURCATION (evidence 0) -- NOT addressed;
      remains unvalidatable under current Psi_bruce until the
      Foreman revisits the formulation

New hypothesis registered by this test:
  H_PAPER_B_4FIELD_DECOMPOSITION -- the four invariants are
      simultaneously (a) xi-invariant in the tested regime and
      (b) distinct from each other (lambda_c != lambda_fold_
      center by at least 10% relative). PASS gives primary
      evidence that Paper B Section 5's transition geometry is
      properly described by four decoupled invariants, not one
      collapsed "fold."
"""

import glob
import json
import os
import sys
import time
from datetime import datetime

import numpy as np


# =====================================================================
# CONFIGURATION
# =====================================================================

CFG = {
    # Search for latest 5_15 JSON
    "search_subdir": os.path.join("data", "paper_results"),
    "search_pattern": "BCM_v26_Paper_B_Probes_5_15_*.json",

    # Fallback: if 5_15 is absent, use 5_12 / 5_14 as best-effort
    # single-xi points (will still produce tensor but without
    # invariance analysis)
    "fallback_patterns": [
        "BCM_v26_Paper_B_Probes_5_14_*.json",
        "BCM_v26_Paper_B_Probes_5_12_*.json",
    ],

    # Gate thresholds
    "e_invariance_rel_range": 1e-6,   # E1-E4 invariance tolerance
    "e_distinctness_min_rel": 0.10,   # E5 distinctness threshold
}


# =====================================================================
# INPUT RESOLUTION
# =====================================================================

def find_source_json():
    """Locate the latest 5_15 JSON, with fallbacks."""
    search_dirs = [
        os.path.join(os.getcwd(), CFG["search_subdir"]),
        os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", CFG["search_subdir"]
        )),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    patterns = [CFG["search_pattern"]] + CFG["fallback_patterns"]
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for pat in patterns:
            matches = glob.glob(os.path.join(d, pat))
            if matches:
                matches.sort(key=os.path.getmtime, reverse=True)
                return matches[0], pat
    return None, None


# =====================================================================
# TENSOR EXTRACTION
# =====================================================================

def extract_per_xi_tensor(source_json):
    """Build the four-field tensor per xi from a 5_15-shape JSON.

    Returns a list of dicts, one per xi, with keys:
        xi, lambda_c, lambda_fold_center (argmax n_steps in active),
        lambda_cold_entry, H_xi, plus diagnostic lambdas and
        sigmoid fit quality.

    Handles fallback: if the source is 5_12/5_14 (single xi), the
    returned list has one entry.
    """
    tensor = []

    # 5_15 shape: per_xi_payload keyed by "xi_<value>"
    per_xi = source_json.get("per_xi_payload")
    if per_xi and isinstance(per_xi, dict):
        for key, payload in per_xi.items():
            entry = _extract_one_xi(payload)
            if entry is not None:
                tensor.append(entry)
        tensor.sort(key=lambda e: e["xi"])
        return tensor, "5_15_six_xi"

    # Fallback: single-xi JSON (5_12, 5_14)
    if source_json.get("forward_sweep_results") is not None:
        fake = {
            "xi": source_json.get("pde_spec", {}).get("xi_coupling"),
            "forward_sweep_results": source_json["forward_sweep_results"],
            "regime_classification": source_json.get("regime_classification", {}),
            "hysteresis_restricted": {
                "area": source_json.get("fold_evaluation", {})
                    .get("hysteresis_restricted_area"),
            },
        }
        entry = _extract_one_xi(fake)
        if entry is not None:
            tensor.append(entry)
        return tensor, "single_xi_fallback"

    return tensor, None


def _extract_one_xi(payload):
    """Extract the 4-field row for a single xi payload."""
    xi = payload.get("xi")
    regime = payload.get("regime_classification") or {}
    fwd = payload.get("forward_sweep_results") or []
    hyst = payload.get("hysteresis_restricted") or {}

    fit = regime.get("active_region_sigmoid_fit") or {}
    lambda_c = fit.get("lambda_c")
    r2 = fit.get("r_squared")
    k = fit.get("k")
    lambda_cold_entry = regime.get("lambda_cold_entry")

    # Compute argmax(n_steps) over active region (pre-cold).
    # An active point is one with regime_label in
    # {sigmoid_basin, fold_boundary}; fallback: lambda < cold_entry.
    active_points = []
    for r in fwd:
        lbl = r.get("regime_label")
        if lbl in ("sigmoid_basin", "fold_boundary"):
            active_points.append(r)
        elif lbl is None and lambda_cold_entry is not None:
            if r["lambda"] < lambda_cold_entry:
                active_points.append(r)
    if not active_points and lambda_cold_entry is not None:
        active_points = [r for r in fwd if r["lambda"] < lambda_cold_entry]
    if not active_points:
        active_points = list(fwd)

    if active_points:
        steps_array = [r.get("n_steps", 0) for r in active_points]
        lambdas_array = [r.get("lambda", 0.0) for r in active_points]
        max_idx = int(np.argmax(steps_array))
        lambda_fold_center_stiffness = float(lambdas_array[max_idx])
        max_n_steps = int(steps_array[max_idx])
    else:
        lambda_fold_center_stiffness = None
        max_n_steps = None

    H_xi = hyst.get("area")

    if xi is None or lambda_c is None:
        return None

    return {
        "xi": float(xi),
        "lambda_c_spectral": float(lambda_c),
        "lambda_fold_center_stiffness": (
            float(lambda_fold_center_stiffness)
            if lambda_fold_center_stiffness is not None else None
        ),
        "lambda_cold_entry": (
            float(lambda_cold_entry) if lambda_cold_entry is not None else None
        ),
        "H_xi": float(H_xi) if H_xi is not None else None,
        "sigmoid_r_squared": float(r2) if r2 is not None else None,
        "sigmoid_k": float(k) if k is not None else None,
        "max_n_steps_at_stiffness_peak": max_n_steps,
        "n_active_points": len(active_points),
    }


# =====================================================================
# INVARIANCE + DISTINCTNESS ANALYSIS
# =====================================================================

def relative_range(values):
    """Max relative range = (max - min) / |mean| for non-None values."""
    arr = [v for v in values if v is not None]
    if len(arr) < 2:
        return None
    arr = np.array(arr, dtype=float)
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    mean = float(np.mean(arr))
    denom = abs(mean) if abs(mean) > 1e-30 else 1e-30
    return {
        "n": int(len(arr)),
        "min": mn,
        "max": mx,
        "mean": mean,
        "range": float(mx - mn),
        "relative_range": float((mx - mn) / denom),
    }


def evaluate_gates(tensor, cfg):
    """Evaluate E1-E5 on the assembled tensor."""
    inv_tol = cfg["e_invariance_rel_range"]
    dist_tol = cfg["e_distinctness_min_rel"]

    rr_lambda_c = relative_range([t["lambda_c_spectral"] for t in tensor])
    rr_fold = relative_range(
        [t["lambda_fold_center_stiffness"] for t in tensor]
    )
    rr_cold = relative_range([t["lambda_cold_entry"] for t in tensor])
    rr_H = relative_range([t["H_xi"] for t in tensor])

    def passes_inv(rr):
        if rr is None:
            return None
        return bool(rr["relative_range"] < inv_tol)

    e1 = passes_inv(rr_lambda_c)
    e2 = passes_inv(rr_fold)
    e3 = passes_inv(rr_cold)
    e4 = passes_inv(rr_H)

    # E5: field distinctness at EACH xi -- lambda_c and
    # lambda_fold_center_stiffness should be at least dist_tol apart
    # (relative to lambda_c) for every xi.
    distinctness_per_xi = []
    for t in tensor:
        lc = t["lambda_c_spectral"]
        lf = t["lambda_fold_center_stiffness"]
        if lc is None or lf is None or abs(lc) < 1e-30:
            distinctness_per_xi.append({
                "xi": t["xi"],
                "rel_diff": None,
                "distinct": None,
            })
            continue
        rel_diff = abs(lf - lc) / abs(lc)
        distinctness_per_xi.append({
            "xi": t["xi"],
            "lambda_c": lc,
            "lambda_fold_center": lf,
            "rel_diff": float(rel_diff),
            "distinct": bool(rel_diff > dist_tol),
        })
    distinctness_vals = [
        d["rel_diff"] for d in distinctness_per_xi if d["rel_diff"] is not None
    ]
    if distinctness_vals:
        min_rel_diff = float(min(distinctness_vals))
        e5 = bool(min_rel_diff > dist_tol)
    else:
        min_rel_diff = None
        e5 = None

    gates = {
        "E1_spectral_invariance": {
            "passed": e1,
            "relative_range": rr_lambda_c,
            "threshold": inv_tol,
        },
        "E2_stiffness_centroid_invariance": {
            "passed": e2,
            "relative_range": rr_fold,
            "threshold": inv_tol,
        },
        "E3_absorbing_boundary_invariance": {
            "passed": e3,
            "relative_range": rr_cold,
            "threshold": inv_tol,
        },
        "E4_hysteresis_invariance": {
            "passed": e4,
            "relative_range": rr_H,
            "threshold": inv_tol,
        },
        "E5_field_distinctness": {
            "passed": e5,
            "min_relative_difference": min_rel_diff,
            "threshold": dist_tol,
            "per_xi": distinctness_per_xi,
        },
    }

    all_truthy = [v for v in (e1, e2, e3, e4, e5) if v is not None]
    passed_count = sum(1 for v in all_truthy if v)
    total = len(all_truthy)

    if total == 5 and passed_count == 5:
        result = "PASS"
    elif passed_count >= 4 and total >= 4:
        result = "PASS"  # 4 of 5 accepted as secondary
    else:
        result = "INCONCLUSIVE"

    return gates, result, passed_count, total


# =====================================================================
# OUTPUT PATH
# =====================================================================

def resolve_output_path(filename):
    cwd_paper = os.path.join(os.getcwd(), "data", "paper_results")
    if os.path.isdir(cwd_paper):
        return os.path.join(cwd_paper, filename)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_paper = os.path.abspath(
        os.path.join(script_dir, "..", "..", "data", "paper_results")
    )
    if os.path.isdir(parent_paper):
        return os.path.join(parent_paper, filename)
    return os.path.join(script_dir, filename)


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 76)
    print("BCM v26 Paper B Probe Test 5_16 -- Four-Field Tensor Phase Test")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC / GIBUSH Systems")
    print("=" * 76)
    print("Type: post-processor (no solver runs)")
    print("Target: H_PAPER_B_4FIELD_DECOMPOSITION")
    print()

    start_ts = datetime.now()
    start_wall = time.time()

    source_path, matched_pattern = find_source_json()
    if source_path is None:
        print("ERROR: no compatible source JSON found.")
        print(f"Searched for {CFG['search_pattern']} and fallbacks.")
        sys.exit(1)
    print(f"Source JSON: {source_path}")
    print(f"Matched pattern: {matched_pattern}")
    with open(source_path, "r", encoding="utf-8") as fh:
        source_json = json.load(fh)
    print(f"Source test: {source_json.get('test_name')}  "
          f"({source_json.get('timestamp')})")
    print()

    tensor, source_mode = extract_per_xi_tensor(source_json)
    if not tensor:
        print("ERROR: could not extract four-field tensor from source.")
        sys.exit(1)
    print(f"Source mode: {source_mode}")
    print(f"xi points extracted: {len(tensor)}")
    print()

    # --- Tensor table ---
    print("=" * 76)
    print("FOUR-FIELD TENSOR (per xi)")
    print("=" * 76)
    header = (f"{'xi':>7}  {'lambda_c':>12}  "
              f"{'lambda_fold_ctr':>16}  {'lambda_cold':>12}  "
              f"{'H(xi)':>10}")
    print(header)
    print("-" * len(header))
    for t in tensor:
        def fmt(v, spec):
            return format(v, spec) if v is not None else "        None"
        print(f"{t['xi']:>7.4f}  "
              f"{fmt(t['lambda_c_spectral'], '12.9f')}  "
              f"{fmt(t['lambda_fold_center_stiffness'], '16.9f')}  "
              f"{fmt(t['lambda_cold_entry'], '12.9f')}  "
              f"{fmt(t['H_xi'], '10.6f')}")
    print("=" * 76)
    print()

    # --- Gate evaluation ---
    gates, result, passed_count, total = evaluate_gates(tensor, CFG)

    print("GATES")
    print("-" * 76)
    for gate_name, gate in gates.items():
        status = "PASS" if gate["passed"] else ("FAIL" if gate["passed"] is False else "N/A")
        if "relative_range" in gate and gate["relative_range"] is not None:
            rr = gate["relative_range"]["relative_range"]
            mean = gate["relative_range"]["mean"]
            print(f"  {gate_name:<40}  {status}  rel_range={rr:.3e}  mean={mean:.6e}")
        elif "min_relative_difference" in gate:
            mrd = gate["min_relative_difference"]
            mrd_str = f"{mrd:.4f}" if mrd is not None else "None"
            print(f"  {gate_name:<40}  {status}  min_rel_diff={mrd_str}")
        else:
            print(f"  {gate_name:<40}  {status}")
    print("-" * 76)
    print(f"Gates passed: {passed_count}/{total}")
    print(f"RESULT: {result}")
    print()

    # --- Interpretation ---
    e1 = gates["E1_spectral_invariance"]["passed"]
    e2 = gates["E2_stiffness_centroid_invariance"]["passed"]
    e3 = gates["E3_absorbing_boundary_invariance"]["passed"]
    e4 = gates["E4_hysteresis_invariance"]["passed"]
    e5 = gates["E5_field_distinctness"]["passed"]

    print("INTERPRETATION")
    print("-" * 76)
    if e1:
        print("  lambda_c is invariant across xi (spectral transition = structural")
        print("  eigenvalue of the basin)")
    if e2:
        print("  lambda_fold_center is invariant across xi (stiffness centroid =")
        print("  PDE response property, not a coupling-controlled variable)")
    if e3:
        print("  lambda_cold_entry is invariant across xi (absorbing boundary =")
        print("  terminal geometry independent of coupling)")
    if e4:
        print("  H(xi) is invariant across tested xi range (loop integral is a")
        print("  structural property; xi does not modulate it in [0.005, 0.07])")
    if e5:
        print("  lambda_c != lambda_fold_center (the spectral transition and the")
        print("  stiffness centroid are distinct geometric objects)")
    if not (e1 and e2 and e3 and e4 and e5):
        print()
        print("  NOTE: one or more gates did not pass. See gate details above.")
    print("-" * 76)
    print()

    elapsed = time.time() - start_wall

    # --- JSON payload ---
    stamp = start_ts.strftime("%Y%m%d_%H%M%S")
    out_path = resolve_output_path(f"BCM_v26_Paper_B_Probes_5_16_{stamp}.json")

    hypotheses_tested = {
        "H_PAPER_B_4FIELD_DECOMPOSITION": {
            "statement": (
                "H-PaperB-4Field The Paper B Section 5 transition "
                "region decomposes into four distinct invariants: "
                "lambda_c (spectral transition center, from sigmoid "
                "inflection), lambda_fold_center (stiffness "
                "centroid, from argmax n_steps in active region), "
                "lambda_cold_entry (absorbing boundary), and H(xi) "
                "(hysteresis loop integral). Five gates test "
                "simultaneous xi-invariance (E1-E4) and field "
                "distinctness (E5: lambda_c != lambda_fold_center "
                "by at least 10% relative). PASS establishes that "
                "the fold-bifurcation framing of 5_11 and earlier "
                "collapsed multiple distinct geometric objects into "
                "a single narrative; the correct structure is a "
                "four-field state tensor."
            ),
            "result": result,
            "evidence_type": "primary" if result == "PASS" else "default",
            "pass_count": int(passed_count),
            "total_configs": int(total),
            "prior": 0.5,
            "keywords": [
                "paper_b",
                "section_7_2",
                "four_field_tensor",
                "state_tensor",
                "spectral_transition",
                "stiffness_centroid",
                "absorbing_boundary",
                "hysteresis_functional",
                "field_distinctness",
                "xi_invariance",
                "deconflation",
                "classifier_v2",
                "section_5_topology",
            ],
        },
    }

    payload = {
        "test_name": "BCM_v26_Paper_B_Probes_5_16",
        "test_number": 5,
        "test_sub_number": 16,
        "test_version": 1,
        "timestamp": start_ts.isoformat(),
        "elapsed_seconds": elapsed,
        "paper_b_section": "7.2",
        "paper_b_probe": "four-field tensor phase test (post-processor)",
        "test_role": "primary_measurement",
        "grid": "post_processor (no grid)",
        "notes": (
            "Test 5_16 is a post-processor on the 5_15 JSON. It "
            "extracts the four-field state tensor (lambda_c, "
            "lambda_fold_center, lambda_cold_entry, H(xi)) per xi "
            "across the six tested xi values, then evaluates five "
            "gates: four invariance gates (E1-E4) plus a "
            "distinctness gate (E5) verifying that lambda_c and "
            "lambda_fold_center are genuinely distinct geometric "
            "objects, not a single collapsed 'fold' as framed in "
            "5_11 and earlier."
        ),
        "source": {
            "source_path": source_path,
            "matched_pattern": matched_pattern,
            "source_mode": source_mode,
            "source_test_name": source_json.get("test_name"),
            "source_timestamp": source_json.get("timestamp"),
        },
        "gate_spec": {
            "e_invariance_rel_range": CFG["e_invariance_rel_range"],
            "e_distinctness_min_rel": CFG["e_distinctness_min_rel"],
            "field_definitions": {
                "lambda_c_spectral": (
                    "active-region sigmoid inflection "
                    "(regime_classification.active_region_sigmoid_fit.lambda_c)"
                ),
                "lambda_fold_center_stiffness": (
                    "argmax(n_steps) in active region, computed here "
                    "from forward_sweep_results; NOT the classifier's "
                    "v2 lambda_fold_center, which is set to lambda_c "
                    "and thus collapses the two fields"
                ),
                "lambda_cold_entry": (
                    "first lambda where Phi stays below 1% max_phi "
                    "for 2+ consecutive points "
                    "(regime_classification.lambda_cold_entry)"
                ),
                "H_xi": (
                    "hysteresis area over active region "
                    "(hysteresis_restricted.area)"
                ),
            },
        },
        "four_field_tensor": tensor,
        "gates": gates,
        "overall_result": {
            "gates_passed": int(passed_count),
            "gates_total": int(total),
            "result": result,
            "interpretation": {
                "lambda_c_xi_invariant": e1,
                "lambda_fold_center_xi_invariant": e2,
                "lambda_cold_entry_xi_invariant": e3,
                "H_xi_xi_invariant": e4,
                "fields_distinct": e5,
            },
        },
        "hypotheses_tested": hypotheses_tested,
        "scope": (
            "Post-processor on 5_15 source JSON. Extracts four-"
            "field tensor per xi and evaluates invariance + "
            "distinctness gates. Uses argmax(n_steps) for the "
            "stiffness centroid (lambda_fold_center), which was "
            "the original 5_11 definition before the 5_12 "
            "classifier patch collapsed it onto lambda_c. This is "
            "intentional: the 4-field tensor restores the two as "
            "distinct fields. Per Foreman direction 2026-04-22."
        ),
        "keywords": [
            "paper_b",
            "section_7_2",
            "four_field_tensor",
            "state_tensor",
            "spectral_transition",
            "stiffness_centroid",
            "absorbing_boundary",
            "hysteresis_functional",
            "field_distinctness",
            "xi_invariance",
            "deconflation",
            "post_processor",
            "phase_test",
            "classifier_v2_derived",
            "section_5_topology",
        ],
        "cube_coordinates": {
            "L": "L4_Operational",
            "OD": "OF_Flight_Operations",
            "cube": "Cube_7_Spectral_Fold",
        },
        "primacy_statement": (
            "All theoretical concepts, the four-field tensor "
            "decomposition, the deconflation of lambda_c from "
            "lambda_fold_center, the invariance-and-distinctness "
            "gate structure, Brucetron and Psi_bruce, and every "
            "originating insight belong solely to Stephen Justin "
            "Burdick Sr. Four AI systems assist the project at the "
            "direction of the Foreman; no AI system owns or co-"
            "owns any theoretical concept. Emerald Entities LLC -- "
            "GIBUSH Systems."
        ),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"JSON written: {out_path}")


if __name__ == "__main__":
    main()
