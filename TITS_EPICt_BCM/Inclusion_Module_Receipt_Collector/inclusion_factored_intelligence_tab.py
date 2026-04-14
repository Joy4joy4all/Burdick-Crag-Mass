#!/usr/bin/env python3
"""
INCLUSION FACTORED INTELLIGENCE TAB
================================================================
PySide6 tab widget for fusion_interview_collector.py

Displays the CaaS Inclusion Pool Quantum Cubit analysis:
  - R&D Convergence Score (Fusion research ↔ Inclusion development)
  - VP-TRL Alignment Matrix (which VPs have development evidence at what TRL)
  - Reverse Cluster Analysis (inclusion observation clusters mapped to VPs)
  - R&D Gaps (VP asks with no dev / Dev with no VP)
  - Immulsion Validation (SaaS recipient confirmation)
  - Doctrine Compliance (safety first)

TRIAD: Fusion (R) + Inclusion (D) + Immulsion (Validation)

For all the industrial workers lost to preventable acts.
© 2026 Stephen J. Burdick Sr. — All Rights Reserved.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QFrame,
    QScrollArea, QHeaderView, QProgressBar, QSplitter,
    QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from datetime import datetime
from pathlib import Path


# ══════════════════════════════════════════════════════════════
# COLORS + STYLING
# ══════════════════════════════════════════════════════════════

_COLORS = {
    'bg': '#0a0a0a',
    'panel': '#111111',
    'border': '#333333',
    'text': '#CCCCCC',
    'gold': '#FFD700',
    'green': '#00FF00',
    'cyan': '#00FFFF',
    'red': '#FF4444',
    'pink': '#FF69B4',
    'purple': '#9933EA',
    'dim': '#666666',
}

_STATUS_COLORS = {
    'PRODUCTION': '#00FF00',
    'FIELD TEST': '#00FFFF',
    'PROTOTYPE': '#FFD700',
    'CONCEPT': '#FF69B4',
    'NO DEV': '#FF4444',
}

_VERDICT_COLORS = {
    'ALIGNED': '#00FF00',
    'WEAK': '#FFD700',
    'ORPHAN': '#FF4444',
}

_BASE_STYLE = f"""
    QWidget {{ background: {_COLORS['bg']}; color: {_COLORS['text']}; }}
    QGroupBox {{
        color: {_COLORS['gold']}; border: 1px solid {_COLORS['border']};
        padding-top: 18px; margin-top: 6px; font-weight: bold;
    }}
    QGroupBox::title {{ subcontrol-position: top left; padding: 2px 8px; }}
    QTableWidget {{
        background: {_COLORS['bg']}; color: {_COLORS['text']};
        gridline-color: {_COLORS['border']}; border: 1px solid {_COLORS['border']};
    }}
    QHeaderView::section {{
        background: #1a1a1a; color: {_COLORS['gold']};
        font-weight: bold; border: 1px solid {_COLORS['border']}; padding: 4px;
    }}
    QProgressBar {{
        background: #1a1a1a; border: 1px solid {_COLORS['border']};
        text-align: center; color: white; font-weight: bold;
    }}
    QProgressBar::chunk {{ background: {_COLORS['cyan']}; }}
    QPushButton {{
        background: #1B3B5E; color: {_COLORS['cyan']}; padding: 8px 16px;
        font-weight: bold; border: 1px solid {_COLORS['cyan']};
    }}
    QPushButton:hover {{ background: #2B4B6E; }}
"""


# ══════════════════════════════════════════════════════════════
# MAIN TAB WIDGET
# ══════════════════════════════════════════════════════════════

class InclusionFactoredIntelligenceTab(QWidget):
    """
    Tab widget showing Inclusion Factored Intelligence.
    Integrate into fusion_interview_collector.py tab widget.
    """

    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dashboard_data = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(_BASE_STYLE)
        main = QVBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)

        # ── HEADER ──
        header = QLabel(
            "⚛ INCLUSION FACTORED INTELLIGENCE\n"
            "   Twin Q-Cube: Fusion (Research) ↔ Inclusion (Development) ↔ Immulsion (Validation)"
        )
        header.setFont(QFont("Consolas", 13, QFont.Bold))
        header.setStyleSheet(f"color: {_COLORS['cyan']}; background: #001a2a; padding: 10px;")
        main.addWidget(header)

        # ── TOOLBAR ──
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("⟳ Refresh Intelligence")
        self.refresh_btn.clicked.connect(self._on_refresh)
        toolbar.addWidget(self.refresh_btn)

        self.convergence_bar = QProgressBar()
        self.convergence_bar.setRange(0, 100)
        self.convergence_bar.setValue(0)
        self.convergence_bar.setFormat("R&D Convergence: %v%")
        self.convergence_bar.setMinimumWidth(300)
        self.convergence_bar.setMaximumHeight(28)
        toolbar.addWidget(self.convergence_bar)

        self.stream_label = QLabel("F:0 | I:0 | M:0")
        self.stream_label.setFont(QFont("Consolas", 10))
        self.stream_label.setStyleSheet(f"color: {_COLORS['dim']};")
        toolbar.addWidget(self.stream_label)
        toolbar.addStretch()
        main.addLayout(toolbar)

        # ── CONVERGENCE LABEL ──
        self.convergence_label = QLabel("")
        self.convergence_label.setFont(QFont("Consolas", 10, QFont.Bold))
        self.convergence_label.setStyleSheet(f"color: {_COLORS['gold']}; padding: 4px;")
        main.addWidget(self.convergence_label)

        # ── SPLITTER: VP-TRL table | Clusters + Gaps ──
        splitter = QSplitter(Qt.Vertical)

        # TOP: VP-TRL Alignment Matrix
        vp_group = QGroupBox("VP-TRL ALIGNMENT MATRIX — Research Ask vs Development Evidence")
        vp_layout = QVBoxLayout(vp_group)

        self.vp_table = QTableWidget()
        self.vp_table.setColumnCount(8)
        self.vp_table.setHorizontalHeaderLabels([
            "Value Proposition", "Fusion %", "Inc. Obs", "TRL",
            "TRL Bar", "R&D Status", "Immulsion", "Gap?"
        ])
        self.vp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.vp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.vp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.vp_table.setMaximumHeight(250)
        vp_layout.addWidget(self.vp_table)
        splitter.addWidget(vp_group)

        # BOTTOM: Clusters + Gaps + Doctrine side by side
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)

        # Cluster table
        cluster_group = QGroupBox("REVERSE CLUSTER REGRESSION — Inclusion Topic ↔ VP Mapping")
        cl_layout = QVBoxLayout(cluster_group)
        self.cluster_table = QTableWidget()
        self.cluster_table.setColumnCount(5)
        self.cluster_table.setHorizontalHeaderLabels([
            "Keywords", "Entries", "Best VP", "Score", "Verdict"
        ])
        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cl_layout.addWidget(self.cluster_table)
        bottom_layout.addWidget(cluster_group, 3)

        # Gaps + Doctrine panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # R&D Gaps
        gap_group = QGroupBox("⚠ R&D GAPS")
        gap_group.setStyleSheet(
            f"QGroupBox {{ color: {_COLORS['red']}; border: 1px solid {_COLORS['red']}; "
            f"padding-top: 18px; }}"
        )
        gap_layout = QVBoxLayout(gap_group)
        self.gap_text = QTextEdit()
        self.gap_text.setReadOnly(True)
        self.gap_text.setFont(QFont("Consolas", 9))
        self.gap_text.setStyleSheet(
            f"background: #1a0a0a; color: {_COLORS['red']}; border: none;"
        )
        self.gap_text.setMaximumHeight(150)
        gap_layout.addWidget(self.gap_text)
        right_layout.addWidget(gap_group)

        # Doctrine check
        doc_group = QGroupBox("DOCTRINE COMPLIANCE")
        doc_group.setStyleSheet(
            f"QGroupBox {{ color: {_COLORS['green']}; border: 1px solid {_COLORS['green']}; "
            f"padding-top: 18px; }}"
        )
        doc_layout = QVBoxLayout(doc_group)
        self.doctrine_text = QLabel("")
        self.doctrine_text.setFont(QFont("Consolas", 9))
        self.doctrine_text.setWordWrap(True)
        self.doctrine_text.setStyleSheet(f"color: {_COLORS['text']}; padding: 4px;")
        doc_layout.addWidget(self.doctrine_text)
        right_layout.addWidget(doc_group)

        right_layout.addStretch()
        bottom_layout.addWidget(right_panel, 2)

        splitter.addWidget(bottom)
        main.addWidget(splitter)

    # ──────────────────────────────────────────
    # DATA LOADING
    # ──────────────────────────────────────────

    def update_dashboard(self, dashboard_data: dict):
        """
        Load computed dashboard data from InclusionCubitEngine.get_dashboard_data().
        Called by the collector after engine computes.
        """
        self._dashboard_data = dashboard_data
        conv = dashboard_data.get('convergence', {})

        # Convergence bar
        score = conv.get('convergence_score', 0)
        self.convergence_bar.setValue(int(score))
        if score >= 80:
            self.convergence_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {_COLORS['green']}; }}")
        elif score >= 50:
            self.convergence_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {_COLORS['cyan']}; }}")
        elif score >= 20:
            self.convergence_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {_COLORS['gold']}; }}")
        else:
            self.convergence_bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {_COLORS['red']}; }}")

        self.convergence_label.setText(conv.get('convergence_label', ''))

        # Stream counts
        sc = dashboard_data.get('stream_counts', {})
        self.stream_label.setText(
            f"Fusion: {sc.get('fusion', 0)} | "
            f"Inclusion: {sc.get('inclusion', 0)} | "
            f"Immulsion: {sc.get('immulsion', 0)}"
        )

        # VP-TRL table
        self._populate_vp_table(dashboard_data.get('vp_rows', []))

        # Cluster table
        self._populate_cluster_table(dashboard_data.get('cluster_summary', []))

        # Gaps
        gaps = conv.get('gaps', [])
        orphans = conv.get('orphans', [])
        gap_lines = []
        for g in gaps:
            gap_lines.append(f"▸ {g['vp']}:\n  {g['problem']}\n  → {g.get('action', '')}\n")
        for o in orphans:
            gap_lines.append(
                f"▸ ORPHAN: {', '.join(o.get('keywords', []))}\n"
                f"  Development work with no VP backing\n")
        self.gap_text.setText('\n'.join(gap_lines) if gap_lines else "No R&D gaps detected.")

        # Doctrine
        doc = conv.get('doctrine_check', {})
        doc_text = (
            f"Safety signals: {doc.get('safety_signals', 0)}\n"
            f"Urgent observations: {doc.get('urgent_observations', 0)}\n"
            f"Service requests: {doc.get('service_requests', 0)}\n\n"
            f"{doc.get('note', '')}"
        )
        self.doctrine_text.setText(doc_text)

    def _populate_vp_table(self, vp_rows: list):
        self.vp_table.setRowCount(len(vp_rows))
        for row, data in enumerate(vp_rows):
            # VP Label
            item = QTableWidgetItem(data['vp_label'])
            item.setFont(QFont("Consolas", 9, QFont.Bold))
            self.vp_table.setItem(row, 0, item)

            # Fusion %
            conf = data['fusion_confidence']
            item = QTableWidgetItem(f"{conf}%")
            if conf >= 80:
                item.setForeground(QColor(_COLORS['green']))
            elif conf >= 50:
                item.setForeground(QColor(_COLORS['gold']))
            else:
                item.setForeground(QColor(_COLORS['dim']))
            self.vp_table.setItem(row, 1, item)

            # Inclusion count
            self.vp_table.setItem(row, 2,
                QTableWidgetItem(str(data['inclusion_count'])))

            # TRL number
            trl = data['max_trl']
            item = QTableWidgetItem(str(trl) if trl > 0 else "—")
            self.vp_table.setItem(row, 3, item)

            # TRL bar
            bar = '█' * trl + '░' * (9 - trl)
            item = QTableWidgetItem(bar)
            item.setFont(QFont("Consolas", 9))
            color = _STATUS_COLORS.get(data['rd_status'], _COLORS['dim'])
            item.setForeground(QColor(color))
            self.vp_table.setItem(row, 4, item)

            # R&D Status
            item = QTableWidgetItem(data['rd_status'])
            item.setForeground(QColor(color))
            item.setFont(QFont("Consolas", 9, QFont.Bold))
            self.vp_table.setItem(row, 5, item)

            # Immulsion
            imm = data.get('immulsion_count', 0)
            item = QTableWidgetItem(str(imm) if imm > 0 else "—")
            if imm > 0:
                item.setForeground(QColor(_COLORS['purple']))
            self.vp_table.setItem(row, 6, item)

            # Gap indicator
            if data['fusion_confidence'] >= 50 and data['max_trl'] == 0:
                item = QTableWidgetItem("⚠ GAP")
                item.setForeground(QColor(_COLORS['red']))
                item.setFont(QFont("Consolas", 9, QFont.Bold))
            elif data['aligned']:
                item = QTableWidgetItem("✓")
                item.setForeground(QColor(_COLORS['green']))
            else:
                item = QTableWidgetItem("—")
            self.vp_table.setItem(row, 7, item)

    def _populate_cluster_table(self, clusters: list):
        self.cluster_table.setRowCount(len(clusters))
        for row, c in enumerate(clusters):
            self.cluster_table.setItem(row, 0,
                QTableWidgetItem(c.get('keywords', '')))
            self.cluster_table.setItem(row, 1,
                QTableWidgetItem(str(c.get('size', 0))))

            vp = c.get('best_vp', '').replace('_', ' ')
            self.cluster_table.setItem(row, 2, QTableWidgetItem(vp))

            score = c.get('score', 0)
            item = QTableWidgetItem(f"{score:.0%}")
            self.cluster_table.setItem(row, 3, item)

            verdict = c.get('verdict', '')
            item = QTableWidgetItem(verdict)
            color = _VERDICT_COLORS.get(verdict, _COLORS['dim'])
            item.setForeground(QColor(color))
            item.setFont(QFont("Consolas", 9, QFont.Bold))
            self.cluster_table.setItem(row, 4, item)

    def _on_refresh(self):
        """Request refresh from parent collector."""
        self.refresh_requested.emit()

    # ──────────────────────────────────────────
    # EMPTY STATE
    # ──────────────────────────────────────────

    def show_empty_state(self):
        """Show when no inclusion data exists yet."""
        self.convergence_bar.setValue(0)
        self.convergence_label.setText(
            "No inclusion data yet. Deploy a CaaS module and submit observations."
        )
        self.stream_label.setText("F:0 | I:0 | M:0")
        self.vp_table.setRowCount(0)
        self.cluster_table.setRowCount(0)
        self.gap_text.setText(
            "Deploy CaaS modules and click GIVE FEEDBACK\n"
            "to generate Inclusion intelligence.\n\n"
            "The TL, EL, and IM champion observations\n"
            "will populate this analysis automatically."
        )
        self.doctrine_text.setText(
            "THE PERSON is the highest priority.\n"
            "Safety signals must be addressed before VP advancement."
        )


# ══════════════════════════════════════════════════════════════
# FACTORY + INTEGRATION HELPER
# ══════════════════════════════════════════════════════════════

def create_inclusion_intelligence_tab(parent=None) -> InclusionFactoredIntelligenceTab:
    """Factory function for fusion_interview_collector.py integration."""
    return InclusionFactoredIntelligenceTab(parent)


def compute_and_update_tab(
    tab: InclusionFactoredIntelligenceTab,
    database,
    project_id: str,
):
    """
    Full compute cycle: load all 3 streams, run cubit engine, update tab.
    Call this from the collector's refresh cycle.
    
    Args:
        tab: The InclusionFactoredIntelligenceTab widget
        database: The Interview database object from the collector
        project_id: Active project ID (e.g. 'CHIP_BLOW_LINE')
    """
    try:
        from inclusion_cubit_engine import InclusionCubitEngine
    except ImportError:
        tab.show_empty_state()
        print("  [INCLUSION_TAB] inclusion_cubit_engine.py not found")
        return

    engine = InclusionCubitEngine()

    # ── Load Fusion data ──
    fusion_interviews = []
    intel_state = {}
    if database:
        try:
            all_interviews = [iv.to_dict() for iv in database.interviews.values()]
            fusion_interviews = [
                iv for iv in all_interviews
                if iv.get('source', 'FUSION') == 'FUSION'
                and iv.get('results')
                and '[PENDING' not in str(iv.get('results', ''))
            ]
        except Exception as e:
            print(f"  [INCLUSION_TAB] Error loading fusion data: {e}")

    # Build intelligence state from fusion interviews
    try:
        from interview_intelligence import InterviewIntelligence
        intel = InterviewIntelligence()
        intel.interviews = fusion_interviews
        intel_state = intel.calculate()
    except ImportError:
        pass

    engine.load_fusion_data(fusion_interviews, intel_state)

    # ── Load Inclusion data ──
    try:
        from Inclusion_Module_Receipt_Collector.inclusion_receipt import (
            get_inclusion_for_project
        )
        inclusion = get_inclusion_for_project(project_id)
        engine.load_inclusion_data(inclusion)
    except ImportError:
        try:
            from inclusion_receipt import get_inclusion_for_project
            inclusion = get_inclusion_for_project(project_id)
            engine.load_inclusion_data(inclusion)
        except ImportError:
            print("  [INCLUSION_TAB] inclusion_receipt.py not found")

    # ── Load Immulsion data ──
    try:
        from immulsion_receiver import get_immulsion_for_project
        immulsion = get_immulsion_for_project(project_id)
        engine.load_immulsion_data(immulsion)
    except ImportError:
        pass  # Immulsion is optional at this stage

    # ── Compute and update ──
    if engine.inclusion_entries or engine.fusion_interviews:
        dashboard = engine.get_dashboard_data()
        tab.update_dashboard(dashboard)
    else:
        tab.show_empty_state()
