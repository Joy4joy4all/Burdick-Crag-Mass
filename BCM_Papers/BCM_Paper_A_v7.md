# Burdick Crag Mass: A Substrate Wave Model for Galactic Rotation Curves Without Dark Matter
## v7 — Anchor Partition Regime Map, ROOT_REENTRY Anatomy, and Macro-Torsion Operator

**Stephen Justin Burdick Sr.**
Emerald Entities LLC — GIBUSH Systems, Baileyville, Maine, USA

**Correspondence:** GitHub: Joy4joy4all/Burdick-Crag-Mass
**Framework DOI:** 10.5281/zenodo.19251192
**Paper version:** v6 (2026-04-21)
**Data provenance:** Full 175-galaxy SPARC analysis from
BCM_v26_Tully_Fisher_Amplitude_Scaling_Ablation (Test 2 rev 6,
completed 2026-04-21) and bracket-stratified Tully-Fisher
bootstrap from BCM_v26_Tully_Fisher_Exponent_Stability (Test 4,
completed 2026-04-21).

---

## Version History

**v7.0 (2026-05-30):** Anchor Partition Ratio (APR) decomposition across all 175
SPARC galaxies. Six-regime structure identified. 125 km/s snap confirmed (delta=+0.193).
ROOT_REENTRY anatomy (6 galaxies, v_max > 300 km/s). Macro-Torsion operator
proposed, tested regime-safe (5/5 gates, Sections 3.8-3.9). Volume Dilatant
rejected as formulated. Conclusions updated. All v6 content retained verbatim.

**v6.0 (2026-04-21):** Full SPARC 175 analysis, amplitude ablation, Tully-Fisher
exponent stability (alpha=3.42, bracket breakdown at massive v_max).

**v5.0 (2026-04-15):** Einstein coupling, null pump proof, boundary dynamics,
σ_crit saturation limit.

**v1–v4:** Progressive 29-galaxy to full SPARC analysis, Tully-Fisher recovery,
neutrino flux predictions.

---

## Abstract

We present the Burdick Crag Mass (BCM) framework, a substrate-based
phenomenological alternative to cold dark matter in which the dark
matter signal is modeled as the energy maintenance budget of a
pre-existing 2D spatial substrate. The substrate field becomes
gravitationally significant only when continuously agitated by wave
energy; we propose supermassive black hole neutrino flux as the
physical funding mechanism. Using four global parameters
(lambda=0.1, kappa=2.0, grid=256, layers=8) plus one amplitude
coefficient fit per galaxy, we evaluate the framework on the complete
175-galaxy SPARC rotation curve sample (Lelli et al. 2016). BCM beats
Newtonian baryonic fits on 130 of 175 galaxies (74.3%) and beats
MOND on 172 of 175 (98.3%), with mean reduced chi-squared of 63.1
compared to Newton's 157.6 and MOND's 1122.6. An ablation study
confirms that a single global amplitude cannot replace per-galaxy
fitting: the 1-parameter-per-galaxy rescaling outperforms a
1-parameter-total global fit by a factor of 13.8. The per-galaxy
amplitude coefficient remains a single scalar with no free shape
parameters, making BCM competitive with NFW dark matter halo fits
(2 parameters per galaxy) and MOND (global acceleration scale).
Bracket-stratified analysis reveals the framework classifies galaxies
into physically distinct substrate interaction states, with BCM
dominating low-to-mid velocity regimes (88% wins in v_max=50-100 km/s,
82% in 100-150 km/s) and showing systematic weakness in the massive
bracket (v_max > 200 km/s, 61% wins). The Tully-Fisher exponent on
the full sample is alpha = 3.42 (95% CI [3.03, 3.88], consistent
with classical baryonic TF), but bracket-stratified bootstrap reveals
substantial scale-dependence: the TF relation breaks down entirely
at the massive bracket (alpha = -0.29, CI fully below classical),
suggesting a scale-dependent phase transition in the substrate
coupling that will be explored in a forthcoming companion paper.
The framework is formulated as a classical field theory with a
well-defined action and Lagrangian density. We extend the framework
to binary stellar dynamics across three systems (Alpha Centauri,
HR 1099, Spica) and reproduce the structural phases of the GW150914
binary black hole merger. Falsifiable predictions are provided for
IceCube/KM3NeT neutrino flavor ratio gradients at galactic edges,
Betelgeuse m=3 tachocline recovery (circa 2030-2031), and binary
mass transfer rates in synchronized vs unsynchronized systems. All
code, data, and timestamped results are publicly available across
26 versioned Zenodo publications with full adversarial audit records
from four independent AI systems.

**Version 7.0 additions:** The Anchor Partition Ratio (APR) is applied
to all 175 SPARC galaxies as a direct decomposition of observed rotation
curves, requiring no BCM solver execution. APR identifies six empirical
substrate regimes; the dominant structure is a substrate plateau at
50-150 km/s (APR_outer median 0.77, BCM wins 91.9%) and a suppression
valley at 150-300 km/s (APR_outer median 0.47, Newton wins 75.7%). A
sharp APR discontinuity at 125 km/s (delta = +0.193) aligns
independently with the Tully-Fisher bracket transition reported in v6.
Six ROOT_REENTRY galaxies (vmax > 300 km/s) show high outer-disk APR
but BCM underfit; anatomical analysis confirms outer-disk substrate
presence in 5/6. A Macro-Torsion operator T = η·Θ(v_max - 300 km/s)·|∂v_φ/∂r - v_φ/r|
is introduced, tested against all six APR regimes, and confirmed
structurally regime-safe: it produces zero effect on all galaxies below
300 km/s (0.000% η sensitivity, 5/5 gates) while recovering ROOT_REENTRY
outer RMS from 113.5 to 58.4 at test parameters. The operator is not yet
integrated into the BCM solver; it is a confirmed directional extension.

**Keywords:** dark matter alternative, rotation curves, SPARC,
substrate wave model, neutrino flux, galactic classification,
binary dynamics, phase coherence, anchor partition ratio, regime map,
ROOT_REENTRY, macro-torsion operator, substrate plateau, suppression valley

---

## 1. Introduction

The dark matter problem remains one of the central unsolved questions
in astrophysics. Observed galactic rotation curves (Rubin & Ford 1970;
Bosma 1981) require either substantial invisible mass or modifications
to gravitational theory. The standard Lambda-CDM cosmological model
postulates cold dark matter halos surrounding galaxies, reproducing
large-scale structure but encountering persistent difficulties at
galactic scales: the cusp-core problem (de Blok 2010), the missing
satellites problem (Klypin et al. 1999), and the too-big-to-fail
problem (Boylan-Kolchin et al. 2011). Direct detection experiments
have found no particle candidates despite decades of effort.

Modified gravity approaches, particularly MOND (Milgrom 1983) and its
relativistic extensions (Bekenstein 2004), successfully reproduce
individual galaxy rotation curves but require per-galaxy fitting of
the mass-to-light ratio and encounter difficulties with galaxy
clusters and cosmological observations.

We propose a third approach: the dark matter signal is neither missing
mass nor modified gravity but the observable signature of a substrate
maintenance cost. A pre-existing 2D substrate medium becomes
gravitationally significant only when continuously agitated by wave
energy, analogous to how a vibrating drumhead reveals its geometry
through standing wave patterns. The proposed funding source is the
supermassive black hole at the galactic center, continuously injecting
energy into the substrate via neutrino flux. Where the funding stops,
the substrate decays and the gravitational signal disappears —
producing the rotation curve profiles attributed to dark matter halos.

The framework is formulated as a classical field theory with a
well-defined action and Lagrangian density (Section 2.5), from which
the equations of motion are derived via the Euler-Lagrange principle.

This paper presents the mathematical framework (Section 2), the
29-galaxy chi-squared comparison against NFW and MOND (Section 3),
binary stellar dynamics on three systems (Section 4), falsifiable
predictions (Section 5), and discussion of limitations and future
work (Section 6).

---

## 2. The Substrate Model

### 2.1 Wave Equation

The substrate field sigma evolves on a 2D grid according to:

    d^2 sigma / dt^2 = c^2 * laplacian(sigma) - lambda * sigma
                       + S(x,t) + alpha * (sigma - sigma_prev)
                       - gamma * d_sigma/dt

where sigma is the substrate memory field (cumulative agitation),
c is the wave speed, lambda is the decay rate (the maintenance
cost — higher lambda means faster decay without continuous funding),
S(x,t) is the SMBH neutrino flux injection source, alpha = 0.80
is the memory coefficient governing how much substrate state persists
between timesteps, and gamma is the damping coefficient.

The memory term alpha*(sigma - sigma_prev) is critical: it provides
the substrate with history-dependent behavior. At alpha = 0.80 the
system operates in a stable regime; a sharp bifurcation occurs at
alpha = 0.90 (v14 Lagrange equilibrium scan), establishing the
operating window at 0.75 to 0.85.

### 2.2 Crag Mass Injection

The SMBH source term uses Bessel function modes:

    J_crag = kappa_BH * (M_BH / M_ref) * J_m(k * r / r_max)

where kappa_BH = 2.0 is frozen globally (never tuned per galaxy),
J_m is the Bessel function of the first kind of order m, k is the
wavenumber set by the tachocline gate, and r is normalized to the
grid radius r_max = grid/2. The mode m is selected by the
tachocline gate based on the stellar/BH rotation profile. This
produces concentric ring patterns in the substrate field that map
to the observed rotation curve structure.

Black hole masses are obtained from the catalog of Kormendy & Ho
(2013) where available, or estimated from the M_BH-sigma relation
of Tremaine et al. (2002) using V_max / sqrt(2) as a velocity
dispersion proxy.

### 2.3 Rotation Curve Comparison

The substrate-modified circular velocity is:

    v_sub(r) = sqrt(v_newton^2(r) + kappa * sigma(r))

where v_newton(r) is computed from baryonic components (gas + disk +
bulge) provided by SPARC Rotmod files (Lelli et al. 2016).

The substrate velocity contribution is extracted from the solver's
gravitational potential via the clean chain:

    rho_eff = rho^2        (energy density of agitation field)
    Psi = Poisson(rho_eff) (gravitational potential)
    v_sub = sqrt(r * |dPsi/dr|)

The substrate contribution replaces the NFW dark matter halo term.
Per-galaxy amplitude scaling is applied: the substrate velocity
profile shape is the test quantity, not the absolute amplitude.

### 2.4 Global Parameters

Four parameters are fixed globally across all 175 galaxies:

| Parameter | Symbol | Value | Role |
|-----------|--------|-------|------|
| Decay rate | lambda | 0.1 | Substrate maintenance cost |
| BH coupling | kappa_BH | 2.0 | SMBH injection strength |
| Grid resolution | grid | 256 | Spatial resolution |
| Entangled layers | layers | 8 | Substrate depth |

No per-galaxy tuning occurs. The six-class taxonomy (Section 3)
emerges from the interaction between global parameters and each
galaxy's specific baryonic mass distribution and SMBH properties.

### 2.5 Action and Lagrangian Density

The substrate model is derived from a variational principle. The
action is:

    S = integral [ L ] d^2x dt

with Lagrangian density:

    L = (1/2)(d_mu sigma)(d^mu sigma)
        - (lambda/2) sigma^2
        + J_crag * sigma
        + (alpha/2)(sigma - sigma_prev)^2

The first term is the kinetic energy of wave propagation. The second
is the mass term encoding the maintenance cost. The third couples the
SMBH neutrino flux to the substrate. The fourth is the memory term,
which in the continuous limit (sigma - sigma_prev)/dt approaches a
first-order time derivative coupling, standard in dissipative field
theories for open thermodynamic systems.

Variation with respect to sigma yields the Euler-Lagrange equation:

    d^2 sigma/dt^2 = c^2 laplacian(sigma) - lambda*sigma
                     + J_crag + alpha*(sigma - sigma_prev)

which reproduces the solver's wave equation (Section 2.1).

The stress-energy tensor is defined as:

    T_mu_nu = d_mu(sigma) * d_nu(sigma) - g_mu_nu * L

The substrate memory field sigma sources an effective gravitational
contribution through this tensor. The connection between the 2+1
dimensional substrate field and 3+1 dimensional spacetime curvature
is the subject of ongoing work (see Section 6.2).

### 2.6 Numerical Implementation

The wave equation is discretized on a uniform 2D Cartesian grid
using the following scheme:

**Time integration:** Störmer-Verlet (leapfrog):

    rho^(n+1) = 2*rho^n - rho^(n-1)
                + dt^2 * (c^2 * lap(rho^n) - lambda*rho^n + J)
                - gamma * dt * (rho^n - rho^(n-1))

**Spatial discretization:** Five-point Laplacian stencil:

    lap(f)_ij = (f_{i+1,j} + f_{i-1,j} + f_{i,j+1} + f_{i,j-1}
                 - 4*f_{ij}) / dx^2

**Boundary conditions:** Absorbing layer at grid edges. An
exponential taper over 10 grid cells damps the field to zero at
all four boundaries, preventing spurious reflections.

**Inter-layer coupling:** Eight substrate layers are coupled via
nearest-neighbor entanglement with coupling coefficient
epsilon = 0.02:

    transfer = epsilon * (field_l - field_{l+1})

**CFL condition:** c * dt / dx < 1.0 is enforced at initialization.

**Convergence protocol:** Each galaxy is evolved for 20,000 settle
steps followed by 5,000 measurement steps. The measurement-phase
average of rho and sigma provides the converged field. The settle
period eliminates transient initialization artifacts.

**Poisson solver:** Jacobi iterative relaxation with 20,000
iterations and tolerance 1e-7, using Dirichlet boundary conditions
(phi = 0 at all edges).

**Computational cost:** The production run on all 175 SPARC
galaxies at grid=256 with 25,000 integration steps per galaxy
required 148.6 minutes wall time on a single NVIDIA GPU
(Windows 10/11, Python 3.11, CuPy, Anaconda terminal).

**Grid convergence:** Six galaxies change winner classification
from non-BCM to BCM when resolution increases from grid=128 to
grid=256, consistent with the resolution boundary documented in
v14 of the framework development record. Grid=256 is used for
all reported results.


### 2.7 The Anchor Equation

The substrate model is grounded in a single governing equation — the
Anchor Equation — which unifies the classical mass-energy relation
with the substrate corridor contribution. This equation has been
developed progressively from v26 through v30 of the framework; its
full form is stated here for the first time in Paper A.

**Two-term form (v26 baseline):**

    E = M·Phi(sigma)·c²  +  ∮_{Aleph-0} J·dl

The first term, M·Phi(sigma)·c², recovers Einstein's E = mc² as
sigma approaches zero (Phi → 1). This is the Einstein recovery
limit, verified numerically at Alpha Centauri (Phi deviation 3.35e-10,
three to eight orders of magnitude below the 5% falsification
threshold).

The second term, the closed contour integral of substrate current J
around a topological Aleph-Null loop, activates only when the substrate
field is driven toward sigma_crit by paired pump sources (supermassive
black holes). At a single isolated pump or in the absence of substrate
(sigma → 0), J = 0 and this term vanishes identically.

The coupling efficiency Phi(sigma) is:

    Phi(sigma) = 1 - tanh²(sigma / sigma_crit)

Properties: Phi(0) = 1 (empty substrate, pure Einstein);
Phi(sigma_crit) → 0 (saturated substrate, full corridor regime);
dPhi/dsigma < 0 monotonically decreasing.

**Extended five-term form (v27):**

    E = M·Phi(sigma)·c²
        + ∮_{Aleph-0} J·dl
        + integral[ P_{7D→3D} / R_{9→10} ] dXi
        + R(nu · grad(G))
        ± T(Psi_tach)

Term 3 integrates the 7D-to-3D projection operator P_{7D→3D}(OpT, OpC)
across the latent substrate structure Xi, normalized by the R_{9→10}
gate functional. This term governs how much substrate information
survives the dimensional collapse from the full 9D ontological stack
to the observable 3D+time. When the gate closes (R_{9→10} → 0),
the integrand becomes large and integration terminates — the gate
closure physically represents a substrate coherence threshold.

Term 4, R(nu · grad(G)), implements post-Poisson snap-back. It
operates on the substrate velocity field nu dotted with the gradient
of the field-shape generator G. This term produces the tare-edge
behavior observed at the Brucetron Hemorrhage threshold in v17-v19
tests, and is responsible for boundary nonlinear behavior at sigma_crit
saturation.

Term 5, ±T(Psi_tach), represents a forward-lead tachyon contribution
with sign ambiguity. The functional form is deferred pending
operational coupling specification. It is not incorporated in any
current solver computation.

Recovery property: at sigma → 0, all terms except Term 1 vanish
identically, and E → M·c². The full equation reduces to Einstein
in the classical limit. This recovery is enforced as a falsification
constraint: any test run that violates it is rejected as solver error.

**Connection to the Anchor Partition Ratio (v30):**

The APR decomposition introduced in Section 3.8 is the observational
projection of the Anchor Equation onto the measurable velocity excess
of SPARC rotation curves:

    APR(r) = substrate-side term² / (mass-side term² + substrate-side term²)

At APR → 0: the mass term M·Phi(sigma)·c² dominates; Newton explains
the curve. At APR → 1: the corridor term ∮ J·dl dominates; substrate
accounts for most of the velocity excess. The six-regime structure
(Section 3.8) maps which galaxies sit in which regime of the Anchor
Equation's two-term balance.

**Connection to the Macro-Torsion Operator (v30):**

The Macro-Torsion operator proposed in Section 3.9 extends the
right-hand side of the Anchor Equation for ROOT_REENTRY systems by
adding a velocity-shear torsion tensor:

    T_munu = eta · Theta(vmax - 300 km/s) · |dv_phi/dr - v_phi/r|

This is a proposed additional term to the substrate corridor side of
the Anchor Equation, gated by the Heaviside function to activate only
when the galactic rotation velocity exceeds 300 km/s — the ROOT_REENTRY
threshold identified in Section 3.7. At this threshold, the standard
two-term Anchor Equation underestimates the outer-disk substrate
contribution, and the torsion term provides the missing coupling.

**Calibration and open questions:**

The Anchor Equation as formulated is phenomenological. The connection
between the 2+1D substrate field and the 3+1D stress-energy tensor
is developed in Section 2.5 but not yet closed into a derivation
from first principles. Term 5 (tachyon contribution) has not been
assigned an operational form. The R_{9→10} gate functional is
operationally defined through the OpT/OpC proxy values but not yet
anchored to a physical observable. These are the primary theoretical
targets for Papers B and C.


---

## 3. SPARC Rotation Curve Classification

### 3.1 Dataset

We use the complete 175-galaxy SPARC dataset (Lelli et al. 2016),
which provides observed rotation curves and baryonic mass models
(gas + disk + bulge) for late-type galaxies spanning five velocity
brackets: dwarf (V < 50 km/s), low (50-100), mid (100-150), high
(150-200), and massive (V > 200 km/s).

### 3.2 Six-Class Substrate Taxonomy

Running the substrate solver on all 175 galaxies with fixed global
parameters produces a natural classification into six physically
distinct substrate interaction states:

**Class I — Transport-Dominated:** The substrate is the dominant
contributor to the rotation curve. The SMBH maintains a strong,
well-funded torus extending beyond the visible disk. Substrate RMS
wins over Newton by significant margins (e.g., NGC 2841, +28.4 km/s).

**Class II — Residual/Hysteresis:** Substrate contribution is
present but secondary. The galaxy is in a transitional state
between full substrate dominance and ground state.

**Class III — Ground State:** Minimal substrate activity. The
baryonic mass distribution alone nearly explains the rotation
curve. The SMBH injection is weak or the galaxy is too diffuse
to maintain a coherent substrate field.

**Class IV — Declining Substrate:** Outer rim depletion. The SMBH
maintains the inner substrate but funding does not extend to the
outer disk. A characteristic inner win / outer loss pattern
emerges.

**Class V-A — Ram Pressure:** Asymmetric lambda field from
external environmental interaction (galaxy cluster membership).

**Class V-B — Substrate Theft:** Multi-body SMBH competition.
A secondary SMBH or nearby massive galaxy depletes the local
substrate field. Confirmed for NGC 7793 via THINGS VLA HI
Moment-0 morphology (Walter et al. 2008).

**Class VI — Barred Substrate Pipe:** The galactic bar channels
substrate flux along its axis, creating a dipole injection
pattern. Confirmed for NGC 3953 via bar geometry and LINER
throttle classification.

### 3.3 Classification Stability

The six-class boundaries are stable under perturbation of global
parameters (lambda, kappa_BH, grid). Sweeping lambda from 0.05
to 0.20 shifts the magnitude of substrate wins but does not
reclassify galaxies between classes. This stability indicates
physical boundaries in galactic substrate topology rather than
model artifacts.

### 3.4 Coupling Efficiency

The substrate coupling efficiency:

    eta = c_substrate / v_medium

maps directly to the six classes: eta > 1 (Class I,
substrate-dominated), eta ~ 1 (Class II, coupled boundary),
eta < 1 (Classes III-IV, medium-dominated). The classification
describes coupling regimes, not mass distributions.

### 3.5 Quantitative Comparison: BCM vs Newton vs MOND on Full SPARC 175

A production run was performed on all 175 galaxies in the SPARC
sample at grid=256 with 25,000 integration steps per galaxy. Four
models are compared:

- **BCM RESCALED:** Four frozen global parameters (lambda=0.1,
  kappa_BH=2.0, grid=256, layers=8), plus one amplitude coefficient
  A fit per galaxy via least-squares minimization against the
  observed rotation curve. The per-galaxy amplitude is a single
  scalar with no free shape parameters.
- **BCM GLOBAL:** Same global parameters as RESCALED, but with a
  single amplitude coefficient fit once across the entire 175-galaxy
  sample (1 parameter total).
- **BCM RAW:** Global parameters only, amplitude = 1.0 (zero fitted
  parameters). Included as an ablation to verify that the amplitude
  fit is carrying real information rather than being an arbitrary
  normalization.
- **MOND:** Standard simple interpolation mu(x) = x/(1+x) with
  a_0 = 1.2 x 10^-10 m/s^2 (Milgrom 1983). Zero per-galaxy tuning
  (same M/L as SPARC baryonic decomposition).
- **Newtonian:** Baryonic components only (gas + disk + bulge),
  zero free parameters.

The reduced chi-squared is computed as:

    chi^2_red = (1 / (N - p)) * sum( (V_model - V_obs)^2 / errV^2 )

where N is the number of radial data points, p is the number of
per-galaxy free parameters, and errV is the observational velocity
uncertainty (floored at 1 km/s).

**Table 1: Summary statistics on the complete 175-galaxy SPARC
sample (grid=256, production run, 148.6 min GPU runtime)**

| Model | Free params | Wins vs Newton | Mean chi2 | Median chi2 |
|-------|-------------|----------------|-----------|-------------|
| BCM RESCALED | 1 per galaxy | 130/175 (74.3%) | 63.1 | 17.7 |
| Newton | 0 | — (baseline) | 157.6 | 51.6 |
| BCM GLOBAL | 1 total | 10/175 (5.7%) | 870.6 | 255.0 |
| MOND | 0 | 3/175 (1.7%) | 1122.6 | 343.9 |
| BCM RAW | 0 | 0/175 (0%) | 5.0e10 | 6.9e8 |

BCM RESCALED achieves the lowest mean reduced chi-squared of any
model tested, beating Newton on 74.3% of galaxies and MOND on 98.3%.
The global amplitude fit from BCM RESCALED settles at
A_global = 1.299 x 10^-4 (dimensional conversion from substrate
code units to observed km/s).

**Parameter count honesty.** BCM RESCALED uses one free parameter
per galaxy. BCM GLOBAL (1 parameter total) performs 13.8x worse than
RESCALED, and BCM RAW (0 parameters) fails catastrophically. This
establishes that the per-galaxy amplitude is doing real physical
work, not absorbing model freedom. For comparison, NFW dark matter
halo fits employ 2 parameters per galaxy (concentration c and
virial mass M_vir), and MOND employs 1 global parameter (a_0).
BCM RESCALED sits between NFW and MOND in parameter count.

**Bracket-stratified performance:**

| Bracket | N | Newton chi2 | MOND chi2 | BCM chi2 | BCM wins |
|---------|---|-------------|-----------|----------|----------|
| Dwarf (V<50) | 22 | 30.3 | 613.5 | **7.5** | 12/22 (55%) |
| Low (50-100) | 64 | 128.3 | 1086.7 | **31.7** | 56/64 (88%) |
| Mid (100-150) | 33 | 218.3 | 1427.7 | **40.4** | 27/33 (82%) |
| High (150-200) | 18 | 84.4 | 714.3 | **57.4** | 12/18 (67%) |
| Massive (V>200) | 38 | 262.7 | 1406.2 | **170.7** | 23/38 (61%) |

BCM is strongest in the low and mid velocity brackets (88% and 82%
wins). The dwarf bracket is competitive at 55% wins, though absolute
chi-squared values are small for all models at that scale. The
massive bracket is the framework's observed weakness, with 61% wins
and a mean chi-squared of 170.7 — higher than any other bracket.
This pattern is consistent with the Tully-Fisher analysis in Section
3.6.

**Representative individual performance.** Among the galaxies where
BCM RESCALED produces the largest improvement over Newton:

| Galaxy | V_max | Newton chi2 | BCM chi2 | Improvement |
|--------|-------|-------------|----------|-------------|
| UGC00128 | 134 | 2485.3 | 302.1 | 8.2x |
| UGC02487 | 383 | 1349.7 | 174.5 | 7.7x |
| UGC00634 | 108 | 1172.6 | 45.4 | 25.8x |
| NGC5055 | 206 | 1592.0 | 560.0 | 2.8x |
| UGC05716 | 75 | 998.8 | 49.4 | 20.2x |
| DDO154 | 48 | 486.4 | 6.7 | 72.5x |
| UGC11820 | 85 | 559.8 | 9.1 | 61.5x |

Galaxies where Newton wins and BCM fails are concentrated in the
massive bracket: UGC05253 (V=248), UGC03546 (V=262), NGC0801
(V=238), NGC2955 (V=276), UGC02916 (V=218). In these systems, the
Newtonian baryonic decomposition alone fits the rotation curve
tightly, and BCM over-corrects via the substrate contribution.

### 3.6 Tully-Fisher Exponent Stability

To test whether the BCM framework reproduces the Tully-Fisher
relation, we fit a linear regression on the full sample:

    log(sigma_energy_integral) = alpha * log(V_max_obs) + intercept

where sigma_energy_integral is the integrated substrate energy
over the galaxy's rotation curve, and V_max_obs is the observed
peak rotation velocity. The fit was performed both on the full
sample and on bracket-stratified subsamples, with bootstrap
resampling (1000 iterations, seed=42) to produce 95% confidence
intervals.

**Full-sample fit:** alpha = 3.42 (95% CI [3.03, 3.88]),
Pearson r = 0.79, r^2 = 0.62. The exponent falls within the
classical baryonic Tully-Fisher range [3.0, 4.0] (McGaugh et al.
2000).

**Bracket-stratified fits:**

| Bracket | N | alpha median | 95% CI | Pearson r |
|---------|---|--------------|--------|-----------|
| Dwarf | 22 | 1.06 | [-0.63, +3.03] | 0.25 |
| Low | 64 | 2.06 | [+0.21, +3.98] | 0.24 |
| Mid | 33 | 7.44 | [+0.66, +13.87] | 0.40 |
| High | 18 | 6.20 | [-3.43, +16.20] | 0.27 |
| Massive | 38 | **-0.29** | **[-2.36, +2.76]** | -0.03 |

The massive bracket is the only bracket whose 95% confidence
interval falls fully below the classical Tully-Fisher range. The
near-zero Pearson r in the massive bracket (r = -0.03) indicates
the log(sigma_energy) - log(V_max) correlation has essentially
vanished at this scale: the BCM framework's substrate-velocity
coupling weakens systematically at V_max > 200 km/s.

The bracket-stratified alpha values span 7.7 units between the
mid-bracket maximum (+7.44) and the massive-bracket minimum
(-0.29), with an interior peak at the mid velocity range. This
scale-dependent profile is an empirical finding from the data and
is formally documented in the Test 4 JSON artifact
(BCM_v26_Tully_Fisher_Exponent_Stability_20260421_081146).

**Interpretation for Paper A.** We report alpha = 3.42 as the
full-sample Tully-Fisher exponent, but emphasize that the
relation is scale-dependent across the BCM framework: the relation
holds (within classical range) in the ensemble but breaks at the
massive bracket. This is an honest statistical description of the
data and does not claim that BCM produces a universal Tully-Fisher
exponent across all galactic scales.

### 3.7 Scale-Dependent Substrate Coupling

The pattern of alpha variation across velocity brackets — small at
low v, peaking at mid v, vanishing at massive v — combined with
the chi-squared degradation at the massive bracket suggests a
scale-dependent transition in the substrate coupling. Whether this
transition is numerical (a limitation of the BCM amplitude fit at
high v) or physical (a genuine phase transition in the substrate
response at high baryonic density) is beyond the scope of Paper A.

The empirical observation stands: the BCM framework as formulated
fits rotation curves across 74% of the SPARC sample, dominates
the low-to-mid velocity regime, and shows systematic weakness at
v_max > 200 km/s. A theoretical extension of the framework
addressing this scale-dependence through a modulation of the
classical mass-energy term is under development and will be
presented in a companion paper (Paper B, in preparation). Paper A's
claims do not depend on Paper B.

### 3.8 Anchor Partition Regime Map (v7)

**The Anchor Partition Ratio.** We introduce the Anchor Partition
Ratio (APR), a direct decomposition of observed SPARC rotation curves
that requires no BCM solver execution:

    APR(r) = max(V_obs²(r) - V_newton²(r), 0) / V_obs²(r)

    where V_newton²(r) = V_gas²(r) + V_disk²(r) + V_bul²(r)

APR measures what fraction of the observed rotation velocity cannot
be explained by visible baryons. It is a property of the SPARC
observational data, not of any model. APR_max denotes the maximum
APR across the rotation curve; APR_outer denotes the mean APR over
the outer third of the disk (r >= 0.67 r_max).

Across 175 galaxies: APR_max median = 0.693; 152/175 (86.9%) have
APR_max >= 0.30, meaning the substrate-side term must be substantial
in the large majority of SPARC galaxies for the Anchor Equation to hold.

**Six-regime structure.** Applying APR across the full SPARC175 sample
with the regime assignment rules below identifies six empirically
distinct substrate coupling regimes:

    MASS_FLOOR (23 galaxies):          APR_max < 0.30
    DWARF_INTERMEDIATE (18 galaxies):  v_max < 50 km/s
    SUBSTRATE_PLATEAU (62 galaxies):   50 ≤ v_max < 150, APR_outer ≥ 0.65
    MIXED_TRANSITION (29 galaxies):    50 ≤ v_max < 150, APR_outer < 0.65
    SUPPRESSION_VALLEY (37 galaxies):  150 ≤ v_max < 300 km/s
    ROOT_REENTRY (6 galaxies):         v_max ≥ 300 km/s

The SUBSTRATE_PLATEAU regime (APR_outer median 0.773) coincides with
the BCM performance peak: BCM wins 91.9% of galaxies in this regime.
The SUPPRESSION_VALLEY (APR_outer median 0.471) coincides with the
regime where Newton dominates: Newton wins 75.7%. This retrodicts
Paper A's bracket performance pattern from a completely independent
decomposition, not from the solver.

**125 km/s snap.** The APR_outer mean drops sharply at 125 km/s:

    Below 125 km/s: APR_outer_mean = 0.6179 (n=109)
    Above 125 km/s: APR_outer_mean = 0.4248 (n=66)
    Delta:          +0.1931

This boundary aligns with the Tully-Fisher exponent peak (alpha = 7.44)
in the mid-velocity bracket (Section 3.6) — two independent measurements
identifying the same substrate transition. The snap is a property of
the SPARC observational data, not a solver artifact.

**ROOT_REENTRY anatomy.** The six ROOT_REENTRY galaxies — ESO563-G021,
NGC2841, NGC5985, UGC02487, UGC02885, UGC02953 — carry APR_outer 0.51-0.76,
indicating substantial outer-disk substrate signal. However, the current
BCM solver (Paper A architecture) underperforms Newton on these systems:
mean BCM outer RMS = 94.0 versus Newton outer RMS = 78.7. Anatomical
analysis confirms the substrate signal is outer-disk dominated in 5/6
systems, and the solver failure is largest in the outer zone. This gap
is not evidence that the BCM framework is incorrect; it identifies where
the current solver architecture lacks an appropriate operator for
ROOT-scale substrate geometry.

One exception: UGC02487 (v_max = 383 km/s), the most extreme
ROOT_REENTRY system, is the only BCM win in this regime (BCM RMS 92.4
versus Newton RMS 109.5). This system is the primary calibration target
for ROOT_REENTRY operator development.

### 3.9 Macro-Torsion Operator — Proposed Extension (v7)

To address the ROOT_REENTRY underfit, we propose a Macro-Torsion operator:

    T_μν(r) = η · Θ(v_max - v_crit) · |∂v_φ/∂r - v_φ/r| · ê_φ

where:
  η       = coupling viscosity coefficient (free parameter)
  Θ       = Heaviside step function at v_crit = 300 km/s
  |shear| = |∂v_φ/∂r - v_φ/r| = magnitude of differential rotation

The shear term |∂v_φ/∂r - v_φ/r| is computable directly from observed
rotation curves without solver execution. For ROOT_REENTRY galaxies with
flat or declining outer rotation, ∂v_φ/∂r ≈ 0 and v_φ/r > 0, producing
a negative shear that characterizes their differential rotation structure.
The absolute value ensures the torsion tensor responds to the magnitude
of differential rotation rather than its sign.

**Regime isolation.** Applied across all six APR regimes, the Heaviside
gate produces strict structural isolation: η sensitivity = 53% for
ROOT_REENTRY (v_max > 300 km/s, Θ=1) and exactly 0.000% for all other
regimes (Θ=0). The isolation is architectural; η can take any value and
produces zero effect on any galaxy below v_crit.

**Performance.** On the six ROOT_REENTRY galaxies at test parameter
η = 100, the operator reduces mean outer RMS from 113.5 (baseline
without solver) to 58.4 — a 48% reduction. The complete η sweep:

    η = 0:    outer RMS = 124.8
    η = 10:   outer RMS = 116.8
    η = 50:   outer RMS = 88.4
    η = 100:  outer RMS = 58.4

**Calibration status.** η = 100 is a first probe parameter, not a
physically calibrated value. v_crit = 300 km/s matches the ROOT_REENTRY
regime boundary and is well motivated. Physical calibration of η requires
outer-disk kinematic data for ROOT_REENTRY galaxies at ALMA resolution.
The operator is not yet integrated into the BCM solver. Paper A's
numerical results (Section 3.5) do not incorporate this operator.
It is presented here as a falsifiable direction: if correct, the six
ROOT_REENTRY galaxies should show improved residuals when the solver is
extended with this term.

**Volume Dilatant — rejected as formulated.** A companion operator
(Volume Dilatant, Λ_vol) was tested but rejected: it worsened ROOT_REENTRY
outer RMS and damaged control regime performance (SUPPRESSION_VALLEY
degraded by 305%) due to per-galaxy normalization that removed all mass
discrimination. A physically anchored reformulation using absolute mass
scaling (M_encl/M_0, M_0 = 10¹¹ M_sun) may be viable as a future
extension; the current formulation is not confirmed.

---

## 4. Binary Stellar Dynamics

### 4.1 Tidal Hamiltonian

The binary substrate bridge system places two stellar pumps on
a shared wave grid. The tidal Hamiltonian:

    H_tidal(m) = (v_A + v_tidal - Omega*R_tach/m)^2

where v_tidal = Omega_orb * R_tach / 2 is derived from the
orbital period with no free parameters. This resolved the first
stellar Class VI: HR 1099 observed at m=2 vs standard Alfven
prediction m=12 — the tidal correction produces the correct mode.

### 4.2 Three Binary Systems

| System | Mass ratio | Separation | Synchronization | Key result |
|--------|-----------|------------|-----------------|------------|
| Alpha Centauri | 3.5:1 | 23.4 AU | No | Coherent bridge, continuous drain |
| HR 1099 | 14:1 | ~10 R_sun | Yes (P_orb=2.84d) | Resistant to colonization, I_B > 0 |
| Spica | 8.4:1 | ~30 R_sun | No (P_orb=4.014d) | One-way drain confirmed |

### 4.3 Phase-Lock Coherence Law

Amplitude stress testing from 8.4:1 to 420:1 pump ratio reveals
that cos(delta_phi) remains +1.000000 through 336:1, with first
hairline fracture (0.999999) at 420:1. The Phi_reach metric
(flood-fill connectivity of ultra-coherent pixels) reproduces
four independently derived metrics (sig_drift, I_B, TCF rate,
Psi_Phi) in the same ordering without additional parameters.

**Burdick Phase-Lock Coherence Law:** Synchronization maximizes
coherent reach; coherent reach determines flow regime; flow
regime determines survival.

### 4.4 External Validation

HR 1099 shows no mass transfer for 70-80 Myr (Fekel 1983),
consistent with the I_B > 0 resistant prediction. Orbital period
oscillates rather than decaying (Donati et al. 1999), consistent
with alternating time-cost. Spica shows Struve-Sahade effect
confirming one-way drain spectroscopically.

---

## 5. Falsifiable Predictions

### 5.1 Neutrino Maintenance Luminosity and Flavor Gradient

The substrate maintenance cost lambda produces a quantitative
prediction for each galaxy's neutrino luminosity. Back-calculating
the substrate field sigma(r) from the BCM rotation curve fits
(Section 3.5) and computing the energy required to maintain that
field against lambda decay yields a maintenance luminosity L_nu
for each galaxy.

The maintenance luminosity scales as:

    L_nu ~ v_max^3.9

independently recovering the baryonic Tully-Fisher relation
(L ~ v^4; Tully & Fisher 1977) from the same four frozen global
parameters used for rotation curve fitting. This scaling was not
an input to the model — it emerges from the substrate energy
budget.

For the 29-galaxy sample, maintenance luminosities range from
10^36 erg/s (dwarf galaxies) to 10^43 erg/s (massive galaxies).
All predicted luminosities remain sub-Eddington (L_nu/L_Edd <
6 x 10^-4), confirming physical self-consistency: no galaxy
requires more neutrino power than its SMBH can provide.

The predicted neutrino energy flux at Earth exceeds the IceCube
point-source sensitivity (10^-12 GeV cm^-2 s^-1) by 2-5 orders
of magnitude for all galaxies within 20 Mpc, suggesting that
the signal may already be present in existing data as
unrecognized extended emission.

The unique BCM signature is the radial gradient: Class IV
galaxies (inner-funded, outer-depleted) should exhibit higher
neutrino density at inner radii declining to background at the
torus edge. Class I galaxies (fully funded) should show uniform
emission across the disk. Testable by angular stacking of
IceCube/KM3NeT events around nearby SPARC galaxies. Null test:
the gradient should vanish for Class I targets.

### 5.2 Betelgeuse Recovery

The m=3 substrate pattern was disrupted by the Great Dimming
(Montarges et al. 2021). BCM predicts full stable m=3 recovery
circa 2030-2031 (~11.5 years post-event = one substrate node
settle time). The coupling efficiency eta = 0.98% (convection
102x faster than substrate phase speed) establishes the recovery
timescale.

### 5.3 Binary Mass Transfer

Tidally synchronized binaries will exhibit reduced mass transfer
rates compared to unsynchronized binaries at similar separation.
Testable against existing RS CVn, Algol-type, and W UMa contact
binary catalogs.

### 5.4 Mercury Magnetosphere

BepiColombo m=1 magnetosphere measurement prediction on record
before data arrives.

### 5.5 Benchtop Falsification — Substrate Mode Selection Device (SMSD)

The Substrate Mode Selection Device (SMSD) is a proposed $225-$230
benchtop apparatus designed to test BCM's discrete substrate mode
structure at laboratory scale. It has not yet been built. The design
is published here so that students or independent researchers can
replicate and falsify the prediction without requiring observational
infrastructure.

**Physical principle.** The SMSD is a Taylor-Couette cell: a rotating
inner cylinder inside a stationary outer cylinder, with the annular
gap filled with galinstan (room-temperature liquid metal). Four N52
neodymium magnet blocks positioned 90 degrees apart around the outer
cylinder create an external magnetic field through the fluid. Three
SS49E Hall sensors positioned 120 degrees apart on the outer cylinder
measure azimuthal magnetic field variations as the inner cylinder rotates.
BCM predicts that the magnetohydrodynamic response of the conducting
fluid will organize into discrete azimuthal modes rather than a smooth
continuum — the substrate mode staircase.

**Bill of Materials:**

    1.  Clear acrylic outer cylinder, ID 80mm, wall 5mm, length 150mm
    2.  316 stainless steel inner cylinder, OD 60mm, length 140mm,
        smooth machined surface
    3.  Galinstan liquid-metal, fills 10mm annular gap
    4.  Top and bottom acrylic end caps
    5.  Top and bottom 608ZZ bearings
    6.  PTFE seal ring (base)
    7.  Viton O-rings (base)
    8.  Flexible shaft coupler
    9.  NEMA 17 stepper motor
    10. A4988 stepper driver board
    11. Arduino Uno R3 controller
    12. SS49E Hall sensors, 3 total, 120 degrees apart
    13. N52 neodymium magnet blocks, 4 total, 90 degrees apart
    14. Magnet mount bracket
    15. Gap spacer inserts: 5mm, 10mm, 15mm (Configuration C variants)
    16. 12V power supply, wiring, and connectors

    Estimated build cost: $225-$230 USD

**Three test configurations:**

Configuration A — Discrete Mode Staircase. Sweep inner cylinder
rotation rate (omega_in) from 0 to maximum. BCM predicts the Hall
sensor output will show discrete steps in azimuthal mode number as
rotation rate increases — the mode staircase. A smooth monotonic
increase in signal with no steps would falsify this prediction.

Configuration B — m=1 Lock. At a specific rotation rate, BCM predicts
a single dominant azimuthal mode (m=1) will lock and rotate coherently,
visible as a stable periodic signal across all three Hall sensors with
120-degree phase offsets. Absence of this locked coherent mode at any
rotation rate would falsify BCM's mode-selection mechanism.

Configuration C — Boundary Analog. Replace the 10mm annular gap with
5mm or 15mm gap spacer inserts. BCM predicts the mode structure shifts
with gap geometry — specifically that the critical rotation rate for
mode locking scales with the gap-to-radius ratio. This tests whether
the substrate sigma_crit boundary behavior is geometrically encoded
in the fluid response.

**Falsification criteria.** The SMSD falsifies BCM if: (1) no discrete
mode steps appear in Configuration A across the full rotation range;
(2) no coherent m=1 lock appears in Configuration B; or (3) mode
structure is invariant to gap geometry change in Configuration C.
Any one of these three is sufficient for falsification. All three
passing is necessary but not sufficient for confirmation — the device
tests the mode-selection mechanism, not the full substrate model.

The SMSD is accessible to any physics student or independent researcher.
No clean room, no cryogenic infrastructure, and no telescope time required.
The Arduino controller and A4988 driver board are standard maker-community
components. Galinstan is available from specialty chemical suppliers.
The full design was developed by Stephen Justin Burdick Sr. (Emerald
Entities LLC — GIBUSH Systems) and is published here under the same
CC BY-NC-ND 4.0 license as this paper.

---

## 6. Discussion

### 6.1 Comparison to Existing Approaches

BCM differs from both dark matter and modified gravity in its
ontological claim: the gravitational signal attributed to dark
matter is modeled as the maintenance cost of spatial substrate,
not missing mass or modified force law. The six-class taxonomy
provides a physical classification scheme that neither NFW halo
fitting (which requires per-galaxy parameters) nor MOND (which
provides a universal acceleration scale but no classification)
offers.

The chi-squared comparison (Section 3.5) demonstrates that BCM
with one amplitude parameter per galaxy achieves a lower mean
chi-squared than MOND (zero per-galaxy parameters) and performs
competitively against NFW (two fitted parameters per galaxy,
typical in SPARC literature analyses). The BCM amplitude parameter
is a single scalar with no shape freedom. This does not prove the
substrate model is correct — it demonstrates that the substrate-
wave approach is competitive with established dark matter and
modified-gravity alternatives on a broad galactic sample.

### 6.2 Limitations

The framework has significant limitations that must be addressed
in future work:

The model has not been tested against gravitational lensing
observations. This is the primary validation gap — dark matter
alternatives historically encounter difficulties reproducing
lensing constraints, and BCM may fail here.

The model has not been tested against CMB power spectrum
constraints, large-scale structure formation, or Bullet Cluster
dynamics — all areas where Lambda-CDM performs well.

The physical mechanism for substrate maintenance (SMBH neutrino
flux) is a proposed interpretation, not a derived result. The
model functions phenomenologically regardless of the physical
funding mechanism; the chi-squared results (Section 3.5) depend
only on the wave equation and its parameters, not on the
neutrino interpretation. The substrate field operates on a 2+1
dimensional manifold; the projection rules connecting this to
3+1 dimensional spacetime curvature are the subject of ongoing
theoretical work.

The per-galaxy amplitude scaling applied to the substrate
velocity profile (Section 2.3) means that BCM tests the shape
of the rotation curve contribution, not its absolute magnitude.
A future version must derive the amplitude from first principles.

### 6.3 AI Collaboration Methodology

The framework was developed through directed collaboration with
four independent AI systems: Claude (Anthropic) for code
execution, ChatGPT (OpenAI) for adversarial audit and kill
conditions, Gemini (Google) for engineering formalization, and
Grok (xAI) for anomaly detection. Each AI was given a different
role and different information. The theoretical direction and all
original concepts were provided by the sole human author. This
methodology — using AI systems as probes with different sampling
functions directed by a human controller — is itself a
contribution to the practice of computational physics research.

### 6.4 Reproducibility

All code is open source (GitHub: Joy4joy4all/Burdick-Crag-Mass).
All results are published on Zenodo with timestamped JSON
evidence across 24 versions (base DOI: 10.5281/zenodo.19251192).
Every covariance requirement was evaluated and documented. The
framework is fully reproducible.

### 6.5 Einstein Coupling and Null Pump (v23)

The substrate stress-energy tensor T_μν was derived explicitly
from the physical velocity excess via compare_rotation(). The
Newtonian limit holds for 4/5 galaxies (M_sub from 9.27×10⁷
to 1.26×10¹² M☉). Conservation ∇_μ T^μν at machine precision
(10⁻²⁰) for all 5. NGC3953 (Class VI barred) fails the
Newtonian limit — Newton already wins. This failure is the
covariance requirement: the gate must be able to say NO.

The null pump test (J=0) proved substrate collapse: σ → 0.000000
in all 5 galaxies. Rotation fits degrade by +129 to +188 km/s.
PUMP ESSENTIAL: 5/5. The substrate is a funded state.

### 6.6 Boundary Dynamics and σ_crit Discovery (v24)

Three substrate perturbation regimes were identified using
synthetic binary source fields:

Diffusive Healing: stochastic perforation of J (±40% noise)
heals completely (coherence 0.99987). The solver self-averages
neutrino injection noise.

Coherence Failure: baryonic density noise degrades coherence
to 0.742 at the binary throat. The mechanism is local
maintenance cost increase, not injection pattern disruption.

Boundary Nonlinear: perturbation at 80% r_max produces 38×
σ overshoot. The torus edge dissolves into bulk without a
nonlinear saturation term. A boundary stability sweep across
8 configurations showed that only a σ_crit clamp maintains
a stable thin edge. Dissipation alone is insufficient.
Injection is catastrophic.

The dimensionless control parameter Π = σ_edge/σ_crit governs
boundary stability. Alpha Centauri (Π << 1): stable at all
approach angles. HR 1099 (Π > 1): requires active clamping.
The safe arrival corridor is defined by min(|∇σ|) — minimum
gradient magnitude, not absolute σ level.

This identifies a nonlinear saturation mechanism as a required
component of the substrate field equation at boundaries.
Whether σ_crit derives from system parameters (separation,
pump ratio, λ) or must be independently measured is the
subject of ongoing work.

---

## 7. Conclusions

The Burdick Crag Mass framework demonstrates that galactic
rotation curves can be reproduced without dark matter or modified
gravity by treating the gravitational signal as a substrate
maintenance cost. On the complete 175-galaxy SPARC sample, BCM
with four frozen global constants plus one amplitude coefficient
per galaxy beats Newtonian baryonic fits on 130 of 175 galaxies
(74.3%) and beats MOND on 172 of 175 (98.3%), achieving a mean
reduced chi-squared of 63.1 compared to Newton's 157.6 and
MOND's 1122.6. An ablation study confirms the per-galaxy amplitude
carries real physical information: a single global amplitude fit
performs 13.8x worse, and an unscaled fit fails catastrophically.
The six-class taxonomy emerging from the framework classifies
galaxies into physically distinct substrate interaction states
that are stable under parameter perturbation.

The Tully-Fisher exponent on the full sample is alpha = 3.42
(95% CI [3.03, 3.88]), consistent with classical baryonic TF.
Bracket-stratified bootstrap reveals substantial scale-dependence
across the framework: the TF relation holds (within classical
range) in the ensemble but breaks down at the massive velocity
bracket (alpha = -0.29, 95% CI fully below classical). This
empirical observation points toward a scale-dependent transition
in the substrate coupling that warrants theoretical extension.
Binary stellar dynamics on three systems reproduce observed
mass transfer behavior.

The null pump test (v23) proved the substrate is a funded state:
σ → 0 without SMBH injection. The Einstein coupling derives
T_μν at machine-precision conservation with substrate enclosed
masses spanning five orders of magnitude.

The boundary dynamics tests (v24) identified three distinct
perturbation regimes and discovered that a nonlinear saturation
limit (σ_crit) is required for stable boundary formation. This
provides a falsifiable prediction: the torus edge of any galaxy
should exhibit a measurable σ_crit that correlates with system
parameters.

A theoretical extension of the framework addressing the
scale-dependent substrate coupling observed in the Tully-Fisher
bracket analysis is under development and will be presented in
a companion paper. Paper A's claims do not depend on that
extension.

**v7 additions (Anchor Partition Regime Map).** The v7 additions
establish that the scale-dependent behavior observed in the TF
bracket analysis corresponds to an identifiable structure in the
observational data itself. The six-regime APR map shows:
(1) substrate coupling peaks at 50-150 km/s where BCM wins most;
(2) APR drops sharply at 125 km/s, aligning with the TF exponent peak;
(3) ROOT_REENTRY galaxies (v_max > 300 km/s) carry real substrate
signal in their outer disks but the current solver architecture lacks
the appropriate operator. The Macro-Torsion operator proposed in
Section 3.9 provides a regime-safe directional extension; its
integration into the solver and physical calibration are reserved for
a future version. The ROOT_REENTRY finding generates a specific
falsifiable prediction: the six galaxies in that regime should show
outer-disk rotation residuals consistent with differential rotation
shear coupling when observed at sufficient spatial resolution.

The framework generates multiple falsifiable predictions testable
with existing observational data and a $225 benchtop device.

Whether or not the substrate model ultimately describes physical
reality, the computational methodology — adversarial multi-AI
collaboration with full reproducibility — provides a template
for future theoretical physics research.

Space is not a container. Space is a maintenance cost.

---

## Acknowledgments

All theoretical concepts originated with Stephen Justin Burdick
Sr. Code execution: Claude (Anthropic). Adversarial computation:
ChatGPT (OpenAI). Engineering formalization: Gemini (Google).
Anomaly detection: Grok (xAI). Named in honor of Bruce Burdick
(Brucetron discovery). The SPARC dataset was provided by Lelli,
McGaugh, and Schombert. THINGS VLA HI data from Walter et al.
GW150914 waveform template from LIGO Open Science Center.

---

## References

Abbott, B. P. et al. 2016, PRL, 116, 061102 (GW150914)
Bekenstein, J. D. 2004, Phys. Rev. D, 70, 083509
Bosma, A. 1981, AJ, 86, 1825
Boylan-Kolchin, M. et al. 2011, MNRAS, 415, L40
de Blok, W. J. G. 2010, Adv. Astron., 2010, 789293
Donati, J.-F. et al. 1999, MNRAS, 302, 457
Fekel, F. C. 1983, ApJ, 268, 274
Goodman, J. & Ji, H. 2002, JFM, 462, 365
Klypin, A. et al. 1999, ApJ, 522, 82
Kormendy, J. & Ho, L. C. 2013, ARA&A, 51, 511
Lelli, F., McGaugh, S. S., & Schombert, J. M. 2016, AJ, 152, 157
Milgrom, M. 1983, ApJ, 270, 365
Montarges, M. et al. 2021, Nature, 594, 365
Navarro, J. F., Frenk, C. S., & White, S. D. M. 1996, ApJ, 462, 563
Rubin, V. C. & Ford, W. K. 1970, ApJ, 159, 379
Shaposhnikov, N. & Titarchuk, L. 2009, ApJ, 699, 453
Tremaine, S. et al. 2002, ApJ, 574, 740
Tully, R. B. & Fisher, J. R. 1977, A&A, 54, 661
Walter, F. et al. 2008, AJ, 136, 2563
Einstein, A. 1915, Sitzungsberichte der Königlich Preußischen Akademie der Wissenschaften — General relativity field equations
Schneider, P., Ehlers, J., & Falco, E. E. 1992, Gravitational Lenses — Einstein radius derivation

---

*Stephen Justin Burdick Sr. — Emerald Entities LLC*
*GIBUSH Systems — 2026*
*All code and data: https://github.com/Joy4joy4all/Burdick-Crag-Mass*
*Zenodo v6: 10.5281/zenodo.19680280 | Base: 10.5281/zenodo.19251192*
