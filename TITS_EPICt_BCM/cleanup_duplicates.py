# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
DATABASE CLEANUP — Deduplicate by PERSON NAME across ALL sources
================================================================
The old system keyed on test_num, so the same person loaded via
different paths (Excel plan, auto-scan, manual entry) got separate entries.

This script:
    1. Groups ALL tests by person name (case-insensitive)
    2. For each person with multiple entries, keeps the RICHEST copy
       (most results text + most equipment + highest synergy score)
    3. Rebuilds cube_matrix keyed by person name
    4. Reports exactly what was removed and why

Usage:
    cd C:\\TITS\\TITS_Production\\gibush_icorps
    python cleanup_duplicates.py
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── Locate database ──────────────────────────────────────────────
search_paths = [
    # App uses BCM_ROOT / "test_database.json"
    Path("BCM_Projects/test_database.json"),
    # Per-project database
    Path("BCM_Projects/project_caas_deployed/BCM_SUBSTRATE/test_database.json"),
    # Legacy paths
    Path("BCM_TESTS/BCM_SUBSTRATE/test_database.json"),
    Path("BCM_TESTS/test_database.json"),
    Path("test_database.json"),
]

found_all = []
for p in search_paths:
    if p.exists():
        size = p.stat().st_size
        found_all.append((p, size))

if not found_all:
    print("ERROR: Cannot find test_database.json")
    for p in search_paths:
        print(f"  checked: {p.absolute()}")
    exit(1)

# Pick the LARGEST file — that's the real database with all test_runs
found_all.sort(key=lambda x: x[1], reverse=True)
db_file = found_all[0][0]

if len(found_all) > 1:
    print("Found multiple database files:")
    for p, size in found_all:
        tag = " ← USING (largest)" if p == db_file else ""
        print(f"  {p}  ({size:,} bytes){tag}")
    print()

print(f"Loading: {db_file}")
with open(db_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

tests = data.get('tests', [])
print(f"Total tests loaded: {len(tests)}")


# ── Normalize person name ────────────────────────────────────────
def normalize(name: str) -> str:
    """Lowercase, strip quotes/parens, collapse whitespace."""
    clean = re.sub(r'["\'\(\)\[\]]', '', name.strip().lower())
    return ' '.join(clean.split())


# ── Richness score ───────────────────────────────────────────────
def richness(iv: dict) -> float:
    """Score how much real content an entry has. Higher = keep."""
    score = 0.0
    for field in ('results', 'experiments', 'hypotheses', 'action_iterate'):
        val = iv.get(field, '') or ''
        text = str(val).strip()
        # Skip placeholder-only text
        if text and '[PENDING' not in text and '[fill' not in text.lower():
            score += 1.0
            score += min(len(text), 2000) / 2000.0  # length bonus, capped

    # Equipment data bonus
    equip = iv.get('substrate_impacts', [])
    if isinstance(equip, list):
        score += len(equip) * 0.5

    # Synergy score bonus
    try:
        score += float(iv.get('synergy_score', 0)) * 2
    except (ValueError, TypeError):
        pass

    # Has a real date? Small bonus
    if iv.get('date', '').strip():
        score += 0.3

    return score


# ── Group by person name ────────────────────────────────────────
groups = defaultdict(list)
for iv in test_runs:
    person = normalize(iv.get('script_name', ''))
    if not person or person in ('unknown', 'target', ''):
        # Keep target/placeholder entries ungrouped — use a unique key
        groups[f"_ungrouped_{id(iv)}"].append(iv)
    else:
        groups[person].append(iv)

# ── Pick winners, collect losers ─────────────────────────────────
kept = []
removed = []

print(f"\n{'='*60}")
print(f"DEDUP BY PERSON NAME — {len(groups)} unique people")
print(f"{'='*60}\n")

for script_key, copies in sorted(groups.items()):
    if script_key.startswith('_ungrouped_'):
        kept.append(copies[0])
        continue

    if len(copies) == 1:
        kept.append(copies[0])
        continue

    # Multiple entries for same person — rank by richness
    scored = [(richness(iv), iv) for iv in copies]
    scored.sort(key=lambda x: x[0], reverse=True)

    winner_score, winner = scored[0]
    losers = scored[1:]

    # Merge: pull substrate_impacts from losers into winner if winner is missing them
    winner_equip_names = {
        e.get('equipment', '').strip().lower()
        for e in winner.get('substrate_impacts', [])
    }
    for _, loser in losers:
        for eq in loser.get('substrate_impacts', []):
            eq_name = eq.get('equipment', '').strip().lower()
            if eq_name and eq_name not in winner_equip_names:
                winner.setdefault('substrate_impacts', []).append(eq)
                winner_equip_names.add(eq_name)

    kept.append(winner)

    winner_person = winner.get('script_name', '?')
    winner_source = winner.get('source', '?')
    print(f"  {winner_person}:")
    print(f"    KEPT:    #{winner.get('test_num','?')} "
          f"({winner_source}) richness={winner_score:.1f}")
    for loser_score, loser in losers:
        print(f"    REMOVED: #{loser.get('test_num','?')} "
              f"({loser.get('source','?')}) richness={loser_score:.1f}")
        removed.append(loser)
    print()

if not removed:
    print("No duplicates found. Database is clean.")
    exit(0)

print(f"{'='*60}")
print(f"REMOVED {len(removed)} duplicate entries")
print(f"KEPT    {len(kept)} unique test_runs")
print(f"{'='*60}")


# ── Rebuild cube_matrix by person name ───────────────────────────
cube_matrix = {}
for iv in kept:
    person = iv.get('script_name', '').strip()
    layer = iv.get('q_layer', '')
    obj = iv.get('q_object', '')
    stacks = iv.get('q_stack', [])
    if not layer or not obj:
        continue
    if isinstance(stacks, str):
        stacks = [stacks]
    for stack in stacks:
        key = f"[{layer}, {obj}, {stack}]"
        if key not in cube_matrix:
            cube_matrix[key] = []
        if person not in cube_matrix[key]:
            cube_matrix[key].append(person)


# ── Backup ───────────────────────────────────────────────────────
backup = db_file.with_suffix(
    f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
)
with open(backup, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"\nBackup: {backup}")


# ── Save cleaned database ────────────────────────────────────────
data['tests'] = kept
data['cube_matrix'] = cube_matrix

with open(db_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Saved:  {db_file}")
print(f"\n  Before: {len(tests)} test_runs")
print(f"  After:  {len(kept)} tests ({len(removed)} duplicates removed)")
print(f"  Cube:   {sum(len(v) for v in cube_matrix.values())} position entries")
print(f"\nRestart the app and regenerate BMC to see clean results.")


# ── Clean duplicate .docx files in tested/ folder ───────────
NAMING_PATTERN = re.compile(r'^Test Run_Packet_.+_completed\.docx$')

# Find tested folder from same search paths
tested_dirs = []
for base in [Path("BCM_Projects/project_caas_deployed"), Path("BCM_Projects")]:
    if base.exists():
        for d in base.rglob("tested"):
            if d.is_dir():
                tested_dirs.append(d)

if tested_dirs:
    print(f"\n{'='*60}")
    print("DOCX FILE CLEANUP — tested/ folders")
    print(f"{'='*60}\n")

    for idir in tested_dirs:
        docx_files = list(idir.glob("*.docx"))
        if not docx_files:
            continue

        print(f"  Folder: {idir}")
        print(f"  Files:  {len(docx_files)}")

        # Separate properly named vs non-standard
        proper = [f for f in docx_files if NAMING_PATTERN.match(f.name)]
        non_standard = [f for f in docx_files if not NAMING_PATTERN.match(f.name)]

        if not non_standard:
            print(f"  ✓ All files follow naming convention.\n")
            continue

        # Build size→proper_file lookup for duplicate detection
        proper_by_size = {}
        for f in proper:
            proper_by_size[f.stat().st_size] = f

        deleted = 0
        for bad_file in non_standard:
            bad_size = bad_file.stat().st_size
            if bad_size in proper_by_size:
                match = proper_by_size[bad_size]
                print(f"  DELETE: {bad_file.name}")
                print(f"         duplicate of {match.name} (same size: {bad_size:,} bytes)")
                bad_file.unlink()
                deleted += 1
            else:
                print(f"  ⚠ ORPHAN: {bad_file.name} ({bad_size:,} bytes)")
                print(f"         Does not match any Test Run_Packet_*_completed.docx")

        if deleted:
            print(f"\n  Removed {deleted} duplicate file(s).")
        remaining = list(idir.glob("*.docx"))
        print(f"  Final:  {len(remaining)} files\n")
else:
    print("\nNo tested/ folders found for file cleanup.")
