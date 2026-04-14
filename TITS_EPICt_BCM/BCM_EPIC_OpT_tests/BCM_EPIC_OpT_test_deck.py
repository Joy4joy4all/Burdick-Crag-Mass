# -*- coding: utf-8 -*-
"""
BCM Sparks Test Deck Builder
==============================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
GIBUSH Systems — EPIC_OpT

Scans all JSON results in data/results/ and builds
the foundation test deck for the Bayesian engine.

Each test run = one interview with the substrate.
The deck maps every run to:
  - Q-Cube coordinates (process layer, component, stack)
  - Substrate impacts (maintenance costs affected)
  - Hypothesis evidence (which priors get updated)
  - Synergy score (confidence metric)

This is the Sparks baseline. Fusion validation happens
when new tests run and update the posteriors.

Usage:
    python BCM_sparks_test_deck.py
    python BCM_sparks_test_deck.py --results-dir data/results

Output: BCM_sparks_test_deck.json
"""

import json
import os
import sys
import time
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════
# Q-CUBE MAPPING — Test Type → Process Layer
# ═══════════════════════════════════════
# L1 = SMBH Pump, L2 = Substrate Field,
# L3 = Boundary/Torus, L4 = Dimensional Gate,
# L5 = Crew Safety, L6 = Navigation

def classify_test(filename):
    """Map a result filename to Q-Cube coordinates and
    test metadata."""
    fn = filename.lower()

    # ── Version detection ──
    version = "v0"
    vm = re.search(r'v(\d+)', fn)
    if vm:
        version = f"v{vm.group(1)}"
    elif "batch_" in fn:
        version = "v1-v6"
    elif "chi2" in fn:
        version = "v22"

    # ── Q-Cube Layer ──
    if any(k in fn for k in ["chi2", "batch_", "ngc", "ugc",
                              "ddo", "ic2574", "mond"]):
        q_layer = "L1"  # SMBH Pump / Galactic
        q_object = "OA"  # Galactic rotation
        category = "galactic"
    elif any(k in fn for k in ["neutrino", "flux"]):
        q_layer = "L1"
        q_object = "OB"  # Neutrino budget
        category = "neutrino"
    elif any(k in fn for k in ["stellar", "binary", "spica",
                                "hr_1099", "alpha_cen",
                                "phaselock", "cavitation",
                                "colonization", "tunnel_"]):
        q_layer = "L2"  # Substrate Field
        q_object = "OC"  # Binary/stellar dynamics
        category = "stellar"
    elif any(k in fn for k in ["planetary", "earth", "jupiter",
                                "saturn", "mercury", "neptune",
                                "uranus"]):
        q_layer = "L2"
        q_object = "OD"  # Planetary
        category = "planetary"
    elif any(k in fn for k in ["arrival", "sweep", "boundary",
                                "gate_transit"]):
        q_layer = "L3"  # Boundary/Torus
        q_object = "OE"  # Arrival/boundary
        category = "arrival"
    elif any(k in fn for k in ["reverse", "coherence_gate"]):
        q_layer = "L4"  # Dimensional Gate
        q_object = "OF"  # Gate check
        category = "gate"
    elif any(k in fn for k in ["brucetron", "chi_freeboard",
                                "frequency", "geometry",
                                "phase_shear", "coherence_collapse",
                                "frastrate", "sensory"]):
        q_layer = "L5"  # Crew Safety
        q_object = "OG"  # Safety diagnostics
        category = "crew_safety"
    elif any(k in fn for k in ["drift", "flight", "navigator",
                                "corridor", "graveyard",
                                "bootes", "wake", "reactor",
                                "live_substrate", "external_frame",
                                "harpoon", "probe", "tunnel_probe",
                                "bom"]):
        q_layer = "L6"  # Navigation
        q_object = "OH"  # Transit/nav
        category = "navigation"
    elif any(k in fn for k in ["blackhole", "bh_", "stellar_gate",
                                "stellar_transit"]):
        q_layer = "L4"
        q_object = "OI"  # BH/stellar transit
        category = "transit"
    elif any(k in fn for k in ["inspiral", "gw150914"]):
        q_layer = "L2"
        q_object = "OJ"  # Merger dynamics
        category = "merger"
    elif any(k in fn for k in ["lambda_drive", "dual_pump",
                                "propulsion", "ghost_packet",
                                "spine", "rigid_body",
                                "pure_gradient", "saddle",
                                "alignment", "phase_lag",
                                "energy_audit", "freeze",
                                "funded_corridors", "galactic_current",
                                "self_funded", "sirius"]):
        q_layer = "L6"
        q_object = "OK"  # Drive/propulsion
        category = "propulsion"
    else:
        q_layer = "L2"
        q_object = "OX"  # Unclassified
        category = "other"

    # ── Q-Stack (hypothesis relevance) ──
    q_stack = []
    if "chi2" in fn:
        q_stack.extend(["H1_kappa", "H3_classes"])
    if "neutrino" in fn or "flux" in fn:
        q_stack.extend(["H2_tully_fisher", "H5_eddington"])
    if "arrival" in fn or "gate" in fn or "reverse" in fn:
        q_stack.append("H4_boundary")
    if "brucetron" in fn or "chi_" in fn or "guardian" in fn:
        q_stack.append("H4_boundary")
    if not q_stack:
        q_stack.append("H3_classes")

    return {
        "version": version,
        "q_layer": q_layer,
        "q_object": q_object,
        "q_stack": q_stack,
        "category": category,
    }


def extract_metrics(data, filename):
    """Extract key substrate metrics from a JSON result."""
    metrics = {}
    fn = filename.lower()

    # ── Chi-squared engine results ──
    if "chi2" in fn and "galaxies" in data:
        s = data.get("summary", {})
        metrics["n_galaxies"] = data.get("n_galaxies", 0)
        metrics["bcm_wins"] = s.get("winners", {}).get("BCM", 0)
        metrics["nfw_wins"] = s.get("winners", {}).get("NFW", 0)
        metrics["avg_chi2_bcm"] = s.get("avg_chi2_bcm", 0)
        metrics["avg_chi2_nfw"] = s.get("avg_chi2_nfw", 0)
        metrics["grid"] = data.get("config", {}).get("grid", 0)

    # ── Neutrino flux results ──
    elif "neutrino" in fn and "galaxies" in data:
        s = data.get("summary", {})
        metrics["n_galaxies"] = data.get("n_galaxies", 0)
        metrics["L_nu_mean"] = s.get("L_nu_mean", 0)
        metrics["detect_icecube"] = s.get("detect_icecube_tev", 0)
        metrics["nu_b_mean"] = s.get("nu_b_massive_mean", 0)
        metrics["nu_b_cv"] = s.get("nu_b_massive_cv_pct", 0)

    # ── Reverse engine results ──
    elif "reverse" in fn and "destinations" in data:
        s = data.get("summary", {})
        metrics["n_destinations"] = data.get("n_destinations", 0)
        metrics["GO"] = s.get("GO", 0)
        metrics["NO_GO"] = s.get("NO-GO", 0)
        metrics["R_9to10_mean"] = s.get("R_9to10_mean", 0)

    # ── Batch galactic runs ──
    elif "batch_" in fn and isinstance(data, list):
        metrics["n_galaxies"] = len(data)
        if data:
            metrics["sample_galaxy"] = data[0].get("galaxy", "")

    # ── Single galaxy results ──
    elif "galaxy" in data:
        metrics["galaxy"] = data.get("galaxy", "")
        for k in ["corr_full", "corr_inner", "rms_substrate",
                   "winner", "cos_delta_phi"]:
            if k in data:
                metrics[k] = data[k]

    # ── Gate transit results ──
    elif "flight_log" in data:
        log = data["flight_log"]
        metrics["n_steps"] = len(log)
        if log:
            metrics["min_R_7D"] = min(
                e.get("R_7D", 1) for e in log)
            metrics["min_coherence"] = min(
                e.get("Coherence", 1) for e in log)
            metrics["verdict"] = data.get("verdict", "")

    # ── Generic: grab config if present ──
    if "config" in data and isinstance(data["config"], dict):
        cfg = data["config"]
        for k in ["grid", "lam", "layers"]:
            if k in cfg:
                metrics[f"config_{k}"] = cfg[k]

    return metrics


def extract_substrate_impacts(data, filename, metrics):
    """Map test results to substrate maintenance impacts,
    same structure as equipment_impacts in I-Corps deck."""
    impacts = []
    fn = filename.lower()

    if "chi2" in fn and "avg_chi2_bcm" in metrics:
        impacts.append({
            "component": "Substrate Field (sigma)",
            "metric": metrics.get("avg_chi2_bcm", 0),
            "metric_name": "avg_chi2_bcm",
            "notes": (f"BCM wins {metrics.get('bcm_wins',0)}/"
                      f"{metrics.get('n_galaxies',0)} at grid="
                      f"{metrics.get('grid',0)}"),
            "impact_type": "validation"
        })

    if "neutrino" in fn and "L_nu_mean" in metrics:
        impacts.append({
            "component": "SMBH Pump (L_nu)",
            "metric": metrics.get("L_nu_mean", 0),
            "metric_name": "L_nu_mean_erg_s",
            "notes": (f"Detectable by IceCube: "
                      f"{metrics.get('detect_icecube',0)}/"
                      f"{metrics.get('n_galaxies',0)}"),
            "impact_type": "prediction"
        })
        impacts.append({
            "component": "Burdick Constant (nu_b)",
            "metric": metrics.get("nu_b_mean", 0),
            "metric_name": "nu_b_massive_mean",
            "notes": f"CV = {metrics.get('nu_b_cv',0):.1f}%",
            "impact_type": "measurement"
        })

    if "reverse" in fn and "GO" in metrics:
        impacts.append({
            "component": "9D-to-10D Gate (R_9to10)",
            "metric": metrics.get("R_9to10_mean", 0),
            "metric_name": "R_9to10_mean",
            "notes": (f"GO: {metrics.get('GO',0)} / "
                      f"NO-GO: {metrics.get('NO_GO',0)}"),
            "impact_type": "gate_check"
        })

    if "arrival" in fn or "gate_transit" in fn:
        if "verdict" in metrics:
            impacts.append({
                "component": "Boundary Layer (K_BOUNDARY)",
                "metric": 150.0,
                "metric_name": "K_BOUNDARY",
                "notes": f"Verdict: {metrics.get('verdict','')}",
                "impact_type": "transit_check"
            })

    return impacts


# ═══════════════════════════════════════
# BUILD THE DECK
# ═══════════════════════════════════════

def build_deck(results_dir):
    """Scan all JSON results and build the foundation deck."""
    results_path = Path(results_dir)
    if not results_path.exists():
        print(f"  ERROR: {results_dir} not found")
        return []

    json_files = sorted(results_path.glob("*.json"))
    print(f"  Found {len(json_files)} JSON files in {results_dir}")

    deck = []
    test_num = 0

    for jf in json_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  SKIP {jf.name}: {e}")
            continue

        test_num += 1
        fn = jf.name

        # Extract timestamp from filename
        tm = re.search(r'(\d{8})_?(\d{6})?', fn)
        if tm:
            date_str = tm.group(1)
            time_str = tm.group(2) or "000000"
            try:
                dt = datetime.strptime(
                    f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                date_display = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                date_display = date_str
        else:
            date_display = "unknown"

        # Classify
        qcube = classify_test(fn)

        # Extract metrics
        metrics = extract_metrics(data, fn)

        # Extract impacts
        impacts = extract_substrate_impacts(data, fn, metrics)

        # Build results summary
        results_text = ""
        for k, v in metrics.items():
            if isinstance(v, float):
                results_text += f"{k}={v:.4g}  "
            else:
                results_text += f"{k}={v}  "

        # Synergy score: higher for more significant results
        synergy = 0.3  # base
        if metrics.get("bcm_wins", 0) > 10:
            synergy = 0.9
        elif metrics.get("GO", 0) > 20:
            synergy = 0.8
        elif metrics.get("detect_icecube", 0) > 20:
            synergy = 0.85
        elif "verdict" in metrics:
            synergy = 0.7 if "STARGATE" in str(
                metrics.get("verdict", "")) else 0.4
        elif impacts:
            synergy = 0.5

        entry = {
            "test_num": test_num,
            "date": date_display,
            "script": fn.replace(".json", ".py"),
            "source_json": fn,
            "version": qcube["version"],
            "category": qcube["category"],
            "test_type": qcube["category"].replace("_", " ").title(),
            "q_layer": qcube["q_layer"],
            "q_object": qcube["q_object"],
            "q_stack": qcube["q_stack"],
            "results": results_text.strip(),
            "substrate_impacts": impacts,
            "metrics": metrics,
            "synergy_score": synergy,
        }

        deck.append(entry)

    return deck


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="BCM Sparks Test Deck Builder")
    parser.add_argument("--results-dir", type=str,
        default=os.path.join(SCRIPT_DIR, "data", "results"),
        help="Path to results directory")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 55)
    print("  BCM SPARKS TEST DECK BUILDER")
    print("  Stephen Justin Burdick Sr.")
    print("  Emerald Entities LLC — GIBUSH Systems")
    print("=" * 55)
    print(f"\n  Results dir: {args.results_dir}")

    t0 = time.time()
    deck = build_deck(args.results_dir)
    elapsed = time.time() - t0

    print(f"\n  Built {len(deck)} test entries in {elapsed:.1f}s")

    # Summary by category
    cats = {}
    for e in deck:
        c = e["category"]
        cats[c] = cats.get(c, 0) + 1

    print(f"\n  BY CATEGORY:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {c:<20} {n:>4}")

    # Summary by version
    vers = {}
    for e in deck:
        v = e["version"]
        vers[v] = vers.get(v, 0) + 1

    print(f"\n  BY VERSION:")
    for v, n in sorted(vers.items()):
        print(f"    {v:<10} {n:>4}")

    # Summary by Q-Layer
    layers = {}
    for e in deck:
        l = e["q_layer"]
        layers[l] = layers.get(l, 0) + 1

    print(f"\n  BY Q-CUBE LAYER:")
    for l, n in sorted(layers.items()):
        print(f"    {l:<10} {n:>4}")

    # High synergy entries
    high = [e for e in deck if e["synergy_score"] >= 0.7]
    print(f"\n  HIGH SYNERGY (>= 0.7): {len(high)}")
    for e in sorted(high, key=lambda x: -x["synergy_score"])[:10]:
        print(f"    [{e['version']}] {e['source_json'][:40]}"
              f"  syn={e['synergy_score']:.1f}")

    # Save
    out_path = args.output
    if out_path is None:
        out_dir = os.path.join(SCRIPT_DIR, "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir,
            "BCM_sparks_test_deck.json")

    output = {
        "deck_name": "BCM_SPARKS_TEST_DECK",
        "version": "v23.0",
        "author": "Stephen Justin Burdick Sr.",
        "entity": "Emerald Entities LLC — GIBUSH Systems",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_tests": len(deck),
        "categories": cats,
        "versions": vers,
        "q_layers": layers,
        "tests": deck,
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved: {out_path}")
    print(f"\n  Foundation deck ready.")
    print(f"  {len(deck)} substrate interviews cataloged.")
    print(f"  Bayesian engine has its baseline.")
