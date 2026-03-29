"""
SPARC Data Download & Setup
============================
Stephen Justin Burdick, 2026

Run this on your Windows machine to download SPARC rotation curves
and verify the data feed into the substrate solver.

Usage:
    python setup_sparc.py

Downloads from:
    http://astroweb.cwru.edu/SPARC/Rotmod_LTG.zip
    (175 galaxy rotation curve files)

Credit: Lelli, McGaugh, Schombert (2016)
        DOI: 10.5281/zenodo.16284118
"""

import os
import sys
import zipfile
import urllib.request

# ─────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data", "sparc_raw")
ZIP_PATH = os.path.join(DATA_DIR, "Rotmod_LTG.zip")

SPARC_URL = "http://astroweb.cwru.edu/SPARC/Rotmod_LTG.zip"

# Also grab the galaxy properties table
TABLE_URL = "http://astroweb.cwru.edu/SPARC/SPARC_Lelli2016c.mrt"
TABLE_PATH = os.path.join(DATA_DIR, "SPARC_Lelli2016c.mrt")


# ─────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────

def download_file(url, dest):
    """Download with progress."""
    print(f"  Downloading: {url}")
    print(f"  To: {dest}")

    def report(block, block_size, total):
        downloaded = block * block_size
        if total > 0:
            pct = min(100, downloaded * 100 / total)
            mb = downloaded / (1024 * 1024)
            print(f"\r  {pct:.0f}% ({mb:.1f} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, dest, report)
        print(f"\n  Done: {os.path.getsize(dest)} bytes")
        return True
    except Exception as e:
        print(f"\n  ERROR: {e}")
        print(f"  Manual download: {url}")
        print(f"  Place in: {DATA_DIR}")
        return False


# ─────────────────────────────────────────
# EXTRACT
# ─────────────────────────────────────────

def extract_zip(zip_path, dest_dir):
    """Extract rotation curve files."""
    print(f"  Extracting: {zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = zf.namelist()
        print(f"  Files in archive: {len(members)}")

        for member in members:
            # Extract to flat directory (ignore internal paths)
            filename = os.path.basename(member)
            if filename and filename.endswith('.dat'):
                source = zf.open(member)
                target_path = os.path.join(dest_dir, filename)
                with open(target_path, 'wb') as target:
                    target.write(source.read())

    dat_files = [f for f in os.listdir(dest_dir) if f.endswith('.dat')]
    print(f"  Extracted {len(dat_files)} .dat files")
    return dat_files


# ─────────────────────────────────────────
# VERIFY
# ─────────────────────────────────────────

def verify_data(data_dir):
    """Check that files are readable and properly formatted."""
    dat_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.dat')])
    print(f"\n  Verifying {len(dat_files)} rotation curve files...")

    good = 0
    bad = 0
    galaxies = []

    for f in dat_files:
        path = os.path.join(data_dir, f)
        try:
            with open(path, 'r') as fh:
                lines = [l.strip() for l in fh if l.strip() and not l.startswith('#')]

            if len(lines) < 3:
                print(f"    WARN: {f} — only {len(lines)} data lines")
                bad += 1
                continue

            # Check first data line has expected columns
            parts = lines[0].split()
            if len(parts) < 4:
                print(f"    WARN: {f} — only {len(parts)} columns")
                bad += 1
                continue

            # Parse and check ranges
            radii = []
            vobs = []
            for line in lines:
                vals = line.split()
                radii.append(float(vals[0]))
                vobs.append(float(vals[1]))

            name = f.replace("_rotmod.dat", "").replace(".dat", "")
            galaxies.append({
                "name": name,
                "file": f,
                "n_points": len(lines),
                "r_max": max(radii),
                "v_max": max(vobs),
            })
            good += 1

        except Exception as e:
            print(f"    ERROR: {f} — {e}")
            bad += 1

    print(f"\n  Results: {good} good, {bad} bad out of {len(dat_files)}")

    if galaxies:
        # Sort by max velocity (most massive first)
        galaxies.sort(key=lambda g: g["v_max"], reverse=True)

        print(f"\n  TOP 10 GALAXIES BY V_MAX:")
        print(f"  {'Name':<16} {'Points':>8} {'R_max kpc':>10} {'V_max km/s':>12}")
        print(f"  {'─'*16} {'─'*8} {'─'*10} {'─'*12}")
        for g in galaxies[:10]:
            print(f"  {g['name']:<16} {g['n_points']:>8} "
                  f"{g['r_max']:>10.1f} {g['v_max']:>12.1f}")

        print(f"\n  RECOMMENDED TEST GALAXIES:")
        print(f"  (diverse range of masses and rotation profiles)")

        # Pick diverse set
        picks = []
        if len(galaxies) > 0: picks.append(galaxies[0])          # highest V
        if len(galaxies) > 5: picks.append(galaxies[5])           # mid-high
        if len(galaxies) > len(galaxies)//2:
            picks.append(galaxies[len(galaxies)//2])              # median
        if len(galaxies) > 3:
            picks.append(galaxies[-3])                             # low V
        # Classic test case NGC2403 if present
        ngc2403 = [g for g in galaxies if "NGC2403" in g["name"]]
        if ngc2403:
            picks.append(ngc2403[0])

        for g in picks:
            print(f"    {g['name']:<16} V_max={g['v_max']:.0f} km/s  "
                  f"R_max={g['r_max']:.1f} kpc  ({g['n_points']} pts)")

    return galaxies


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  SPARC DATA DOWNLOAD & SETUP")
    print("  175 Galaxy Rotation Curves")
    print("=" * 60)

    # Create directories
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(SCRIPT_DIR, "data", "results"), exist_ok=True)

    # Check if already downloaded
    dat_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.dat')]

    if len(dat_files) >= 100:
        print(f"\n  Data already present: {len(dat_files)} .dat files")
        print(f"  Skipping download. Verifying...")
    else:
        # Download
        print(f"\n  Step 1: Download rotation curves")
        if download_file(SPARC_URL, ZIP_PATH):
            print(f"\n  Step 2: Extract")
            extract_zip(ZIP_PATH, DATA_DIR)
        else:
            print(f"\n  MANUAL DOWNLOAD INSTRUCTIONS:")
            print(f"  1. Open browser to: {SPARC_URL}")
            print(f"  2. Save Rotmod_LTG.zip to: {DATA_DIR}")
            print(f"  3. Extract all .dat files into: {DATA_DIR}")
            print(f"  4. Re-run this script to verify")
            sys.exit(1)

        # Also grab properties table
        print(f"\n  Step 3: Download galaxy properties table")
        download_file(TABLE_URL, TABLE_PATH)

    # Verify
    print(f"\n  Step 4: Verify data")
    galaxies = verify_data(DATA_DIR)

    if galaxies:
        print(f"\n  ✓ READY. {len(galaxies)} galaxies loaded.")
        print(f"\n  NEXT STEPS:")
        print(f"  1. python solvers/run_layers.py --layers 4 6 12 42 72")
        print(f"  2. python solvers/run_sparc.py --galaxy {galaxies[0]['name']}")
        print(f"  3. python solvers/run_sparc.py --max-galaxies 10")
    else:
        print(f"\n  ✗ No valid galaxies found. Check data directory.")
