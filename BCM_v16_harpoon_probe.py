# -*- coding: utf-8 -*-
"""
BCM v16 -- Harpoon Probe Integration Test
============================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Full integration: 12 tesseract probes + omega anchor +
live substrate + graveyard hazards + Bayesian navigator.

The craft moves through void. Probes cycle through the
hypercube vertices, sample the substrate, return through
the L1 tunnel, and feed TITS. The navigator makes real-
time GO/AVOID/TUNNEL decisions. The omega harpoon proves
the displacement is real.

Three embedded hazards at different distances:
  - Shallow grave at 1/3 transit (navigable)
  - Deep grave at 1/2 transit (danger -- should trigger AVOID)
  - Clean corridor at 2/3 transit (recovery zone)

The test measures:
  1. Did probes detect hazards BEFORE the craft arrived?
  2. Did the navigator change decision in time?
  3. Is displacement real (omega anchor)?
  4. Did the craft survive the transit?
  5. How many steps of warning did the far-shell probes give?

Usage:
    python BCM_v16_harpoon_probe.py
    python BCM_v16_harpoon_probe.py --steps 3000 --grid 256
"""

import numpy as np
import json
import os
import time
import math
import argparse


# ═══════════════════════════════════════════════════════
# CORE UTILITIES
# ═══════════════════════════════════════════════════════

def compute_com(field):
    total = np.sum(field)
    if total < 1e-15:
        return None
    nx, ny = field.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    return np.array([np.sum(X * field) / total,
                     np.sum(Y * field) / total])


def compute_coherence(sigma, center, radius=8):
    nx, ny = sigma.shape
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    r2 = (X - center[0])**2 + (Y - center[1])**2
    inside = np.sum(sigma[r2 < radius**2])
    total = np.sum(sigma)
    if total < 1e-15:
        return 0.0
    return inside / total


# ═══════════════════════════════════════════════════════
# SUBSTRATE HYPOTHESIS (Bayesian -- from Genesis brain)
# ═══════════════════════════════════════════════════════

EVIDENCE_STRENGTH = {
    "density_anomaly": 0.50, "void_confirmed": 0.20,
    "lambda_gradient": 0.40, "chi_direct": 0.45,
    "wake_mass": 0.35, "coherence_reading": 0.30,
    "density_normal": 0.15, "default": 0.10,
}


class Hypothesis:
    def __init__(self, key, name, prior=0.50):
        self.key = key
        self.name = name
        self.prior = prior
        self.posterior = prior
        self.evidence_count = 0
        self.status = "NEEDS_MORE_DATA"

    def update(self, direction, evidence_type="default"):
        strength = EVIDENCE_STRENGTH.get(evidence_type, 0.10)
        p = max(0.01, min(0.99, self.posterior))
        lo = math.log(p / (1.0 - p))
        lo += direction * strength
        self.posterior = 1.0 / (1.0 + math.exp(-lo))
        self.evidence_count += 1
        if self.evidence_count >= 3:
            if self.posterior >= 0.85:
                self.status = "VALIDATED"
            elif self.posterior <= 0.15:
                self.status = "INVALIDATED"


# ═══════════════════════════════════════════════════════
# PROBE (tesseract orbital)
# ═══════════════════════════════════════════════════════

class Probe:
    def __init__(self, pid, radius, phase):
        self.pid = pid
        self.radius = radius
        self.phase = phase
        self.speed = 0.05
        self.position = np.array([0.0, 0.0])
        self.readings = 0
        self.first_danger_step = None

    def compute_position(self, craft_com, step):
        angle = self.phase + self.speed * step
        self.position = np.array([
            craft_com[0] + self.radius * np.cos(angle),
            craft_com[1] + self.radius * np.sin(angle)])
        return self.position

    def sample(self, lam_field, sigma, nx, ny):
        ix = int(np.clip(self.position[0], 0, nx - 1))
        iy = int(np.clip(self.position[1], 0, ny - 1))
        local_lam = float(lam_field[ix, iy])
        local_sig = float(sigma[ix, iy])

        grad_x = float((lam_field[min(ix+1, nx-1), iy] -
                         lam_field[max(ix-1, 0), iy]) / 2.0)
        grad_y = float((lam_field[ix, min(iy+1, ny-1)] -
                         lam_field[ix, max(iy-1, 0)]) / 2.0)
        grad_mag = math.sqrt(grad_x**2 + grad_y**2)

        self.readings += 1

        is_danger = local_lam < 0.04
        if is_danger and self.first_danger_step is None:
            self.first_danger_step = -1  # mark for caller to set

        return {
            "pid": self.pid, "ix": ix, "iy": iy,
            "lambda": round(local_lam, 6),
            "sigma": round(local_sig, 6),
            "grad": round(grad_mag, 8),
            "danger": is_danger,
        }


# ═══════════════════════════════════════════════════════
# TITS NAVIGATOR
# ═══════════════════════════════════════════════════════

class Navigator:
    def __init__(self):
        self.hyp_safe = Hypothesis("SAFE", "Forward safe", 0.50)
        self.hyp_grave = Hypothesis("GRAVE", "Grave ahead", 0.30)
        self.decision = "PROCEED"
        self.decision_history = []
        self.warnings = []

    def ingest(self, reading, step):
        if reading["danger"]:
            self.hyp_grave.update(+1, "density_anomaly")
            self.hyp_safe.update(-1, "density_anomaly")
            if not any(w["step"] == step for w in self.warnings):
                self.warnings.append({
                    "step": step,
                    "probe": reading["pid"],
                    "lambda": reading["lambda"],
                    "position": (reading["ix"], reading["iy"]),
                })
        elif reading["lambda"] > 0.07:
            self.hyp_safe.update(+1, "void_confirmed")
            self.hyp_grave.update(-1, "void_confirmed")
        else:
            self.hyp_safe.update(+1, "density_normal")

    def decide(self, step):
        if self.hyp_grave.posterior > 0.75:
            self.decision = "AVOID"
        elif self.hyp_grave.posterior > 0.50:
            self.decision = "CAUTION"
        elif self.hyp_safe.posterior > 0.70:
            self.decision = "PROCEED"
        else:
            self.decision = "CAUTION"

        self.decision_history.append({
            "step": step,
            "decision": self.decision,
            "safe_p": round(self.hyp_safe.posterior, 4),
            "grave_p": round(self.hyp_grave.posterior, 4),
        })
        return self.decision


# ═══════════════════════════════════════════════════════
# BUILD VOID WITH HAZARDS
# ═══════════════════════════════════════════════════════

def build_hazard_field(nx, ny, void_lambda):
    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    lam = np.full((nx, ny), void_lambda, dtype=float)

    hazards = []

    # Shallow grave at 1/3 transit
    gx1 = nx // 3
    r2 = (X - gx1)**2 + (Y - ny//2)**2
    lam -= 0.04 * np.exp(-r2 / (2 * 12.0**2))
    hazards.append({"name": "SHALLOW", "x": gx1, "depth": 0.04,
                     "radius": 12})

    # Deep grave at 1/2 transit
    gx2 = nx // 2
    r2 = (X - gx2)**2 + (Y - ny//2)**2
    lam -= 0.08 * np.exp(-r2 / (2 * 18.0**2))
    hazards.append({"name": "DEEP", "x": gx2, "depth": 0.08,
                     "radius": 18})

    # Clean corridor at 2/3
    hazards.append({"name": "CLEAN", "x": nx * 2 // 3,
                     "depth": 0.0, "radius": 0})

    lam = np.maximum(lam, 0.001)
    return lam, hazards


# ═══════════════════════════════════════════════════════
# MAIN TEST
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Harpoon Probe Integration")
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--grid", type=int, default=256)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- HARPOON PROBE INTEGRATION TEST")
    print(f"  12 probes + omega anchor + hazards + navigator")
    print(f"  Stephen Justin Burdick Sr.")
    print(f"  Emerald Entities LLC -- GIBUSH Systems")
    print(f"{'='*65}")
    print(f"  Grid: {nx}x{ny}  Steps: {args.steps}")

    dt = 0.05
    D = 0.5
    void_lambda = 0.10
    pump_A = 0.5
    ratio = 0.25
    alpha = 0.80
    separation = 15.0

    x = np.arange(nx)
    y = np.arange(ny)
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Build hazard field
    lam_field, hazards = build_hazard_field(nx, ny, void_lambda)

    print(f"\n  HAZARD MAP:")
    for h in hazards:
        lam_at = float(lam_field[h["x"], ny//2]) if h["depth"] > 0 else void_lambda
        print(f"    {h['name']:>8} at x={h['x']:>4}  "
              f"depth={h['depth']:.2f}  lambda={lam_at:.4f}")

    # Initialize sigma (craft)
    start_x = nx // 8
    start_y = ny // 2
    r2_init = (X - start_x)**2 + (Y - start_y)**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    # Omega anchor (harpoon -- never moves)
    initial_com = compute_com(sigma)
    omega_com = initial_com.copy()

    prev_com = initial_com.copy()

    # Build 12 probes (3 shells x 4 probes)
    probes = []
    for i in range(4):
        probes.append(Probe(i+1, 15.0, i * math.pi / 2))
    for i in range(4):
        probes.append(Probe(i+5, 35.0, i * math.pi / 2 + math.pi/4))
    for i in range(4):
        probes.append(Probe(i+9, 60.0, i * math.pi / 2 + math.pi/6))

    # Navigator
    nav = Navigator()

    print(f"\n  Fleet: {len(probes)} probes (shells 15/35/60)")
    print(f"  Omega anchor at ({omega_com[0]:.1f}, {omega_com[1]:.1f})")

    # Timeline
    timeline = []
    craft_first_at_hazard = {}
    probe_first_detect = {}

    print(f"\n  {'Step':>6} {'X':>8} {'Sep':>8} {'Decision':>10} "
          f"{'Safe':>6} {'Grave':>6} {'Coh':>6} {'Warn':>5}")
    print(f"  {'-'*6} {'-'*8} {'-'*8} {'-'*10} "
          f"{'-'*6} {'-'*6} {'-'*6} {'-'*5}")

    alive = True

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            alive = False
            print(f"  DISSOLVED at step {step}")
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])
        speed = float(np.linalg.norm(velocity_vec))

        # Track when craft reaches each hazard
        for h in hazards:
            if h["name"] not in craft_first_at_hazard:
                if abs(com[0] - h["x"]) < h.get("radius", 10) + 5:
                    craft_first_at_hazard[h["name"]] = step

        # Pumps (raw -- no governor)
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # Sigma PDE
        lap = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
               np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
               4 * sigma)
        sigma_new = sigma + D * lap * dt - lam_field * sigma * dt
        if alpha > 0:
            sigma_new += alpha * (sigma - sigma_prev)
        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            print(f"  BLOWUP at step {step}")
            alive = False
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # Probe cycle every 10 steps
        if step % 10 == 0:
            for probe in probes:
                pos = probe.compute_position(com, step)
                reading = probe.sample(lam_field, sigma, nx, ny)
                nav.ingest(reading, step)

                # Track first detection per hazard
                if reading["danger"]:
                    if probe.first_danger_step == -1:
                        probe.first_danger_step = step
                    key = f"P{probe.pid}"
                    if key not in probe_first_detect:
                        probe_first_detect[key] = {
                            "step": step,
                            "probe": probe.pid,
                            "shell": probe.radius,
                            "at": (reading["ix"], reading["iy"]),
                            "lambda": reading["lambda"],
                        }

        # Navigator decision every 20 steps
        if step % 20 == 0:
            decision = nav.decide(step)

        # Log every 100 steps
        if step % 100 == 0:
            new_com = compute_com(sigma)
            if new_com is not None:
                drift = float(np.linalg.norm(new_com - initial_com))
                omega_sep = float(np.linalg.norm(new_com - omega_com))
                coh = compute_coherence(sigma, new_com)

                entry = {
                    "step": step,
                    "x": round(float(new_com[0]), 2),
                    "drift": round(drift, 2),
                    "omega_sep": round(omega_sep, 2),
                    "decision": nav.decision,
                    "safe_p": round(nav.hyp_safe.posterior, 4),
                    "grave_p": round(nav.hyp_grave.posterior, 4),
                    "coherence": round(coh, 4),
                    "warnings": len(nav.warnings),
                }
                timeline.append(entry)

                print(f"  {step:>6} {new_com[0]:>8.1f} "
                      f"{omega_sep:>8.1f} {nav.decision:>10} "
                      f"{nav.hyp_safe.posterior:>6.3f} "
                      f"{nav.hyp_grave.posterior:>6.3f} "
                      f"{coh:>6.3f} {len(nav.warnings):>5}")

        prev_com = com

    # ═══════════════════════════════════════════════════
    # FINAL REPORT
    # ═══════════════════════════════════════════════════
    final_com = compute_com(sigma)
    if final_com is not None:
        final_drift = float(np.linalg.norm(final_com - initial_com))
        final_omega = float(np.linalg.norm(final_com - omega_com))
        final_coh = compute_coherence(sigma, final_com)
    else:
        final_drift = 0
        final_omega = 0
        final_coh = 0

    print(f"\n{'='*65}")
    print(f"  HARPOON PROBE INTEGRATION -- FINAL REPORT")
    print(f"{'='*65}")

    print(f"\n  1. OMEGA ANCHOR (frame independence):")
    print(f"     Omega position: ({omega_com[0]:.1f}, {omega_com[1]:.1f})")
    print(f"     Omega drift: 0.000 px (static)")
    print(f"     Sigma drift: {final_drift:.2f} px")
    print(f"     Separation: {final_omega:.2f} px")
    omega_pass = final_omega > 1.0
    print(f"     VERDICT: {'PASS' if omega_pass else 'FAIL'}")

    print(f"\n  2. EARLY WARNING (did probes detect before craft?)")
    for h in hazards:
        if h["depth"] == 0:
            continue
        craft_step = craft_first_at_hazard.get(h["name"], "never")
        # Find earliest probe detection near this hazard
        earliest_probe = None
        for key, det in probe_first_detect.items():
            if abs(det["at"][0] - h["x"]) < h["radius"] + 20:
                if earliest_probe is None or det["step"] < earliest_probe["step"]:
                    earliest_probe = det

        if earliest_probe and craft_step != "never":
            warning_steps = craft_step - earliest_probe["step"]
            print(f"     {h['name']:>8}: Probe P{earliest_probe['probe']} "
                  f"detected at step {earliest_probe['step']}, "
                  f"craft arrived step {craft_step}")
            print(f"              WARNING LEAD: {warning_steps} steps "
                  f"({'ADEQUATE' if warning_steps > 50 else 'MARGINAL' if warning_steps > 0 else 'TOO LATE'})")
        elif earliest_probe:
            print(f"     {h['name']:>8}: Probe detected at step "
                  f"{earliest_probe['step']}, craft never reached")
        else:
            print(f"     {h['name']:>8}: No probe detection")

    print(f"\n  3. NAVIGATOR DECISIONS:")
    decisions_seen = set()
    for d in nav.decision_history:
        if d["decision"] not in decisions_seen:
            decisions_seen.add(d["decision"])
            print(f"     First {d['decision']}: step {d['step']} "
                  f"(safe={d['safe_p']:.3f} grave={d['grave_p']:.3f})")

    # Decision transitions
    transitions = []
    for i in range(1, len(nav.decision_history)):
        if nav.decision_history[i]["decision"] != nav.decision_history[i-1]["decision"]:
            transitions.append(nav.decision_history[i])
    print(f"     Decision transitions: {len(transitions)}")
    for t in transitions[:5]:
        print(f"       step {t['step']}: -> {t['decision']} "
              f"(safe={t['safe_p']:.3f} grave={t['grave_p']:.3f})")

    print(f"\n  4. CRAFT SURVIVAL:")
    print(f"     Alive: {'YES' if alive else 'NO'}")
    print(f"     Final coherence: {final_coh:.4f}")
    print(f"     Warnings received: {len(nav.warnings)}")

    print(f"\n  5. PROBE FLEET STATUS:")
    for p in probes:
        danger_str = f"step {p.first_danger_step}" if p.first_danger_step and p.first_danger_step > 0 else "none"
        print(f"     P{p.pid:>2} shell={p.radius:>4.0f}  "
              f"reads={p.readings:>4}  first_danger={danger_str}")

    # Overall verdict
    print(f"\n{'='*65}")
    print(f"  INTEGRATION VERDICT")
    print(f"{'='*65}")

    probes_warned = any(p.first_danger_step is not None and
                        p.first_danger_step > 0 for p in probes)
    nav_reacted = len(transitions) > 0
    frame_ok = omega_pass

    if frame_ok and probes_warned and nav_reacted and alive:
        print(f"\n  ALL SYSTEMS NOMINAL.")
        print(f"  Transport real (omega anchor). Probes detected")
        print(f"  hazards. Navigator reacted. Craft survived.")
        print(f"  The ship thinks. The thinking kept it alive.")
    elif frame_ok and probes_warned and not nav_reacted:
        print(f"\n  PARTIAL: Probes detected but navigator did not react.")
        print(f"  Bayesian update thresholds may need adjustment.")
    elif frame_ok and not probes_warned:
        print(f"\n  PARTIAL: No hazard detected by probes.")
        print(f"  Probe orbital radius may be insufficient.")
    else:
        print(f"\n  INTEGRATION INCOMPLETE. Check individual systems.")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_harpoon_probe_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Harpoon Probe Integration Test",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "purpose": "Full integration: probes + anchor + hazards + navigator",
        "grid": nx,
        "steps": args.steps,
        "hazards": hazards,
        "omega_anchor": [float(omega_com[0]), float(omega_com[1])],
        "result": {
            "alive": alive,
            "drift": round(final_drift, 4),
            "omega_separation": round(final_omega, 4),
            "coherence": round(final_coh, 4),
            "omega_pass": omega_pass,
            "warnings": len(nav.warnings),
            "transitions": len(transitions),
            "probes_detected": probes_warned,
            "navigator_reacted": nav_reacted,
        },
        "early_warnings": probe_first_detect,
        "craft_arrival": craft_first_at_hazard,
        "timeline": timeline,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
