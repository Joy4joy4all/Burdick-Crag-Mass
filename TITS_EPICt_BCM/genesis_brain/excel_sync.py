# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GENESIS BRAIN - EXCEL SYNC MODULE
==================================
Makes the Excel file the SINGLE SOURCE OF TRUTH.

When Excel changes → JSON regenerates → Pipeline recalculates

This module:
1. Reads GIBUSH_BCM_Test_Plan.xlsx (or any team's plan)
2. Extracts team config, value proposition, test targets
3. Generates test_database.json
4. Can watch for file changes and auto-sync

ANY BCM team can use this by providing their own Excel file.
"""

import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd


class ExcelSyncEngine:
    """
    Synchronizes Excel Test Plan → JSON Database
    
    The Excel file is the single source of truth.
    All downstream analysis derives from it.
    """
    
    def __init__(self, 
                 excel_path: Path = None,
                 output_dir: Path = None):
        """
        Args:
            excel_path: Path to FUSION Test Plan Excel file
            output_dir: Where to write test_database.json
        """
        self.excel_path = excel_path or Path("BCM_TESTS/GIBUSH_BCM_Test_Plan.xlsx")
        self.output_dir = output_dir or Path("BCM_TESTS")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Track file state for change detection
        self._last_hash = None
        self._last_modified = None
        
        # Parsed data
        self.team_config: Dict = {}
        self.value_proposition: Dict = {}
        self.tests: List[Dict] = []
        self.cube_matrix: Dict = {}
    
    def sync(self, force: bool = False) -> Dict:
        """
        Main sync operation: Excel → JSON
        
        Args:
            force: If True, sync even if file hasn't changed
            
        Returns:
            Dict with sync status and stats
        """
        if not self.excel_path.exists():
            return {
                'success': False,
                'error': f'Excel file not found: {self.excel_path}',
                'timestamp': datetime.now().isoformat()
            }
        
        # Check if file changed
        current_hash = self._get_file_hash()
        if not force and current_hash == self._last_hash:
            return {
                'success': True,
                'changed': False,
                'message': 'No changes detected',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Parse Excel
            self._parse_excel()
            
            # Generate JSON
            db_path = self._write_database()
            
            # Update tracking
            self._last_hash = current_hash
            self._last_modified = datetime.now()
            
            return {
                'success': True,
                'changed': True,
                'team': self.team_config.get('team_name', 'Unknown'),
                'tests_count': len(self.tests),
                'database_path': str(db_path),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_file_hash(self) -> str:
        """Get MD5 hash of Excel file for change detection"""
        with open(self.excel_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _parse_excel(self):
        """Parse Excel file into structured data"""
        df = pd.read_excel(self.excel_path, sheet_name=0, header=None)
        
        # --- TEAM CONFIG (Rows 0-2) ---
        self.team_config = {
            'team_name': self._extract_team_name(df.iloc[1, 0] if len(df) > 1 else ''),
            'substrate_class': self._clean_text(df.iloc[2, 0] if len(df) > 2 else ''),
            'source_file': str(self.excel_path),
            'last_sync': datetime.now().isoformat()
        }
        
        # --- VALUE PROPOSITION (Rows 4-7) ---
        self.value_proposition = {}
        vp_rows = {
            4: 'gap_we_fill',
            5: 'what_they_cant_do', 
            6: 'synergy_play',
            7: 'differentiation'
        }
        for row_idx, key in vp_rows.items():
            if len(df) > row_idx and pd.notna(df.iloc[row_idx, 2]):
                self.value_proposition[key] = self._clean_text(df.iloc[row_idx, 2])
        
        # --- TESTS (Rows 9+) ---
        self.tests = []
        for idx in range(9, len(df)):
            row = df.iloc[idx]
            
            # Skip empty rows
            if pd.isna(row[0]) and pd.isna(row[1]):
                continue
            
            # Parse test number
            test_num = self._parse_int(row[0])
            if test_num is None:
                continue
            
            test_entry = self._parse_test_row(test_num, row)
            if test_entry:
                self.tests.append(test_run)
        
        # --- CUBE MATRIX ---
        self.cube_matrix = self._generate_cube_matrix()
    
    def _extract_team_name(self, text: str) -> str:
        """Extract team name from 'Team: GIBUSH ...' format"""
        text = str(text) if text else ''
        if 'Team:' in text:
            return text.replace('Team:', '').strip()
        return text.strip() or 'Unknown Team'
    
    def _clean_text(self, text) -> str:
        """Clean and normalize text"""
        if pd.isna(text):
            return ''
        return str(text).strip()
    
    def _parse_int(self, value) -> Optional[int]:
        """Safely parse integer"""
        try:
            if pd.isna(value):
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _parse_test_row(self, test_num: int, row: pd.Series) -> Optional[Dict]:
        """Parse a single test row from Excel"""
        # Column mapping:
        # 0: Test #
        # 1: Name
        # 2: Title
        # 3: Role (customer type)
        # 4: Company
        # 5: Hypothesis/Context
        # 6: Questions
        
        name = self._clean_text(row[1]) if len(row) > 1 else ''
        title = self._clean_text(row[2]) if len(row) > 2 else ''
        role = self._clean_text(row[3]) if len(row) > 3 else ''
        company = self._clean_text(row[4]) if len(row) > 4 else ''
        hypothesis = self._clean_text(row[5]) if len(row) > 5 else ''
        questions = self._clean_text(row[6]) if len(row) > 6 else ''
        
        # Skip if no meaningful data
        if not name and not company:
            return None
        
        # Infer Q-Cube position from role/title
        q_layer, q_object, q_stack = self._infer_cube_position(role, title, hypothesis)
        
        return {
            'test_num': test_num,
            'date': '',  # Filled when test is run
            'script_name': name,
            'title': title,
            'source_version': company,
            'test_category': role,
            'hypotheses': hypothesis,
            'experiments': questions,  # Pre-planned questions
            'results': '',  # Filled after test
            'action_iterate': '',  # Filled after test
            'q_layer': q_layer,
            'q_object': q_object,
            'q_stack': q_stack,
            'synergy_score': 0.0,
            'status': 'planned'  # planned, scheduled, completed
        }
    
    def _infer_cube_position(self, role: str, title: str, hypothesis: str) -> Tuple[str, str, List[str]]:
        """
        Infer Q-Cube position from test metadata
        
        Q-Layer: L1 (Operator), L2 (Manager), L3 (Executive)
        Q-Object: OA (Upstream), OB (Transfer), OC (Downstream)
        Q-Stack: Sα (Cross-Mill), Sβ (Post-Investment), Sγ (Baseline), Sδ (Dual Impact)
        """
        role_lower = role.lower()
        title_lower = title.lower()
        hyp_lower = hypothesis.lower()
        
        # Q-Layer inference
        q_layer = 'L2'  # Default: Manager
        if any(kw in title_lower for kw in ['operator', 'tender', 'foreman', 'technician']):
            q_layer = 'L1'
        elif any(kw in title_lower for kw in ['president', 'vp', 'vice president', 'executive', 'director', 'ceo', 'owner']):
            q_layer = 'L3'
        elif any(kw in title_lower for kw in ['manager', 'superintendent', 'supervisor']):
            q_layer = 'L2'
        
        # Q-Object inference
        q_object = 'OC'  # Default: Downstream receiver
        if any(kw in hyp_lower for kw in ['supplier', 'chip mill', 'timber', 'forest', 'procurement']):
            q_object = 'OA'
        elif any(kw in hyp_lower for kw in ['blow line', 'transfer', 'transport', 'conveyor']):
            q_object = 'OB'
        elif any(kw in hyp_lower for kw in ['kraft', 'digester', 'pulp', 'tissue', 'paper']):
            q_object = 'OC'
        
        # Q-Stack inference (can be multiple)
        q_stack = []
        if any(kw in hyp_lower for kw in ['multiple', 'cross', 'all mills', 'industry', 'common']):
            q_stack.append('Sα')
        if any(kw in hyp_lower for kw in ['modern', 'upgrade', 'investment', 'billion', 'new equipment']):
            q_stack.append('Sβ')
        if any(kw in hyp_lower for kw in ['baseline', 'commissioning', 'new system']):
            q_stack.append('Sγ')
        if any(kw in hyp_lower for kw in ['both', 'dual', 'multiple product', 'tissue', 'kraft']):
            q_stack.append('Sδ')
        
        if not q_stack:
            q_stack = ['Sα']  # Default
        
        return q_layer, q_object, q_stack
    
    def _generate_cube_matrix(self) -> Dict:
        """Generate Q-Cube matrix mapping positions to tests"""
        matrix = {}
        
        for test_entry in self.tests:
            layer = test_entry.get('q_layer', 'L2')
            obj = test_entry.get('q_object', 'OC')
            stacks = test_entry.get('q_stack', ['Sα'])
            
            for stack in stacks:
                key = f"[{layer}, {obj}, {stack}]"
                if key not in matrix:
                    matrix[key] = []
                matrix[key].append(test_entry['test_num'])
        
        return matrix
    
    def _write_database(self) -> Path:
        """Write test database JSON"""
        db_data = {
            'team_config': self.team_config,
            'value_proposition': self.value_proposition,
            'tests': self.tests,
            'cube_matrix': self.cube_matrix,
            'metadata': {
                'source_file': str(self.excel_path),
                'generated_at': datetime.now().isoformat(),
                'test_count': len(self.tests),
                'version': '2.0'
            }
        }
        
        db_path = self.output_dir / 'test_database.json'
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, indent=2, ensure_ascii=False)
        
        return db_path
    
    def watch(self, interval: float = 2.0, callback=None):
        """
        Watch Excel file for changes and auto-sync
        
        Args:
            interval: Check interval in seconds
            callback: Optional function to call after sync (receives sync result)
        """
        print(f"Watching {self.excel_path} for changes (Ctrl+C to stop)...")
        print(f"Check interval: {interval}s")
        
        # Initial sync
        result = self.sync(force=True)
        print(f"Initial sync: {result.get('tests_count', 0)} tests loaded")
        if callback:
            callback(result)
        
        try:
            while True:
                time.sleep(interval)
                result = self.sync()
                
                if result.get('changed'):
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Excel changed - Synced {result.get('tests_count', 0)} test_runs")
                    if callback:
                        callback(result)
                        
        except KeyboardInterrupt:
            print("\nWatch stopped.")
    
    def get_test_run(self, test_num: int) -> Optional[Dict]:
        """Get single test_run by number"""
        for test_entry in self.tests:
            if test_entry.get('test_num') == test_num:
                return test_run
        return None
    
    def update_test_run_results(self, test_num: int, results: str, action: str):
        """
        Update test of results after running it.
        This writes back to JSON (not Excel - Excel is for planning).
        """
        for test_entry in self.tests:
            if test_entry.get('test_num') == test_num:
                test_entry['results'] = results
                test_entry['action_iterate'] = action
                test_entry['status'] = 'completed'
                test_entry['date'] = datetime.now().strftime('%Y-%m-%d')
                break
        
        self._write_database()


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Command-line interface for Excel sync"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync Excel Test Plan to JSON')
    parser.add_argument('--excel', '-e', type=str, 
                       default='BCM_TESTS/GIBUSH_BCM_Test_Plan.xlsx',
                       help='Path to Excel file')
    parser.add_argument('--output', '-o', type=str,
                       default='BCM_TESTS',
                       help='Output directory for JSON')
    parser.add_argument('--watch', '-w', action='store_true',
                       help='Watch for changes and auto-sync')
    parser.add_argument('--interval', '-i', type=float, default=2.0,
                       help='Watch interval in seconds')
    
    args = parser.parse_args()
    
    engine = ExcelSyncEngine(
        excel_path=Path(args.excel),
        output_dir=Path(args.output)
    )
    
    if args.watch:
        engine.watch(interval=args.interval)
    else:
        result = engine.sync(force=True)
        
        if result.get('success'):
            print("=" * 60)
            print("EXCEL SYNC COMPLETE")
            print("=" * 60)
            print(f"Team: {result.get('team', 'Unknown')}")
            print(f"Tests: {result.get('tests_count', 0)}")
            print(f"Output: {result.get('database_path', 'N/A')}")
        else:
            print(f"ERROR: {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    main()
