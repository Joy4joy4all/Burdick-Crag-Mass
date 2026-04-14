# -*- coding: utf-8 -*-
"""
BCM Phase Block — Shared Data Structure
==========================================
Stephen Justin Burdick Sr., 2026 -- Emerald Entities LLC

The phase block is the fundamental unit of mission planning.
Every phase of a transit is described by one block. All three
layers (Navigator, Flight Computer, AI Engine) read and write
phase blocks using the same structure.

Three locks. Three keys. All three turn together.
"""

import json
import time


class PhaseBlock:
    """
    One phase of a substrate transit mission.
    Carries position, velocity, lambda settings, coherence
    status, gap checks, and crew authorization.
    """

    def __init__(self, phase_id, name, phase_type,
                 x_au=0.0, y_au=0.0, r_au=0.0,
                 v_kms=0.0, day_start=0, day_end=0,
                 lambda_eta=1.0, lambda_fore=0.05,
                 lambda_aft=0.20,
                 coherence_min=0.20,
                 slew_limit_deg_hr=15.0,
                 bridge_threshold=0.01):
        self.phase_id = phase_id
        self.name = name
        self.phase_type = phase_type  # LAUNCH, INWARD, SLEW, CRUISE, OPS, RETURN

        # Position and velocity
        self.x_au = x_au
        self.y_au = y_au
        self.r_au = r_au
        self.v_kms = v_kms
        self.day_start = day_start
        self.day_end = day_end

        # Lambda drive settings
        self.lambda_eta = lambda_eta
        self.lambda_fore = lambda_fore
        self.lambda_aft = lambda_aft

        # Safety thresholds (crew-set)
        self.coherence_min = coherence_min
        self.slew_limit_deg_hr = slew_limit_deg_hr
        self.bridge_threshold = bridge_threshold

        # Status (updated by AI engine)
        self.coherence_current = 1.0
        self.bridge_tension = 0.0
        self.heading_error_deg = 0.0
        self.velocity_error_pct = 0.0

        # Gap checks (updated by navigator)
        self.sigma_shadow = "CLEAR"
        self.lead_angle_au = 0.0
        self.slew_status = "NOMINAL"
        self.l1_available = False

        # Authorization
        self.navigator_valid = False
        self.ai_coherence_ok = False
        self.crew_confirmed = False

    @property
    def duration_days(self):
        return self.day_end - self.day_start

    @property
    def all_clear(self):
        """All three locks must be turned."""
        return (self.navigator_valid and
                self.ai_coherence_ok and
                self.crew_confirmed)

    def validate_navigator(self):
        """Navigator validates trajectory feasibility."""
        self.navigator_valid = (
            self.v_kms >= 0 and
            self.day_end >= self.day_start and
            self.sigma_shadow == "CLEAR"
        )
        return self.navigator_valid

    def validate_ai(self):
        """AI engine validates coherence safety."""
        self.ai_coherence_ok = (
            self.coherence_current >= self.coherence_min and
            self.heading_error_deg < self.slew_limit_deg_hr
        )
        return self.ai_coherence_ok

    def confirm_crew(self):
        """Crew confirms phase transition."""
        self.crew_confirmed = True
        return self.crew_confirmed

    def to_dict(self):
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "phase_type": self.phase_type,
            "x_au": self.x_au, "y_au": self.y_au,
            "r_au": self.r_au, "v_kms": self.v_kms,
            "day_start": self.day_start,
            "day_end": self.day_end,
            "lambda_eta": self.lambda_eta,
            "lambda_fore": self.lambda_fore,
            "lambda_aft": self.lambda_aft,
            "coherence_min": self.coherence_min,
            "coherence_current": self.coherence_current,
            "slew_limit_deg_hr": self.slew_limit_deg_hr,
            "bridge_tension": self.bridge_tension,
            "heading_error_deg": self.heading_error_deg,
            "velocity_error_pct": self.velocity_error_pct,
            "sigma_shadow": self.sigma_shadow,
            "lead_angle_au": self.lead_angle_au,
            "slew_status": self.slew_status,
            "l1_available": bool(self.l1_available),
            "navigator_valid": bool(self.navigator_valid),
            "ai_coherence_ok": bool(self.ai_coherence_ok),
            "crew_confirmed": bool(self.crew_confirmed),
            "all_clear": bool(self.all_clear),
        }

    def status_line(self):
        nav = "NAV:OK" if self.navigator_valid else "NAV:--"
        ai = "AI:OK" if self.ai_coherence_ok else "AI:--"
        crew = "CREW:OK" if self.crew_confirmed else "CREW:--"
        return (f"  [{self.phase_id}] {self.name:>16} | "
                f"D{self.day_start:>4}-{self.day_end:<4} | "
                f"v={self.v_kms:>6.0f} km/s | "
                f"coh={self.coherence_current:.3f} | "
                f"{nav} {ai} {crew}")

    def __repr__(self):
        return f"PhaseBlock({self.phase_id}, '{self.name}', all_clear={self.all_clear})"
