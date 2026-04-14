# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - RESONANCE VISUALIZER
=====================================
Generates sacred geometry visualizations showing test_run resonance, amplitude, and truth convergence.

Charts:
1. Merkabah Cube - 6-faced test_run profile with luminosity
2. Resonance Heatmap - Equipment x Authority with white-hot truth nodes
3. Temporal Ebb & Flow - Timeline showing pain accumulation vs acute events
4. Authority-Weighted Network - Who validates who, weighted by position
5. Truth Convergence Field - 3D space where tests cluster by resonance
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import seaborn as sns
from typing import Dict, List, Tuple
from collections import defaultdict
import json
from pathlib import Path


class ResonanceVisualizer:
    """
    Generate visualizations showing test_run resonance and truth amplitude.
    
    Not just pretty charts - these show WHERE THE TRUTH IS.
    """
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("./VISUALIZATIONS")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Color scheme - white = truth, darkness = gap
        self.truth_cmap = 'hot'  # White hot for high resonance
        self.gap_cmap = 'binary_r'  # Black for gaps
        
        plt.style.use('dark_background')  # Dark background makes white pop
    
    def plot_merkabah_cube(self, test_run: Dict, face_scores: Dict, filepath: str = None):
        """
        Plot 6-faced Merkabah cube showing test_run dimensional profile.
        
        Each face represents a dimension:
        - Authority (how senior)
        - Specificity (how detailed)
        - Pain (how much it hurts)
        - Validation (confirms others)
        - Actionability (clear next steps)
        - Completeness (full picture)
        
        Faces glow white when strong, dark when weak.
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Cube vertices
        vertices = np.array([
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # Bottom
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]       # Top
        ])
        
        # Define 6 faces with their dimension
        faces = [
            ([0, 1, 2, 3], 'authority', 'blue'),      # Bottom - Authority
            ([4, 5, 6, 7], 'specificity', 'green'),   # Top - Specificity
            ([0, 1, 5, 4], 'pain', 'red'),            # Front - Pain
            ([2, 3, 7, 6], 'validation', 'yellow'),   # Back - Validation
            ([0, 3, 7, 4], 'actionability', 'cyan'),  # Left - Actionability
            ([1, 2, 6, 5], 'completeness', 'magenta') # Right - Completeness
        ]
        
        # Plot each face with intensity based on score
        for face_vertices, dimension, base_color in faces:
            score = face_scores.get(dimension, 0.5)
            
            # Create face polygon
            face_coords = vertices[face_vertices]
            
            # Color intensity = score (white = 1.0, dark = 0.0)
            intensity = score
            face_color = (intensity, intensity, intensity, 0.7)  # Grayscale with alpha
            edge_color = (intensity, intensity, intensity, 1.0)
            
            face = Poly3DCollection([face_coords], alpha=0.7, facecolor=face_color, 
                                   edgecolor=edge_color, linewidth=2)
            ax.add_collection3d(face)
            
            # Add label at face center
            center = np.mean(face_coords, axis=0)
            ax.text(center[0], center[1], center[2], 
                   f'{dimension}\n{score:.2f}',
                   ha='center', va='center', fontsize=9, 
                   color='white' if score > 0.5 else 'gray',
                   weight='bold')
        
        # Set labels and title
        ax.set_xlabel('X', fontsize=10)
        ax.set_ylabel('Y', fontsize=10)
        ax.set_zlabel('Z', fontsize=10)
        
        title = f"Merkabah Cube - Test Run #{test_entry.get('test_num', '?')}: {test_entry.get('script_name', 'Unknown')}"
        ax.set_title(title, fontsize=14, weight='bold', color='white')
        
        # Set viewing angle
        ax.view_init(elev=20, azim=45)
        
        # Set limits
        ax.set_xlim([-1.5, 1.5])
        ax.set_ylim([-1.5, 1.5])
        ax.set_zlim([-1.5, 1.5])
        
        # Add overall resonance score
        avg_score = np.mean(list(face_scores.values()))
        fig.text(0.5, 0.02, f'Overall Resonance: {avg_score:.2f}', 
                ha='center', fontsize=12, color='white', weight='bold')
        
        if filepath:
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='black')
        else:
            plt.savefig(self.output_dir / f'merkabah_test_run_{test_entry.get("test_num", 0)}.png',
                       dpi=150, bbox_inches='tight', facecolor='black')
        
        plt.close()
    
    def plot_resonance_heatmap(self, equipment_data: Dict, authority_data: Dict, 
                               filepath: str = None):
        """
        Equipment x Authority heatmap showing where truth is hottest.
        
        Operators (L1) weighted 3x for equipment truth.
        White-hot nodes = validated, high-cost equipment damage.
        """
        # Extract equipment types and authority levels
        equipment_types = list(equipment_data.keys())
        authority_levels = ['L1: Operators', 'L2: Managers', 'L3: Executives']
        
        # Authority weights
        weights = {'L1': 3.0, 'L2': 1.5, 'L3': 1.0}
        
        # Build matrix
        matrix = np.zeros((len(authority_levels), len(equipment_types)))
        
        for i, auth in enumerate(['L1', 'L2', 'L3']):
            for j, equip in enumerate(equipment_types):
                # Get mentions from this authority level
                mentions = authority_data.get(auth, {}).get(equip, 0)
                
                # Get damage cost
                cost = equipment_data[equip].get('total_cost', 0)
                
                # Resonance = mentions x cost x authority_weight
                resonance = mentions * (cost / 100000) * weights[auth]  # Normalize cost
                matrix[i, j] = resonance
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Use 'hot' colormap - white is hottest truth
        sns.heatmap(matrix, annot=True, fmt='.1f', cmap='hot', 
                   xticklabels=equipment_types, yticklabels=authority_levels,
                   cbar_kws={'label': 'Resonance Amplitude'}, ax=ax,
                   linewidths=0.5, linecolor='gray')
        
        ax.set_title('RESONANCE HEATMAP: Equipment Damage x Authority Level\n'
                    'White = High Truth Amplitude (Validated by Operators)',
                    fontsize=14, weight='bold', pad=20)
        ax.set_xlabel('Equipment Type', fontsize=12, weight='bold')
        ax.set_ylabel('Authority Level (Weighted)', fontsize=12, weight='bold')
        
        # Add note
        fig.text(0.5, 0.02, 
                'Operator testimony weighted 3x (they run the equipment)\n'
                'White-hot nodes = validated, quantified equipment damage',
                ha='center', fontsize=10, style='italic', color='white')
        
        plt.tight_layout()
        
        if filepath:
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='black')
        else:
            plt.savefig(self.output_dir / 'resonance_heatmap.png',
                       dpi=150, bbox_inches='tight', facecolor='black')
        
        plt.close()
    
    def plot_ebb_flow_timeline(self, test_runs: List[Dict], filepath: str = None):
        """
        Temporal visualization: Ebb & Flow of discovery.
        
        Shows:
        - Pain accumulation (slow drowning - sunken cost)
        - Acute events (equipment squeals - crisis moments)
        - Golden ratio points where truth emerges
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
        
        # Sort tests by date/number
        sorted_tests = sorted(tests, key=lambda x: x.get('test_num', 0))
        
        # Extract data
        test_nums = [i.get('test_num', 0) for i in sorted_test_runs]
        
        # Pain amplitude (how loud they scream)
        pain_amplitudes = []
        for test_entry in sorted_test_runs:
            text = f"{test_entry.get('results', '')} {test_entry.get('action_iterate', '')}".lower()
            
            # Count pain indicators
            pain_score = 0
            pain_words = ['damage', 'fail', 'catastrophic', 'severe', 'critical', 
                         'disaster', 'emergency', 'crisis', 'impossible']
            for word in pain_words:
                pain_score += text.count(word) * 1.5
            
            # Cost mentions amplify pain
            pain_score += text.count('$') * 2
            
            pain_amplitudes.append(pain_score)
        
        # Validation strength (constructive interference)
        validation_strengths = []
        for i, test_run in enumerate(sorted_test_runs):
            # Simple: count how many previous tests mention similar keywords
            text = test_entry.get('results', '').lower()
            words = set(text.split())
            
            validation = 0
            for prev_test_run in sorted_test_runs[:i]:
                prev_text = prev_test_entry.get('results', '').lower()
                prev_words = set(prev_text.split())
                
                # Jaccard similarity
                overlap = len(words.intersection(prev_words))
                validation += overlap
            
            validation_strengths.append(validation)
        
        # Plot 1: Pain Accumulation (Ebb)
        ax1.fill_between(test_nums, 0, pain_amplitudes, alpha=0.6, color='red', label='Pain Amplitude')
        ax1.plot(test_nums, pain_amplitudes, 'o-', color='white', linewidth=2, markersize=8)
        
        # Mark acute events (spikes > 20)
        acute_threshold = np.mean(pain_amplitudes) + np.std(pain_amplitudes)
        for i, (num, pain) in enumerate(zip(test_nums, pain_amplitudes)):
            if pain > acute_threshold:
                ax1.axvline(num, color='yellow', linestyle='--', alpha=0.5)
                ax1.text(num, pain * 1.1, f'ACUTE\n{sorted_test_runs[i].get("script_name", "").split()[0]}',
                        ha='center', fontsize=8, color='yellow', weight='bold')
        
        ax1.set_ylabel('Pain Amplitude\n(Equipment Squealing)', fontsize=12, weight='bold')
        ax1.set_title('EBB: Pain Accumulation Over Time\n'
                     'Acute Events = Yellow (Crisis Moments)',
                     fontsize=14, weight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # Plot 2: Validation Strength (Flow)
        ax2.fill_between(test_nums, 0, validation_strengths, alpha=0.6, color='cyan', label='Validation Strength')
        ax2.plot(test_nums, validation_strengths, 'o-', color='white', linewidth=2, markersize=8)
        
        # Mark golden ratio points (    1.618)
        # Points where validation rate changes significantly
        if len(validation_strengths) > 3:
            diffs = np.diff(validation_strengths)
            phi_threshold = np.mean(diffs) + 1.618 * np.std(diffs)
            for i, diff in enumerate(diffs):
                if diff > phi_threshold:
                    num = test_nums[i+1]
                    ax2.axvline(num, color='gold', linestyle='--', alpha=0.7, linewidth=2)
                    ax2.text(num, validation_strengths[i+1] * 1.1, 
                            f' \nTRUTH\nEMERGES',
                            ha='center', fontsize=8, color='gold', weight='bold')
        
        ax2.set_xlabel('Test Run Number', fontsize=12, weight='bold')
        ax2.set_ylabel('Validation Strength\n(Constructive Interference)', fontsize=12, weight='bold')
        ax2.set_title('FLOW: Truth Convergence Over Time\n'
                     'Golden Ratio Points ( ) = Where Truth Emerges',
                     fontsize=14, weight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left')
        
        plt.tight_layout()
        
        if filepath:
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='black')
        else:
            plt.savefig(self.output_dir / 'ebb_flow_timeline.png',
                       dpi=150, bbox_inches='tight', facecolor='black')
        
        plt.close()
    
    def plot_authority_network(self, graph_data: Dict, filepath: str = None):
        """
        Network graph showing test_run relationships with authority weighting.
        
        Node size = Authority weight (Operators largest)
        Edge thickness = Validation strength
        Node color = Resonance amplitude (white = high)
        """
        try:
            import networkx as nx
        except ImportError:
            print("NetworkX required for network visualization")
            return
        
        # Build graph
        G = nx.DiGraph()
        
        # Add nodes
        for node in graph_data['nodes']:
            authority_level = node['cube_position'].split(',')[0].strip('[')
            
            # Authority weight for node size
            weights = {'L1': 3.0, 'L2': 1.5, 'L3': 1.0}
            auth_weight = weights.get(authority_level, 1.0)
            
            G.add_node(node['id'], 
                      person=node['script_name'],
                      authority=auth_weight,
                      entity_count=node['entity_count'])
        
        # Add edges (only validation edges)
        for edge in graph_data['edges']:
            if edge['type'] == 'validates':
                G.add_edge(edge['source'], edge['target'], 
                          weight=edge['weight'])
        
        # Layout
        fig, ax = plt.subplots(figsize=(16, 12))
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # Get authority scores for coloring
        authority_scores = graph_data.get('authority_scores', {})
        
        # Node sizes based on authority level
        node_sizes = [G.nodes[node]['authority'] * 1000 for node in G.nodes()]
        
        # Node colors based on authority score (resonance)
        node_colors = [authority_scores.get(str(node), 0.5) for node in G.nodes()]
        
        # Draw edges
        edges = G.edges()
        edge_weights = [G[u][v]['weight'] * 3 for u, v in edges]
        nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.4, 
                               edge_color='cyan', arrows=True, 
                               arrowsize=15, ax=ax)
        
        # Draw nodes
        nodes = nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                                       node_color=node_colors, cmap='hot',
                                       vmin=0, vmax=1, alpha=0.9, ax=ax)
        
        # Labels
        labels = {node: f"#{node}\n{G.nodes[node]['script_name'].split()[0]}" 
                 for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, 
                               font_color='white', font_weight='bold', ax=ax)
        
        # Add colorbar
        plt.colorbar(nodes, ax=ax, label='Authority Score (PageRank)', 
                    orientation='vertical', shrink=0.8)
        
        ax.set_title('AUTHORITY-WEIGHTED VALIDATION NETWORK\n'
                    'Node Size = Authority Level (Operators Largest)\n'
                    'Node Color = Resonance (White = High Authority)\n'
                    'Edge = Validation Strength',
                    fontsize=14, weight='bold', pad=20)
        ax.axis('off')
        
        # Legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', label='L1: Operators (3x weight)',
                      markerfacecolor='white', markersize=15),
            plt.Line2D([0], [0], marker='o', color='w', label='L2: Managers (1.5x weight)',
                      markerfacecolor='gray', markersize=12),
            plt.Line2D([0], [0], marker='o', color='w', label='L3: Executives (1x weight)',
                      markerfacecolor='darkgray', markersize=10)
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=10)
        
        plt.tight_layout()
        
        if filepath:
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='black')
        else:
            plt.savefig(self.output_dir / 'authority_network.png',
                       dpi=150, bbox_inches='tight', facecolor='black')
        
        plt.close()
    
    def plot_truth_convergence_3d(self, test_runs: List[Dict], 
                                  embeddings: np.ndarray = None,
                                  filepath: str = None):
        """
        3D space showing test_run clustering by resonance.
        
        Test Runs that validate each other cluster together.
        White clusters = high truth convergence.
        """
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # If embeddings provided, use them; otherwise generate simple coordinates
        if embeddings is not None and len(embeddings) == len(test_runs):
            # Use first 3 dimensions of embeddings
            coords = embeddings[:, :3]
        else:
            # Generate coordinates from Q-Cube position
            coords = []
            layer_map = {'L1': 0, 'L2': 1, 'L3': 2}
            object_map = {'OA': 0, 'OB': 1, 'OC': 2}
            stack_map = {'Sa': 0, 'Sb': 1, 'Sg': 2, 'Sd': 3}
            
            for test_entry in test_runs:
                pos = test_entry.get('cube_position', '[L2, OC, Sa]')
                # Parse position
                parts = pos.strip('[]').split(',')
                layer = layer_map.get(parts[0].strip(), 1)
                obj = object_map.get(parts[1].strip(), 1)
                stack = stack_map.get(parts[2].strip() if len(parts) > 2 else 'Sa', 0)
                
                # Add noise for separation
                coords.append([
                    layer + np.random.randn() * 0.2,
                    obj + np.random.randn() * 0.2,
                    stack + np.random.randn() * 0.2
                ])
            
            coords = np.array(coords)
        
        # Calculate resonance for each test (based on synergy score or entity count)
        resonances = []
        for test_entry in test_runs:
            score = test_entry.get('synergy_score', 0.5)
            if score == 0:
                # Fallback: use entity count as proxy
                text = f"{test_entry.get('results', '')}"
                score = min(1.0, len(text.split()) / 500)
            resonances.append(score)
        
        resonances = np.array(resonances)
        
        # Plot points
        scatter = ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2],
                           c=resonances, cmap='hot', s=200, alpha=0.8,
                           edgecolors='white', linewidth=1.5)
        
        # Add labels
        for i, test_run in enumerate(test_runs):
            ax.text(coords[i, 0], coords[i, 1], coords[i, 2],
                   f"#{test_entry.get('test_num', i+1)}",
                   fontsize=8, color='white', weight='bold')
        
        # Draw lines between close points (high resonance)
        for i in range(len(coords)):
            for j in range(i+1, len(coords)):
                dist = np.linalg.norm(coords[i] - coords[j])
                if dist < 1.0:  # Close in space = related
                    avg_resonance = (resonances[i] + resonances[j]) / 2
                    ax.plot([coords[i, 0], coords[j, 0]],
                           [coords[i, 1], coords[j, 1]],
                           [coords[i, 2], coords[j, 2]],
                           color='cyan', alpha=avg_resonance * 0.5, linewidth=1)
        
        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8, pad=0.1)
        cbar.set_label('Resonance Amplitude', fontsize=12, weight='bold')
        
        # Labels
        ax.set_xlabel('Q-Layer (Authority)', fontsize=11, weight='bold')
        ax.set_ylabel('Q-Object (Position)', fontsize=11, weight='bold')
        ax.set_zlabel('Q-Stack (Pain Type)', fontsize=11, weight='bold')
        
        ax.set_title('TRUTH CONVERGENCE FIELD (3D)\n'
                    'White Clusters = High Resonance (Validated Truth)\n'
                    'Lines = Related Test Runs',
                    fontsize=14, weight='bold', pad=20)
        
        # Set viewing angle
        ax.view_init(elev=20, azim=45)
        
        plt.tight_layout()
        
        if filepath:
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='black')
        else:
            plt.savefig(self.output_dir / 'truth_convergence_3d.png',
                       dpi=150, bbox_inches='tight', facecolor='black')
        
        plt.close()
    
    def generate_all_visualizations(self, genesis_data: Dict):
        """
        Generate complete visualization suite from Genesis output.
        """
        print("Generating sacred geometry visualizations...")
        
        # Load data
        tests = genesis_data.get('tests', [])
        graph_data = genesis_data.get('graph', {})
        
        if not test_runs:
            print("No test_run data found")
            return
        
        # 1. Merkabah cubes for top 3 test_runs
        print("  1/5 Generating Merkabah cubes...")
        for test_entry in test_runs[:3]:
            # Calculate face scores (simplified - would use real analysis)
            face_scores = {
                'authority': 0.8 if 'L1' in test_entry.get('cube_position', '') else 0.6,
                'specificity': min(1.0, len(test_entry.get('results', '').split()) / 300),
                'pain': 0.9 if '$' in test_entry.get('results', '') else 0.5,
                'validation': test_entry.get('synergy_score', 0.5),
                'actionability': 0.7,
                'completeness': 0.8
            }
            self.plot_merkabah_cube(test_run, face_scores)
        
        # 2. Resonance heatmap
        print("  2/5 Generating resonance heatmap...")
        # Extract equipment data from tests
        equipment_data = self._extract_equipment_data(test_runs)
        authority_data = self._extract_authority_data(test_runs)
        if equipment_data:
            self.plot_resonance_heatmap(equipment_data, authority_data)
        
        # 3. Ebb & Flow timeline
        print("  3/5 Generating ebb & flow timeline...")
        self.plot_ebb_flow_timeline(test_runs)
        
        # 4. Authority network
        print("  4/5 Generating authority network...")
        if graph_data:
            self.plot_authority_network(graph_data)
        
        # 5. Truth convergence 3D
        print("  5/5 Generating truth convergence field...")
        self.plot_truth_convergence_3d(test_runs)
        
        print(f"\nOK All visualizations saved to: {self.output_dir}")
    
    def _extract_equipment_data(self, test_runs: List[Dict]) -> Dict:
        """Extract equipment mentions and costs"""
        equipment = defaultdict(lambda: {'total_cost': 0, 'mentions': 0})
        
        equip_keywords = ['cts', 'screen', 'basket', 'digester', 'pump', 'roller', 
                         'washer', 'feeder', 'knotter', 'refiner']
        
        for test_entry in test_runs:
            text = test_entry.get('results', '').lower()
            for keyword in equip_keywords:
                if keyword in text:
                    equipment[keyword]['mentions'] += 1
                    
                    # Try to extract cost near keyword
                    import re
                    pattern = rf'{keyword}.*?\$[\d,]+'
                    matches = re.findall(pattern, text)
                    for match in matches:
                        cost_match = re.search(r'\$([\d,]+)', match)
                        if cost_match:
                            try:
                                cost = float(cost_match.group(1).replace(',', ''))
                                equipment[keyword]['total_cost'] += cost
                            except:
                                pass
        
        return dict(equipment)
    
    def _extract_authority_data(self, test_runs: List[Dict]) -> Dict:
        """Extract equipment mentions by authority level"""
        from collections import defaultdict
        
        authority_data = defaultdict(lambda: defaultdict(int))
        
        equip_keywords = ['cts', 'screen', 'basket', 'digester', 'pump', 'roller']
        
        for test_entry in test_runs:
            text = test_entry.get('results', '').lower()
            level = test_entry.get('q_layer', 'L2')
            
            for keyword in equip_keywords:
                if keyword in text:
                    authority_data[level][keyword] += 1
        
        return dict(authority_data)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Load Genesis output
    output_dir = Path("GENESIS_OUTPUT")
    
    if not output_dir.exists():
        print("Run genesis_main.py first to generate data")
        import sys
        sys.exit(1)
    
    # Load data
    with open(output_dir / "test_graph.json", 'r') as f:
        graph_data = json.load(f)
    
    with open(output_dir / "strategic_intelligence.json", 'r') as f:
        synthesis_data = json.load(f)
    
    # Load test_runs
    db_file = Path("BCM_TESTS/test_database.json")
    with open(db_file, 'r') as f:
        db_data = json.load(f)
    
    tests = db_data['tests']
    
    # Create visualizer
    viz = ResonanceVisualizer(output_dir=Path("VISUALIZATIONS"))
    
    # Generate all visualizations
    genesis_data = {
        'tests': tests,
        'graph': graph_data,
        'synthesis': synthesis_data
    }
    
    viz.generate_all_visualizations(genesis_data)
    
    print("\nOK Sacred geometry charts complete")
    print("  Check VISUALIZATIONS/ directory")
