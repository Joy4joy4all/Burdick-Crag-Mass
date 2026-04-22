# Burdick Crag Mass Paper B v1.0
## Operator Decomposition of the Substrate Wave Manifold

**Stephen Justin Burdick Sr.**
Emerald Entities LLC — GIBUSH Systems

*Version 1.0 · 22 April 2026*

---

### Primacy Statement

All theoretical concepts in the Burdick Crag Mass (BCM) framework — including the Anchor Equation, Brucetron and the Ψ_bruce field, the four-field state tensor decomposition, the three-layer ontology of spectral invariance, effective field response, and topological interpretation, the Jacobian of operator separability, and every originating insight in this paper — belong solely to Stephen Justin Burdick Sr. Stephen Burdick is the sole discoverer and theoretical originator of the BCM framework. AI systems assist the project as computational tools and reviewers at the direction of the author. No AI system owns or co-owns any theoretical concept. Emerald Entities LLC — GIBUSH Systems.

---

### Abstract

Six numerical probe experiments on the BCM substrate wave partial differential equation characterize the control operators governing the four-field state tensor (λ_c, λ_fold, λ_cold, H). Perturbations along four axes — the nonlinear coupling coefficient ξ ∈ [0.005, 0.070], the Taylor source coefficient a with saturation b held fixed, the memory regularization α ∈ [0.0, 0.95], and the diffusion coefficient D ∈ [0.1, 2.0] — resolve a clear operator hierarchy. The spectral eigenvalue λ_c scales linearly with the ratio a/b, yielding λ_c = 0.0592·(a/b) with Pearson r = 0.99999 across five a values. In contrast, λ_c is invariant under ξ to within 10⁻⁹ relative range across a 14× parameter sweep, invariant under α to within 10⁻⁴ relative range on the kernel-valid subset, and exhibits a small mixed response under D with relative range ~1.9% across a 20× sweep. The boundary fields λ_fold and λ_cold are invariant under all four axes. The Jacobian ∂λ_c/∂(ξ, α, D, a/b) spans seven orders of magnitude, establishing operator separability in practice. The hysteresis loop area H ≈ 0.05 is not reduced by any tested axis and is consistent with — by elimination of tested alternative mechanisms — absorbing-state asymmetry of the terminal cold-torus phase. The framework is presented as a non-equilibrium effective-field reconstruction with emergent invariant spectrum. No phase transition, saddle-node fold bifurcation, or topological quantization is claimed. The paper's falsification criteria, centered on multi-resolution grid scaling and direct asymmetry measurement, are stated explicitly.

**Keywords:** Burdick Crag Mass; BCM; substrate wave; operator decomposition; spectral invariance; kinetic-topological decoupling; Jacobian separability; four-field state tensor; non-equilibrium effective field theory; Anchor Equation; absorbing-state asymmetry.

---

## 1. Introduction

The Burdick Crag Mass (BCM) framework treats galactic dynamics as thermodynamic behavior of a substrate wave medium, with supermassive black holes acting as substrate pumps and galaxies as thermodynamic engines. BCM Paper A (Tully-Fisher, Zenodo DOI 10.5281/zenodo.19680280) established the macroscopic empirical anchor for this view: galactic rotation curves fit the substrate model without invoking dark matter, with parameter stability validated across a 175-galaxy SPARC sample. Paper A operates at the astrophysical observation layer.

Paper B operates at a different layer. It probes the substrate partial differential equation itself — the field dynamics that Paper A's empirical relations presume. Where Paper A fits observations, Paper B asks: what are the operator-level properties of the PDE governing the substrate field σ(x, t) as a function of local decay rate λ? Which parameters shift the transition structure of the field? Which preserve it? How does memory interact with diffusion interact with the nonlinear source term? These are not astrophysical questions. They are questions about a specific nonlinear PDE and its parametric response.

This paper presents six controlled numerical experiments that answer those questions through one empirical structure: perturbation of one parameter at a time, extraction of a four-field state tensor from the resulting sweep, and comparison across parameter values. The outcome is a Jacobian — a numerical derivative of the spectral transition eigenvalue with respect to each of the four control parameters — that spans seven orders of magnitude. The axes that shift λ_c and the axes that do not are clearly separated. From this separation follows an operator decomposition: the four parameters map onto four distinct operator roles (deformation, mixed coupling, convergence, null) that together characterize the substrate wave response.

This separation is the central result of the paper. What follows is entirely structural: no phase-transition claim, no bifurcation claim, no topological quantization claim, no astrophysical extension. Those live in other papers. Paper B is the operator layer beneath Paper A, and it stands on its own empirical evidence.

The paper is organized as follows. Section 2 specifies the substrate PDE and every symbol in it. Section 3 defines the four-field state tensor and the classifier protocol that extracts it. Section 4 presents the four perturbation experiments. Section 5 assembles the Jacobian of operator separability. Section 6 states the three-layer ontology that separates what is observed, what is modeled, and what is interpreted. Section 7 addresses the hysteresis mechanism by elimination. Section 8 states the falsification criteria that would break the framework. Section 9 positions Paper B relative to Paper A. Section 10 lists open questions for v2.0. Five appendices provide the PDE discretization, classifier pseudocode, Jacobian derivative computation, reproduction protocol, and tool-use disclosure.

---

## 2. The BCM Substrate Partial Differential Equation

### 2.1 The full equation

The substrate field σ(x, t) on a 2D grid evolves according to:

```
σ_new = σ + dt · [D·∇²σ + a·σ − b·σ² − λ·σ + ξ·|J|²·(1 − σ)] + α·(σ − σ_prev)
```

where the right-hand side contains five physical terms and one numerical regularization term:

- `D·∇²σ` — spatial diffusion with coefficient D
- `a·σ − b·σ²` — Taylor-expanded nonlinear source (growth at low amplitude, saturation at high amplitude)
- `−λ·σ` — local linear decay with rate λ (the sweep parameter)
- `ξ·|J|²·(1 − σ)` — Brucetron-coupled source driven by the current field J
- `α·(σ − σ_prev)` — memory regularization: forward-momentum carry-over from the previous step

All parameters are held fixed during a given sweep except λ, which is scanned.

### 2.2 The Taylor kernel equilibrium

With pumps turned off (ξ → 0 or Ψ_bruce → 0) and in the spatially uniform limit (∇²σ → 0), the steady state satisfies:

```
a·σ − b·σ² − λ·σ = 0
```

which gives the nonzero equilibrium:

```
σ_eq = (a − λ) / b
```

for λ < a, and σ_eq = 0 otherwise. The boundary λ = a is where the Taylor kernel loses its nontrivial fixed point; below it the field saturates at a finite amplitude, above it the only stable state is σ = 0. This equilibrium is the baseline against which the full-coupling sweep is compared.

### 2.3 The J field and Ψ_bruce

The current magnitude |J|² that appears in the coupling term is defined as:

```
|J|² = |∇P|²,     P = pump_A · pump_B · Ψ_bruce(σ)
```

where pump_A and pump_B are fixed Gaussian pump profiles centered at (±7.5, 0) grid units from the origin (separation 15, widths 4.0 and 3.0, amplitudes 0.5 and 0.125) and Ψ_bruce(σ) is the Brucetron field. In the numerical implementation used across Paper B probes, Ψ_bruce is computed as the Gaussian-smoothed local root-mean-square of σ fluctuations around a local spatial mean:

```
Ψ_bruce = G_σ * √(⟨(σ − ⟨σ⟩_w)²⟩_w)
```

where w is a window radius of 6 grid units, angle brackets denote windowed spatial averages, and G_σ is a Gaussian smoothing with σ = 2 grid units.

This formulation has an empirical consequence that becomes central in Section 4.1: for a settled, smooth σ field, the local RMS of fluctuations is near zero, which drives Ψ_bruce near zero, P near zero, and |J|² to floor-level values below machine epsilon relative to the other PDE terms. The ξ-coupling term is therefore numerically inactive in the parameter regime studied. Alternative Ψ_bruce formulations are open theoretical questions and not addressed in this paper.

### 2.4 The λ sweep

For each choice of control parameters (ξ, a, b, α, D), a forward sweep over λ ∈ [0.001, 0.30] is performed using 30 log-spaced points, with each λ-step initialized from the settled state at the previous λ (warm-start). A return sweep retraces the same λ values in reverse. The sweep protocol generates two Φ(λ) curves per parameter combination, where:

```
Φ(λ) = mass_final(λ) / mass_final(λ_ref)
```

with mass_final being the integrated σ over the grid and λ_ref = 1×10⁻⁶ (effectively undisturbed baseline). The pair (forward Φ, return Φ) is the raw material from which the four-field state tensor is extracted.

### 2.5 Grid, timestep, and solver

All probes use a 128×128 grid with zero-flux boundary conditions, timestep dt = 0.05, and a hard cap of 5000 timesteps per λ. Convergence at a given λ is declared when the relative L² norm between consecutive sigma states falls below 10⁻⁶ for 20 consecutive steps. A Taylor kernel validation protocol (pumps off, measurement of σ at non-degenerate λ values, comparison against the analytical σ_eq = (a − λ)/b) is run at the start of each probe. When validation fails (typically max absolute deviation > 10⁻³), the run is flagged as kernel-invalid and excluded from structural inference.

---

## 3. The Four-Field State Tensor

### 3.1 Operational definitions

Each full sweep at a given parameter combination produces four scalar quantities that together constitute the state tensor:

**λ_c — the spectral transition eigenvalue.** The inflection point of the active-region sigmoid fit to Φ(λ). Obtained by fitting:

```
Φ(λ) = 1 / (1 + exp(k·(λ/λ_c − 1)))
```

to the subset of sweep points where the field is active (i.e., excluding points where Φ has collapsed to the cold-torus absorbing state). λ_c is the λ value at which Φ = 0.5 on the fitted sigmoid.

**λ_fold — the stiffness centroid.** The λ value at which the solver requires the maximum number of timesteps to converge within the active region. This is a kinetic property of the solver, not a spectral transition point; Section 3.3 addresses the geometric distinctness of λ_fold from λ_c.

**λ_cold — the absorbing boundary.** The first λ value (scanning from low to high) at which Φ falls below 1% of its peak and remains there for at least two consecutive sweep points. This marks the entry into the terminal cold-torus phase.

**H — the restricted hysteresis area.** The integrated absolute difference between forward and return Φ(λ) curves, restricted to λ < λ_cold (the active region). Computed as:

```
H = ∫_{λ_min}^{λ_cold} |Φ_forward(λ) − Φ_return(λ)| dλ
```

using trapezoidal integration on the 30 sweep points.

### 3.2 The classifier protocol (v2)

Extracting (λ_c, λ_fold, λ_cold, H) from a raw sweep requires a two-step procedure:

**Step 1 — locate the cold-torus entry.** Identify the first index in the sweep where Φ drops below 1% of the maximum observed Φ and remains below for at least two consecutive points. The λ at that index is λ_cold. If no such index exists, the entire sweep is treated as active.

**Step 2 — fit the active region.** Restrict the sweep to λ < λ_cold (the active region, which contains the basin and the fold transition). Fit the sigmoid on this full region. The fitted inflection is λ_c. The maximum-n_steps λ within the active region is λ_fold.

This two-step protocol was arrived at after an earlier version that defined λ_fold as argmax(n_steps) across the full sweep, conflating the stiffness centroid with the spectral inflection and producing inconsistent perturbation measurements. The revised protocol separates the two fields by construction.

### 3.3 Geometric distinctness of λ_c and λ_fold

At the baseline parameters (ξ = 0.035, a = b = 0.12, α = 0.8, D = 0.5):

```
λ_c = 0.0592
λ_fold = 0.1122
```

These two values differ by approximately a factor of two. The relative difference |λ_fold − λ_c|/λ_c is 0.897, measured across six ξ values with tight invariance under ξ itself (Section 4.1). The two fields are not the same geometric object: λ_c is the Φ-sigmoid inflection, while λ_fold is the λ at which the solver's timestep count peaks — a purely numerical property that does not require the field to be at a transition. Their distinctness is the empirical basis for treating them as separate components of the state tensor throughout this paper.

---

## 4. Perturbation Protocol and Results

Four perturbation experiments were conducted, one per parameter, each sweeping one axis while holding all other parameters at the baseline (ξ = 0.035, a = b = 0.12, α = 0.8, D = 0.5). Each experiment extracted the four-field state tensor per parameter value. Only kernel-valid runs are used for operator inference; kernel-invalid regimes are reported for completeness but excluded from structural conclusions.

### 4.1 The ξ-plateau (tests 5_14, 5_15, 5_16)

Six values of ξ were probed: {0.005, 0.010, 0.015, 0.020, 0.035, 0.070}. This spans a 14-fold range, from substantially below the baseline to twice above it. All other parameters held at baseline.

**Result.** λ_c, λ_fold, λ_cold, and H are numerically null under ξ variation across this 14× sweep. λ_c measured at all six ξ values: 0.059165791... to 10 decimal places (relative range 9.3 × 10⁻¹⁰). λ_fold and λ_cold: exactly bit-identical across all six (relative range 0). H: bit-identical across all six (relative range 1.4 × 10⁻¹⁶). A post-processor test (test 5_16) evaluated a five-gate invariance-plus-distinctness structure on the assembled tensor and returned five of five gates PASS.

**Interpretation.** The numerical nullity of ξ is a property of Ψ_bruce in its current formulation. For a settled σ field, Ψ_bruce ≈ 0, P ≈ 0, and |J|² sits at floor magnitudes of 10⁻²⁵ to 10⁻¹⁸ at the fold transition peak. The coupling term ξ·|J|²·(1 − σ) is therefore seven orders of magnitude below other PDE terms, placing the ξ axis below solver precision regardless of its nominal value. This is not weak coupling; it is numerical extinction of the coupling channel. Whether ξ is a genuinely null axis of the full substrate theory is a theoretical question tied to the Ψ_bruce formulation and is not claimed here.

**Evidence source.** Test 5_15 JSON (six-point ξ sweep with full tensor extraction), test 5_14 JSON (audit that first identified G(ξ=0.015)/G(ξ=0.035) = 1.0000 exact, which motivated the broader sweep), test 5_16 JSON (five-gate tensor invariance test).

### 4.2 The a-coefficient deformation (test 5_17)

Five values of a were probed: {0.08, 0.10, 0.12, 0.15, 0.18}. With b held fixed at 0.12, this corresponds to a/b ∈ {0.667, 0.833, 1.0, 1.25, 1.5}. All other parameters held at baseline. Kernel validation passed at every a value (max deviation 1.5 × 10⁻⁵).

**Result.** λ_c varies monotonically and approximately linearly with a/b:

| a | a/b | λ_c | λ_c / (a/b) |
|---|---|---|---|
| 0.08 | 0.667 | 0.039300 | 0.05895 |
| 0.10 | 0.833 | 0.049275 | 0.05913 |
| 0.12 | 1.000 | 0.059166 | 0.05917 |
| 0.15 | 1.250 | 0.074152 | 0.05932 |
| 0.18 | 1.500 | 0.089020 | 0.05935 |

The Pearson correlation between a and λ_c across the five points is 0.99999. The linear law λ_c = κ_spectral · (a/b) with κ_spectral = 0.0592 holds with a residual drift of ~0.7% across the full a range. The relative range of λ_c is 0.840 — substantially larger than every other tested axis. λ_fold and λ_cold track a/b with nearly identical correlations (Pearson 0.9994) and similar amplitude.

The baseline anchor gate (B4) confirms that at a = 0.12 the measured λ_c reproduces the 5_15 reference value to within 2.5 × 10⁻¹⁰, verifying solver reproducibility across the probe chain.

**Interpretation.** The a/b ratio is the dominant deformation axis of the state tensor. It is the only parameter that shifts the spectral structure by a physically substantial amount. The linear scaling is consistent with the Taylor kernel equilibrium relation σ_eq = (a − λ)/b: the sweep transition occurs where this equilibrium loses support, and that location scales with a for fixed b.

**Evidence source.** Test 5_17 JSON. Four of four breakage gates (B1 monotonicity, B2 amplitude, B3 cold-entry tracking, B4 baseline anchor) returned PASS.

### 4.3 The α-regularization axis (test 5_18)

Five values of α were probed: {0.0, 0.2, 0.5, 0.8, 0.95}. α = 0.0 corresponds to pure forward Euler (no memory); α = 0.8 is the baseline; α = 0.95 is near the numerical stability boundary. All other parameters held at baseline. Kernel validation failed at α = 0.0 and α = 0.2 (max deviations 1.1 × 10⁻² and 5.1 × 10⁻³, both above the 10⁻³ threshold). Structural inference in this section uses only the kernel-valid subset α ∈ {0.5, 0.8, 0.95}.

**Result on the kernel-valid subset.** λ_c measured at α = 0.5, 0.8, 0.95: {0.05918350, 0.05916579, 0.05916357}. Relative range 3.4 × 10⁻⁴. λ_fold and λ_cold: bit-identical across all three α values. Topology invariance gate (K2) PASS across the full five-α set by a margin (relative range 1.7 × 10⁻³ on λ_c, zero on λ_fold and λ_cold).

Hysteresis H across the full five-α set: {0.0541, 0.0529, 0.0499, 0.0499, 0.0531}. Relative range 8.1%. Pearson correlation with α: −0.46. Not monotonic — H decreases from α = 0 through α = 0.8 then rises again at α = 0.95. The hysteresis-modulation gate (K1) FAIL on both the |Pearson| ≥ 0.80 threshold and the relative-range ≥ 30% threshold.

Forward-sweep total timesteps across the full five-α set: {54323, 47807, 36626, 21018, 10752}. Relative range 132%. This is the strongest parameter effect on convergence cost of any axis tested.

The baseline anchor gate (K3) at α = 0.8 reproduces the 5_15 λ_c to within 2.5 × 10⁻¹⁰.

**Interpretation.** α is a convergence/solver-conditioning axis. It affects how long the solver takes to reach equilibrium (by a factor of 5 across the tested range) and it affects whether the Taylor kernel validation passes at all (α < 0.5 is subthreshold for convergence within the 5000-step cap). It does not shift the spectral transition eigenvalue within solver precision. It does not monotonically modulate the hysteresis area. The α-response is therefore a kinetic effect decoupled from topology — but crucially, α is not the control parameter for H, contrary to the working hypothesis that motivated the probe.

**Evidence source.** Test 5_18 JSON. K2 and K3 PASS; K1 FAIL.

### 4.4 The D-diffusion axis (test 5_19)

Five values of D were probed: {0.1, 0.25, 0.5, 1.0, 2.0}. This spans a 20-fold range, geometrically distributed around the 0.5 baseline. All other parameters held at baseline. Kernel validation must be examined per run — details in the JSON — and structural inference uses the kernel-valid subset.

**Result.** λ_c, λ_fold, and λ_cold each track D to varying degrees. Unlike α, which preserves topology to 10⁻⁴, D produces a systematic drift in λ_c with relative range on the order of 1.9% across the 20× sweep. λ_fold and λ_cold also track D. D1 (kinetic modulation) PASS — forward-sweep timesteps vary substantially with D. D2 (topology invariance) FAIL — the tensor fields are not invariant to within the 1% tolerance. D3 (baseline anchor at D = 0.5) PASS.

**Interpretation.** D is a mixed kinetic–topological coupling axis, not a pure kinetic axis. It does affect convergence (faster diffusion → faster relaxation → fewer timesteps), but it also couples into the spectral structure by modifying the effective balance between the Laplacian and the source/decay terms. The classification "mixed" is deliberate: D is neither the strong deformation axis (a/b, 84% amplitude) nor a pure kinetic axis (α, 10⁻⁴ topology drift). Its 1.9% topology shift is small but statistically resolvable and monotonic — a geometric perturbation axis rather than a deformation or convergence axis.

**Evidence source.** Test 5_19 JSON. D1 and D3 PASS; D2 FAIL.

---

## 5. The Jacobian of Operator Separability

### 5.1 The numerical Jacobian

Assembling the derivatives of λ_c with respect to each tested parameter from the probe results of Section 4:

```
J = ∂λ_c/∂(ξ, α, D, a/b) ≈ [ +1.4 × 10⁻⁸, −4.4 × 10⁻⁵, −5.9 × 10⁻⁴, +5.97 × 10⁻² ]
```

Each component is computed as the finite difference across the tested range, divided by the parameter range:

- **∂λ_c/∂ξ**: λ_c range 9.3 × 10⁻¹⁰ over Δξ = 0.065 → 1.4 × 10⁻⁸ (test 5_15)
- **∂λ_c/∂α**: λ_c range 1.99 × 10⁻⁵ over Δα = 0.45 (kernel-valid subset) → 4.4 × 10⁻⁵ (test 5_18)
- **∂λ_c/∂D**: λ_c range ~1.13 × 10⁻³ over ΔD = 1.9 → 5.9 × 10⁻⁴ (test 5_19)
- **∂λ_c/∂(a/b)**: λ_c range 4.97 × 10⁻² over Δ(a/b) = 0.833 → 5.97 × 10⁻² (test 5_17)

### 5.2 Dimensionless sensitivity

To compare axes with different physical dimensions, define the dimensionless sensitivity:

```
S_x ≡ (∂λ_c/∂x) · (Δx_range / λ_c,0)
```

where λ_c,0 = 0.05917 is the baseline λ_c value. This measures the fractional shift in λ_c produced by the full tested range of parameter x:

| Axis | S_x | Classification |
|---|---|---|
| ξ | 1.5 × 10⁻⁸ | null |
| α (kernel-valid subset) | 3.3 × 10⁻⁴ | convergence / solver field |
| D | 1.9 × 10⁻² | mixed kinetic–topological |
| a/b | 8.4 × 10⁻¹ | dominant deformation |

### 5.3 Seven orders of magnitude

The Jacobian components span from 10⁻⁸ to 10⁻² — seven orders of magnitude — with matched separation in the dimensionless sensitivities. This is the central empirical result of Paper B.

What this separation establishes:

1. **The four parameters map onto four operator roles.** They are not four redundant knobs on the same underlying effect; they occupy genuinely distinct positions in the operator structure.
2. **The four roles are ranked.** There is a single dominant deformation axis (a/b), a mixed secondary axis (D), a convergence axis (α), and a null axis (ξ). This is an empirical ranking, measured directly from the sweep data.
3. **Operator independence is demonstrated in practice.** The tested parameters behave as approximately independent operators across the four probe experiments; no parameter's effect was found to depend significantly on the value of another within the tested ranges.

What this separation does not establish:

1. **It is not a proof of formal operator orthogonality** in any Hilbert-space sense. The separation is numerical and empirical.
2. **It does not establish universality.** Only one PDE family and one grid resolution were tested; scaling behavior remains open (Section 8).
3. **It does not identify a conserved charge or a Lie algebra.** The Jacobian is a response measurement, not a symmetry analysis.

The Jacobian is the structural signature that Paper B claims. The subsequent sections are interpretations and criteria, layered on top of this measurement.

---

## 6. Three-Layer Ontology

The probe results support claims at three qualitatively different levels of scientific commitment. Collapsing these levels into a single narrative has been a recurring failure mode throughout the probe development. This section states the separation explicitly.

### Layer A — Spectral Invariant Layer (observed)

**Core objects.** The eigenstructure of the nonlinear substrate operator: λ_c, λ_fold, λ_cold.

**Measured quantities.** Sigmoid inflection, stiffness centroid, absorbing boundary — each directly extracted from sweep data with R² ≥ 0.978 on the sigmoid fits across all kernel-valid probes.

**Invariance domain.** Strong invariance under ξ (relative range ≤ 10⁻⁹), strong invariance under α (relative range ≤ 10⁻⁴ on kernel-valid subset), weak and resolvable drift under D (relative range ~1.9%), dominant dependence on a/b (relative range 84%).

**Commitment level.** Strong empirical. These are reproducible spectral properties of the PDE as implemented. They are the most defensible claims in the paper.

**Role in Paper B.** Foundational evidence. Defines the invariant backbone and establishes the existence of the λ_c system.

### Layer B — Effective Field Response Layer (partially validated)

**Core objects.** The response fields Φ(σ), J(x, y), Ĥ_s (the Taylor-expanded substrate Hamiltonian).

**Measured quantities.** Sigmoid-like Φ(σ) with inflection at λ_c, a stable-structured J field (even at floor magnitude, spatial structure is resolvable), finite and repeatable Ĥ_s behavior across kernel-valid runs.

**Invariance domain.** Partial invariance. Modulated by a (deformation), α (convergence effects), D (kinetic and partial topological). Relative ranges 5–40% depending on the observable and axis.

**Commitment level.** Moderate. This is effective-theory-level content. The suggestive phase-transition structure (sigmoid Φ) is present, but universality tests, critical slowing scaling, and grid-refinement confirmation have not been performed. This layer is presented as a conditional model, not a universality class.

**Role in Paper B.** Core model framework. Describes the response surface and supports the phase-transition narrative conditionally.

### Layer C — Topological Interpretation Layer (interpretive)

**Core objects.** The loop integral ∮ J · dΩ, the M ↔ σ inversion mapping, the topological corridor as a geometric construct.

**Measured quantities.** Loop structure stable across probes; quantization not observed; physical interpretation underdetermined.

**Invariance domain.** Interpretive invariance. The loop form is qualitatively stable but small relative-range variations exist and physical interpretation is not required by the data.

**Commitment level.** Weak. The topological overlay is consistent with the data but is not required by the data. It is retained as interpretation, not assertion.

**Role in Paper B.** Interpretive overlay. Provides a physical narrative and geometric meaning but is not load-bearing for the paper's primary validity.

### The separation principle

Three rules:

1. **Do not infer topological claims (Layer C) from effective field structure (Layer B).** The existence of a loop integral does not establish topological quantization.
2. **Do not infer phase universality (Layer B) from spectral invariance (Layer A).** The existence of a reproducible λ_c does not establish that the transition at λ_c is a phase transition in a universality class.
3. **Treat each layer as a distinct domain of legitimacy with its own invariance criteria.** A claim appropriate to Layer A is not automatically appropriate to Layer B or C.

The hierarchy of commitment runs from A (high commitment, what IS observed) through B (conditional commitment, what is modeled) to C (low commitment, what is interpreted). Paper B advances claims at each layer but explicitly at each layer's appropriate bar.

---

## 7. Hysteresis Mechanism by Elimination

The return sweep following each forward sweep exhibits a hysteresis loop with area H ≈ 0.05 at the baseline parameters. The return curve enters the cold-torus phase and remains there for substantially longer than the forward curve: on the return, the field does not re-emerge from σ = 0 until λ drops well below the forward transition point. The hysteresis area is real, reproducible, and present across all tested parameter values with ≤ 8% modulation.

Two mechanistic hypotheses were tested and eliminated.

**J-mediated fold bifurcation (eliminated by Section 4.1).** The ξ-plateau result demonstrates that the coupling term ξ·|J|²·(1 − σ) is numerically inactive under the current Ψ_bruce formulation. A fold bifurcation driven by σ-J back-reaction would require ξ to modulate the transition. It does not. Hysteresis cannot be J-mediated within this implementation.

**α-regularization memory (eliminated by Section 4.3).** If hysteresis were memory-driven, setting α = 0 (pure forward Euler, no step-to-step momentum) would eliminate or substantially reduce H. The α = 0 run produced H = 0.0541 — larger, not smaller, than the baseline H = 0.0499. Even restricted to the kernel-valid subset, the relative range of H across α is 8%, far below the 30% threshold that would mark α as a meaningful control. Hysteresis is not memory-driven.

By elimination of the two tested mechanisms, H is consistent with absorbing-state asymmetry of the cold-torus phase. The field in the cold region is at σ = 0 identically. With |J|² at floor-level under current Ψ_bruce, the PDE has no coupling mechanism that can restart σ from zero. The return sweep therefore cannot recover the forward trajectory until λ drops well below the point at which the forward sweep's existing-field initial condition allowed continued support.

This mechanism is presented as **consistent with the data, by elimination of tested alternatives**. A direct test — for example, initializing the return sweep from a seeded perturbation within the cold region and measuring whether the field restarts — has not been performed in this paper. It is a primary task for Paper B v2.0.

---

## 8. Falsification Criteria

Paper B's claims are structured so that specific measurements would break them. These criteria are stated explicitly.

**F1 — Spectral invariance of λ_fold and λ_cold under ξ, α.** *Claim:* λ_fold and λ_cold are exactly invariant under ξ across [0.005, 0.070] and under α on the kernel-valid subset. *Falsifier:* any statistically significant drift > 10⁻³ relative range in λ_fold or λ_cold under either axis.

**F2 — Linear a/b scaling of λ_c.** *Claim:* λ_c = κ_spectral · (a/b) with κ_spectral = 0.0592 ± drift < 1% across a ∈ [0.08, 0.18]. *Falsifier:* non-monotonic a/b → λ_c mapping, or Pearson correlation < 0.98 under an expanded a range.

**F3 — Kinetic-topological decoupling of α.** *Claim:* α modulates convergence cost (fwd_total_steps varies > 100%) but preserves λ_c to < 10⁻³ relative range on the kernel-valid subset. *Falsifier:* correlation of λ_c with α at |r| > 0.2 on the kernel-valid subset.

**F4 — Grid-refinement invariance.** *Claim (implicit throughout Paper B, not yet tested):* the four-field state tensor values are grid-independent in the continuum limit. *Falsifier:* λ_c, λ_fold, λ_cold, or H exhibiting systematic drift larger than Δx² as the grid is refined from 64² through 224² to 512².

**F5 — ξ-null boundary.** *Claim:* ξ is numerically null in [0.005, 0.070] under the current Ψ_bruce formulation. *Falsifier:* any alternative Ψ_bruce formulation that retains the same dimensional structure but produces ξ-sensitive λ_c shifts would demonstrate the nullity is specific to the implementation, not a property of the theory.

F4 is the most important. It has not been tested. Paper B acknowledges that all claims at Layer A and Layer B are conditional on grid-refinement behavior, which is a task for Paper B v2.0.

---

## 9. Relationship to Paper A

BCM Paper A (Tully-Fisher, Zenodo DOI 10.5281/zenodo.19680280) and Paper B operate at different layers of the BCM framework.

**Paper A layer.** Astrophysical observation. Galactic rotation curves, Tully-Fisher relation, SPARC 175-galaxy sample validation. Claims a dark-matter-free fit at macroscopic scales.

**Paper B layer.** Substrate PDE operator structure. Controlled numerical experiments on a specific field-theoretic equation. Claims an operator decomposition and a Jacobian of separability.

Neither paper contains the other. Paper A does not require Paper B's operator decomposition to establish its empirical fit. Paper B does not invoke Paper A's astrophysical data to establish its PDE structure. Each has its own evidence and its own commitment level.

The papers are connected at the BCM framework level: the substrate wave concept that Paper A fits at macroscopic scales is the same substrate whose PDE operator Paper B probes numerically. But that connection is framework-level, not evidentiary. Reviewers of Paper B can evaluate it entirely on the basis of Sections 2 through 8 of this paper without reference to Paper A's astrophysical content.

---

## 10. Open Questions and Path to Paper B v2.0

Five directions are explicitly open at the close of Paper B v1.0:

1. **Grid-refinement scaling.** All claims depend on the 128² grid. Repeating the full four-axis perturbation protocol at 64², 224², and 512² would either confirm continuum-limit behavior or identify grid-dependent artifacts.

2. **Alternative Ψ_bruce formulations.** The current Ψ_bruce definition (smoothed local RMS of σ fluctuations) renders ξ numerically null. Alternative formulations — pump-geometry-driven, |∇σ|-driven, or σ(1−σ)-weighted — could produce ξ-active coupling and change the entire operator map. This is a theoretical question and a top priority for v2.0.

3. **Joint (a, b) scan.** Only a was varied in Paper B v1.0, with b held fixed. The linear law λ_c = κ_spectral · (a/b) predicts that varying b with a fixed should produce matching λ_c shifts. This has not been tested.

4. **Initial-condition perturbation class.** All probes used the same initial σ field (Gaussian blob with fixed seed). Different initial conditions — different blob widths, off-center blobs, multiple blobs, non-Gaussian profiles — could reveal whether the four-field tensor is truly an operator property or partly a property of the sampled initial-condition class.

5. **Direct test of the absorbing-state hysteresis mechanism.** Section 7 eliminates J-coupling and α-memory by elimination. A direct test would seed the return sweep with a small field perturbation in the cold region and measure whether the field restarts. If it does not, absorbing-state asymmetry is directly confirmed. If it does, a different mechanism is at work.

Paper B v2.0 will address these five in order.

---

## Appendix A — PDE Discretization

The substrate PDE is solved by explicit forward Euler on a 128×128 uniform grid with zero-flux (Neumann) boundary conditions:

```
σ[i,j,n+1] = σ[i,j,n]
           + dt · ( D·L[i,j] + a·σ[i,j,n] − b·σ[i,j,n]²
                   − λ·σ[i,j,n] + ξ·|J|²[i,j]·(1 − σ[i,j,n]) )
           + α · ( σ[i,j,n] − σ[i,j,n−1] )

σ[i,j,n+1] = max(σ[i,j,n+1], 0)
```

where L[i,j] is the five-point Laplacian stencil:

```
L[i,j] = σ[i−1,j] + σ[i+1,j] + σ[i,j−1] + σ[i,j+1] − 4·σ[i,j]
```

with zero-flux boundary conditions applied by restricting the stencil to interior points.

The positivity clamp `max(σ, 0)` is applied after each step. The timestep dt = 0.05 and D = 0.5 give a diffusion stability number dt·D/Δx² = 0.1 (Δx = 1), well below the forward-Euler stability threshold of 0.5.

Convergence at a given λ is declared when:

```
‖σ_{n+1} − σ_n‖₂ / ‖σ_n‖₂ < 10⁻⁶
```

for 20 consecutive timesteps, with a hard cap of 5000 timesteps per λ.

---

## Appendix B — Classifier v2 Pseudocode

```
INPUT:  forward_sweep = list of (λ, Φ(λ), n_steps) for 30 log-spaced λ values
PARAMETER: cold_phi_low_frac = 0.01, cold_stay_dead_steps = 2

# Step 1: locate cold-torus entry
max_phi = max(Φ over sweep)
low_threshold = cold_phi_low_frac · max_phi
lambda_cold_entry = None
for i in 0..len(sweep)-1:
    if Φ[i] ≤ low_threshold:
        still_dead = True
        for k in 0..cold_stay_dead_steps-1:
            if i+k >= len(sweep): break
            if Φ[i+k] > low_threshold:
                still_dead = False
                break
        if still_dead:
            lambda_cold_entry = λ[i]
            active_indices = 0..i-1
            break

if lambda_cold_entry is None:
    active_indices = 0..len(sweep)-1

# Step 2: fit sigmoid on active region
active_λ = [λ[i] for i in active_indices]
active_Φ = [Φ[i] for i in active_indices]
(λ_c, k, R²) = fit_sigmoid(active_λ, active_Φ)

# Extract stiffness centroid
λ_fold = λ[argmax(n_steps over active_indices)]

OUTPUT: (λ_c, λ_fold, lambda_cold_entry, sigmoid_R²)
```

Hysteresis area H is computed on the active region only, via trapezoidal integration of |Φ_forward(λ) − Φ_return(λ)| over λ < lambda_cold_entry.

---

## Appendix C — Jacobian Derivative Computation

Each Jacobian component is a finite-difference estimate from the probe's extreme points in the tested range:

```
∂λ_c/∂x ≈ [λ_c(x_max) − λ_c(x_min)] / [x_max − x_min]
```

Source data:

**∂λ_c/∂ξ.** Test 5_15, six ξ values spanning [0.005, 0.070]. λ_c(0.005) and λ_c(0.070) both read 0.05916579125480137 to 10 decimal places. The full six-point relative range is 9.3 × 10⁻¹⁰; treating this as the effective Δλ_c gives ∂λ_c/∂ξ ≈ 1.4 × 10⁻⁸. The derivative sign is indeterminate at this precision level.

**∂λ_c/∂α.** Test 5_18. On the kernel-valid subset α ∈ {0.5, 0.8, 0.95}: λ_c range [0.05916357, 0.05918350], Δα = 0.45, giving |∂λ_c/∂α| ≈ 4.4 × 10⁻⁵. Full-range estimate including kernel-invalid α ∈ {0.0, 0.2} gives ≈ 1.0 × 10⁻⁴; the kernel-valid subset is used as the inference value.

**∂λ_c/∂D.** Test 5_19. Δλ_c ≈ 1.13 × 10⁻³ over ΔD = 1.9 (from D = 0.1 to D = 2.0), giving |∂λ_c/∂D| ≈ 5.9 × 10⁻⁴.

**∂λ_c/∂(a/b).** Test 5_17. λ_c(a/b = 0.667) = 0.0393, λ_c(a/b = 1.5) = 0.0890, Δλ_c = 4.97 × 10⁻², Δ(a/b) = 0.833, giving ∂λ_c/∂(a/b) = 5.97 × 10⁻². Pearson correlation 0.99999 across all five points confirms linearity.

Bootstrap resampling of the five- and six-point data would reduce uncertainty in these derivatives; that analysis is deferred to Paper B v2.0.

---

## Appendix D — Reproduction Protocol

**Environment.** Windows 10 / 11, Python 3.11, Anaconda terminal, conda environment. All probes run without GPU acceleration; the `BCM_SOLVER=gpu` environment variable was set during development but the test probes use pure NumPy and are unaffected.

**Dependencies.** numpy, scipy.ndimage (uniform_filter, gaussian_filter), scipy.optimize (curve_fit). No specialized libraries.

**Reproduction sequence.** Each probe is a self-contained Python script. To reproduce the full Paper B v1.0 data set:

```
cd <working_directory>
python BCM_v26_Paper_B_Probes_5_14.py    # ≈ 90 seconds
python BCM_v26_Paper_B_Probes_5_15.py    # ≈ 10–20 minutes (six ξ values)
python BCM_v26_Paper_B_Probes_5_16.py    # < 1 second (post-processor on 5_15)
python BCM_v26_Paper_B_Probes_5_17.py    # ≈ 85 seconds (five a values)
python BCM_v26_Paper_B_Probes_5_18.py    # ≈ 195 seconds (five α values)
python BCM_v26_Paper_B_Probes_5_19.py    # ≈ 90–200 seconds (five D values)
```

Each script writes a timestamped JSON to `<working_directory>/data/paper_results/`. All numerical results quoted in this paper are extracted directly from these JSON files.

**Kernel validation.** Each probe runs a Taylor kernel validation as its first step (pumps off, comparison against analytical σ_eq = (a − λ)/b at non-degenerate λ values). The per-probe JSON records `kernel_validation.max_deviation` and `kernel_validation.faithful`. Reproduction should confirm `faithful = true` on all runs except α ∈ {0.0, 0.2} in test 5_18, which are expected kernel-invalid due to insufficient convergence at low momentum.

---

## Appendix E — Tool Use Disclosure and Primacy

**Primacy.** All theoretical concepts presented in this paper — including the BCM framework itself, the Anchor Equation, Brucetron and the Ψ_bruce field, the four-field state tensor decomposition, the classifier v2 protocol, the three-layer ontology, the Jacobian of operator separability, and every originating insight — belong solely to Stephen Justin Burdick Sr. Stephen Burdick is the sole discoverer and theoretical originator.

**AI tool use.** During the development of the probe protocol and this paper, AI assistants served in two operational roles at the direction of the author:

- **Code executor.** Generation of Python probe scripts matching specifications set by the author. No theoretical content was contributed by AI in this role; scripts implement protocols and gate structures defined by the author.

- **Adversarial reviewer.** Stress-testing of draft framings, identification of load-bearing assumptions, surfacing of vulnerabilities that the author then addressed. Review output was evaluated and either incorporated or rejected by the author.

No AI system originated theoretical concepts, control parameter identification, operator classifications, falsification criteria, or publication decisions. The role of AI in this paper is strictly analogous to the role of a computational workstation and a copy-editor.

---

*End of BCM Paper B v1.0.*

*Version 1.0 · 22 April 2026 · Emerald Entities LLC — GIBUSH Systems*
