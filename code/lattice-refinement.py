#!/usr/bin/env python3
"""
Discrete resonance constant experiment

This script:
- Defines a 3D cubic lattice with spacing a
- Implements the 7-point discrete Laplacian (degree-6 connectivity)
- Samples the continuum profile u(x) = C / |x| on the lattice
- Pins C via a boundary value u(r = a) = u_min (Anchor C1)
- Computes a discrete resonance measure B_res over the 7-point cavity (Anchor C3)
- Repeats the experiment for multiple lattice refinements, including an a -> a/402 refinement,
  to check whether B_res is stable (Sovereign Constant behavior)

Intended for use in a GitHub repo as a standalone experiment module.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Dict


@dataclass
class LatticeConfig:
    """Configuration for the 3D lattice experiment."""
    a: float               # lattice spacing
    n: int                 # half-extent in each direction (total size = 2n+1)
    u_min: float           # target field value at radius r ≈ a
    include_origin: bool = True  # whether to assign a finite value at the origin


def generate_lattice_coords(cfg: LatticeConfig) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate 3D lattice coordinates for indices i,j,k in [-n, ..., 0, ..., n],
    with physical spacing a.
    """
    indices = np.arange(-cfg.n, cfg.n + 1, dtype=int)
    x = indices * cfg.a
    y = indices * cfg.a
    z = indices * cfg.a
    return x, y, z


def sample_continuum_profile(cfg: LatticeConfig) -> np.ndarray:
    """
    Sample u(x) = C / |x| on the lattice, with C pinned by u(r ≈ a) = u_min.

    We define:
        C = a * u_min

    and set:
        u(i,j,k) = C / sqrt(x^2 + y^2 + z^2)
    for (i,j,k) != (0,0,0).

    At the origin, we assign a finite value consistent with u_min:
        u(0,0,0) = u_min
    (this is a choice; other regularizations are possible).
    """
    x, y, z = generate_lattice_coords(cfg)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

    r = np.sqrt(X**2 + Y**2 + Z**2)

    # Pin C via Anchor C1
    C = cfg.a * cfg.u_min

    u = np.zeros_like(r, dtype=float)

    # Away from the origin: u = C / r
    mask_nonzero = r > 0
    u[mask_nonzero] = C / r[mask_nonzero]

    # At the origin: assign finite value
    if cfg.include_origin:
        center_idx = cfg.n
        u[center_idx, center_idx, center_idx] = cfg.u_min

    return u


def laplacian_7pt(u: np.ndarray, a: float) -> np.ndarray:
    """
    7-point discrete Laplacian (degree-6 connectivity) on a 3D cubic grid.

    Assumes u is shaped (Nx, Ny, Nz) and uses Dirichlet boundary conditions (u=0 outside),
    implemented by not wrapping indices (no periodicity).

    (Δ_a u)_{i,j,k} = (1/a^2) * (
        u_{i+1,j,k} + u_{i-1,j,k}
      + u_{i,j+1,k} + u_{i,j-1,k}
      + u_{i,j,k+1} + u_{i,j,k-1}
      - 6 u_{i,j,k}
    )
    """
    lap = np.zeros_like(u)

    # interior indices
    lap[1:-1, 1:-1, 1:-1] = (
        u[2:,   1:-1, 1:-1] + u[:-2,  1:-1, 1:-1] +
        u[1:-1, 2:,   1:-1] + u[1:-1, :-2,  1:-1] +
        u[1:-1, 1:-1, 2:  ] + u[1:-1, 1:-1, :-2 ] -
        6.0 * u[1:-1, 1:-1, 1:-1]
    ) / (a * a)

    # boundaries left as zero (Dirichlet u=0 outside)
    return lap


def get_cavity_indices(cfg: LatticeConfig) -> List[Tuple[int, int, int]]:
    """
    Return indices of the 7-point cavity:
        - center node (0,0,0)
        - 6 neighbors at ±a along each axis

    In array indices:
        center index = cfg.n
        neighbors at (±1, 0, 0), (0, ±1, 0), (0, 0, ±1) offsets from center.
    """
    c = cfg.n  # center index in each dimension
    cavity = [
        (c, c, c),         # center
        (c + 1, c, c),
        (c - 1, c, c),
        (c, c + 1, c),
        (c, c - 1, c),
        (c, c, c + 1),
        (c, c, c - 1),
    ]
    return cavity


def compute_B_res(cfg: LatticeConfig, u: np.ndarray) -> float:
    """
    Discrete resonance measure over the 7-point cavity:

        B_res(a) = sum_{(i,j,k) in cavity} u_{i,j,k}^4

    With C pinned via C = a * u_min, and u sampled from the 1/|x| profile,
    this quantity is expected to be asymptotically stable under refinement
    (including a -> a/402), up to discretization/finite-size effects.
    """
    cavity = get_cavity_indices(cfg)
    values = [u[i, j, k] for (i, j, k) in cavity]
    values = np.array(values, dtype=float)
    return float(np.sum(values**4))


def run_single_experiment(cfg: LatticeConfig) -> Dict[str, float]:
    """
    Run a single lattice experiment:
      - sample u(x) on the discrete lattice
      - compute discrete Laplacian
      - compute residual at origin
      - compute B_res over the 7-point cavity

    Returns a small dict of diagnostic values.
    """
    u = sample_continuum_profile(cfg)
    lap = laplacian_7pt(u, cfg.a)

    c = cfg.n
    residual_center = -lap[c, c, c]

    B_res_val = compute_B_res(cfg, u)

    return {
        "a": cfg.a,
        "n": cfg.n,
        "u_min": cfg.u_min,
        "residual_center": residual_center,
        "B_res": B_res_val,
    }


def run_refinement_suite(
    a_base: float,
    n_base: int,
    u_min: float,
    refinement_factors: List[float],
) -> List[Dict[str, float]]:
    """
    Run a suite of experiments for multiple lattice spacings:

        a_k = a_base / factor_k

    For each spacing, choose n_k so that the *physical* half-extent L = n_k * a_k
    stays approximately constant across refinements, i.e.:

        L_target ≈ n_base * a_base
        n_k ≈ round(L_target / a_k)

    This way, we compare lattices representing roughly the same physical region
    at different resolutions (including a -> a/402).

    refinement_factors: list of >0 scalars. E.g. [1.0, 2.0, 10.0, 402.0]
    """
    results = []

    L_target = n_base * a_base

    for factor in refinement_factors:
        a_k = a_base / factor
        n_k = max(2, int(round(L_target / a_k)))  # ensure at least small lattice

        cfg = LatticeConfig(
            a=a_k,
            n=n_k,
            u_min=u_min,
            include_origin=True,
        )

        res = run_single_experiment(cfg)
        res["refinement_factor"] = factor
        results.append(res)

    return results


def main():
    # Base configuration
    a_base = 1.0        # base lattice spacing
    n_base = 10         # half-extent (gives size 21^3)
    u_min = 1.0         # field value at r ≈ a (Anchor C1 pinning)

    # Refinement factors to test, including 402×
    refinement_factors = [
        1.0,
        2.0,
        4.0,
        10.0,
        20.0,
        50.0,
        100.0,
        402.0,
    ]

    results = run_refinement_suite(
        a_base=a_base,
        n_base=n_base,
        u_min=u_min,
        refinement_factors=refinement_factors,
    )

    # Print results in a GitHub-friendly table
    header = (
        "factor",
        "a",
        "n",
        "u_min",
        "residual_center",
        "B_res",
    )
    print("# Discrete resonance experiment results")
    print("# Columns: factor, a, n, u_min, residual_center, B_res")
    print("#")
    print(",".join(header))

    for r in results:
        row = [
            f"{r['refinement_factor']:.6g}",
            f"{r['a']:.6g}",
            f"{r['n']}",
            f"{r['u_min']:.6g}",
            f"{r['residual_center']:.6g}",
            f"{r['B_res']:.6g}",
        ]
        print(",".join(row))


if __name__ == "__main__":
    main()
