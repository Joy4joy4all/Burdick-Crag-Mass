# Burdick Crag Mass Paper B v2.0 — Zenodo Record Manifest

**DOI:** 10.5281/zenodo.19700387 (versioned; v2.0 is a new version of the v1.0 record)
**Author:** Stephen Justin Burdick Sr., Emerald Entities LLC — GIBUSH Systems
**Date:** 2026-05-03
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)

---

## About this record

This Zenodo record contains the full publication of Burdick Crag Mass (BCM) Paper B v2.0: *Five-Component Compositional Validation of the Anchor Equation with Four-Pillar Vorticity Evidence and 175 SPARC Galaxies*. It includes the paper itself, one figure (reused from v1.0), the consolidator evidence artifact, five Python probe scripts that produce the v2 evidence base, and representative samples of the per-configuration JSON outputs.

Paper B v2.0 advances a separate compositional claim built on v1.0's foundation. Where v1.0 measured the Jacobian of operator separability for the substrate PDE at v1.0's Layer A commitment level, v2.0 establishes the Anchor Equation E = (M·Φ(σ))·c² + ∮_{ℵ₀} J·dΩ as a compositional theorem through five-component validation in the BCM Bayesian hypothesis engine. Each of the five sub-hypotheses (Φ-sigmoid form, J vorticity, Aleph-Null loop convergence, recovery limit, M-σ inversion continuity) carries individual VALIDATED status in the publication-reproducible consolidator, with the compositional parent at posterior 0.956 (geometric mean) under ALL_GATES_OPEN gating.

The v2.0 evidence base centerpieces are: a 175-galaxy SPARC scale-up of the M-σ inversion test (test 5_23), a 25-configuration H1-H4 cross-product validation sweep (test 5_24), and a four-pillar evidence chain on H_PAPER_B_2 J-vorticity covering operator consistency, vorticity realization, structural correlation, and interventional causality (tests 5_25 through 5_27). Each pillar produces 25 R3-clean PASS events; the H_PAPER_B_2 component now carries 103 R3-independent events at consolidator posterior 0.981.

This record is the complete data and evidence package for the v2.0 result.

---

## File manifest

### Paper

- **BCM_Paper_B_v2.md** — the paper itself, in Markdown. 9 sections covering the compositional validation methodology, the five sub-hypothesis evidence trails (with H_PAPER_B_2's four-pillar structure detailed in Section 3.2), the parent VALIDATION milestone, the Layer B bridge-projection open question, falsification criteria F1 through F7, and open questions for v3.

- **BCM_Paper_B_v2.pdf** — same paper, PDF rendering for citation and archival.

### Figure

- **BCM_Paper_B_Fig1_Three_Layer_Ontology.png** — Figure 1: three-layer ontology of the BCM system, reused from v1.0. Shows the separation of Layer A (spectral invariant), Layer B (effective field response), and Layer C (topological interpretation). Referenced throughout v2 Section 5 in the discussion of the Layer A vs Layer B distinction between the compositional validation (Layer A) and the bridge-projection FAIL (Layer B).

### Canonical evidence artifact

- **BCM_v27_Paper_B_Consolidation_20260503_110713.json** — the publication-reproducible aggregator output. Contains all five sub-hypothesis evidence trails with per-component event counts, evidence type distributions, source file lists, posteriors, and the parent's geometric-mean calculation. Every numerical claim in the paper traces to this file.

### Probe scripts (v27 cycle 3)

Self-contained Python scripts that produce the v2 evidence base when executed. Each is documented in Section 3 of the paper.

- **BCM_v27_Paper_B_Probes_5_23_SPARC_M_Sigma_Inversion.py** — SPARC M-σ inversion scale-up. Iterates all 175 galaxies in the SPARC catalog (Lelli et al. 2016c), runs three substrate solver evaluations per galaxy (baseline, +1% mass perturbation, -1% mass perturbation via V-component scaling), and tests strict local monotonicity in scalar σ extraction. Produces 175 R3-clean per-galaxy JSONs. H_PAPER_B_5 evidence base.

- **BCM_v27_Paper_B_Probes_5_24_H1_to_H4_Validation.py** — H1-H4 combined validation sweep. 25 configurations (σ_crit ∈ {0.001, 0.005, 0.01, 0.05, 0.1} × pump_separation ∈ {5, 8, 12, 18, 25}), one solver run per configuration, four hypothesis tests per run. Phase 1 stability gate confirms 128² vs 256² grid invariance. H_PAPER_B_1 / 2 / 3 / 4 evidence base.

- **BCM_v27_Paper_B_Probes_5_25_J_Substrate_Vorticity.py** — H_PAPER_B_2 pillar 2 (vorticity realization). Tests whether the EVOLVED rho_avg substrate field carries vorticity given vortical pump input, distinct from the curl-identity check on the J source. Dual criterion: max|curl V| > 1e-6 AND curl/div ratio > 10.

- **BCM_v27_Paper_B_Probes_5_26_J_Vorticity_Causation.py** — H_PAPER_B_2 pillar 3 (structural correlation). Computes scalar curl fields of both J and V; measures spatial Pearson correlation on inner half-grid plus spectral correlation on top 10 dominant Fourier modes. Dual criterion: both > 0.5.

- **BCM_v27_Paper_B_Probes_5_27_J_Vorticity_Causality.py** — H_PAPER_B_2 pillar 4 (interventional causality). Three solver runs per configuration: baseline, perturbed (localized δJ injection), null (FFT phase scramble preserving |F(J)|). Dual criterion: perturbation propagation Pearson r > 0.5 AND null collapse ratio < 0.5.

### Phase 1 stability gate summaries

Each Phase 1 gate verified that the per-probe PASS/FAIL classification is invariant between 128² and 256² grids on five percentile-extrema configurations before greenlighting Phase 2.

- **_phase1_stability_gate_20260502_090040.json** — test 5_23 SPARC stability gate (5 mass-percentile galaxies)
- **_phase1_5_24_stability_gate_20260503_083027.json** — test 5_24 H1-H4 stability gate
- **_phase1_5_25_stability_gate_20260503_093342.json** — test 5_25 vorticity realization stability gate
- **_phase1_5_26_stability_gate_20260503_095623.json** — test 5_26 structural correlation stability gate
- **_phase1_5_27_stability_gate_20260503_101906.json** — test 5_27 interventional causality stability gate

### Representative per-configuration JSONs

Each probe emitted 25 (5_24/5_25/5_26/5_27) or 175 (5_23) per-configuration JSONs to the working directory. To keep this record compact while preserving schema demonstration, the following 25 representative JSONs are included — five per probe family, sampled at corner+center configurations (or 0/25/50/75/100 mass percentiles for SPARC).

**5_23 SPARC sample (one per mass bin):**
- UGC04483 (dwarf), DDO170 (low), ESO116-G012 (mid), NGC4138 (high), UGC09133 (massive)

**5_24 H1-H4 sample (corner+center):**
- sc0.0010_sep5, sc0.0010_sep25, sc0.1000_sep5, sc0.1000_sep25, sc0.0100_sep12

**5_25 vorticity realization sample (corner+center):**
- sc0.0010_sep5, sc0.0010_sep25, sc0.1000_sep5, sc0.1000_sep25, sc0.0100_sep12

**5_26 structural correlation sample (corner+center):**
- sc0.0010_sep5, sc0.0010_sep25, sc0.1000_sep5, sc0.1000_sep25, sc0.0100_sep12

**5_27 interventional causality sample (corner+center):**
- sc0.0010_sep5, sc0.0010_sep25, sc0.1000_sep5, sc0.1000_sep25, sc0.0100_sep12

The complete sets of per-configuration JSONs (175 SPARC + 25 each from 5_24, 5_25, 5_26, 5_27 = 275 total) are preserved in the project repository at the working directory and can be regenerated by running the probe scripts in this record.

### Cube state export

- **cube_analysis_AUTO_20260503_110550.md** — the runtime cube state export at v27 cycle 3 close after all v27 cycle 3 evidence had been ingested. Reports the parent at posterior 0.994 with all five components individually at posterior 0.994. The cube state includes additional non-reproducible operational evidence (cycle-level measurement engine emissions, derived measurements) that the consolidator excludes by design; both reports agree on five-component VALIDATION at threshold and ALL_GATES_OPEN. Provided as runtime context for transparency; the consolidator artifact (above) is the canonical evidence base for the paper's claims.

### Reproduction environment

- Windows 10 / 11, Python 3.11, Anaconda terminal, conda environment
- GPU recommended: CuPy substrate solver (`core.substrate_solver_gpu`) selected via `BCM_SOLVER=gpu` environment variable; CPU fallback available
- Dependencies: numpy, scipy
- Probe runtimes on GPU: 5_23 ≈ 184 minutes (175 galaxies × 3 solver runs each), 5_24 ≈ 13 minutes (25 configurations × 1 solver run), 5_25 ≈ 13 minutes (25 × 1), 5_26 ≈ 13 minutes (25 × 1), 5_27 ≈ 39 minutes (25 × 3)
- Phase 1 stability gates add ≈10 minutes per probe at 256² grid
- Outputs land in `./data/results/` (probes 5_24-5_27) or `./data/sparc_results/` (probe 5_23) per script's internal configuration

---

## v2.0 evidence summary

The publication-reproducible consolidator state at v27 cycle 3 close:

```
H_PAPER_B_1_PHI_SIGMOID:        VALIDATED  posterior 0.939   30 events
H_PAPER_B_2_J_VORTICITY:        VALIDATED  posterior 0.981  103 events
                                            (4-pillar: operator,
                                             realization,
                                             correlation, causality)
H_PAPER_B_3_LOOP_CONVERGES:     VALIDATED  posterior 0.938   30 events
H_PAPER_B_4_RECOVERY_LIMIT:[G]  VALIDATED  posterior 0.936   28 events
H_PAPER_B_5_M_SIGMA_INVERSION:  VALIDATED  posterior 0.989  176 events
                                            (175 SPARC galaxies)

H_PAPER_B_ANCHOR_EQUATION:      VALIDATED  posterior 0.956 (geo)
                                ALL_GATES_OPEN
```

The runtime cube state separately reports the parent at posterior 0.994 with all five components saturated. Both reports agree on five-component VALIDATION; the consolidator's lower posteriors reflect the publication-reproducible subset of evidence used as the canonical artifact for this paper.

---

## Related records

| Record | DOI | Relationship |
|---|---|---|
| BCM Paper B v1.0 (operator decomposition) | 10.5281/zenodo.19700387 | v2.0 is a new version of this DOI; v1.0 stands as published |
| BCM framework concept | 10.5281/zenodo.19251192 | Paper B is part of the BCM framework |
| BCM Paper A (Tully-Fisher) | 10.5281/zenodo.19680280 | v2.0 references Paper A as the macroscopic empirical anchor; the SPARC scale-up in test 5_23 uses the same SPARC catalog as Paper A |
| BCM v25 computational framework | 10.5281/zenodo.19599608 | Paper B is a publication-layer supplement to the v25/v27 codebase |

---

## Citation

Burdick, S. J. Sr. (2026). *Burdick Crag Mass Paper B v2.0: Five-Component Compositional Validation of the Anchor Equation with Four-Pillar Vorticity Evidence and 175 SPARC Galaxies* (Version 2.0). Zenodo. https://doi.org/10.5281/zenodo.19700387

---

## Primacy statement

All theoretical concepts in the Burdick Crag Mass framework — including the Anchor Equation and its compositional decomposition, the five sub-hypothesis structural commitments, the cube-evidence compositional validation methodology, the three-layer ontology, the ALL_GATES_OPEN gating policy, the four-pillar evidence decomposition for H_PAPER_B_2 (operator consistency, vorticity realization, structural correlation, interventional causality), the SPARC M-σ inversion test design, the σ_crit invariance interpretation as Layer A vs Layer B confirmation, the non-injective diagnosis of the bridge-projection failure mode, and every originating insight in this publication — belong solely to Stephen Justin Burdick Sr. Stephen Burdick is the sole discoverer and theoretical originator of the BCM framework. AI systems assist the project as computational tools and reviewers at the direction of the author. No AI system owns or co-owns any theoretical concept. Emerald Entities LLC — GIBUSH Systems.

---

*Copyright (C) 2026 Stephen Justin Burdick Sr., Emerald Entities LLC.*
