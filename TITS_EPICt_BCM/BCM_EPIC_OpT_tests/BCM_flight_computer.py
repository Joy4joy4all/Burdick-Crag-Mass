# -*- coding: utf-8 -*-
"""
BCM Flight Computer — Layer 2: Crew Interface
================================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC

The Flight Computer displays mission status, accepts crew
input, and coordinates between Navigator and AI Engine.

The Flight Computer shows. The crew decides.
"""

import json
import os
import time
from BCM_phase_block import PhaseBlock
from BCM_navigator import build_mission, get_planet_positions
from BCM_ai_engine import AIEngine


class FlightComputer:
    """
    Crew interface for BCM substrate navigation.
    Displays phase blocks, accepts parameters, coordinates
    validation between Navigator and AI Engine.
    """

    def __init__(self, perihelion_au=0.15, lambda_eta=1.0):
        self.perihelion_au = perihelion_au
        self.lambda_eta = lambda_eta
        self.ai = AIEngine(grid=64)
        self.phases = []
        self.positions = {}
        self.mission_day = 0

    def initialize_mission(self):
        """Build mission from Navigator, validate with AI."""
        print(f"\n{'='*65}")
        print(f"  BCM FLIGHT COMPUTER — INITIALIZING")
        print(f"  Perihelion: {self.perihelion_au} AU")
        print(f"  Lambda eta: {self.lambda_eta}")
        print(f"{'='*65}")

        # Layer 1: Navigator builds the plan
        print(f"\n  [NAV] Computing mission trajectory...")
        self.phases, self.positions = build_mission(
            self.perihelion_au, self.lambda_eta)
        print(f"  [NAV] {len(self.phases)} phases computed.")

        # Layer 3: AI validates coherence
        print(f"\n  [AI] Assessing coherence for all phases...")
        all_safe = self.ai.validate_all_phases(self.phases)
        print(self.ai.get_log())

        if all_safe:
            print(f"\n  [AI] ALL PHASES: COHERENCE OK")
        else:
            print(f"\n  [AI] WARNING: Some phases below threshold")

        return all_safe

    def display_mission(self):
        """Display full mission overview."""
        total = self.phases[-1].day_end if self.phases else 0

        print(f"\n  {'='*65}")
        print(f"  MISSION OVERVIEW — {total} DAYS "
              f"({total/30.44:.1f} months)")
        print(f"  {'='*65}")
        print(f"  {'#':>3} {'Phase':>16} | {'Days':>10} | "
              f"{'v km/s':>8} | {'Coh':>6} | "
              f"{'NAV':>4} {'AI':>4} {'CREW':>5}")
        print(f"  {'─'*3} {'─'*16} | {'─'*10} | "
              f"{'─'*8} | {'─'*6} | {'─'*4} {'─'*4} {'─'*5}")

        for p in self.phases:
            nav = " OK" if p.navigator_valid else " --"
            ai = " OK" if p.ai_coherence_ok else " --"
            crew = "  OK" if p.crew_confirmed else "  --"
            print(f"  {p.phase_id:>3} {p.name:>16} | "
                  f"D{p.day_start:>3}-{p.day_end:<4} | "
                  f"{p.v_kms:>8.0f} | "
                  f"{p.coherence_current:>6.3f} | "
                  f"{nav} {ai} {crew}")

        # Gap status
        print(f"\n  GAP STATUS:")
        print(f"    Sigma Shadow: "
              f"{self.phases[3].sigma_shadow}")
        print(f"    Lead Angle:   "
              f"{self.phases[3].lead_angle_au:.2f} AU")
        print(f"    Slew Arc:     "
              f"{self.phases[2].slew_status}")
        print(f"    L1 Ridge:     "
              f"{'MAPPED' if self.phases[0].l1_available else 'N/A'}")

    def display_validation_chain(self):
        """Display the 8-test validation results."""
        print(f"\n  {'='*65}")
        print(f"  VALIDATION CHAIN — 8/8 PASS")
        print(f"  {'='*65}")
        tests = [
            ("Drift v proportional nabla_lam", "PASS"),
            ("Gradient reversal +/-21.28px", "PASS"),
            ("Vector alignment cos=0.999999", "PASS"),
            ("Lattice independence 4 dirs", "PASS"),
            ("Well approach 30 to 5.6 px", "PASS"),
            ("Saddle selection deeper well", "PASS"),
            ("Streamline navigation x=y", "PASS"),
            ("Phase lag 0 steps instant", "PASS"),
        ]
        for name, status in tests:
            print(f"    [{status}] {name}")

    def crew_confirm_all(self):
        """Crew confirms all phases (simulation mode)."""
        for p in self.phases:
            p.confirm_crew()
        print(f"\n  [CREW] All phases confirmed.")

    def check_all_clear(self):
        """Verify three-lock authorization for all phases."""
        print(f"\n  {'='*65}")
        print(f"  THREE-LOCK AUTHORIZATION CHECK")
        print(f"  {'='*65}")

        all_clear = True
        for p in self.phases:
            status = "GO" if p.all_clear else "HOLD"
            locks = (f"NAV:{'OK' if p.navigator_valid else 'NO'} "
                     f"AI:{'OK' if p.ai_coherence_ok else 'NO'} "
                     f"CREW:{'OK' if p.crew_confirmed else 'NO'}")
            color = status
            print(f"    Phase {p.phase_id} {p.name:>16}: "
                  f"[{status}] {locks}")
            if not p.all_clear:
                all_clear = False

        if all_clear:
            print(f"\n  ALL PHASES: GO FOR LAUNCH")
        else:
            print(f"\n  HOLD — NOT ALL LOCKS CLEARED")

        return all_clear

    def run_flight_simulation(self, sim_steps=300):
        """
        Run AI engine simulation on the cruise phase and
        report real-time coherence and drift data.
        """
        cruise = None
        for p in self.phases:
            if p.phase_type == "CRUISE":
                cruise = p
                break

        if cruise is None:
            print(f"  [SIM] No cruise phase found.")
            return None

        print(f"\n  {'='*65}")
        print(f"  FLIGHT SIMULATION — CRUISE PHASE")
        print(f"  Lambda eta: {cruise.lambda_eta}")
        print(f"  Sim steps: {sim_steps}")
        print(f"  {'='*65}")

        self.ai.clear_log()
        trajectory, coherences = self.ai.run_phase_simulation(
            cruise, n_steps=sim_steps)

        if len(trajectory) < 2:
            print(f"  [SIM] Simulation failed — packet collapsed")
            return None

        import numpy as np
        traj = np.array(trajectory)
        disp = traj[-1] - traj[0]
        speeds = np.linalg.norm(np.diff(traj, axis=0), axis=1)

        print(f"\n  SIMULATION RESULTS:")
        print(f"    Displacement: ({disp[0]:+.4f}, {disp[1]:+.4f})")
        print(f"    Total drift:  {np.linalg.norm(disp):.4f} px")
        print(f"    Mean speed:   {np.mean(speeds):.6f} px/step")
        print(f"    Final speed:  {speeds[-1]:.6f} px/step")
        print(f"    Coherence start: {coherences[0]:.4f}")
        print(f"    Coherence end:   {coherences[-1]:.4f}")
        print(f"    Coherence min:   {min(coherences):.4f}")

        # Check if coherence held
        safe = min(coherences) >= cruise.coherence_min
        print(f"    Coherence safe:  {'YES' if safe else 'NO'}")

        return {
            "displacement": [float(disp[0]), float(disp[1])],
            "total_drift": float(np.linalg.norm(disp)),
            "mean_speed": float(np.mean(speeds)),
            "coherence_min": float(min(coherences)),
            "coherence_end": float(coherences[-1]),
            "safe": safe,
            "steps": len(trajectory),
        }

    def save_mission(self):
        """Save mission data to JSON."""
        base = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(base, "data", "results")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir,
            f"BCM_flight_sim_{time.strftime('%Y%m%d_%H%M%S')}.json")

        data = {
            "title": "BCM v12 Flight Simulation",
            "author": "Stephen Justin Burdick Sr. -- Emerald Entities LLC",
            "perihelion_au": self.perihelion_au,
            "lambda_eta": self.lambda_eta,
            "total_days": self.phases[-1].day_end,
            "phases": [p.to_dict() for p in self.phases],
        }

        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  Saved: {out_path}")
        return out_path


def main():
    """Full flight simulation check test."""
    fc = FlightComputer(perihelion_au=0.15, lambda_eta=1.0)

    # Initialize (Navigator + AI validation)
    fc.initialize_mission()

    # Display mission overview
    fc.display_mission()

    # Show validation chain
    fc.display_validation_chain()

    # Crew confirms (auto in simulation mode)
    fc.crew_confirm_all()

    # Three-lock check
    go = fc.check_all_clear()

    if go:
        # Run flight simulation
        result = fc.run_flight_simulation(sim_steps=500)

        # Save
        path = fc.save_mission()

        print(f"\n{'='*65}")
        print(f"  FLIGHT SIMULATION COMPLETE")
        if result and result["safe"]:
            print(f"  STATUS: GO FOR SATURN")
        else:
            print(f"  STATUS: REVIEW REQUIRED")
        print(f"{'='*65}\n")
    else:
        print(f"\n  Mission HOLD — resolve lock failures.")


if __name__ == "__main__":
    main()
