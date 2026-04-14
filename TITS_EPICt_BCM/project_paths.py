# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
PROJECT PATHS — Single Source of Truth for All Folder Locations
================================================================
Location: TITS_GIBUSH_AISOS_SPINE_EPIC/project_paths.py

EVERY file that needs a path imports from here.
One place to change when folder structure evolves.

STRUCTURE (as of 2026-02-23):
  EPIC_ROOT/
  ├── BCM_Projects/
  │   ├── projects.json               (project registry)
  │   ├── test_database.json     (global test_run DB)
  │   └── BCM_Navigator_Project/
  │       ├── BCM_SUBSTRATE/
  │       │   ├── project_config.json
  │       │   ├── inclusion_log.json
  │       │   ├── doctrine_pass.json
  │       │   ├── change_log.json
  │       │   ├── BMC_generation/              (project BMC output)
  │       │   ├── substrate_class_profile/    (project customer segment)
  │       │   ├── BCM_test_config/      (project's living Excel)
  │       │   ├── Baseline_deck_tests_final/ (project Baseline deck)
  │       │   ├── tested/                 (completed tests + inclusion)
  │       │   ├── test_template_list/     (pending test_run packets)
  │       │   ├── test_report_slides/
  │       │   └── _BCM_generated_report/
  │       └── AISOS_SPINE/
  │           └── (same structure)
  └── ... (genesis_brain, config, etc.)

HIERARCHY: THE PERSON > TITS > GIBUSH > AISOS/SPINE > CaaS > SaaS
© 2025-2026 Stephen J. Burdick Sr. — All Rights Reserved.
"""

import sys
import json
from pathlib import Path
from typing import List, Optional, Dict

# ══════════════════════════════════════════════════════════════
# ROOT PATHS
# ══════════════════════════════════════════════════════════════

# EPIC root — where this file lives
EPIC_ROOT = Path(__file__).resolve().parent

# TITS ecosystem root
TITS_ROOT = EPIC_ROOT.parent  # C:\TITS\TITS_GIBUSH_AISOS_SPINE

# FUSION Projects root (was BCM_TESTS)
BCM_ROOT = EPIC_ROOT / "BCM_Projects"

# Project deployment root — where per-project folders live
PROJECT_ROOT = BCM_ROOT / "BCM_Navigator_Project"

# Global files at BCM_ROOT level
PROJECTS_JSON = BCM_ROOT / "projects.json"
TEST_DATABASE_JSON = BCM_ROOT / "test_database.json"

# AISOS / CaaS paths
AISOS_ROOT = TITS_ROOT / "TITS_GIBUSH_AISOS_SPINE"
CAAS_ROOT = AISOS_ROOT / "AISOS_SPINE_MODULES" / "TITS_GIBUSH_AISOS_SPINE_Production_CaaS"
PASS_DIR = AISOS_ROOT / "AISOS_SPINE_MODULES" / "PASS_REQUESTS"

# Backward compat — old name, new location
# Any code using TEST_DATA_DIR gets PROJECT_ROOT
TEST_DATA_DIR = PROJECT_ROOT


# ══════════════════════════════════════════════════════════════
# PROJECT DISCOVERY
# ══════════════════════════════════════════════════════════════

def list_deployed_projects() -> List[str]:
    """List all project IDs that have folders in BCM_Navigator_Project/."""
    projects = []
    if PROJECT_ROOT.exists():
        for d in sorted(PROJECT_ROOT.iterdir()):
            if d.is_dir() and (d / "project_config.json").exists():
                projects.append(d.name)
    return projects


def get_project_dir(project_id: str) -> Path:
    """Get the full path to a project's folder."""
    return PROJECT_ROOT / project_id


def ensure_project_structure(project_id: str) -> Path:
    """
    Ensure a project folder has all required subdirectories.
    Creates missing folders. Returns project path.
    """
    project_dir = get_project_dir(project_id)
    
    required_subdirs = [
        "BMC_generation",
        "substrate_class_profile",
        "exports",
        "genesis_output",
        "tested",
        "test_template_list",
        "test_report_slides",
        "Baseline_deck_tests_final",
        "_BCM_generated_report",
    ]
    
    for sub in required_subdirs:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)
    
    # Ensure project_config.json exists
    cfg_file = project_dir / "project_config.json"
    if not cfg_file.exists():
        cfg = {
            "project_id": project_id,
            "created": "",
            "champions": {},
            "status": "ACTIVE",
        }
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    
    # Ensure inclusion_log.json exists
    inc_file = project_dir / "inclusion_log.json"
    if not inc_file.exists():
        inc = {
            "project_id": project_id,
            "stream": "INCLUSION",
            "entry_count": 0,
            "entries": [],
        }
        inc_file.write_text(json.dumps(inc, indent=2), encoding='utf-8')
    
    return project_dir


# ══════════════════════════════════════════════════════════════
# PROJECT-SPECIFIC PATHS
# ══════════════════════════════════════════════════════════════

def get_project_config(project_id: str) -> Path:
    return get_project_dir(project_id) / "project_config.json"

def get_inclusion_log(project_id: str) -> Path:
    return get_project_dir(project_id) / "inclusion_log.json"

def get_tested_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "tested"

def get_template_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "test_template_list"

def get_bmc_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "BMC_generation"

def get_substrate_class_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "substrate_class_profile"

def get_baseline_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "Baseline_deck_tests_final"

def get_bcm_report_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "_BCM_generated_report"

def get_report_slide_dir(project_id: str) -> Path:
    return get_project_dir(project_id) / "test_report_slides"


# ══════════════════════════════════════════════════════════════
# EXCEL DISCOVERY (per-project)
# ══════════════════════════════════════════════════════════════

# Subfolder names where projects MAY store their Excel
# (projects can use any of these — we search all of them)
EXCEL_SUBFOLDER_NAMES = [
    "BCM_test_config",
    "BCM_test_config_legacy",
]


def find_project_config(project_id: str) -> Optional[Path]:
    """
    Find the Excel test_run plan for ANY project — zero hardcoding.
    
    Search order:
      1. Known Excel subfolders inside the project dir → any *Test_Plan*.xlsx
      2. Direct in project dir → any *Test_Plan*.xlsx
      3. Legacy location at EPIC root → BCM_test_config_legacy/
      4. Any .xlsx anywhere in the project tree (last resort)
    
    Returns first match or None.
    """
    project_dir = get_project_dir(project_id)
    
    # Search 1: Known Excel subfolders inside the project
    for subfolder_name in EXCEL_SUBFOLDER_NAMES:
        excel_dir = project_dir / subfolder_name
        if excel_dir.exists():
            for f in sorted(excel_dir.glob("*.xlsx")):
                if "Test_Plan" in f.name or "test_run" in f.name.lower():
                    return f
    
    # Search 2: Direct in project folder
    if project_dir.exists():
        for f in sorted(project_dir.glob("*Test_Plan*.xlsx")):
            return f
    
    # Search 3: Legacy location at EPIC root
    legacy_dir = EPIC_ROOT / "BCM_test_config_legacy"
    if legacy_dir.exists():
        for f in sorted(legacy_dir.glob("*.xlsx")):
            # Match by project_id appearing in filename (case-insensitive)
            if project_id.lower().replace("_", "") in f.stem.lower().replace("_", ""):
                return f
    
    # Search 4: Any xlsx anywhere under project dir (last resort)
    if project_dir.exists():
        for f in project_dir.rglob("*.xlsx"):
            if "test_run" in f.name.lower():
                return f
    
    return None


def find_project_baseline_deck(project_id: str) -> Optional[Path]:
    """Find the Baseline test_run deck JSON for a project."""
    baseline_dir = get_baseline_dir(project_id)
    if baseline_dir.exists():
        for f in baseline_dir.glob("*deck*.json"):
            return f
    
    # Fallback: legacy location
    legacy = EPIC_ROOT / "BCM_Projects" / "Baseline_deck_tests_final"
    if legacy.exists():
        for f in legacy.glob("*deck*.json"):
            return f
    
    return None


# ══════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY — OLD PATH MAPPING
# ══════════════════════════════════════════════════════════════

def migrate_path(old_path: str) -> Path:
    """Convert an old BCM_TESTS path to new BCM_Navigator_Project structure."""
    p = str(old_path)
    p = p.replace("BCM_TESTS", str(PROJECT_ROOT))
    return Path(p)


# ══════════════════════════════════════════════════════════════
# STANDALONE TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  PROJECT PATHS — Structure Verification")
    print("  The Person is the Highest Responsibility")
    print("=" * 60)
    
    print(f"\n  EPIC_ROOT:   {EPIC_ROOT}")
    print(f"  BCM_ROOT:   {BCM_ROOT}")
    print(f"  PROJECT_ROOT:  {PROJECT_ROOT}")
    print(f"  PROJECTS_JSON: {PROJECTS_JSON}")
    print(f"  CAAS_ROOT:     {CAAS_ROOT}")
    print(f"  PASS_DIR:      {PASS_DIR}")
    
    print(f"\n  Deployed Projects:")
    projects = list_deployed_projects()
    if projects:
        for pid in projects:
            pdir = get_project_dir(pid)
            excel = find_project_config(pid)
            sparks = find_project_baseline_deck(pid)
            print(f"    {pid}:")
            print(f"      Dir:    {pdir} {'✓' if pdir.exists() else '✗'}")
            print(f"      Excel:  {excel or 'NOT FOUND'}")
            print(f"      Baseline: {sparks or 'NOT FOUND'}")
            print(f"      Config: {get_project_config(pid)} "
                  f"{'✓' if get_project_config(pid).exists() else '✗'}")
            print(f"      BMC:    {get_bmc_dir(pid)} "
                  f"{'✓' if get_bmc_dir(pid).exists() else '✗'}")
    else:
        print("    (none found)")
    
    print(f"\n  Done.")
