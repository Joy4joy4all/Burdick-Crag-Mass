# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
TEST RECONCILER — Data Integrity for the Intelligence Triad
================================================================
Location: C:\\TITS\\TITS_GIBUSH_AISOS_SPINE\\TITS_GIBUSH_AISOS_SPINE_EPIC\\test_reconciler.py

PROBLEM:
  An test_run leaves footprints in 6+ locations. The existing doc_reader removal
  only cleans 2 of them (change_log.json + tested/*.docx). The Test Run object
  persists in test_database.json, AI reports linger, Q-Cube references remain,
  and counts drift out of sync.

FOOTPRINT MAP (what this reconciler manages):
  ┌─────────────────────────────────────────────────────────────────────┐
  │ # │ Location                          │ Written By                 │
  ├───┼───────────────────────────────────┼────────────────────────────┤
  │ 1 │ test_database.json           │ Test RunDatabase.save()   │
  │   │   └─ test_runs[]                 │                            │
  │   │   └─ cube_matrix{}                │                            │
  │ 2 │ change_log.json                   │ Test RunMover.log_change  │
  │ 3 │ tested/*.docx                │ Test RunMover.move_to_*   │
  │ 4 │ _BCM_generated_report/*.txt        │ ReportGenerator.generate   │
  │ 5 │ _BCM_generated_report/summary*.json│ ReportGenerator.gen_json   │
  │ 6 │ genesis_output/ (references)      │ Genesis pipeline           │
  └───┴───────────────────────────────────┴────────────────────────────┘

DUPLICATES CAN ENTER VIA:
  - _load_deck_files() scanning same deck twice
  - _on_doc_reader_processed() reprocessing same packet
  - Manual Test RunEntryWidget with same test_num
  - _rescan_completed_packets() on re-run

HIERARCHY:
  THE PERSON > TITS > GIBUSH > AISOS/SPINE > CaaS/SaaS > HONUS

For all the industrial workers lost to preventable acts.
© 2026 Stephen J. Burdick Sr. — All Rights Reserved.
"""

import json
import re
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set


# ══════════════════════════════════════════════════════════════
# BRAIN ENGINE IMPORTS (optional — graceful fallback)
# ══════════════════════════════════════════════════════════════

try:
    from hypothesis_engine import HypothesisEngine, EVIDENCE_STRENGTH_RULES
    _HAS_HYPOTHESIS_ENGINE = True
except ImportError:
    _HAS_HYPOTHESIS_ENGINE = False

try:
    from qcube_config import QCubeEngine, heavy_industry_config
    _HAS_QCUBE_ENGINE = True
except ImportError:
    _HAS_QCUBE_ENGINE = False


# ══════════════════════════════════════════════════════════════
# PATH RESOLUTION — matches validation_test_collector.py
# ══════════════════════════════════════════════════════════════

try:
    from project_paths import (
        BCM_ROOT, get_project_dir, get_tested_dir,
        get_bcm_report_dir, get_inclusion_log, list_deployed_projects,
    )
    _PATHS_AVAILABLE = True
except ImportError:
    _PATHS_AVAILABLE = False
    _TITS_ROOT = Path(r"C:\TITS\TITS_GIBUSH_AISOS_SPINE")
    _EPIC_ROOT = _TITS_ROOT / "TITS_GIBUSH_AISOS_SPINE_EPIC"
    BCM_ROOT = _EPIC_ROOT / "BCM_TESTS"

    def get_project_dir(pid):
        return BCM_ROOT / pid

    def get_tested_dir(pid):
        return get_project_dir(pid) / "tested"

    def get_bcm_report_dir(pid):
        return get_project_dir(pid) / "_BCM_generated_report"

    def get_inclusion_log(pid):
        return get_project_dir(pid) / "inclusion_log.json"

    def list_deployed_projects():
        if not BCM_ROOT.exists():
            return []
        return sorted([
            d.name for d in BCM_ROOT.iterdir()
            if d.is_dir() and not d.name.startswith(('.', '_'))
        ])


# ══════════════════════════════════════════════════════════════
# AUDIT FINDING — one discrepancy or issue detected
# ══════════════════════════════════════════════════════════════

class AuditFinding:
    """Single issue found during reconciliation audit."""

    DUPLICATE = "DUPLICATE"
    ORPHAN_FILE = "ORPHAN_FILE"
    ORPHAN_REPORT = "ORPHAN_REPORT"
    GHOST_DB_ENTRY = "GHOST_DB_ENTRY"
    GHOST_CHANGELOG = "GHOST_CHANGELOG"
    COUNT_MISMATCH = "COUNT_MISMATCH"
    MISSING_FILE = "MISSING_FILE"

    def __init__(self, finding_type: str, test_num: int,
                 person: str, detail: str, severity: str = "WARN"):
        self.finding_type = finding_type
        self.test_num = test_num
        self.person = person
        self.detail = detail
        self.severity = severity  # INFO, WARN, ERROR
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'type': self.finding_type,
            'test_num': self.test_num,
            'script_name': self.person,
            'detail': self.detail,
            'severity': self.severity,
            'timestamp': self.timestamp,
        }

    def __repr__(self):
        return f"[{self.severity}] #{self.test_num} {self.person}: {self.finding_type} — {self.detail}"


# ══════════════════════════════════════════════════════════════
# TEST RECONCILER
# ══════════════════════════════════════════════════════════════

class Test RunReconciler:
    """
    Ensures data integrity across all test_run storage locations.

    Three operations:
      audit()     — Read-only scan. Returns list of AuditFindings.
      reconcile() — Fix all findings automatically (dedup, clean orphans).
      remove()    — Surgically remove one test_run from ALL 6 footprints.
    """

    def __init__(self, project_id: str, database=None):
        """
        Args:
            project_id: Active project ID (e.g. 'BCM_SUBSTRATE')
            database: Test RunDatabase instance (if None, loads from disk)
        """
        self.project_id = project_id
        self.project_dir = get_project_dir(project_id)
        self.db_file = BCM_ROOT / "test_database.json"
        self.change_log_path = self.project_dir / "change_log.json"
        self.tested_dir = get_tested_dir(project_id)
        self.report_dir = get_bcm_report_dir(project_id)
        self.inclusion_log_path = get_inclusion_log(project_id)

        self._database = database
        self._db_loaded_from_disk = False
        self._log: List[str] = []

    # ── Internal logging ──

    def _print(self, msg: str):
        self._log.append(msg)
        print(f"  [RECONCILER] {msg}")

    # ── Data access helpers ──

    def _load_database(self):
        """Load Test RunDatabase from disk if not provided."""
        if self._database is not None:
            return self._database

        if not self.db_file.exists():
            self._print(f"No database file: {self.db_file}")
            return None

        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Return raw dict list — we don't need the full class here
            self._db_loaded_from_disk = True
            return data
        except Exception as e:
            self._print(f"Error loading database: {e}")
            return None

    def _get_db_test_runs(self) -> List[Dict]:
        """Get test_run dicts from database (works with both object and raw)."""
        db = self._load_database()
        if db is None:
            return []

        # If it's the Test RunDatabase class
        if hasattr(db, 'tests'):
            tests = db.test_runs
            if isinstance(tests, list):
                return [
                    iv.to_dict() if hasattr(iv, 'to_dict') else iv
                    for iv in test_runs
                ]
            elif isinstance(tests, dict):
                return [
                    iv.to_dict() if hasattr(iv, 'to_dict') else iv
                    for iv in tests.values()
                ]
        # If it's raw JSON data
        elif isinstance(db, dict) and 'tests' in db:
            return db['tests']

        return []

    def _load_change_log(self) -> List[Dict]:
        """Load change_log.json entries."""
        if not self.change_log_path.exists():
            return []
        try:
            with open(self.change_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_change_log(self, entries: List[Dict]):
        """Save change_log.json."""
        with open(self.change_log_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

    def _get_tested_files(self) -> Dict[str, List[Path]]:
        """Map person name → list of .docx files in tested/ folder."""
        result: Dict[str, List[Path]] = {}
        if not self.tested_dir.exists():
            return result
        for docx in self.tested_dir.glob("*.docx"):
            # New format: Jeff_Custer_completed_20260402.docx
            # Old format: Test Run_26_Jeff_Custer_completed_20260402.docx
            stem = docx.stem
            # Strip old prefix if present
            stem = re.sub(r'^Test Run_\d+_', '', stem)
            # Strip timestamp suffix
            person = re.sub(r'_completed_\d+.*$', '', stem).replace('_', ' ').strip()
            if person:
                result.setdefault(person.lower(), []).append(docx)
        return result

    def _get_report_files(self) -> Dict[str, List[Path]]:
        """Map person name → list of report files in _BCM_generated_report/."""
        result: Dict[str, List[Path]] = {}
        if not self.report_dir.exists():
            return result
        for f in self.report_dir.iterdir():
            if not f.is_file():
                continue
            stem = f.stem
            # Pattern: AI_Report_Test Run_3_Name_20260223.txt → extract Name
            # Or: summary_3_20260223.json (no person name — skip)
            match = re.search(r'Test Run_\d+_(.+?)_\d{8}', stem)
            if match:
                person = match.group(1).replace('_', ' ').strip()
                result.setdefault(person.lower(), []).append(f)
        return result

    # ══════════════════════════════════════════════════════
    # AUDIT — Read-only scan for all discrepancies
    # ══════════════════════════════════════════════════════

    def audit(self) -> List[AuditFinding]:
        """
        Read-only scan of all 6 footprint locations.
        Returns list of findings. Does NOT modify anything.
        """
        findings: List[AuditFinding] = []
        self._print(f"AUDIT START — project: {self.project_id}")

        # ── 1. Load all data sources ──
        db_tests = self._get_db_test_runs()
        change_log = self._load_change_log()
        tested_files = self._get_tested_files()
        report_files = self._get_report_files()

        # Completed nums from change_log
        completed_entries = [
            e for e in change_log
            if e.get('action') == 'TEST_COMPLETED'
        ]
        completed_nums = {e.get('test_num', 0) for e in completed_entries}

        # DB test_run nums
        db_nums: Dict[int, List[Dict]] = {}
        for iv in db_test_runs:
            num = iv.get('test_num', 0)
            db_nums.setdefault(num, []).append(iv)

        self._print(f"  Database:      {len(db_tests)} test_run objects")
        self._print(f"  Change log:    {len(completed_entries)} COMPLETED entries")
        self._print(f"  Test Runed/:  {sum(len(v) for v in tested_files.values())} .docx files")
        self._print(f"  AI Reports:    {sum(len(v) for v in report_files.values())} report files")

        # ── 2. Check for DUPLICATES in database ──
        for num, copies in db_nums.items():
            if len(copies) > 1:
                persons = [c.get('script_name', '?') for c in copies]
                findings.append(AuditFinding(
                    AuditFinding.DUPLICATE, num, ', '.join(persons),
                    f"{len(copies)} copies in database: {persons}",
                    severity="ERROR",
                ))

        # ── 3. Check for DUPLICATE .docx files per test ──
        for num, files in tested_files.items():
            if len(files) > 1:
                findings.append(AuditFinding(
                    AuditFinding.DUPLICATE, num, "",
                    f"{len(files)} .docx files in tested/: {[f.name for f in files]}",
                    severity="WARN",
                ))

        # ── 4. ORPHAN FILES — .docx in tested/ with no database entry ──
        all_db_nums = set(db_nums.keys())
        for num, files in tested_files.items():
            if num not in all_db_nums:
                for f in files:
                    findings.append(AuditFinding(
                        AuditFinding.ORPHAN_FILE, num, "",
                        f"File {f.name} in tested/ but #{num} NOT in database",
                        severity="WARN",
                    ))

        # ── 5. ORPHAN REPORTS — AI report with no database entry ──
        for num, files in report_files.items():
            if num not in all_db_nums:
                for f in files:
                    findings.append(AuditFinding(
                        AuditFinding.ORPHAN_REPORT, num, "",
                        f"Report {f.name} exists but #{num} NOT in database",
                        severity="INFO",
                    ))

        # ── 6. GHOST DB ENTRIES — in database but no change_log completion ──
        # (Only for validation tests — sparks don't go through doc_reader)
        for num, copies in db_nums.items():
            source = copies[0].get('source', '')
            if source == 'validation' and num not in completed_nums:
                person = copies[0].get('script_name', '?')
                findings.append(AuditFinding(
                    AuditFinding.GHOST_DB_ENTRY, num, person,
                    f"Validation #{num} ({person}) in database but NO change_log completion",
                    severity="WARN",
                ))

        # ── 7. GHOST CHANGELOG — in change_log but not in database ──
        for entry in completed_entries:
            num = entry.get('test_num', 0)
            if num not in all_db_nums:
                person = entry.get('script_name', '?')
                findings.append(AuditFinding(
                    AuditFinding.GHOST_CHANGELOG, num, person,
                    f"change_log says #{num} ({person}) completed but NOT in database",
                    severity="WARN",
                ))

        # ── 8. MISSING FILES — change_log says completed but no .docx ──
        for entry in completed_entries:
            num = entry.get('test_num', 0)
            dest_file = entry.get('dest_file', '')
            if dest_file:
                expected = self.tested_dir / dest_file
                if not expected.exists():
                    findings.append(AuditFinding(
                        AuditFinding.MISSING_FILE, num,
                        entry.get('script_name', '?'),
                        f"change_log references {dest_file} but file missing from tested/",
                        severity="INFO",
                    ))

        # ── 9. COUNT MISMATCH — overall sanity check ──
        validation_db = [iv for iv in db_tests if iv.get('source') == 'validation']
        if len(validation_db) != len(completed_entries):
            findings.append(AuditFinding(
                AuditFinding.COUNT_MISMATCH, 0, "",
                f"Validation DB count ({len(validation_db)}) ≠ change_log completed count ({len(completed_entries)})",
                severity="WARN" if abs(len(validation_db) - len(completed_entries)) <= 2 else "ERROR",
            ))

        self._print(f"AUDIT COMPLETE — {len(findings)} findings")
        for f in findings:
            self._print(f"  {f}")

        return findings

    # ══════════════════════════════════════════════════════
    # REMOVE — Surgically remove one test_run from ALL footprints
    # ══════════════════════════════════════════════════════

    def remove(self, person_name: str, delete_files: bool = True) -> Dict:
        """
        Remove test_run from ALL 6 footprint locations.

        Args:
            person_name: The person name to remove
            delete_files: If True, delete physical .docx and report files

        Returns:
            Dict with removal details and what was cleaned.
        """
        person_lower = person_name.strip().lower()
        result = {
            'success': False,
            'script_name': person_name,
            'cleaned': [],
            'errors': [],
        }

        self._print(f"REMOVE {person_name} — scanning all footprints...")

        # ── 1. Remove from test_database.json ──
        db = self._load_database()
        db_removed = 0

        if db is not None and hasattr(db, 'tests'):
            # Working with Test RunDatabase object
            before = len(db.tests)
            db.tests = [
                iv for iv in db.test_runs
                if getattr(iv, 'script_name', '').strip().lower() != person_lower
            ]
            db_removed = before - len(db.tests)
            if db_removed > 0:
                result['script_name'] = person_name
                db.rebuild_cube_matrix()
                try:
                    db.save(self.db_file)
                    result['cleaned'].append(
                        f"database: removed {db_removed} entry(ies), cube matrix rebuilt"
                    )
                except Exception as e:
                    result['errors'].append(f"database save failed: {e}")
            self._database = db
        elif db is not None and isinstance(db, dict) and 'tests' in db:
            # Working with raw JSON
            before = len(db['tests'])
            db['tests'] = [
                iv for iv in db['tests']
                if iv.get('script_name', '').strip().lower() != person_lower
            ]
            db_removed = before - len(db['tests'])
            if db_removed > 0:
                result['script_name'] = person_name
                # Rebuild cube matrix from remaining test_runs
                db['cube_matrix'] = {}
                try:
                    with open(self.db_file, 'w', encoding='utf-8') as f:
                        json.dump(db, f, indent=2, ensure_ascii=False)
                    result['cleaned'].append(
                        f"database: removed {db_removed} entry(ies) from JSON"
                    )
                except Exception as e:
                    result['errors'].append(f"database save failed: {e}")

        if db_removed > 0:
            self._print(f"  ✓ Database: removed {db_removed} entry(ies)")
        else:
            self._print(f"  — Database: {person_name} not found")

        # ── 2. Remove from change_log.json ──
        change_log = self._load_change_log()
        cl_before = len(change_log)
        # Remove ALL entries referencing this person (completed + any others)
        change_log_kept = [
            e for e in change_log
            if e.get('script_name', '').strip().lower() != person_lower
        ]
        cl_removed = cl_before - len(change_log_kept)

        # Add REMOVAL audit entry
        change_log_kept.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'TEST_REMOVED',
            'script_name': person_name,
            'project': self.project_id,
            'removed_by': 'Test RunReconciler',
            'entries_removed': cl_removed,
            'files_deleted': [],  # Will be filled below
        })

        self._save_change_log(change_log_kept)
        if cl_removed > 0:
            result['cleaned'].append(f"change_log: removed {cl_removed} entry(ies)")
            self._print(f"  ✓ Change log: removed {cl_removed} entry(ies)")
        else:
            self._print(f"  — Change log: {person_name} not found")

        # ── 3. Delete tested/*.docx files ──
        files_deleted = []
        if delete_files:
            tested_files = self._get_tested_files()
            for docx_path in tested_files.get(person_lower, []):
                try:
                    docx_path.unlink()
                    files_deleted.append(str(docx_path.name))
                    self._print(f"  ✓ Deleted: {docx_path.name}")
                except Exception as e:
                    result['errors'].append(f"delete {docx_path.name}: {e}")

            if files_deleted:
                result['cleaned'].append(
                    f"tested/: deleted {len(files_deleted)} file(s)"
                )

        # ── 4. Delete _BCM_generated_report files ──
        reports_deleted = []
        if delete_files:
            report_files = self._get_report_files()
            for report_path in report_files.get(person_lower, []):
                try:
                    report_path.unlink()
                    reports_deleted.append(str(report_path.name))
                    self._print(f"  ✓ Deleted report: {report_path.name}")
                except Exception as e:
                    result['errors'].append(f"delete {report_path.name}: {e}")

            if reports_deleted:
                result['cleaned'].append(
                    f"_BCM_generated_report/: deleted {len(reports_deleted)} file(s)"
                )

        # Update the removal audit entry with deleted files
        for entry in change_log_kept:
            if (entry.get('action') == 'TEST_REMOVED'
                    and entry.get('script_name', '').strip().lower() == person_lower):
                entry['files_deleted'] = files_deleted + reports_deleted
                break
        self._save_change_log(change_log_kept)

        result['success'] = True
        result['files_deleted'] = files_deleted + reports_deleted

        self._print(
            f"REMOVE COMPLETE — {person_name}: "
            f"{len(result['cleaned'])} locations cleaned, "
            f"{len(files_deleted) + len(reports_deleted)} files deleted"
        )

        return result

    # ══════════════════════════════════════════════════════
    # DEDUPLICATE — Remove duplicate test_nums from database
    # ══════════════════════════════════════════════════════

    def deduplicate(self) -> Dict:
        """
        Remove duplicate test_run entries from the database.

        Strategy: Keep the RICHEST copy (most non-empty fields).
        For ties, keep the one with the latest date or longest results.

        Returns dict with dedup details.
        """
        result = {
            'duplicates_found': 0,
            'entries_removed': 0,
            'kept': [],
        }

        db = self._load_database()
        if db is None:
            return result

        # Get tests as dicts + track originals
        if hasattr(db, 'tests'):
            iv_list = db.test_runs
            is_object = True
        elif isinstance(db, dict) and 'tests' in db:
            iv_list = db['tests']
            is_object = False
        else:
            return result

        # Group by person name (case-insensitive)
        groups: Dict[str, List] = {}
        for iv in iv_list:
            person = (iv.person if is_object else iv.get('script_name', '')).strip().lower()
            groups.setdefault(person, []).append(iv)

        # Find duplicates and pick winner
        keep_set = []
        for script_key, copies in groups.items():
            if len(copies) <= 1:
                keep_set.append(copies[0])
                continue

            result['duplicates_found'] += 1

            # Score each copy by richness
            def _richness(iv):
                """Count non-empty meaningful fields."""
                if is_object:
                    d = iv.to_dict()
                else:
                    d = iv
                score = 0
                for key in ('results', 'experiments', 'hypotheses',
                            'action_iterate', 'script_name', 'source_version'):
                    val = d.get(key, '')
                    if val and str(val).strip():
                        score += 1
                        score += min(len(str(val)), 500) / 500  # length bonus
                # Equipment bonus
                equip = d.get('substrate_impacts', [])
                score += len(equip) * 0.5
                # Synergy score bonus
                score += float(d.get('synergy_score', 0)) * 2
                return score

            copies.sort(key=_richness, reverse=True)
            winner = copies[0]
            losers = copies[1:]

            winner_name = (
                winner.person if is_object
                else winner.get('script_name', '?')
            )
            result['kept'].append({
                'script_name': winner_name,
                'copies_removed': len(losers),
            })
            result['entries_removed'] += len(losers)

            self._print(
                f"  DEDUP {winner_name}: kept 1/{len(copies)} "
                f"(richness={_richness(winner):.1f})"
            )

            keep_set.append(winner)

        # Save deduplicated database
        if result['entries_removed'] > 0:
            if is_object:
                db.tests = keep_set
                db.rebuild_cube_matrix()
                try:
                    db.save(self.db_file)
                except Exception as e:
                    self._print(f"  ERROR saving deduped database: {e}")
            else:
                db['tests'] = keep_set
                db['cube_matrix'] = {}  # will be rebuilt on next load
                try:
                    with open(self.db_file, 'w', encoding='utf-8') as f:
                        json.dump(db, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    self._print(f"  ERROR saving deduped database: {e}")

            self._print(
                f"DEDUP COMPLETE — {result['duplicates_found']} duplicate groups, "
                f"{result['entries_removed']} entries removed"
            )

        return result

    # ══════════════════════════════════════════════════════
    # CLEAN ORPHANS — Remove files with no database backing
    # ══════════════════════════════════════════════════════

    def clean_orphans(self, dry_run: bool = True) -> Dict:
        """
        Find and optionally delete orphaned files.

        Orphans: .docx or reports that reference test_run numbers
        not present in the database.

        Args:
            dry_run: If True, only report. If False, delete files.

        Returns dict with orphan details.
        """
        result = {
            'orphan_docx': [],
            'orphan_reports': [],
            'deleted': [],
        }

        db_nums = {
            iv.get('test_num', 0)
            for iv in self._get_db_test_runs()
        }

        # Orphan .docx
        tested_files = self._get_tested_files()
        for num, files in tested_files.items():
            if num not in db_nums:
                for f in files:
                    result['orphan_docx'].append(f.name)
                    if not dry_run:
                        try:
                            f.unlink()
                            result['deleted'].append(f.name)
                            self._print(f"  DELETED orphan: {f.name}")
                        except Exception as e:
                            self._print(f"  ERROR deleting {f.name}: {e}")

        # Orphan reports
        report_files = self._get_report_files()
        for num, files in report_files.items():
            if num not in db_nums:
                for f in files:
                    result['orphan_reports'].append(f.name)
                    if not dry_run:
                        try:
                            f.unlink()
                            result['deleted'].append(f.name)
                        except Exception as e:
                            self._print(f"  ERROR deleting {f.name}: {e}")

        total = len(result['orphan_docx']) + len(result['orphan_reports'])
        mode = "DRY RUN" if dry_run else "CLEANED"
        self._print(f"ORPHANS [{mode}] — {total} orphaned files found")

        return result

    # ══════════════════════════════════════════════════════
    # RECONCILE — Full pass: audit + dedup + clean + verify
    # ══════════════════════════════════════════════════════

    def reconcile(self, fix: bool = False) -> Dict:
        """
        Full reconciliation pass.

        Args:
            fix: If True, actually fix problems. If False, audit only.

        Returns comprehensive report.
        """
        self._log.clear()
        self._print("=" * 60)
        self._print(f"RECONCILIATION — {self.project_id}")
        self._print(f"Mode: {'FIX' if fix else 'AUDIT ONLY'}")
        self._print("=" * 60)

        report = {
            'project_id': self.project_id,
            'timestamp': datetime.now().isoformat(),
            'mode': 'FIX' if fix else 'AUDIT',
            'audit_findings': [],
            'dedup_result': {},
            'orphan_result': {},
            'post_fix_findings': [],
        }

        # Step 1: Initial audit
        self._print("\n── STEP 1: AUDIT ──")
        findings = self.audit()
        report['audit_findings'] = [f.to_dict() for f in findings]

        if not fix:
            report['summary'] = self._build_summary(findings, {}, {})
            self._print(f"\n{report['summary']}")
            return report

        # Step 2: Deduplicate
        self._print("\n── STEP 2: DEDUPLICATE ──")
        has_dupes = any(f.finding_type == AuditFinding.DUPLICATE for f in findings)
        if has_dupes:
            report['dedup_result'] = self.deduplicate()
        else:
            self._print("  No duplicates found")

        # Step 3: Clean orphans
        self._print("\n── STEP 3: CLEAN ORPHANS ──")
        has_orphans = any(
            f.finding_type in (AuditFinding.ORPHAN_FILE, AuditFinding.ORPHAN_REPORT)
            for f in findings
        )
        if has_orphans:
            report['orphan_result'] = self.clean_orphans(dry_run=False)
        else:
            self._print("  No orphans found")

        # Step 4: Re-audit to verify fixes
        self._print("\n── STEP 4: POST-FIX VERIFICATION ──")
        post_findings = self.audit()
        report['post_fix_findings'] = [f.to_dict() for f in post_findings]

        report['summary'] = self._build_summary(
            findings, report['dedup_result'], report['orphan_result'],
            post_findings,
        )
        self._print(f"\n{report['summary']}")

        # Save audit report
        audit_path = self.project_dir / "reconciler_audit.json"
        try:
            with open(audit_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self._print(f"Audit saved: {audit_path}")
        except Exception as e:
            self._print(f"Error saving audit: {e}")

        return report

    def _build_summary(self, findings, dedup, orphans, post_findings=None) -> str:
        """Build human-readable summary string."""
        lines = ["", "═" * 50, "RECONCILIATION SUMMARY", "═" * 50]

        by_type = {}
        for f in findings:
            by_type.setdefault(f.finding_type, []).append(f)

        lines.append(f"  Findings:     {len(findings)}")
        for ftype, flist in sorted(by_type.items()):
            lines.append(f"    {ftype}: {len(flist)}")

        if dedup:
            lines.append(f"  Dedup:        {dedup.get('entries_removed', 0)} removed")
        if orphans:
            lines.append(
                f"  Orphans:      {len(orphans.get('deleted', []))} deleted"
            )

        if post_findings is not None:
            lines.append(f"  Post-fix:     {len(post_findings)} remaining findings")
            if len(post_findings) == 0:
                lines.append("  ✓ ALL CLEAN")
            else:
                for f in post_findings:
                    lines.append(f"    ⚠ {f}")

        lines.append("═" * 50)
        return "\n".join(lines)

    # ══════════════════════════════════════════════════════
    # VERIFY COUNTS — Quick count check without full audit
    # ══════════════════════════════════════════════════════

    def verify_counts(self) -> Dict:
        """
        Quick count verification across all locations.
        Returns dict with counts and whether they match.
        """
        db_tests = self._get_db_test_runs()
        change_log = self._load_change_log()
        tested_files = self._get_tested_files()

        sparks = [iv for iv in db_tests if iv.get('source', '') != 'validation']
        validation = [iv for iv in db_tests if iv.get('source', '') == 'validation']
        completed = [
            e for e in change_log
            if e.get('action') == 'TEST_COMPLETED'
        ]
        removed = [
            e for e in change_log
            if e.get('action') == 'TEST_REMOVED'
        ]

        unique_db_nums = len(set(
            iv.get('test_num', 0) for iv in db_test_runs
        ))
        total_docx = sum(len(v) for v in tested_files.values())

        counts = {
            'database_total': len(db_tests),
            'database_unique_nums': unique_db_nums,
            'database_sparks': len(sparks),
            'database_validation': len(validation),
            'change_log_completed': len(completed),
            'change_log_removed': len(removed),
            'tested_docx': total_docx,
            'has_duplicates': unique_db_nums < len(db_tests),
            'validation_matches_changelog': len(validation) == len(completed),
            'docx_matches_completed': total_docx == len(completed),
        }

        all_match = (
            not counts['has_duplicates']
            and counts['validation_matches_changelog']
            and counts['docx_matches_completed']
        )
        counts['all_counts_match'] = all_match

        return counts


# ══════════════════════════════════════════════════════════════
# CONVENIENCE: One-call removal for doc_reader integration
# ══════════════════════════════════════════════════════════════

def remove_test_run_completely(
    person_name: str,
    project_id: str,
    database=None,
    delete_files: bool = True,
) -> Dict:
    """
    Remove a test from ALL footprint locations.
    Drop-in replacement for Test RunMover.remove_completed().

    Args:
        person_name: Person name to remove
        project_id: Active project ID
        database: Test RunDatabase instance (optional, loads from disk if None)
        delete_files: Delete physical files

    Returns:
        Dict with 'success', 'script_name', 'cleaned', 'files_deleted', 'errors'
    """
    reconciler = Test RunReconciler(project_id, database)
    return reconciler.remove(person_name, delete_files=delete_files)


def quick_verify(project_id: str, database=None) -> Dict:
    """Quick count verification — call after any add/remove."""
    reconciler = Test RunReconciler(project_id, database)
    return reconciler.verify_counts()


# ══════════════════════════════════════════════════════════════
# FUSION TALLY — The Copier: Sequential Re-Run Through Clean Pipes
# ══════════════════════════════════════════════════════════════
#
# PURPOSE:
#   During R&D, tests were processed piecemeal by evolving engines.
#   Test Run #1 was analyzed by a different machine than Test Run #7.
#   The accumulated state has drift from months of building while testing.
#
#   The Tally is a COPIER: feed all completed packets back through the
#   NOW-FINISHED pipeline, one at a time, in order. Each test_run builds
#   on the last. By the end, you have a clean progressive chain where
#   every step was computed by the same engine version with the same logic.
#
#   That's the TARE — the zeroed scale. The Q-Cube lens distribution at
#   that point is the true calibration. The foreman sees this as proof
#   the system produces reproducible, accumulative intelligence.
#
# FLOW:
#   1. RECONCILE — clean all footprints (audit, dedup, orphans)
#   2. COLLATE   — load all completed packets, sort by test_run number
#   3. COPY      — re-process each through current AI pipeline in order
#   4. TALLY     — produce the balanced tare snapshot
#
# OUTPUT:
#   test_tally.json — complete progressive chain + final tare state
#   Each step includes: VP confidence, Q-Cube coverage, equipment damage,
#   hypothesis validation, IoC delta from previous step
#
# ══════════════════════════════════════════════════════════════


class TallyStep:
    """One test_run processed in the copier chain."""

    def __init__(self, test_num: int, person: str, company: str):
        self.test_num = test_num
        self.person = person
        self.company = company
        self.source = ''
        self.q_cube = ''
        self.equipment_count = 0
        self.equipment_names = []
        self.cost_data = []
        self.has_results = False
        self.has_experiments = False
        self.has_hypothesis_validation = False
        self.has_action_items = False
        self.completeness = 0  # 0-7 score
        self.error = ''

        # Progressive state AFTER this test_run
        self.cumulative_equipment = 0
        self.cumulative_damage_dollars = 0
        self.cube_cells_filled = 0
        self.cube_cells_total = 0
        self.cube_coverage_pct = 0.0
        self.vp_confidence = {}  # {vp_id: pct}
        self.hypothesis_posteriors = {}  # {key: posterior} after this step
        self.evidence_applied = []  # Evidence entries applied at this step

    def to_dict(self) -> Dict:
        return {
            'test_num': self.test_num,
            'script_name': self.person,
            'source_version': self.company,
            'source': self.source,
            'q_cube': self.q_cube,
            'equipment_count': self.equipment_count,
            'equipment_names': self.equipment_names,
            'cost_data': self.cost_data,
            'completeness': self.completeness,
            'has_results': self.has_results,
            'has_experiments': self.has_experiments,
            'has_hypothesis_validation': self.has_hypothesis_validation,
            'has_action_items': self.has_action_items,
            'error': self.error,
            'cumulative_equipment': self.cumulative_equipment,
            'cumulative_damage_dollars': self.cumulative_damage_dollars,
            'cube_cells_filled': self.cube_cells_filled,
            'cube_cells_total': self.cube_cells_total,
            'cube_coverage_pct': self.cube_coverage_pct,
            'vp_confidence': self.vp_confidence,
            'hypothesis_posteriors': self.hypothesis_posteriors,
            'evidence_applied': self.evidence_applied,
        }


class ValidationTally:
    """
    The Copier — sequential re-processing of all tests through
    the current pipeline to produce the tare (balanced zero'd state).

    Usage:
        tally = ValidationTally(project_id='BCM_SUBSTRATE')
        result = tally.run()
        # result['tare'] = final balanced state
        # result['chain'] = progressive steps
        # result['reconcile_report'] = data integrity report
    """

    # All Q-Cube cells (3 layers × 3 objects × 4 stacks = 36 max)
    LAYERS = ['L1', 'L2', 'L3']
    OBJECTS = ['OA', 'OB', 'OC']
    STACKS = ['Sα', 'Sβ', 'Sγ', 'Sδ']

    def __init__(self, project_id: str, database=None,
                 reconcile_first: bool = True):
        self.project_id = project_id
        self.project_dir = get_project_dir(project_id)
        self.db_file = BCM_ROOT / "test_database.json"
        self._database = database
        self._reconcile_first = reconcile_first
        self._log: List[str] = []

        # ── Brain Engines (optional — graceful if not available) ──
        self._hypothesis_engine = None
        self._qcube_engine = None

        if _HAS_HYPOTHESIS_ENGINE:
            self._hypothesis_engine = HypothesisEngine()
            # Team-defined hypotheses (BCM GIBUSH)
            self._hypothesis_engine.add_hypothesis(
                "H1", "Manual Detection is Industry-Wide Failure",
                "Operators and basic instruments miss contamination that causes damage",
                prior=0.50)
            self._hypothesis_engine.add_hypothesis(
                "H2", "Annual Contamination Damage Exceeds $200K/Mill",
                "True cost of contamination damage is understated across industry",
                prior=0.50)
            self._hypothesis_engine.add_hypothesis(
                "H3", "Mills Will Pay for Real-Time Detection",
                "Budget authority exists and ROI justification is clear",
                prior=0.50)
            self._hypothesis_engine.add_hypothesis(
                "H4", "Operator Knowledge > Instrument Knowledge",
                "Operators sense problems before instruments detect them",
                prior=0.60)
            self._hypothesis_engine.add_hypothesis(
                "H5", "Blow Line is Critical Blind Spot",
                "Blow line entry point lacks monitoring and causes repeated damage",
                prior=0.55)

        if _HAS_QCUBE_ENGINE:
            config = heavy_industry_config()
            self._qcube_engine = QCubeEngine(config)

    def _print(self, msg: str):
        self._log.append(msg)
        print(f"  [TALLY] {msg}")

    # ── STEP 1: RECONCILE (optional but recommended) ──

    def _reconcile(self) -> Dict:
        """Run reconciler to clean pipes before tare run."""
        self._print("STEP 1: RECONCILE — cleaning pipes...")
        reconciler = Test RunReconciler(self.project_id, self._database)
        report = reconciler.reconcile(fix=True)
        counts = reconciler.verify_counts()

        self._print(f"  Database: {counts['database_total']} tests "
                    f"({counts['database_sparks']}S + {counts['database_validation']}F)")
        if counts['all_counts_match']:
            self._print("  ✓ ALL COUNTS MATCH — pipes clean")
        else:
            self._print("  ⚠ Counts still mismatched after reconcile")

        return {'reconcile': report, 'counts': counts}

    # ── STEP 2: COLLATE — gather all tests in order ──

    def _collate(self) -> List[Dict]:
        """
        Load all tests from database, sorted by test_num.
        This is the copier's input stack — the pages to re-feed.
        """
        self._print("STEP 2: COLLATE — gathering tests in order...")

        if not self.db_file.exists():
            self._print("  ✗ No database file found")
            return []

        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._print(f"  ✗ Error loading database: {e}")
            return []

        tests = data.get('tests', [])

        # Sort by test_num
        tests.sort(key=lambda iv: iv.get('test_num', 0))

        # Separate by source for logging
        sparks = [iv for iv in tests if iv.get('source', '') != 'FUSION']
        validation = [iv for iv in tests if iv.get('source', '') == 'FUSION']

        self._print(f"  Collated: {len(tests)} test_runs")
        self._print(f"    Baseline: {len(sparks)} (discovery phase)")
        self._print(f"    Validation: {len(validation)} (validation phase)")
        self._print(f"    Order:  #{test_runs[0].get('test_num', '?')}"
                    f" → #{test_runs[-1].get('test_num', '?')}"
                    if tests else "    Order: (empty)")

        return test_runs

    # ── STEP 3: COPY — re-process each test sequentially ──

    def _copy(self, test_runs: List[Dict]) -> List[TallyStep]:
        """
        The copier pass: process each test in order, accumulating
        progressive intelligence. Each step builds on the last.
        """
        self._print(f"STEP 3: COPY — processing {len(tests)} tests...")

        chain: List[TallyStep] = []

        # Progressive accumulators
        all_equipment: Set[str] = set()
        total_damage = 0
        cube_matrix: Dict[str, List[int]] = {}
        all_cube_cells = set()

        # Enumerate all possible cube cells
        for layer in self.LAYERS:
            for obj in self.OBJECTS:
                for stack in self.STACKS:
                    all_cube_cells.add(f"[{layer}, {obj}, {stack}]")
        total_cells = len(all_cube_cells)

        for idx, iv in enumerate(tests):
            num = iv.get('test_num', 0)
            person = iv.get('script_name', 'Unknown')
            company = iv.get('source_version', 'Unknown')

            step = TallyStep(num, person, company)
            step.source = iv.get('source', 'SPARKS')

            # ── Parse Q-Cube ──
            layer = iv.get('q_layer', 'L1')
            obj = iv.get('q_object', 'OA')
            stacks = iv.get('q_stack', ['Sα'])
            if isinstance(stacks, str):
                stacks = [stacks]
            step.q_cube = f"[{layer}, {obj}, {','.join(stacks)}]"

            # Add to cube matrix
            for stack in stacks:
                key = f"[{layer}, {obj}, {stack}]"
                if key not in cube_matrix:
                    cube_matrix[key] = []
                cube_matrix[key].append(num)

            # ── Parse equipment ──
            equip_impacts = iv.get('substrate_impacts', [])
            if isinstance(equip_impacts, list):
                for eq in equip_impacts:
                    name = eq.get('equipment', '') if isinstance(eq, dict) else str(eq)
                    if name:
                        all_equipment.add(name)
                        step.equipment_names.append(name)
                step.equipment_count = len(step.equipment_names)

            # ── Parse cost data ──
            cost_data = iv.get('cost_data', [])
            if isinstance(cost_data, list):
                step.cost_data = cost_data
                for cd in cost_data:
                    # Try to extract dollar amount from annual_damage field
                    damage_str = cd.get('annual_damage', '') if isinstance(cd, dict) else ''
                    dollars = self._extract_dollars(damage_str)
                    total_damage += dollars

            # ── Completeness check (7 fields) ──
            fields = {
                'results': iv.get('results', ''),
                'experiments': iv.get('experiments', ''),
                'hypotheses': iv.get('hypotheses', ''),
                'action_iterate': iv.get('action_iterate', ''),
                'script_name': person,
                'source_version': company,
                'equipment': bool(equip_impacts),
            }
            completeness = sum(1 for v in fields.values()
                             if v and str(v).strip())
            step.completeness = completeness
            step.has_results = bool(fields['results'] and str(fields['results']).strip())
            step.has_experiments = bool(fields['experiments'] and str(fields['experiments']).strip())
            step.has_hypothesis_validation = bool(fields['hypotheses'] and str(fields['hypotheses']).strip())
            step.has_action_items = bool(fields['action_iterate'] and str(fields['action_iterate']).strip())

            # ── BRAIN: Evidence classification + Bayesian update ──
            if self._hypothesis_engine:
                # Build full text for evidence scanning
                full_text = ' '.join(
                    str(iv.get(f, '')) for f in
                    ('results', 'experiments', 'hypotheses', 'action_iterate')
                    if iv.get(f)
                ).lower()

                evidence_list = self._classify_evidence(full_text, num)
                for ev in evidence_list:
                    self._hypothesis_engine.update_hypothesis(
                        key=ev['hypothesis'],
                        direction=ev['direction'],
                        reason=ev['reason'],
                        test_num=num,
                        evidence_type=ev['evidence_type'],
                    )
                step.evidence_applied = evidence_list

                # Snapshot posteriors after this test_run
                step.hypothesis_posteriors = {
                    k: round(h.posterior, 4)
                    for k, h in self._hypothesis_engine.hypotheses.items()
                }

            # ── BRAIN: QCube geometric registration ──
            if self._qcube_engine:
                # Register in QCubeEngine with proper axis values
                # Map Greek stack labels back to config keys
                _stack_to_key = {'Sα': 'Sa', 'Sβ': 'Sb', 'Sγ': 'Sg', 'Sδ': 'Sd'}
                for stack in stacks:
                    stack_key = _stack_to_key.get(stack, stack)
                    self._qcube_engine.register_test_run(num, layer, obj, stack_key)

            # ── Progressive state after this test_run ──
            step.cumulative_equipment = len(all_equipment)
            step.cumulative_damage_dollars = total_damage

            # Use QCubeEngine for coverage if available, else manual count
            if self._qcube_engine:
                step.cube_coverage_pct = round(
                    self._qcube_engine.coverage_percentage(), 1)
                step.cube_cells_filled = len(self._qcube_engine.filled_positions)
                step.cube_cells_total = self._qcube_engine.config.total_positions
            else:
                filled_cells = len(cube_matrix)
                step.cube_cells_filled = filled_cells
                step.cube_cells_total = total_cells
                step.cube_coverage_pct = round(
                    (filled_cells / total_cells) * 100, 1
                ) if total_cells > 0 else 0.0

            chain.append(step)

            self._print(
                f"  [{idx+1}/{len(tests)}] #{num} {person} ({company}) "
                f"— equip={step.equipment_count}, "
                f"cube={step.cube_coverage_pct}%, "
                f"complete={completeness}/7"
            )

        return chain

    # ── EVIDENCE CLASSIFIER (rule-based, Appendix A.1 compliant) ──

    def _classify_evidence(self, text: str, test_num: int) -> List[Dict]:
        """
        Sca test text for evidence signals and classify them.

        This is a RULE-BASED classifier with heuristic patterns.
        Not NLP — explicit keyword matching. The value is in structured
        tracking, not in statistical sophistication. (Appendix A.1)

        Returns list of {hypothesis, direction, evidence_type, reason}.
        """
        evidence = []
        if not text:
            return evidence

        # ── H1: Manual detection failure ──
        manual_signals = [
            'manual detection', 'can\'t see', 'don\'t detect', 'missed',
            'no way to know', 'by the time', 'not until', 'didn\'t know',
            'visual inspection', 'nobody checks', 'no instrument',
        ]
        for signal in manual_signals:
            if signal in text:
                evidence.append({
                    'hypothesis': 'H1',
                    'direction': +1,
                    'evidence_type': 'explicit_validate',
                    'reason': f'Manual detection signal: "{signal}"',
                })
                break  # One hit per hypothesis per test

        # ── H2: Cost > $200K ──
        cost_match = re.findall(
            r'\$\s?(\d[\d,]*)\s*(?:k|K|thousand)?', text)
        for c in cost_match:
            try:
                val = int(c.replace(',', ''))
                if 'k' in text[text.index(c):text.index(c)+10].lower():
                    val *= 1000
                if val >= 50000:
                    evidence.append({
                        'hypothesis': 'H2',
                        'direction': +1,
                        'evidence_type': 'cost_direct',
                        'reason': f'Cost data: ${val:,}',
                    })
                    break
            except (ValueError, IndexError):
                continue

        # ── H3: Willingness to pay ──
        pay_signals = [
            'would pay', 'budget', 'roi', 'invest', 'purchase',
            'capital', 'fund', 'approve', 'allocated', 'procurement',
        ]
        for signal in pay_signals:
            if signal in text:
                evidence.append({
                    'hypothesis': 'H3',
                    'direction': +1,
                    'evidence_type': 'sentiment_positive',
                    'reason': f'Payment signal: "{signal}"',
                })
                break

        # ── H4: Operator knowledge ──
        operator_signals = [
            'operator', 'hear', 'feel', 'smell', 'vibrat',
            'sound', 'before the alarm', 'know before',
            'experience tells', 'can tell',
        ]
        for signal in operator_signals:
            if signal in text:
                evidence.append({
                    'hypothesis': 'H4',
                    'direction': +1,
                    'evidence_type': 'explicit_validate',
                    'reason': f'Operator knowledge signal: "{signal}"',
                })
                break

        # ── H5: Blow line blind spot ──
        blow_signals = [
            'blow line', 'blow-line', 'blowline', 'blind spot',
            'no monitoring', 'entry point', 'chip feed',
            'before the digester', 'mkp', 'star feeder',
        ]
        for signal in blow_signals:
            if signal in text:
                evidence.append({
                    'hypothesis': 'H5',
                    'direction': +1,
                    'evidence_type': 'equipment_damage',
                    'reason': f'Blow line signal: "{signal}"',
                })
                break

        # ── Contradiction detection (applies to any hypothesis) ──
        contradict_signals = [
            'not a problem', 'don\'t see that', 'doesn\'t apply',
            'never had', 'not relevant', 'our sensors catch',
            'modern equipment', 'already solved',
        ]
        for signal in contradict_signals:
            if signal in text:
                # Apply mild contradiction to H1 (most common pushback target)
                evidence.append({
                    'hypothesis': 'H1',
                    'direction': -1,
                    'evidence_type': 'explicit_contradict',
                    'reason': f'Contradiction signal: "{signal}"',
                })
                break

        return evidence

    # ── STEP 4: TALLY — produce the tare snapshot ──

    def _tally(self, chain: List[TallyStep], test_runs: List[Dict]) -> Dict:
        """
        Produce the final tare — the balanced state after all test_runs
        have been processed sequentially through the same engine.
        """
        self._print("STEP 4: TALLY — computing tare...")

        if not chain:
            return {'error': 'No tests processed'}

        last = chain[-1]

        # Build progressive data series (for charting)
        progression = {
            'cube_coverage': [],
            'equipment_count': [],
            'damage_dollars': [],
            'completeness': [],
        }
        for step in chain:
            progression['cube_coverage'].append({
                'test_run': step.test_num,
                'script_name': step.person,
                'value': step.cube_coverage_pct,
            })
            progression['equipment_count'].append({
                'test_run': step.test_num,
                'script_name': step.person,
                'value': step.cumulative_equipment,
            })
            progression['damage_dollars'].append({
                'test_run': step.test_num,
                'script_name': step.person,
                'value': step.cumulative_damage_dollars,
            })
            progression['completeness'].append({
                'test_run': step.test_num,
                'script_name': step.person,
                'value': step.completeness,
            })

        # Source breakdown
        baseline_count = sum(1 for s in chain if s.source != 'FUSION')
        validation_count = sum(1 for s in chain if s.source == 'FUSION')

        # Completeness stats
        full_complete = sum(1 for s in chain if s.completeness == 7)
        avg_complete = (
            sum(s.completeness for s in chain) / len(chain)
        ) if chain else 0

        # Equipment uniqueness
        all_equip = set()
        for step in chain:
            all_equip.update(step.equipment_names)

        # Cube cell detail
        cube_detail: Dict[str, List[int]] = {}
        for iv in test_runs:
            layer = iv.get('q_layer', 'L1')
            obj = iv.get('q_object', 'OA')
            stacks = iv.get('q_stack', ['Sα'])
            if isinstance(stacks, str):
                stacks = [stacks]
            for stack in stacks:
                key = f"[{layer}, {obj}, {stack}]"
                if key not in cube_detail:
                    cube_detail[key] = []
                cube_detail[key].append(iv.get('test_num', 0))

        # Coverage gaps
        all_cells = set()
        for layer in self.LAYERS:
            for obj in self.OBJECTS:
                for stack in self.STACKS:
                    all_cells.add(f"[{layer}, {obj}, {stack}]")
        filled = set(cube_detail.keys())
        gaps = sorted(all_cells - filled)

        tare = {
            'tare_computed': datetime.now().isoformat(),
            'project_id': self.project_id,
            'total_test_runs': len(chain),
            'baseline_count': baseline_count,
            'validation_count': validation_count,

            # The tare readings
            'cube_coverage_pct': last.cube_coverage_pct,
            'cube_cells_filled': last.cube_cells_filled,
            'cube_cells_total': last.cube_cells_total,
            'cube_gaps': gaps,
            'cube_gaps_count': len(gaps),
            'cube_detail': cube_detail,

            'unique_equipment': sorted(all_equip),
            'unique_equipment_count': len(all_equip),
            'total_damage_documented': last.cumulative_damage_dollars,

            'completeness_avg': round(avg_complete, 1),
            'completeness_full': full_complete,
            'completeness_full_pct': round(
                (full_complete / len(chain)) * 100, 1
            ) if chain else 0,

            # Progressive data (for charting in UI)
            'progression': progression,
        }

        # ── BRAIN: Hypothesis posteriors (Bayesian tare) ──
        if self._hypothesis_engine:
            summary = self._hypothesis_engine.summary()
            tare['hypotheses'] = summary['hypotheses']
            tare['hypotheses_validated'] = summary['validated']
            tare['hypotheses_invalidated'] = summary['invalidated']
            tare['hypotheses_needs_data'] = summary['needs_data']

            # Progression: posteriors at each step (for charting)
            progression['hypothesis_posteriors'] = []
            for step in chain:
                if step.hypothesis_posteriors:
                    progression['hypothesis_posteriors'].append({
                        'test_run': step.test_num,
                        'script_name': step.person,
                        'posteriors': step.hypothesis_posteriors,
                    })

        # ── BRAIN: QCube ranked gaps (information-gain ordering) ──
        if self._qcube_engine:
            # Override simple gaps with ranked gaps from QCubeEngine
            validated_positions = set()
            # Build validated set from hypothesis state
            if self._hypothesis_engine:
                for h in self._hypothesis_engine.get_validated():
                    # Use filled positions as proxy for validated
                    for pos_key in self._qcube_engine.filled_positions:
                        validated_positions.add(pos_key)

            ranked_gaps = self._qcube_engine.find_gaps(
                validated_positions=validated_positions)
            tare['cube_gaps_ranked'] = [
                {
                    'position': g.position_key,
                    'label': g.position_label,
                    'priority': round(g.priority, 3),
                    'information_gain': round(g.information_gain, 3),
                    'reason': g.reason,
                }
                for g in ranked_gaps[:15]  # Top 15 gaps
            ]
            # Update coverage from QCubeEngine (more accurate)
            tare['cube_coverage_pct'] = round(
                self._qcube_engine.coverage_percentage(), 1)
            tare['cube_cells_filled'] = len(
                self._qcube_engine.filled_positions)
            tare['cube_cells_total'] = (
                self._qcube_engine.config.total_positions)

        self._print(f"  ═══ TARE READING ═══")
        self._print(f"  Tests:    {tare['total_test_runs']} "
                    f"({baseline_count}S + {validation_count}F)")
        self._print(f"  Q-Cube:        {tare['cube_coverage_pct']}% "
                    f"({tare['cube_cells_filled']}/{tare['cube_cells_total']} cells)")
        self._print(f"  Cube Gaps:     {tare['cube_gaps_count']} empty cells")
        self._print(f"  Equipment:     {tare['unique_equipment_count']} unique items")
        self._print(f"  Damage:        ${tare['total_damage_documented']:,.0f} documented")
        self._print(f"  Completeness:  {tare['completeness_avg']}/7 avg, "
                    f"{tare['completeness_full']}/{tare['total_test_runs']} fully complete")

        # ── BRAIN: Print hypothesis state ──
        if self._hypothesis_engine:
            self._print(f"  ─── BAYESIAN HYPOTHESES (Appendix A.1) ───")
            for key, h in self._hypothesis_engine.hypotheses.items():
                ci = h.confidence_interval
                moved = h.posterior - h.prior
                status_icon = {
                    'VALIDATED': '✓', 'INVALIDATED': '✗',
                    'NEEDS_MORE_DATA': '◐',
                }.get(h.status, '?')
                self._print(
                    f"    {status_icon} {h.name[:45]:<45} "
                    f"{h.prior:.0%}→{h.posterior:.0%} "
                    f"CI[{ci[0]:.0%},{ci[1]:.0%}] "
                    f"n={h.evidence_count} {h.status}"
                )
            self._print(
                f"  Summary: {len(self._hypothesis_engine.get_validated())} validated, "
                f"{len(self._hypothesis_engine.get_invalidated())} invalidated, "
                f"{len(self._hypothesis_engine.get_needs_data())} needs data"
            )
        else:
            self._print(f"  Hypotheses:    (hypothesis_engine.py not available)")

        return tare

    # ── PUBLIC: Run the full tally ──

    def run(self) -> Dict:
        """
        Execute the full Validation Tally:
          1. Reconcile (clean pipes)
          2. Collate (gather in order)
          3. Copy (re-process sequentially)
          4. Tally (produce tare)

        Returns dict with:
          'reconcile_report' — data integrity results
          'chain' — list of TallyStep dicts (progressive)
          'tare' — final balanced state
          'log' — human-readable run log
        """
        self._log.clear()
        self._print("=" * 60)
        self._print(f"FUSION TALLY — {self.project_id}")
        self._print(f"The Copier: Sequential Re-Run Through Clean Pipes")
        self._print("=" * 60)

        result = {
            'project_id': self.project_id,
            'started': datetime.now().isoformat(),
            'reconcile_report': {},
            'chain': [],
            'tare': {},
            'log': [],
        }

        # Step 1: Reconcile
        if self._reconcile_first:
            result['reconcile_report'] = self._reconcile()
        else:
            self._print("STEP 1: RECONCILE — skipped (reconcile_first=False)")

        # Step 2: Collate
        tests = self._collate()

        # Step 3: Copy
        chain = self._copy(tests)
        result['chain'] = [step.to_dict() for step in chain]

        # Step 4: Tally
        tare = self._tally(chain, tests)
        result['tare'] = tare

        result['completed'] = datetime.now().isoformat()
        result['log'] = self._log

        # Save tally to disk
        tally_path = self.project_dir / "test_tally.json"
        try:
            with open(tally_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            self._print(f"\n✓ Tally saved: {tally_path}")
        except IOError as e:
            self._print(f"\n✗ Error saving tally: {e}")

        self._print("=" * 60)
        self._print("FUSION TALLY COMPLETE")
        self._print("=" * 60)

        return result

    # ── Utility ──

    @staticmethod
    def _extract_dollars(text: str) -> int:
        """Extract dollar amount from text like '$100,000' or '100K'."""
        if not text or not isinstance(text, str):
            return 0
        text = text.replace(',', '').replace('$', '').strip()
        # Try direct number
        try:
            return int(float(text))
        except ValueError:
            pass
        # Try 100K format
        match = re.search(r'(\d+(?:\.\d+)?)\s*[kK]', text)
        if match:
            return int(float(match.group(1)) * 1000)
        # Try number anywhere in string
        match = re.search(r'(\d{3,})', text)
        if match:
            return int(match.group(1))
        return 0


# ══════════════════════════════════════════════════════════════
# CONVENIENCE: One-call tally for tab integration
# ══════════════════════════════════════════════════════════════

def run_test_tally(project_id: str, database=None,
                     reconcile_first: bool = True) -> Dict:
    """
    Run the full Validation Tally and return results.
    Drop-in call for the Validation Tally tab.

    Args:
        project_id: Active project ID
        database: Test RunDatabase instance (optional)
        reconcile_first: Run reconciler before tally (recommended)

    Returns:
        Dict with 'reconcile_report', 'chain', 'tare', 'log'
    """
    tally = ValidationTally(project_id, database, reconcile_first)
    return tally.run()


# ══════════════════════════════════════════════════════════════
# CLI — Run standalone for diagnostics
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  TEST RECONCILER — Data Integrity Check")
    print("  For all the industrial workers lost to preventable acts")
    print("=" * 60)

    # Discover projects
    projects = list_deployed_projects()
    if not projects:
        print("\n  No deployed projects found.")
        print(f"  Looked in: {BCM_ROOT}")
        sys.exit(1)

    print(f"\n  Found {len(projects)} project(s): {', '.join(projects)}")

    for pid in projects:
        reconciler = Test RunReconciler(pid)

        # Quick counts first
        counts = reconciler.verify_counts()
        print(f"\n{'─' * 50}")
        print(f"  PROJECT: {pid}")
        print(f"  Database:  {counts['database_total']} tests "
              f"({counts['database_sparks']}S + {counts['database_validation']}F)")
        print(f"  Unique #s: {counts['database_unique_nums']}")
        print(f"  Completed: {counts['change_log_completed']} (change_log)")
        print(f"  .docx:     {counts['tested_docx']} files")
        print(f"  Removed:   {counts['change_log_removed']} (audit trail)")

        if counts['has_duplicates']:
            print(f"  ⚠ DUPLICATES DETECTED in database")
        if not counts['validation_matches_changelog']:
            print(f"  ⚠ Validation count ({counts['database_validation']}) "
                  f"≠ change_log ({counts['change_log_completed']})")
        if not counts['docx_matches_completed']:
            print(f"  ⚠ .docx count ({counts['tested_docx']}) "
                  f"≠ completed ({counts['change_log_completed']})")
        if counts['all_counts_match']:
            print(f"  ✓ ALL COUNTS MATCH")

    # Full audit
    print(f"\n{'═' * 60}")
    print("  Run full audit? (y/n): ", end="")
    try:
        choice = input().strip().lower()
    except EOFError:
        choice = 'y'

    if choice == 'y':
        for pid in projects:
            reconciler = Test RunReconciler(pid)
            report = reconciler.reconcile(fix=False)

        print("\n  Run fixes? (y/n): ", end="")
        try:
            fix_choice = input().strip().lower()
        except EOFError:
            fix_choice = 'n'

        if fix_choice == 'y':
            for pid in projects:
                reconciler = Test RunReconciler(pid)
                report = reconciler.reconcile(fix=True)

    # Validation Tally option
    print(f"\n{'═' * 60}")
    print("  Run FUSION TALLY (copier re-run + tare)? (y/n): ", end="")
    try:
        tally_choice = input().strip().lower()
    except EOFError:
        tally_choice = 'n'

    if tally_choice == 'y':
        for pid in projects:
            tally = ValidationTally(pid, reconcile_first=False)
            result = tally.run()
            tare = result.get('tare', {})
            if tare:
                print(f"\n  ═══ TARE RESULT: {pid} ═══")
                print(f"  Q-Cube: {tare.get('cube_coverage_pct', 0)}%")
                print(f"  Equipment: {tare.get('unique_equipment_count', 0)} items")
                print(f"  Damage: ${tare.get('total_damage_documented', 0):,.0f}")
                print(f"  Gaps: {tare.get('cube_gaps_count', 0)} empty cells")

    print("\n  Done.")
