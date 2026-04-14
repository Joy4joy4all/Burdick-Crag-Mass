# -*- coding: utf-8 -*-
"""
BCM v16 -- Probe Collector (Observer Perturbation Model)
=========================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC
GIBUSH Systems

Architecture origin: Stephen's Genesis Brain interview model
(TITS_GIBUSH_AISOS_SPINE). The interview system was never
about chip handling. It was a cognitive architecture for
navigating unknown environments, tested on humans first.

MAPPING:
  Interview      -> Probe orbital pass
  Interviewee    -> Substrate state at coordinate
  Questions      -> Sensor queries (λ, χ, wake, coherence)
  Results        -> Substrate measurements
  HypothesisEng  -> Chi field state tracker
  GraphBuilder   -> TITS reconciler (relational map)
  CogSynthesis   -> Bayesian navigator (actionable path)
  Orchestrator   -> Flight computer pipeline
  Contradictions -> Bifurcation detection
  Communities    -> Substrate regions with shared character
  Gaps           -> Unmapped substrate zones
  Info gain      -> Exploration value of probing a direction
  Circumpunct    -> Convergence / arrival readiness

12 probes cycle around the craft on orbital paths,
eject through the L1 tunnel corridor, sample the
substrate, and return through the funded hallway
to report to TITS.

Each probe is an interviewer. The substrate is the
interviewee. The probe asks: what is lambda here?
What is chi? What is the wake mass? What is the
gradient tendency? The answers update the posterior.
The posterior becomes the next prior. The craft's
picture of reality sharpens with every orbit.

Usage:
    python BCM_v16_probe_collector.py
    python BCM_v16_probe_collector.py --steps 2000 --grid 128
"""

import numpy as np
import json
import os
import time
import math
import argparse


# ════════════════════════════════════════════════════════
# EVIDENCE STRENGTH RULES (from Genesis hypothesis_engine)
# Remapped: interview evidence types -> substrate measurements
# ════════════════════════════════════════════════════════

EVIDENCE_STRENGTH = {
    "chi_direct":        0.45,   # Direct chi field reading
    "lambda_gradient":   0.40,   # Lambda gradient measurement
    "wake_mass":         0.35,   # Wake mass residual (Pearson)
    "coherence_reading": 0.30,   # Coherence at sample point
    "density_anomaly":   0.50,   # Density spike (grave detect)
    "density_normal":    0.15,   # Normal density reading
    "gradient_reversal": 0.45,   # Gradient direction change
    "void_confirmed":    0.20,   # Confirmed empty void
    "default":           0.10,   # Unclassified reading
}


# ════════════════════════════════════════════════════════
# SUBSTRATE HYPOTHESIS (from Genesis Hypothesis class)
# ════════════════════════════════════════════════════════

class SubstrateHypothesis:
    """
    Bayesian hypothesis about substrate state ahead.
    Log-odds formulation from Genesis hypothesis_engine.
    """
    def __init__(self, key, name, prior=0.50):
        self.key = key
        self.name = name
        self.prior = prior
        self.posterior = prior
        self.evidence_for = []
        self.evidence_against = []
        self.status = "NEEDS_MORE_DATA"

    VALIDATE_THRESHOLD = 0.85
    INVALIDATE_THRESHOLD = 0.15
    MIN_EVIDENCE = 3

    @property
    def evidence_count(self):
        return len(self.evidence_for) + len(self.evidence_against)

    @property
    def confidence_interval(self):
        if self.evidence_count == 0:
            half = 0.15
        else:
            half = 0.15 / math.sqrt(self.evidence_count)
        return (max(0.0, self.posterior - half),
                min(1.0, self.posterior + half))

    def update(self, direction, strength, reason,
               probe_id, evidence_type="default"):
        if strength <= 0:
            strength = EVIDENCE_STRENGTH.get(
                evidence_type, EVIDENCE_STRENGTH["default"])

        p = max(0.01, min(0.99, self.posterior))
        log_odds = math.log(p / (1.0 - p))
        log_odds += direction * strength
        self.posterior = 1.0 / (1.0 + math.exp(-log_odds))

        entry = {
            "probe": probe_id,
            "reason": reason,
            "strength": strength,
            "type": evidence_type,
            "direction": direction,
            "posterior_after": round(self.posterior, 4),
        }

        if direction > 0:
            self.evidence_for.append(entry)
        else:
            self.evidence_against.append(entry)

        self._update_status()

    def _update_status(self):
        if self.evidence_count < self.MIN_EVIDENCE:
            self.status = "NEEDS_MORE_DATA"
        elif self.posterior >= self.VALIDATE_THRESHOLD:
            self.status = "VALIDATED"
        elif self.posterior <= self.INVALIDATE_THRESHOLD:
            self.status = "INVALIDATED"
        else:
            self.status = "NEEDS_MORE_DATA"

    def to_dict(self):
        return {
            "key": self.key, "name": self.name,
            "prior": self.prior,
            "posterior": round(self.posterior, 4),
            "evidence_count": self.evidence_count,
            "confidence_interval": [round(x, 4)
                                    for x in self.confidence_interval],
            "status": self.status,
        }


# ════════════════════════════════════════════════════════
# PROBE (from Genesis Interview structure)
# ════════════════════════════════════════════════════════

class Probe:
    """
    One orbital probe. Cycles around the craft on a fixed
    orbital path, samples the substrate at its current
    position, and returns data through the L1 corridor.

    Maps to: one interview in the Genesis system.
    """
    def __init__(self, probe_id, orbital_radius,
                 orbital_phase, sample_types):
        self.probe_id = probe_id
        self.orbital_radius = orbital_radius
        self.orbital_phase = orbital_phase  # radians
        self.orbital_speed = 0.05  # rad/step
        self.sample_types = sample_types

        # Telemetry (maps to Genesis 3d_objects faces)
        self.position = np.array([0.0, 0.0])
        self.last_reading = {}
        self.readings_count = 0
        self.resonance = 0.0  # quality of substrate coupling

    def compute_position(self, craft_com, step):
        """Compute probe position on its orbital path."""
        angle = self.orbital_phase + self.orbital_speed * step
        self.position = np.array([
            craft_com[0] + self.orbital_radius * np.cos(angle),
            craft_com[1] + self.orbital_radius * np.sin(angle),
        ])
        return self.position

    def sample_substrate(self, sigma, lam_field, chi_field,
                         nx, ny):
        """
        Sample the substrate at the probe's current position.
        Returns a reading dict (maps to interview results).
        """
        ix = int(np.clip(self.position[0], 0, nx - 1))
        iy = int(np.clip(self.position[1], 0, ny - 1))

        # Core measurements
        local_sigma = float(sigma[ix, iy])
        local_lambda = float(lam_field[ix, iy])
        local_chi = float(chi_field[ix, iy])

        # Gradient at probe position
        grad_lam_x = float(
            (lam_field[min(ix+1, nx-1), iy] -
             lam_field[max(ix-1, 0), iy]) / 2.0)
        grad_lam_y = float(
            (lam_field[ix, min(iy+1, ny-1)] -
             lam_field[ix, max(iy-1, 0)]) / 2.0)
        grad_magnitude = math.sqrt(grad_lam_x**2 + grad_lam_y**2)

        # Local coherence (within 5px radius)
        x = np.arange(nx)
        y = np.arange(ny)
        X, Y = np.meshgrid(x, y, indexing='ij')
        r2 = (X - ix)**2 + (Y - iy)**2
        mask = r2 < 25  # 5px radius
        local_total = float(np.sum(sigma[mask]))
        global_total = float(np.sum(sigma))
        coherence = local_total / global_total if global_total > 1e-15 else 0

        # Wake mass (trailing behind probe position relative to craft)
        # Simplified: sum sigma in aft quadrant from probe
        aft_mask = (X < ix) & (r2 < 100)
        wake_mass = float(np.sum(sigma[aft_mask]))

        # Resonance (quality of substrate coupling at this point)
        # Higher lambda = less coupling = lower resonance
        self.resonance = max(0, 1.0 - local_lambda * 5.0)

        reading = {
            "probe_id": self.probe_id,
            "ix": ix, "iy": iy,
            "sigma": round(local_sigma, 6),
            "lambda": round(local_lambda, 6),
            "chi": round(local_chi, 6),
            "grad_magnitude": round(grad_magnitude, 8),
            "grad_direction": round(
                math.atan2(grad_lam_y, grad_lam_x), 4),
            "coherence": round(coherence, 4),
            "wake_mass": round(wake_mass, 4),
            "resonance": round(self.resonance, 4),
        }

        self.last_reading = reading
        self.readings_count += 1
        return reading

    def classify_reading(self, reading):
        """
        Classify the reading into evidence type.
        Maps to Genesis evidence_type assignment.
        """
        if reading["lambda"] < 0.03:
            return "density_anomaly", -1, "Deep grave detected"
        elif reading["lambda"] > 0.08:
            return "void_confirmed", +1, "Safe void confirmed"
        elif reading["grad_magnitude"] > 0.01:
            return "lambda_gradient", +1, "Navigable gradient"
        elif reading["chi"] > 0.5:
            return "chi_direct", -1, "High chi (4D potential)"
        elif reading["wake_mass"] > 10.0:
            return "wake_mass", -1, "Trailing wake mass detected"
        elif reading["coherence"] > 0.3:
            return "coherence_reading", +1, "Good coherence zone"
        else:
            return "density_normal", +1, "Normal substrate"

    def to_dict(self):
        return {
            "probe_id": self.probe_id,
            "orbital_radius": self.orbital_radius,
            "orbital_phase": round(self.orbital_phase, 4),
            "position": [round(float(p), 4) for p in self.position],
            "readings_count": self.readings_count,
            "resonance": round(self.resonance, 4),
            "last_reading": self.last_reading,
        }


# ════════════════════════════════════════════════════════
# TITS RECONCILER (from Genesis GraphBuilder + CogEngine)
# ════════════════════════════════════════════════════════

class TITSReconciler:
    """
    Tensor Imagery Trasference Sensory -- the reconciler.

    Receives readings from all 12 probes, builds a relational
    graph of substrate states, detects contradictions
    (bifurcation), identifies communities (substrate regions),
    and produces the navigation posterior.

    Maps to: GraphBuilder + CognitiveSynthesisEngine
    """
    def __init__(self):
        self.hypotheses = {}
        self.readings_log = []
        self.contradictions = []
        self.communities = {}  # substrate region clusters
        self.navigation_posterior = {
            "safe_direction": None,
            "danger_direction": None,
            "recommended_heading": 0.0,
            "confidence": 0.0,
        }

        # Initialize navigation hypotheses
        self._init_hypotheses()

    def _init_hypotheses(self):
        """Initialize substrate navigation hypotheses."""
        hyps = [
            ("SAFE_AHEAD", "Forward path is navigable", 0.50),
            ("GRAVE_AHEAD", "Dead galaxy substrate ahead", 0.30),
            ("GRADIENT_FAVORABLE", "Lambda gradient supports drift", 0.50),
            ("WAKE_ACCUMULATING", "Ship accumulating wake mass", 0.30),
            ("COHERENCE_STABLE", "Ship coherence is stable", 0.60),
            ("CHI_TUNNEL_AVAILABLE", "4D bypass route available", 0.40),
        ]
        for key, name, prior in hyps:
            self.hypotheses[key] = SubstrateHypothesis(key, name, prior)

    def ingest_reading(self, reading, probe):
        """
        Ingest one probe reading into the hypothesis engine.
        Maps to: Genesis knowledge_extractor + hypothesis update.
        """
        evidence_type, direction, reason = probe.classify_reading(reading)

        # Update relevant hypotheses based on evidence type
        if evidence_type == "density_anomaly":
            self.hypotheses["GRAVE_AHEAD"].update(
                +1, 0, f"Probe {reading['probe_id']}: {reason}",
                reading["probe_id"], evidence_type)
            self.hypotheses["SAFE_AHEAD"].update(
                -1, 0, f"Probe {reading['probe_id']}: grave detected",
                reading["probe_id"], evidence_type)

        elif evidence_type == "void_confirmed":
            self.hypotheses["SAFE_AHEAD"].update(
                +1, 0, f"Probe {reading['probe_id']}: {reason}",
                reading["probe_id"], evidence_type)
            self.hypotheses["GRAVE_AHEAD"].update(
                -1, 0, f"Probe {reading['probe_id']}: safe void",
                reading["probe_id"], evidence_type)

        elif evidence_type == "lambda_gradient":
            self.hypotheses["GRADIENT_FAVORABLE"].update(
                +1, 0, f"Probe {reading['probe_id']}: {reason}",
                reading["probe_id"], evidence_type)

        elif evidence_type == "chi_direct":
            self.hypotheses["CHI_TUNNEL_AVAILABLE"].update(
                +1, 0, f"Probe {reading['probe_id']}: {reason}",
                reading["probe_id"], evidence_type)

        elif evidence_type == "wake_mass":
            self.hypotheses["WAKE_ACCUMULATING"].update(
                +1, 0, f"Probe {reading['probe_id']}: {reason}",
                reading["probe_id"], evidence_type)

        elif evidence_type == "coherence_reading":
            self.hypotheses["COHERENCE_STABLE"].update(
                +1, 0, f"Probe {reading['probe_id']}: {reason}",
                reading["probe_id"], evidence_type)

        self.readings_log.append(reading)

        # Contradiction detection
        self._check_contradictions()

    def _check_contradictions(self):
        """
        Detect contradictions (bifurcation).
        If probes disagree about the same region, flag it.
        """
        if len(self.readings_log) < 4:
            return

        recent = self.readings_log[-12:]
        safe_probes = [r for r in recent if r["lambda"] > 0.07]
        danger_probes = [r for r in recent if r["lambda"] < 0.03]

        if safe_probes and danger_probes:
            self.contradictions.append({
                "step": len(self.readings_log),
                "type": "bifurcation",
                "description": (
                    f"Probes disagree: {len(safe_probes)} report safe, "
                    f"{len(danger_probes)} report danger"),
            })

    def compute_navigation_posterior(self, craft_com):
        """
        Compute the navigation decision from all hypotheses.
        Maps to: Genesis CognitiveSynthesisEngine.run_synthesis()

        Returns the recommended heading and confidence.
        """
        # Aggregate probe directions weighted by gradient
        recent = self.readings_log[-12:]  # last full orbit
        if not recent:
            return self.navigation_posterior

        # Weighted direction from gradient readings
        wx, wy = 0.0, 0.0
        total_weight = 0.0

        for r in recent:
            if r["grad_magnitude"] > 0.001:
                angle = r["grad_direction"]
                weight = r["grad_magnitude"] * r["resonance"]
                wx += weight * math.cos(angle)
                wy += weight * math.sin(angle)
                total_weight += weight

        if total_weight > 0:
            recommended = math.atan2(wy / total_weight,
                                     wx / total_weight)
        else:
            recommended = 0.0

        # Confidence from hypothesis posteriors
        safe_p = self.hypotheses["SAFE_AHEAD"].posterior
        grave_p = self.hypotheses["GRAVE_AHEAD"].posterior
        coh_p = self.hypotheses["COHERENCE_STABLE"].posterior

        confidence = safe_p * coh_p * (1.0 - grave_p)

        # Navigation decision
        if grave_p > 0.80:
            decision = "AVOID"
        elif self.hypotheses["CHI_TUNNEL_AVAILABLE"].posterior > 0.70:
            decision = "TUNNEL"
        elif safe_p > 0.70:
            decision = "PROCEED"
        else:
            decision = "CAUTION"

        self.navigation_posterior = {
            "recommended_heading": round(recommended, 4),
            "confidence": round(confidence, 4),
            "decision": decision,
            "safe_posterior": round(safe_p, 4),
            "grave_posterior": round(grave_p, 4),
            "coherence_posterior": round(coh_p, 4),
            "chi_tunnel_posterior": round(
                self.hypotheses["CHI_TUNNEL_AVAILABLE"].posterior, 4),
            "contradictions": len(self.contradictions),
        }

        return self.navigation_posterior

    def get_gaps(self):
        """
        Identify unmapped substrate regions.
        Maps to: Genesis gaps analysis.
        """
        needs_data = [k for k, h in self.hypotheses.items()
                      if h.status == "NEEDS_MORE_DATA"]
        return needs_data

    def get_strategic_intelligence(self):
        """
        Full navigation intelligence report.
        Maps to: Genesis strategic_intelligence.json
        """
        return {
            "hypotheses": {k: h.to_dict()
                           for k, h in self.hypotheses.items()},
            "navigation": self.navigation_posterior,
            "contradictions": len(self.contradictions),
            "gaps": self.get_gaps(),
            "total_readings": len(self.readings_log),
        }


# ════════════════════════════════════════════════════════
# PROBE FLEET (12 probes in orbital formation)
# ════════════════════════════════════════════════════════

def build_probe_fleet():
    """
    Build 12 probes in orbital formation around the craft.
    Three orbital shells, four probes per shell, evenly spaced.

    Maps to: 12 interviews in Genesis system.
    """
    probes = []

    # Shell 1: Close orbit (immediate hull boundary)
    for i in range(4):
        phase = i * (2 * math.pi / 4)
        probes.append(Probe(
            probe_id=i + 1,
            orbital_radius=15.0,
            orbital_phase=phase,
            sample_types=["lambda", "sigma", "coherence"],
        ))

    # Shell 2: Mid orbit (substrate transition zone)
    for i in range(4):
        phase = i * (2 * math.pi / 4) + math.pi / 4  # offset 45 deg
        probes.append(Probe(
            probe_id=i + 5,
            orbital_radius=30.0,
            orbital_phase=phase,
            sample_types=["lambda", "chi", "gradient"],
        ))

    # Shell 3: Far orbit (look-ahead / early warning)
    for i in range(4):
        phase = i * (2 * math.pi / 4) + math.pi / 6  # offset 30 deg
        probes.append(Probe(
            probe_id=i + 9,
            orbital_radius=50.0,
            orbital_phase=phase,
            sample_types=["lambda", "chi", "wake_mass", "density"],
        ))

    return probes


# ════════════════════════════════════════════════════════
# FLIGHT SIMULATION WITH PROBE COLLECTOR
# ════════════════════════════════════════════════════════

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


def main():
    parser = argparse.ArgumentParser(
        description="BCM v16 Probe Collector")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--grid", type=int, default=128)
    args = parser.parse_args()

    nx = ny = args.grid

    print(f"\n{'='*65}")
    print(f"  BCM v16 -- PROBE COLLECTOR")
    print(f"  12 orbital probes. Bayesian substrate navigator.")
    print(f"  Observer perturbation model.")
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

    # Initialize sigma (the craft)
    center = (nx // 3, ny // 2)
    r2_init = (X - center[0])**2 + (Y - center[1])**2
    sigma = 1.0 * np.exp(-r2_init / (2 * 5.0**2))
    sigma_prev = sigma.copy()

    # Lambda field with one embedded grave for testing
    lam_field = np.full((nx, ny), void_lambda, dtype=float)
    grave_x, grave_y = nx * 2 // 3, ny // 2
    r2_grave = (X - grave_x)**2 + (Y - grave_y)**2
    lam_field -= 0.06 * np.exp(-r2_grave / (2 * 15.0**2))
    lam_field = np.maximum(lam_field, 0.001)

    # Chi field (4D potential -- starts at zero)
    chi_field = np.zeros((nx, ny))

    initial_com = compute_com(sigma)
    prev_com = initial_com.copy()

    # Build fleet and reconciler
    probes = build_probe_fleet()
    tits = TITSReconciler()

    print(f"\n  Fleet deployed: {len(probes)} probes")
    print(f"  Shell 1 (close):  probes 1-4  radius=15")
    print(f"  Shell 2 (mid):    probes 5-8  radius=30")
    print(f"  Shell 3 (far):    probes 9-12 radius=50")
    print(f"  Grave embedded at ({grave_x}, {grave_y}) depth=0.06")

    # Navigation timeline
    nav_timeline = []

    print(f"\n  {'Step':>6} {'X':>8} {'Decision':>10} "
          f"{'Conf':>6} {'Safe':>6} {'Grave':>6} "
          f"{'Contrad':>8} {'Gaps':>5}")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*6} {'-'*6} "
          f"{'-'*6} {'-'*8} {'-'*5}")

    for step in range(args.steps):
        com = compute_com(sigma)
        if com is None:
            print(f"  DISSOLVED at step {step}")
            break

        velocity_vec = com - prev_com if prev_com is not None else np.array([0.0, 0.0])

        # Pumps (raw, no governor -- testing probe system)
        r2_A = (X - com[0])**2 + (Y - com[1])**2
        pA = pump_A * np.exp(-r2_A / (2 * 4.0**2))
        sigma += pA * dt

        bx = com[0] + separation
        r2_B = (X - bx)**2 + (Y - com[1])**2
        actual_B = pump_A * ratio
        pB = actual_B * np.exp(-r2_B / (2 * 3.0**2))
        sigma += pB * dt

        # Evolve sigma PDE
        lap_sigma = (np.roll(sigma, 1, 0) + np.roll(sigma, -1, 0) +
                     np.roll(sigma, 1, 1) + np.roll(sigma, -1, 1) -
                     4 * sigma)
        sigma_new = sigma + D * lap_sigma * dt - lam_field * sigma * dt
        if alpha > 0:
            sigma_new += alpha * (sigma - sigma_prev)
        sigma_new = np.maximum(sigma_new, 0)

        if float(np.max(sigma_new)) > 1e10:
            print(f"  BLOWUP at step {step}")
            break

        sigma_prev = sigma.copy()
        sigma = sigma_new

        # -- PROBE ORBITAL CYCLE --
        # Every 20 steps, all 12 probes sample
        if step % 20 == 0:
            for probe in probes:
                pos = probe.compute_position(com, step)
                reading = probe.sample_substrate(
                    sigma, lam_field, chi_field, nx, ny)
                tits.ingest_reading(reading, probe)

            # Compute navigation posterior
            nav = tits.compute_navigation_posterior(com)
            gaps = tits.get_gaps()

        # Log every 100 steps
        if step % 100 == 0:
            nav = tits.compute_navigation_posterior(com)
            gaps = tits.get_gaps()
            drift = float(np.linalg.norm(com - initial_com))

            nav_entry = {
                "step": step,
                "x": round(float(com[0]), 2),
                "drift": round(drift, 2),
            }
            nav_entry.update(nav)
            nav_entry["gaps"] = len(gaps)
            nav_timeline.append(nav_entry)

            decision = nav.get("decision", "---")
            conf = nav.get("confidence", 0)
            safe = nav.get("safe_posterior", 0)
            grave = nav.get("grave_posterior", 0)
            contrad = nav.get("contradictions", 0)

            print(f"  {step:>6} {com[0]:>8.1f} {decision:>10} "
                  f"{conf:>6.3f} {safe:>6.3f} {grave:>6.3f} "
                  f"{contrad:>8} {len(gaps):>5}")

        prev_com = com

    # -- FINAL REPORT --
    print(f"\n{'='*65}")
    print(f"  PROBE COLLECTOR FINAL REPORT")
    print(f"{'='*65}")

    intel = tits.get_strategic_intelligence()

    print(f"\n  HYPOTHESES:")
    for key, h in intel["hypotheses"].items():
        ci = h["confidence_interval"]
        print(f"    {h['name']:>40}: "
              f"{h['posterior']:.3f} [{ci[0]:.3f}-{ci[1]:.3f}] "
              f"{h['status']}")

    print(f"\n  NAVIGATION DECISION: {intel['navigation']['decision']}")
    print(f"  Confidence: {intel['navigation']['confidence']:.4f}")
    print(f"  Recommended heading: "
          f"{intel['navigation']['recommended_heading']:.4f} rad")
    print(f"  Contradictions detected: {intel['contradictions']}")
    print(f"  Unmapped gaps: {len(intel['gaps'])}")
    print(f"  Total probe readings: {intel['total_readings']}")

    # Probe fleet status
    print(f"\n  PROBE FLEET STATUS:")
    for p in probes:
        lr = p.last_reading
        lam_str = f"{lr.get('lambda', 0):.4f}" if lr else "---"
        print(f"    Probe {p.probe_id:>2} | "
              f"shell={p.orbital_radius:>4.0f} | "
              f"reads={p.readings_count:>4} | "
              f"res={p.resonance:.3f} | "
              f"last_λ={lam_str}")

    print(f"{'='*65}")

    # Save
    base = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base, "data", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
        f"BCM_v16_probe_collector_{time.strftime('%Y%m%d_%H%M%S')}.json")

    out_data = {
        "title": "BCM v16 Probe Collector -- Observer Perturbation Model",
        "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
        "architecture_origin": "Genesis Brain interview model (TITS_GIBUSH_AISOS_SPINE)",
        "purpose": "12 orbital probes with Bayesian substrate navigation",
        "grid": nx,
        "steps": args.steps,
        "probe_count": len(probes),
        "probe_fleet": [p.to_dict() for p in probes],
        "strategic_intelligence": intel,
        "navigation_timeline": nav_timeline,
    }

    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
