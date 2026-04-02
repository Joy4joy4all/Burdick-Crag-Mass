<meta name="google-site-verification" content="8SWX9Vuczy9DAWDE" />


# SUBSTRATE SOLVER
**Stephen Justin Burdick, 2026 — Emerald Entities LLC**

Multi-layer damped wave substrate solver with SPARC galaxy rotation curve validation.

## Theory

Space is not a container. Space is a maintenance cost. The substrate is a pre-existing
2D medium that becomes detectable ("space") only when continuously agitated by wave energy.
Gravity emerges as the cumulative memory (Σ) of substrate agitation, producing a potential
well that maps to Newtonian gravity in the near field and screens at distance.

## Directory Structure

```
SUBSTRATE_SOLVER/
├── core/
│   ├── substrate_solver.py    # Multi-layer wave engine
│   └── sparc_ingest.py        # SPARC data loader
├── solvers/
│   ├── run_sparc.py           # Galaxy rotation curve runner
│   └── run_layers.py          # Layer scaling tests (4→42→72)
├── data/
│   ├── sparc_raw/             # Place SPARC .dat files here
│   ├── sparc_processed/       # Intermediate outputs
│   └── results/               # Solver results (JSON)
├── analysis/                  # Post-processing scripts
└── docs/                      # Thesis, doctrine, notes
```

## Quick Start

### 1. Self-test (no data needed)
```bash
cd core
python substrate_solver.py
```

### 2. Layer scaling test
```bash
cd solvers
python run_layers.py --layers 4 6 12 --grid 64
```

### 3. Full layer sweep (overnight)
```bash
python run_layers.py --layers 4 6 12 42 72 --grid 128 --settle 25000
```

### 4. SPARC galaxy test
```bash
# First: download SPARC rotation curves from
# https://zenodo.org/record/16284118
# Place _rotmod.dat files in data/sparc_raw/

python solvers/run_sparc.py --galaxy NGC2403
python solvers/run_sparc.py --max-galaxies 5
```

## Requirements

- Python 3.8+
- NumPy
- (Optional) SciPy for source field interpolation

## Key Parameters

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| grid      |        | 128     | Spatial resolution |
| layers    |        | 6       | Entangled substrate layers |
| lam       | λ      | 0.1     | Decay rate (maintenance cost) |
| gamma     | γ      | 0.05    | Wave damping |
| entangle  |        | 0.02    | Inter-layer coupling |
| c_wave    | C      | 1.0     | Wave speed |
| settle    |        | 20000   | Steps before measurement |
| measure   |        | 5000    | Measurement window |

## Progression (Gaussian source, control λ→0)

| Engine            | Ψ~Φ correlation |
|-------------------|-----------------|
| Diffusion 1L/64   | +0.8377         |
| Wave 1L/64        | +0.8701         |
| Wave 1L/128       | +0.9408         |
| Wave 4L/128       | +0.9539         |
| Wave 6L/64        | +0.9617         |
| Target            | > +0.9500       |

## License

(c) 2026 Stephen J. Burdick Sr. / Emerald Entities LLC — All Rights Reserved.
