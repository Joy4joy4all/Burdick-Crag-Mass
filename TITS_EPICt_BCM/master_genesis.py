# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - MASTER INTEGRATOR
NO HTML. PYTHON OUTPUTS ONLY.
PRODUCTION HARDENED.

Runs the full pipeline:
  Phase 1: Load tests from BCM_TESTS/test_database.json
  Phase 2: Genesis analysis (extract → graph → cognitive synthesis)
  Phase 3: 3D transformation (NMF + spectral embedding)
  Phase 4: Circumpunct convergence check
  Phase 5: Dashboard data JSON
  Phase 6: Adaptive questions for next test_run
  Phase 7: Solution synthesis from validated hypotheses
  Phase 8: Visualizations (PNG)
  Phase 9: Summary

All outputs go to GENESIS_OUTPUT/
"""

import sys
import io
import json
import math
from pathlib import Path
from datetime import datetime


# =============================================================================
# SAFE UTF-8 CONSOLE CONFIG (WINDOWS HARDENED)
# =============================================================================

def configure_utf8_console():
    """
    Preferred: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    Fallback: detach the underlying buffer and re-wrap ONCE.
    """
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name)
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
            else:
                try:
                    buf = stream.detach()
                except Exception:
                    buf = stream.buffer
                setattr(sys, stream_name,
                        io.TextIOWrapper(buf, encoding="utf-8", errors="replace",
                                         line_buffering=True))
        except Exception:
            pass


configure_utf8_console()


from genesis_brain import (
    AdaptiveTestGenerator,
    ResonanceVisualizer,
    Transformer3D,
    GenesisOrchestrator
)

# Optional: Holographic dashboard (Plotly-based)
try:
    from holographic_dashboard import HolographicDashboard
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False


# =============================================================================
# HELPERS
# =============================================================================

def safe_float(v, default=0.0) -> float:
    """Hardened float conversion: float/int/'0.83'/'83%'/None → float."""
    try:
        if v is None:
            return default
        if isinstance(v, str):
            s = v.strip()
            is_percent = "%" in s
            s = s.replace("%", "").strip()
            f = float(s)
            if is_percent and f > 1.0:
                f = f / 100.0
        else:
            f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def safe_list(v):
    """Return v as list safely, supports numpy arrays with tolist()."""
    try:
        if hasattr(v, "tolist"):
            return v.tolist()
        if isinstance(v, (list, tuple)):
            return list(v)
    except Exception:
        pass
    return [0.0, 0.0, 0.0]


# =============================================================================
# SOLUTION GENERATOR
# =============================================================================

def generate_solutions(synthesis: dict, graph_data: dict) -> dict:
    """
    Generate solution candidates from validated hypotheses and patterns.

    This is deterministic: solutions are templates filled from synthesis data.
    Each solution is ranked by the confidence of the hypotheses it addresses.
    """
    hypotheses = synthesis.get("hypotheses", {})
    patterns = synthesis.get("patterns", [])
    gaps = synthesis.get("gaps", [])
    insights = synthesis.get("insights", [])
    market = synthesis.get("market_opportunity", {})

    # Find validated hypotheses (posterior > 0.70)
    validated = []
    for key, h in hypotheses.items():
        post = safe_float(h.get("posterior", 0))
        if post > 0.70 and h.get("total_evidence_pieces", 0) >= 2:
            validated.append(h)

    # Equipment hotspot
    hotspot = ""
    for p in patterns:
        if p.get("type") == "equipment_hotspot":
            hotspot = p.get("description", "")
            break

    # Top gaps
    top_gaps = [g.get("description", "") for g in gaps[:3]]

    # Build solutions
    solutions = []

    # SOL-001: Detection solution (always generated if manual_detection validated)
    manual_hyp = hypotheses.get("manual_detection_fails", {})
    if safe_float(manual_hyp.get("posterior", 0)) > 0.60:
        sol1_score = safe_float(manual_hyp.get("posterior", 0.5))
        solutions.append({
            "solution_id": "SOL-001",
            "title": "Real-Time Contamination Early Warning + Proof Packet",
            "type": "detection + evidence + operator playbook",
            "why_now": (
                f"Manual detection validated as failing at {sol1_score:.0%} confidence. "
                f"{hotspot or 'Equipment damage pattern detected.'}"
            ),
            "rank_score": round(sol1_score * 0.9, 3),
            "requirements": [
                "Deploy sensor validation at critical entry/transfer point.",
                "Event capture with confidence gating (avoid alarm fatigue).",
                "Proof packet per event: timestamps, features, operator notes.",
                "Operator-first response playbook."
            ],
            "mvp_spec": {
                "deployment_zone": {
                    "primary": "blow line entry / transfer point",
                    "secondary": hotspot or "highest-damage equipment zone"
                },
                "nonnegotiables": [
                    "must not require daily recalibration",
                    "must not spam alarms",
                    "must log evidence for every alarm",
                    "must degrade safely (fail to monitoring-only, not spam)"
                ]
            },
            "pilot_plan": {
                "duration_days": 30,
                "success_metrics": [
                    "lead time gained vs current detection",
                    "false positives per shift < 1",
                    "operator acknowledgment rate",
                    "reduction in cascade damage"
                ]
            },
            "evidence": {
                "validated_hypotheses": [manual_hyp.get("name", "")],
                "top_patterns": [hotspot] if hotspot else [],
                "gaps": top_gaps,
            }
        })

    # SOL-002: Cost discovery (if cost_understated validated)
    cost_hyp = hypotheses.get("cost_understated", {})
    if safe_float(cost_hyp.get("posterior", 0)) > 0.60:
        sol2_score = safe_float(cost_hyp.get("posterior", 0.5))
        avg_damage = market.get("avg_annual_damage_per_source",
                                market.get("average_damage_per_mill", "unknown"))
        solutions.append({
            "solution_id": "SOL-002",
            "title": "True Cost Discovery + ROI Engine",
            "type": "economic intelligence + executive proof",
            "why_now": (
                f"Cost understated validated at {sol2_score:.0%} confidence. "
                f"Average damage per source: {avg_damage}."
            ),
            "rank_score": round(sol2_score * 0.7, 3),
            "requirements": [
                "Incident cost worksheet (10 min to fill)",
                "Standard categories: downtime, labor, cleanup, quality, repairs",
                "Auto-generate conservative/expected/worst-case ROI",
                "Tie costs to events and equipment hotspots"
            ],
            "mvp_spec": {
                "inputs": ["event timestamps", "downtime minutes", "crew hours",
                           "repair estimate", "quality loss", "production rate"],
                "outputs": ["cost_per_event", "annualized_damage", "ROI_by_zone"],
                "nonnegotiables": [
                    "fast to fill",
                    "does not require finance involvement to start",
                    "auditable assumptions"
                ]
            },
            "evidence": {
                "validated_hypotheses": [cost_hyp.get("name", "")],
                "hotspot": hotspot,
            }
        })

    # SOL-003: Test Run targeting (always generated if gaps exist)
    if gaps:
        best_gap = gaps[0]
        solutions.append({
            "solution_id": "SOL-003",
            "title": "Test Run Targeting Engine (Gap Closure)",
            "type": "discovery optimizer + convergence driver",
            "why_now": (
                f"{len(gaps)} information gaps remaining. "
                f"Top gap: {best_gap.get('description', 'unknown')}."
            ),
            "rank_score": round(safe_float(best_gap.get("priority", 0.5)) * 0.6, 3),
            "requirements": [
                "Convert gaps into role-target recommendations",
                "Generate question sets tied to uncertain hypotheses",
                "Track convergence over time (circumpunct readiness)"
            ],
            "gap_plan": {
                "recommendation": best_gap.get("description", ""),
                "expected_info_gain": safe_float(best_gap.get("expected_info_gain", 0)),
                "priority": safe_float(best_gap.get("priority", 0)),
            }
        })

    # Sort by rank
    solutions.sort(key=lambda s: s.get("rank_score", 0), reverse=True)

    return {
        "generated": datetime.now().isoformat(),
        "hotspot_hint": hotspot,
        "validated_hypotheses": validated,
        "solution_candidates": solutions,
        "gap_plan": solutions[-1].get("gap_plan", {}) if solutions else {},
        "notes": "Deterministic solution synthesis from tests/graph/synthesis."
    }


# =============================================================================
# MASTER INTEGRATOR
# =============================================================================

class MasterIntegrator:

    def __init__(self):
        self.tests = []
        self.synthesis = {}       # strategic_intelligence output
        self.graph_data = {}      # test_graph output
        self.objects_3d = []
        self.circumpunct_achieved = False

        self.test_run_dir = Path("BCM_TESTS")
        self.output_dir = Path("GENESIS_OUTPUT")
        self.viz_dir = Path("VISUALIZATIONS")

        for d in [self.test_run_dir, self.output_dir, self.viz_dir]:
            d.mkdir(exist_ok=True, parents=True)

    # -------------------------------------------------------------------------

    def run_complete_pipeline(self):
        print("=" * 80)
        print("GENESIS BRAIN - MASTER INTEGRATOR")
        print("=" * 80)
        print()

        # PHASE 1: Load
        print("PHASE 1: Loading Test Run Database")
        print("-" * 80)
        if not self._load_test_runs():
            print("ERROR: No test database found or database is empty.")
            print(f"  Expected: {self.test_run_dir / 'test_database.json'}")
            return False
        print(f"[OK] Loaded {len(self.tests)} test_runs\n")

        # PHASE 2: Genesis Analysis
        print("PHASE 2: Running Genesis Analysis")
        print("-" * 80)
        try:
            orchestrator = GenesisOrchestrator(output_dir=self.output_dir)
            self.synthesis = orchestrator.run_full_analysis(self.tests)
        except Exception as e:
            print(f"FATAL: Genesis analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Load graph data from file (orchestrator writes it)
        graph_file = self.output_dir / "test_graph.json"
        if graph_file.exists():
            with open(graph_file, "r", encoding="utf-8") as f:
                self.graph_data = json.load(f)
        print()

        # PHASE 3: 3D Transform
        print("PHASE 3: 3D Transformation")
        print("-" * 80)
        try:
            self._run_3d_transform()
        except Exception as e:
            print(f"WARNING: 3D transformation failed: {e}")
            import traceback
            traceback.print_exc()
            print("  (Continuing without 3D data)\n")

        # PHASE 4: Circumpunct
        print("PHASE 4: Circumpunct Analysis")
        print("-" * 80)
        try:
            self._analyze_circumpunct()
        except Exception as e:
            print(f"WARNING: Circumpunct analysis failed: {e}")
        print()

        # PHASE 5: Dashboard Data
        print("PHASE 5: Generating Dashboard Data")
        print("-" * 80)
        try:
            self._generate_dashboard_data()
        except Exception as e:
            print(f"WARNING: Dashboard data generation failed: {e}")
        print()

        # PHASE 6: Adaptive Questions
        print("PHASE 6: Adaptive Questions")
        print("-" * 80)
        try:
            self._run_adaptive_questions()
        except Exception as e:
            print(f"WARNING: Adaptive questions failed: {e}")
        print()

        # PHASE 7: Solution Synthesis
        print("PHASE 7: Solution Synthesis")
        print("-" * 80)
        try:
            solutions = generate_solutions(self.synthesis, self.graph_data)
            sol_file = self.output_dir / "solutions.json"
            with open(sol_file, "w", encoding="utf-8") as f:
                json.dump(solutions, f, indent=2, ensure_ascii=False)
            n_sol = len(solutions.get("solution_candidates", []))
            n_val = len(solutions.get("validated_hypotheses", []))
            print(f"[OK] {n_sol} solution candidates from {n_val} validated hypotheses")
            print(f"[OK] Saved: {sol_file}")
        except Exception as e:
            print(f"WARNING: Solution synthesis failed: {e}")
        print()

        # PHASE 8: Visualizations (PNG)
        print("PHASE 8: Generating Visualizations")
        print("-" * 80)
        try:
            viz = ResonanceVisualizer(output_dir=self.viz_dir)
            genesis_data = {
                "tests": self.tests,
                "graph": self.graph_data,
                "synthesis": self.synthesis
            }
            viz.generate_all_visualizations(genesis_data)
            print(f"[OK] Visualizations saved to: {self.viz_dir}\n")
        except Exception as e:
            print(f"WARNING: Visualization generation failed: {e}\n")

        # PHASE 8b: Holographic Dashboard (Plotly) - optional
        if PLOTLY_AVAILABLE:
            print("PHASE 8b: Holographic Dashboard")
            print("-" * 80)
            try:
                dashboard = HolographicDashboard()
                dashboard.load_genesis_data()
                dashboard.launch_holographic_dashboard()
                print("[OK] Holographic dashboard launched\n")
            except Exception as e:
                print(f"WARNING: Holographic dashboard failed: {e}\n")

        # PHASE 9: Summary
        print("PHASE 9: Integration Summary")
        print("-" * 80)
        self._generate_summary()

        print("\n" + "=" * 80)
        print("MASTER INTEGRATION COMPLETE")
        print("=" * 80)
        return True

    # -------------------------------------------------------------------------

    def _load_test_runs(self) -> bool:
        db_file = self.test_run_dir / "test_database.json"
        if not db_file.exists():
            return False
        with open(db_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tests = data.get("tests", [])
        self.tests = [i for i in tests if isinstance(i, dict)]
        return len(self.tests) > 0

    # -------------------------------------------------------------------------

    def _run_3d_transform(self):
        """Phase 3: NMF + Spectral Embedding → 3D objects."""
        transformer = Transformer3D(n_latent_factors=12)

        # Runtime defensive patch for broadcast/shape bug in _find_neighbors
        try:
            import numpy as np

            if hasattr(transformer, "_find_neighbors"):
                _orig_find = transformer._find_neighbors

                def _patched_find_neighbors(position, all_positions, k=3):
                    ap = np.asarray(all_positions)
                    pos = np.asarray(position)

                    # If all_positions is affinity matrix (N,N), find 3D embedding
                    if ap.ndim == 2 and ap.shape[0] == ap.shape[1] and pos.shape == (3,):
                        cand = None
                        for attr in ("embedding_3d", "embedding_", "positions_", "coords_3d"):
                            if hasattr(transformer, attr):
                                cand = np.asarray(getattr(transformer, attr))
                                break
                        if cand is not None and cand.ndim == 2 and cand.shape[1] == 3:
                            ap = cand
                        else:
                            raise ValueError(
                                f"_find_neighbors: affinity matrix {ap.shape} but no 3D embedding"
                            )

                    if ap.ndim != 2 or ap.shape[1] != 3:
                        raise ValueError(f"_find_neighbors expected (N,3) got {ap.shape}")

                    d = np.linalg.norm(ap - pos, axis=1)
                    idx = np.argsort(d)[1:k+1]  # skip self
                    return idx.tolist()

                transformer._find_neighbors = _patched_find_neighbors
        except Exception:
            pass

        self.objects_3d = transformer.fit_transform(self.tests)

        # Save 3D objects
        objects_file = self.output_dir / "3d_objects.json"
        serial = []
        for obj in self.objects_3d:
            try:
                d = obj.to_dict()
                d["resonance"] = safe_float(d.get("resonance", getattr(obj, "resonance", 0.0)))
                d["volume"] = safe_float(d.get("volume", getattr(obj, "volume", 0.0)))
                if "position" in d:
                    d["position"] = safe_list(d["position"])
                serial.append(d)
            except Exception:
                continue

        with open(objects_file, "w", encoding="utf-8") as f:
            json.dump(serial, f, indent=2, ensure_ascii=False)

        print(f"[OK] Transformed {len(self.objects_3d)} tests → 3D objects")
        print(f"[OK] Saved: {objects_file}")

    # -------------------------------------------------------------------------

    def _analyze_circumpunct(self):
        """Phase 4: Check if discovery has reached convergence."""
        synthesis = self.synthesis
        if not synthesis:
            synthesis_file = self.output_dir / "strategic_intelligence.json"
            if synthesis_file.exists():
                with open(synthesis_file, "r", encoding="utf-8") as f:
                    synthesis = json.load(f)
            else:
                raise FileNotFoundError("No synthesis data available")

        hypotheses = synthesis.get("hypotheses", {})
        validated_count = sum(
            1 for h in hypotheses.values()
            if safe_float(h.get("posterior", 0)) > 0.75
        )
        total_hypotheses = len(hypotheses)
        validation_rate = validated_count / total_hypotheses if total_hypotheses > 0 else 0.0

        segments = synthesis.get("substrate_classs", [])
        avg_confidence = (
            sum(safe_float(c.get("confidence", 0)) for c in segments) / len(segments)
        ) if segments else 0.0

        avg_resonance = (
            sum(safe_float(getattr(obj, "resonance", 0.0)) for obj in self.objects_3d)
            / len(self.objects_3d)
        ) if self.objects_3d else 0.0

        self.circumpunct_achieved = (
            validation_rate > 0.75
            and avg_confidence > 0.70
            and avg_resonance > 0.6
        )

        print(f"Validation Rate: {validation_rate:.0%} ({validated_count}/{total_hypotheses})")
        print(f"Avg Segment Confidence: {avg_confidence:.0%}")
        print(f"Avg 3D Resonance: {avg_resonance:.2f}")

        if self.circumpunct_achieved:
            print("[OK] TARGET CIRCUMPUNCT ACHIEVED")
        else:
            missing = []
            if validation_rate <= 0.75:
                missing.append(f"validation rate {validation_rate:.0%} <= 75%")
            if avg_confidence <= 0.70:
                missing.append(f"segment confidence {avg_confidence:.0%} <= 70%")
            if avg_resonance <= 0.6:
                missing.append(f"resonance {avg_resonance:.2f} <= 0.60")
            print(f"[--] Circumpunct not yet achieved: {', '.join(missing)}")

        circumpunct_data = {
            "achieved": self.circumpunct_achieved,
            "validation_rate": round(validation_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "avg_resonance": round(avg_resonance, 4),
            "timestamp": datetime.now().isoformat()
        }

        with open(self.output_dir / "circumpunct_analysis.json", "w", encoding="utf-8") as f:
            json.dump(circumpunct_data, f, indent=2, ensure_ascii=False)

    # -------------------------------------------------------------------------

    def _generate_dashboard_data(self):
        """Phase 5: JSON payload for dashboard visualization."""
        tests_payload = []
        for obj in self.objects_3d:
            tests_payload.append({
                "test_num": getattr(obj, "test_num", None),
                "script_name": getattr(obj, "script_name", ""),
                "position": safe_list(getattr(obj, "position", [0, 0, 0])),
                "resonance": safe_float(getattr(obj, "resonance", 0.0)),
                "volume": safe_float(getattr(obj, "volume", 0.0)),
                "faces": getattr(obj, "faces", {}),
                "neighbors": getattr(obj, "neighbors", []),
                "attractors": getattr(obj, "attractors", [])
            })

        dashboard_data = {
            "tests": tests_payload,
            "circumpunct": self.circumpunct_achieved,
            "metadata": {
                "total_test_runs": len(self.tests),
                "generated": datetime.now().isoformat()
            }
        }

        dashboard_file = self.output_dir / "dashboard_data.json"
        with open(dashboard_file, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Dashboard data: {dashboard_file}")

    # -------------------------------------------------------------------------

    def _run_adaptive_questions(self):
        """Phase 6: Generate adaptive questions for next test_run."""
        generator = AdaptiveTestGenerator()

        # Use gap analysis to determine next target
        gaps = self.synthesis.get("gaps", [])
        cube_target = "[L2, OC, Sb]"  # default
        for g in gaps:
            profile = g.get("suggested_profile", {})
            if "q_layer" in profile and "q_object" in profile:
                cube_target = f"[{profile['q_layer']}, {profile['q_object']}]"
                break

        next_profile = {
            "test_num": len(self.tests) + 1,
            "script_name": "[Next Test Run]",
            "source_version": "[Target Company]",
            "cube_position": cube_target
        }

        guide = generator.generate_complete_test_run_guide(self.tests, next_profile)

        adaptive_file = self.output_dir / "adaptive_questions.json"
        with open(adaptive_file, "w", encoding="utf-8") as f:
            json.dump(guide, f, indent=2, ensure_ascii=False)

        rec = guide.get("recommended_focus", "N/A")
        ig = guide.get("expected_total_info_gain", None)

        print("[OK] Generated adaptive questions")
        print(f"  Recommended: {rec}")
        if ig is not None:
            print(f"  Info Gain: {safe_float(ig):.2f}")
        print(f"[OK] Saved: {adaptive_file}")

    # -------------------------------------------------------------------------

    def _generate_summary(self):
        print("\nOUTPUTS:")
        outputs = [
            ("Strategic Intelligence", "strategic_intelligence.json"),
            ("Knowledge Entities", "knowledge_entities.json"),
            ("Test Run Graph", "test_graph.json"),
            ("Solutions", "solutions.json"),
            ("3D Objects", "3d_objects.json"),
            ("Dashboard Data", "dashboard_data.json"),
            ("Circumpunct", "circumpunct_analysis.json"),
            ("Adaptive Questions", "adaptive_questions.json"),
        ]
        for label, fname in outputs:
            fp = self.output_dir / fname
            if fp.exists():
                size = fp.stat().st_size
                print(f"  OK {label}: {fp} ({size:,} bytes)")
            else:
                print(f"  -- {label}: {fp} (not generated)")

        viz_pngs = list(self.viz_dir.glob("*.png"))
        if viz_pngs:
            print(f"  OK Visualizations: {len(viz_pngs)} PNGs in {self.viz_dir}/")

        print("\nMETRICS:")
        print(f"  Tests: {len(self.tests)}")
        print(f"  3D Objects: {len(self.objects_3d)}")
        print(f"  Circumpunct: {'YES' if self.circumpunct_achieved else 'NO'}")

        # Hypothesis summary
        hyps = self.synthesis.get("hypotheses", {})
        if hyps:
            print("\nHYPOTHESES:")
            for key, h in hyps.items():
                prior = safe_float(h.get("prior", 0.5))
                post = safe_float(h.get("posterior", 0.5))
                moved = post - prior
                sym = "^" if moved > 0.05 else ("v" if moved < -0.05 else "=")
                ev = h.get("total_evidence_pieces", 0)
                print(f"  {sym} {h.get('name', key)}: {prior:.0%} -> {post:.0%} ({ev} evidence)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    integrator = MasterIntegrator()
    success = integrator.run_complete_pipeline()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
