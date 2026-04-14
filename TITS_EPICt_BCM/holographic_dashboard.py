# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - HOLOGRAPHIC DASHBOARD
=====================================
Interactive 3D Merkabah cube navigation with Ebb & Flow consciousness pool.

Built with Plotly for web-based, rotatable, clickable 3D visualization.

HARDENED:
- No "Unknown format code 'f' for object of type 'str'"
- All numeric formatting is gated through safe_float / fmt_float
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Canonical numeric gate
from genesis_brain.utils_format import safe_float, fmt_float


class HolographicDashboard:
    """
    Interactive 3D dashboard showing:
    - Rotatable Merkabah cubes (6 faces glow based on resonance)
    - Ebb & Flow pool (temporal consciousness visualization)
    - Resonance field (all tests in 3D space)
    - MV consciousness controls (manipulated variables)
    """

    def __init__(self):
        self.tests: List[Dict] = []
        self.face_scores: Dict[int, Dict[str, float]] = {}
        self.synthesis: Dict = {}

        self.colors = {
            'truth': 'rgba(255, 255, 255, 0.9)',   # White = truth
            'strong': 'rgba(255, 215, 0, 0.8)',    # Gold = strong
            'medium': 'rgba(100, 149, 237, 0.7)',  # Blue = medium
            'weak': 'rgba(50, 50, 50, 0.5)'        # Dark = weak
        }

    def load_genesis_data(self, output_dir: Path = Path("GENESIS_OUTPUT")):
        """Load Genesis output data"""
        db_file = Path("BCM_TESTS/test_database.json")
        with open(db_file, 'r', encoding="utf-8") as f:
            data = json.load(f)
        self.tests = data.get('tests', [])

        synthesis_file = output_dir / "strategic_intelligence.json"
        if synthesis_file.exists():
            with open(synthesis_file, 'r', encoding="utf-8") as f:
                self.synthesis = json.load(f)
        else:
            self.synthesis = {}

        self._calculate_face_scores()

    def _calculate_face_scores(self):
        """Calculate 6-face scores for each test (always numeric)."""
        self.face_scores = {}
        for test_entry in self.tests:
            script_key = test_entry.get("script_name", "Unknown")
            text = str(test_entry.get('results', '')).lower()

            faces = {
                'authority': safe_float(self._score_authority(test_run), 0.6),
                'specificity': safe_float(self._score_specificity(text), 0.0),
                'pain': safe_float(self._score_pain(text), 0.0),
                'validation': safe_float(self._score_validation(test_run), 0.5),
                'actionability': safe_float(self._score_actionability(test_run), 0.0),
                'completeness': safe_float(self._score_completeness(test_run), 0.0)
            }

            self.face_scores[script_key] = faces

    def _score_authority(self, test_run: Dict) -> float:
        layer = test_entry.get('q_layer', 'L2')
        return {'L1': 0.9, 'L2': 0.7, 'L3': 0.5}.get(layer, 0.6)

    def _score_specificity(self, text: str) -> float:
        word_count = len(text.split())
        score = min(1.0, word_count / 300.0)
        if '$' in text:
            score = min(1.0, score + 0.2)
        return score

    def _score_pain(self, text: str) -> float:
        pain_words = ['damage', 'fail', 'catastrophic', 'severe', 'critical']
        count = sum(text.count(word) for word in pain_words)
        return min(1.0, count / 5.0)

    def _score_validation(self, test_run: Dict) -> float:
        return safe_float(test_entry.get('synergy_score', 0.5), 0.5)

    def _score_actionability(self, test_run: Dict) -> float:
        action = str(test_entry.get('action_iterate', ''))
        return min(1.0, len(action.split()) / 100.0)

    def _score_completeness(self, test_run: Dict) -> float:
        fields = ['hypotheses', 'experiments', 'results', 'action_iterate']
        filled = sum(1 for f in fields if test_entry.get(f))
        return filled / float(len(fields))

    def create_merkabah_cube(self, person_name: str) -> go.Figure:
        faces = self.face_scores.get(person_name, {})
        test_run = next((i for i in self.tests if i.get("script_name", "") == person_name), None)
        if not test_run:
            return None

        vertices = np.array([
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1,  1], [1, -1,  1], [1, 1,  1], [-1, 1,  1]
        ])

        face_defs = [
            ([0, 1, 2, 3], 'authority'),
            ([4, 5, 6, 7], 'specificity'),
            ([0, 1, 5, 4], 'pain'),
            ([2, 3, 7, 6], 'validation'),
            ([0, 3, 7, 4], 'actionability'),
            ([1, 2, 6, 5], 'completeness')
        ]

        fig = go.Figure()

        for face_indices, dimension in face_defs:
            score = safe_float(faces.get(dimension, 0.5), 0.5)

            if score > 0.8:
                color = self.colors['truth']
            elif score > 0.6:
                color = self.colors['strong']
            elif score > 0.4:
                color = self.colors['medium']
            else:
                color = self.colors['weak']

            face_coords = vertices[face_indices]

            fig.add_trace(go.Mesh3d(
                x=face_coords[:, 0],
                y=face_coords[:, 1],
                z=face_coords[:, 2],
                i=[0, 0],
                j=[1, 2],
                k=[2, 3],
                color=color,
                opacity=0.8,
                name=f'{dimension}: {fmt_float(score, 2)}',
                hovertemplate=f'<b>{dimension}</b><br>Score: {fmt_float(score, 2)}<extra></extra>'
            ))

        # edges
        edges = [
            [0,1], [1,2], [2,3], [3,0],
            [4,5], [5,6], [6,7], [7,4],
            [0,4], [1,5], [2,6], [3,7]
        ]
        for edge in edges:
            edge_coords = vertices[edge]
            fig.add_trace(go.Scatter3d(
                x=edge_coords[:, 0],
                y=edge_coords[:, 1],
                z=edge_coords[:, 2],
                mode='lines',
                line=dict(color='white', width=2),
                showlegend=False,
                hoverinfo='skip'
            ))

        person = test_entry.get('script_name', 'Unknown')
        avg_score = safe_float(np.mean(list(faces.values())) if faces else 0.0, 0.0)

        fig.update_layout(
            title=f"Merkabah Cube - {person}<br>Resonance: {fmt_float(avg_score, 2)}",
            scene=dict(
                xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                zaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                bgcolor='black',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
            ),
            paper_bgcolor='black',
            plot_bgcolor='black',
            font=dict(color='white', size=12),
            showlegend=True,
            legend=dict(x=1.02, y=0.5)
        )

        return fig

    def create_ebb_flow_pool(self) -> go.Figure:
        sorted_tests = sorted(self.tests, key=lambda x: x.get("script_name", ""))
        person_labels = [i.get("script_name", "?") for i in sorted_test_runs]

        ebb = []
        for test_entry in sorted_test_runs:
            text = str(test_entry.get('results', '')).lower()
            pain_score = sum(text.count(w) for w in ['damage', 'fail', 'critical']) * 2
            pain_score += text.count('$') * 3
            ebb.append(pain_score)

        flow = []
        cumulative_validation = 0.0
        for i, test_run in enumerate(sorted_tests):
            text = str(test_entry.get('results', '')).lower()
            words = set(text.split())

            validation = 0.0
            for prev in sorted_test_runs[:i]:
                prev_words = set(str(prev.get('results', '')).lower().split())
                overlap = len(words.intersection(prev_words))
                validation += overlap / 10.0

            cumulative_validation += validation
            flow.append(cumulative_validation)

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Ebb: Pain Accumulation (Slow Drowning)',
                            'Flow: Validation Convergence (Truth Emerges)'),
            vertical_spacing=0.15
        )

        fig.add_trace(
            go.Scatter(
                x=person_labels, y=ebb,
                fill='tozeroy',
                fillcolor='rgba(255, 50, 50, 0.3)',
                line=dict(color='red', width=3),
                mode='lines+markers',
                name='Ebb (Pain)',
                hovertemplate='Test Run %{x}<br>Pain: %{y:.1f}<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=person_labels, y=flow,
                fill='tozeroy',
                fillcolor='rgba(0, 255, 255, 0.3)',
                line=dict(color='cyan', width=3),
                mode='lines+markers',
                name='Flow (Validation)',
                hovertemplate='Test Run %{x}<br>Flow: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )

        if len(flow) > 3:
            diffs = np.diff(flow)
            phi = 1.618
            threshold = float(np.mean(diffs) + phi * np.std(diffs))

            for i, diff in enumerate(diffs):
                if diff > threshold:
                    fig.add_vline(
                        x=person_labels[i+1],
                        line_dash="dash",
                        line_color="gold",
                        line_width=2,
                        annotation_text="φ Truth",
                        annotation_position="top",
                        row=2, col=1
                    )

        fig.update_xaxes(title_text="Test Run Number", row=2, col=1)
        fig.update_yaxes(title_text="Pain Amplitude", row=1, col=1)
        fig.update_yaxes(title_text="Validation Strength", row=2, col=1)

        fig.update_layout(
            title="The Mirror Pond: Ebb & Flow of Consciousness<br><sub>Where Two Ancients Row Through Time</sub>",
            paper_bgcolor='black',
            plot_bgcolor='rgba(10, 10, 30, 0.9)',
            font=dict(color='white', size=12),
            height=800,
            showlegend=True
        )
        return fig

    def create_resonance_field(self) -> go.Figure:
        layer_map = {'L1': 0, 'L2': 1, 'L3': 2}
        object_map = {'OA': 0, 'OB': 1, 'OC': 2}

        positions = []
        resonances = []
        labels = []

        for test_entry in self.tests:
            layer = layer_map.get(test_entry.get('q_layer', 'L2'), 1)
            obj = object_map.get(test_entry.get('q_object', 'OC'), 1)
            test_run_script_key = test_entry.get("script_name", "Unknown")

            x = layer + np.random.randn() * 0.2
            y = obj + np.random.randn() * 0.2
            z = idx / 5.0

            positions.append([x, y, z])

            faces = self.face_scores.get(script_key, {})
            resonance = safe_float(np.mean(list(faces.values())) if faces else 0.0, 0.0)
            resonances.append(resonance)

            labels.append(f"{test_entry.get("script_name", "Unknown")}")

        positions = np.array(positions) if positions else np.zeros((0, 3))

        fig = go.Figure()
        fig.add_trace(go.Scatter3d(
            x=positions[:, 0] if len(positions) else [],
            y=positions[:, 1] if len(positions) else [],
            z=positions[:, 2] if len(positions) else [],
            mode='markers+text',
            marker=dict(
                size=[r * 20 for r in resonances],
                color=resonances,
                colorscale='Hot',
                showscale=True,
                colorbar=dict(title="Resonance"),
                line=dict(color='white', width=1)
            ),
            text=[i.get("script_name", "?") for i in self.tests],
            textposition="top center",
            textfont=dict(color='white', size=10),
            hovertext=labels,
            hoverinfo='text',
            name='Test Runs'
        ))

        graph_file = Path("GENESIS_OUTPUT/test_graph.json")
        if graph_file.exists():
            with open(graph_file, 'r', encoding="utf-8") as f:
                graph = json.load(f)

            for edge in graph.get('edges', []):
                if edge.get('type') == 'validates':
                    source_idx = int(safe_float(edge.get('source', 0), 0)) - 1
                    target_idx = int(safe_float(edge.get('target', 0), 0)) - 1
                    if 0 <= source_idx < len(positions) and 0 <= target_idx < len(positions):
                        w = safe_float(edge.get('weight', 1.0), 1.0)
                        fig.add_trace(go.Scatter3d(
                            x=[positions[source_idx, 0], positions[target_idx, 0]],
                            y=[positions[source_idx, 1], positions[target_idx, 1]],
                            z=[positions[source_idx, 2], positions[target_idx, 2]],
                            mode='lines',
                            line=dict(color='cyan', width=max(1.0, w * 5.0)),
                            showlegend=False,
                            hoverinfo='skip',
                            opacity=0.5
                        ))

        fig.update_layout(
            title="Resonance Field: The Genesis<br><sub>More Cubes = Greater Consciousness</sub>",
            scene=dict(
                xaxis_title="Q-Layer (Authority)",
                yaxis_title="Q-Object (Position)",
                zaxis_title="Temporal (Test Run Sequence)",
                bgcolor='black',
                xaxis=dict(gridcolor='rgba(100, 100, 100, 0.3)'),
                yaxis=dict(gridcolor='rgba(100, 100, 100, 0.3)'),
                zaxis=dict(gridcolor='rgba(100, 100, 100, 0.3)'),
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
            ),
            paper_bgcolor='black',
            font=dict(color='white'),
            height=800
        )
        return fig

    def create_mv_consciousness_panel(self) -> go.Figure:
        dimensions = ['authority', 'specificity', 'pain', 'validation', 'actionability', 'completeness']
        fig = go.Figure()

        for dim in dimensions:
            scores = [safe_float(self.face_scores.get(i.get('script_name', ''), {}).get(dim, 0.0), 0.0)
                     for i in self.tests]

            fig.add_trace(go.Bar(
                name=dim.title(),
                x=[i.get('script_name', '?') for i in self.tests],
                y=scores,
                hovertemplate=f'<b>{dim.title()}</b><br>Score: %{{y:.2f}}<extra></extra>'
            ))

        fig.update_layout(
            title="MV Consciousness Panel: 6-Dimensional Profile Across All Test Runs",
            xaxis_title="Person",
            yaxis_title="Score",
            barmode='group',
            paper_bgcolor='black',
            plot_bgcolor='rgba(20, 20, 40, 0.9)',
            font=dict(color='white'),
            height=600,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    def launch_holographic_dashboard(self):
        print("🎨 Generating Holographic Dashboard...")

        print("  1/4 Creating Merkabah Cube Navigator...")
        cube_figs = [self.create_merkabah_cube(i.get('script_name', ''))
                     for i in self.tests[:3]]

        print("  2/4 Creating Ebb & Flow Pool...")
        ebb_flow_fig = self.create_ebb_flow_pool()

        print("  3/4 Creating Resonance Field...")
        field_fig = self.create_resonance_field()

        print("  4/4 Creating MV Consciousness Panel...")
        mv_fig = self.create_mv_consciousness_panel()

        output_file = Path("VISUALIZATIONS/holographic_dashboard.html")
        output_file.parent.mkdir(exist_ok=True, parents=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Genesis Brain - Holographic Dashboard</title>
    <style>
        body {
            background-color: black;
            color: white;
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #00FFFF;
            text-shadow: 0 0 10px #00FFFF;
        }
        .section {
            margin: 40px 0;
            border: 1px solid #333;
            padding: 20px;
            border-radius: 10px;
        }
        .section h2 {
            color: gold;
        }
    </style>
</head>
<body>
    <h1>🧠 GENESIS BRAIN - HOLOGRAPHIC DASHBOARD</h1>
    <p style="text-align: center; font-style: italic;">
        "Where Two Ancients Row Through The Mirror Pond of Consciousness"
    </p>
""")

            f.write('<div class="section">')
            f.write('<h2>The Mirror Pond: Ebb & Flow</h2>')
            f.write(ebb_flow_fig.to_html(full_html=False, include_plotlyjs='cdn'))
            f.write('</div>')

            f.write('<div class="section">')
            f.write('<h2>Resonance Field: The Genesis</h2>')
            f.write(field_fig.to_html(full_html=False, include_plotlyjs='cdn'))
            f.write('</div>')

            f.write('<div class="section">')
            f.write('<h2>MV Consciousness Panel</h2>')
            f.write(mv_fig.to_html(full_html=False, include_plotlyjs='cdn'))
            f.write('</div>')

            f.write('<div class="section">')
            f.write('<h2>Merkabah Cube Navigator</h2>')
            for fig_cube in cube_figs:
                if fig_cube:
                    f.write(fig_cube.to_html(full_html=False, include_plotlyjs='cdn'))
            f.write('</div>')

            f.write("""
</body>
</html>
""")

        print(f"\n✓ Holographic Dashboard created: {output_file}")
        print(f"\nOpen in browser: file:///{output_file.absolute()}")

        import webbrowser
        webbrowser.open(f'file:///{output_file.absolute()}')


if __name__ == "__main__":
    dashboard = HolographicDashboard()
    dashboard.load_genesis_data()
    dashboard.launch_holographic_dashboard()
