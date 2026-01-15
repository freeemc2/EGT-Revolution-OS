#!/bin/bash

# First, create and run the bootstrap script
cat > bootstrap_egt_project.py << 'EOF'
#!/usr/bin/env python3
"""
bootstrap_egt_project.py

Run this script once in an empty directory to generate:

- egt_lattice.py       : core EGT lattice logic (C1–C3)
- run_experiment.py    : CLI to run the refinement suite and print results
- README.md            : explanation and usage
- .gitignore           : basic Python ignores

After generation, you can:
- run: python run_experiment.py
- inspect/modify: egt_lattice.py, README.md
- commit and push to GitHub.
"""

import textwrap
from pathlib import Path


# ------------------------
# File contents
# ------------------------

EGT_LATTICE_PY = textwrap.dedent(r"""
    #!/usr/bin/env python3
    """
    egt_lattice.py

    Core EGT lattice model (Anchors C1, C2, C3).

    This module implements:
    - A 3D cubic lattice with spacing a (Anchor C1: discrete spacing / UV cutoff)
    - A 7-point discrete Laplacian with degree-6 connectivity (Anchor C2: discrete skeleton)
    - Sampling of the continuum profile u(x) = C / |x| with C pinned by u(r=a) = u_min
    - A localized resonance measure B_res over the 7-point cavity (Anchor C3: discrete normalization)

    The goal is to:
    - Collapse the continuum 1/|x| singularity at the origin into a finite discrete structure
    - Define a resonance measure that becomes asymptotically invariant under lattice refinement
    - Provide a concrete, testable definition of an emergent "Sovereign Constant" from the lattice.
    """

    from dataclasses import dataclass
    from typing import Tuple, List, Dict

    import numpy as np


    # ----------------------------------------------------------------------
    # Lattice configuration (Anchor C1: spacing a, lattice extent, u_min)
    # ----------------------------------------------------------------------


    @dataclass
    class LatticeConfig:
        """
        Configuration for the 3D lattice experiment.

        Attributes
        ----------
        a : float
            Lattice spacing (Anchor C1: fundamental discrete spacing / pixel size).
        n : int
            Half-extent in each direction. The grid indices run from -n..+n,
            so the total size is (2n+1)^3.
        u_min : float
            Target field value at radius r ≈ a. This pins the continuum amplitude via:
                C = a * u_min
            so that the sampled profile u(x) = C / |x| satisfies u(r=a) = u_min.
        include_origin : bool
            Whether to assign a finite value u(0,0,0) = u_min at the origin.
            This regularizes the continuum singularity at r=0 and reflects the UV cutoff a.
        """
        a: float
        n: int
        u_min: float
        include_origin: bool = True


    # ----------------------------------------------------------------------
    # Coordinate generation
    # ----------------------------------------------------------------------


    def generate_lattice_coords(cfg: LatticeConfig) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate 1D coordinate arrays for the 3D lattice:

            i, j, k in [-n, ..., 0, ..., n], with physical spacing a.

        Returns
        -------
        x, y, z : np.ndarray
            1D arrays of coordinates in each dimension (shape: 2n+1).
        """
        indices = np.arange(-cfg.n, cfg.n + 1, dtype=int)
        x = indices * cfg.a
        y = indices * cfg.a
        z = indices * cfg.a
        return x, y, z


    # ----------------------------------------------------------------------
    # Continuum profile sampling (u ~ C / |x|, with C pinned)
    # ----------------------------------------------------------------------


    def sample_continuum_profile(cfg: LatticeConfig) -> np.ndarray:
        """
        Sample the continuum profile u(x) = C / |x| on the discrete lattice.

        Anchor C1 pins the amplitude via:
            u(r = a) = u_min  =>  C = a * u_min.

        Implementation
        --------------
        - Compute C = cfg.a * cfg.u_min.
        - For all lattice points with r > 0:
              u(i,j,k) = C / sqrt(x^2 + y^2 + z^2)
        - At the origin (r = 0):
              u(0,0,0) = u_min   (a finite, pinned value)

        This regularizes the continuum singularity at r=0 and matches the
        desired behavior at r ≈ a.
        """
        x, y, z = generate_lattice_coords(cfg)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

        r = np.sqrt(X**2 + Y**2 + Z**2)

        # Anchor C1: pin C using u(r=a) = u_min
        C = cfg.a * cfg.u_min

        u = np.zeros_like(r, dtype=float)

        # Away from the origin: u = C / r
        mask_nonzero = r > 0.0
        u[mask_nonzero] = C / r[mask_nonzero]

        # At the origin: assign finite value u_min
        if cfg.include_origin:
            center_idx = cfg.n
            u[center_idx, center_idx, center_idx] = cfg.u_min

        return u


    # ----------------------------------------------------------------------
    # Discrete Laplacian (Anchor C2: 7-point, degree-6 stencil)
    # ----------------------------------------------------------------------


    def laplacian_7pt(u: np.ndarray, a: float) -> np.ndarray:
        """
        7-point discrete Laplacian on a 3D cubic grid (degree-6 connectivity).

        For interior points:

            (Δ_a u)_{i,j,k} = (1/a^2) * (
                u_{i+1,j,k} + u_{i-1,j,k}
              + u_{i,j+1,k} + u_{i,j-1,k}
              + u_{i,j,k+1} + u_{i,j,k-1}
              - 6 u_{i,j,k}
            )

        We use Dirichlet boundary conditions (u=0 outside):
        - The boundary values of lap are left as zero.
        - No periodic wrapping.

        Parameters
        ----------
        u : np.ndarray
            3D array of field values (shape: Nx x Ny x Nz).
        a : float
            Lattice spacing.

        Returns
        -------
        lap : np.ndarray
            3D array of Laplacian values with the same shape as u.
        """
        lap = np.zeros_like(u)

        lap[1:-1, 1:-1, 1:-1] = (
            u[2:,   1:-1, 1:-1] + u[:-2,  1:-1, 1:-1] +
            u[1:-1, 2:,   1:-1] + u[1:-1, :-2,  1:-1] +
            u[1:-1, 1:-1, 2:  ] + u[1:-1, 1:-1, :-2 ] -
            6.0 * u[1:-1, 1:-1, 1:-1]
        ) / (a * a)

        return lap


    # ----------------------------------------------------------------------
    # Resonant cavity: center + 6 neighbors
    # ----------------------------------------------------------------------


    def get_cavity_indices(cfg: LatticeConfig) -> List[Tuple[int, int, int]]:
        """
        Return indices of the 7-point resonant cavity:

        - Center node: (0,0,0)  -> array index (n, n, n)
        - 6 neighbors at ±a along each axis:

              (±1, 0, 0), (0, ±1, 0), (0, 0, ±1)  in index offsets.

        In array indices:
            center index = cfg.n
        """
        c = cfg.n
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


    # ----------------------------------------------------------------------
    # Discrete resonance measure B_res (Anchor C3)
    # ----------------------------------------------------------------------


    def compute_B_res(cfg: LatticeConfig, u: np.ndarray) -> float:
        """
        Compute the discrete resonance measure over the 7-point cavity:

            B_res(a) = sum_{(i,j,k) in cavity} [u_{i,j,k}]^4

        Interpretation
        --------------
        - The cavity is the central node plus its 6 neighbors at distance a.
        - The 4th power encodes the nonlinear resonance structure consistent
          with the continuum u^4 behavior.
        - With the amplitude pinned via C = a * u_min and a fixed stencil,
          B_res(a) is expected to approach a constant as a -> 0, up to
          finite-size and discretization effects.

        This constant is the discrete "Sovereign Constant" associated with
        this lattice, stencil, and normalization choice.
        """
        cavity = get_cavity_indices(cfg)
        values = [u[i, j, k] for (i, j, k) in cavity]
        values = np.array(values, dtype=float)
        return float(np.sum(values**4))


    # ----------------------------------------------------------------------
    # Single experiment: one lattice spacing a
    # ----------------------------------------------------------------------


    def run_single_experiment(cfg: LatticeConfig) -> Dict[str, float]:
        """
        Run a single lattice experiment for a given configuration.

        Steps
        -----
        1. Sample the pinned continuum profile u(x) = C/|x| on the discrete lattice.
        2. Compute the 7-point discrete Laplacian.
        3. Extract the discrete residual at the origin:
               residual_center = - (Δ_a u)(0,0,0)
           which is the finite replacement of the continuum singular source.
        4. Compute B_res(a) over the 7-point cavity.

        Returns
        -------
        results : dict
            Keys:
                - "a"               : lattice spacing
                - "n"               : half-extent in each direction
                - "u_min"           : pinned field value at r ~ a
                - "residual_center" : discrete residual at the origin
                - "B_res"           : discrete resonance measure
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


    # ----------------------------------------------------------------------
    # Refinement suite: test stability under a -> a / factor
    # ----------------------------------------------------------------------


    def run_refinement_suite(
        a_base: float,
        n_base: int,
        u_min: float,
        refinement_factors: List[float],
    ) -> List[Dict[str, float]]:
        """
        Run a suite of experiments for multiple lattice spacings:

            a_k = a_base / factor_k

        For each spacing a_k, choose n_k so that the *physical* half-extent
        L = n_k * a_k stays approximately constant:

            L_target ≈ n_base * a_base
            n_k ≈ round(L_target / a_k)

        This allows us to compare lattices that represent roughly the same
        physical region at different resolutions (including a -> a/402).

        Parameters
        ----------
        a_base : float
            Base lattice spacing.
        n_base : int
            Base half-extent (grid size = 2n_base + 1).
        u_min : float
            Pinned field value at r ≈ a (Anchor C1).
        refinement_factors : list of float
            Refinement factors > 0. Example: [1.0, 2.0, 10.0, 402.0]

        Returns
        -------
        results : list of dict
            One dict per refinement configuration, containing:
                - "a"               : lattice spacing
                - "n"               : half-extent
                - "u_min"           : pinned value
                - "residual_center" : discrete residual at origin
                - "B_res"           : resonance measure
                - "refinement_factor": the factor used
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
""")


RUN_EXPERIMENT_PY = textwrap.dedent(r"""
    #!/usr/bin/env python3
    """
    run_experiment.py

    Command-line entrypoint for the EGT lattice experiment.

    This script:
    - Imports the core EGT lattice model from egt_lattice.py
    - Defines a base configuration (a_base, n_base, u_min)
    - Runs a refinement suite over multiple lattice spacings, including a -> a/402
    - Prints results as a CSV table:
        factor, a, n, u_min, residual_center, B_res
    """

    from typing import List

    from egt_lattice import run_refinement_suite


    def main() -> None:
        # Base configuration:
        # - a_base: base lattice spacing
        # - n_base: half-extent (grid size = 2*n_base + 1)
        # - u_min: pinned field value at r ≈ a_base
        a_base = 1.0
        n_base = 10
        u_min = 1.0

        # Refinement factors, including a -> a/402
        refinement_factors: List[float] = [
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

        # Print results in CSV form, GitHub-friendly
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
""")


README_MD = textwrap.dedent(r"""
    # EGT Lattice Resonance Experiment

    This repository implements a **discrete lattice version** of the core EGT idea:

    - A continuum field with profile
      \[
      u(x) \sim \frac{C}{|x|}
      \]
      has no intrinsic scale or amplitude.
    - By introducing a **fundamental lattice spacing** and a **discrete Laplacian**, the
      continuum singularity at the origin becomes a **finite resonant cavity**.
    - A localized, nonlinear resonance measure over this cavity becomes
      **asymptotically invariant** under lattice refinement (including large
      refinements like `a -> a/402`), defining a **discrete constant**.

    The code in this project lets you **compute and inspect** that discrete constant.

    ## Files

    - `egt_lattice.py`  
      Core lattice logic:
      - Anchor C1: discrete spacing `a` and pinned amplitude `C = a * u_min`
      - Anchor C2: 7-point 3D Laplacian (degree-6 connectivity)
      - Anchor C3: localized resonance measure over the 7-point cavity

    - `run_experiment.py`  
      CLI entrypoint that:
      - runs a refinement suite over multiple lattice spacings
      - includes a large refinement factor (e.g. 402x)
      - prints a CSV table of:
        - lattice spacing `a`
        - half-extent `n`
        - pinned value `u_min`
        - discrete residual at the origin
        - discrete resonance measure `B_res`

    ## Conceptual Overview

    ### 1. Continuum Profile

    Start with a continuum field in 3D:

    \[
    u(x) \sim \frac{C}{|x|}.
    \]

    This profile is:
    - scale-invariant (no preferred length),
    - amplitude-free (C is not fixed),
    - singular at the origin.

    On its own, it cannot produce a finite, universal constant.

    ### 2. Anchor C1 – Discrete Spacing and Pinned Amplitude

    Introduce a **fundamental lattice spacing** `a`:

    - This is a UV cutoff / pixel size.
    - You decide that the field at radius `r ≈ a` has a fixed value:
      \[
      u(r = a) = u_{\min}.
      \]

    This immediately pins the amplitude:

    \[
    C = a \cdot u_{\min}.
    \]

    The continuum singularity is now controlled by the discrete scale `a`.

    In code, this shows up as:

    ```python
    C = cfg.a * cfg.u_min
    u[mask_nonzero] = C / r[mask_nonzero]
    u[center_idx, center_idx, center_idx] = cfg.u_min
    ```

    ### 3. Anchor C2 – Discrete Laplacian (7-Point Stencil)

    We discretize space on a 3D cubic lattice with spacing `a` and use the standard
    **7-point discrete Laplacian**:

    ```python
    lap[1:-1, 1:-1, 1:-1] = (
        u[2:,   1:-1, 1:-1] + u[:-2,  1:-1, 1:-1] +
        u[1:-1, 2:,   1:-1] + u[1:-1, :-2,  1:-1] +
        u[1:-1, 1:-1, 2:  ] + u[1:-1, 1:-1, :-2 ] -
        6.0 * u[1:-1, 1:-1, 1:-1]
    ) / (a * a)
    ```

    Each node has degree 6 (six nearest neighbors). The continuum Laplacian becomes a
    graph Laplacian on a rigid 3D skeleton.

    The origin plus its 6 neighbors form a **7-point resonant cavity**:
    - center node (0,0,0),
    - six neighbors at distance `a` along ±x, ±y, ±z.

    The continuum singularity at the origin is now replaced by a **finite discrete
    residual** when you apply the Laplacian to the sampled 1/|x| profile.

    ### 4. Anchor C3 – Discrete Resonance Measure B_res

    We define a **localized resonance measure**:

    \[
    B_{\text{res}}(a) = \sum_{(i,j,k) \in \text{cavity}} u_{i,j,k}^4.
    \]

    Here:
    - The cavity is the 7-point resonant structure: center + 6 nearest neighbors.
    - The 4th power encodes a nonlinear resonance consistent with continuum u^4 behavior.
    - With:
      \[
      C = a \cdot u_{\min}
      \]
      and a fixed stencil, B_res(a) is expected to approach a *constant* as the
      lattice is refined.

    This constant is the discrete, scale-invariant quantity associated with this
    lattice and normalization. It is the **emergent constant** of the experiment.

    ## Running the Experiment

    Requirements:
    - Python 3.8+
    - NumPy

    Install dependencies (if needed):

    ```bash
    pip install numpy
    ```

    Run the experiment:

    ```bash
    python run_experiment.py
    ```

    You will see a CSV-like output:

    ```text
    # Discrete resonance experiment results
    # Columns: factor, a, n, u_min, residual_center, B_res
    #
    factor,a,n,u_min,residual_center,B_res
    1,1,10,1,-0.123456,7.000000
    2,0.5,20,1,-0.123456,7.000000
    ...
    402,0.00248756,4020,1,-0.123456,7.000000
    ```

    (Numbers above are illustrative; actual values will depend on the lattice size
    and discretization effects.)

    - `factor` is the refinement factor (e.g. 402 means a = a_base / 402).
    - `a` is the lattice spacing.
    - `n` is the half-extent of the lattice (size = (2n+1)^3).
    - `u_min` is the pinned value at r ≈ a.
    - `residual_center` is the discrete residual at the origin:
      \[
      -(\Delta_a u)(0,0,0).
      \]
    - `B_res` is the discrete resonance measure over the 7-point cavity.

    The goal is to see `B_res` stabilize as `factor` increases, demonstrating that
    the resonance measure is a **scale-invariant constant** of the lattice model.

    ## Next Steps

    - Analyze the convergence of `B_res` as a function of refinement factor.
    - Compare its limiting value with other constants or invariants in your broader
      EGT framework.
    - Extend the model to include nonlocal/fractional corrections (the "fog") while
      keeping the same core lattice skeleton.

    This project gives you a concrete, testable foundation for the emergent constant
    in your discrete EGT picture.
""")


GITIGNORE = textwrap.dedent(r"""
    __pycache__/
    *.pyc
    .DS_Store
    .idea/
    .vscode/
    .pytest_cache/
    .mypy_cache/
    .env
    .venv
    venv/
    env/
""")


# ------------------------
# Write files
# ------------------------

def write_file(path: Path, content: str, executable: bool = False) -> None:
    path.write_text(content, encoding="utf-8")
    if executable:
        try:
            # Make executable on POSIX; harmless on Windows
            mode = path.stat().st_mode
            path.chmod(mode | 0o111)
        except Exception:
            pass


def main() -> None:
    root = Path(".").resolve()

    files = {
        "egt_lattice.py": (EGT_LATTICE_PY, True),
        "run_experiment.py": (RUN_EXPERIMENT_PY, True),
        "README.md": (README_MD, False),
        ".gitignore": (GITIGNORE, False),
    }

    for name, (content, exe) in files.items():
        path = root / name
        if path.exists():
            print(f"[skip] {name} already exists")
        else:
            write_file(path, content, executable=exe)
            print(f"[write] {name}")

    print("\nDone. You can now run:")
    print("  python run_experiment.py")
    print("and inspect the generated files for GitHub.")


if __name__ == "__main__":
    main()
EOF

# Run the bootstrap script
python3 bootstrap_egt_project.py

# Check if numpy is installed, install if not
python3 -c "import numpy" 2>/dev/null || {
    echo "Installing numpy..."
    pip3 install numpy --quiet
}

# Now run the experiment
echo -e "\n=== Running EGT Lattice Experiment ==="
python3 run_experiment.py

# Run a more comprehensive experiment with different u_min values
echo -e "\n=== Extended Experiment with Different u_min Values ==="
cat > extended_experiment.py << 'EOF'
#!/usr/bin/env python3
"""
Extended experiment to test B_res convergence for different u_min values.
"""
from egt_lattice import run_refinement_suite

def run_extended():
    a_base = 1.0
    n_base = 10
    
    # Test different u_min values
    u_min_values = [0.5, 1.0, 2.0, 5.0]
    
    refinement_factors = [1.0, 2.0, 4.0, 10.0, 20.0, 50.0, 100.0, 402.0]
    
    print("# Extended EGT Lattice Experiment")
    print("# Testing convergence for different u_min values")
    print("# u_min, factor, a, n, B_res")
    
    for u_min in u_min_values:
        results = run_refinement_suite(
            a_base=a_base,
            n_base=n_base,
            u_min=u_min,
            refinement_factors=refinement_factors,
        )
        
        for r in results:
            print(f"{u_min:.3f},{r['refinement_factor']:.3f},{r['a']:.6g},{r['n']},{r['B_res']:.6g}")

if __name__ == "__main__":
    run_extended()
EOF

python3 extended_experiment.py

# Run a convergence analysis
echo -e "\n=== Convergence Analysis ==="
cat > convergence_analysis.py << 'EOF'
#!/usr/bin/env python3
"""
Analyze convergence of B_res as a -> 0.
"""
from egt_lattice import run_refinement_suite
import numpy as np

def analyze_convergence():
    a_base = 1.0
    n_base = 10
    u_min = 1.0
    
    # More refinement factors for better analysis
    refinement_factors = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 8.0, 10.0, 
                          15.0, 20.0, 30.0, 50.0, 75.0, 100.0, 
                          150.0, 200.0, 300.0, 402.0, 500.0]
    
    results = run_refinement_suite(
        a_base=a_base,
        n_base=n_base,
        u_min=u_min,
        refinement_factors=refinement_factors,
    )
    
    # Extract data
    factors = [r['refinement_factor'] for r in results]
    a_vals = [r['a'] for r in results]
    B_res_vals = [r['B_res'] for r in results]
    residuals = [r['residual_center'] for r in results]
    
    # Calculate convergence metrics
    print("# Convergence Analysis of B_res")
    print("# factor, a, B_res, B_res/B_res[0], |ΔB_res|/B_res, expected_scaling")
    
    B_res_0 = B_res_vals[0]
    
    for i, (factor, a, B, residual) in enumerate(zip(factors, a_vals, B_res_vals, residuals)):
        if i == 0:
            delta_rel = 0
        else:
            delta_rel = abs(B - B_res_vals[i-1]) / max(abs(B), abs(B_res_vals[i-1]))
        
        # Expected scaling based on continuum analysis
        # If B_res ~ constant, then B_res/B_res_0 should approach 1
        # If there's a ~ 1/a dependence, then B_res * a should approach constant
        B_normalized = B / B_res_0
        B_times_a = B * a
        
        print(f"{factor:.3f},{a:.6g},{B:.6g},{B_normalized:.6g},{delta_rel:.6g},{B_times_a:.6g}")

if __name__ == "__main__":
    analyze_convergence()
EOF

python3 convergence_analysis.py

# Create a summary visualization
echo -e "\n=== Creating Summary Report ==="
cat > summary_report.md << 'EOF'
# EGT Lattice Experiment Summary

## Overview
This experiment tests the discrete regularization of a continuum singularity:
- Continuum profile: u(x) = C/|x|
- Discrete regularization: lattice spacing a, pinned amplitude C = a * u_min
- Resonance measure: B_res = Σ_{cavity} u^4

## Key Questions Tested
1. Does B_res converge as a → 0?
2. Is the convergence independent of u_min?
3. Does the 402x refinement show stability?

## Mathematical Framework

### Continuum Singularity
The continuum Laplacian of 1/|x| in 3D gives:
∇²(1/|x|) = -4π δ(x)

This is singular at the origin.

### Discrete Regularization
With lattice spacing a:
1. UV cutoff: r_min = a
2. Pinned amplitude: u(a) = u_min ⇒ C = a·u_min
3. Discrete Laplacian: 7-point stencil with degree 6 connectivity

### Expected Behavior
If the model is well-defined, B_res should approach a finite limit as a → 0.

## Physical Interpretation
This implements a lattice version of renormalization:
- The continuum singularity is regulated by the lattice spacing
- Physical quantities should be finite in the a → 0 limit
- The emergent constant B_res_∞ represents the "renormalized" strength of the singularity

## Results Interpretation
Check if:
1. B_res shows convergence with refinement
2. The 402x refinement factor gives similar B_res to smaller refinements
3. Different u_min values scale predictably

## Connection to Original EGT Claims
The original repository made grandiose claims about:
- "Zero-jitter architecture"
- "Dark matter energy extraction"
- "Biological sovereignty"

This code implements the actual computational core that might have inspired those claims, stripped of pseudoscience.
EOF

echo -e "\n=== Files Generated ==="
ls -la *.py *.md .gitignore

echo -e "\n=== Experiment Complete ==="
echo "Summary report saved to summary_report.md"
echo "Raw data available from: python3 run_experiment.py"
echo "Extended analysis: python3 extended_experiment.py"
echo "Convergence analysis: python3 convergence_analysis.py"
EOF

# Make the bash script executable and run it
chmod +x run_experiments.sh
./run_experiments.sh
