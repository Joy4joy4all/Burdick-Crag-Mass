"""
MOND Standalone Comparison
===========================
Stephen Justin Burdick, 2026

Reads SPARC .dat files directly.
Computes V_MOND from baryonic components.
Compares against V_obs.
No solver needed. Pure math.

Merges with existing substrate batch results.

Usage:
    python mond_comparison.py
    python mond_comparison.py --data-dir data/sparc_raw
    python mond_comparison.py --batch-file data/results/batch_20260325_093406.json
"""

import numpy as np
import os
import sys
import json
import time

# ─────────────────────────────────────────
# MOND PHYSICS
# ─────────────────────────────────────────

A0_SI = 1.2e-10       # Milgrom critical acceleration (m/s^2)
KPC_TO_M = 3.0857e19  # kpc to meters
KMS_TO_MS = 1000.0    # km/s to m/s


def compute_mond(v_baryonic, r_kpc):
    """MOND velocity from baryonic velocity. Simple interpolation mu(x)=x/(1+x)."""
    v_mond = np.zeros_like(v_baryonic)
    for i in range(len(v_baryonic)):
        v_n = v_baryonic[i] * KMS_TO_MS
        r = r_kpc[i] * KPC_TO_M
        if r <= 0 or v_n <= 0:
            v_mond[i] = v_baryonic[i]
            continue
        g_n = (v_n ** 2) / r
        x = g_n / A0_SI
        if x > 100:
            mu = 1.0
        elif x < 0.01:
            mu = x
        else:
            mu = x / (1.0 + x)
        g_mond = g_n / mu if mu > 0 else g_n
        v_mond[i] = np.sqrt(g_mond * r) / KMS_TO_MS
    return v_mond


# ─────────────────────────────────────────
# LOAD SPARC FILE
# ─────────────────────────────────────────

def load_dat(path):
    """Load a SPARC _rotmod.dat file. Returns arrays."""
    radii, vobs, errv, vgas, vdisk, vbul = [], [], [], [], [], []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            vals = line.split()
            if len(vals) < 6:
                continue
            radii.append(float(vals[0]))
            vobs.append(float(vals[1]))
            errv.append(float(vals[2]))
            vgas.append(float(vals[3]))
            vdisk.append(float(vals[4]))
            vbul.append(float(vals[5]))

    return {
        "radius": np.array(radii),
        "vobs": np.array(vobs),
        "errv": np.array(errv),
        "vgas": np.array(vgas),
        "vdisk": np.array(vdisk),
        "vbul": np.array(vbul),
    }


# ─────────────────────────────────────────
# COMPARE ONE GALAXY
# ─────────────────────────────────────────

def compare_galaxy(data):
    """Run Newton and MOND comparison against V_obs for one galaxy."""
    r = data["radius"]
    vobs = data["vobs"]
    vgas = data["vgas"]
    vdisk = data["vdisk"]
    vbul = data["vbul"]

    if len(r) < 3:
        return None

    # Baryonic Newtonian: V_bar^2 = Vgas^2 + Vdisk^2 + Vbul^2
    v_bar_sq = vgas**2 + vdisk**2 + vbul**2
    v_newton = np.sqrt(np.maximum(v_bar_sq, 0.0))

    # MOND from baryonic velocity
    v_mond = compute_mond(v_newton, r)

    # RMS errors
    rms_newton = np.sqrt(np.mean((v_newton - vobs)**2))
    rms_mond = np.sqrt(np.mean((v_mond - vobs)**2))

    # Shape correlations
    def corr(a, b):
        if np.std(a) > 0 and np.std(b) > 0:
            return np.corrcoef(a, b)[0, 1]
        return 0.0

    corr_newton = corr(v_newton, vobs)
    corr_mond = corr(v_mond, vobs)

    # Outer half
    n = len(r)
    o = slice(n // 2, n)
    if n > 4:
        outer_rms_newton = np.sqrt(np.mean((v_newton[o] - vobs[o])**2))
        outer_rms_mond = np.sqrt(np.mean((v_mond[o] - vobs[o])**2))
    else:
        outer_rms_newton = rms_newton
        outer_rms_mond = rms_mond

    # Winner (Newton vs MOND only)
    if abs(rms_newton - rms_mond) < 0.5:
        winner_nm = "TIE"
    elif rms_mond < rms_newton:
        winner_nm = "MOND"
    else:
        winner_nm = "NEWTON"

    return {
        "rms_newton": rms_newton,
        "rms_mond": rms_mond,
        "corr_newton": corr_newton,
        "corr_mond": corr_mond,
        "outer_rms_newton": outer_rms_newton,
        "outer_rms_mond": outer_rms_mond,
        "winner_nm": winner_nm,
        "mond_improvement": rms_newton - rms_mond,
        "v_max": np.max(vobs),
        "n_points": len(r),
        "r_max": np.max(r),
    }


# ─────────────────────────────────────────
# BATCH ALL GALAXIES
# ─────────────────────────────────────────

def run_all(data_dir):
    """Run MOND comparison on all .dat files in directory."""
    files = sorted([f for f in os.listdir(data_dir) if f.endswith('.dat')])
    results = {}
    for f in files:
        name = f.replace("_rotmod.dat", "").replace(".dat", "")
        path = os.path.join(data_dir, f)
        try:
            data = load_dat(path)
            comp = compare_galaxy(data)
            if comp is not None:
                results[name] = comp
        except Exception as e:
            print(f"  SKIP {name}: {e}")
    return results


# ─────────────────────────────────────────
# MERGE WITH SUBSTRATE BATCH
# ─────────────────────────────────────────

def merge_with_substrate(mond_results, substrate_batch_path):
    """Merge MOND results with existing substrate batch JSON."""
    with open(substrate_batch_path) as f:
        substrate = json.load(f)

    sub_dict = {d["galaxy"]: d for d in substrate}
    merged = []

    for name, mond in mond_results.items():
        entry = {
            "galaxy": name,
            "v_max": mond["v_max"],
            "n_points": mond["n_points"],
            "rms_newton": mond["rms_newton"],
            "rms_mond": mond["rms_mond"],
            "corr_newton": mond["corr_newton"],
            "corr_mond": mond["corr_mond"],
            "mond_improvement": mond["mond_improvement"],
        }

        if name in sub_dict:
            s = sub_dict[name]
            entry["corr_substrate_full"] = s.get("corr_full", 0)
            entry["corr_substrate_inner"] = s.get("corr_inner", 0)

        merged.append(entry)

    return merged


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MOND comparison on SPARC data")
    parser.add_argument("--data-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "data", "sparc_raw"))
    parser.add_argument("--batch-file", type=str, default=None,
                        help="Substrate batch JSON to merge with")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON path")
    args = parser.parse_args()

    print("=" * 60)
    print("  MOND STANDALONE COMPARISON")
    print("  Milgrom 1983, a0 = 1.2e-10 m/s^2")
    print("  Simple interpolation: mu(x) = x/(1+x)")
    print("=" * 60)

    if not os.path.exists(args.data_dir):
        print(f"\n  Data directory not found: {args.data_dir}")
        sys.exit(1)

    t0 = time.time()
    results = run_all(args.data_dir)
    elapsed = time.time() - t0

    print(f"\n  Processed {len(results)} galaxies in {elapsed:.1f}s")

    # ── Summary ──
    mond_wins = sum(1 for r in results.values() if r["winner_nm"] == "MOND")
    newton_wins = sum(1 for r in results.values() if r["winner_nm"] == "NEWTON")
    ties = sum(1 for r in results.values() if r["winner_nm"] == "TIE")

    rms_newtons = [r["rms_newton"] for r in results.values()]
    rms_monds = [r["rms_mond"] for r in results.values()]

    print(f"\n  {'='*55}")
    print(f"  NEWTON vs MOND (no substrate)")
    print(f"  {'='*55}")
    print(f"  MOND wins:   {mond_wins} / {len(results)}")
    print(f"  Newton wins: {newton_wins} / {len(results)}")
    print(f"  Ties:        {ties} / {len(results)}")
    print(f"\n  Avg RMS Newton: {np.mean(rms_newtons):.2f} km/s")
    print(f"  Avg RMS MOND:   {np.mean(rms_monds):.2f} km/s")
    print(f"  Avg MOND improvement: {np.mean(rms_newtons) - np.mean(rms_monds):+.2f} km/s")

    # ── By mass bracket ──
    print(f"\n  BY MASS BRACKET:")
    print(f"  {'Bracket':<28} {'N':>4} {'MOND wins':>10} {'Newton wins':>12} {'Avg ΔRMS':>10}")
    print(f"  {'─'*28} {'─'*4} {'─'*10} {'─'*12} {'─'*10}")

    brackets = [
        ("V < 50 (dwarf)", lambda r: r["v_max"] < 50),
        ("50-100 (low)", lambda r: 50 <= r["v_max"] < 100),
        ("100-150 (mid)", lambda r: 100 <= r["v_max"] < 150),
        ("150-200 (high)", lambda r: 150 <= r["v_max"] < 200),
        ("V > 200 (massive)", lambda r: r["v_max"] >= 200),
    ]

    for label, filt in brackets:
        subset = {k: v for k, v in results.items() if filt(v)}
        if subset:
            mw = sum(1 for r in subset.values() if r["winner_nm"] == "MOND")
            nw = sum(1 for r in subset.values() if r["winner_nm"] == "NEWTON")
            avg_imp = np.mean([r["mond_improvement"] for r in subset.values()])
            print(f"  {label:<28} {len(subset):>4} {mw:>10} {nw:>12} {avg_imp:>+10.2f}")

    # ── Top and bottom ──
    sorted_by_imp = sorted(results.items(), key=lambda x: x[1]["mond_improvement"], reverse=True)

    print(f"\n  TOP 10 MOND WINS (by RMS improvement over Newton):")
    for name, r in sorted_by_imp[:10]:
        print(f"    {name:<18} Newton={r['rms_newton']:6.1f}  MOND={r['rms_mond']:6.1f}"
              f"  Δ={r['mond_improvement']:+6.1f}  V={r['v_max']:.0f}")

    print(f"\n  TOP 10 NEWTON WINS (MOND worse than Newton):")
    for name, r in sorted_by_imp[-10:]:
        print(f"    {name:<18} Newton={r['rms_newton']:6.1f}  MOND={r['rms_mond']:6.1f}"
              f"  Δ={r['mond_improvement']:+6.1f}  V={r['v_max']:.0f}")

    # ── Merge with substrate if available ──
    if args.batch_file and os.path.exists(args.batch_file):
        print(f"\n  Merging with substrate results: {args.batch_file}")
        merged = merge_with_substrate(results, args.batch_file)

        # Three-way comparison
        three_way = [m for m in merged if "corr_substrate_inner" in m]
        if three_way:
            print(f"\n  {'='*55}")
            print(f"  THREE-WAY COMPARISON: {len(three_way)} galaxies")
            print(f"  {'='*55}")
            print(f"  {'Galaxy':<16} {'RMS_N':>7} {'RMS_M':>7} {'Sub_inner':>10} {'Best':>10}")
            print(f"  {'─'*16} {'─'*7} {'─'*7} {'─'*10} {'─'*10}")

            for m in sorted(three_way, key=lambda x: x.get("corr_substrate_inner", 0), reverse=True)[:20]:
                best = "MOND" if m["rms_mond"] < m["rms_newton"] else "NEWTON"
                si = m.get("corr_substrate_inner", 0)
                print(f"  {m['galaxy']:<16} {m['rms_newton']:>7.1f} {m['rms_mond']:>7.1f}"
                      f" {si:>+10.4f} {best:>10}")

    # ── Save ──
    out_path = args.output
    if out_path is None:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir,
                                f"mond_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {name: {
        "rms_newton": r["rms_newton"],
        "rms_mond": r["rms_mond"],
        "corr_newton": r["corr_newton"],
        "corr_mond": r["corr_mond"],
        "mond_improvement": r["mond_improvement"],
        "winner": r["winner_nm"],
        "v_max": r["v_max"],
    } for name, r in results.items()}

    with open(out_path, 'w') as f:
        json.dump(out_data, f, indent=2)
    print(f"\n  Saved: {out_path}")
    print(f"\n  Done.")
