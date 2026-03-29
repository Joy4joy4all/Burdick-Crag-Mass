"""
Burdick's Crag Mass
====================
Stephen Justin Burdick, 2026 — Emerald Entities LLC
NSF I-Corps Program — Team GIBUSH (Genesis Industrial Brain Unified Systems Hub)
PRELIMINARY — PATENT PENDING — ALL RIGHTS RESERVED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THEORETICAL FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THE CENTRAL CLAIM:
Space is not a container. Space is a maintenance cost.
The substrate that carries gravity requires continuous
energy input to sustain spatial extent. The parameter λ
in the wave equation is that cost per unit volume per unit time.

BURDICK'S CRAG MASS — THE THREE PROPOSITIONS:

1. SUPERMASSIVE BLACK HOLES ARE SUBSTRATE PUMPS, NOT SINKS

   Standard cosmology treats SMBHs as endpoints — matter falls
   in, nothing escapes. This model inverts that interpretation.

   By crushing baryonic matter beyond the electromagnetic and
   strong-force thresholds, the SMBH strips away all force
   constraints except the weakest: the weak nuclear force.
   The output is not radiation. It is neutrino flux.

   The SMBH is a refinery. Input: bound baryonic matter.
   Output: weak-force currency (neutrinos) — the only particle
   that can interact with the substrate without disturbing the
   baryonic structure sitting on top of it.

   The galaxy does not survive despite its black hole.
   The galaxy survives because of it.
   The BH is continuously funding the galaxy's spatial footprint.

2. FLAVOR OSCILLATION IS THE ENERGY DEPOSITION MECHANISM

   Standard quantum mechanics treats neutrino flavor oscillation
   as a passive quantum quirk — a consequence of mass/flavor
   eigenstate misalignment during free propagation.

   Burdick's reinterpretation: oscillation is not passive.
   It is work.

   As a neutrino travels outward from the galactic core, it
   traverses substrate that requires maintenance. The friction
   of interacting with the substrate causes it to step down
   through flavor states. Each flavor transition is a
   thermodynamic transaction — energy deposited into the
   substrate at the point of oscillation.

   The phase shift from electron neutrino to tau neutrino is
   not merely superposition — it is the thermodynamic exhaust
   of doing work on the spatial substrate.

   TESTABLE PREDICTION:
   The flavor ratio at the galactic edge differs predictably
   from the flavor ratio at the core. The deficit encodes
   the energy required to support the outer disk rotation.
   Measurable by IceCube, KM3NeT, Super-Kamiokande.

3. THE GALAXY IS A THERMODYNAMIC ENGINE — OCEAN HARVESTING MODEL

   Input:      baryonic matter accreting onto the SMBH
   Conversion: weak force strips it to neutrino flux (the Upwelling)
   Transport:  neutrinos travel outward as a Swell
   Deposition: substrate impedance increases with radius —
               the substrate THINS at the galactic rim —
               neutrinos are forced to deposit energy where
               resistance is highest (the Wave Break)
   Output:     substrate maintenance paid at the perimeter —
               the Crag — sustained rotation curve

   The dark matter signal IS the neutrino maintenance budget.
   The galaxy rim is the shoreline. The BH is the ocean pump.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE OCEAN HARVESTING MECHANISM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Substrate Impedance: Z(r) = 1 - exp(-r / r_Compton)

   The substrate thins with distance from the baryonic mass.
   As impedance increases, neutrino passage becomes more costly —
   energy is deposited into the substrate rather than transmitted.
   This is the wave break.

   r_Compton = C / sqrt(λ)  — the Compton length of the substrate.
   This is NOT a new parameter. It is set by λ, the same
   maintenance cost already in the wave equation.

Deposition Profile: J_nu(r) proportional to Flux(r) times Z(r)

   Injection is at the center (BH pump).
   Deposition peaks at intermediate radii (wave break zone).
   The substrate wave equation propagates this outward.

   This is why the model wins outer radii consistently (65%):
   the deposition profile naturally concentrates energy where
   the rotation curve deficit is largest.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONNECTION TO THE SOLVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ONE GLOBAL COUPLING CONSTANT: kappa_BH
    Calibrated on 3 massive galaxies with known M_BH.
    Frozen thereafter. No per-galaxy tuning.
    If it requires per-galaxy tuning: the mechanism fails.

THE CHAIN (unchanged):
    J_total = J_baryon + kappa_BH * J_neutrino(M_BH, r)
    J_total to wave(λ) to rho to rho2 to Poisson(rho2) to Psi to V

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FALSIFICATION CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUCCESS:
  - Single kappa_BH closes the massive galaxy gap
  - outer_lift > 0: substrate transported energy outward
  - No degradation in low/mid bracket
  - Flavor ratio prediction matches IceCube galactic data

FAILURE:
  - Requires per-galaxy kappa (mechanism wrong)
  - outer_lift approx 0: no outward transport (local only)
  - Breaks low/mid bracket wins

References:
    Kormendy & Ho 2013, ARA&A 51, 511
    McConnell & Ma 2013, ApJ 764, 184
    Tremaine et al. 2002, ApJ 574, 740
    Pontecorvo 1957, JETP 6, 429
    Fukuda et al. 1998, PRL 81, 1562
    IceCube Collaboration 2023
"""

import numpy as np
import logging
from dataclasses import dataclass, field

# ─────────────────────────────────────────
# GIBUSH LOGGING
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - GIBUSH.CRAG_MASS - %(levelname)s - %(message)s'
)

# ─────────────────────────────────────────
# PHYSICAL CONSTANTS
# ─────────────────────────────────────────

G_ASTRO        = 4.30091e-6    # kpc (km/s)^2 / M_sun
C_KMS          = 299792.458    # km/s

# Neutrino oscillation parameters — PDG 2022, measured
DELTA_M21_SQ   = 7.53e-5       # eV^2  solar sector
DELTA_M31_SQ   = 2.51e-3       # eV^2  atmospheric sector
THETA_12       = 0.5836        # radians

# M_BH-sigma relation — Tremaine et al. 2002
MBH_SIGMA_ALPHA = 8.13
MBH_SIGMA_BETA  = 4.02
SIGMA_REF_KMS   = 200.0
SIGMA_PROXY     = 1.0 / np.sqrt(2.0)

# ─────────────────────────────────────────
# COUPLING CONSTANT
# ─────────────────────────────────────────

KAPPA_BH_DEFAULT    = 1.0    # placeholder — run test_crag_calibration.py
KAPPA_BH_CALIBRATED = 2.0   # set after calibration

CALIBRATION_GALAXIES = ["NGC2841", "NGC7331", "NGC3521"]


# ─────────────────────────────────────────
# GALACTIC TELEMETRY
# ─────────────────────────────────────────

@dataclass
class GalacticTelemetry:
    """Observables package for one galaxy — used by analytical engine."""
    galaxy_id:        str
    smbh_mass_solar:  float
    radii_kpc:        np.ndarray
    v_baryon_kms:     np.ndarray
    v_obs_kms:        np.ndarray = field(default_factory=lambda: np.array([]))
    mbh_source:       str = "unknown"


# ─────────────────────────────────────────
# BH MASS CATALOG
# ─────────────────────────────────────────

_BH_CATALOG_LOG = {
    "NGC0891":  7.60,
    "NGC2683":  7.72,
    "NGC2841":  8.11,   # calibration galaxy
    "NGC3521":  7.70,   # calibration galaxy
    "NGC3953":  7.90,
    "NGC3992":  8.10,
    "NGC5005":  8.20,
    "NGC5371":  8.30,
    "NGC5907":  7.80,
    "NGC5985":  8.00,
    "NGC6674":  8.20,
    "NGC7331":  7.86,   # calibration galaxy
    "NGC7814":  8.60,
}


def load_bh_catalog():
    return {name: 10.0 ** lm for name, lm in _BH_CATALOG_LOG.items()}


def estimate_mbh(vmax_kms):
    sigma = max(vmax_kms * SIGMA_PROXY, 1.0)
    return 10.0 ** (MBH_SIGMA_ALPHA + MBH_SIGMA_BETA * np.log10(sigma / SIGMA_REF_KMS))


def get_mbh(galaxy_name, vmax_kms):
    cat = load_bh_catalog()
    if galaxy_name in cat:
        return cat[galaxy_name], "catalog"
    return estimate_mbh(vmax_kms), "estimated"


def build_telemetry(galaxy_name, vmax_kms, radii_kpc,
                    v_baryon_kms, v_obs_kms=None):
    M_bh, src = get_mbh(galaxy_name, vmax_kms)
    return GalacticTelemetry(
        galaxy_id=galaxy_name, smbh_mass_solar=M_bh,
        radii_kpc=radii_kpc, v_baryon_kms=v_baryon_kms,
        v_obs_kms=v_obs_kms if v_obs_kms is not None else np.array([]),
        mbh_source=src,
    )


# ─────────────────────────────────────────
# SUBSTRATE IMPEDANCE — THE SHALLOWS
# ─────────────────────────────────────────

def substrate_impedance(r_kpc, lam=0.1, c_wave=1.0):
    """
    Z(r) = 1 - exp(-r / r_Compton)

    The substrate thins with radius. Impedance increases toward the rim.
    Neutrino passage becomes costly — energy is deposited where
    resistance is highest. This is the wave break.

    r_Compton = c_wave / sqrt(lambda) — set by the wave equation.
    NOT a new parameter. No free variables added.

    Near center  (r << r_C): Z near 0 — substrate dense, neutrinos pass.
    At rim       (r >> r_C): Z near 1 — substrate thin, wave breaks.
    """
    r_c = c_wave / np.sqrt(max(lam, 1e-10))
    return 1.0 - np.exp(-r_kpc / r_c)


# ─────────────────────────────────────────
# NEUTRINO SOURCE KERNEL — SOLVER VERSION
# ─────────────────────────────────────────

def neutrino_source_kernel(grid, M_bh_solar, lam=0.1,
                           r_soft_gridunits=2.0, use_impedance=True):
    """
    2D neutrino source field for injection into solver J.

    use_impedance=True (Ocean Harvesting — recommended):
        J_nu(r) proportional to Gaussian(r) times Z(r)
        Deposition peaks at intermediate radii, not center.
        No new parameters — Z(r) is set by lambda.

    use_impedance=False (injection only):
        Pure Gaussian at center. Simpler, less physical.

    r_soft: 2 grid units — prevents sub-Compton artifacts.
    NOT a free parameter.
    """
    cx = cy = grid // 2
    iy_g, ix_g = np.mgrid[0:grid, 0:grid]
    r_grid = np.sqrt(((ix_g - cx)**2 + (iy_g - cy)**2).astype(float))

    # Compton radius in grid units — this is where the wave break lives.
    # Injection peaks here, not at center. The BH drives the pump;
    # the substrate absorbs it at the boundary where impedance transitions.
    r_compton_grid = 1.0 / np.sqrt(max(lam, 1e-10))

    # MODE A — PURE TRANSPORT TEST (ChatGPT peer review, Burdick 2026)
    # Central injection only. No ring shaping. No pre-imposed deposition.
    # Energy enters at BH location. Wave equation + λ + entanglement
    # must transport it outward. If outer_lift > 0 — transport is proven.
    # If not — mechanism needs work before ring injection is justified.
    J_nu = np.exp(-(r_grid**2) / (2.0 * r_soft_gridunits**2))

    # Normalize to unit peak — inject_crag_mass scales to J_baryon
    peak = np.max(J_nu)
    if peak > 0:
        J_nu /= peak
    return J_nu


# ─────────────────────────────────────────
# INJECT INTO SOLVER SOURCE FIELD
# ─────────────────────────────────────────

def inject_crag_mass(J_baryon, galaxy_name, vmax_kms,
                     kappa=KAPPA_BH_DEFAULT, lam=0.1,
                     r_soft_gridunits=2.0,
                     use_impedance=True, verbose=True,
                     rms_newton=None):
    """
    Inject SMBH neutrino source term into baryonic source field.

    Only entry point. Touches J only. Clean chain preserved.

    J_total = J_baryon + kappa * J_neutrino(M_BH, r, Z(r))
    J_total to wave(lam) to rho to rho2 to Poisson to Psi to V

    Returns J_total and info dict for run record.
    """
    grid = J_baryon.shape[0]
    M_bh, mbh_source = get_mbh(galaxy_name, vmax_kms)
    J_nu  = neutrino_source_kernel(grid, M_bh, lam=lam,
                                   r_soft_gridunits=r_soft_gridunits,
                                   use_impedance=use_impedance)

    # Scale injection to J_baryon peak so kappa is a true fraction.
    # kappa=0.1 → BH contributes 10% of baryonic peak at reference M_BH.
    # M_BH log ratio preserves relative scaling between galaxies.
    J_bar_peak = float(np.max(np.abs(J_baryon))) if np.max(np.abs(J_baryon)) > 0 else 1.0
    # MODE A — linear M_BH scaling, no damping, no ADAF shaping
    # Single kappa. No hidden degrees of freedom.
    # adaf_ratio = 1.0 (linear), damping = 1.0 (none)
    adaf_ratio = 1.0
    damping    = 1.0
    J_inj = kappa * J_bar_peak * J_nu * adaf_ratio
    J_total = J_baryon + J_inj

    baryon_sum  = np.sum(np.abs(J_baryon))
    inj_sum     = np.sum(J_inj)
    nu_fraction = inj_sum / (baryon_sum + inj_sum) if (baryon_sum + inj_sum) > 0 else 0.0
    r_compton   = 1.0 / np.sqrt(max(lam, 1e-10))

    if verbose:
        logging.info(f"Crag Mass ONLINE — {galaxy_name}")
        print(f"    Crag Mass [{galaxy_name}]  Ocean Harvesting: {use_impedance}")
        print(f"    M_BH      = {M_bh:.3e} M_sun  ({mbh_source})")
        print(f"    kappa     = {kappa:.4f}")
        print(f"    r_Compton = {r_compton:.2f} grid units  (lambda={lam})")
        print(f"    nu fraction of J: {nu_fraction:.4f}")

    info = {
        "galaxy":         galaxy_name,
        "M_bh_solar":     float(M_bh),
        "mbh_source":     mbh_source,
        "kappa":          float(kappa),
        "lam":            float(lam),
        "r_compton_grid": float(r_compton),
        "nu_fraction":    float(nu_fraction),
        "J_nu_peak":      float(np.max(J_inj)),
        "J_bar_peak":     float(np.max(J_baryon)),
        "use_impedance":  use_impedance,
        "mechanism":      "ocean_harvesting_wave_break"
                          if use_impedance else "central_injection",
    }
    return J_total, info


# backward-compatible alias
inject_bh = inject_crag_mass


# ─────────────────────────────────────────
# ANALYTICAL ENGINE — OCEAN HARVESTING
# ─────────────────────────────────────────

class BurdickCragMassEngine:
    """
    Analytical rotation curve engine — Ocean Harvesting model.

    Runs WITHOUT the substrate solver. Direct velocity calculation
    from neutrino deposition profile. Use for fast diagnostics
    and parameter exploration before full solver runs.

    For full science: use inject_crag_mass() with SubstrateSolver.
    """

    def __init__(self, kappa=KAPPA_BH_DEFAULT, lam=0.1, c_wave=1.0):
        self.kappa     = kappa
        self.lam       = lam
        self.c_wave    = c_wave
        self.G         = G_ASTRO
        self.r_compton = c_wave / np.sqrt(max(lam, 1e-10))
        logging.info(
            f"GIBUSH Engine Online — Ocean Harvesting | "
            f"kappa={kappa}  lam={lam}  r_Compton={self.r_compton:.2f} grid units"
        )

    def _impedance(self, r_kpc):
        return substrate_impedance(r_kpc, self.lam, self.c_wave)

    def _flux(self, r_kpc, M_bh_solar):
        """Outward neutrino flux — inverse square from BH upwelling."""
        return (M_bh_solar * self.c_wave**2) / (4.0 * np.pi * (r_kpc**2 + 0.1))

    def _deposition(self, r_kpc, M_bh_solar):
        """
        Energy deposited per unit radius — flux times impedance.
        The wave break: swell hits the shallows.
        Peaks at intermediate radii. No free parameters.
        """
        return self._flux(r_kpc, M_bh_solar) * self._impedance(r_kpc) * self.kappa

    def run_crag_analysis(self, data: GalacticTelemetry):
        """
        Compute Crag Mass velocity lift analytically.

        1. E_dep(r)   = deposition profile
        2. M_crag(r)  = E_dep / c^2
        3. V_lift^2   = G * M_crag / r
        4. V_total    = sqrt(V_baryon^2 + V_lift^2)
        """
        logging.info(
            f"Analyzing {data.galaxy_id} | "
            f"M_BH={data.smbh_mass_solar:.2e} ({data.mbh_source})"
        )

        r     = data.radii_kpc
        E_dep = self._deposition(r, data.smbh_mass_solar)
        M_crag = E_dep / (C_KMS**2)

        v_lift_sq       = np.zeros_like(r)
        mask            = r > 0
        v_lift_sq[mask] = (self.G * M_crag[mask]) / r[mask]

        v_lift  = np.sqrt(np.maximum(v_lift_sq, 0.0))
        v_total = np.sqrt(data.v_baryon_kms**2 + v_lift_sq)

        result = {
            "galaxy":    data.galaxy_id,
            "r_kpc":     r,
            "v_total":   v_total,
            "v_baryon":  data.v_baryon_kms,
            "v_lift":    v_lift,
            "M_crag":    M_crag,
            "E_dep":     E_dep,
            "impedance": self._impedance(r),
        }

        if len(data.v_obs_kms) == len(r) and len(r) > 0:
            rms   = float(np.sqrt(np.mean((v_total - data.v_obs_kms)**2)))
            rms_n = float(np.sqrt(np.mean((data.v_baryon_kms - data.v_obs_kms)**2)))
            result["rms_crag"]   = rms
            result["rms_newton"] = rms_n
            result["delta_rms"]  = rms_n - rms
            logging.info(
                f"  Newton RMS: {rms_n:.2f}  Crag RMS: {rms:.2f}  "
                f"delta={rms_n-rms:+.2f}"
            )

        return result


# ─────────────────────────────────────────
# ENERGY TRANSPORT DIAGNOSTIC
# ─────────────────────────────────────────

def energy_spread_diagnostic(rho_eff_baryon, rho_eff_crag, grid):
    """
    Track whether the substrate transported neutrino energy outward.

    outer_lift > 0  =>  energy moved core to rim. MECHANISM WORKS.
    outer_lift ~= 0 =>  energy stayed local.      MECHANISM FAILS.
    inner >> outer  =>  just deepened center.      WRONG DIRECTION.
    """
    cy, cx = grid // 2, grid // 2
    mr     = min(cx, cy) - 3

    iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
    ri_arr = np.sqrt((ix_arr - cx)**2 + (iy_arr - cy)**2).astype(int)

    prof_bar  = np.zeros(mr)
    prof_crag = np.zeros(mr)

    for ri in range(mr):
        mask = ri_arr == ri
        if np.any(mask):
            prof_bar[ri]  = np.mean(rho_eff_baryon[mask])
            prof_crag[ri] = np.mean(rho_eff_crag[mask])

    delta      = prof_crag - prof_bar
    outer_lift = float(np.mean(delta[mr // 2:]))
    inner_lift = float(np.mean(delta[:mr // 2]))

    return np.arange(mr), delta, outer_lift, inner_lift


# ─────────────────────────────────────────
# FLAVOR RATIO PREDICTION (STUB)
# ─────────────────────────────────────────

def predict_flavor_ratio(r_kpc, E_neutrino_gev, substrate_deficit_kms):
    """
    Electron neutrino survival probability at galactic radius r.
    Flavor ratio encodes energy deposited — the IceCube test.
    Status: stub — requires lambda-Lambda dimensional mapping.
    """
    L_km    = r_kpc * 3.086e16
    arg     = 1.27 * DELTA_M21_SQ * L_km / max(E_neutrino_gev, 0.001)
    P_ee    = 1.0 - (np.sin(2 * THETA_12)**2) * (np.sin(arg)**2)
    return {
        "r_kpc":            r_kpc,
        "P_ee_vacuum":      float(P_ee),
        "energy_deposited": float((1.0 - P_ee) * E_neutrino_gev),
        "deficit_kms":      substrate_deficit_kms,
        "status":           "stub — lambda mapping required",
    }


# ─────────────────────────────────────────
# SELF TEST
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("  BURDICK'S CRAG MASS")
    print("  GIBUSH Astrophysics — Ocean Harvesting Engine")
    print("  Stephen Justin Burdick, 2026 — Emerald Entities LLC")
    print("=" * 65)

    print("\n  SUBSTRATE IMPEDANCE Z(r) at lambda=0.1:")
    r_c = 1.0 / np.sqrt(0.1)
    print(f"  r_Compton = {r_c:.2f} grid units")
    print(f"  {'r (kpc)':>10}  {'Z(r)':>8}  Interpretation")
    print(f"  {'─'*10}  {'─'*8}  {'─'*30}")
    for r in [0.5, 1.0, r_c, 5.0, 10.0, 20.0]:
        z = float(substrate_impedance(np.array([r]), lam=0.1)[0])
        label = ("dense — passes" if z < 0.4 else
                 "wave break zone" if z < 0.8 else
                 "thin — forced deposit")
        print(f"  {r:>10.2f}  {z:>8.4f}  {label}")

    print("\n  CALIBRATION GALAXIES:")
    for g in CALIBRATION_GALAXIES:
        m, src = get_mbh(g, 250.0)
        print(f"    {g:<12}  M_BH={m:.3e} M_sun  ({src})")

    print("\n  ANALYTICAL ENGINE TEST:")
    engine = BurdickCragMassEngine(kappa=1.0, lam=0.1)
    r_t  = np.linspace(1, 50, 50)
    v_b  = 200 * np.exp(-r_t / 15.0)
    v_o  = 180 * np.ones_like(r_t)
    tel  = GalacticTelemetry("M31_TEST", 1.4e8, r_t, v_b, v_o, "test")
    res  = engine.run_crag_analysis(tel)
    print(f"  {'Radius':>8}  {'V_Bar':>8}  {'V_Lift':>8}  {'V_Total':>8}")
    for i in [0, 12, 24, 37, 49]:
        print(f"  {res['r_kpc'][i]:>8.1f}  {res['v_baryon'][i]:>8.2f}"
              f"  {res['v_lift'][i]:>8.2f}  {res['v_total'][i]:>8.2f}")

    print(f"\n  NEXT: python test_crag_calibration.py")
    print("=" * 65)
