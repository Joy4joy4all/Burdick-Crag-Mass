# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
CaaS INCLUSION POOL QUANTUM CUBIT
================================================================
Twin Q-Cube: Validation (Research) ↔ Inclusion (Development)

TRIAD INTELLIGENCE:
  FUSION     → What the INDUSTRY says they need  (Research)
  INCLUSION  → What deployed modules ACTUALLY show (Development)
  IMMULSION  → What SaaS recipients VALIDATE     (Deployment)

This engine correlates all three streams:
  1. VP-TRL Alignment:   Do inclusion observations support validation VPs?
  2. Reverse Clustering:  Cluster inclusion topics → regress against VPs
  3. R&D Convergence:     Where research ask meets development evidence
  4. Gap Detection:       VP asks with no development / Dev with no VP
  5. Doctrine Compliance: Does development honor the safety mission?

HIERARCHY:
  THE PERSON > TITS > GIBUSH > AISOS/SPINE > CaaS/SaaS

For all the industrial workers lost to preventable acts.
© 2026 Stephen J. Burdick Sr. — All Rights Reserved.
"""

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# ── ML imports (graceful fallback) ──
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


# ══════════════════════════════════════════════════════════════
# DIRECTORY FILE LOCATIONS — Must match TITS governance hierarchy
# ══════════════════════════════════════════════════════════════
#
# C:\TITS\TITS_GIBUSH_AISOS_SPINE\                          ← _TITS_ROOT (gibush_boot.py lives here)
#   ├── gibush_boot.py                                       ← ENTRY POINT
#   ├── gibush_launcher.py                                   ← TIER 2 launcher
#   ├── gibush_login_gate.py                                 ← Auth + VLAN RBAC
#   ├── gibush_security_controller.py                        ← MAIDon 9-ring defense
#   ├── .gibush_auth/                                        ← users.json, sessions.json, audit
#   ├── mAIDon_Security/                                     ← rings/, config/, logs/, audit/
#   │
#   ├── TITS_GIBUSH_AISOS_SPINE\                             ← _AISOS_ROOT (inner)
#   │   ├── gibush_world_class_ehs.py                        ← TIER 3: AISOS/SPINE (80+ EHS modules)
#   │   └── AISOS_SPINE_MODULES\
#   │       ├── PASS_REQUESTS\                               ← AISOS PASS review files
#   │       ├── TITS_GIBUSH_AISOS_SPINE_Production_CaaS\     ← _CAAS_ROOT
#   │       │   ├── gibush_main_CaaS.py                      ← TIER 4a: CaaS Control Center
#   │       │   ├── icorps_project_tab.py                    ← BCM bridge tab
#   │       │   ├── caas_fleet_monitor.py                    ← Fleet monitoring
#   │       │   ├── aisos_pass_review.py                     ← PASS review tab
#   │       │   ├── inclusion_hot_button.py                  ← Injected into deployed modules
#   │       │   ├── inclusion_receiver.py                    ← Hot button save target
#   │       │   ├── gibush_modules\                          ← Individual CaaS module .py files
#   │       │   ├── gibush_comms\                            ← MQTT, serial, comms
#   │       │   ├── gibush_core\                             ← Core module framework
#   │       │   ├── gibush_config\                           ← Module config JSON
#   │       │   └── gibush_charts\                           ← Chart/viz widgets
#   │       │
#   │       └── TITS_GIBUSH_AISOS_SPINE_PRODUCTION_SaaS\    ← Future (LOCKED)
#   │
#   └── TITS_GIBUSH_AISOS_SPINE_ICORPS\                     ← _ICORPS_ROOT
#       ├── validation_test_collector.py                    ← TIER 5: Test Collector
#       ├── test_intelligence.py                        ← VP scoring + intelligence
#       ├── progressive_test_run_engine.py                  ← Forward/backward/reverse flows
#       ├── post_test_run_generator.py                      ← Post-test packet builder
#       ├── inclusion_cubit_engine.py                        ← ★ THIS FILE ★
#       ├── inclusion_factored_intelligence_tab.py           ← ★ Companion tab widget ★
#       ├── bmc_engine.py                                    ← BMC generation
#       ├── project_paths.py                                 ← Centralized path resolution
#       │
#       ├── genesis_brain\                                   ← Genesis compound intelligence package
#       │   ├── orchestrator.py                              ← Pipeline entry point
#       │   ├── knowledge_extractor.py                       ← 10 entity types
#       │   ├── graph_builder.py                             ← NetworkX, HITS, communities
#       │   ├── cognitive_engine.py                          ← Bayesian synthesis
#       │   ├── bayesian_engine.py                           ← Beta-Binomial (USPTO cited)
#       │   ├── hypothesis_engine.py                         ← Log-odds updating
#       │   ├── qcube_config.py                              ← Configurable Q-Cube axes
#       │   ├── doctoral_analyzer.py                      ← Info-gain adaptive questions
#       │   ├── adaptive_analyzer.py                      ← TF-IDF keyword amplitude
#       │   ├── doctoral_project_manager.py                  ← Project lifecycle
#       │   ├── module_registry.py                           ← Equipment EPV catalog
#       │   ├── transformer_3d.py                            ← NMF + spectral embedding
#       │   ├── resonance_visualizer.py                      ← 6 visualizations
#       │   ├── auth_manager.py                              ← RBAC + PBKDF2
#       │   ├── feature_flags.py                             ← Per-team toggles
#       │   ├── ml_research_roadmap.py                       ← Tier 1-5 ML expansion
#       │   ├── project_manager.py                           ← Directory management
#       │   ├── genesis_workstation.py                       ← PySide6 GUI shell
#       │   └── utils_format.py                              ← safe_float helpers
#       │
#       ├── Inclusion_Module_Receipt_Collector\              ← Inclusion package
#       │   ├── __init__.py                                  ← Exports MASTER_LENS, get_*
#       │   └── inclusion_receipt.py                         ← Receipt collector + ML tagging
#       │
#       ├── Immulsion_Receiver\                              ← Immulsion package (future)
#       │   └── immulsion_receiver.py                        ← ML5/6/7 SaaS feedback
#       │
#       └── BCM_TESTS\                               ← Per-project data
#           ├── BCM_SUBSTRATE\
#           │   ├── test_database.json
#           │   ├── project_config.json
#           │   ├── doctrine.md
#           │   ├── inclusion_log.json                       ← Written by inclusion_receiver.py
#           │   ├── immulsion_log.json                       ← Written by immulsion_receiver.py
#           │   ├── inclusion_cubit_state.json               ← Written by THIS ENGINE
#           │   ├── inclusion_tests.json                ← Consolidated by receipt collector
#           │   ├── tested\                             ← Individual test_run/inclusion files
#           │   ├── BMC_generation\                          ← BMC docs
#           │   └── genesis_output\                          ← strategic_intelligence.json, etc.
#           ├── BCM_NAVIGATION\
#           ├── BARK_TRANSFER\
#           └── (other projects...)
#
# DATA FLOW:
#   CaaS module deployed → inclusion_hot_button → inclusion_receiver →
#     inclusion_log.json → inclusion_receipt.py reads → THIS ENGINE correlates →
#     inclusion_factored_intelligence_tab.py displays
#
# GOVERNANCE RULE: One-way data flow CaaS → SPINE (read-only, never reverse)
# PERSON PRIORITY: Safety signals must be addressed before VP advancement
#
# ══════════════════════════════════════════════════════════════

from pathlib import Path as _Path

_TITS_ROOT = _Path(r"C:\TITS\TITS_GIBUSH_AISOS_SPINE")
_AISOS_ROOT = _TITS_ROOT / "TITS_GIBUSH_AISOS_SPINE"
_CAAS_ROOT = _AISOS_ROOT / "AISOS_SPINE_MODULES" / "TITS_GIBUSH_AISOS_SPINE_Production_CaaS"
_ICORPS_ROOT = _TITS_ROOT / "TITS_GIBUSH_AISOS_SPINE_ICORPS"
_BCM_ROOT = _ICORPS_ROOT / "BCM_TESTS"
_GENESIS_ROOT = _ICORPS_ROOT / "genesis_brain"
_INCLUSION_PKG = _ICORPS_ROOT / "Inclusion_Module_Receipt_Collector"
_PASS_DIR = _AISOS_ROOT / "AISOS_SPINE_MODULES" / "PASS_REQUESTS"


# ══════════════════════════════════════════════════════════════
# TRL STAGES — Technology Readiness Levels
# ══════════════════════════════════════════════════════════════

TRL_STAGES = {
    1: "Basic principles observed",
    2: "Technology concept formulated",
    3: "Experimental proof of concept",
    4: "Technology validated in lab",
    5: "Technology validated in relevant environment",
    6: "Technology demonstrated in relevant environment",
    7: "System prototype in operational environment",
    8: "System complete and qualified",
    9: "Actual system proven in operational environment",
}

# TRL keywords — what inclusion observations indicate about development stage
TRL_KEYWORDS = {
    1: ['concept', 'idea', 'theory', 'research', 'principle', 'fundamental'],
    2: ['design', 'formulate', 'specification', 'architecture', 'requirements'],
    3: ['prototype', 'proof of concept', 'poc', 'bench test', 'lab test', 'experimental'],
    4: ['validated', 'lab environment', 'controlled test', 'calibration', 'baseline'],
    5: ['field test', 'relevant environment', 'pilot site', 'mill trial', 'on-site test'],
    6: ['demonstrated', 'operational demo', 'live environment', 'production trial'],
    7: ['system prototype', 'integration test', 'full system', 'operational prototype'],
    8: ['qualified', 'complete system', 'acceptance test', 'commissioning'],
    9: ['operational', 'production', 'deployed', 'running', 'in service', 'saas'],
}


# ══════════════════════════════════════════════════════════════
# VP ALIGNMENT KEYWORDS — What observations map to which VP
# ══════════════════════════════════════════════════════════════

VP_ALIGNMENT_KEYWORDS = {
    'VP1_DAMAGE_PREVENTION': [
        'damage', 'prevent', 'detect', 'rock', 'tramp', 'metal',
        'contamination', 'cost', 'repair', 'downtime', 'loss',
    ],
    'VP2_PLANNED_MAINTENANCE': [
        'maintenance', 'planned', 'reactive', 'schedule', 'predict',
        'condition', 'monitor', 'proactive', 'preventive',
    ],
    'VP3_OPERATOR_VISIBILITY': [
        'operator', 'visibility', 'real-time', 'dashboard', 'alert',
        'alarm', 'display', 'interface', 'hmi', 'notification',
    ],
    'VP4_CHEMICAL_OPTIMIZATION': [
        'chemical', 'quality', 'optimization', 'stabilization',
        'pulp quality', 'consistency', 'variance', 'additive',
    ],
    'VP5_SUPPLIER_ACCOUNTABILITY': [
        'supplier', 'vendor', 'accountability', 'log', 'record',
        'trace', 'source', 'incoming', 'receiving', 'chip quality',
    ],
    'VP6_PITCH_CONTAMINATION': [
        'pitch', 'upstream', 'paper machine', 'trace', 'contaminant',
        'fiber', 'extractive', 'deposit', 'sticky',
    ],
}


# ══════════════════════════════════════════════════════════════
# INCLUSION CUBIT ENGINE — The Twin Q-Cube
# ══════════════════════════════════════════════════════════════

class InclusionCubitEngine:
    """
    Builds a twin Q-Cube from Inclusion data that mirrors the Validation Q-Cube.
    
    Validation cube axes:  [L1-L3 (role), OA-OC (company type), Sa-Sg (segment)]
    Inclusion cube:    [TRL1-9 (readiness), ML0-ML4 (lens), Dev/Test/Deploy]
    
    The engine computes alignment between the two cubes to show
    where R (research/validation) and D (development/inclusion) converge or diverge.
    """

    def __init__(self):
        self.validation_tests = []
        self.inclusion_entries = []
        self.immulsion_entries = []
        self.validation_state = {}
        self.inclusion_state = {}
        self.alignment_matrix = {}
        self.clusters = []
        self.convergence_score = 0.0

    def load_validation_data(self, test_runs: List[dict], intel_state: dict = None):
        """Load Validation test data and intelligence state."""
        self.validation_tests = [
            iv for iv in test_runs
            if iv.get('source', 'FUSION') == 'FUSION'
            and iv.get('results')
            and '[PENDING' not in str(iv.get('results', ''))
        ]
        self.validation_state = intel_state or {}

    def load_inclusion_data(self, entries: List[dict]):
        """Load Inclusion observations from receipt collector."""
        self.inclusion_entries = [
            e for e in entries
            if e.get('source') == 'INCLUSION'
        ]

    def load_immulsion_data(self, entries: List[dict]):
        """Load Immulsion feedback from receiver."""
        self.immulsion_entries = [
            e for e in entries
            if e.get('source') == 'IMMULSION'
        ]

    # ──────────────────────────────────────────
    # TRL CLASSIFICATION
    # ──────────────────────────────────────────

    def classify_trl(self, text: str) -> int:
        """
        Classify an observation's TRL based on keyword matching.
        Returns highest TRL stage with evidence.
        """
        if not text:
            return 1
        text_lower = text.lower()
        best_trl = 1
        best_score = 0

        for trl, keywords in TRL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_trl = trl
            elif score == best_score and trl > best_trl:
                best_trl = trl

        return best_trl

    # ──────────────────────────────────────────
    # VP ALIGNMENT SCORING
    # ──────────────────────────────────────────

    def score_vp_alignment(self, text: str) -> Dict[str, float]:
        """
        Score how much an observation aligns with each VP.
        Returns dict: {VP_ID: alignment_score (0-1)}
        """
        if not text:
            return {vp: 0.0 for vp in VP_ALIGNMENT_KEYWORDS}

        text_lower = text.lower()
        scores = {}

        for vp_id, keywords in VP_ALIGNMENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            # Normalize by keyword count
            scores[vp_id] = min(1.0, hits / max(1, len(keywords) * 0.3))

        return scores

    # ──────────────────────────────────────────
    # VP-TRL ALIGNMENT MATRIX
    # ──────────────────────────────────────────

    def build_alignment_matrix(self) -> Dict:
        """
        Build the VP-TRL alignment matrix.
        
        Rows: 6 VPs
        Columns: 9 TRL stages
        Cells: count of inclusion observations + alignment score
        
        This shows WHERE development evidence exists for each VP
        and at what technology readiness level.
        """
        matrix = {}
        for vp_id in VP_ALIGNMENT_KEYWORDS:
            matrix[vp_id] = {
                trl: {'count': 0, 'score': 0.0, 'observations': []}
                for trl in range(1, 10)
            }

        for entry in self.inclusion_entries:
            text = entry.get('results', '') or entry.get('observation', '')
            trl = self.classify_trl(text)
            vp_scores = self.score_vp_alignment(text)

            for vp_id, score in vp_scores.items():
                if score > 0.1:  # Threshold
                    cell = matrix[vp_id][trl]
                    cell['count'] += 1
                    cell['score'] += score
                    cell['observations'].append({
                        'script_name': entry.get('script_name', '?'),
                        'lens': entry.get('master_lens', '?'),
                        'text': text[:100],
                        'score': round(score, 2),
                    })

        self.alignment_matrix = matrix
        return matrix

    # ──────────────────────────────────────────
    # REVERSE CLUSTER REGRESSION
    # ──────────────────────────────────────────

    def reverse_cluster_regression(self, n_clusters: int = 5) -> List[dict]:
        """
        Cluster inclusion observations by topic, then regress each
        cluster against validation VPs to find alignment/gaps.
        
        Returns list of clusters with:
          - topic keywords
          - VP alignment scores
          - TRL distribution
          - R&D verdict: ALIGNED | GAP | ORPHAN
        """
        if not _HAS_SKLEARN or not _HAS_NUMPY:
            return self._fallback_clustering()

        texts = []
        entries = []
        for e in self.inclusion_entries:
            text = e.get('results', '') or e.get('observation', '')
            if text and len(text) > 10:
                texts.append(text)
                entries.append(e)

        if len(texts) < 3:
            return self._fallback_clustering()

        # Fit n_clusters but don't exceed document count
        k = min(n_clusters, len(texts))

        # TF-IDF vectorize
        vectorizer = TfidfVectorizer(
            max_features=200, stop_words='english',
            ngram_range=(1, 2), min_df=1
        )
        tfidf = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()

        # KMeans clustering
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(tfidf)

        # Build VP keyword vectors for regression
        vp_texts = {
            vp_id: ' '.join(keywords)
            for vp_id, keywords in VP_ALIGNMENT_KEYWORDS.items()
        }
        vp_tfidf = vectorizer.transform(list(vp_texts.values()))
        vp_ids = list(vp_texts.keys())

        clusters = []
        for c in range(k):
            mask = (labels == c)
            cluster_indices = np.where(mask)[0]
            if len(cluster_indices) == 0:
                continue

            # Top keywords for this cluster
            centroid = km.cluster_centers_[c]
            top_idx = centroid.argsort()[-5:][::-1]
            top_keywords = [feature_names[i] for i in top_idx]

            # Cluster entries
            cluster_entries = [entries[i] for i in cluster_indices]

            # TRL distribution
            trl_dist = defaultdict(int)
            for e in cluster_entries:
                text = e.get('results', '') or e.get('observation', '')
                trl_dist[self.classify_trl(text)] += 1

            # Regression: cosine similarity of cluster centroid to each VP
            centroid_2d = centroid.reshape(1, -1)
            vp_sims = cosine_similarity(centroid_2d, vp_tfidf)[0]
            vp_alignment = {
                vp_ids[i]: round(float(vp_sims[i]), 3)
                for i in range(len(vp_ids))
            }
            best_vp = max(vp_alignment, key=vp_alignment.get)
            best_score = vp_alignment[best_vp]

            # Master lens distribution
            lens_dist = defaultdict(int)
            for e in cluster_entries:
                lens_dist[e.get('master_lens', '?')] += 1

            # R&D Verdict
            if best_score > 0.15:
                verdict = "ALIGNED"
                verdict_detail = f"Development supports {best_vp} ({best_score:.0%})"
            elif best_score > 0.05:
                verdict = "WEAK"
                verdict_detail = f"Weak link to {best_vp} — needs targeted inclusion work"
            else:
                verdict = "ORPHAN"
                verdict_detail = "Development activity with no VP backing — reassess priority"

            clusters.append({
                'cluster_id': c,
                'size': len(cluster_entries),
                'keywords': top_keywords,
                'best_vp': best_vp,
                'best_vp_score': best_score,
                'vp_alignment': vp_alignment,
                'trl_distribution': dict(trl_dist),
                'max_trl': max(trl_dist.keys()) if trl_dist else 1,
                'lens_distribution': dict(lens_dist),
                'verdict': verdict,
                'verdict_detail': verdict_detail,
                'sample_observations': [
                    e.get('results', e.get('observation', ''))[:80]
                    for e in cluster_entries[:3]
                ],
            })

        self.clusters = sorted(clusters, key=lambda c: c['best_vp_score'], reverse=True)
        return self.clusters

    def _fallback_clustering(self) -> List[dict]:
        """Simple keyword-based clustering when sklearn unavailable."""
        clusters = []
        by_type = defaultdict(list)
        for e in self.inclusion_entries:
            obs_type = e.get('observation_type', 'General')
            by_type[obs_type].append(e)

        for obs_type, entries in by_type.items():
            texts = [e.get('results', '') or e.get('observation', '') for e in entries]
            combined = ' '.join(texts)
            vp_scores = self.score_vp_alignment(combined)
            best_vp = max(vp_scores, key=vp_scores.get)

            trl_dist = defaultdict(int)
            for text in texts:
                trl_dist[self.classify_trl(text)] += 1

            clusters.append({
                'cluster_id': len(clusters),
                'size': len(entries),
                'keywords': [obs_type],
                'best_vp': best_vp,
                'best_vp_score': vp_scores[best_vp],
                'vp_alignment': vp_scores,
                'trl_distribution': dict(trl_dist),
                'max_trl': max(trl_dist.keys()) if trl_dist else 1,
                'verdict': 'ALIGNED' if vp_scores[best_vp] > 0.15 else 'WEAK',
                'verdict_detail': obs_type,
            })

        self.clusters = clusters
        return clusters

    # ──────────────────────────────────────────
    # STREAM CONVERGENCE — R&D Score
    # ──────────────────────────────────────────

    def compute_convergence(self) -> dict:
        """
        Compute R&D convergence between Validation (R) and Inclusion (D).
        
        Returns:
          - convergence_score: 0-100% (how well D tracks R)
          - vp_coverage: which VPs have inclusion evidence
          - trl_frontier: highest TRL reached per VP
          - gaps: VPs with no development evidence
          - orphans: development clusters with no VP support
          - immulsion_validation: which VPs have SaaS recipient confirmation
        """
        if not self.alignment_matrix:
            self.build_alignment_matrix()
        if not self.clusters:
            self.reverse_cluster_regression()

        # VP coverage from validation state
        validation_vps = self.validation_state.get('vp_scores', {})

        # VP coverage from inclusion
        vp_coverage = {}
        trl_frontier = {}
        for vp_id, trl_data in self.alignment_matrix.items():
            total_obs = sum(cell['count'] for cell in trl_data.values())
            max_trl = 0
            for trl, cell in trl_data.items():
                if cell['count'] > 0:
                    max_trl = max(max_trl, trl)
            vp_coverage[vp_id] = {
                'inclusion_observations': total_obs,
                'max_trl': max_trl,
                'trl_label': TRL_STAGES.get(max_trl, 'No evidence'),
                'validation_confidence': validation_vps.get(vp_id, {}).get('confidence', 0),
            }
            trl_frontier[vp_id] = max_trl

        # Gaps: VPs with high validation confidence but no inclusion evidence
        gaps = []
        for vp_id, cov in vp_coverage.items():
            if cov['validation_confidence'] >= 50 and cov['inclusion_observations'] == 0:
                gaps.append({
                    'vp': vp_id,
                    'validation_confidence': cov['validation_confidence'],
                    'problem': f"Industry says {cov['validation_confidence']}% important "
                               f"but ZERO inclusion development evidence",
                    'action': "Deploy CaaS module targeting this VP. Get TL inclusion feedback.",
                })

        # Orphans: inclusion clusters with no VP alignment
        orphans = [c for c in self.clusters if c.get('verdict') == 'ORPHAN']

        # Immulsion validation
        immulsion_vp_support = defaultdict(int)
        for entry in self.immulsion_entries:
            text = entry.get('results', '') or entry.get('observation', '')
            vp_scores = self.score_vp_alignment(text)
            for vp_id, score in vp_scores.items():
                if score > 0.1:
                    immulsion_vp_support[vp_id] += 1

        # Convergence score: weighted average of VP development coverage
        if not validation_vps:
            convergence = 0.0
        else:
            covered = 0
            total_weight = 0
            for vp_id, vp_data in validation_vps.items():
                weight = vp_data.get('confidence', 50) / 100.0
                total_weight += weight
                cov = vp_coverage.get(vp_id, {})
                if cov.get('max_trl', 0) >= 3:
                    covered += weight * min(1.0, cov['max_trl'] / 7.0)
                elif cov.get('inclusion_observations', 0) > 0:
                    covered += weight * 0.2  # Some evidence, low TRL

            convergence = (covered / total_weight * 100) if total_weight > 0 else 0.0

        self.convergence_score = round(convergence, 1)

        return {
            'convergence_score': self.convergence_score,
            'convergence_label': self._convergence_label(self.convergence_score),
            'validation_test_count': len(self.validation_tests),
            'inclusion_entry_count': len(self.inclusion_entries),
            'immulsion_entry_count': len(self.immulsion_entries),
            'vp_coverage': vp_coverage,
            'trl_frontier': trl_frontier,
            'gaps': gaps,
            'orphans': [
                {'keywords': o['keywords'], 'size': o['size'], 'detail': o['verdict_detail']}
                for o in orphans
            ],
            'immulsion_validation': dict(immulsion_vp_support),
            'clusters': self.clusters,
            'alignment_matrix': {
                vp: {
                    str(trl): {'count': cell['count'], 'score': round(cell['score'], 2)}
                    for trl, cell in trl_data.items()
                    if cell['count'] > 0
                }
                for vp, trl_data in self.alignment_matrix.items()
            },
            'doctrine_check': self._check_doctrine(),
            'timestamp': datetime.now().isoformat(),
        }

    def _convergence_label(self, score: float) -> str:
        if score >= 80:
            return "STRONG R&D ALIGNMENT — Development tracks industry ask"
        elif score >= 50:
            return "MODERATE — Some VPs developing, others need inclusion work"
        elif score >= 20:
            return "WEAK — Significant gaps between research and development"
        else:
            return "MINIMAL — Development not aligned with validated VPs"

    def _check_doctrine(self) -> dict:
        """Check if inclusion observations honor safety doctrine."""
        safety_count = sum(
            1 for e in self.inclusion_entries
            if e.get('safety_signal')
        )
        urgent_count = sum(
            1 for e in self.inclusion_entries
            if e.get('severity') in ('URGENT', 'CRITICAL')
        )
        service_count = sum(
            1 for e in self.immulsion_entries
            if e.get('service_request')
        )

        return {
            'safety_signals': safety_count,
            'urgent_observations': urgent_count,
            'service_requests': service_count,
            'person_priority_met': urgent_count == 0 or safety_count > 0,
            'note': "THE PERSON is the highest priority. "
                    "Safety signals must be addressed before VP advancement."
                    if safety_count > 0 else
                    "No safety signals detected in current inclusion data.",
        }

    # ──────────────────────────────────────────
    # SUMMARY FOR GUI
    # ──────────────────────────────────────────

    def get_dashboard_data(self) -> dict:
        """
        Complete data package for the Inclusion Factored Intelligence tab.
        Call this after loading all three streams.
        """
        convergence = self.compute_convergence()

        # Build VP summary rows for table display
        vp_rows = []
        for vp_id, cov in convergence['vp_coverage'].items():
            vp_label = vp_id.replace('VP', 'VP ').replace('_', ' ').title()
            imm_count = convergence['immulsion_validation'].get(vp_id, 0)

            # R&D status
            trl = cov['max_trl']
            if trl >= 7:
                rd_status = "PRODUCTION"
            elif trl >= 5:
                rd_status = "FIELD TEST"
            elif trl >= 3:
                rd_status = "PROTOTYPE"
            elif trl >= 1 and cov['inclusion_observations'] > 0:
                rd_status = "CONCEPT"
            else:
                rd_status = "NO DEV"

            vp_rows.append({
                'vp_id': vp_id,
                'vp_label': vp_label,
                'validation_confidence': cov['validation_confidence'],
                'inclusion_count': cov['inclusion_observations'],
                'max_trl': trl,
                'trl_label': TRL_STAGES.get(trl, 'None'),
                'immulsion_count': imm_count,
                'rd_status': rd_status,
                'aligned': cov['validation_confidence'] > 0 and trl > 0,
            })

        return {
            'convergence': convergence,
            'vp_rows': sorted(vp_rows, key=lambda r: r['validation_confidence'], reverse=True),
            'cluster_summary': [
                {
                    'keywords': ', '.join(c['keywords'][:3]),
                    'size': c['size'],
                    'best_vp': c['best_vp'],
                    'score': c['best_vp_score'],
                    'trl': c.get('max_trl', 0),
                    'verdict': c['verdict'],
                }
                for c in self.clusters[:8]
            ],
            'stream_counts': {
                'validation': len(self.validation_tests),
                'inclusion': len(self.inclusion_entries),
                'immulsion': len(self.immulsion_entries),
            },
        }

    # ──────────────────────────────────────────
    # SAVE / LOAD
    # ──────────────────────────────────────────

    def save_state(self, project_dir: Path):
        """Save cubit state to project folder."""
        out_file = project_dir / "inclusion_cubit_state.json"
        data = {
            'engine': 'InclusionCubitEngine',
            'timestamp': datetime.now().isoformat(),
            'convergence_score': self.convergence_score,
            'cluster_count': len(self.clusters),
            'alignment_matrix_summary': {
                vp: sum(cell['count'] for cell in trl_data.values())
                for vp, trl_data in self.alignment_matrix.items()
            },
        }
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return out_file


# ══════════════════════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  CaaS INCLUSION POOL QUANTUM CUBIT — Self-Test")
    print("  Twin Q-Cube: Validation (Research) ↔ Inclusion (Development)")
    print("=" * 70)

    engine = InclusionCubitEngine()

    # Simulate validation data
    fake_validation = [
        {'test_num': 1, 'script_name': 'Jerry Keck', 'source': 'FUSION',
         'results': 'Rock damage costs $200K/year. No detection system exists.'},
        {'test_num': 2, 'script_name': 'Ryan Thorton', 'source': 'FUSION',
         'results': 'Operators hear rocks before instruments detect. Need real-time alerts.'},
        {'test_num': 3, 'script_name': 'Rocky Smith', 'source': 'FUSION',
         'results': 'Maintenance is reactive. Planned maintenance would save 40% costs.'},
    ]
    fake_intel = {
        'vp_scores': {
            'VP1_DAMAGE_PREVENTION': {'confidence': 100, 'status': 'VALIDATED'},
            'VP2_PLANNED_MAINTENANCE': {'confidence': 80, 'status': 'VALIDATED'},
            'VP3_OPERATOR_VISIBILITY': {'confidence': 90, 'status': 'VALIDATED'},
            'VP4_CHEMICAL_OPTIMIZATION': {'confidence': 40, 'status': 'TESTING'},
            'VP5_SUPPLIER_ACCOUNTABILITY': {'confidence': 60, 'status': 'TESTING'},
            'VP6_PITCH_CONTAMINATION': {'confidence': 20, 'status': 'UNTESTED'},
        }
    }

    # Simulate inclusion data
    fake_inclusion = [
        {'source': 'INCLUSION', 'master_lens': 'ML2', 'script_name': 'Steve (TL)',
         'observation_type': 'Equipment Observation',
         'results': 'Prototype sensor detected rock signature at 3kHz. Lab validated.',
         'severity': 'NOTICE'},
        {'source': 'INCLUSION', 'master_lens': 'ML2', 'script_name': 'Steve (TL)',
         'observation_type': 'Process Anomaly',
         'results': 'Field test at mill showed detection 200ms before operator heard impact.',
         'severity': 'NOTICE'},
        {'source': 'INCLUSION', 'master_lens': 'ML1', 'script_name': 'Dad (EL)',
         'observation_type': 'Hypothesis Evidence',
         'results': 'Supplier chip quality varies 40% between loads. Need accountability log.',
         'severity': 'CONCERN'},
        {'source': 'INCLUSION', 'master_lens': 'ML0', 'script_name': 'Operator',
         'observation_type': 'Operator Feedback',
         'results': 'Dashboard alert worked during night shift. Operator confirmed visibility.',
         'severity': 'NOTICE'},
    ]

    # Simulate immulsion data
    fake_immulsion = [
        {'source': 'IMMULSION', 'master_lens': 'ML5', 'script_name': 'Mill Engineer',
         'results': 'Detection system caught 3 rock events in first week. Damage prevented.',
         'service_request': False},
    ]

    engine.load_validation_data(fake_validation, fake_intel)
    engine.load_inclusion_data(fake_inclusion)
    engine.load_immulsion_data(fake_immulsion)

    dashboard = engine.get_dashboard_data()
    conv = dashboard['convergence']

    print(f"\n  R&D CONVERGENCE: {conv['convergence_score']}%")
    print(f"  {conv['convergence_label']}")
    print(f"\n  Streams: F={conv['validation_test_count']} | "
          f"I={conv['inclusion_entry_count']} | "
          f"M={conv['immulsion_entry_count']}")

    print(f"\n  VP-TRL ALIGNMENT:")
    print(f"  {'VP':<30} {'Validation':>8} {'Inc.Obs':>8} {'TRL':>5} {'R&D Status':<12}")
    print(f"  {'─'*30} {'─'*8} {'─'*8} {'─'*5} {'─'*12}")
    for row in dashboard['vp_rows']:
        print(f"  {row['vp_label']:<30} {row['validation_confidence']:>7}% "
              f"{row['inclusion_count']:>8} {row['max_trl']:>5} {row['rd_status']:<12}")

    if conv['gaps']:
        print(f"\n  ⚠ R&D GAPS:")
        for gap in conv['gaps']:
            print(f"    {gap['vp']}: {gap['problem']}")

    if dashboard['cluster_summary']:
        print(f"\n  INCLUSION CLUSTERS:")
        for c in dashboard['cluster_summary']:
            print(f"    [{c['verdict']:<8}] {c['keywords']:<30} "
                  f"→ {c['best_vp']} ({c['score']:.0%}) TRL{c['trl']}")

    doc = conv['doctrine_check']
    print(f"\n  DOCTRINE: {doc['note']}")

    print(f"\n  {'='*70}")
    print(f"  TEST COMPLETE")
    print(f"  {'='*70}")
