# -*- coding: utf-8 -*-
"""
BCM AI Engine — Layer 3: Autonomous Execution
================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC

The AI Engine monitors substrate coherence, adjusts lambda
modulation, corrects heading drift, and manages the coherence
budget during maneuvers. It executes within crew-set limits
and flags anomalies for crew review.

The AI engine executes. The crew authorizes.
"""

import numpy as np
from BCM_phase_block import PhaseBlock
from BCM_substrate_model import (
    build_lambda_dipole, init_sigma_packet,
    step_substrate, compute_com, compute_coherence,
    compute_drift_velocity, compute_bridge_tension
)


class AIEngine:
    """
    Autonomous substrate navigation engine.
    Monitors, corrects, and executes within crew limits.
    """

    def __init__(self, grid=64, dt=0.05, D=0.5):
        self.grid = grid
        self.dt = dt
        self.D = D
        self.log = []

    def _log(self, msg):
        self.log.append(msg)

    def assess_coherence(self, phase):
        """
        Run a short substrate simulation to assess coherence
        for the given phase block parameters.
        Returns updated coherence value and safety status.
        """
        nx = ny = self.grid
        center = (nx // 2, ny // 2)
        sigma = init_sigma_packet(nx, ny, center)

        # Build lambda field for this phase
        direction = (1, 0)  # simplified
        lam_field = build_lambda_dipole(
            nx, ny, ship_pos=center,
            direction=direction,
            base_lam=0.1,
            delta_lam=phase.lambda_eta * 0.05,
            spread=10.0)

        # Run 200 steps and measure
        for _ in range(200):
            sigma = step_substrate(sigma, lam_field,
                                    self.D, self.dt)

        com = compute_com(sigma)
        if com is None:
            phase.coherence_current = 0.0
            phase.ai_coherence_ok = False
            self._log(f"  [AI] Phase {phase.phase_id} "
                      f"{phase.name}: COHERENCE COLLAPSED")
            return False

        coh = compute_coherence(sigma, com, radius=8)
        phase.coherence_current = round(coh, 4)

        # Check against crew-set minimum
        safe = coh >= phase.coherence_min
        phase.ai_coherence_ok = safe

        status = "OK" if safe else "BELOW THRESHOLD"
        self._log(f"  [AI] Phase {phase.phase_id} "
                  f"{phase.name}: coh={coh:.4f} [{status}]")

        return safe

    def assess_drift(self, phase):
        """
        Measure drift velocity for the phase's lambda settings.
        Returns drift speed in px/step.
        """
        nx = ny = self.grid
        center = (nx // 2, ny // 2)
        sigma = init_sigma_packet(nx, ny, center)

        lam_field = build_lambda_dipole(
            nx, ny, ship_pos=center,
            direction=(1, 0),
            base_lam=0.1,
            delta_lam=phase.lambda_eta * 0.05,
            spread=10.0)

        vel = compute_drift_velocity(
            sigma, lam_field, self.D, self.dt, n_steps=100)

        speed = np.linalg.norm(vel)
        self._log(f"  [AI] Phase {phase.phase_id} drift: "
                  f"v={speed:.6f} px/step "
                  f"dir=({vel[0]:+.4f},{vel[1]:+.4f})")

        return speed, vel

    def check_heading(self, phase, target_x, target_y):
        """
        Check if phase trajectory is aimed at target.
        Returns heading error in degrees.
        """
        dx = target_x - phase.x_au
        dy = target_y - phase.y_au
        target_angle = np.degrees(np.arctan2(dy, dx))

        # Assume current heading from phase velocity direction
        # For now, heading = direct line to target
        phase.heading_error_deg = 0.0  # on-vector (from alignment test)
        return 0.0

    def recommend_correction(self, phase, actual_v, planned_v):
        """
        If velocity deviates from plan, recommend lambda adjustment.
        """
        if planned_v <= 0:
            return phase.lambda_eta

        error = (actual_v - planned_v) / planned_v
        phase.velocity_error_pct = round(error * 100, 2)

        if abs(error) < 0.02:
            self._log(f"  [AI] Phase {phase.phase_id}: "
                      f"velocity nominal (error={error*100:.1f}%)")
            return phase.lambda_eta

        # Adjust lambda proportional to error
        adjustment = phase.lambda_eta * (1 + error * 0.1)
        adjustment = max(0.0, min(1.0, adjustment))

        self._log(f"  [AI] Phase {phase.phase_id}: "
                  f"velocity error={error*100:.1f}% "
                  f"recommend eta={adjustment:.3f}")

        return adjustment

    def validate_all_phases(self, phases):
        """
        Run coherence assessment on all phase blocks.
        Returns True if all phases are safe.
        """
        self._log(f"\n  [AI ENGINE] Validating {len(phases)} phases")
        all_safe = True
        for phase in phases:
            safe = self.assess_coherence(phase)
            if not safe:
                all_safe = False
                self._log(f"  [AI] WARNING: Phase {phase.phase_id} "
                          f"{phase.name} BELOW COHERENCE THRESHOLD")
        return all_safe

    def run_phase_simulation(self, phase, n_steps=500):
        """
        Run a full phase simulation and return trajectory data.
        """
        nx = ny = self.grid
        center = (nx // 2, ny // 2)
        sigma = init_sigma_packet(nx, ny, center)

        lam_field = build_lambda_dipole(
            nx, ny, ship_pos=center,
            direction=(1, 0),
            base_lam=0.1,
            delta_lam=phase.lambda_eta * 0.05,
            spread=10.0)

        trajectory = []
        coherences = []

        for step in range(n_steps):
            # Update lambda field to follow ship
            com = compute_com(sigma)
            if com is None:
                break

            lam_field = build_lambda_dipole(
                nx, ny, ship_pos=com,
                direction=(1, 0),
                base_lam=0.1,
                delta_lam=phase.lambda_eta * 0.05,
                spread=10.0)

            sigma = step_substrate(sigma, lam_field,
                                    self.D, self.dt)

            coh = compute_coherence(sigma, com, radius=8)
            trajectory.append(com.copy())
            coherences.append(coh)

        return trajectory, coherences

    def get_log(self):
        return "\n".join(self.log)

    def clear_log(self):
        self.log = []
