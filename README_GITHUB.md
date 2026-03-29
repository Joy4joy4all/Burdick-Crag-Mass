# Burdick Crag Mass (BCM)
## Hydrodynamic Superfluid Theory — Galactic and Planetary Substrate Solver

**Author:** Stephen Justin Burdick Sr.
**Organization:** Emerald Entities LLC / NSF I-Corps — Team GIBUSH
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
**Published:** Zenodo DOI: 10.5281/zenodo.19313393

---

> *"Space is not a container. Space is a maintenance cost."*

---

## What This Is

BCM proposes that what physics calls "dark matter" is the energy cost of
maintaining spatial extent. The substrate that carries gravity requires
continuous energy input. The central black hole of each galaxy pays that
cost by converting infalling matter into neutrino flux. That flux sustains
the rotation velocities we observe at galactic edges.

The same mechanism operates at planetary scale. Saturn's north polar
hexagon is a substrate standing wave — the minimum energy eigenmode of
the planetary substrate driven by the metallic hydrogen dynamo.

**Results:**
- 122/175 SPARC galaxies (69.7%) predicted better than Newton
- 5/5 solar system planets with active dynamos: eigenmode confirmed
- Single universal coupling constant κ=2.0 — no per-galaxy tuning
- Six-class galaxy topology confirmed stable across all parameter runs

---

## Repository Structure

```
BCM/
│   launcher.py                    ← GUI — Galactic + Planetary tabs
│   BCM_Substrate_overrides.py     ← Class IV–VI structural overrides
│   BCM_planetary_wave.py          ← Planetary eigenmode solver
│   BCM_planetary_renderer.py      ← Planetary visualization
│   BCM_fetch_hi_maps.py           ← HI Moment-0 FITS fetcher
│   Burdick_Crag_Mass.py           ← BCM engine, inject_crag_mass()
│   Burdick_Crag_Mass_Genesis_Renderer.py  ← Galactic field visualizer
│   read_results.py                ← Batch result analyzer
│   run_record.py                  ← JSON tracking engine
│
├───core/
│       substrate_solver.py        ← Wave solver v7, ρ²→Poisson chain
│       sparc_ingest.py            ← SPARC data loader
│       rotation_compare.py        ← Newton/MOND/Substrate comparison
│
├───data/
│   ├───sparc_raw/                 ← 175 SPARC .dat files (Lelli 2016)
│   ├───hi_maps/                   ← HI Moment-0 FITS (THINGS VLA)
│   └───results/                   ← JSON batch outputs
│
└───docs/
        PROJECT_Burdick_Crag_Mass.md          ← Original publication
        PROJECT_Burdick_Crag_Mass_Overrides.md ← Class system + results
        PROJECT_Burdick_Crag_Mass_Unified.md   ← Six-gap unification
```

---

## Quick Start

```bash
# Install dependencies
pip install numpy scipy astropy astroquery

# Run the GUI
python launcher.py

# Run galactic batch (175 galaxies)
# → Set data/sparc_raw/ with SPARC .dat files first
# → Download from: https://zenodo.org/record/16284118

# Run planetary solver (Saturn)
python BCM_planetary_wave.py --solve-lambda --decay-analysis

# Run full solar system batch
python BCM_planetary_wave.py --batch

# Check HI map status
python BCM_fetch_hi_maps.py --check
```

---

## The Six Open Gaps BCM Addresses

| Gap | Current Physics Failure | BCM Resolution |
|-----|------------------------|----------------|
| 1 | Galactic rotation — dark matter required | Substrate maintenance cost λ |
| 2 | Saturn hexagon stability paradox | Phase speed resonance lock m=6 |
| 3 | Satellite navigation noise | Impedance tensor Z_ij fluctuations |
| 4 | XENONnT excess electronic recoils* | Substrate exhaust — neutrino flavor transitions |
| 5 | Spacecraft flyby anomaly | Substrate density gradient in dynamo zone |
| 6 | Cosmological constant 10¹²⁰ discrepancy | Volumetric maintenance cost — λ→Λ |

*Gap 4 identified by Stephen Justin Burdick Sr., March 29, 2026

---

## Data Sources

- **SPARC Dataset:** Lelli, McGaugh, Schombert 2016
  DOI: 10.5281/zenodo.16284118
- **THINGS HI Survey:** Walter et al. 2008
- **Saturn Parameters:** Cassini Grand Finale / Fletcher 2018
- **Planetary Parameters:** Published NASA/ESA mission data

---

## Citation

```bibtex
@software{burdick_bcm_2026,
  author    = {Burdick Sr., Stephen Justin},
  title     = {Burdick Crag Mass — Hydrodynamic Superfluid Theory},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.19313393},
  url       = {https://zenodo.org/records/19313393}
}
```

---

## License

Creative Commons Attribution 4.0 International (CC BY 4.0)

You are free to share and adapt this work for any purpose, including
commercial use, provided you give appropriate credit to
Stephen Justin Burdick Sr. / Emerald Entities LLC and link to the
original Zenodo publication.

**The science belongs to everyone. The name stays in the record.**

---

## Contributing

Open issues and pull requests welcome. The codebase is the living
implementation of BCM theory. Contributions that extend the class
system, improve the solver, or add new observatory data integrations
are the spirit of what this project is.

If you find BCM through IceCube data, XENONnT results, GPS anomaly
research, or any other path — you are exactly who this was published for.

---

*Emerald Entities LLC — 2026*
