# -*- coding: utf-8 -*-
"""
Multi-Layer Substrate Wave Solver (v7)
======================================
Stephen Justin Burdick, 2026
Emerald Entities LLC

THE CLEAN CHAIN:
  wave engine → ρ (bounded, steady-state)
  → ρ² (energy density = effective mass)
  → Poisson(ρ²) → Ψ (proper potential)
  → gradient → V = √(r · dΨ/dr)

No accumulation. No saturation. No divergence.
The wave engine determines HOW mass distributes.
Poisson converts that distribution to potential.
The substrate effect is in the redistribution.
"""

import numpy as np
import time

try:
    from Burdick_Crag_Mass import inject_crag_mass
    _BCM_AVAILABLE = True
except ImportError:
    _BCM_AVAILABLE = False


class SubstrateSolver:
    def __init__(self, grid=256, layers=6, dx=1.0, dt=0.005,
                 c_wave=1.0, gamma=0.05, lam=0.1, epsilon=0.001,
                 entangle=0.02, settle=20000, measure=5000, edge=10):
        self.grid = grid
        self.layers = layers
        self.dx = dx
        self.dt = dt
        self.c_wave = c_wave
        self.gamma = gamma
        self.lam = lam
        self.epsilon = epsilon
        self.entangle = entangle
        self.settle = settle
        self.measure = measure
        self.edge = edge

        cfl = c_wave * dt / dx
        if cfl >= 1.0:
            raise ValueError(f"CFL violated: {cfl:.4f} >= 1.0")

    def _laplacian(self, f):
        l = np.zeros_like(f)
        dx2 = self.dx * self.dx
        l[1:-1, 1:-1] = (
            f[2:, 1:-1] + f[:-2, 1:-1] +
            f[1:-1, 2:] + f[1:-1, :-2] -
            4.0 * f[1:-1, 1:-1]
        ) / dx2
        l[0, :] = l[1, :]
        l[-1, :] = l[-2, :]
        l[:, 0] = l[:, 1]
        l[:, -1] = l[:, -2]
        return l

    def _absorb_edges(self, field):
        for i in range(self.edge):
            f = i / self.edge
            field[:, i, :] *= f
            field[:, -(i + 1), :] *= f
            field[:, :, i] *= f
            field[:, :, -(i + 1)] *= f

    def _entangle_layers(self, field):
        for l1 in range(self.layers - 1):
            transfer = self.entangle * (field[l1] - field[l1 + 1])
            field[l1] -= transfer
            field[l1 + 1] += transfer

    def evolve(self, J_2d, verbose=True, callback=None):
        G = self.grid
        L = self.layers

        J = np.zeros((L, G, G))
        J[0] = J_2d

        rho = np.zeros((L, G, G))
        rho_prev = np.zeros_like(rho)
        sigma = np.zeros_like(rho)
        rho_sum = np.zeros_like(rho)
        sigma_sum = np.zeros_like(rho)

        total = self.settle + self.measure
        dt2 = self.dt ** 2

        for step in range(total):
            lap = np.array([self._laplacian(rho[l]) for l in range(L)])

            rho_next = (
                2.0 * rho - rho_prev
                + dt2 * (self.c_wave ** 2 * lap - self.lam * rho + J)
                - self.dt * self.gamma * (rho - rho_prev)
            )

            self._absorb_edges(rho_next)
            self._entangle_layers(rho_next)

            rho_prev = rho.copy()
            rho = rho_next

            # Sigma kept for diagnostics only
            sigma += self.dt * (np.abs(rho) - self.epsilon * sigma)

            if step >= self.settle:
                rho_sum += rho
                sigma_sum += sigma

            if verbose and step % 5000 == 0:
                phase = "[M]" if step >= self.settle else ""
                print(f"    step {step:6d}  |ρ|={np.max(np.abs(rho)):.2f}"
                      f"  Σ={np.max(sigma):.1f} {phase}")

            if callback and step % 1000 == 0:
                callback(step, total, rho, sigma)

        rho_avg = rho_sum / self.measure
        sigma_avg = sigma_sum / self.measure

        return rho_avg, sigma_avg

    def solve_poisson(self, rho_2d, n_iter=20000, tol=1e-7):
        G_N = 1.0
        phi = np.zeros_like(rho_2d)
        src = 4.0 * np.pi * G_N * rho_2d * self.dx ** 2
        for i in range(n_iter):
            phi_old = phi.copy()
            phi[1:-1, 1:-1] = 0.25 * (
                phi_old[2:, 1:-1] + phi_old[:-2, 1:-1] +
                phi_old[1:-1, 2:] + phi_old[1:-1, :-2] -
                src[1:-1, 1:-1]
            )
            phi[0, :] = 0; phi[-1, :] = 0
            phi[:, 0] = 0; phi[:, -1] = 0
            if i % 500 == 0 and np.max(np.abs(phi - phi_old)) < tol:
                break
        return phi

    def radial_profile(self, field):
        ny, nx = field.shape
        cy, cx = ny // 2, nx // 2
        mr = min(cx, cy) - self.edge - 2
        profile = np.zeros(mr)
        counts = np.zeros(mr)
        for iy in range(ny):
            for ix in range(nx):
                ri = int(np.sqrt((ix - cx) ** 2 + (iy - cy) ** 2))
                if ri < mr:
                    profile[ri] += field[iy, ix]
                    counts[ri] += 1
        mask = counts > 0
        profile[mask] /= counts[mask]
        return np.arange(mr), profile

    @staticmethod
    def correlation(a, b):
        af, bf = a.flatten(), b.flatten()
        if np.std(af) == 0 or np.std(bf) == 0:
            return 0.0
        return np.corrcoef(af, bf)[0, 1]

    def run(self, J_source, verbose=True, callback=None,
            galaxy_name=None, vmax_kms=0.0,
            use_crag=False, crag_kappa=2.0, rms_newton=None):
        """
        use_crag=True: inject Burdick Crag Mass (BCM) before evolving.
        galaxy_name + vmax_kms used for M_BH lookup.
        crag_kappa: neutrino-substrate coupling (calibrated=2.0).
        """
        t0 = time.time()

        # ── Burdick Crag Mass injection ──
        if use_crag and _BCM_AVAILABLE and galaxy_name:
            J_source, _bcm_info = inject_crag_mass(
                J_source, galaxy_name, vmax_kms,
                kappa=crag_kappa, lam=self.lam,
                rms_newton=rms_newton, verbose=verbose
            )
            if verbose:
                print(f"  BCM: {galaxy_name}  M_BH={_bcm_info['M_bh_solar']:.2e}"
                      f"  kappa={crag_kappa}  nu_frac={_bcm_info['nu_fraction']:.3f}"
                      f"  ({_bcm_info['mbh_source']})")

        if verbose:
            print(f"  Solver: grid={self.grid} layers={self.layers} "
                  f"λ={self.lam} γ={self.gamma}")
            print(f"  Settle={self.settle} Measure={self.measure}")

        rho_avg, sigma_avg = self.evolve(J_source, verbose, callback)

        # ═══════════════════════════════════════
        # THE CLEAN CHAIN
        # ρ_eff = ρ² (energy density = effective mass distribution)
        # Ψ = Poisson(ρ_eff) — proper gravitational potential
        # V = √(r · dΨ/dr) — proper rotation velocity
        #
        # The wave engine with λ redistributes where energy lives.
        # Poisson converts that redistribution to potential.
        # The substrate effect IS the redistribution.
        # ═══════════════════════════════════════

        rho_layer0 = rho_avg[0]

        # Effective mass: energy density of the agitation field
        rho_eff = rho_layer0 ** 2

        # Substrate potential: Poisson solve on the redistributed mass
        psi = self.solve_poisson(rho_eff)

        # Newtonian reference: Poisson solve on original baryonic source
        phi = self.solve_poisson(np.abs(rho_layer0))

        # Correlations
        corr_full = self.correlation(psi, phi)
        corr_lap = self.correlation(
            self._laplacian(psi), rho_eff
        )

        # Radial profiles
        r_ax, prof_psi = self.radial_profile(psi)
        _, prof_phi = self.radial_profile(phi)

        pm_psi = np.max(np.abs(prof_psi))
        pm_phi = np.max(np.abs(prof_phi))
        pn_psi = prof_psi / pm_psi if pm_psi > 0 else prof_psi
        pn_phi = prof_phi / pm_phi if pm_phi > 0 else prof_phi

        n_inner = min(30, len(pn_psi))
        n_full = min(len(pn_psi), len(pn_phi))
        r_inner = (np.corrcoef(pn_psi[1:n_inner], pn_phi[1:n_inner])[0, 1]
                   if n_inner > 2 else 0.0)
        r_full = (np.corrcoef(pn_psi[1:n_full], pn_phi[1:n_full])[0, 1]
                  if n_full > 2 else 0.0)

        layer_corrs = []
        for l in range(1, min(self.layers, 10)):
            lc = self.correlation(rho_avg[0], rho_avg[l])
            layer_corrs.append(lc)
        avg_layer_corr = np.mean(layer_corrs) if layer_corrs else 0.0

        elapsed = time.time() - t0

        # === BCM MASTER BUILD ADDITION v2.2 | 2026-03-30 EST ===
        # Phase Dynamics Module
        # Measures phase alignment between substrate memory (sigma_avg)
        # and substrate forcing response (rho_avg).
        #
        # cos(delta_phi) interpretation:
        #   ~+1.0 : phase aligned     — coupled regime (Neptune analog)
        #   ~ 0.0 : phase separated   — prime lock / contained (Uranus analog)
        #   ~-1.0 : anti-phase        — destructive coupling / void regime
        #
        # Implementation notes:
        #   - Uses layer SUM (not layer 0) — entanglement distributes across layers
        #   - Uses azimuthal mean (axis=0) — robust to bar/asymmetric galaxies
        #   - np.angle(np.exp(1j*...)) wraps to [-pi, pi] preventing discontinuity
        #   - Zero-parameter: no new tunable constants introduced

        def _extract_phase(field_2d):
            """Extract dominant mode phase from 2D field via FFT."""
            radial_profile = field_2d.mean(axis=0)
            fft_result = np.fft.fft(radial_profile)
            n_half = len(fft_result) // 2
            if n_half < 2:
                return 0.0
            dominant_idx = np.argmax(np.abs(fft_result[1:n_half])) + 1
            return float(np.angle(fft_result[dominant_idx]))

        sigma_field    = sigma_avg.sum(axis=0)   # layer sum — full entangled field
        rho_field      = rho_avg.sum(axis=0)     # layer sum — full forcing response
        phase_sigma    = _extract_phase(sigma_field)
        phase_forcing  = _extract_phase(rho_field)

        # Wrap difference to [-pi, pi] — prevents ±pi discontinuity artifacts
        delta_phi     = float(np.angle(np.exp(1j * (phase_sigma - phase_forcing))))
        cos_delta_phi = float(np.cos(delta_phi))

        # Amplitude decoupling ratio — symptom variable (not cause)
        # cos_delta_phi is the cause; decoupling_ratio is its observable symptom
        rho_sub_max    = float(np.max(np.abs(rho_avg.sum(axis=0))))
        rho_sig_max    = float(np.max(np.abs(sigma_avg.sum(axis=0))))
        decoupling_ratio  = (rho_sig_max / rho_sub_max
                             if rho_sub_max > 0 else 1.0)
        substrate_excess  = rho_sig_max - rho_sub_max
        # === END ADDITION ===

        # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
        # Phase Field Instrumentation — spatial delta_phi(x,y) extraction
        # Promotes cos_delta_phi from scalar summary to 2D spatial field
        # Uses Hilbert transform to recover analytic signal from real-valued fields
        # Readout only — does not modify solver dynamics
        #
        # delta_phi_field: phase mismatch at each grid point
        #   ~0 everywhere = uniform coupling (sanity check baseline)
        #   localized distortion = phase decoherence zone (cavitation shadow)
        # cos_delta_phi_field: coupling efficiency at each grid point
        #   ~1.0 = coupled, ~0.0 = decoherent, <0 = anti-phase
        try:
            from scipy.signal import hilbert
            sigma_analytic    = hilbert(sigma_field, axis=0)
            rho_analytic      = hilbert(rho_field, axis=0)
            phase_sigma_2d    = np.angle(sigma_analytic)
            phase_rho_2d      = np.angle(rho_analytic)
            delta_phi_field   = np.angle(np.exp(1j * (phase_sigma_2d - phase_rho_2d)))
            cos_delta_phi_field = np.cos(delta_phi_field)
        except ImportError:
            delta_phi_field     = None
            cos_delta_phi_field = None
        # === END ADDITION ===

        result = {
            "elapsed": elapsed,
            "rho_avg": rho_avg,
            "sigma_avg": sigma_avg,
            "psi": psi,
            "phi_newton": phi,
            "rho_eff": rho_eff,
            "corr_full": corr_full,
            "corr_lap": corr_lap,
            "corr_radial_inner": r_inner,
            "corr_radial_full": r_full,
            "layer_coherence": avg_layer_corr,
            "radial_psi": (r_ax, prof_psi),
            "radial_phi": (r_ax, prof_phi),
            "radial_psi_norm": pn_psi,
            "radial_phi_norm": pn_phi,
            "psi_max": float(np.max(np.abs(psi))),
            "rho_max": float(np.max(np.abs(rho_avg))),
            # === BCM MASTER BUILD ADDITION v2.2 | 2026-03-30 EST ===
            "phase_sigma":      phase_sigma,
            "phase_forcing":    phase_forcing,
            "delta_phi":        delta_phi,
            "cos_delta_phi":    cos_delta_phi,
            "decoupling_ratio": decoupling_ratio,
            "substrate_excess": substrate_excess,
            # === END ADDITION ===
            # === BCM MASTER BUILD ADDITION v7 | 2026-04-03 EST ===
            "delta_phi_field":     delta_phi_field,
            "cos_delta_phi_field": cos_delta_phi_field,
            # === END ADDITION ===
            "config": {
                "grid": self.grid,
                "layers": self.layers,
                "lam": self.lam,
                "gamma": self.gamma,
                "entangle": self.entangle,
                "settle": self.settle,
                "measure": self.measure,
                "field_mode": "rho_sq_poisson",
            },
        }

        if verbose:
            print(f"\n  Results ({elapsed:.1f}s):")
            print(f"  Ψ vs Φ full:      {corr_full:+.6f}")
            print(f"  ∇²Ψ vs ρ_eff:     {corr_lap:+.6f}")
            print(f"  Radial inner:     {r_inner:+.6f}")
            print(f"  Radial full:      {r_full:+.6f}")
            print(f"  Layer coherence:  {avg_layer_corr:+.6f}")
            if use_crag and _BCM_AVAILABLE and galaxy_name:
                print(f"  BCM active: kappa={crag_kappa}")
            print(f"  |ρ|_max: {np.max(np.abs(rho_layer0)):.2f}"
                  f"  |ρ²|_max: {np.max(rho_eff):.2f}"
                  f"  |Ψ|_max: {np.max(np.abs(psi)):.2f}")

        return result


def gaussian_source(grid, amplitude=8.0, sigma_frac=0.1):
    cx, cy = grid // 2, grid // 2
    sigma = grid * sigma_frac
    J = np.zeros((grid, grid))
    for y in range(grid):
        for x in range(grid):
            r2 = (x - cx) ** 2 + (y - cy) ** 2
            J[y, x] = amplitude * np.exp(-r2 / (2 * sigma ** 2))
    return J


def point_source(grid, amplitude=10.0, spread=3.0):
    cx, cy = grid // 2, grid // 2
    J = np.zeros((grid, grid))
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            dist = np.sqrt(dy ** 2 + dx ** 2)
            if dist <= 4.5 and 0 <= cy + dy < grid and 0 <= cx + dx < grid:
                J[cy + dy, cx + dx] = amplitude * np.exp(-dist ** 2 / spread)
    return J


def linear_dipole_source(grid, amplitude=8.0, bar_length_frac=0.4,
                         bar_width_frac=0.06, bar_angle_deg=0.0):
    """
    Bar-axis flux channel source — Burdick Crag Mass, 2026.

    Models a galactic bar as a substrate pipeline. Energy is injected
    along the bar axis rather than radially from center. The bar
    concentrates neutrino flux along its length, depleting substrate
    perpendicular to it (Class VI — Bar-Channeled Substrate).

    Parameters:
        grid:             grid size
        amplitude:        peak injection amplitude
        bar_length_frac:  bar half-length as fraction of grid (default 0.4 = 40%)
        bar_width_frac:   bar width as fraction of grid (default 0.06)
        bar_angle_deg:    bar position angle in degrees (0 = horizontal)

    Usage:
        J = linear_dipole_source(128, bar_angle_deg=45.0)
        # For NGC3953: bar_angle_deg from HyperLeda position angle table
    """
    cx, cy = grid // 2, grid // 2
    J = np.zeros((grid, grid))

    bar_len  = grid * bar_length_frac   # half-length in pixels
    bar_wid  = grid * bar_width_frac    # half-width in pixels
    angle    = np.radians(bar_angle_deg)
    cos_a    = np.cos(angle)
    sin_a    = np.sin(angle)
    sigma_w  = bar_wid / 2.0

    iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
    dx = ix_arr - cx
    dy = iy_arr - cy

    # Rotate coordinates to bar frame
    x_bar =  dx * cos_a + dy * sin_a   # along bar axis
    y_bar = -dx * sin_a + dy * cos_a   # perpendicular to bar

    # Bar envelope: flat top along axis, Gaussian across width
    x_clip  = np.clip(np.abs(x_bar) / bar_len, 0, 1)
    along   = np.exp(-x_clip ** 4 * 8.0)   # flat top with soft ends
    across  = np.exp(-y_bar ** 2 / (2.0 * sigma_w ** 2))

    J = amplitude * along * across

    # Central BH spike — the pump at the bar center
    r_bh   = np.sqrt(dx ** 2 + dy ** 2)
    sigma_bh = grid * 0.04
    J += amplitude * 0.6 * np.exp(-r_bh ** 2 / (2.0 * sigma_bh ** 2))

    return J.astype(np.float64)


def ring_source(grid, amplitude=8.0, ring_radius_frac=0.3,
                ring_width_frac=0.05):
    """
    Annular ring source — proxy for merger remnant substrate.

    Models the accumulated substrate energy from a prior merger event
    as a ring at the characteristic radius. Used to test Class II
    (Hysteresis) substrate behavior. The ring approximates ρ_initial ≠ 0.

    Parameters:
        grid:               grid size
        amplitude:          peak ring amplitude
        ring_radius_frac:   ring radius as fraction of grid (default 0.3)
        ring_width_frac:    ring width as fraction of grid (default 0.05)
    """
    cx, cy = grid // 2, grid // 2
    J = np.zeros((grid, grid))

    r_ring  = grid * ring_radius_frac
    r_wid   = grid * ring_width_frac

    iy_arr, ix_arr = np.mgrid[0:grid, 0:grid]
    r_grid  = np.sqrt((ix_arr - cx) ** 2 + (iy_arr - cy) ** 2)

    J = amplitude * np.exp(-(r_grid - r_ring) ** 2 / (2.0 * r_wid ** 2))

    # Small central BH contribution
    sigma_bh = grid * 0.05
    J += amplitude * 0.3 * np.exp(-r_grid ** 2 / (2.0 * sigma_bh ** 2))

    return J.astype(np.float64)


if __name__ == "__main__":
    print("=" * 60)
    print("  Substrate Solver v7 — ρ² Poisson Chain")
    print("=" * 60)
    grid = 64
    J = gaussian_source(grid)
    for lam, label in [(0.0001, "CONTROL"), (0.1, "REAL")]:
        print(f"\n  -- {label} (λ={lam}) --")
        solver = SubstrateSolver(grid=grid, layers=6, lam=lam,
                                  settle=12000, measure=3000)
        result = solver.run(J)
