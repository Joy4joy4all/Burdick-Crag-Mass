# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS WORKSTATION - INTEGRATED INTERFACE
===========================================
Professional workstation combining:
- Test Run data entry (left panel)
- Live 3D holographic dashboard (right panel / separate window)
- Real-time sync between test_run changes and visualization
- Bidirectional data flow

Built with PySide6 + Web integration
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWebEngineWidgets import QWebEngineView
import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess


class GenesisWorkstation(QMainWindow):
    """
    Integrated workstation for Genesis Brain.
    
    Left: Test Run collector
    Right: Live dashboard (embedded or separate window)
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("GENESIS WORKSTATION - Test Run Collection + Live Analysis")
        self.setGeometry(100, 100, 1800, 1000)
        
        # Paths
        self.db_file = Path("BCM_TESTS/test_database.json")
        self.output_dir = Path("GENESIS_OUTPUT")
        self.viz_dir = Path("VISUALIZATIONS")
        
        # Data
        self.tests = []
        self.current_test_run = None
        
        # UI
        self.setup_ui()
        self.load_data()
        
        # Auto-refresh dashboard every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(5000)  # 5 seconds
    
    def setup_ui(self):
        """Setup integrated UI"""
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout: Splitter for resizable panels
        main_layout = QVBoxLayout(central)
        
        # Toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Splitter: Test Run Collector | Dashboard
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT PANEL: Test Run Collector
        collector_panel = self.create_collector_panel()
        splitter.addWidget(collector_panel)
        
        # RIGHT PANEL: Dashboard (embedded web view)
        dashboard_panel = self.create_dashboard_panel()
        splitter.addWidget(dashboard_panel)
        
        # Set initial sizes (40% collector, 60% dashboard)
        splitter.setSizes([720, 1080])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready - 0 tests loaded")
    
    def create_toolbar(self):
        """Create top toolbar with sync controls"""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Title
        title = QLabel("🧠 GENESIS WORKSTATION")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f0;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Sync button
        sync_btn = QPushButton("⚡ RUN GENESIS")
        sync_btn.setStyleSheet("""
            QPushButton {
                background: #0a0a0a;
                color: #0f0;
                border: 2px solid #0f0;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0f0;
                color: #000;
            }
        """)
        sync_btn.clicked.connect(self.run_genesis_analysis)
        layout.addWidget(sync_btn)
        
        # Dashboard toggle
        dash_toggle = QPushButton("📊 DASHBOARD → NEW WINDOW")
        dash_toggle.clicked.connect(self.open_dashboard_external)
        layout.addWidget(dash_toggle)
        
        # Refresh
        refresh_btn = QPushButton("🔄 REFRESH")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        layout.addWidget(refresh_btn)
        
        return toolbar
    
    def create_collector_panel(self):
        """Create test_run collector panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Header
        header = QLabel("TEST COLLECTOR")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #1a1a1a;")
        layout.addWidget(header)
        
        # Test Run list
        list_label = QLabel("All Tests:")
        layout.addWidget(list_label)
        
        self.test_run_list = QListWidget()
        self.test_run_list.itemClicked.connect(self.on_test_run_selected)
        layout.addWidget(self.test_run_list)
        
        # Test Run entry form
        form_group = QGroupBox("New Test Run")
        form_layout = QFormLayout()
        
        self.person_input = QLineEdit()
        self.company_input = QLineEdit()
        self.layer_combo = QComboBox()
        self.layer_combo.addItems(["L1", "L2", "L3"])
        self.object_combo = QComboBox()
        self.object_combo.addItems(["OA", "OB", "OC"])
        
        self.results_input = QTextEdit()
        self.results_input.setMaximumHeight(150)
        
        form_layout.addRow("Person:", self.person_input)
        form_layout.addRow("Company:", self.company_input)
        form_layout.addRow("Q-Layer:", self.layer_combo)
        form_layout.addRow("Q-Object:", self.object_combo)
        form_layout.addRow("Results:", self.results_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ ADD TEST")
        add_btn.clicked.connect(self.add_test_run)
        btn_layout.addWidget(add_btn)
        
        save_btn = QPushButton("💾 SAVE ALL")
        save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        return panel
    
    def create_dashboard_panel(self):
        """Create embedded dashboard panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Header
        header = QLabel("LIVE GENESIS DASHBOARD")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background: #1a1a1a;")
        layout.addWidget(header)
        
        # Web view for dashboard
        self.dashboard_view = QWebEngineView()
        
        # Load dashboard HTML
        dashboard_html = self.viz_dir / "genesis_dashboard_integrated.html"
        if dashboard_html.exists():
            self.dashboard_view.setUrl(QUrl.fromLocalFile(str(dashboard_html.absolute())))
        else:
            # Placeholder
            self.dashboard_view.setHtml("""
                <html>
                <body style="background: #000; color: #0f0; font-family: monospace; text-align: center; padding-top: 200px;">
                    <h1>GENESIS DASHBOARD</h1>
                    <p>Run Genesis Analysis to generate dashboard</p>
                    <p>Click "⚡ RUN GENESIS" button above</p>
                </body>
                </html>
            """)
        
        layout.addWidget(self.dashboard_view)
        
        # Stats panel
        stats_panel = self.create_stats_panel()
        layout.addWidget(stats_panel)
        
        return panel
    
    def create_stats_panel(self):
        """Create live stats panel"""
        panel = QWidget()
        panel.setMaximumHeight(100)
        layout = QGridLayout(panel)
        
        # Stats labels
        self.stat_tests = QLabel("Tests: 0")
        self.stat_entities = QLabel("Entities: 0")
        self.stat_resonance = QLabel("Avg Resonance: 0.00")
        self.stat_circumpunct = QLabel("Circumpunct: ❌")
        
        for label in [self.stat_tests, self.stat_entities, self.stat_resonance, self.stat_circumpunct]:
            label.setStyleSheet("font-size: 11px; padding: 5px; background: #0a0a0a; border: 1px solid #0f0;")
        
        layout.addWidget(self.stat_tests, 0, 0)
        layout.addWidget(self.stat_entities, 0, 1)
        layout.addWidget(self.stat_resonance, 0, 2)
        layout.addWidget(self.stat_circumpunct, 0, 3)
        
        return panel
    
    def load_data(self):
        """Load test_run database"""
        if not self.db_file.exists():
            return
        
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        self.tests = data.get('tests', [])
        self.refresh_test_run_list()
        self.update_stats()
    
    def save_data(self):
        """Save test_run database"""
        self.db_file.parent.mkdir(exist_ok=True, parents=True)
        
        data = {'tests': self.tests}
        
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.statusBar().showMessage(f"Saved {len(self.tests)} test_runs", 3000)
        QMessageBox.information(self, "Saved", f"Saved {len(self.tests)} tests to database")
    
    def refresh_test_run_list(self):
        """Refresh test_run list widget"""
        self.test_run_list.clear()
        
        for test_entry in self.tests:
            item_text = f"#{test_entry.get('test_num', '?')}: {test_entry.get('script_name', 'Unknown')} ({test_entry.get('source_version', '')})"
            self.test_run_list.addItem(item_text)
    
    def on_test_run_selected(self, item):
        """Handle test_run selection from list"""
        index = self.test_run_list.row(item)
        if 0 <= index < len(self.tests):
            test_run = self.tests[index]
            
            # Load into form
            self.person_input.setText(test_entry.get('script_name', ''))
            self.company_input.setText(test_entry.get('source_version', ''))
            self.layer_combo.setCurrentText(test_entry.get('q_layer', 'L2'))
            self.object_combo.setCurrentText(test_entry.get('q_object', 'OC'))
            self.results_input.setPlainText(test_entry.get('results', ''))
            
            self.current_test_run = test_run
    
    def add_test_run(self):
        """Add new test_run"""
        new_test_run = {
            'test_num': len(self.tests) + 1,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'script_name': self.person_input.text(),
            'source_version': self.company_input.text(),
            'q_layer': self.layer_combo.currentText(),
            'q_object': self.object_combo.currentText(),
            'q_stack': ['Sa'],  # Default
            'results': self.results_input.toPlainText(),
            'synergy_score': 0.0
        }
        
        self.tests.append(new_test_run)
        self.refresh_test_run_list()
        self.update_stats()
        
        # Clear form
        self.person_input.clear()
        self.company_input.clear()
        self.results_input.clear()
        
        self.statusBar().showMessage(f"Added test_run #{new_test_entry['test_num']}", 3000)
    
    def run_genesis_analysis(self):
        """Run complete Genesis analysis pipeline"""
        if len(self.tests) == 0:
            QMessageBox.warning(self, "No Data", "Please add tests first")
            return
        
        # Save first
        self.save_data()
        
        # Show progress dialog
        progress = QProgressDialog("Running Genesis Analysis...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        
        try:
            # Run master genesis
            progress.setLabelText("Running Genesis pipeline...")
            progress.setValue(30)
            
            # Run as subprocess to avoid blocking
            result = subprocess.run(
                [sys.executable, "master_genesis.py"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            progress.setValue(90)
            
            if result.returncode == 0:
                progress.setValue(100)
                QMessageBox.information(self, "Success", "Genesis analysis complete!\n\nDashboard updated.")
                self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "Error", f"Genesis analysis failed:\n{result.stderr[:500]}")
        
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Timeout", "Analysis took too long - may still be running in background")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run analysis:\n{str(e)}")
        finally:
            progress.close()
    
    def refresh_dashboard(self):
        """Refresh embedded dashboard"""
        dashboard_html = self.viz_dir / "genesis_dashboard_integrated.html"
        
        if dashboard_html.exists():
            self.dashboard_view.reload()
            self.update_stats()
            self.statusBar().showMessage("Dashboard refreshed", 2000)
    
    def update_stats(self):
        """Update stats panel with latest data"""
        self.stat_tests.setText(f"Tests: {len(self.tests)}")
        
        # Load Genesis outputs if available
        try:
            entities_file = self.output_dir / "knowledge_entities.json"
            if entities_file.exists():
                with open(entities_file, 'r') as f:
                    entities = json.load(f)
                    self.stat_entities.setText(f"Entities: {len(entities.get('entities', []))}")
            
            objects_file = self.output_dir / "3d_objects.json"
            if objects_file.exists():
                with open(objects_file, 'r') as f:
                    objects = json.load(f)
                    if objects:
                        avg_res = sum(obj.get('resonance', 0) for obj in objects) / len(objects)
                        self.stat_resonance.setText(f"Avg Resonance: {avg_res:.2f}")
            
            circ_file = self.output_dir / "circumpunct_analysis.json"
            if circ_file.exists():
                with open(circ_file, 'r') as f:
                    circ = json.load(f)
                    if circ.get('achieved'):
                        self.stat_circumpunct.setText("Circumpunct: ✅")
                        self.stat_circumpunct.setStyleSheet("font-size: 11px; padding: 5px; background: #0a5000; border: 1px solid #0f0; color: #0ff;")
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def open_dashboard_external(self):
        """Open dashboard in external browser window"""
        dashboard_html = self.viz_dir / "genesis_dashboard_integrated.html"
        
        if dashboard_html.exists():
            import webbrowser
            webbrowser.open(f'file:///{dashboard_html.absolute()}')
        else:
            QMessageBox.warning(self, "Not Found", "Dashboard not generated yet.\nClick 'RUN GENESIS' first.")


def main():
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyle("Validation")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 10, 10))
    palette.setColor(QPalette.WindowText, QColor(0, 255, 0))
    palette.setColor(QPalette.Base, QColor(20, 20, 20))
    palette.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.Text, QColor(0, 255, 0))
    palette.setColor(QPalette.Button, QColor(10, 10, 10))
    palette.setColor(QPalette.ButtonText, QColor(0, 255, 0))
    app.setPalette(palette)
    
    workstation = GenesisWorkstation()
    workstation.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
