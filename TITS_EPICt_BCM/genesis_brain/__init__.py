"""
GENESIS BRAIN - Strategic Intelligence for I-Corps Customer Discovery

Core pipeline (GenesisOrchestrator):
  1. KnowledgeExtractor  – pattern-match entities from interview text
  2. GraphBuilder        – build validation/contradiction graph
  3. CognitiveEngine     – Bayesian hypothesis updating + gap analysis

Extended pipeline (MasterIntegrator / master_genesis.py):
  4. Transformer3D               – NMF + spectral embedding → 3D objects
  5. AdaptiveInterviewGenerator   – next-best questions from gaps
  6. ResonanceVisualizer          – PNG visualizations

Usage from GUI:
  from genesis_brain import GenesisOrchestrator
  orch = GenesisOrchestrator(output_dir=Path("GENESIS_OUTPUT"))
  result = orch.run_full_analysis(interviews_dict_list)

Usage from master_genesis.py:
  from genesis_brain import (
      GenesisOrchestrator, Transformer3D,
      AdaptiveInterviewGenerator, ResonanceVisualizer
  )
"""

from .orchestrator import GenesisOrchestrator
from .transformer_3d import Transformer3D
from .adaptive_interviewer import AdaptiveInterviewGenerator
from .resonance_visualizer import ResonanceVisualizer

__all__ = [
    "GenesisOrchestrator",
    "Transformer3D",
    "AdaptiveInterviewGenerator",
    "ResonanceVisualizer",
]
