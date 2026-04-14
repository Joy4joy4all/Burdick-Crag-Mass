# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - GRAPH BUILDER
==============================
Builds relationship graph between tests based on entity overlap,
contradiction detection, and information reinforcement.

Creates weighted edges representing:
- Validation strength (multiple sources confirming same fact)
- Contradiction severity (conflicting claims)
- Information dependency (Test Run B depends on Test Run A's context)
"""

import json
import networkx as nx
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import numpy as np


@dataclass
class Test RunNode:
    """Node representing a single test_run in the graph"""
    test_num: int
    person: str
    company: str
    q_layer: str  # L1, L2, L3
    q_object: str  # OA, OB, OC
    q_stack: List[str]  # Sa, Sb, Sg, Sd
    entities: List[Dict]  # Extracted entities from this test_run
    
    def get_cube_position(self) -> str:
        """Get cube position as string"""
        stacks = ','.join(self.q_stack)
        return f"[{self.q_layer}, {self.q_object}, {stacks}]"


@dataclass
class Edge:
    """Edge between two test_runs"""
    source: int
    target: int
    edge_type: str  # 'validates', 'contradicts', 'extends', 'duplicates'
    weight: float  # Strength of relationship
    evidence: List[str]  # What entities/facts create this edge
    
    def to_dict(self) -> Dict:
        return {
            'source': self.source,
            'target': self.target,
            'type': self.edge_type,
            'weight': self.weight,
            'evidence': self.evidence
        }


class TestGraphBuilder:
    """
    Builds knowledge graph from extracted entities and test metadata.
    
    Graph theory approach:
    - Nodes = Test Runs
    - Edges = Relationships (validation, contradiction, extension)
    - Weights = Relationship strength
    - Communities = Synergy clusters
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[int, Test RunNode] = {}
        self.edges: List[Edge] = []
    
    def add_test_run_node(self, test_num: int, person: str, company: str,
                          q_layer: str, q_object: str, q_stack: List[str],
                          entities: List[Dict]):
        """Add test_run as node in graph"""
        node = Test RunNode(
            test_num=test_num,
            person=person,
            company=company,
            q_layer=q_layer,
            q_object=q_object,
            q_stack=q_stack,
            entities=entities
        )
        
        self.nodes[person] = node
        
        # Add to NetworkX graph
        self.graph.add_node(
            test_num,
            person=person,
            company=company,
            cube_position=node.get_cube_position(),
            entity_count=len(entities)
        )
    
    def build_edges(self):
        """
        Build all edges between test_run nodes.
        
        Edge types:
        1. VALIDATES - Two tests mention same fact (reinforcement)
        2. CONTRADICTS - Two tests have conflicting claims (needs resolution)
        3. EXTENDS - Test Run B adds detail to Test Run A's claim
        4. DUPLICATES - Same person/company tested twice (temporal comparison)
        """
        script_keys = list(self.nodes.keys())
        
        for i, source_key in enumerate(script_keys):
            for target_key in script_keys[i+1:]:
                source_node = self.nodes[source_key]
                target_node = self.nodes[target_key]
                
                # Check for validation edges
                self._check_validation_edge(source_node, target_node)
                
                # Check for contradiction edges
                self._check_contradiction_edge(source_node, target_node)
                
                # Check for extension edges
                self._check_extension_edge(source_node, target_node)
                
                # Check for duplicate source edges
                self._check_duplicate_edge(source_node, target_node)
    
    def _check_validation_edge(self, source: Test RunNode, target: Test RunNode):
        """Check if target validates source's claims"""
        evidence = []
        validation_score = 0.0
        
        # Extract costs from both
        source_costs = [e for e in source.entities if e['type'] == 'cost']
        target_costs = [e for e in target.entities if e['type'] == 'cost']
        
        # Check cost overlap (within 20% tolerance)
        for s_cost in source_costs:
            s_val = self._parse_cost(s_cost['value'])
            for t_cost in target_costs:
                t_val = self._parse_cost(t_cost['value'])
                
                if s_val and t_val:
                    diff_pct = abs(s_val - t_val) / max(s_val, t_val)
                    if diff_pct < 0.2:  # Within 20%
                        evidence.append(f"Cost validation: {s_cost['value']} ~= {t_cost['value']}")
                        validation_score += 0.3
        
        # Extract equipment from both
        source_equip = set([e['value'] for e in source.entities if e['type'] == 'equipment'])
        target_equip = set([e['value'] for e in target.entities if e['type'] == 'equipment'])
        
        # Equipment overlap
        common_equip = source_equip.intersection(target_equip)
        if common_equip:
            evidence.extend([f"Both mention: {eq}" for eq in common_equip])
            validation_score += 0.1 * len(common_equip)
        
        # Extract pain points from both
        source_pain = set([e['value'] for e in source.entities if e['type'] == 'pain_point'])
        target_pain = set([e['value'] for e in target.entities if e['type'] == 'pain_point'])
        
        # Pain overlap
        common_pain = source_pain.intersection(target_pain)
        if common_pain:
            evidence.extend([f"Shared pain: {p}" for p in common_pain])
            validation_score += 0.15 * len(common_pain)
        
        # If sufficient validation, create edge
        if validation_score >= 0.3 and evidence:
            edge = Edge(
                source=source.person,
                target=target.person,
                edge_type='validates',
                weight=min(1.0, validation_score),
                evidence=evidence
            )
            self.edges.append(edge)
            self.graph.add_edge(
                source.person,
                target.person,
                type='validates',
                weight=edge.weight,
                evidence=evidence
            )
    
    def _check_contradiction_edge(self, source: Test RunNode, target: Test RunNode):
        """Check if target contradicts source"""
        evidence = []
        contradiction_score = 0.0
        
        # Check for validation conflicts
        source_val = [e for e in source.entities if e['type'] == 'validation']
        target_val = [e for e in target.entities if e['type'] == 'validation']
        
        for s_v in source_val:
            if 'VALIDATED' in s_v['value']:
                for t_v in target_val:
                    if 'INVALIDATED' in t_v['value'] or 'pivot' in t_v['value'].lower():
                        evidence.append(f"Conflict: {source.person} validates, {target.person} invalidates")
                        contradiction_score += 0.8
        
        # Check for cost conflicts (>50% difference)
        source_costs = [e for e in source.entities if e['type'] == 'cost']
        target_costs = [e for e in target.entities if e['type'] == 'cost']
        
        for s_cost in source_costs:
            s_val = self._parse_cost(s_cost['value'])
            for t_cost in target_costs:
                t_val = self._parse_cost(t_cost['value'])
                
                if s_val and t_val:
                    diff_pct = abs(s_val - t_val) / max(s_val, t_val)
                    if diff_pct > 0.5:  # >50% difference
                        evidence.append(f"Cost conflict: {s_cost['value']} vs {t_cost['value']}")
                        contradiction_score += 0.4
        
        if contradiction_score >= 0.4 and evidence:
            edge = Edge(
                source=source.person,
                target=target.person,
                edge_type='contradicts',
                weight=min(1.0, contradiction_score),
                evidence=evidence
            )
            self.edges.append(edge)
            self.graph.add_edge(
                source.person,
                target.person,
                type='contradicts',
                weight=edge.weight,
                evidence=evidence,
                color='red'
            )
    
    def _check_extension_edge(self, source: Test RunNode, target: Test RunNode):
        """Check if target extends/elaborates on source"""
        # Extension occurs when:
        # 1. Same cube position (similar role/pain)
        # 2. Target has more entities (more detail)
        # 3. Target mentions source's entities + new ones
        
        if source.get_cube_position() == target.get_cube_position():
            source_entity_set = set([e['value'] for e in source.entities])
            target_entity_set = set([e['value'] for e in target.entities])
            
            # Target contains source + more
            if source_entity_set.issubset(target_entity_set) and len(target_entity_set) > len(source_entity_set):
                new_entities = target_entity_set - source_entity_set
                evidence = [f"Adds detail: {e}" for e in list(new_entities)[:3]]
                
                edge = Edge(
                    source=source.person,
                    target=target.person,
                    edge_type='extends',
                    weight=0.6,
                    evidence=evidence
                )
                self.edges.append(edge)
                self.graph.add_edge(
                    source.person,
                    target.person,
                    type='extends',
                    weight=edge.weight,
                    evidence=evidence
                )
    
    def _check_duplicate_edge(self, source: Test RunNode, target: Test RunNode):
        """Check if same company/person tested multiple times"""
        if source.company == target.company and source.company != "":
            evidence = [f"Same company: {source.company}"]
            
            edge = Edge(
                source=source.person,
                target=target.person,
                edge_type='duplicates',
                weight=0.9,
                evidence=evidence
            )
            self.edges.append(edge)
            self.graph.add_edge(
                source.person,
                target.person,
                type='duplicates',
                weight=edge.weight,
                evidence=evidence
            )
    
    def _parse_cost(self, cost_str: str) -> float:
        """Parse cost string to float"""
        try:
            cost_str = cost_str.replace('$', '').replace(',', '')
            if 'k' in cost_str.lower():
                return float(cost_str.lower().replace('k', '')) * 1000
            elif 'm' in cost_str.lower():
                return float(cost_str.lower().replace('m', '')) * 1000000
            else:
                return float(cost_str)
        except:
            return 0.0
    
    def detect_synergy_communities(self) -> Dict[str, List[int]]:
        """
        Detect communities (clusters) using Louvain algorithm.
        These are groups of tests with high internal validation.
        """
        # Only use validation edges for community detection
        validation_graph = nx.Graph()
        for edge in self.edges:
            if edge.edge_type == 'validates':
                validation_graph.add_edge(edge.source, edge.target, weight=edge.weight)
        
        # Run community detection
        try:
            import community  # python-louvain
            communities = community.best_partition(validation_graph)
            
            # Group by community
            community_groups = defaultdict(list)
            for node, comm_id in communities.items():
                community_groups[f"Community_{comm_id}"].append(node)
            
            return dict(community_groups)
        except ImportError:
            # Fallback: Simple connected components
            communities = {}
            for i, component in enumerate(nx.connected_components(validation_graph)):
                communities[f"Community_{i}"] = list(component)
            return communities
    
    def calculate_test_run_authority(self) -> Dict[str, float]:
        """
        Calculate authority score for each test using PageRank.
        Test Runs that are validated by many others have higher authority.
        """
        # Run PageRank on validation subgraph
        validation_graph = self.graph.copy()
        
        # Remove non-validation edges
        edges_to_remove = [(u, v) for u, v, d in validation_graph.edges(data=True) 
                          if d.get('type') != 'validates']
        validation_graph.remove_edges_from(edges_to_remove)
        
        if len(validation_graph.edges()) > 0:
            pagerank = nx.pagerank(validation_graph, weight='weight')
            return pagerank
        else:
            # No validation edges, equal authority
            return {n: 1.0 / len(self.nodes) for n in self.nodes.keys()}
    
    def get_contradiction_report(self) -> List[Dict]:
        """Get all contradictions that need resolution"""
        contradictions = []
        
        for edge in self.edges:
            if edge.edge_type == 'contradicts':
                source_node = self.nodes[edge.source]
                target_node = self.nodes[edge.target]
                
                contradictions.append({
                    'source': f"#{edge.source}: {source_node.person} ({source_node.company})",
                    'target': f"#{edge.target}: {target_node.person} ({target_node.company})",
                    'severity': edge.weight,
                    'evidence': edge.evidence
                })
        
        return sorted(contradictions, key=lambda x: x['severity'], reverse=True)
    
    def export_graph(self, filepath: str):
        """Export graph to JSON for visualization"""
        data = {
            'nodes': [
                {
                    'id': num,
                    'script_name': node.person,
                    'source_version': node.company,
                    'cube_position': node.get_cube_position(),
                    'entity_count': len(node.entities)
                }
                for num, node in self.nodes.items()
            ],
            'edges': [edge.to_dict() for edge in self.edges],
            'communities': self.detect_synergy_communities(),
            'authority_scores': self.calculate_test_run_authority(),
            'contradictions': self.get_contradiction_report()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_graphml(self, filepath: str):
        """Export as GraphML for Gephi/Cytoscape visualization"""
        nx.write_graphml(self.graph, filepath)

    # ── Orchestrator API wrappers ──────────────────────────────
    def build(self, test_runs: list, entity_dicts: list):
        """Build graph from test_run dicts and entity dicts.
        Called by GenesisOrchestrator.run_full_analysis()."""
        # Group entities by source test_run
        from collections import defaultdict
        entities_by_source = defaultdict(list)
        for ed in entity_dicts:
            src = ed.get('source', ed.get('source_test_run', 0))
            entities_by_source[src].append(ed)

        for iv in test_runs:
            num = iv.get('test_num', 0)
            person = iv.get('script_name', '')
            if not person:
                continue
            self.add_test_run_node(
                test_num=num,
                person=person,
                company=iv.get('source_version', ''),
                q_layer=iv.get('q_layer', ''),
                q_object=iv.get('q_object', ''),
                q_stack=iv.get('q_stack', []),
                entities=entities_by_source.get(num, [])
            )

        self.build_edges()
        self._contradictions = self.get_contradiction_report()
        self._communities = self.detect_synergy_communities()

    def export_json(self, filepath: str):
        """Alias for export_graph — orchestrator calls this name."""
        self.export_graph(filepath)

    @property
    def contradictions(self):
        if not hasattr(self, '_contradictions'):
            self._contradictions = self.get_contradiction_report()
        return self._contradictions

    @property
    def communities(self):
        if not hasattr(self, '_communities'):
            self._communities = self.detect_synergy_communities()
        return self._communities


# Alias — genesis_brain/orchestrator.py imports GraphBuilder
GraphBuilder = TestGraphBuilder

# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test graph building — loads from actual test_run database
    import sys
    from pathlib import Path
    
    db_path = Path("FUSION_Projects/test_database.json")
    if not db_path.exists():
        print(f"No database at {db_path} — cannot test without real data.")
        sys.exit(1)
    
    with open(db_path, 'r') as f:
        db_data = json.load(f)
    
    builder = TestGraphBuilder()
    
    for iv in db_data.get('tests', []):
        if not iv.get('results', '').strip():
            continue
        entities = []
        import re
        costs = re.findall(r'\$[\d,]+(?:\.\d+)?(?:\s*[kKmM])?', iv.get('results', ''))
        for c in costs:
            entities.append({'type': 'cost', 'value': c, 'confidence': 0.85})
        
        builder.add_test_run_node(
            iv['script_name'], iv.get('script_name', ''), iv.get('source_version', ''),
            iv.get('q_layer', ''), iv.get('q_object', ''),
            iv.get('q_stack', []), entities
        )
    
    builder.build_edges()
    
    print(f"Built graph with {len(builder.nodes)} nodes and {len(builder.edges)} edges")
    print(f"\nEdge breakdown:")
    edge_types = defaultdict(int)
    for edge in builder.edges:
        edge_types[edge.edge_type] += 1
    for etype, count in edge_types.items():
        print(f"  {etype}: {count}")
    
    print(f"\nAuthority scores:")
    authority = builder.calculate_test_run_authority()
    for script_key in sorted(authority.keys()):
        print(f"  {script_key}: {authority[script_key]:.3f}")
    
    print(f"\nCommunities:")
    communities = builder.detect_synergy_communities()
    for comm_name, members in communities.items():
        print(f"  {comm_name}: {members}")
