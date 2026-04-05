# Burdick Crag Mass (BCM) — Substrate Wave Solver

**Stephen Justin Burdick Sr., 2026 — Emerald Entities LLC — GIBUSH Systems**

Multi-layer damped wave substrate solver with Phase-Lock Coherence Law,
topological selection rule (Phi_reach), amplitude stress testing to 420:1,
binary black hole inspiral analog (GW150914), and rotation curve validation
across 175 SPARC galaxies, 8 solar system planets, 13 stars, 5
phase-mapped binary systems, and 1 binary black hole merger.

**Zenodo DOI:** [10.5281/zenodo.19251192](https://doi.org/10.5281/zenodo.19251192)

---

## Theory

In this model, space is not a container — space is a maintenance cost.
The substrate is a proposed pre-existing 2D medium that becomes
detectable ("space") only when continuously agitated by wave energy.
Gravity emerges as the cumulative memory of substrate agitation,
producing a potential well that maps to Newtonian gravity in the near
field and screens at distance. The dark matter signal is reinterpreted
as the neutrino maintenance budget of the spatial substrate, funded
continuously by the central SMBH.

All physical interpretations presented here are model-based and
informed by outputs of the BCM solver framework. They should not
be taken as established physical law.

No per-object tuning parameters. All simulations use identical global
parameters (lambda=0.1 baseline, kappa=2.0, grid=256, layers=6)
without object-specific fitting or optimization. Initial conditions
vary by system geometry, but solver parameters remain fixed across
all runs.

---

## Reproducibility Guarantee

This repository is designed to produce deterministic outputs given
fixed global parameters, fixed grid resolution, and fixed system
selection. No per-object tuning is required.

---

## Quick Start

Primary entry point: `launcher.py` (recommended for all users).
Module-level scripts are for advanced or batch execution.

### 1. Clone the repository

```bash
git clone https://github.com/Joy4joy4all/Burdick-Crag-Mass.git
cd Burdick-Crag-Mass
```

### 2. Create a clean Python environment

**Conda (recommended — matches development environment):**

```bash
conda create -n bcm python=3.11
conda activate bcm
```

**Alternative (venv):**

```bash
python -m venv venv
```

- Windows: `venv\Scripts\activate`
- macOS / Linux: `source venv/bin/activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install numpy scipy Pillow matplotlib
```

Full dependency list:

| Package | Required | Tested version | Used for |
|---------|----------|----------------|----------|
| numpy   | Yes      | 2.4.1          | All numerical computation |
| scipy   | Yes      | 1.16.3         | Bessel functions, Hilbert transform |
| Pillow  | Yes      | 11.3.0         | Renderer field visualization |
| matplotlib | Yes   | 3.10.6         | Genesis Renderer, diagnostic plots |
| tkinter | Built-in | tk 8.6.15      | GUI launcher and renderer windows |
| astropy | Optional | 7.2.0          | HI moment-0 map fetching |
| astroquery | Optional | 0.4.11      | SkyView/VLA archive queries |

Development environment: Python 3.11.13, conda, Windows 10/11.

### System dependency (tkinter)

tkinter is required for the GUI but is not installable via pip.

- **Ubuntu/Debian:** `sudo apt-get install python3-tk`
- **macOS:** included with Python from python.org
- **Windows:** included by default in the standard Python installer

### 4. Run the launcher

```bash
python launcher.py
```

This opens the BCM GUI with tabs for galactic rotation curves (175 SPARC
galaxies), planetary substrate modes (8 planets), and stellar/binary
substrate bridge (13 stars, 3 binary systems).

If the GUI does not open:

- Ensure tkinter is installed (see System dependency above)
- Verify no import errors appear in the terminal
- Run `python launcher.py` and check console logs for error messages

### 5. Run a binary substrate bridge

From the launcher Stellar tab:

1. Select a binary pair from the dropdown (Alpha_Cen, HR_1099, or Spica)
2. Set grid size (192 recommended for binary runs)
3. Click "Run Binary Substrate Bridge"
4. A live wave propagation window opens showing the solver in real time
5. When complete, click the Renderer button to view the topology

### 6. Run the stellar wave solver standalone

```bash
python BCM_stellar_wave.py --star Sun
python BCM_stellar_wave.py --star HR_1099
python BCM_stellar_wave.py --batch
python BCM_stellar_wave.py --batch --solve-lambda
```

Output JSON files are written to `data/results/`.

### 7. Run substrate colonization sweep (v8)

Forward sweep — increase dominant pump, measure colonization:

```bash
python BCM_colonization_sweep.py --pair Spica --phase 0.0
```

Reverse sweep — increase weaker pump, find revival boundary:

```bash
python BCM_colonization_sweep_reverse.py --pair Spica --phase 0.0
```

### 8. Run tunnel time-series (v8)

Three-point bridge instrumentation — measures substrate flow
direction and turnstile timing at L1:

```bash
python BCM_tunnel_timeseries.py --pair Spica --phase 0.0
python BCM_tunnel_timeseries.py --pair HR_1099 --phase 0.5
python BCM_tunnel_timeseries.py --pair Alpha_Cen --phase 0.5
```

Output: 31 data points per run (every 1000 solver steps) with
rho amplitude, sigma amplitude, cos(delta_phi), curl, and sigma
drift at three points along the bridge axis (mid_A, L1, mid_B).

### 9. Self-test (no external data needed)

Run from the repository root directory:

```bash
python -m core.substrate_solver
```

Runs a Gaussian source control test confirming the solver chain.

---

## Minimal Reproducibility Test

To confirm the system is working:

1. Run `python launcher.py`
2. Load a binary system (e.g., Alpha Centauri)
3. Verify: two distinct source fields initialize, a continuous field
   connects them, and the output visualization appears without errors
4. Check that the output indicates a coherent bridge at L1 and that
   cos(delta_phi) approaches +1.0 at the L1 region

If those conditions are met, the pipeline is functioning.

---

## Expected Behavior

- GUI window opens with multiple tabs (Galactic, Planetary, Stellar)
- Binary systems load from registry JSON
- Running a simulation produces:
  - field evolution visualization in a live window
  - output logs in terminal
  - saved results in `data/results/`

---

## Directory Structure

```
Burdick-Crag-Mass/
├── launcher.py                    # GUI entry point / orchestrator
├── BCM_stellar_wave.py            # Stellar wave solver (13 stars)
├── BCM_stellar_overrides.py       # Binary pair registry + dual-pump builder
├── BCM_stellar_renderer.py        # Stellar/binary visualization
├── BCM_colonization_sweep.py      # v8: forward amplitude sweep
├── BCM_colonization_sweep_reverse.py  # v8: reverse amplitude sweep
├── BCM_tunnel_timeseries.py       # v8: 3-point tunnel time-series
├── BCM_cavitation_sweep.py        # v9: throat bandwidth sweep
├── BCM_tcf_analyzer.py            # v9: time-cost function analyzer
├── BCM_3d_renderer.py             # v9: cinematic 3D renderer
├── BCM_phase_lock.py              # v10: phase-lock coherence analyzer
├── BCM_inspiral_sweep.py          # v11: binary black hole inspiral
├── BCM_planetary_wave.py          # Planetary substrate solver (8 planets)
├── BCM_planetary_renderer.py      # Planetary visualization
├── Burdick_Crag_Mass.py           # Crag Mass injection (SMBH neutrino flux)
├── Burdick_Crag_Mass_Genesis_Renderer.py  # Genesis galactic renderer
├── rotation_compare.py            # Four-way rotation curve comparison
├── core/
│   ├── substrate_solver.py        # Multi-layer wave engine
│   ├── sparc_ingest.py            # SPARC data loader
│   └── rotation_compare.py        # Core rotation comparison
├── data/
│   ├── sparc_raw/                 # Place SPARC .dat files here
│   ├── sparc_processed/           # Intermediate outputs
│   └── results/                   # Solver results (JSON)
│       └── BCM_stellar_registry.json  # 13-star parameter registry
└── docs/                          # Session records, notes
```

---

## Key Parameters

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| grid      |        | 256     | Spatial resolution (production standard) |
| layers    |        | 6       | Entangled substrate layers |
| lam       | lambda | 0.1     | Decay rate (maintenance cost) |
| gamma     |        | 0.05    | Wave damping |
| entangle  |        | 0.02    | Inter-layer coupling |
| c_wave    | C      | 1.0     | Wave speed |
| settle    |        | 20000   | Steps before measurement |
| measure   |        | 5000    | Measurement window |
| kappa     |        | 2.0     | Neutrino-substrate coupling (Crag Mass) |

---

## BCM Classification System

Six physically distinct substrate interaction states:

| Class | Name | Description |
|-------|------|-------------|
| I     | Transport-Dominated | Full substrate coupling |
| II    | Residual/Hysteresis | Merger remnant substrate |
| III   | Ground State | Minimal substrate expression |
| IV    | Declining Substrate | Outer rim depletion |
| V-A   | Ram Pressure | Asymmetric lambda field |
| V-B   | Substrate Theft | Multi-body SMBH competition |
| VI    | Barred Substrate Pipe | Bar-channeled flux |

---

## Binary Substrate Bridge (v7)

Three binary systems implemented with dual-pump solver:

| System | Class | Separation | Result |
|--------|-------|------------|--------|
| Alpha Cen A+B | I — Mode-Matched | 23.4 AU | Coherent bridge |
| HR 1099 | VI — Tidal Bar Channel | 0.05 AU | Coherent bridge |
| Spica A+B | IV — High-Energy | 0.12 AU | Coherent bridge |

Tidal Hamiltonian: H_tidal(m) = (v_A + v_tidal - Omega*R_tach/m)^2

HR 1099 confirmed: standard Alfven predicted m=12, tidal predicts m=2,
observed m=2.

---

## Substrate Colonization and Tunnel Time-Series (v8)

v8 extends the binary bridge from steady-state to time-resolved
analysis. Five systems tested with three-point tunnel instrumentation.

### Colonization Boundary

A provisional colonization transition is observed near amplitude
ratio 2.86:1 in the Spica periastron configuration. Transition is
smooth, not a snap. Further systems required to determine universality.

### Five-System Comparison

| System | Ratio | Phase | Sync | sig_drift | B alive? |
|--------|-------|-------|------|-----------|----------|
| Spica periastron | 8.4:1 | 0.0 | No | 3727 | No |
| Alpha Cen | 3.5:1 | 0.5 | No | 2257 | No |
| Spica mean | 8.4:1 | 0.5 | No | 1250 | No |
| HR 1099 phase=0.5 | 14:1 | 0.5 | Yes | 1198 | Yes |
| HR 1099 phase=0.0 | 14:1 | 0.0 | Yes | 1198 | Yes |

### Three Governors of Colonization (observed ranking)

1. **Tidal synchronization** (strongest): HR 1099 at 14:1 has the
   lowest drift and is the only system where B pushes back.
2. **Separation** (strong): Spica drains 3x less at mean vs periastron.
3. **Amplitude ratio** (weakest alone): ratio without timing loses
   to timing without ratio.

---

## Time-Cost Function and Cavitation Regimes (v9)

v9 prices the flows measured in v8 and discovers three throat
bandwidth regimes.

### Three Regimes

| Regime | Width range | sig_drift | I_B | Governor |
|--------|-------------|-----------|-----|----------|
| Throttle | 0.005–0.015 | Decreasing | Rising | Pipe-limited |
| Default | 0.06 | 3493 | 0.0 | Balanced |
| Saturation | 0.06–1.0 | ~3583 | 0.0 | Pump-limited |

Narrowing the corridor protects the weaker star (orifice effect).
Widening adds less than 3% more drain — pump-limited.
Grid=256 validation confirms pattern is resolution-independent.

### Time-Cost Function

| System | Rate/k | Tax above baseline |
|--------|--------|--------------------|
| Spica periastron | 118.83 | +80.10 |
| Alpha Cen | 71.69 | +32.96 |
| Spica mean | 40.58 | +1.85 |
| HR 1099 (baseline) | 38.73 | 0.00 |

### External Validation

HR 1099: no mass transfer for 70-80 Myr (Fekel 1983), consistent
with I_B > 0 resistant prediction. Spica: Struve-Sahade effect
confirms one-way drain spectroscopically.

### Run commands (v9)

```bash
python BCM_cavitation_sweep.py --pair Spica --phase 0.0
python BCM_tcf_analyzer.py --compare
python BCM_3d_renderer.py --pair Spica --phase 0.0
```

---

## Phase-Lock Coherence Law (v10)

v10 establishes the Burdick Phase-Lock Coherence Law through
amplitude stress testing and spatial phase-field topology analysis.

### The Law

Synchronization maximizes coherent reach. Coherent reach determines
flow regime. Flow regime determines survival.

### Amplitude Stress Test

Solver maintains cos_delta_phi = +1.000000 from 8.4:1 through 336:1
(12 runs at grid=256). First hairline fracture (0.999999) at 420:1.
The solver is mathematically ideal across all physically meaningful
ratios — no known binary exceeds ~100:1.

### Phi_reach — Topological Selection Rule

Phi_reach measures the fraction of ultra-coherent pixels
(cos_delta_phi > 0.999999) reachable from the dominant pump.

| System | Ratio | Sync | Phi_reach | I_B | Status |
|--------|-------|------|-----------|-----|--------|
| HR 1099 | 14:1 | Yes | 31.6% | +210.8 | RESISTANT |
| Spica mean | 8.4:1 | No | 28.3% | 0.0 | DRAIN |
| Spica peri | 8.4:1 | No | 25.7% | 0.0 | DRAIN |
| Alpha Cen | 3.5:1 | No | 18.3% | 0.0 | DRAIN |

Phi_reach reproduces the ordering of four independent metrics
(sig_drift, I_B, TCF rate, Psi~Phi) without additional parameters.

### Run commands (v10)

```bash
python BCM_phase_lock.py --pair Spica --phase 0.0
python BCM_phase_lock.py --compare
```

---

## Combined Stress Validation and Binary Black Hole Inspiral (v11)

v11 validates the Phase-Lock Coherence Law under combined stress
and extends the framework to binary black hole merger analogs.

### Combined Stress Test

Amplitude (amp_A=500, ratio 210:1) through narrowing corridor
(0.02 to 0.002). First real phase crack: cos_delta_phi dropped
to 0.9997 — three orders of magnitude below unity. Orifice
protection survived: I_B rose from 0 to 223.6 under 40x natural
pump pressure. The law holds under combined stress.

### Binary Black Hole Inspiral — GW150914 Analog

Two near-equal pumps (50:43, ratio 1.16:1, analog to GW150914
observed 1.24:1) swept from wide separation to merger in 15 steps.
Three unprecedented events in the framework's history:

1. **Phase snap:** cos_delta_phi = -0.991 at sep=0.336.
   First anti-phase reading ever. The substrate briefly fought
   itself — possible analog of the ISCO transition.

2. **Negative I_B:** foreclosure at sep=0.155. B loses sovereign
   independence. The substrate dismantles B's territory.

3. **Exact zero sig_drift:** at sep=0.087. Two pumps become one.
   Merger is topological unification, not collision.

Three phases match GW150914 structure: inspiral (I_B rising),
merger (I_B negative, foreclosure), ringdown (sig_drift=0,
single pump settles). rho_L1 rises continuously from 0.9 to
627.3, mapping to the rising strain amplitude of the chirp.

### Run commands (v11)

```bash
python BCM_cavitation_sweep.py --pair Spica --phase 0.0 --amp-A 500 --width-start 0.02 --width-end 0.002 --width-steps 6
python BCM_inspiral_sweep.py --grid 128 --steps 15
```

---

## Troubleshooting

- **Module import errors**: ensure you are running inside the virtual environment
- **Missing dependencies**: install any additional packages reported by Python
- **File not found errors**: confirm working directory is the repo root
- **Rendering issues**: check Pillow installation; renderer falls back to
  canvas rectangles if PIL is unavailable
- **scipy not found**: install with `pip install scipy` — required for
  Bessel functions and Hilbert transform

---

## Definitions

- **Substrate:** The modeled underlying 2D medium in the BCM framework.
- **Colonization:** A state where one source dominates substrate flow
  in a binary system, suppressing the secondary's independent contribution.
- **sig_drift:** Time-accumulated imbalance in sigma (memory field)
  amplitude between mid_A and mid_B measurement points.
- **I_B:** Independence metric (sig_midB - sig_L1). Near zero indicates
  drain regime; positive indicates active backflow (resistance).
- **Tachocline:** The interface between radiative and convective zones
  in a star, where the substrate pump (J_ind) operates.
- **Phi_reach:** Fraction of ultra-coherent pixels (cos_delta_phi >
  0.999999) reachable from the dominant pump via flood-fill
  connectivity. Topological selection rule for regime discrimination.
- **Foreclosure:** State where I_B becomes negative — the secondary
  pump has lost sovereign substrate independence and its territory
  is being actively dismantled by the primary.
- **Phase snap:** A transient anti-phase event (cos_delta_phi < 0)
  during binary inspiral, possibly analogous to the innermost
  stable circular orbit (ISCO) transition.

---

## Falsifiability Criteria

The framework would be challenged if:

- Simulations fail to reproduce rotation curves under fixed parameters
  across the 175-galaxy SPARC dataset
- Binary bridge coherence does not emerge under identical configurations
  on independent hardware
- Tunnel diagnostics show non-reproducible drift behavior across
  repeated runs with identical inputs
- Synchronized binaries do not exhibit reduced drift compared to
  unsynchronized systems at comparable ratios
- Phi_reach ordering does not reproduce sig_drift, I_B, and TCF
  rankings across new binary systems not yet tested
- The amplitude stress boundary (420:1) shifts significantly under
  different solver parameters (lambda, gamma, entangle)

---

## References

- Burdick, S. J. Sr. 2026, BCM v1-v9, Zenodo 10.5281/zenodo.19251192 — Burdick Crag Mass framework
- Lelli, F., McGaugh, S. S., & Schombert, J. M. 2016, AJ, 152, 157 — SPARC rotation curve dataset
- Walter, F., Brinks, E., de Blok, W. J. G., et al. 2008, AJ, 136, 2563 — THINGS VLA HI Moment-0
- Pourbaix, D. & Boffin, H. M. J. 2016 — Alpha Centauri dynamical masses
- Kervella, P. et al. 2016 — Alpha Centauri interferometric orbit
- Herbison-Evans, D. et al. 1971, MNRAS, 151 — Spica binary orbit
- Harrington, D. et al. 2016, A&A, 590 — Spica line-profile variations, apsidal motion
- Tkachenko, A. et al. 2016, MNRAS, 458 — Spica stellar modelling, apsidal constant
- Odell, A. P. 1974, ApJ, 192 — Spica internal structure constant discrepancy
- Fekel, F. C. 1983, ApJ, 268 — HR 1099 spectroscopic binary, mass transfer prediction
- Donati, J.-F. et al. 1999, MNRAS, 302 — HR 1099 magnetic cycles, period oscillation
- Berdyugina, S. V. & Tuominen, I. 1998, A&A, 336 — RS CVn active longitudes

---

## License

Copyright (C) 2026 Stephen Justin Burdick Sr., Emerald Entities LLC.
Creative Commons Attribution Non Commercial No Derivatives 4.0 International (CC BY-NC-ND 4.0).
