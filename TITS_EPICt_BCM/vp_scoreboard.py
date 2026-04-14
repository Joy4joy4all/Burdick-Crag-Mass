# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
VP SCOREBOARD - Value Proposition Validation Dashboard
=======================================================
PySide6 Widget for GIBUSH BCM Validation Test Collector

Real-time scoreboard showing:
- VP validation status across customer segments
- Evidence strength per value proposition claim
- Test Run coverage gaps
- Pivot recommendations
- Business model readiness score

Designed as Tab 9 drop-in for validation_test_collector.py

Architecture: PySide6 widget matching existing GIBUSH patterns
Author: GIBUSH AI Engineering Team
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QScrollArea,
    QFrame, QGridLayout, QPushButton, QComboBox, QTextEdit,
    QSplitter, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette

import numpy as np


# ============================================================================
# VALUE PROPOSITION DEFINITIONS
# ============================================================================

@dataclass
class ValueProposition:
    """A specific value proposition claim to validate"""
    vp_id: str
    claim: str
    target_segment: str  # Customer segment this applies to
    evidence_keywords: List[str]  # Keywords that indicate validation
    counter_keywords: List[str]  # Keywords that indicate invalidation
    supporting_test_runs: List[int] = None
    contradicting_test_runs: List[int] = None
    confidence: float = 0.0  # 0-100%
    status: str = "TESTING"  # TESTING, VALIDATED, INVALIDATED, PIVOT
    
    def __post_init__(self):
        if self.supporting_tests is None:
            self.supporting_tests = []
        if self.contradicting_tests is None:
            self.contradicting_tests = []


# BCM_SUBSTRATE Value Propositions
BCM_SUBSTRATE_VPS = [
    ValueProposition(
        vp_id="VP1",
        claim="Real-time contamination detection prevents $100K+ damage events",
        target_segment="Decision-Maker/Payer",
        evidence_keywords=["$100k", "$300k", "damage event", "prevented", "saved"],
        counter_keywords=["not worth", "too expensive", "wouldn't pay"]
    ),
    ValueProposition(
        vp_id="VP2",
        claim="3D acoustic triangulation is more accurate than existing methods",
        target_segment="Technical/Engineering",
        evidence_keywords=["accurate", "better than", "more precise", "3d", "triangulate"],
        counter_keywords=["doesn't work", "not accurate", "false positive"]
    ),
    ValueProposition(
        vp_id="VP3",
        claim="Sub-second response time enables diversion before damage",
        target_segment="User/Operator",
        evidence_keywords=["fast", "quick", "respond", "divert", "catch in time"],
        counter_keywords=["too slow", "already damaged", "not fast enough"]
    ),
    ValueProposition(
        vp_id="VP4",
        claim="ROI payback within 12 months from avoided damage",
        target_segment="Decision-Maker/Payer",
        evidence_keywords=["payback", "roi", "worth it", "pay for itself"],
        counter_keywords=["no roi", "not justified", "budget won't"]
    ),
    ValueProposition(
        vp_id="VP5",
        claim="Complements existing equipment (BTG, Voith) rather than replacing",
        target_segment="Technical/Engineering",
        evidence_keywords=["complement", "integrate", "work with", "btg", "voith"],
        counter_keywords=["replace", "conflict", "incompatible"]
    ),
    ValueProposition(
        vp_id="VP6",
        claim="Converts reactive maintenance to planned maintenance",
        target_segment="Maintenance Superintendent",
        evidence_keywords=["planned", "schedule", "predict", "prevent emergency"],
        counter_keywords=["still reactive", "emergency", "surprise"]
    ),
    ValueProposition(
        vp_id="VP7",
        claim="Digital contamination log enables vendor accountability",
        target_segment="Procurement/Buyer",
        evidence_keywords=["log", "track", "vendor", "accountability", "penalize"],
        counter_keywords=["can't prove", "no record", "vendor dispute"]
    ),
    ValueProposition(
        vp_id="VP8",
        claim="OEM integration (Andritz, Valmet) is preferred purchase channel",
        target_segment="Executive",
        evidence_keywords=["oem", "andritz", "valmet", "integrated", "bundled"],
        counter_keywords=["direct", "standalone", "not bundled"]
    ),
]

# BCM_NAVIGATION Value Propositions
BCM_NAVIGATION_VPS = [
    ValueProposition(
        vp_id="SVP1",
        claim="EPV (Exposure Probability Value) quantifies risk better than traditional metrics",
        target_segment="EHS Manager",
        evidence_keywords=["quantify", "measure risk", "better metric", "epv"],
        counter_keywords=["current metrics work", "don't need new"]
    ),
    ValueProposition(
        vp_id="SVP2",
        claim="Real-time H2S detection with <10 second response prevents exposure",
        target_segment="Safety Supervisor",
        evidence_keywords=["h2s", "fast response", "prevent exposure", "alarm"],
        counter_keywords=["false alarm", "too sensitive", "cry wolf"]
    ),
    ValueProposition(
        vp_id="SVP3",
        claim="RTLS personnel tracking improves emergency evacuation accountability",
        target_segment="Emergency Response",
        evidence_keywords=["rtls", "track", "muster", "account for", "evacuate"],
        counter_keywords=["privacy concern", "big brother", "won't wear"]
    ),
    ValueProposition(
        vp_id="SVP4",
        claim="Incident near-miss AI analysis predicts future accidents",
        target_segment="EHS Manager",
        evidence_keywords=["predict", "pattern", "near-miss", "prevent accident"],
        counter_keywords=["can't predict", "random", "not useful"]
    ),
    ValueProposition(
        vp_id="SVP5",
        claim="Contractor safety compliance monitoring reduces liability",
        target_segment="Plant Manager",
        evidence_keywords=["contractor", "compliance", "liability", "audit"],
        counter_keywords=["contractor's problem", "not our responsibility"]
    ),
    ValueProposition(
        vp_id="SVP6",
        claim="Parent/Child safety doctrine resonates with workforce",
        target_segment="All",
        evidence_keywords=["parent", "child", "family", "home safe", "resonate"],
        counter_keywords=["corny", "doesn't matter", "just work"]
    ),
]


# ============================================================================
# VP SCOREBOARD WIDGET
# ============================================================================

class VPScoreboardWidget(QWidget):
    """
    Value Proposition Validation Scoreboard Widget.
    
    Shows real-time VP validation status based on test evidence.
    Designed as Tab 9 for validation_test_collector.py.
    
    Signals:
        pivot_recommended: Emitted when evidence suggests a pivot
        vp_validated: Emitted when a VP reaches validation threshold
    """
    
    pivot_recommended = Signal(str, str)  # vp_id, recommendation
    vp_validated = Signal(str, float)  # vp_id, confidence
    
    # Validation thresholds
    VALIDATION_THRESHOLD = 75.0  # % confidence to mark validated
    INVALIDATION_THRESHOLD = 25.0  # % confidence to mark invalidated
    MIN_TESTS = 3  # Minimum tests to make determination
    
    def __init__(self, database=None, project: str = "BCM_SUBSTRATE", parent=None):
        """
        Initialize VP Scoreboard.
        
        Args:
            database: Test RunDatabase instance (from validation_test_collector)
            project: "BCM_SUBSTRATE" or "BCM_NAVIGATION"
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.database = database
        self.project = project
        self.value_propositions: Dict[str, ValueProposition] = {}
        
        # Initialize VPs based on project
        self._init_value_propositions()
        
        self.init_ui()
        
        # Initial refresh if database provided
        if database:
            self.refresh()
    
    def _init_value_propositions(self):
        """Initialize value propositions for current project"""
        vp_list = BCM_SUBSTRATE_VPS if self.project == "BCM_SUBSTRATE" else BCM_NAVIGATION_VPS
        
        for vp in vp_list:
            self.value_propositions[vp.vp_id] = ValueProposition(
                vp_id=vp.vp_id,
                claim=vp.claim,
                target_segment=vp.target_segment,
                evidence_keywords=vp.evidence_keywords.copy(),
                counter_keywords=vp.counter_keywords.copy()
            )
    
    def init_ui(self):
        """Build the scoreboard UI"""
        layout = QVBoxLayout()
        
        # Header with project selector
        header_layout = QHBoxLayout()
        
        title = QLabel(f"<h2>📊 Value Proposition Scoreboard</h2>")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Project selector
        project_label = QLabel("Project:")
        header_layout.addWidget(project_label)
        
        self.project_combo = QComboBox()
        self.project_combo.addItem("🔴 BCM_SUBSTRATE", "BCM_SUBSTRATE")
        self.project_combo.addItem("🟢 BCM_NAVIGATION", "BCM_NAVIGATION")
        self.project_combo.setCurrentIndex(0 if self.project == "BCM_SUBSTRATE" else 1)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        header_layout.addWidget(self.project_combo)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Overall readiness score
        readiness_group = QGroupBox("Business Model Readiness")
        readiness_layout = QHBoxLayout()
        
        self.readiness_score_label = QLabel("<h1>0%</h1>")
        self.readiness_score_label.setAlignment(Qt.AlignCenter)
        readiness_layout.addWidget(self.readiness_score_label)
        
        self.readiness_bar = QProgressBar()
        self.readiness_bar.setMinimum(0)
        self.readiness_bar.setMaximum(100)
        self.readiness_bar.setValue(0)
        self.readiness_bar.setTextVisible(True)
        self.readiness_bar.setFormat("%v% Ready")
        readiness_layout.addWidget(self.readiness_bar, stretch=2)
        
        self.tests_label = QLabel("0 tests analyzed")
        readiness_layout.addWidget(self.tests_label)
        
        readiness_group.setLayout(readiness_layout)
        layout.addWidget(readiness_group)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: VP Table
        vp_group = QGroupBox("Value Proposition Status")
        vp_layout = QVBoxLayout()
        
        self.vp_table = QTableWidget()
        self.vp_table.setColumnCount(5)
        self.vp_table.setHorizontalHeaderLabels([
            "VP", "Claim", "Confidence", "Evidence", "Status"
        ])
        self.vp_table.setColumnWidth(0, 50)
        self.vp_table.setColumnWidth(1, 350)
        self.vp_table.setColumnWidth(2, 100)
        self.vp_table.setColumnWidth(3, 80)
        self.vp_table.setColumnWidth(4, 100)
        self.vp_table.cellClicked.connect(self._on_vp_selected)
        
        vp_layout.addWidget(self.vp_table)
        vp_group.setLayout(vp_layout)
        splitter.addWidget(vp_group)
        
        # Right: Details panel
        details_group = QGroupBox("Evidence Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("Select a VP to see evidence details...")
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        splitter.addWidget(details_group)
        
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        
        # Bottom: Recommendations
        rec_group = QGroupBox("🎯 Recommendations")
        rec_layout = QVBoxLayout()
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setMaximumHeight(150)
        rec_layout.addWidget(self.recommendations_text)
        
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        self.setLayout(layout)
    
    def _on_project_changed(self, index: int):
        """Handle project selection change"""
        self.project = self.project_combo.currentData()
        self._init_value_propositions()
        self.refresh()
    
    def _on_vp_selected(self, row: int, col: int):
        """Handle VP row selection"""
        vp_id = self.vp_table.item(row, 0).text()
        self._show_vp_details(vp_id)
    
    def set_database(self, database):
        """Update database reference"""
        self.database = database
        self.refresh()
    
    def refresh(self):
        """Refresh scoreboard from database"""
        if not self.database:
            return
        
        # Reset VP states
        for vp in self.value_propositions.values():
            vp.supporting_tests = []
            vp.contradicting_tests = []
            vp.confidence = 0.0
            vp.status = "TESTING"
        
        # Analyze test_runs
        tests = self.database.tests if hasattr(self.database, 'tests') else []
        
        for test_entry in test_runs:
            self._analyze_test_run(test_run)
        
        # Calculate confidences and statuses
        self._calculate_confidences()
        
        # Update UI
        self._update_table()
        self._update_readiness()
        self._generate_recommendations()
        
        self.tests_label.setText(f"{len(tests)} tests analyzed")
    
    def _analyze_test_run(self, test_run):
        """Analyze single test_run for VP evidence"""
        # Get text to analyze
        results = test_run.results if hasattr(test_run, 'results') else test_entry.get('results', '')
        action = test_run.action_iterate if hasattr(test_run, 'action_iterate') else test_entry.get('action_iterate', '')
        test_run_person = test_run.person if hasattr(test_run, 'script_name') else test_entry.get('script_name', '')
        
        text = f"{results} {action}".lower()
        
        for vp in self.value_propositions.values():
            # Check for supporting evidence
            supports = any(kw.lower() in text for kw in vp.evidence_keywords)
            contradicts = any(kw.lower() in text for kw in vp.counter_keywords)
            
            if supports and not contradicts:
                if test_run_person not in vp.supporting_test_runs:
                    vp.supporting_tests.append(test_run_person)
            elif contradicts and not supports:
                if test_run_person not in vp.contradicting_test_runs:
                    vp.contradicting_tests.append(test_run_person)
    
    def _calculate_confidences(self):
        """Calculate confidence scores and statuses"""
        for vp in self.value_propositions.values():
            total = len(vp.supporting_tests) + len(vp.contradicting_tests)
            
            if total == 0:
                vp.confidence = 50.0  # Neutral
                vp.status = "NO DATA"
            else:
                # Confidence = % of supporting evidence
                vp.confidence = (len(vp.supporting_tests) / total) * 100
                
                # Determine status
                if total >= self.MIN_TESTS:
                    if vp.confidence >= self.VALIDATION_THRESHOLD:
                        vp.status = "✅ VALIDATED"
                        self.vp_validated.emit(vp.vp_id, vp.confidence)
                    elif vp.confidence <= self.INVALIDATION_THRESHOLD:
                        vp.status = "❌ INVALIDATED"
                    else:
                        vp.status = "🔄 TESTING"
                else:
                    vp.status = f"📊 TESTING ({total}/{self.MIN_TESTS})"
    
    def _update_table(self):
        """Update VP table with current data"""
        self.vp_table.setRowCount(len(self.value_propositions))
        
        for row, (vp_id, vp) in enumerate(self.value_propositions.items()):
            # VP ID
            self.vp_table.setItem(row, 0, QTableWidgetItem(vp_id))
            
            # Claim (truncated)
            claim_text = vp.claim[:60] + "..." if len(vp.claim) > 60 else vp.claim
            self.vp_table.setItem(row, 1, QTableWidgetItem(claim_text))
            
            # Confidence with progress bar style
            conf_item = QTableWidgetItem(f"{vp.confidence:.0f}%")
            if vp.confidence >= self.VALIDATION_THRESHOLD:
                conf_item.setBackground(QColor(200, 255, 200))  # Green
            elif vp.confidence <= self.INVALIDATION_THRESHOLD:
                conf_item.setBackground(QColor(255, 200, 200))  # Red
            else:
                conf_item.setBackground(QColor(255, 255, 200))  # Yellow
            self.vp_table.setItem(row, 2, conf_item)
            
            # Evidence count
            evidence = f"+{len(vp.supporting_tests)}/-{len(vp.contradicting_tests)}"
            self.vp_table.setItem(row, 3, QTableWidgetItem(evidence))
            
            # Status
            status_item = QTableWidgetItem(vp.status)
            if "VALIDATED" in vp.status:
                status_item.setForeground(QColor(0, 128, 0))
            elif "INVALIDATED" in vp.status:
                status_item.setForeground(QColor(200, 0, 0))
            self.vp_table.setItem(row, 4, status_item)
    
    def _update_readiness(self):
        """Calculate and display overall readiness"""
        validated_count = sum(1 for vp in self.value_propositions.values() if "VALIDATED" in vp.status)
        total = len(self.value_propositions)
        
        readiness = (validated_count / total) * 100 if total > 0 else 0
        
        self.readiness_bar.setValue(int(readiness))
        self.readiness_score_label.setText(f"<h1>{readiness:.0f}%</h1>")
        
        # Color code
        if readiness >= 75:
            self.readiness_bar.setStyleSheet("QProgressBar::chunk { background-color: #00aa00; }")
        elif readiness >= 50:
            self.readiness_bar.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
        else:
            self.readiness_bar.setStyleSheet("QProgressBar::chunk { background-color: #aa0000; }")
    
    def _show_vp_details(self, vp_id: str):
        """Show detailed evidence for selected VP"""
        vp = self.value_propositions.get(vp_id)
        if not vp:
            return
        
        details = []
        details.append(f"<h3>{vp_id}: {vp.claim}</h3>")
        details.append(f"<p><b>Target Segment:</b> {vp.target_segment}</p>")
        details.append(f"<p><b>Confidence:</b> {vp.confidence:.1f}%</p>")
        details.append(f"<p><b>Status:</b> {vp.status}</p>")
        details.append("")
        
        # Supporting evidence
        details.append("<h4>✅ Supporting Evidence:</h4>")
        if vp.supporting_test_runs:
            for person_name in vp.supporting_test_runs:
                test_run = self._get_test_run_by_name(person_name)
                if test_run:
                    company = test_run.company if hasattr(test_run, 'source_version') else test_entry.get('source_version', '')
                    details.append(f"<p>• {person_name} ({company})</p>")
                else:
                    details.append(f"<p>• {person_name}</p>")
        else:
            details.append("<p><i>No supporting evidence yet</i></p>")
        
        # Contradicting evidence
        details.append("<h4>❌ Contradicting Evidence:</h4>")
        if vp.contradicting_test_runs:
            for person_name in vp.contradicting_test_runs:
                test_run = self._get_test_run_by_name(person_name)
                if test_run:
                    company = test_run.company if hasattr(test_run, 'source_version') else test_entry.get('source_version', '')
                    details.append(f"<p>• {person_name} ({company})</p>")
                else:
                    details.append(f"<p>• {person_name}</p>")
        else:
            details.append("<p><i>No contradicting evidence</i></p>")
        
        # Keywords
        details.append("<h4>🔍 Evidence Keywords:</h4>")
        details.append(f"<p><b>Supporting:</b> {', '.join(vp.evidence_keywords)}</p>")
        details.append(f"<p><b>Contradicting:</b> {', '.join(vp.counter_keywords)}</p>")
        
        self.details_text.setHtml("".join(details))
    
    def _get_test_run_by_name(self, person_name: str):
        """Get test_run by person name"""
        if not self.database or not person_name:
            return None
        
        tests = self.database.tests if hasattr(self.database, 'tests') else []
        pn = person_name.strip().lower()
        
        for test_entry in test_runs:
            name = test_run.person if hasattr(test_run, 'script_name') else test_entry.get('script_name', '')
            if name.strip().lower() == pn:
                return test_run
        
        return None
    
    def _generate_recommendations(self):
        """Generate strategic recommendations"""
        recs = []
        
        # Check for invalidated VPs (need pivot)
        invalidated = [vp for vp in self.value_propositions.values() if "INVALIDATED" in vp.status]
        if invalidated:
            recs.append("🚨 <b>PIVOT REQUIRED:</b>")
            for vp in invalidated:
                recs.append(f"   • {vp.vp_id}: '{vp.claim}' - Evidence contradicts this claim")
                self.pivot_recommended.emit(vp.vp_id, f"Evidence contradicts: {vp.claim}")
            recs.append("")
        
        # Check for VPs needing more data
        low_data = [vp for vp in self.value_propositions.values() 
                    if len(vp.supporting_tests) + len(vp.contradicting_tests) < self.MIN_TESTS]
        if low_data:
            recs.append("📊 <b>NEED MORE DATA:</b>")
            for vp in low_data:
                recs.append(f"   • {vp.vp_id}: Need {self.MIN_TESTS - len(vp.supporting_tests) - len(vp.contradicting_tests)} more test_runs")
            recs.append("")
        
        # Check for VPs close to validation
        almost = [vp for vp in self.value_propositions.values() 
                  if 60 <= vp.confidence < self.VALIDATION_THRESHOLD and "TESTING" in vp.status]
        if almost:
            recs.append("🎯 <b>ALMOST VALIDATED (60-75%):</b>")
            for vp in almost:
                recs.append(f"   • {vp.vp_id}: {vp.confidence:.0f}% - One or two more supporting tests could validate")
            recs.append("")
        
        # Celebrate validated VPs
        validated = [vp for vp in self.value_propositions.values() if "VALIDATED" in vp.status]
        if validated:
            recs.append("✅ <b>VALIDATED VALUE PROPOSITIONS:</b>")
            for vp in validated:
                recs.append(f"   • {vp.vp_id}: '{vp.claim[:50]}...'")
            recs.append("")
        
        # Overall recommendation
        readiness = len(validated) / len(self.value_propositions) * 100 if self.value_propositions else 0
        
        if readiness >= 75:
            recs.append("🚀 <b>READY FOR PITCH:</b> Strong evidence supports core value propositions")
        elif readiness >= 50:
            recs.append("📈 <b>MAKING PROGRESS:</b> Continue tests, focus on weak areas")
        else:
            recs.append("⚠️ <b>MORE DISCOVERY NEEDED:</b> Core hypotheses still unvalidated")
        
        self.recommendations_text.setHtml("<br>".join(recs))
    
    def get_validation_summary(self) -> Dict:
        """Get summary data for export"""
        return {
            "project": self.project,
            "timestamp": datetime.now().isoformat(),
            "readiness_percent": sum(1 for vp in self.value_propositions.values() if "VALIDATED" in vp.status) / len(self.value_propositions) * 100,
            "value_propositions": [
                {
                    "id": vp.vp_id,
                    "claim": vp.claim,
                    "confidence": vp.confidence,
                    "status": vp.status,
                    "supporting": len(vp.supporting_tests),
                    "contradicting": len(vp.contradicting_tests)
                }
                for vp in self.value_propositions.values()
            ]
        }


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test without database
    widget = VPScoreboardWidget(project="BCM_SUBSTRATE")
    widget.setWindowTitle("VP Scoreboard Test")
    widget.resize(1000, 700)
    widget.show()
    
    sys.exit(app.exec())
