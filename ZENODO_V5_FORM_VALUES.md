# ZENODO v5 — FORM VALUES (copy-paste ready)
# Stephen Justin Burdick Sr. — Emerald Entities LLC
# 2026-03-31

---

## TITLE
Burdick's Crag Mass v5: Substrate Exchange Mechanics — Settle Factor, Coupling Efficiency, and Falsifiable Device Specification for a $225 Benchtop Test

---

## RESOURCE TYPE
Publication / Preprint

---

## PUBLICATION DATE
2026-03-31

---

## AUTHORS/CREATORS
Burdick, Stephen Justin Senior (Emerald Entities LLC)

---

## DESCRIPTION
(paste everything below into Description field — includes v1-v4 history then v5 new)

We present the Burdick Crag Mass (BCM) framework — a substrate wave model driven by supermassive black hole neutrino flux that classifies SPARC galaxies into three distinct substrate interaction states without dark matter. Using the 175-galaxy SPARC rotation curve dataset (Lelli et al. 2016), we identify a stable tripartite classification: Class I (Transport-Dominated, 9/31 massive bracket), Class II (Residual/Hysteresis, 7/31), and Class III (Ground State, 15/31). This classification remains stable under parameter perturbation, indicating a physical boundary in galactic substrate topology rather than a model artifact. The dark matter signal is reinterpreted as the neutrino maintenance budget of the spatial substrate, funded continuously by the central SMBH. A testable prediction is provided for IceCube/KM3NeT neutrino flavor ratio measurements at galactic edges.

Version 1.2 adds: The BCM Structural Override System (Classes IV-VI), extending the original three-class topology to six physically distinct substrate interaction states. New classes confirmed: Class IV (Declining Substrate — outer rim depletion), Class V-A (Ram Pressure — asymmetric lambda field), Class V-B (Substrate Theft — multi-body SMBH competition), Class VI (Barred Substrate Pipe — bar-channeled flux). Validation runs on three galaxies with the override system confirmed: NGC3953 Class VI delta flipped from -31.3 to +11.1 km/s (substrate wins) via bar dipole geometry and LINER throttle; NGC7793 Class V-B flipped to substrate win (+2.2 km/s) via 2D HI Moment-0 morphology and void depletion; NGC2841 Class I control stable at +28.4 km/s. Environmental depletion suppression gate confirmed for NGC2976 (substrate vacuum, Newton RMS 3.7 km/s). 2D HI Moment-0 ingestion live for three THINGS galaxies. BCM_Substrate_overrides.py and Genesis Renderer visualization methodology included. No per-object tuning parameters maintained throughout.

Version 2.1 adds: Complete solar system planetary substrate solver (all 8 planets). Resonance Hamiltonian H(m) = (c_s - Omega*R/m)^2 confirmed for Earth (m=1), Jupiter (m=1), Saturn (m=6), Uranus (m=2), Neptune (m=2). Mercury m=1 prediction documented for BepiColombo magnetometer target. Gap 7 (Uranus-Neptune Twin Paradox) identified and quantified — Lambda regime classifier implemented. Mixing Length Theory convective velocity added to all planetary parameters. Diamond rain convective pump identified as Uranus substrate mechanism. Full codebase open source: https://github.com/Joy4joy4all/Burdick-Crag-Mass

Version 3.0 adds: Phase diagnostic framework with cos_delta_phi (phase alignment between substrate memory field and forcing field) and decoupling_ratio (amplitude separation between observable and substrate). These two orthogonal axes distinguish coupled regimes (Class I, cos_delta_phi ~ 1.0) from energy-depleted phase-locked states (Class V-B, phase coherent but structurally empty). Resolution mode boundary discovery: NGC2841 Class I resolution sweep (128/256/512 grid) reveals peak substrate expression at 256 grid; at 512, finer modes fragment the inner field — the mode boundary is itself a physical finding. Neptune/Uranus Q6/Q7 prime mode stability hypothesis: Neptune Q=6 (composite, energy radiates outward, explaining 2.6x excess heat) versus Uranus Q=7 (prime, irreducible, energy contained internally, explaining thermal silence despite stronger B-field). Data-driven lambda: outer_slope computed from rotation curve outer 20%, replacing fixed lambda=0.1 with a physically motivated per-galaxy coupling that preserves the no per-object tuning principle. NGC0801 Class IV outer_winner divergence identified. Language precision: "No per-object tuning parameters" replaces "Zero free parameters" throughout — the global parameters (lambda=0.1 baseline, kappa=2.0, grid=256, layers=8) are universal, no per-galaxy tuning occurs.

Version 4.0 adds: Stellar tachocline extension with resonance Hamiltonian correction, 13-star combined arms registry, tachocline gate discovery, and publication-quality figures. The resonance Hamiltonian achieves 9/10 eigenmode matches across 13 stars spanning all six BCM galactic classes. Tachocline gate confirmed: fully convective stars lock to m=1 (3/3). EV Lacertae mode boundary at conv_depth=0.9. Betelgeuse m=3 confirmed as wave-to-convection transition. Scale invariance: lambda_stellar/lambda_galactic = 0.977.

Version 5.0 adds: Theoretical framework for substrate exchange mechanics, moving BCM from empirical classification ("what") to mechanical definition ("how"). This version contains no new code or data — it is the theoretical extension implied by v1-v4 results, peer-reviewed across three independent AI engines (Claude, ChatGPT, Gemini).

SUBSTRATE PRIMITIVES: Mass reinterpreted as x-bar (mean resonance state) in the 2D substrate. What 3D observers measure as mass is the integrated mean of all coupled mode patterns projected into observable space. Rate of exchange R_ex = 1/m derived from the resonance Hamiltonian — higher modes exchange slower, m=1 is the broadband default. Opportunistic value set V_opp = {m : H(m) < threshold} defines which modes the substrate permits at any gate.

SETTLE FACTOR AND RE-EMERGENCE: N_settle = R/delta_r, where delta_r is the local coherence length (smallest unit of 3D material capable of holding the substrate write instruction). The grid 256 finding from v3 is reinterpreted as N_settle for galactic scale. Re-emergence follows a field propagation sequence: seed, field propagation, grid convergence, material draw, settle. The substrate does not create mass — it organizes existing 3D field energy according to the mode blueprint.

CONSERVATION OF COHERENCE: The substrate conserves phase-amplitude density, not mass. Expressing a pattern at Gate B requires phase-drain from Gate A — the source amplitude collapses to ground state. No duplication. The substrate is a single-user bus per tethered pattern.

COUPLING EFFICIENCY: eta = c_s/v_medium. eta > 1: substrate-dominated (Class I). eta ~ 1: coupled boundary (Class II). eta < 1: medium-dominated (Classes III-IV). This maps directly to BCM galactic classification and explains why the six classes work without dark matter — they describe coupling regimes, not mass distributions.

BETELGEUSE t_settle CALCULATION: Coupling efficiency eta = 0.98% (convection 102x faster than substrate phase speed). Great Dimming recovery (~180 days) tracks convective overturn time (~41 days per cell). Post-event irregularity (~2 years) tracks substrate settle clock. Prediction: fully stable m=3 pattern returns circa 2030-2031 (~11.5 years post-event = one substrate node settle time).

NEUTRINO FLAVOR GRADIENT PIPELINE: Target Class IV galaxies for maximum substrate transition contrast. Stack IceCube/KM3NeT events by angular distance from galaxy center. Compare inner (coupled) vs outer (decoupled) flavor ratios. Null test on Class I galaxies. Uses existing public data — no new observations required.

SUBSTRATE MODE SELECTION DEVICE (SMSD): $225 benchtop falsification test. Modified Taylor-Couette cell with galinstan (room-temperature liquid metal) in external magnetic field. Three configurations: Config B (solid body rotation, no tachocline — BCM predicts m=1 lock), Config A (differential rotation — BCM predicts discrete mode staircase m = round(Omega*R/c_s)), Config C (variable gap width — EV Lac boundary analog). Full bill of materials, engineering challenges addressed (Rm ~ 0.3, sensor sensitivity, oxide skin, vibration artifacts, hydrodynamic contamination), and clean falsification criteria documented.

RESEARCH LANDSCAPE: Five fields eliminated if BCM holds (WIMP/axion detection, NFW halo fitting, MOND variants, Lambda-CDM dark matter component, random instability stellar eruption models). Six fields opened (substrate field measurement, neutrino flavor gradient astronomy, tachocline gate biology, prime mode stability engineering, substrate exchange rate measurement, settle factor engineering).

Full codebase open source: https://github.com/Joy4joy4all/Burdick-Crag-Mass

---

## LICENSE
Creative Commons Attribution Non Commercial No Derivatives 4.0 International

---

## KEYWORDS
(add each as separate keyword)
dark matter alternative
substrate wave model
substrate exchange mechanics
settle factor
coupling efficiency
resonance Hamiltonian
tachocline gate
scale invariance
Taylor-Couette MHD
falsifiable device specification
neutrino flavor gradient
galactic rotation curves
SPARC dataset
combined arms
phase dynamics
conservation of coherence

---

## VERSION
5.0

---

## PUBLISHER
Emerald Entities LLC

---

## DATES
Date: 2026-03-31
Type: Created

---

## DEVELOPMENT STATUS
Active

---

## PROGRAMMING LANGUAGE
Python

---

## REPOSITORY URL
https://github.com/Joy4joy4all/Burdick-Crag-Mass

---

## RELATED WORKS
Relation: Is new version of
Identifier: (use the v4 DOI once published — check your Zenodo dashboard)
Scheme: DOI
Resource type: Publication / Preprint

---

## REFERENCES
Lelli, F., McGaugh, S. S., & Schombert, J. M. 2016, AJ, 152, 157 — SPARC rotation curve dataset
Auriere, M., et al. 2010, A&A, 516, L2 — Betelgeuse magnetic field detection
Morin, J., et al. 2008, MNRAS, 390, 567 — M dwarf magnetic topologies (EV Lac, V374 Peg)
Goodman, J. & Ji, H. 2002, JFM, 462, 365 — Princeton MRI experiment (Rm precedent)
Montarges, M., et al. 2021, Nature, 594, 365 — Betelgeuse Great Dimming surface mass ejection
Donati, J.-F. & Landstreet, J. D. 2009, ARA&A, 47, 333 — Stellar magnetic fields review

---

## FILES TO UPLOAD
- BCM_V5_THEORETICAL_FRAMEWORK.md
- BCM_V5_DEVICE_SPEC.md
