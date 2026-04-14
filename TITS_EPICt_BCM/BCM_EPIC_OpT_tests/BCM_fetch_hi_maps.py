"""
BCM_fetch_hi_maps.py
=====================
Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC
NSF I-Corps — Team GIBUSH

Single script. One run. No garbage gets through.

Pipeline per galaxy:
  1. Try THINGS direct FITS (highest quality)
  2. Try astroquery SkyView HI4PI
  3. Validate immediately — delete if corrupt
  4. Write PENDING instructions if all sources fail

Usage:
    python BCM_fetch_hi_maps.py
    python BCM_fetch_hi_maps.py --check
    python BCM_fetch_hi_maps.py --galaxy NGC0801
"""

import os, sys, time, json, urllib.request, urllib.parse, argparse
import numpy as np

def resolve_coords(name):
    """Resolve galaxy name to RA/Dec via SIMBAD for reliable SkyView queries."""
    try:
        from astroquery.simbad import Simbad
        result = Simbad.query_object(name)
        if result is None:
            return None
        ra  = result['RA'][0]
        dec = result['DEC'][0]
        return f"{ra} {dec}"
    except Exception:
        return None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HI_MAP_DIR = os.path.join(SCRIPT_DIR, "data", "hi_maps")

# ─────────────────────────────────────────
# 48 LOSS GALAXIES
# ─────────────────────────────────────────

LOSS_GALAXIES = {
    "NGC0801":    "Extreme Warp Class IV",
    "NGC2976":    "Ram Pressure Class V-A",
    "NGC3953":    "Barred Pipe Class VI",
    "NGC3992":    "Barred Logic",
    "NGC3972":    "Topological Fix",
    "NGC4100":    "Warp Mapping",
    "NGC4138":    "Core Rotation",
    "NGC7793":    "Void/Theft Class V-B",
    "UGC04305":   "Holmberg II",
    "NGC2683":    "Edge-On Depth",
    "NGC5907":    "Giant Warp",
    "UGC11914":   "Giant LSB",
    "NGC2955":    "High-Loss",
    "UGC05253":   "Core Shear",
    "UGC09133":   "Asymmetry",
    "UGC11455":   "Extended Disk",
    "UGC02953":   "High-Mass Warp",
    "NGC2998":    "Substrate Wake",
    "UGC02916":   "Pressure Slosh",
    "NGC5371":    "Topological Bias",
    "UGC03205":   "LSB Geometry",
    "ESO563-G021":"Velocity Slosh",
    "UGC07261":   "Impedance Fix",
    "UGC06787":   "Density Peak",
    "UGC07089":   "Gradient Mapping",
    "NGC0024":    "LSB Center-Shift",
    "NGC3877":    "Shear Layers",
    "UGC08699":   "Relativistic Lag",
    "NGC1090":    "Warp Alignment",
    "NGC3917":    "Extended Flow",
    "NGC4010":    "Edge-On Slosh",
    "NGC6195":    "High-Mass Shear",
    "NGC7814":    "Bulge Distortion",
    "UGC05750":   "LSB Warp",
    "UGC06399":   "Non-Circular Fix",
    "UGC06628":   "Density Lambda",
    "UGC07323":   "Shear Gradient",
    "UGC07577":   "Low-Mass Coherence",
    "UGC09992":   "Substrate Wake",
    "CamB":       "LSB Throttle",
    "ESO079-G014":"2D Moment-0",
    "F561-1":     "Low-Mass Coherence",
    "F563-V1":    "Substrate Ripple",
    "F579-V1":    "High-V Impedance",
    "IC4202":     "Massive Spiral",
    "KK98-251":   "LSB Coherence",
    "UGCA281":    "Ripple Control",
    "NGC4010":    "Edge-On Slosh",
}

# THINGS catalog mapping
THINGS_BASE = "https://www2.mpia-hd.mpg.de/THINGS/Data_files/"
THINGS_FILES = {
    "NGC2976":  "NGC_2976_NA_MOM0_THINGS.FITS",
    "NGC3992":  "NGC_3992_NA_MOM0_THINGS.FITS",
    "NGC3972":  "NGC_3972_NA_MOM0_THINGS.FITS",
    "NGC4100":  "NGC_4100_NA_MOM0_THINGS.FITS",
    "NGC4138":  "NGC_4138_NA_MOM0_THINGS.FITS",
    "NGC7793":  "NGC_7793_NA_MOM0_THINGS.FITS",
    "UGC04305": "UGC_04305_NA_MOM0_THINGS.FITS",
}

# ─────────────────────────────────────────
# WHISP TARGETS — Known coordinates
# Bypasses SIMBAD resolution entirely
# ─────────────────────────────────────────

WHISP_TARGETS = {
    "NGC0801":  {"ra":"02:03:45", "dec":"+38:15:33",
                 "fits":"whisp_ngc0801_cube.fits",   "notes":"Class IV Bow"},
    "NGC2998":  {"ra":"09:48:43", "dec":"+44:04:54",
                 "fits":"whisp_ngc2998_cube.fits",   "notes":"Large Scale Warp"},
    "NGC3953":  {"ra":"11:53:48", "dec":"+52:19:36",
                 "fits":"whisp_ngc3953_cube.fits",   "notes":"Class VI Bar Dipole"},
    "NGC3992":  {"ra":"11:57:35", "dec":"+53:22:24",
                 "fits":"whisp_ngc3992_cube.fits",   "notes":"Bar-Channeled Flux"},
    "UGC02916": {"ra":"03:59:16", "dec":"+33:28:43",
                 "fits":"whisp_ugc02916_cube.fits",  "notes":"Pressure Slosh"},
    "UGC05253": {"ra":"09:49:15", "dec":"+18:31:37",
                 "fits":"whisp_ugc05253_cube.fits",  "notes":"Core Shear Layer"},
    "UGC09133": {"ra":"14:17:15", "dec":"+23:40:31",
                 "fits":"whisp_ugc09133_cube.fits",  "notes":"2D Asymmetry"},
    "UGC11914": {"ra":"22:04:41", "dec":"+35:36:18",
                 "fits":"whisp_ugc11914_cube.fits",  "notes":"Giant LSB Warp"},
}

def try_skyview_by_coords(ra, dec, dest, size=0.5, pixels=256):
    """
    Query SkyView using known RA/Dec — bypasses name resolution.
    More reliable than name-based queries.
    """
    try:
        from astroquery.skyview import SkyView
        import astropy.units as u
        from astropy.coordinates import SkyCoord

        coord = SkyCoord(ra=ra, dec=dec, unit=("hourangle","deg"))
        pos_str = f"{coord.ra.deg:.6f} {coord.dec.deg:.6f}"

        for survey in ["HI4PI"]:
            try:
                print(f"    SkyView coord [{survey}] {pos_str[:25]}...",
                      end="", flush=True)
                images = SkyView.get_images(
                    position=pos_str,
                    survey=[survey],
                    pixels=pixels,
                    radius=size*u.deg,
                )
                if not images:
                    print(" no images")
                    continue
                images[0].writeto(dest, overwrite=True)
                valid, info = validate_fits(dest)
                if valid:
                    print(f" VALID — {info}")
                    return True
                else:
                    if os.path.exists(dest): os.remove(dest)
                    print(f" INVALID — {info}")
            except Exception as e:
                print(f" {str(e)[:60]}")
            time.sleep(1.5)
    except ImportError:
        print("    astroquery not available")
    return False

# ─────────────────────────────────────────
# WHISP DIRECT DOWNLOAD
# ─────────────────────────────────────────

# Known WHISP datacube base URLs — tried in order
WHISP_BASES = [
    "https://www.astron.nl/~whisp/data/",
    "https://www.astron.nl/research-software/whisp/data/",
]

def try_whisp_direct(name, dest):
    """
    Attempt direct WHISP archive download for galaxies in WHISP_TARGETS.
    Tries multiple base URLs and filename patterns.
    Falls back gracefully — never raises.
    """
    if name not in WHISP_TARGETS:
        return False

    wt = WHISP_TARGETS[name]
    fits_file = wt.get("fits", f"whisp_{name.lower().replace(' ','')}_cube.fits")

    # Filename variants WHISP has used historically
    name_lower = name.lower().replace("gc", "gc_").replace("ugc", "ugc_")
    variants = [
        fits_file,
        f"{name}_NA_MOM0_WHISP.fits",
        f"{name}_HI_mom0.fits",
        f"whisp_{name.lower()}_mom0.fits",
    ]

    for base in WHISP_BASES:
        for variant in variants:
            url = base + variant
            print(f"    WHISP {variant[:45]}...", end="", flush=True)
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "BCM-Fetch/1.0 (Emerald Entities LLC)"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
                if len(data) < 5000:
                    print(f" too small ({len(data)}B)")
                    continue
                with open(dest, 'wb') as f:
                    f.write(data)
                valid, info = validate_fits(dest)
                if valid:
                    print(f" VALID — {info}")
                    return True
                else:
                    if os.path.exists(dest):
                        os.remove(dest)
                    print(f" INVALID — {info}")
            except urllib.error.HTTPError as e:
                print(f" HTTP {e.code}")
            except Exception as e:
                print(f" {str(e)[:50]}")
            time.sleep(0.5)

    return False


# ─────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────

def validate_fits(path):
    """
    Returns (is_valid, info_str).
    Valid = FITS with physical float values.
    Invalid = raw bytes misread as float (huge integers).
    """
    try:
        from astropy.io import fits
        with fits.open(path) as hdul:
            data = hdul[0].data
            if data is None:
                return False, "no data"
            data = np.squeeze(data).astype(np.float64)
            data = np.nan_to_num(data, nan=0.0)
            max_val = float(np.max(np.abs(data)))
            # Physical HI flux: typically 0.001 to 10000 Jy/beam*km/s
            # Corrupt SkyView returns: max > 1e15 (raw bytes as float64)
            if max_val > 1e12:
                return False, f"corrupt max={max_val:.2e}"
            if max_val == 0:
                return False, "all zeros"
            nonzero = int(np.sum(data != 0))
            if nonzero < 500:
                return False, f"too sparse nonzero={nonzero}"
            shape = data.shape
            return True, f"shape={shape} max={max_val:.2f} nonzero={nonzero}"
    except Exception as e:
        return False, str(e)[:60]

# ─────────────────────────────────────────
# DOWNLOAD + VALIDATE
# ─────────────────────────────────────────

def try_download(url, dest, label, timeout=30):
    """Download URL, validate immediately. Returns True only if real data."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "BCM-Fetch/1.0 (Emerald Entities LLC)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if len(data) < 5000:
            print(f"    {label}: too small ({len(data)} bytes)")
            return False
        with open(dest, 'wb') as f:
            f.write(data)
        # Validate immediately
        valid, info = validate_fits(dest)
        if valid:
            print(f"    {label}: VALID — {info}")
            return True
        else:
            os.remove(dest)
            print(f"    {label}: INVALID — {info} — deleted")
            return False
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        print(f"    {label}: FAIL — {str(e)[:60]}")
        return False

def try_astroquery(name, dest):
    """Fetch via astroquery SkyView with validation."""
    try:
        from astroquery.skyview import SkyView
        import astropy.units as u
        # Resolve coords via SIMBAD for reliable lookup
        pos = resolve_coords(name)
        if pos:
            print(f"    SIMBAD resolved: {pos[:30]}")
        else:
            pos = name
            print(f"    SIMBAD failed — using name directly")
        for survey in ["HI4PI", "GALFA-HI"]:
            try:
                print(f"    astroquery [{survey}]...", end="", flush=True)
                images = SkyView.get_images(
                    position=pos,
                    survey=[survey],
                    pixels=256,
                    radius=0.5*u.deg,
                )
                if not images:
                    print(" no images")
                    continue
                images[0].writeto(dest, overwrite=True)
                valid, info = validate_fits(dest)
                if valid:
                    print(f" VALID — {info}")
                    return True
                else:
                    if os.path.exists(dest):
                        os.remove(dest)
                    print(f" INVALID — {info}")
            except Exception as e:
                print(f" {str(e)[:50]}")
            time.sleep(1.5)
    except ImportError:
        print("    astroquery not available")
    return False

# ─────────────────────────────────────────
# PENDING INSTRUCTIONS
# ─────────────────────────────────────────

def write_pending(name, notes, out_dir):
    path = os.path.join(out_dir, f"{name}_mom0_PENDING.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"BCM OFFSET - PENDING: {name}\n")
        f.write(f"Notes: {notes}\n\n")
        f.write(f"DOWNLOAD MANUALLY:\n\n")
        f.write(f"Option 1 - NASA SkyView browser:\n")
        f.write(f"  https://skyview.gsfc.nasa.gov/current/cgi/query.pl\n")
        f.write(f"  Object: {name}\n")
        f.write(f"  Survey: HI4PI\n")
        f.write(f"  Pixels: 256  Size: 0.5 deg  Return: FITS\n\n")
        f.write(f"Option 2 - NASA NED:\n")
        f.write(f"  https://ned.ipac.caltech.edu/\n")
        f.write(f"  Search: {name} > Images > HI 21cm > FITS\n\n")
        f.write(f"Option 3 - ESO Archive:\n")
        f.write(f"  https://archive.eso.org/scienceportal/home\n")
        f.write(f"  Target: {name} > HI radio\n\n")
        f.write(f"Save as: {os.path.join(out_dir, name)}_mom0.fits\n")

# ─────────────────────────────────────────
# FETCH ONE GALAXY
# ─────────────────────────────────────────

def fetch_galaxy(name, notes, out_dir):
    dest = os.path.join(out_dir, f"{name}_mom0.fits")

    # Already have it?
    if os.path.exists(dest):
        valid, info = validate_fits(dest)
        if valid:
            size_kb = os.path.getsize(dest) // 1024
            print(f"  HAVE {name:<16} {size_kb}KB — {info[:40]}")
            return "READY"
        else:
            os.remove(dest)
            print(f"  BAD  {name:<16} deleted corrupt file")

    print(f"\n  {name:<16} {notes}")

    # Try THINGS first
    if name in THINGS_FILES:
        url = THINGS_BASE + THINGS_FILES[name]
        if try_download(url, dest, "THINGS"):
            return "READY"

    # Try WHISP direct download first for known WHISP targets
    if name in WHISP_TARGETS:
        if try_whisp_direct(name, dest):
            return "READY"

    # Try coordinate-based SkyView for WHISP targets
    if name in WHISP_TARGETS:
        wt = WHISP_TARGETS[name]
        print(f"    Using known coords: {wt['ra']} {wt['dec']}")
        if try_skyview_by_coords(wt["ra"], wt["dec"], dest):
            return "READY"

    # Try astroquery name-based fallback
    if try_astroquery(name, dest):
        return "READY"

    # Write pending with failure mode noted
    write_pending(name, notes, out_dir)
    # Log failure mode — correlates with galaxy class
    fail_log = os.path.join(out_dir, "BCM_fetch_failures.json")
    try:
        failures = json.load(open(fail_log)) if os.path.exists(fail_log) else {}
        failures[name] = {"notes": notes, "status": "PENDING",
                          "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        with open(fail_log, 'w', encoding='utf-8') as f:
            json.dump(failures, f, indent=2)
    except Exception:
        pass
    return "PENDING"

# ─────────────────────────────────────────
# STATUS CHECK
# ─────────────────────────────────────────

def check_status(out_dir):
    if not os.path.exists(out_dir):
        print(f"  Directory not found: {out_dir}")
        return
    ready = pend = 0
    print(f"\n  {'Galaxy':<16} {'Status':<10} Info")
    print(f"  {'─'*16} {'─'*10} {'─'*40}")
    for name in sorted(LOSS_GALAXIES):
        fits = os.path.join(out_dir, f"{name}_mom0.fits")
        pend_f = os.path.join(out_dir, f"{name}_mom0_PENDING.txt")
        if os.path.exists(fits):
            valid, info = validate_fits(fits)
            size_kb = os.path.getsize(fits) // 1024
            status = "READY" if valid else "CORRUPT"
            print(f"  {name:<16} {status:<10} {size_kb}KB {info[:35]}")
            if valid: ready += 1
        elif os.path.exists(pend_f):
            print(f"  {name:<16} {'PENDING':<10} manual download needed")
            pend += 1
        else:
            print(f"  {name:<16} {'MISSING':<10}")
    print(f"\n  READY: {ready}  PENDING: {pend}  MISSING: {len(LOSS_GALAXIES)-ready-pend}")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check",   action="store_true")
    parser.add_argument("--galaxy",  type=str, default=None)
    args = parser.parse_args()

    os.makedirs(HI_MAP_DIR, exist_ok=True)

    print("=" * 60)
    print("  BCM OFFSET — HI MAP FETCH WITH VALIDATION")
    print("  Burdick Crag Mass 2026 — Emerald Entities LLC")
    print("=" * 60)
    print(f"  Output: {HI_MAP_DIR}\n")

    if args.check:
        check_status(HI_MAP_DIR)
        sys.exit(0)

    targets = ({args.galaxy: LOSS_GALAXIES[args.galaxy]}
               if args.galaxy and args.galaxy in LOSS_GALAXIES
               else LOSS_GALAXIES)

    results = {"READY": [], "PENDING": []}
    for name, notes in sorted(targets.items()):
        status = fetch_galaxy(name, notes, HI_MAP_DIR)
        results[status].append(name)
        time.sleep(0.3)

    # Summary
    print(f"\n{'='*60}")
    print(f"  READY (real 2D data): {len(results['READY'])}")
    for n in results["READY"]:
        print(f"    {n}")
    print(f"\n  PENDING (manual download): {len(results['PENDING'])}")
    for n in results["PENDING"]:
        print(f"    {n}  -> {n}_mom0_PENDING.txt")

    # Save registry
    reg = {}
    for name, notes in LOSS_GALAXIES.items():
        fits = os.path.join(HI_MAP_DIR, f"{name}_mom0.fits")
        pend = os.path.join(HI_MAP_DIR, f"{name}_mom0_PENDING.txt")
        valid = False
        if os.path.exists(fits):
            valid, _ = validate_fits(fits)
        reg[name] = {
            "notes": notes,
            "status": "READY" if valid else
                      "PENDING" if os.path.exists(pend) else "MISSING",
            "size_kb": os.path.getsize(fits)//1024 if os.path.exists(fits) else 0,
        }
    reg_path = os.path.join(HI_MAP_DIR, "BCM_offset_registry.json")
    with open(reg_path, 'w', encoding='utf-8') as f:
        json.dump(reg, f, indent=2)
    print(f"\n  Registry: {reg_path}")
    print(f"\n  BCM_OFFSET panel will use 2D for {len(results['READY'])} galaxies.")
    print(f"  Remaining {len(results['PENDING'])} fall back to classic 1D.")
