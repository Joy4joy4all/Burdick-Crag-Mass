# Burdick Crag Mass: A Substrate Wave Model for Galactic Rotation Curves Without Dark Matter

**Stephen Justin Burdick Sr.**
Emerald Entities LLC — GIBUSH Systems, Calais, Maine, USA

**Correspondence:** GitHub: Joy4joy4all/Burdick-Crag-Mass
**DOI (preprint series):** 10.5281/zenodo.19251192

---

## Abstract

We present the Burdick Crag Mass (BCM) framework, a substrate-based
alternative to cold dark matter in which the dark matter signal is
reinterpreted as the neutrino maintenance budget of a pre-existing 2D
spatial substrate. The substrate becomes detectable only when
continuously agitated by wave energy from supermassive black hole
neutrino flux; gravity emerges as the cumulative memory of substrate
agitation. Using four global parameters (lambda=0.1, kappa=2.0,
grid=256, layers=8) and no per-galaxy tuning, we classify 175 SPARC
rotation curve galaxies (Lelli et al. 2016) into six physically
distinct substrate interaction states. The classification is stable
under parameter perturbation, indicating physical boundaries in
galactic substrate topology rather than model artifacts. We extend
the framework to binary stellar dynamics across three systems (Alpha
Centauri, HR 1099, Spica) and reproduce the structural phases of the
GW150914 binary black hole merger. The framework generates falsifiable
predictions for IceCube/KM3NeT neutrino flavor ratio gradients at
galactic edges, Betelgeuse m=3 tachocline recovery (circa 2030-2031),
and binary mass transfer rates in synchronized vs unsynchronized
systems. All code, data, and timestamped results are publicly
available across 21 versioned Zenodo publications with full
adversarial audit records from four independent AI systems.

**Keywords:** dark matter alternative, rotation curves, SPARC,
substrate wave model, neutrino flux, galactic classification,
binary dynamics, phase coherence

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
maintenance cost. Space is not a container; space is a maintenance
cost. A pre-existing 2D substrate medium becomes detectable only when
continuously agitated by wave energy, analogous to how a vibrating
drumhead reveals its geometry through standing wave patterns. The
funding source is the supermassive black hole at the galactic center,
continuously injecting energy into the substrate via neutrino flux.
Where the funding stops, the substrate decays and the gravitational
signal disappears — producing the rotation curve profiles attributed
to dark matter halos.

This paper presents the mathematical framework (Section 2), the
175-galaxy SPARC validation producing six substrate interaction classes
(Section 3), binary stellar dynamics on three systems (Section 4),
falsifiable predictions (Section 5), and discussion of limitations
and future work (Section 6).

---

## 2. The Substrate Model

### 2.1 Wave Equation

The substrate field sigma evolves on a 2D grid according to:

    d_sigma/dt = D * laplacian(sigma) - lambda * sigma
                 + S(x,t) + alpha * (sigma - sigma_prev)

where sigma is the substrate memory field (cumulative agitation),
D is the diffusion coefficient, lambda is the decay rate (the
maintenance cost — higher lambda means faster decay without
continuous funding), S(x,t) is the SMBH neutrino flux injection
source, and alpha = 0.80 is the memory coefficient governing how
much substrate state persists between timesteps.

The memory term alpha*(sigma - sigma_prev) is critical: it provides
the substrate with history-dependent behavior. At alpha = 0.80 the
system operates in a stable regime; a sharp bifurcation occurs at
alpha = 0.90 (v14 Lagrange equilibrium scan), establishing the
operating window at 0.75 to 0.85.

### 2.2 Crag Mass Injection

The SMBH source term uses Bessel function modes:

    J_crag = kappa_BH * (M_BH / M_ref) * Bessel(m, r)

where kappa_BH = 2.0 is frozen globally (never tuned per galaxy)
and the Bessel mode m is selected by the tachocline gate. This
produces concentric ring patterns in the substrate field that map
to the observed rotation curve structure.

### 2.3 Rotation Curve Comparison

The substrate-modified circular velocity is:

    v_sub(r) = sqrt(G * M(r)/r + kappa * sigma(r))

where M(r) is the baryonic mass from SPARC Rotmod files (decomposed
into gas, disk, and bulge components per Lelli et al. 2016) and
sigma(r) is the azimuthally averaged substrate memory field at
radius r. The substrate contribution kappa*sigma(r) replaces the
NFW dark matter halo term.

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

---

## 3. SPARC Rotation Curve Classification

### 3.1 Dataset

We use the complete 175-galaxy SPARC dataset (Lelli et al. 2016),
which provides observed rotation curves and baryonic mass models
(gas + disk + bulge) for late-type galaxies spanning four velocity
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
emerges, consistent with SMBH cavitation blowback scrambling
inner substrate phase while the outer torus stabilizes (v6).

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
describes coupling regimes, not mass distributions — explaining
why six classes work without dark matter.

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

### 5.1 Neutrino Flavor Gradient

BCM predicts a measurable neutrino flavor ratio shift between
inner (substrate-coupled) and outer (decoupled) regions of
Class IV galaxies. Testable with existing IceCube/KM3NeT public
data by stacking events by angular distance from galaxy center.
Null test: Class I galaxies should show no gradient.

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

### 5.5 Benchtop Falsification

The Substrate Mode Selection Device (SMSD): a $225 modified
Taylor-Couette cell with galinstan (room-temperature liquid
metal) in an external magnetic field. Three configurations test
discrete mode staircase vs m=1 lock vs boundary analog. Full
bill of materials and falsification criteria documented in v5.

---

## 6. Discussion

### 6.1 Comparison to Existing Approaches

BCM differs from both dark matter and modified gravity in its
ontological claim: the gravitational signal attributed to dark
matter is the maintenance cost of spatial substrate, not missing
mass or modified force law. The six-class taxonomy provides a
physical classification scheme that neither NFW halo fitting
(which requires per-galaxy parameters) nor MOND (which provides
a universal acceleration scale but no classification) offers.

### 6.2 Limitations

The framework has not been tested against gravitational lensing
observations, CMB power spectrum constraints, or Bullet Cluster
dynamics — all areas where Lambda-CDM performs well. The physical
mechanism for lambda modulation (what tunes the substrate decay
rate) remains unresolved.

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
evidence across 21 versions (base DOI: 10.5281/zenodo.19251192).
Every adversarial test designed by the AI systems was run, and
every kill condition was evaluated and documented. The framework
is fully reproducible.

---

## 7. Conclusions

The Burdick Crag Mass framework demonstrates that galactic
rotation curves can be reproduced without dark matter or modified
gravity by treating the gravitational signal as a substrate
maintenance cost funded by SMBH neutrino flux. The six-class
taxonomy emerging from four global parameters classifies 175
SPARC galaxies into physically distinct substrate interaction
states. Binary stellar dynamics on three systems reproduce
observed mass transfer behavior. The framework generates
multiple falsifiable predictions testable with existing
observational data and a $225 benchtop device.

Whether or not the substrate model ultimately describes physical
reality, the computational methodology — adversarial multi-AI
collaboration with full reproducibility — provides a template
for future theoretical physics research.

Space is not a container. Space is a maintenance cost.

---

## Acknowledgments

All theoretical concepts originated with Stephen Justin Burdick
Sr. Code execution: Claude (Anthropic). Adversarial audit:
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
Lelli, F., McGaugh, S. S., & Schombert, J. M. 2016, AJ, 152, 157
Milgrom, M. 1983, ApJ, 270, 365
Montarges, M. et al. 2021, Nature, 594, 365
Rubin, V. C. & Ford, W. K. 1970, ApJ, 159, 379
Shaposhnikov, N. & Titarchuk, L. 2009, ApJ, 699, 453
Walter, F. et al. 2008, AJ, 136, 2563

---

*Stephen Justin Burdick Sr. — Emerald Entities LLC*
*GIBUSH Systems — 2026*
*All code and data: https://github.com/Joy4joy4all/Burdick-Crag-Mass*
*Zenodo: 10.5281/zenodo.19251192*
