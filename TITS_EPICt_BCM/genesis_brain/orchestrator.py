# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - ORCHESTRATOR
==============================
Single entry point for the full analysis pipeline.

The GUI calls:
    from genesis_brain import GenesisOrchestrator
    orch = GenesisOrchestrator(output_dir=Path("GENESIS_OUTPUT"))
    result = orch.run_full_analysis(tests_dict_list)

Pipeline:
    tests → KnowledgeExtractor → GraphBuilder → CognitiveSynthesisEngine → JSON files

VERIFIED against actual genesis_brain/ package files:
  - graph_builder.py       → GraphBuilder (has .build(), .export_json())
  - cognitive_engine.py    → CognitiveSynthesisEngine (has .run_synthesis())
  - knowledge_extractor.py → KnowledgeExtractor (has .extract_from_test_run())
"""

import json
import time
from pathlib import Path
from typing import Dict, List

# Genesis modules — verified class names from actual package files
from .knowledge_extractor import KnowledgeExtractor
from .graph_builder import GraphBuilder
from .cognitive_engine import CognitiveSynthesisEngine


class GenesisOrchestrator:
    """
    Run the full Genesis Brain pipeline and write output files.

    Output files (all in output_dir):
        knowledge_entities.json  – extracted entities + summary
        test_graph.json     – graph nodes, edges, communities
        strategic_intelligence.json – hypotheses, insights, gaps, market
    """

    def __init__(self, output_dir: Path = None, project: str = 'BCM_SUBSTRATE'):
        self.output_dir = output_dir or Path('GENESIS_OUTPUT')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project = project

    def run_full_analysis(self, test_runs: List[Dict]) -> Dict:
        """
        Full pipeline.

        Args:
            test_runs: list of test_run dicts (from Test Run.to_dict())

        Returns:
            strategic_intelligence dict (also saved to disk)
        """
        t0 = time.time()
        print(f"[GENESIS] Starting analysis of {len(test_runs)} tests...")

        # ── Step 1: Extract entities ──────────────────────────────
        print("[GENESIS] Step 1/3: Extracting knowledge entities...")
        extractor = KnowledgeExtractor(project=self.project)

        # KnowledgeExtractor API: .extract_from_test_run(num, text)
        # No .extract_all() method — must call per test
        all_entities = []
        for iv in test_runs:
            num = iv.get('test_num', 0)
            # Combine all text fields for extraction
            text_parts = []
            for field in ('results', 'hypotheses', 'action_iterate',
                          'experiments', 'hypothesis_validation'):
                val = iv.get(field, '')
                if val and not str(val).startswith('[PENDING'):
                    text_parts.append(str(val))
            text = ' '.join(text_parts)
            if text.strip():
                entities = extractor.extract_from_test_run(num, text)
                all_entities.extend(entities)

        entity_dicts = [e.to_dict() for e in all_entities]

        # Save entities — use .export_knowledge_graph() (not .export_json())
        ent_file = self.output_dir / 'knowledge_entities.json'
        extractor.export_knowledge_graph(str(ent_file))
        print(f"  → {len(all_entities)} entities extracted. Saved to {ent_file.name}")

        # Summary — use .get_entity_summary() (not .get_summary())
        summary = extractor.get_entity_summary()
        for etype, count in sorted(summary.get('by_type', {}).items()):
            print(f"    {etype}: {count}")

        # ── Step 2: Build graph ───────────────────────────────────
        print("[GENESIS] Step 2/3: Building test_run graph...")
        builder = GraphBuilder()
        builder.build(tests, entity_dicts)

        graph_file = self.output_dir / 'test_graph.json'
        builder.export_json(str(graph_file))
        print(f"  → {len(builder.nodes)} nodes, {len(builder.edges)} edges, "
              f"{len(builder.contradictions)} contradictions, "
              f"{len(builder.communities)} communities. Saved to {graph_file.name}")

        # Load graph data back for cognitive engine
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)

        # ── Step 3: Cognitive synthesis ───────────────────────────
        print("[GENESIS] Step 3/3: Running cognitive synthesis...")
        # CognitiveSynthesisEngine(graph_data, entities_data, qcube_axes=None)
        engine = CognitiveSynthesisEngine(graph_data, {'entities': entity_dicts})
        result = engine.run_synthesis()

        intel_file = self.output_dir / 'strategic_intelligence.json'
        with open(intel_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"  → Saved to {intel_file.name}")

        # Print hypothesis summary
        for k, h in result.get('hypotheses', {}).items():
            prior = h.get('prior', 0)
            posterior = h.get('posterior', 0)
            moved = posterior - prior
            sym = '↑' if moved > 0 else ('↓' if moved < 0 else '—')
            print(f"    {h.get('name', k)}: {prior:.0%} → {posterior:.0%} ({sym})")

        elapsed = time.time() - t0
        print(f"[GENESIS] Complete in {elapsed:.1f}s. "
              f"Entities={len(all_entities)}, Edges={len(builder.edges)}, "
              f"Insights={len(result.get('insights', []))}, "
              f"Gaps={len(result.get('gaps', []))}")

        return result
