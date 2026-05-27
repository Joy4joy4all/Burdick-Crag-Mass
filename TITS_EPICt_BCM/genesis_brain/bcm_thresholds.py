# -*- coding: utf-8 -*-
"""
BCM Frozen Constants — Work Formulas v24 + Session Docs v15-v24

Stephen Justin Burdick Sr. -- Emerald Entities LLC -- GIBUSH Systems
All theoretical IP: Burdick.

Every constant has its origin session traced in a comment.
Nothing in this module is invented. Thresholds live here only,
NOT inside axes. Axes import these constants by name.
"""

from __future__ import annotations


# ============================================================================
# CORE FIELD CONSTANTS  (v24 — Work Formulas v24 Section 2)
# ============================================================================

LAMBDA_DECAY    = 0.1          # v24  — substrate maintenance cost (universal)
KAPPA_BH        = 2.0          # v24  — SMBH coupling (calibrated, frozen)
ALPHA_MEMORY    = 0.80         # v17  — memory coefficient, sharp alpha locked
ALPHA_BIFURCATE = 0.90         # v24  — memory bifurcation point
GRID_SIZE       = 256          # v22  — production grid resolution
LAYERS          = 8            # v24  — entangled substrate layers

DT_STRIDE       = 1.25e-13     # v17  — CMB-locked timestep (seconds)
C_SUBSTRATE     = 12000        # v20  — crewed substrate speed (x c)
OM_SYNC         = 0.010        # v22  — 1D heartbeat sync reference
FIB_RATIO       = 1.618034     # v20  — golden ratio, 7D ribbon fold into 9D


# ============================================================================
# NAVIGATIONAL DRAIN & RECOVERY BOILER  (v19)
# ============================================================================

KAPPA_DRAIN     = 0.35         # v19  — Venturi tunnel bleed rate, FROZEN
CHI_DECAY       = 0.997        # v19  — recovery boiler decay rate, FROZEN
CHI_C           = 0.002582     # v19  — commutation threshold, MEASURED


# ============================================================================
# BOUNDARY OPERATOR  (v21)
# Craft only — NOT in galactic solver. v23 taught this mistake.
# ============================================================================

K_BOUNDARY      = 150.0        # v21  — Jasper Beach gradient dissipation
PHI_SAFETY      = 0.10         # v21  — max safe phase deviation


# ============================================================================
# 9D COHERENCE GATE  (v21) and 7D MIRROR  (v20)
# ============================================================================

THETA_9TO10     = 0.92         # v21  — 9D-to-10D gate pass threshold
R_9TO10_MIN     = 0.92         # v21  — reflectivity minimum at 9D-10D
R_7D_MIN        = 0.92         # v20  — 7D mirror polish threshold
DELTA_OP_MAX    = 0.08         # v20  — operator divergence max (fogging)
COHERENCE_MIN   = 0.95         # v20  — STARGATE phase alignment minimum


# ============================================================================
# CREW SAFETY THRESHOLDS  (Cube 6 — Guardians / OE)
# ============================================================================

GUARDIAN_MIN         = 0.85    # v20  — crew-grade twin guardian hold
GUARDIAN_FLOOR       = 0.68    # v24  — absolute f/2 heartbeat hold floor
BRUCETRON_HEMORRHAGE = 0.0045  # v17  — crew hemorrhage RMS threshold


# ============================================================================
# CUBE 3 — PHYSICAL / 3D LANDING  (v29 — Burdick, 2026-05-12)
# ============================================================================
# f/2 heartbeat constants derived from v14 kill tests and v17 Brucetron work.
# F2_TARE_FRACTION = 0.115 measured from v14 fixed-pump retention (11.5%).
# F2_TARE_FLOOR    = BRUCETRON_HEMORRHAGE × F2_TARE_FRACTION (= 0.000518)
# F2_HEMORRHAGE    = same as BRUCETRON_HEMORRHAGE (0.0045) — same physical limit.
# organic_f2 = brucetron_rms - F2_TARE_FLOOR
# HEARTBEAT_ACTIVE when organic_f2 > 0 AND brucetron_rms < F2_HEMORRHAGE.

F2_TARE_FRACTION = 0.115       # v14  — fixed-pump retention floor (inorganic)
F2_TARE_FLOOR    = 0.000518    # v29  — BRUCETRON_HEMORRHAGE × 0.115
F2_HEMORRHAGE    = 0.0045      # v17  — same as BRUCETRON_HEMORRHAGE


# ============================================================================
# 7D SPECTRAL FOLD GATE  (v20 — stellar transit)
# ============================================================================

DPHI_GATE            = 0.012   # v20.2 — phase rate trigger
PHASE_LOCK_THRESHOLD = 0.18    # v20.2 — spectral proximity check
PUMP_CLIP            = 0.55    # v20.2 — pre-coupling pump governor
CHI_SHOCK            = 0.82    # v20.2 — fast chi bleed multiplier
GRADIENT_KILL        = 0.85    # v20.21 — nabla_phi flatten at L1


# ============================================================================
# 8D HARD POINT & DISGUISE  (v20)
# ============================================================================

D_CLOAK         = 0.90         # v20  — hard point cloaking strength
D_OPERATION     = 0.75         # v20  — Fibonacci collapse anchor strength
NODE_CLAMP      = 0.92         # v20  — phi zero at L1 (monochord)
CURL_STRENGTH   = 0.65         # v20  — Venturi curl, rifled bore


# ============================================================================
# V24 BOUNDARY DYNAMICS  (catadioptric gate physics)
# ============================================================================
# Pi = sigma_edge / sigma_crit   v24 dimensionless control parameter
# Pi << 1 : naturally stable   (Alpha Centauri wide binary)
# Pi ~ 1  : marginal            (sensitive to perturbation)
# Pi >> 1 : collapse to bulk    (HR 1099 without clamp)
#
# sigma_crit is system-dependent (NOT frozen universally).
# Determined by torus geometry, pump ratio, and substrate class.
# ============================================================================

PI_STABLE   = 0.5              # v24  — Pi below this = naturally stable
PI_MARGINAL = 1.0              # v24  — Pi at this = marginal threshold
PI_COLLAPSE = 2.0              # v24  — Pi above this = bulk flood


# ============================================================================
# COHERENCE REGIME LABELS  (v19/v20/v24)
# ============================================================================

COHERENCE_GREEN   = 0.95       # v19 — STARGATE pass
COHERENCE_YELLOW  = 0.85       # v19 — marginal, guardians hold
COHERENCE_RED     = 0.74       # v24 — Coherence Failure regime


# ============================================================================
# V24 THREE SUBSTRATE REGIMES  (Burdick classification)
# ============================================================================
# Diffusive Healing   : coherence ~ 1.0,  Q(r) mild negative  (buckshot heals)
# Coherence Failure   : coherence 0.74-0.85, Q(r) strongly neg (grind breaks)
# Boundary Nonlinear  : coherence variable,  Q(r) localized pos (edge floods)

REGIME_DIFFUSIVE_HEALING_MIN = 0.95
REGIME_COHERENCE_FAILURE_MIN = 0.74
REGIME_COHERENCE_FAILURE_MAX = 0.85


# ============================================================================
# V18 FRASTRATE  (fractal dimension of probe-written boundary)
# ============================================================================
# D_f = 1.59 at probe trajectory = Frastrate is real
# D_f ~ 0.88 at chi boundary     = no Frastrate at that surface
# The silence has topology only where the craft writes into it.

FRASTRATE_D_F_PROBE = 1.59     # v18 — fractal dim at probe trajectory
FRASTRATE_D_F_CHI   = 0.88     # v18 — chi boundary is flat (no frastrate)


# ============================================================================
# UTILITY
# ============================================================================

# ============================================================================
# NEBULAR / PRE-PUMP SUBSTRATE  (v29 — Burdick, 2026-05-17)
# ============================================================================
# Variant 2 infrastructure — Nebular Formation Operator.
# Directed by SJB. Equation form: Gemini engineering channel.
# Adversarial basis: ChatGPT JWST gap analysis.
#
# KAPPA_CMB: CMB pre-strain scaling governor. Locks the coupling between
#   σ_local and σ_CMB in σ_eff(r) = [σ_local(r)·F_form] + κ_CMB·σ_CMB.
#   Too high → washes out local baryonic structure.
#   Too low → cannot account for JWST "too massive, too early" galaxies.
#   Value 0.01432 established as baseline anchor (v29).
#
# ALPHA_ROOT_DEFAULT: fractional memory-depth exponent for ROOT crag regime.
#   Ξ_S → 1 at ROOT (stiff, integer-like). α=2.0 maps to high commitment.
#
# ALPHA_VOID_DEFAULT: fractional memory-depth exponent for VOID/nebular regime.
#   Ξ_S → 0 at pre-pump nebula. α=1.0 maps to pure fractional accumulation.

KAPPA_CMB          = 0.01432   # v29  — CMB pre-strain coupling governor, LOCKED
ALPHA_ROOT_DEFAULT = 2.0       # v29  — ROOT crag memory depth (stiff, Ξ_S→1)
ALPHA_VOID_DEFAULT = 1.0       # v29  — void/nebular memory depth (fractional, Ξ_S→0)

# W_D: Well-Depth Coefficient (v29 — Burdick 2026-05-17)
# -------------------------------------------------------
# Separates observed luminous size from effective substrate load size.
# L_load = L_obs * W_d
# Galaxy: W_d ~ 1.0 (mass-bound rotating well, full canyon depth)
# Nebula: W_d ~ low (broad luminous/scattering/formation field, rolling hills)
# Without W_d, the solver treats a 3.2 ly nebula as equivalent in well depth
# to a 3.2 ly galaxy slice — physically dishonest.
# Test21 confirmed: PMR 1 absorbed craft tare and recovered above pre-transit sigma.
# That is rolling-hill formation terrain behavior, not canyon/galactic well behavior.
# W_D_NEBULAR_BASELINE: first estimate for stellar nebulae class.
#   PMR 1 at W_d=0.05: L_load = 3.2 ly * 0.05 = 0.16 ly effective well scale.
# W_D_GALACTIC_REF: reference only — galactic framework implicitly uses full depth.

W_D_NEBULAR_BASELINE = 0.05   # v29  — stellar nebula well-depth (shallow rolling terrain)
W_D_GALACTIC_REF     = 1.0    # v29  — galactic reference (full canyon, implicit in solver)


def all_thresholds_dict() -> dict:
    """Return every frozen constant as a dict for logging/reporting."""
    return {
        "LAMBDA_DECAY":         LAMBDA_DECAY,
        "KAPPA_BH":             KAPPA_BH,
        "ALPHA_MEMORY":         ALPHA_MEMORY,
        "DT_STRIDE":            DT_STRIDE,
        "C_SUBSTRATE":          C_SUBSTRATE,
        "OM_SYNC":              OM_SYNC,
        "FIB_RATIO":            FIB_RATIO,
        "KAPPA_DRAIN":          KAPPA_DRAIN,
        "CHI_DECAY":            CHI_DECAY,
        "CHI_C":                CHI_C,
        "K_BOUNDARY":           K_BOUNDARY,
        "PHI_SAFETY":           PHI_SAFETY,
        "THETA_9TO10":          THETA_9TO10,
        "R_9TO10_MIN":          R_9TO10_MIN,
        "R_7D_MIN":             R_7D_MIN,
        "DELTA_OP_MAX":         DELTA_OP_MAX,
        "COHERENCE_MIN":        COHERENCE_MIN,
        "GUARDIAN_MIN":         GUARDIAN_MIN,
        "GUARDIAN_FLOOR":       GUARDIAN_FLOOR,
        "BRUCETRON_HEMORRHAGE": BRUCETRON_HEMORRHAGE,
        "DPHI_GATE":            DPHI_GATE,
        "PHASE_LOCK_THRESHOLD": PHASE_LOCK_THRESHOLD,
        "PUMP_CLIP":            PUMP_CLIP,
        "CHI_SHOCK":            CHI_SHOCK,
        "GRADIENT_KILL":        GRADIENT_KILL,
        "D_CLOAK":              D_CLOAK,
        "D_OPERATION":          D_OPERATION,
        "NODE_CLAMP":           NODE_CLAMP,
        "CURL_STRENGTH":        CURL_STRENGTH,
        "PI_STABLE":            PI_STABLE,
        "PI_MARGINAL":          PI_MARGINAL,
        "PI_COLLAPSE":          PI_COLLAPSE,
        "COHERENCE_GREEN":      COHERENCE_GREEN,
        "COHERENCE_YELLOW":     COHERENCE_YELLOW,
        "COHERENCE_RED":        COHERENCE_RED,
        "FRASTRATE_D_F_PROBE":  FRASTRATE_D_F_PROBE,
        "FRASTRATE_D_F_CHI":    FRASTRATE_D_F_CHI,
        "F2_TARE_FRACTION":     F2_TARE_FRACTION,
        "F2_TARE_FLOOR":        F2_TARE_FLOOR,
        "F2_HEMORRHAGE":        F2_HEMORRHAGE,
        "KAPPA_CMB":            KAPPA_CMB,
        "ALPHA_ROOT_DEFAULT":   ALPHA_ROOT_DEFAULT,
        "ALPHA_VOID_DEFAULT":   ALPHA_VOID_DEFAULT,
        "W_D_NEBULAR_BASELINE": W_D_NEBULAR_BASELINE,
        "W_D_GALACTIC_REF":     W_D_GALACTIC_REF,
    }


if __name__ == "__main__":
    print("BCM Frozen Constants — Work Formulas v24 + Session Docs v15-v24")
    print("Stephen Justin Burdick Sr. -- GIBUSH Systems")
    print("=" * 64)
    for k, v in all_thresholds_dict().items():
        print(f"  {k:24s} = {v}")
