# -*- coding: utf-8 -*-
"""
BCM v27 -- Paper B Consolidation

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Stephen Justin Burdick Sr.

PURPOSE
=======
Aggregate the v23-v27 evidence chain for the five Anchor Equation
sub-hypotheses into a single consolidated JSON document. The output
is the read-and-aggregate companion artifact for Paper B v2:
each sub-hypothesis's evidence trail becomes a structured record
showing source files, evidence directions, evidence types, and
cumulative posterior progression toward VALIDATED status.

This is NOT a measurement test. It does not perturb the corpus, run
new solver iterations, or emit hypotheses for the cube to ingest.
It produces a publication artifact.

Five sub-hypotheses tracked:
  H_PAPER_B_1_PHI_SIGMOID
  H_PAPER_B_2_J_VORTICITY
  H_PAPER_B_3_LOOP_CONVERGES
  H_PAPER_B_4_RECOVERY_LIMIT
  H_PAPER_B_5_M_SIGMA_INVERSION

For each sub-hypothesis, the consolidator finds every JSON in the
corpus where the sub-hypothesis ID appears in any hypotheses_tested
block, extracts the evidence direction (PASS/FAIL/INCONCLUSIVE) and
evidence_type, and produces an ordered evidence trail. The parent
H_PAPER_B_ANCHOR_EQUATION posterior is computed as the geometric
mean of component posteriors, matching the cube engine's
ALL_GATES_OPEN gating semantics.

PIPELINE
========
    For each JSON in data/results/ + data/paper_results/:
        1. Load top-level dict (or list-wrapped fallback)
        2. Scan all hypotheses_tested blocks (top-level and nested)
        3. For each of the five tracked sub-hypothesis IDs found:
             - Extract result, evidence_type, timestamp, source path
             - Append to that sub-hypothesis's evidence trail
    For each sub-hypothesis:
        4. Compute Bayesian posterior from accumulated evidence
        5. Determine status (NEEDS_MORE_DATA / VALIDATED / INVALIDATED)
        6. Build per-component summary
    For the compositional parent:
        7. Geometric-mean over component posteriors
        8. Apply ALL_GATES_OPEN gating
    Emit consolidated JSON to data/paper_results/.

DOES NOT TOUCH
==============
- core solver
- launcher
- hypothesis_engine.py
- bcm_tensor_hypothesis.py
- measurement_engine.py
- vocabulary registry
- any engine state

PRIMACY STATEMENT: All theoretical concepts -- the Anchor Equation,
the five-sub-hypothesis decomposition, the cube-evidence
compositional validation methodology, the gating-policy framework,
the per-symbol weight policy, and every originating insight --
belong solely to Stephen Justin Burdick Sr. AI systems were used
strictly as computational processing tools at the direction of SJB.
No AI system contributed theoretical concepts. Emerald Entities LLC
-- GIBUSH Systems.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================================
# CONSTANTS
# ============================================================================

# Anchor Equation sub-hypothesis IDs
SUB_HYPOTHESIS_IDS = (
    "H_PAPER_B_1_PHI_SIGMOID",
    "H_PAPER_B_2_J_VORTICITY",
    "H_PAPER_B_3_LOOP_CONVERGES",
    "H_PAPER_B_4_RECOVERY_LIMIT",
    "H_PAPER_B_5_M_SIGMA_INVERSION",
)

# Compositional parent
PARENT_HYPOTHESIS_ID = "H_PAPER_B_ANCHOR_EQUATION"

# Component labels for human-readable output
COMPONENT_LABELS = {
    "H_PAPER_B_1_PHI_SIGMOID":       "Phi-sigmoid form fits substrate response",
    "H_PAPER_B_2_J_VORTICITY":       "J carries vorticity in dual-pump topology",
    "H_PAPER_B_3_LOOP_CONVERGES":    "Aleph-Null loop integral converges",
    "H_PAPER_B_4_RECOVERY_LIMIT":    "Recovery limit (Phi -> 1, J -> 0) holds",
    "H_PAPER_B_5_M_SIGMA_INVERSION": "M-sigma inversion mapping is continuous",
}

# Component is GATE if recovery-limit (matches tensor parent definition)
GATE_COMPONENTS = {"H_PAPER_B_4_RECOVERY_LIMIT"}

# Bayesian validation thresholds (match hypothesis_engine.py)
VALIDATION_THRESHOLD = 0.80
INVALIDATION_THRESHOLD = 0.20
MIN_EVIDENCE_FOR_DECISION = 3

# Evidence-type strength table (matches EVIDENCE_STRENGTH_RULES in
# hypothesis_engine.py at v26 close + v26 derived_measurement addition,
# plus v26 probe-corpus evidence_type strings: primary, secondary,
# secondary_corroboration)
EVIDENCE_STRENGTH_RULES = {
    "explicit_validate":      0.50,
    "primary":                0.50,
    "cost_direct":            0.45,
    "explicit_contradict":    0.45,
    "equipment_damage":       0.40,
    "pain_severe":            0.35,
    "secondary":              0.30,
    "secondary_corroboration": 0.20,
    "pain_moderate":          0.20,
    "sentiment_positive":     0.15,
    "sentiment_negative":     0.15,
    "derived_measurement":    0.12,
    "default":                0.10,
    "equipment_mention":      0.10,
}

# Beta-Binomial conjugate prior (uniform, matches engine defaults)
PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0


# ============================================================================
# JSON LOADING
# ============================================================================

def _safe_dict(data: Any) -> Optional[Dict[str, Any]]:
    """Normalize loaded JSON to a dict. Top-level lists wrap into a
    synthetic dict with the list as 'sweep_results'."""
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"sweep_results": data}
    return None


def _load_json_safely(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return _safe_dict(data)


# ============================================================================
# HYPOTHESIS BLOCK EXTRACTION
# ============================================================================

def _scan_hypothesis_blocks(node: Any,
                             out: List[Tuple[Dict[str, Any], List[str]]],
                             path: Optional[List[str]] = None) -> None:
    """
    Recursively walk the JSON structure looking for any 'hypotheses_tested'
    block. Each find is appended to `out` as (block_dict, location_path).
    Both dict-of-dicts and list-of-dicts shapes are supported.
    """
    if path is None:
        path = []
    if isinstance(node, dict):
        ht = node.get("hypotheses_tested")
        if ht is not None:
            normalized = _normalize_block(ht)
            if normalized:
                out.append((normalized, list(path)))
        for k, v in node.items():
            if k == "hypotheses_tested":
                continue  # already handled above
            _scan_hypothesis_blocks(v, out, path + [k])
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_hypothesis_blocks(item, out, path + [f"[{i}]"])


def _normalize_block(ht: Any) -> Dict[str, Dict[str, Any]]:
    """
    Normalize a hypotheses_tested block to dict[hyp_id -> details].
    Accepts both dict-keyed-by-id and list-of-dicts-with-id formats.
    """
    if isinstance(ht, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for hid, decl in ht.items():
            if isinstance(decl, dict):
                out[str(hid)] = decl
        return out
    if isinstance(ht, list):
        out = {}
        for item in ht:
            if not isinstance(item, dict):
                continue
            hid = item.get("id") or item.get("hypothesis_id")
            if hid:
                out[str(hid)] = item
        return out
    return {}


# ============================================================================
# EVIDENCE EVENT EXTRACTION
# ============================================================================

class EvidenceEvent:
    """One evidence event extracted from a JSON's hypotheses_tested block."""

    __slots__ = (
        "hypothesis_id", "result", "direction", "evidence_type",
        "base_strength", "source_file", "source_path",
        "test_name", "timestamp", "description",
    )

    def __init__(self) -> None:
        self.hypothesis_id: str = ""
        self.result: str = ""
        self.direction: int = 0
        self.evidence_type: str = "default"
        self.base_strength: float = EVIDENCE_STRENGTH_RULES["default"]
        self.source_file: str = ""
        self.source_path: List[str] = []
        self.test_name: str = ""
        self.timestamp: str = ""
        self.description: str = ""


def _result_to_direction(result: Any) -> int:
    """Map result string to evidence direction. PASS -> +1, FAIL -> -1,
    INCONCLUSIVE / unknown -> 0."""
    if not result:
        return 0
    rs = str(result).upper()
    if rs in ("PASS", "PASS_TARGETED", "VALIDATED", "TRUE"):
        return 1
    if rs in ("FAIL", "FAIL_TARGETED", "INVALIDATED", "FALSE"):
        return -1
    return 0


def extract_events(json_path: str,
                    data: Dict[str, Any]) -> List[EvidenceEvent]:
    """
    Walk the JSON, find every hypotheses_tested block, extract one
    evidence event per tracked sub-hypothesis ID found.
    """
    events: List[EvidenceEvent] = []
    blocks: List[Tuple[Dict[str, Any], List[str]]] = []
    _scan_hypothesis_blocks(data, blocks)

    test_name = str(data.get("test_name") or data.get("test")
                    or os.path.basename(json_path))
    timestamp = str(data.get("timestamp") or data.get("time")
                    or "")

    for block, location in blocks:
        for tracked_id in SUB_HYPOTHESIS_IDS:
            if tracked_id not in block:
                continue
            decl = block[tracked_id]
            if not isinstance(decl, dict):
                continue

            ev = EvidenceEvent()
            ev.hypothesis_id = tracked_id
            ev.result = str(decl.get("result", ""))
            ev.direction = _result_to_direction(decl.get("result"))
            etype = str(decl.get("evidence_type", "default"))
            ev.evidence_type = etype
            ev.base_strength = EVIDENCE_STRENGTH_RULES.get(
                etype, EVIDENCE_STRENGTH_RULES["default"])
            ev.source_file = os.path.basename(json_path)
            ev.source_path = location
            ev.test_name = test_name
            ev.timestamp = timestamp
            ev.description = str(decl.get("description", ""))[:280]
            events.append(ev)

    return events


# ============================================================================
# BAYESIAN POSTERIOR
# ============================================================================

def _accumulate_posterior(events: List[EvidenceEvent]
                          ) -> Tuple[float, int, int]:
    """
    Beta-Binomial conjugate update over the events for one
    sub-hypothesis. Returns (posterior, n_supports, n_contradicts).

    Each support event adds base_strength to alpha; each contradict
    event adds base_strength to beta. Inconclusive events do not
    update the posterior. Posterior = alpha / (alpha + beta).
    """
    alpha = PRIOR_ALPHA
    beta = PRIOR_BETA
    n_supports = 0
    n_contradicts = 0

    for ev in events:
        if ev.direction > 0:
            alpha += ev.base_strength
            n_supports += 1
        elif ev.direction < 0:
            beta += ev.base_strength
            n_contradicts += 1

    posterior = alpha / (alpha + beta + 1e-18)
    return posterior, n_supports, n_contradicts


def _classify_status(posterior: float, n_evidence: int) -> str:
    if n_evidence < MIN_EVIDENCE_FOR_DECISION:
        return "NEEDS_MORE_DATA"
    if posterior >= VALIDATION_THRESHOLD:
        return "VALIDATED"
    if posterior <= INVALIDATION_THRESHOLD:
        return "INVALIDATED"
    return "NEEDS_MORE_DATA"


# ============================================================================
# CONSOLIDATION
# ============================================================================

def consolidate_component(hypothesis_id: str,
                          events: List[EvidenceEvent]) -> Dict[str, Any]:
    """Build the consolidated record for one sub-hypothesis."""
    # Sort events by source_file (timestamp not always present)
    sorted_events = sorted(events, key=lambda e: (e.timestamp, e.source_file))

    posterior, n_supports, n_contradicts = _accumulate_posterior(sorted_events)
    n_evidence = n_supports + n_contradicts
    status = _classify_status(posterior, n_evidence)

    # Build per-event audit trail (compact)
    trail = []
    for ev in sorted_events:
        trail.append({
            "source_file":   ev.source_file,
            "source_path":   "/".join(ev.source_path) if ev.source_path else "(root)",
            "test_name":     ev.test_name,
            "timestamp":     ev.timestamp,
            "result":        ev.result,
            "direction":     ev.direction,
            "evidence_type": ev.evidence_type,
            "base_strength": ev.base_strength,
            "description":   ev.description,
        })

    # Distinct source files contributing
    distinct_sources = sorted({e.source_file for e in sorted_events})

    # Distinct evidence types used
    type_histogram: Dict[str, int] = {}
    for e in sorted_events:
        type_histogram[e.evidence_type] = type_histogram.get(
            e.evidence_type, 0) + 1

    return {
        "hypothesis_id":         hypothesis_id,
        "label":                 COMPONENT_LABELS.get(hypothesis_id, ""),
        "is_gate":               hypothesis_id in GATE_COMPONENTS,
        "status":                status,
        "posterior":             posterior,
        "n_evidence_total":      n_evidence,
        "n_supports":            n_supports,
        "n_contradicts":         n_contradicts,
        "n_distinct_sources":    len(distinct_sources),
        "evidence_type_histogram": type_histogram,
        "distinct_source_files": distinct_sources,
        "evidence_trail":        trail,
    }


def consolidate_parent(component_records: Dict[str, Dict[str, Any]]
                       ) -> Dict[str, Any]:
    """Build the parent compositional record using ALL_GATES_OPEN gating
    and geometric-mean posterior."""
    posteriors = [rec["posterior"]
                  for rec in component_records.values()]
    statuses = [rec["status"]
                for rec in component_records.values()]
    gate_components = [hid for hid, rec in component_records.items()
                       if rec["is_gate"]]

    # Geometric mean posterior
    if posteriors:
        log_sum = sum(math.log(max(p, 1e-12)) for p in posteriors)
        geom_mean = math.exp(log_sum / len(posteriors))
    else:
        geom_mean = 0.0

    # ALL_GATES_OPEN: parent VALIDATED only if every component VALIDATED
    if all(s == "VALIDATED" for s in statuses):
        parent_status = "VALIDATED"
        gating_state = "ALL_GATES_OPEN"
    elif any(s == "INVALIDATED" for s in statuses):
        parent_status = "INVALIDATED"
        gating_state = "GATE_CLOSED"
    else:
        parent_status = "NEEDS_MORE_DATA"
        gating_state = "GATES_PENDING"

    # If a GATE component is not VALIDATED, parent cannot be VALIDATED
    # regardless of others (matches tensor parent semantics)
    for gate_id in gate_components:
        if component_records[gate_id]["status"] != "VALIDATED":
            parent_status = "NEEDS_MORE_DATA"
            gating_state = "GATE_PENDING"
            break

    return {
        "hypothesis_id":      PARENT_HYPOTHESIS_ID,
        "label":              "Anchor Equation Composition",
        "parent_status":      parent_status,
        "gating_policy":      "ALL_GATES_OPEN",
        "gating_state":       gating_state,
        "posterior_geometric_mean": geom_mean,
        "component_count":    len(component_records),
        "component_summary": {
            hid: {
                "status":           rec["status"],
                "posterior":        rec["posterior"],
                "n_evidence_total": rec["n_evidence_total"],
                "is_gate":          rec["is_gate"],
            }
            for hid, rec in component_records.items()
        },
    }


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    print("=" * 72)
    print("BCM v27 -- PAPER B CONSOLIDATION")
    print("Aggregating Anchor Equation evidence chain across v23-v27")
    print("Stephen Justin Burdick Sr. -- Emerald Entities LLC")
    print("=" * 72)

    t_start = time.time()

    test_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(test_dir))
    results_dir = os.path.join(repo_root, "data", "results")
    paper_dir = os.path.join(repo_root, "data", "paper_results")

    candidates: List[str] = []
    for d in (results_dir, paper_dir):
        if os.path.isdir(d):
            for fname in sorted(os.listdir(d)):
                if fname.endswith(".json") and not fname.startswith("_"):
                    candidates.append(os.path.join(d, fname))

    print(f"  Found {len(candidates)} candidate JSON file(s)")
    print(f"  results_dir : {results_dir}")
    print(f"  paper_dir   : {paper_dir}")

    # Bucket events by hypothesis ID
    events_by_id: Dict[str, List[EvidenceEvent]] = {
        hid: [] for hid in SUB_HYPOTHESIS_IDS}
    files_with_evidence = 0
    files_scanned = 0

    for path in candidates:
        data = _load_json_safely(path)
        if data is None:
            continue
        files_scanned += 1
        events = extract_events(path, data)
        if events:
            files_with_evidence += 1
            for ev in events:
                events_by_id[ev.hypothesis_id].append(ev)

    print(f"  Scanned {files_scanned} valid JSON file(s)")
    print(f"  {files_with_evidence} file(s) carried tracked sub-hypothesis "
          f"evidence")

    # Per-component consolidation
    component_records: Dict[str, Dict[str, Any]] = {}
    for hid in SUB_HYPOTHESIS_IDS:
        component_records[hid] = consolidate_component(hid, events_by_id[hid])

    # Parent consolidation
    parent_record = consolidate_parent(component_records)

    # Print human-readable summary
    print()
    print("PER-COMPONENT EVIDENCE TRAILS")
    print("-" * 72)
    for hid in SUB_HYPOTHESIS_IDS:
        rec = component_records[hid]
        gate_marker = " [GATE]" if rec["is_gate"] else ""
        print(f"  {hid}{gate_marker}")
        print(f"    label    : {rec['label']}")
        print(f"    status   : {rec['status']}")
        print(f"    posterior: {rec['posterior']:.4f}")
        print(f"    evidence : {rec['n_evidence_total']} "
              f"(supports={rec['n_supports']}, "
              f"contradicts={rec['n_contradicts']})")
        print(f"    sources  : {rec['n_distinct_sources']} distinct file(s)")
        if rec["evidence_type_histogram"]:
            hist_str = ", ".join(
                f"{k}={v}"
                for k, v in sorted(rec["evidence_type_histogram"].items()))
            print(f"    types    : {hist_str}")

    print()
    print("COMPOSITIONAL PARENT")
    print("-" * 72)
    print(f"  {PARENT_HYPOTHESIS_ID}")
    print(f"    parent_status     : {parent_record['parent_status']}")
    print(f"    gating_state      : {parent_record['gating_state']}")
    print(f"    posterior (geo)   : "
          f"{parent_record['posterior_geometric_mean']:.4f}")
    print(f"    component_count   : {parent_record['component_count']}")

    # Build consolidated output JSON
    elapsed = time.time() - t_start
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {
        "test_name": "BCM_v27_Paper_B_Consolidation",
        "test_class": ("Paper B v2 publication artifact -- "
                       "compositional evidence consolidation"),
        "version": "v27",
        "timestamp": timestamp,
        "elapsed_sec": elapsed,
        "primacy_statement": (
            "All theoretical concepts -- the Anchor Equation, the "
            "five-sub-hypothesis decomposition, the cube-evidence "
            "compositional validation methodology, the gating-policy "
            "framework -- belong solely to Stephen Justin Burdick Sr. "
            "Emerald Entities LLC -- GIBUSH Systems."),
        "scan_stats": {
            "candidates_found":        len(candidates),
            "files_scanned":           files_scanned,
            "files_with_evidence":     files_with_evidence,
        },
        "evidence_strength_table": dict(EVIDENCE_STRENGTH_RULES),
        "validation_thresholds": {
            "validation":   VALIDATION_THRESHOLD,
            "invalidation": INVALIDATION_THRESHOLD,
            "min_evidence": MIN_EVIDENCE_FOR_DECISION,
        },
        "components": component_records,
        "parent":     parent_record,
    }

    out_dir = os.path.join(repo_root, "data", "paper_results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(
        out_dir, f"BCM_v27_Paper_B_Consolidation_{timestamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print()
    print(f"  Output: {out_path}")
    print(f"  Elapsed: {elapsed:.2f}s")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
