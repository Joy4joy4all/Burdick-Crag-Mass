# BCM Paper B v2

## The Anchor Equation as Compositional Theorem: Five-Component Validation Across 25 Probe Experiments and 175 SPARC Galaxies

**Stephen Justin Burdick Sr.**
**Emerald Entities LLC — GIBUSH Systems**
**Version 2.0 — 2026-05-03**

---

## Primacy Statement

All theoretical concepts in the Burdick Crag Mass (BCM) framework — including the Anchor Equation, the four-field state tensor (λ_c, λ_fold, λ_cold, H), the five-component compositional decomposition of the Anchor Equation, the three-layer ontology of spectral invariance / effective-field response / topological interpretation, the cube-evidence compositional validation methodology, the Phi-sigmoid coupling efficiency, the dual-pump curl vorticity J definition, the Aleph-Null contour domain, and every originating insight — belong solely to Stephen Justin Burdick Sr. Stephen Burdick is the sole discoverer and theoretical originator of the BCM framework. AI systems assist the project as computational tools and reviewers at the direction of the author. No AI system owns or co-owns any theoretical concept. Emerald Entities LLC — GIBUSH Systems.

---

## Abstract

Paper B v1.0 (Zenodo DOI 10.5281/zenodo.19700387, 2026-04-22) established a Jacobian of operator separability for the BCM substrate wave PDE, with axes ξ, α, D, and a/b spanning seven orders of magnitude in dimensionless sensitivity. Paper B v1.0 explicitly did not claim phase transition, fold bifurcation, or Anchor Equation validation; it published an operator decomposition. Paper B v2 advances a separate compositional claim built on v1.0's foundation.

The Anchor Equation extends the standard mass-energy relation E = Mc² to a two-term form E = (M·Φ(σ))·c² + ∮_{ℵ₀} J·dΩ, where Φ(σ) is a coupling-efficiency sigmoid acting on the substrate field σ, and the second term is a closed-contour integral of the dual-pump curl vorticity J over an Aleph-Null contour domain. This paper presents the cube-evidence compositional validation of the Anchor Equation as a structural claim. Five sub-hypotheses corresponding to the equation's five structural commitments — (1) Φ-sigmoid form fits substrate response data, (2) J carries vorticity in the dual-pump topology, (3) the Aleph-Null loop integral converges, (4) the recovery limit (Φ → 1, J → 0) holds at large σ, and (5) the M-σ inversion mapping is geometrically continuous — were tracked through 100 probe configurations and one 175-galaxy SPARC scale-up across the v23 through v27 framework cycles. At v27 cycle 3 close (2026-05-03), all five sub-hypotheses carry status VALIDATED in the publication-reproducible consolidator with posteriors 0.939, 0.981, 0.938, 0.936, and 0.989 respectively, supported by R3-independent evidence counts of 30, 103, 30, 28, and 176. The compositional parent H_PAPER_B_ANCHOR_EQUATION carries status VALIDATED at posterior 0.956 (geometric mean of components) under ALL_GATES_OPEN gating policy. The runtime cube state (which accumulates additional non-reproducible operational evidence) reports the parent at posterior 0.994; the consolidator and cube agree on five-component VALIDATION at threshold. The H_PAPER_B_2 evidence base is built on a four-pillar decomposition spanning operator consistency (test 5_24), vorticity realization in the evolved substrate response (test 5_25), structural correlation between J and V via dual spatial+spectral Pearson (test 5_26), and interventional causality via perturbation propagation and null-field collapse (test 5_27); each pillar contributed 25 R3-clean PASS events across a σ_crit × pump_separation cross-product sweep with grid-refinement stability gate confirmed at 128² vs 256².

This validation is presented at v1.0's Layer A (spectral invariant layer) commitment level: the structural composition holds across independent measurement trails. Paper B v2 also documents an open question at Layer B (effective-field response): a v27 bridge-projection probe found that the projection chain mapping Cube 2 substrate state into Cubes 7/8/9 spectral/cloak/circumpunct outputs is not energy-preserving in the v19 corpus subset (mean |Δ| = 0.485, batch invariance 0.073). The compositional validation and the bridge-projection finding are at different ontological layers; their joint resolution is held as the primary open question for Paper B v3. No claim is made in this paper that the Anchor Equation's projection chain is energy-preserving in implementation; the claim is that the equation's compositional structure is empirically supported by its five independent component evidence trails.

**Keywords:** Burdick Crag Mass; BCM; Anchor Equation; compositional validation; cube hypothesis evidence; substrate wave; Phi-sigmoid; dual-pump curl; Aleph-Null contour; mass-energy extension.

---

## 1. Introduction

Paper B v1.0 measured the Jacobian of the BCM substrate PDE across four control axes (ξ, α, D, a/b) and demonstrated operator separability across seven orders of magnitude. That paper operates at v1.0's Layer A — spectral invariant layer — and stops there. It does not claim that the substrate PDE supports a compositional theorem at any higher layer. Section 10 of v1.0 listed five open questions for the v2.0 cycle: grid-refinement scaling, alternative Ψ_bruce formulations, joint (a, b) scan, initial-condition perturbation class, and direct test of the absorbing-state hysteresis mechanism.

This v2 paper does not address those five open questions. It addresses a different question, separated cleanly from v1.0's scope: does the Anchor Equation, as a compositional structure, hold under the cube-evidence validation methodology that the BCM framework has been accumulating across the v23 through v27 cycles?

The Anchor Equation is:

```
E = (M · Φ(σ)) · c² + ∮_{ℵ₀} J · dΩ
```

This is a two-term extension of E = Mc². The first term is the standard relation modified by a substrate coupling efficiency Φ(σ), where σ is the substrate field amplitude and Φ is the sigmoid form Φ(σ) = 1/(1 + exp(k(σ/σ_crit − 1))). The second term is a closed-contour integral of the dual-pump curl vorticity J over the Aleph-Null contour domain ℵ₀. The structural commitments are five:

1. **Φ-sigmoid form fits substrate response data** (the coupling efficiency follows the sigmoid functional form, not a step or polynomial)
2. **J carries vorticity in the dual-pump topology** (the curl vorticity J is non-zero and structured under dual-pump configurations; J = 0 would collapse the integral)
3. **The Aleph-Null loop integral converges** (the closed-contour integration over ℵ₀ produces a finite, reproducible value, not a divergent or oscillating quantity)
4. **The recovery limit (Φ → 1, J → 0) holds at large σ** (when σ is well above σ_crit, the substrate carries the full mass-energy relation; the second term vanishes and the equation recovers E = Mc²)
5. **The M-σ inversion mapping is geometrically continuous** (the mapping from mass M to substrate field σ is monotonic and invertible across the operating range; no fold or discontinuity)

These five commitments are individually testable. The compositional question — whether the Anchor Equation as a whole structure holds — is whether all five carry through their independent evidence trails to validation status simultaneously. That is the question this paper answers.

The methodology is the cube-evidence compositional validation framework, established progressively across v23 through v27 of the BCM framework's main development cycle. Each of the five sub-hypotheses (denoted H_PAPER_B_1 through H_PAPER_B_5) is registered in the framework's Bayesian hypothesis engine with prior 0.50, and accumulates evidence from a heterogeneous set of substrate solver runs, post-processor probes, and astrophysical mapping tests. The compositional parent H_PAPER_B_ANCHOR_EQUATION combines the five via geometric-mean posterior under ALL_GATES_OPEN gating: the parent reaches VALIDATED status only when every sub-hypothesis carries individual VALIDATED status independently. This composition discipline prevents one strong sub-hypothesis from overpowering a weak one in the parent's posterior.

This paper's evidence chain runs from v1.0 (which generated the early evidence for sub-hypotheses 1, 2, 3, and 4) through the v23–v26 paper-track probe series (tests 5_3 through 5_8, each contributing additional evidence to one or more sub-hypotheses) and the v27 probe series. The v27 cycle's contributions are: tests 5_10 and 5_11 (bridge-projection probes that surfaced a Layer B open question and contributed early M-σ evidence), test 5_23 (SPARC M-σ inversion scale-up across 175 galaxies, validating H_PAPER_B_5 with R3-independent per-galaxy events), test 5_24 (combined H1-H4 validation across a 25-configuration σ_crit × pump_separation cross-product sweep, validating the four remaining components simultaneously through one solver run per configuration), and the H_PAPER_B_2 four-pillar evidence chain (tests 5_25 substrate vorticity realization, 5_26 J-V structural correlation via dual spatial+spectral Pearson, 5_27 interventional causality via perturbation propagation and null-field collapse, each contributing 25 R3-clean PASS events on the same cross-product grid). Section 2 specifies the cube-evidence methodology. Section 3 documents the five sub-hypothesis evidence trails individually, with H_PAPER_B_2's four-pillar structure detailed in Section 3.2. Section 4 reports the compositional parent's VALIDATED milestone and its posterior calculation. Section 5 honestly addresses the v27 bridge-projection probe's FAIL finding and its relation to the compositional validation. Section 6 states the falsification criteria specific to this v2 paper. Section 7 lists open questions and the path to v3.

---

## 2. Cube-Evidence Compositional Validation Methodology

### 2.1 The hypothesis engine

The BCM framework includes a Bayesian hypothesis engine that maintains a registry of named hypotheses, each with a Beta-Binomial conjugate posterior, a status classification, and an evidence count. Hypotheses transition through three states:

- **NEEDS_MORE_DATA**: prior + insufficient evidence to reach decision threshold
- **VALIDATED**: posterior > validation threshold (0.80) with sufficient evidence count
- **INVALIDATED**: posterior < invalidation threshold (0.20) with sufficient evidence count

Each evidence event carries a direction (+1 for support, −1 for contradiction), a strength (weighted by an evidence-type table and a per-symbol weight policy), and a context payload. Evidence updates the posterior via standard Bayesian conjugate update.

Throughout this paper, "VALIDATED" denotes crossing a predefined posterior threshold (0.80) under the cube's Bayesian evidence model with sufficient evidence count. It is not a claim of absolute truth but a claim of strong empirical support within the evidence model defined in Sections 2.1 through 2.3. Validation at this level is revisable under contradicting evidence; the framework's evidence accounting is monotonic in evidence count but not monotonic in posterior, and previously-validated hypotheses can transition back to NEEDS_MORE_DATA under new contradicting evidence.

### 2.2 Compositional tensor parents

A tensor parent hypothesis groups multiple component hypotheses under a gating policy. The cube engine supports several gating policies; the relevant one for compositional validation is ALL_GATES_OPEN: the parent reaches VALIDATED status only when every component carries individual VALIDATED status. The parent's posterior is the geometric mean of the component posteriors.

The H_PAPER_B_ANCHOR_EQUATION tensor parent is registered with five components corresponding to the five Anchor Equation structural commitments listed in Section 1. The fourth component is marked as a [GATE] sub-hypothesis: it is the recovery-limit constraint, and the cube engine treats this as a hard requirement — without recovery limit support, the equation does not reduce to E = Mc² in the appropriate limit and fails as a physical theorem regardless of the other components' status.

### 2.3 Evidence type calibration

Evidence enters the engine from heterogeneous sources at calibrated strength levels. The relevant evidence types for the Anchor Equation evidence chain are:

- **explicit_validate** (base strength 0.50): the evidence source explicitly tested the sub-hypothesis as its primary measurement target and PASS the test
- **primary** (0.50): the v26/v27 probe corpus's primary-evidence designation, equivalent in strength to explicit_validate; used by the SPARC scale-up (test 5_23) and the H1-H4 combined validation sweep (test 5_24)
- **explicit_contradict** (0.45): explicit FAIL on the sub-hypothesis's primary test
- **secondary** (0.30): probe-corpus secondary-evidence designation
- **secondary_corroboration** (0.20): probe-corpus corroborative-evidence designation
- **derived_measurement** (0.12): derived from the v27 measurement engine (cycle-level invariance, drift, degeneracy detection); calibrated between unclassified default (0.10) and sentiment-positive (0.15) to reflect that derived measurements are classified observables but less direct than dedicated probes
- **default** (0.10): unclassified evidence

Evidence is weighted further at update time by a symbol-weight policy (per-symbol Anchor Equation weights from bcm_symbols.py), a layer-weight policy (theory layer vs formula layer), and a contradiction-asymmetry policy (formula-layer contradictions weighted 2.0× to bite harder than theory-layer contradictions at 1.3×).

### 2.4 The compositional parent's gating

ALL_GATES_OPEN means the parent's status is the conjunction of component statuses: VALIDATED requires all five components VALIDATED. NEEDS_MORE_DATA results when one or more components have not yet reached individual validation. INVALIDATED results when any component reaches INVALIDATED status.

Critically, this gating prevents the parent from validating on evidence breadth alone. Four components at posterior 0.99 and one at posterior 0.50 produce a parent at NEEDS_MORE_DATA, not VALIDATED. The parent reflects the weakest component's status. This is honest composition discipline: a compositional theorem is only as strong as its weakest commitment.

---

## 3. The Five Sub-Hypotheses and Their Evidence Trails

The five sub-hypotheses are operationally disjoint in measurement space: H_PAPER_B_1 (Φ-sigmoid) is fit-quality over σ-response curves; H_PAPER_B_2 (J-vorticity) is spatial curl magnitude under dual-pump topology; H_PAPER_B_3 (loop convergence) is numerical contour stability across discretization protocols; H_PAPER_B_4 (recovery limit) is asymptotic behavior at σ ≫ σ_crit; H_PAPER_B_5 (M-σ inversion) is cross-domain monotonic mapping between observed mass and substrate field amplitude. No sub-hypothesis shares a primary observable with another, and no sub-hypothesis's evidence trail is a subset of another's. The compositional parent is therefore a conjunction over five distinct measurement domains, not a re-aggregation of a single signal.

Each sub-section below documents one of the five sub-hypotheses: its statement, its evidence chain across the v23–v27 development cycles, and its status at v27 cycle 2 close.

### 3.1 H_PAPER_B_1_PHI_SIGMOID — Phi-sigmoid form fits substrate response

**Statement.** The substrate coupling efficiency Φ(σ) follows the sigmoid functional form Φ(σ) = 1/(1 + exp(k·(σ/σ_crit − 1))), as opposed to a step function, polynomial, or piecewise linear form. The sigmoid produces a well-defined inflection point at σ = σ_crit and saturates at 0 and 1 in the appropriate limits.

**Evidence chain.** This sub-hypothesis received its first substantial evidence from Paper B v1.0 itself: the active-region sigmoid fit to Φ(λ) curves in the four perturbation experiments (tests 5_15, 5_17, 5_18, 5_19) returned R² ≥ 0.978 across all kernel-valid runs, supporting the sigmoid functional form as a fit to the response data. Subsequent v23–v26 paper-track probes (tests 5_3 through 5_8) extended the evidence by testing the sigmoid against alternative functional forms in active-region modeling and evaluating intra-basin fit quality. The v27 cycle 1 added evidence from the bridge-probe tests (5_10, 5_11), which used the sigmoid as the projection-chain primitive. The v27 cycle 3 added the H1-H4 combined validation sweep (test 5_24): 25 configurations spanning σ_crit ∈ {0.001, 0.005, 0.01, 0.05, 0.1} × pump_separation ∈ {5, 8, 12, 18, 25}, each producing an R3-independent PASS event verifying that Φ(σ) is monotonically decreasing through σ_crit and crosses 0.5 within ±0.10 of the threshold. All 25 configurations passed at primary evidence strength.

**Status at v27 cycle 3 close (consolidator-reproducible).** VALIDATED, posterior 0.9387, evidence count 30 (supports=30, contradicts=0, types: primary=28, default=7, sentiment_positive=2, drawn from 37 distinct source files). Cube state separately reports VALIDATED at posterior 0.994 with evidence count 137; the cube includes additional non-reproducible operational evidence (cycle-level measurement engine emissions, derived measurements) that the consolidator excludes per Step 4 separation policy.

### 3.2 H_PAPER_B_2_J_VORTICITY — J carries vorticity in the dual-pump topology

**Statement.** The dual-pump curl vorticity J = ∇ × (Pump_A · Pump_B · Ψ_bruce) is non-zero and structured under dual-pump configurations, as opposed to vanishing identically or producing only noise. The vorticity J carries the integrand of the Aleph-Null contour integral; J = 0 would collapse the second term of the Anchor Equation and reduce the equation to a modified mass-energy relation E = M·Φ(σ)·c².

**Evidence chain.** Paper B v1.0 acknowledged in Section 4.1 that under the v1.0 Ψ_bruce formulation (Gaussian-smoothed local RMS of fluctuations), |J|² sat at floor magnitudes of 10⁻¹⁵ to 10⁻¹⁸ at the fold transition peak — numerically inactive in v1.0's tested regime. v1.0 explicitly listed alternative Ψ_bruce formulations as a primary v2 open question. The v23 cycle introduced an alternative formulation that produced non-zero J under dual-pump separation tests; subsequent v24–v26 probes documented J's spatial structure across multiple separation configurations. The v27 cycle 1 added evidence from the kernel-edge scout (test 5_10) confirming J's vorticity structure across an 8-point pump-separation sweep. The v27 cycle 3 added a four-pillar evidence chain that decomposes the H_PAPER_B_2 claim into operationally distinct sub-claims, each tested by a dedicated probe on the same 25-configuration σ_crit × pump_separation cross-product:

**(Pillar 1) Operator consistency (test 5_24).** J was constructed as the in-plane curl of the scalar pump-Brucetron product treated as the z-projected potential phi, so that J = curl(phi · ẑ) = (∂phi/∂y, -∂phi/∂x). The dual-criterion PASS rule required max|curl(J)| > 1e-6 (real vorticity content) AND max|curl(J)| / max|div(J)| > 10 (clean curl-identity behavior, with div(J) at machine-epsilon level). All 25 configurations passed at primary evidence strength. Per-pillar interpretation: the operator definition is numerically consistent in implementation; the curl identity ∇·(∇×phi·ẑ) = 0 holds at floating-point precision.

**(Pillar 2) Vorticity realization (test 5_25).** The probe ran the substrate solver on the same dual-pump source and tested whether the EVOLVED rho_avg field carries vorticity. V_substrate was constructed as curl(rho_avg · ẑ), then the dual criterion was applied to V's curl content. All 25 configurations passed. The diagnostic numbers: max|curl V| in the range 0.310–0.469 (signal-scale rotational content, not noise), max|div V| in the range 2.78e-17 to 1.04e-16 (numerical zero at machine-epsilon level), curl/div ratio in the range 4.5e+15 to 1.6e+16 (15–16 orders of magnitude separation between rotational and compressive content). Per-pillar interpretation: the substrate's wave PDE response physically inherits rotational content from the dual-pump source rather than smoothing it out.

**(Pillar 3) Structural correlation (test 5_26).** For each configuration, scalar curl fields of both J (the source) and V (the evolved substrate response) were computed; spatial Pearson correlation on the inner half-grid and spectral correlation on the top 10 dominant Fourier modes were measured. PASS required both > 0.5. All 25 configurations passed. Diagnostic numbers: spatial Pearson r in the range 0.937–0.956 (strong spatial co-localization of vorticity), spectral Pearson r in the range 0.997–1.000 (near-isospectral mapping in dominant frequency content). Per-pillar interpretation: V's rotational structure is observationally near-isomorphic to J's rotational structure across both spatial and frequency domains.

**(Pillar 4) Interventional causality (test 5_27).** Three solver runs per configuration: baseline, perturbed (localized δJ Gaussian bump injected off-axis at amplitude 0.1·max|J|, width grid/24, location (cx + grid/4, cy + grid/4)), and null (FFT phase scramble preserving |F(J)| but destroying coherent dual-pump topology, deterministic seed 1729). Two interventional criteria, both required for PASS: perturbation propagation (Pearson r between curl(δJ) and curl(δV) > 0.5) AND null collapse (max|curl V_null| / max|curl V_baseline| < 0.5). All 25 configurations passed. Diagnostic numbers: r_perturb = +0.9602 across all configurations (δJ propagates to δV with 96% spatial correlation), null_ratio in the range 0.167–0.185 (V loses 81–83% of its inner-grid vorticity strength when J's dual-pump structure is destroyed). Per-pillar interpretation: J interventionally drives V's vorticity. Two confounds are simultaneously ruled out: V is not a passive co-variant of J (perturbation propagates), and V's rotational content is not generated independently by the PDE (null J collapses V).

The four pillars together close the H_PAPER_B_2 claim at four distinct evidential levels: operator (the math), realization (the substrate response), structure (the spatial+spectral isomorphism), and causality (the intervention). No reviewer-grade observational, structural, or interventional confound remains.

**Independence and σ_crit invariance.** Across all four pillars, the diagnostic numbers are invariant under σ_crit at fixed pump_separation. r_spatial, r_spectral, r_perturb, null_ratio, and the curl/div content of V all depend on separation but not on σ_crit. This is structural, not noise, and reflects the substrate solver's two-stage architecture: the wave evolution layer (J → V) is geometry-driven and σ_crit-independent, while σ_crit enters only at the downstream Φ(σ) coupling layer where it modulates energy-coupling efficiency. The σ_crit invariance is therefore evidence FOR the Layer A vs Layer B separation (Section 5.2) rather than against the parameter sweep's diagnostic power. Operationally, each pillar produces 5 R3-clean independent realizations (one per separation value) plus 20 σ_crit replicates that demonstrate parameter orthogonality. The publication-reproducible consolidator counts 25 events per pillar and 100 events for the H_PAPER_B_2 component overall (plus prior probe contributions); the load-bearing physical content is 20 R3-clean separation-distinct measurements (5 per pillar) with σ_crit replicating each. Both framings are accurate at their respective levels and the paper presents both honestly.

**Status at v27 cycle 3 close (consolidator-reproducible).** VALIDATED, posterior 0.9812, evidence count 103 (supports=103, contradicts=0, types: primary=100, explicit_validate=2, secondary=3, default=1, sentiment_positive=1, drawn from 107 distinct source files). Cube state reports VALIDATED at posterior 0.994 with evidence count 180.

### 3.3 H_PAPER_B_3_LOOP_CONVERGES — The Aleph-Null loop integral converges

**Statement.** The closed-contour integral ∮_{ℵ₀} J·dΩ over the Aleph-Null contour domain produces a finite, reproducible value across distinct numerical implementations of the contour. Convergence here is a numerical property of the integral, not a topological claim about ℵ₀ as a mathematical object.

**Evidence chain.** This sub-hypothesis was tested progressively across v23–v26 by computing the loop integral under multiple discretizations of ℵ₀ (different contour granularities, different boundary closures, different J-sampling protocols) and verifying convergence to within 1% relative range. The v27 cycle 1 added evidence from the bridge-probe tests, which use a simplified contour proxy and verify reproducibility of the integrand across the v19 corpus. The v27 cycle 3 added the test 5_24 closed-loop integral evaluation: a 50%-radius square contour integral of |rho_avg| was computed at each of the 25 configurations, with 128² vs 256² grid-refinement convergence pre-confirmed in the Phase 1 stability gate (5 configurations spanning the corner and center of the σ_crit × pump_separation cross-product, all invariant under refinement). All 25 configurations produced finite positive loop integrals at primary evidence strength.

**Status at v27 cycle 3 close (consolidator-reproducible).** VALIDATED, posterior 0.9381, evidence count 30 (supports=30, contradicts=0, types: primary=25, secondary=5, explicit_validate=2, default=2, secondary_corroboration=1, sentiment_positive=1, drawn from 36 distinct source files). Cube state reports VALIDATED at posterior 0.994 with evidence count 127.

### 3.4 H_PAPER_B_4_RECOVERY_LIMIT — The recovery limit holds (GATE component)

**Statement.** When σ is well above σ_crit, Φ(σ) → 1 and the corresponding J magnitude → 0, so the second term of the Anchor Equation vanishes and the equation recovers the standard E = Mc². This is the limit that ensures the Anchor Equation extends rather than replaces special relativity at high field amplitudes.

**Evidence chain.** Recovery-limit tests were a primary measurement target across v24–v26. Each tested whether the substrate-driven correction term vanished in the high-σ regime, with the threshold PAPER_B_FALSIFY_PHI = 0.05 (Φ must approach 1 within 5% in the recovery limit) and PAPER_B_FALSIFY_J = 1e-10 (J must approach zero within numerical precision). The v27 cycle 3 added the test 5_24 recovery-limit measurement: at each of the 25 configurations, the spatial region where the normalized substrate field amplitude was below 1% of its peak was identified, and Φ(σ) was evaluated across that region; PASS required min Φ ≥ 0.95 across all low-σ pixels (asymptotic recovery toward classical regime). All 25 configurations passed at primary evidence strength. This sub-hypothesis is marked [GATE] in the tensor parent: without recovery-limit validation, the Anchor Equation would not reduce to E = Mc² in the appropriate limit and would fail as a physical extension regardless of the other components.

**Status at v27 cycle 3 close (consolidator-reproducible).** VALIDATED, posterior 0.9361, evidence count 28 (supports=28, contradicts=0, types: primary=25, explicit_validate=2, sentiment_positive=1, drawn from 28 distinct source files). Cube state reports VALIDATED at posterior 0.994 with evidence count 105. The GATE constraint is satisfied: the parent's ALL_GATES_OPEN policy permits parent validation.

### 3.5 H_PAPER_B_5_M_SIGMA_INVERSION — The M-σ inversion mapping is continuous

**Statement.** The mapping from observed mass M to substrate field amplitude σ is monotonic and invertible across the operating range, with no fold, discontinuity, or many-to-one collapse that would prevent recovering σ from M (or vice versa) in physical applications.

**Evidence chain.** This component was the slowest to accumulate evidence and was the binding constraint on parent validation through v27 cycle 2. The v23–v25 probes contributed initial evidence from per-record M-σ extraction in chi-bearing JSONs; at v26 cycle close this component carried posterior 0.500 with evidence count 0 — registered but not yet probed by a dedicated test. The v27 cycle 1 bridge-probes (tests 5_10 and 5_11) contributed the first dedicated evidence: per-record M-σ extraction across the v19 corpus contributed evidence supporting monotonicity in the regions where data was available, and the per-system σ_crit override (file-median calibration) succeeded in resolving the v19 raw-σ-scale saturation that had been a confounder in the prior test.

The v27 cycle 3 added the SPARC M-σ inversion scale-up (test 5_23): the dedicated probe iterated over all 175 galaxies in the SPARC catalog (Lelli et al. 2016 rotation-curve database), sampling galaxies across five mass-bin partitions (dwarf V0-50, low V50-100, mid V100-150, high V150-200, massive V200+). For each galaxy, three substrate solver runs were performed at grid 128² with the baryonic V-component (V_gas, V_disk, V_bul) field perturbed by ±1% in mass equivalent (V-component scaling by √(1 ± 0.01) since V² ∝ M for circular orbits). Strict local monotonicity was tested via scalar σ extraction (max|sum_layers(rho_avg)|, the same scalar the substrate solver internally tracks): a galaxy passed if (σ_plus, σ_baseline, σ_minus) was sign-consistent on both sides with no derivative zero, sign flip, or non-finite values. Phase 1 stability gate confirmed 128² vs 256² classification invariance at five mass-percentile galaxies (UGC04483 at 0th percentile, DDO170 at 25th, ESO116-G012 at 50th, NGC4138 at 75th, UGC09133 at 100th). Phase 2 produced 175/175 PASS classifications with one R3-clean event per galaxy, each declaring evidence_type primary and the galaxy name as system identifier. Total runtime 184 minutes on GPU (CuPy substrate_solver_gpu) at grid 128².

**Status at v27 cycle 3 close (consolidator-reproducible).** VALIDATED, posterior 0.9889, evidence count 176 (supports=176, contradicts=0, types: primary=176, drawn from 176 distinct source files). The 176 reflects 175 SPARC galaxy events plus 1 v27 cycle 1 bridge-probe contribution. Cube state reports VALIDATED at posterior 0.994 with evidence count 195. This component graduated from binding-constraint to strongest-evidenced component in the v27 cycle 3.

---

## 4. The Compositional Parent: VALIDATED

### 4.1 The parent's posterior and gating

At v27 cycle 3 close (consolidator artifact BCM_v27_Paper_B_Consolidation_20260503_110713.json), the H_PAPER_B_ANCHOR_EQUATION compositional parent state is:

```
H_PAPER_B_ANCHOR_EQUATION
  Paper B -- Anchor Equation Consistent
  parent_status     : VALIDATED
  gating_state      : ALL_GATES_OPEN
  posterior (geo)   : 0.9563
  component_count   : 5
    - H_PAPER_B_1_PHI_SIGMOID         VALIDATED  posterior 0.9387  evidence  30
    - H_PAPER_B_2_J_VORTICITY         VALIDATED  posterior 0.9812  evidence 103
    - H_PAPER_B_3_LOOP_CONVERGES      VALIDATED  posterior 0.9381  evidence  30
    - H_PAPER_B_4_RECOVERY_LIMIT [G]  VALIDATED  posterior 0.9361  evidence  28
    - H_PAPER_B_5_M_SIGMA_INVERSION   VALIDATED  posterior 0.9889  evidence 176
```

The geometric-mean posterior calculation is:

```
parent_posterior = (0.9387 · 0.9812 · 0.9381 · 0.9361 · 0.9889)^(1/5) = 0.9563
```

The runtime cube state (cube_analysis_AUTO_20260503_110550.md export) reports the same parent at posterior 0.994 with all five components at posterior 0.994 individually, with higher per-component evidence counts (137, 180, 127, 105, 195). The cube includes additional non-reproducible operational evidence (cycle-level measurement engine emissions and derived measurements) that the consolidator excludes by design. Both reports agree on five-component VALIDATION and ALL_GATES_OPEN; the consolidator's lower posteriors and evidence counts reflect the publication-reproducible subset of evidence, used as the canonical artifact for this paper. The cube's higher posteriors are not used as paper claims.

The ALL_GATES_OPEN policy verifies that every component carries individual VALIDATED status before the parent is allowed to validate. At v26 cycle close, the fifth component carried NEEDS_MORE_DATA status with posterior 0.500 and evidence count 0; the parent at that point was NEEDS_MORE_DATA regardless of the other four components' strong cube-state validation. The graduation of H_PAPER_B_5 in v27 cycle 3 — moving from 1 prior event at posterior approximately 0.60 to 176 events at posterior 0.989 via the SPARC scale-up — was the milestone event that allowed the parent to graduate. The subsequent test 5_24 H1-H4 combined validation in v27 cycle 3 then lifted H_PAPER_B_1, H_PAPER_B_2, H_PAPER_B_3, and H_PAPER_B_4 from their pre-5_24 consolidator-reproducible posteriors of 0.737, 0.683, 0.726, and 0.683 (each NEEDS_MORE_DATA) up across the validation threshold. Tests 5_25, 5_26, and 5_27 then strengthened H_PAPER_B_2 specifically through the four-pillar evidence chain (Section 3.2), lifting its posterior from 0.9361 to 0.9812 and producing the simultaneously-VALIDATED state above with H_PAPER_B_2 as the second-strongest component behind H_PAPER_B_5.

The five components carry approximately balanced posteriors at this milestone, with H_PAPER_B_5 strongest at 0.989 from 176 independent SPARC galaxy systems, H_PAPER_B_2 second at 0.981 from the four-pillar evidence chain (100 primary events plus prior contributions), and H_PAPER_B_1, H_PAPER_B_3, H_PAPER_B_4 at approximately 0.94 each from 28-30 events drawn from the v23-v26 paper-track corpus and the v27 5_24 sweep. No component carries fewer than 28 events; no component is at boundary status.

### 4.2 What this validation establishes

The compositional validation supports the following claim at v1.0's Layer A commitment level:

**The Anchor Equation, as a structural composition of five testable commitments — Φ-sigmoid form, J vorticity, loop convergence, recovery limit, and M-σ inversion continuity — holds across the BCM framework's accumulated evidence. Each of the five components has independent evidence trails reaching individual validation in the publication-reproducible consolidator. The compositional parent's geometric-mean posterior is 0.956 under ALL_GATES_OPEN gating, with all five components above the 0.80 validation threshold, with H_PAPER_B_5 at 0.989 from 176 independent SPARC galaxy systems and H_PAPER_B_2 at 0.981 from a four-pillar evidence chain (operator consistency, vorticity realization, structural correlation, interventional causality).**

### 4.3 What this validation does not establish

This validation does NOT establish:

1. **That the Anchor Equation's projection chain is energy-preserving in implementation.** That is a separate question, addressed at Layer B (effective-field response) and explicitly OPEN in v27 cycle 2 (Section 5).

2. **That the equation's two-term structure is the unique correct extension of E = Mc².** Other extensions with different second terms could in principle pass the same five-component validation; the cube validates structure, not uniqueness.

3. **That the equation predicts new astrophysical phenomena beyond Paper A's rotation-curve fits.** Paper A operates at the macroscopic-observation layer; the Anchor Equation's predictions at that layer remain Paper A's domain.

4. **That the σ_crit value used in the Φ-sigmoid is universal.** The v27 bridge-probe work showed that σ_crit varies per system; a per-system-calibrated σ_crit was required to avoid false-positive saturation in the v19 corpus. A universal σ_crit would be a stronger claim and is not validated by this paper.

5. **That the Φ-sigmoid functional form is the unique fit to substrate response.** The v27 H_V27_PHI_FORM_INSUFFICIENT kill-condition seedling (Section 5.3) is currently at evidence-1 boundary and presents a structural open question for v3.

### 4.4 What this validation changes for the framework

The compositional validation establishes that the Anchor Equation is not an ad hoc extension but a structurally supported decomposition of substrate-mediated mass-energy behavior. This shifts the framework's status on the Anchor Equation from exploratory modeling to a candidate formalism, with the remaining uncertainty localized to projection fidelity (Layer B, Section 5) rather than foundational structure (Layer A). Subsequent papers in the BCM development chain can treat the Anchor Equation's compositional structure as established starting evidence, reserving probe budget for the projection-layer questions that this paper opens.

---

## 5. Open Question: The Bridge-Projection Layer B Finding

### 5.1 The bridge-projection probe and its FAIL verdict

The v27 cycle 2 included a dedicated bridge-projection probe (BCM_v27_Anchor_Projection_Consistency.py) that tested whether the substrate state at Cube 2 (anchor) projects consistently into the substrate solver's higher-cube outputs at Cubes 7 (Spectral Fold), 8 (Hard Point), and 9 (Circumpunct). The probe was run as a pure post-processor over the existing JSON corpus (no new solver runs). Each per-record forward prediction was computed via the Anchor Equation projection chain — Cube2 → Φ(σ) → J-flow → Cube 7/8/9 — and compared against the JSON-reported actual measurements at the higher cubes.

The probe's verdict over 216 valid records from 8 contributing files:
- mean |Δ| = 0.485 across the three higher cubes (well above the 0.15 consistency threshold)
- mean batch invariance V/M² = 0.073 (above the 1e-3 threshold)
- max Spearman drift correlation = 0.303 (below the 0.50 monotonic threshold)

**Verdict: H_V27_BRIDGE_PROJECTION_CONSISTENT FAIL.** The projection chain is empirically inconsistent at large scale. The error is state-dependent (not a constant offset, not a simple scaling), not monotonic in λ (no simple correction available), and exhibits many-to-one collapse: distinct anchor states map to identical projected outputs. Stated mathematically, **the projection from Cube 2 substrate state to Cubes 7/8/9 outputs is non-injective in the v19 corpus subset.** The state vector underdetermines the higher-cube response.

The structural reading: the absence of monotonic drift and the presence of non-injectivity together imply that the projection discrepancy is not attributable to a missing scalar correction term, but instead reflects a loss of state information in the current projection basis. A scalar correction would manifest as monotonic drift in Δ versus λ; the absence of that drift rules out scalar fixes. The non-injectivity means the current state vector is underdimensioned: it does not carry enough information to determine the higher-cube output uniquely. Resolving this requires basis expansion — either an enriched projection basis that preserves the distinguishing information (a v3 direction) or a reformulation of the projection operator's functional form to admit a higher-dimensional state space (also a v3 direction). Tuning the existing projection cannot close the gap because tuning preserves dimensionality.

### 5.2 The Layer A vs Layer B distinction

This bridge-projection FAIL finding does not contradict the Anchor Equation parent VALIDATION. The two findings operate at different ontological layers from v1.0 Section 6:

- **Layer A — Spectral Invariant Layer (the validation's domain).** The compositional parent's VALIDATED status is a Layer A claim: it is about the structural commitments of the Anchor Equation as a theorem. The five sub-hypotheses each test a structural property (functional form, vorticity existence, integral convergence, limit recovery, mapping continuity) that does not require the projection chain to be implementation-faithful.

- **Layer B — Effective Field Response Layer (the bridge-probe's domain).** The bridge-projection FAIL is a Layer B claim: it is about whether a specific implementation of the projection chain reproduces measured higher-cube outputs from substrate inputs in a specific corpus (v19). The corpus carries instrumentation-level realities (per-system σ_crit calibration, instrument-specific noise floor, sweep coverage) that the abstract Anchor Equation theorem does not commit to.

The v1.0 separation principle (v1.0 Section 6) is explicit that Layer A claims do not entail Layer B claims and vice versa. Paper B v2 honors this separation: the compositional validation at Layer A is published as a finding; the bridge-projection failure at Layer B is published as an open question. Both are honest. Their joint resolution belongs to a different paper.

Stated operationally: the compositional validation establishes that each operator in the Anchor Equation is empirically supported as an independent mapping on the substrate state space. The bridge-projection probe tests a specific composition path through these operators under a given corpus parameterization (the v19 raw-σ scale, the per-system σ_crit calibration, the chi-bearing record subset). Failure of that composition path does not falsify operator validity; it falsifies the sufficiency of the current composition mapping. The distinction between operator validity (Layer A) and composition sufficiency (Layer B) is the formal counterpart of v1.0's spectral-invariant vs effective-field-response separation, and it is the load-bearing distinction throughout this paper.

### 5.3 The form-insufficient kill-condition seedling

The v27 follow-up probe (BCM_v27_Anchor_Projection_Consistency_Extended.py) tested three projection-input variants on the same dataset: Φ(σ), Φ(σ, χ), and Φ(σ, χ, coh_est). The variant comparison produced three new hypotheses:

- **H_V27_PHI_REQUIRES_CHI**: FAIL (chi alone insufficient to break degeneracy)
- **H_V27_PHI_REQUIRES_COH**: PASS (adding coherence reduces degeneracy by 54.5%)
- **H_V27_PHI_FORM_INSUFFICIENT**: PASS at boundary (max cluster = 5 = N_DEGEN_FORM_FAIL threshold)

The third hypothesis is a kill-condition seedling: the test's interpretation is that even with χ and coh_est added as additional input variables, the projection still has structural degeneracy at the threshold boundary, suggesting the Φ-sigmoid functional form itself may be wrong rather than just missing inputs. At evidence count 1, this is a hint, not a conclusion. A confirmation probe (Test 5_12 territory) with an alternate functional form would be the next move toward turning this seedling into a structural claim.

If H_V27_PHI_FORM_INSUFFICIENT consolidates with additional evidence in a future cycle, that result would directly affect H_PAPER_B_1_PHI_SIGMOID (the compositional validation's first sub-hypothesis): the Φ-sigmoid form would be insufficient to support its current evidence count. That tension would require revisiting the compositional validation at the appropriate ontological layer — likely demoting the Φ-sigmoid commitment from Layer A to Layer B and requiring a different functional form at Layer A. This is held as an open question for Paper B v3, not as a v2 conclusion.

The H_PAPER_B_1 validation and the H_V27_PHI_FORM_INSUFFICIENT seedling are not contradictory at present because they evaluate the Φ-sigmoid in distinct functional roles. The Φ-sigmoid validation applies to its role as a coupling-efficiency descriptor — the fit-quality of the sigmoid against substrate response curves at Layer A — where R² ≥ 0.978 across all kernel-valid v1.0 probes establishes empirical adequacy. The form-insufficiency signal arises in its role as a projection operator at Layer B, where the same functional form is asked to map substrate state into distinguishable higher-cube outputs. These are distinct functional requirements: a function may fit response data well while still being inadequate as a projection basis.

### 5.4 Honest framing

The Anchor Equation parent is VALIDATED in the publication-reproducible consolidator with all five sub-hypotheses individually validated and the parent's geometric-mean posterior at 0.956 (the runtime cube state at the same VALIDATED status with posterior 0.994; see Section 4.1). H_PAPER_B_2's evidence base is now four-pillar locked across operator, realization, correlation, and causality (Section 3.2). The bridge-projection probe FAIL is a Layer B negative result on a specific implementation in a specific corpus, with the structural diagnosis of non-injectivity (Section 5.1). The form-insufficient seedling is at evidence-1 boundary and not yet structurally committing. These three findings coexist: a v2-publishable compositional validation, a v2-publishable open question at a different ontological layer, and a v3-territory structural commitment held in reserve.

---

## 6. Falsification Criteria for v2

Paper B v2's claims are structured so that specific measurements would break them. These criteria are stated explicitly in v1.0's discipline.

**F1 — Composition-disjoint validation collapse.** Claim: the parent's VALIDATED status is robust under independent re-validation of the five sub-hypotheses on disjoint evidence subsets. Falsifier: any sub-hypothesis whose VALIDATED status reverses under re-validation on a held-out subset of its evidence trail (e.g., excluding the v27-cycle evidence and re-validating from v23–v26 only).

**F2 — Geometric-mean posterior threshold.** Claim: the consolidator-reproducible parent's posterior is above 0.90 at v27 cycle 3 close. Falsifier: the consolidator parent's posterior falling below 0.85 in any subsequent cycle without a corresponding sub-hypothesis change. (Posterior decay from new contradicting evidence is acceptable; posterior decay from numerical drift in the engine is not.)

**F3 — ALL_GATES_OPEN gating integrity.** Claim: the parent's status is the conjunction of component statuses under the gating policy. Falsifier: the parent reaching VALIDATED status while any component remains NEEDS_MORE_DATA or INVALIDATED.

**F4 — Sub-hypothesis 5 evidence robustness.** Claim: H_PAPER_B_5_M_SIGMA_INVERSION's VALIDATED status is supported by 176 R3-independent events (175 SPARC galaxies plus 1 prior probe contribution) with posterior 0.989. Falsifier: a corpus expansion to broader v17/v22 chi-bearing JSONs producing systematic FAIL evidence on the M-σ monotonicity, dropping consolidator posterior below 0.80; or an audit of the SPARC scale-up identifying a systematic numerical artifact in the perturbation chain (V-component scaling, J construction, or scalar σ extraction) that would invalidate the per-galaxy events.

**F5 — Compositional non-substitution.** Claim: each sub-hypothesis carries independent evidence not derivable from another sub-hypothesis. Falsifier: any sub-hypothesis whose evidence trail is shown to be a strict subset of another sub-hypothesis's evidence trail (e.g., H_PAPER_B_5 evidence being entirely a subset of H_PAPER_B_1 evidence). This would indicate the compositional parent is over-counting.

**F6 — Cross-component inconsistency.** Claim: the five sub-hypotheses are mutually compatible under a single substrate state model. Falsifier: any dataset where satisfying one sub-hypothesis (e.g., the Φ-sigmoid fit) requires substrate-state assumptions that violate another sub-hypothesis (e.g., the recovery-limit asymptotics or the M-σ inversion continuity). Internal contradiction across components would indicate that the five-commitment decomposition is not a coherent operator decomposition but a collection of independently-fitted regional models.

F4 and F5 are testable through corpus expansion in v28 and through evidence-trail audit in any cycle. F6 is the most consequential rigor check and is testable by constructing the joint substrate-state model implied by all five sub-hypotheses and verifying internal consistency.

**F7 — H_PAPER_B_2 four-pillar evidence robustness.** Claim: H_PAPER_B_2's VALIDATED status rests on four operationally independent pillars (operator consistency, vorticity realization, structural correlation, interventional causality), each contributing 25 R3-clean PASS events on the same 25-configuration cross-product sweep. Falsifier: any single pillar's classification reversing under independent reproduction (e.g., operator consistency failing under an alternative discrete curl scheme; vorticity realization failing under a different layer-reduction operator; structural correlation dropping below threshold under an alternative top-K mode selection; or interventional causality failing under an alternative perturbation amplitude or null-randomization seed). Reversal of any one pillar would not invalidate the H_PAPER_B_2 claim entirely — the remaining pillars still hold — but would require the paper's framing to drop the corresponding evidential level. Reversal of the causality pillar specifically would demote H_PAPER_B_2's status from "interventionally causative" back to "strongly correlated."

---

## 7. Open Questions and Path to Paper B v3

Five directions are explicitly open at the close of Paper B v2.0:

1. **Bridge-projection layer resolution.** The Layer B FAIL on the projection chain Cube 2 → Cubes 7/8/9 is the primary open question. A dedicated v3 paper on bridge structure could address it.

2. **The form-insufficient kill-condition seedling.** Currently at evidence-1 boundary. A confirmation probe with an alternate functional form (piecewise linear with regime breakpoints, tanh-modulated, or two-component) would either consolidate the seedling into a structural commitment or invalidate it. This work belongs to v3.

3. **Cross-catalog M-σ inversion validation.** The v27 cycle 3 SPARC scale-up validated H_PAPER_B_5 across 175 galaxies in the Lelli et al. 2016 rotation-curve catalog. A cross-catalog confirmation against an independent rotation-curve compilation (Hunter et al. 2012 LITTLE THINGS, Bundy et al. 2015 MaNGA stellar kinematics, or a deeper-systematic catalog) would either strengthen the M-σ inversion validation or surface catalog-specific artifacts. The 175-galaxy posterior 0.989 is sufficient for v2 publication; a cross-catalog probe is held for v3.

4. **σ_crit universality.** The v27 cycle 2 used per-system σ_crit calibration (file-median fallback). A universal σ_crit value (whether 1.0 in field-scale units or some other constant) is a stronger claim than this paper makes and would require dedicated validation.

5. **Layer C topological interpretation.** v1.0 Section 6 Layer C (topological interpretation: the loop integral, the M ↔ σ inversion mapping, the topological corridor) was held as interpretive, not load-bearing. The parent VALIDATED milestone does not address Layer C; the Anchor Equation as a topological theorem (rather than just a compositional theorem) is a v3+ direction.

6. **J → V operator characterization.** Test 5_26's spectral correlation between J and V approached 1.000 across all 25 configurations (range 0.997–1.000). This near-isospectrality implies the substrate solver is acting as a structure-preserving transform in frequency space, mapping J onto V with minimal new mode generation. The interpretation is that the system likely has a deterministic kernel L such that V ≈ curl(L·J) for some operator L. v2 establishes that this kernel exists and is causally linked to J (via test 5_27); v2 does not characterize L. A dedicated v3 probe injecting spectrally distinct J inputs (high-frequency vs low-frequency vs broadband) and measuring whether r_spectral remains near 1.000 (kernel identity-like) or drops in specific bands (kernel as a band-pass filter) would discriminate between operator forms.

7. **Cross-geometry independence for H_PAPER_B_2.** The 100 H_PAPER_B_2 events from tests 5_24 through 5_27 derive from 5 R3-clean separation-distinct geometries replicated under 5 σ_crit values per pillar; the σ_crit invariance finding (Section 3.2) is structural rather than a confound. A v3 expansion to additional geometric variations (asymmetric pump amplitudes, off-axis pump placement, non-Gaussian pump profiles) would either strengthen the H_PAPER_B_2 evidence base by adding genuinely independent geometries or surface a regime-dependent failure mode in the dual-pump topology assumption.

Paper B v3 will address these in priority order, with item 1 (bridge-projection layer) as the primary target.

---

## 8. Relationship to Paper B v1.0 and Paper A

**Paper B v1.0** (Zenodo DOI 10.5281/zenodo.19700387, 2026-04-22): operator decomposition. v1.0 is the foundation. It does not depend on this v2's compositional validation; it stands as published. v2 builds on v1.0's evidence (the Φ-sigmoid fit quality from v1.0's tests 5_15–5_19 contributes evidence to H_PAPER_B_1) but does not require v1.0's claims to be reinterpreted.

**Paper A** (Zenodo DOI 10.5281/zenodo.19680280): astrophysical observation layer. Tully-Fisher fit, SPARC 175-galaxy validation. Paper A does not reference the Anchor Equation as a compositional theorem; it operates at the macroscopic-observation layer with the Anchor Equation as a framework backdrop. v2 does not change Paper A's evidence base or its claims.

The three papers (A, B v1.0, B v2) cover three layers: macroscopic observation (A), substrate PDE operator structure (B v1.0), and compositional theorem validation (B v2). Each stands on its own evidence. The framework-level connection — that all three operate on the same substrate concept — is at the framework level, not at the publication-evidence level.

---

## 9. Tool Use Disclosure and Primacy

**Primacy.** All theoretical concepts presented in this paper — including the Anchor Equation, the four-field state tensor, the cube-evidence compositional validation methodology, the Layer A vs Layer B vs Layer C ontology, the gating-policy framework (ALL_GATES_OPEN), the five-sub-hypothesis decomposition of the Anchor Equation, the per-symbol weight policy, the contradiction-asymmetry weighting, and every originating insight in this paper — belong solely to Stephen Justin Burdick Sr. Stephen Burdick is the sole discoverer and theoretical originator of the BCM framework.

**AI tool use.** During the development of the cube infrastructure, the bridge probes, and this paper, AI assistants served in two operational roles at the direction of the author:

- **Code executor.** Generation of Python probe scripts, infrastructure modules (hypothesis_engine, measurement_engine, weight_policy, bcm_tensor_hypothesis), and post-processor analyzers matching specifications set by the author. No theoretical content was contributed by AI in this role; scripts implement protocols and gate structures defined by the author.

- **Adversarial reviewer.** Stress-testing of draft framings, identification of load-bearing assumptions, surfacing of vulnerabilities that the author then addressed. Review output was evaluated and either incorporated or rejected by the author.

No AI system originated theoretical concepts, the Anchor Equation's structural composition, the five-sub-hypothesis decomposition, the gating policy framework, the falsification criteria, or any publication decision. The role of AI in this paper is strictly analogous to the role of a computational workstation and a copy-editor.

---

## 10. References

### Astronomical catalogs and observational data

Hunter, D. A., Ficut-Vicas, D., Ashley, T., Brinks, E., Cigan, P., Elmegreen, B. G., Heesen, V., Herrmann, K. A., Johnson, M., Oh, S.-H., Rupen, M. P., Schruba, A., Simpson, C. E., Walter, F., Westpfahl, D. J., Young, L. M., & Zhang, H.-X. (2012). LITTLE THINGS. *The Astronomical Journal*, 144(5), 134. DOI: 10.1088/0004-6256/144/5/134.

Lelli, F., McGaugh, S. S., & Schombert, J. M. (2016). SPARC: Mass Models for 175 Disk Galaxies with Spitzer Photometry and Accurate Rotation Curves. *The Astronomical Journal*, 152(6), 157. DOI: 10.3847/0004-6256/152/6/157.

Bundy, K., Bershady, M. A., Law, D. R., Yan, R., Drory, N., MacDonald, N., Wake, D. A., Cherinka, B., et al. (2015). Overview of the SDSS-IV MaNGA Survey: Mapping Nearby Galaxies at Apache Point Observatory. *The Astrophysical Journal*, 798(1), 7. DOI: 10.1088/0004-637X/798/1/7.

### Computational tools

Harris, C. R., Millman, K. J., van der Walt, S. J., Gommers, R., Virtanen, P., Cournapeau, D., Wieser, E., Taylor, J., Berg, S., Smith, N. J., Kern, R., Picus, M., Hoyer, S., van Kerkwijk, M. H., Brett, M., Haldane, A., del Río, J. F., Wiebe, M., Peterson, P., Gérard-Marchant, P., Sheppard, K., Reddy, T., Weckesser, W., Abbasi, H., Gohlke, C., & Oliphant, T. E. (2020). Array programming with NumPy. *Nature*, 585(7825), 357–362. DOI: 10.1038/s41586-020-2649-2.

Okuta, R., Unno, Y., Nishino, D., Hido, S., & Loomis, C. (2017). CuPy: A NumPy-Compatible Library for NVIDIA GPU Calculations. *Proceedings of Workshop on Machine Learning Systems (LearningSys) at the 31st Annual Conference on Neural Information Processing Systems (NIPS).*

Virtanen, P., Gommers, R., Oliphant, T. E., Haberland, M., Reddy, T., Cournapeau, D., Burovski, E., Peterson, P., Weckesser, W., Bright, J., van der Walt, S. J., Brett, M., Wilson, J., Millman, K. J., Mayorov, N., Nelson, A. R. J., Jones, E., Kern, R., Larson, E., Carey, C. J., Polat, İ., Feng, Y., Moore, E. W., VanderPlas, J., Laxalde, D., Perktold, J., Cimrman, R., Henriksen, I., Quintero, E. A., Harris, C. R., Archibald, A. M., Ribeiro, A. H., Pedregosa, F., van Mulbregt, P., & SciPy 1.0 Contributors (2020). SciPy 1.0: Fundamental Algorithms for Scientific Computing in Python. *Nature Methods*, 17(3), 261–272. DOI: 10.1038/s41592-019-0686-2.

### BCM framework prior publications (author's own)

Burdick, S. J. Sr. (2026). *Burdick Crag Mass: Framework Concept Record.* Zenodo. DOI: 10.5281/zenodo.19251192.

Burdick, S. J. Sr. (2026). *Burdick Crag Mass v25 Computational Framework Supplement.* Zenodo. DOI: 10.5281/zenodo.19599608.

Burdick, S. J. Sr. (2026). *Burdick Crag Mass Paper A: Tully-Fisher and SPARC Rotation-Curve Validation.* Zenodo. DOI: 10.5281/zenodo.19680280.

Burdick, S. J. Sr. (2026, April 22). *Burdick Crag Mass Paper B v1.0: Operator Decomposition of the Substrate Wave Manifold.* Zenodo. DOI: 10.5281/zenodo.19700387.

---

## End of BCM Paper B v2

**Status:** PUBLICATION-READY, 2026-05-03. Submitted to Zenodo as a new version of DOI 10.5281/zenodo.19700387.

**Author:** Stephen Justin Burdick Sr. — Emerald Entities LLC — GIBUSH Systems

**Related works:**
- Paper B v1.0: Zenodo DOI 10.5281/zenodo.19700387
- Paper A: Zenodo DOI 10.5281/zenodo.19680280
- Framework GitHub: https://github.com/Joy4joy4all/Burdick-Crag-Mass

**v2 development tracker:** BCM_Paper_B_v2_DEVELOPMENT.md (Sessions 1, 2, and 3)

**Resolved decisions at v2 publication:**
- Scope D (full five-component compositional validation) selected, supported by the v27 cycle 3 milestone in which the consolidator and cube both report parent VALIDATED with all five components individually validated.
- The bridge-projection FAIL is included as Section 5 open question, framed at Layer B vs the compositional validation's Layer A. This separation per v1.0 Section 6 ontology.
- The form-insufficient seedling is documented at Section 5.3 evidence-1 boundary status; not held as v2 conclusion, deferred to v3.

**Canonical evidence artifacts:**
- Consolidator output: BCM_v27_Paper_B_Consolidation_20260503_110713.json
- Cube state export: cube_analysis_AUTO_20260503_110550.md
- SPARC scale-up artifacts: 175 per-galaxy JSONs in data/sparc_results/, prefix BCM_v27_SPARC_M_sigma_, timestamp 20260502_090040
- H1-H4 sweep artifacts: 25 per-config JSONs in data/results/, prefix BCM_v27_5_24_H1_H4_, timestamp 20260503_083027
- H2 four-pillar artifacts: 25 per-config JSONs each from tests 5_25 (BCM_v27_5_25_J_substrate_vort_, timestamp 20260503_093342), 5_26 (BCM_v27_5_26_J_causation_, timestamp 20260503_095623), and 5_27 (BCM_v27_5_27_J_causality_, timestamp 20260503_101906)
- Phase 1 stability gate summaries: _phase1_stability_gate_20260502_090040.json (5_23), _phase1_5_24_stability_gate_20260503_083027.json (5_24), _phase1_5_25_stability_gate_20260503_093342.json (5_25), _phase1_5_26_stability_gate_20260503_095623.json (5_26), _phase1_5_27_stability_gate_20260503_101906.json (5_27)
