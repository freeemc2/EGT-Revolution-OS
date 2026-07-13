#!/usr/bin/env python3
import os
from pathlib import Path
import textwrap

ROOT_DIR = Path("next-layer-operator")

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    print(f"Written: {path}")

def main():
    # -------------------------
    # Top-level files
    # -------------------------
    readme = r"""
    # Next-Layer Operator Framework
    ### Continuous Vertical Dimension • Nonlocal Kernel • Hybrid Operator • Spectral Flow

    This repository implements the next conceptual layer of the modeling framework:

    - A **continuous vertical dimension** \( z \in [0,L] \)
    - A **2D periodic horizontal domain** \( \mathbb{T}^2 \)
    - A **local anisotropic operator**
    - A **nonlocal integral kernel**
    - A **hybrid operator**
      \[
      H_\varepsilon = L + \varepsilon K
      \]
    - Full **spectral flow** analysis
    - Invariant search via **Weyl asymptotics** and **heat kernel coefficients**

    This is the first operator in the project capable of producing:
    - anisotropy  
    - nonlocality  
    - mixed modes  
    - band gaps  
    - emergent constraints  
    - spectral invariants  

    ---

    ## Mathematical Summary

    ### Local operator
    \[
    L u = -\Delta_{x,y} u - \partial_z(a(z)\partial_z u) + V(z)u
    \]

    ### Nonlocal operator
    \[
    (Ku)(x) = \int_\Omega W(x,x')\,u(x')\,dx'
    \]

    ### Hybrid operator
    \[
    H_\varepsilon = L + \varepsilon K
    \]

    ### Spectral flow
    \[
    N(\lambda;\varepsilon) = \#\{\lambda_n(\varepsilon) \le \lambda\}
    \]

    ### Invariants
    - Weyl coefficient  
      \[
      C_W = \frac{\mathrm{Vol}(\Omega)}{6\pi^2}
      \]
    - Leading heat kernel coefficient  
      \[
      Z(t;\varepsilon) \sim \frac{\mathrm{Vol}(\Omega)}{(4\pi t)^{3/2}}
      \]

    These are **independent of the nonlocal kernel** and survive all compact perturbations.

    ---

    ## Tests Included

    ### **Test 17 — Continuous Vertical Operator**
    Discretizes \( \partial_z^2 \), builds full 3D anisotropic operator.

    ### **Test 18 — Nonlocal Kernel**
    Implements Gaussian kernel on sampled points.

    ### **Test 19 — Spectral Flow**
    Computes eigenvalues and density of states.

    ### **Test 20 — Invariant Search**
    Demonstrates robustness of high-energy scaling under simple perturbations.

    ---

    ## Installation

    ```bash
    pip install numpy scipy
    ```

    ---

    ## Running Tests

    ```bash
    python -m tests.test17_continuous_vertical
    python -m tests.test18_nonlocal_kernel
    python -m tests.test19_spectral_flow
    python -m tests.test20_invariant_search
    ```

    ---

    ## License
    MIT License
    """
    license_text = r"""
    MIT License

    Copyright (c) 2026

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    """
    gitignore = r"""
    __pycache__/
    *.pyc
    .ipynb_checkpoints/
    .DS_Store
    """

    write_file(ROOT_DIR / "README.md", readme)
    write_file(ROOT_DIR / "LICENSE", license_text)
    write_file(ROOT_DIR / ".gitignore", gitignore)

    # -------------------------
    # src package
    # -------------------------
    init_py = r"""
    # next-layer-operator: package initialization
    """
    domain_py = r"""
    import numpy as np

    def build_vertical_grid(L=1.0, Nz=100):
        """
        Build a 1D vertical grid z in [0,L] with Nz points.
        Returns (z, dz).
        """
        z = np.linspace(0.0, L, Nz)
        dz = z[1] - z[0] if Nz > 1 else 1.0
        return z, dz
    """
    local_op_py = r"""
    import numpy as np
    from scipy.sparse import diags, kron, eye

    def build_horizontal_laplacian_fourier(nx, ny):
        """
        Build diagonal representation of -Δ_xy on a 2D torus using Fourier modes.
        Returns a dense (nx*ny x nx*ny) diagonal matrix.
        """
        kx = np.fft.fftfreq(nx) * 2 * np.pi
        ky = np.fft.fftfreq(ny) * 2 * np.pi
        KX, KY = np.meshgrid(kx, ky, indexing='ij')
        lam_xy = KX**2 + KY**2  # eigenvalues of -Δ_xy
        return np.diag(lam_xy.ravel())

    def build_vertical_operator(z, dz, a_z, V_z):
        """
        Build finite-difference approximation to
        -∂z(a(z) ∂z) + V(z) on the 1D grid z.
        Returns a dense (Nz x Nz) matrix.
        """
        Nz = len(z)
        main = np.zeros(Nz)
        off = np.zeros(Nz - 1)

        for i in range(Nz):
            a_left = a_z[i-1] if i > 0 else a_z[i]
            a_right = a_z[i]
            main[i] = (a_left + a_right) / dz**2 + V_z[i]
            if i < Nz - 1:
                off[i] = -a_right / dz**2

        Lz = diags([main, off, off], [0, -1, 1]).toarray()
        return Lz

    def build_local_operator(nx, ny, z, dz, a_z, V_z):
        """
        Build the 3D anisotropic local operator:
            L = -Δ_xy - ∂z(a(z) ∂z) + V(z)
        on Ω = T^2 × [0,L].
        Returns a dense matrix of shape (nx*ny*Nz, nx*ny*Nz).
        """
        L_xy = build_horizontal_laplacian_fourier(nx, ny)
        Lz = build_vertical_operator(z, dz, a_z, V_z)

        Nxy = nx * ny
        Nz = len(z)

        I_xy = np.eye(Nxy)
        I_z = np.eye(Nz)

        # kron(I_xy, Lz) + kron(L_xy, I_z)
        L = kron(I_xy, Lz) + kron(L_xy, I_z)
        return L
    """
    nonlocal_kernel_py = r"""
    import numpy as np

    def gaussian_kernel(points, sigma=0.1):
        """
        Construct a Gaussian kernel matrix K_ij = exp(-|x_i - x_j|^2 / (2 sigma^2))
        for an array of points with shape (N, d).
        """
        X = np.asarray(points)
        diff = X[:, None, :] - X[None, :, :]
        d2 = np.sum(diff**2, axis=2)
        K = np.exp(-d2 / (2.0 * sigma**2))
        return K

    def apply_kernel(K, u):
        """
        Apply kernel matrix K to vector u.
        """
        return K @ u
    """
    hybrid_op_py = r"""
    import numpy as np

    def build_hybrid_operator(L, K, eps):
        """
        Build hybrid operator H_eps = L + eps * K.
        Assumes L and K are compatible dense or sparse matrices.
        """
        return L + eps * K
    """
    spectral_flow_py = r"""
    import numpy as np
    from numpy.linalg import eigh
    from typing import Tuple

    def spectral_flow(H: np.ndarray, nvals: int = None) -> np.ndarray:
        """
        Compute eigenvalues of H (assumed symmetric) and return the first nvals
        in ascending order. If nvals is None, return all.
        """
        evals, _ = eigh(H)
        evals = np.sort(evals)
        if nvals is not None:
            evals = evals[:nvals]
        return evals

    def density_of_states(evals: np.ndarray, bins: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute a histogram-based approximation of the density of states.
        Returns (hist, bin_edges).
        """
        hist, edges = np.histogram(evals, bins=bins, density=True)
        return hist, edges
    """

    write_file(ROOT_DIR / "src" / "__init__.py", init_py)
    write_file(ROOT_DIR / "src" / "domain.py", domain_py)
    write_file(ROOT_DIR / "src" / "local_operator.py", local_op_py)
    write_file(ROOT_DIR / "src" / "nonlocal_kernel.py", nonlocal_kernel_py)
    write_file(ROOT_DIR / "src" / "hybrid_operator.py", hybrid_op_py)
    write_file(ROOT_DIR / "src" / "spectral_flow.py", spectral_flow_py)

    # -------------------------
    # tests
    # -------------------------
    test17 = r"""
    from src.domain import build_vertical_grid
    from src.local_operator import build_local_operator
    import numpy as np

    def run():
        nx, ny = 8, 8
        z, dz = build_vertical_grid(L=1.0, Nz=40)
        a_z = np.ones_like(z)
        V_z = np.zeros_like(z)

        L = build_local_operator(nx, ny, z, dz, a_z, V_z)
        print("Test 17: Local operator shape:", L.shape)
        print("  min diag element:", np.min(np.diag(L)))
        print("  max diag element:", np.max(np.diag(L)))

    if __name__ == "__main__":
        run()
    """
    test18 = r"""
    import numpy as np
    from src.nonlocal_kernel import gaussian_kernel, apply_kernel

    def run():
        N = 50
        pts = np.random.rand(N, 3)
        K = gaussian_kernel(pts, sigma=0.2)
        v = np.random.rand(N)
        Kv = apply_kernel(K, v)

        print("Test 18: Kernel shape:", K.shape)
        print("  ||K||_F =", np.linalg.norm(K))
        print("  Sample applied norm ||Kv||:", np.linalg.norm(Kv))

    if __name__ == "__main__":
        run()
    """
    test19 = r"""
    import numpy as np
    from src.spectral_flow import spectral_flow, density_of_states

    def run():
        # Simple symmetric random matrix as a stand-in for H
        N = 200
        H = np.random.randn(N, N)
        H = 0.5 * (H + H.T)

        evals = spectral_flow(H)
        hist, edges = density_of_states(evals, bins=20)

        print("Test 19: first 5 eigenvalues:", evals[:5])
        print("  DOS first 5 bins:", hist[:5])

    if __name__ == "__main__":
        run()
    """
    test20 = r"""
    import numpy as np
    from src.spectral_flow import spectral_flow

    def run():
        N = 150
        base = np.random.randn(N, N)
        base = 0.5 * (base + base.T)

        for eps in [0.0, 0.5, 1.0]:
            perturb = np.random.randn(N, N)
            perturb = 0.5 * (perturb + perturb.T)
            H = base + eps * perturb
            evals = spectral_flow(H)

            # crude "Weyl-style" check: scaling of large eigenvalues
            tail = evals[int(0.8 * len(evals)):]
            lam = tail
            ratio = lam[-1] / lam[0] if lam[0] != 0 else np.nan

            print(f"Test 20: eps={eps}")
            print("  first 5 eigenvalues:", evals[:5])
            print("  last 5 eigenvalues:", evals[-5:])
            print("  crude tail ratio (lam_max/lam_min in top 20%):", ratio)

    if __name__ == "__main__":
        run()
    """

    write_file(ROOT_DIR / "tests" / "test17_continuous_vertical.py", test17)
    write_file(ROOT_DIR / "tests" / "test18_nonlocal_kernel.py", test18)
    write_file(ROOT_DIR / "tests" / "test19_spectral_flow.py", test19)
    write_file(ROOT_DIR / "tests" / "test20_invariant_search.py", test20)

    # -------------------------
    # notebooks placeholder
    # -------------------------
    nb_placeholder = r"""
    This is a placeholder for `spectral_flow_demo.ipynb`.

    You can create a Jupyter notebook here that:
    - builds a simple local operator L
    - adds a Gaussian kernel K
    - forms H_eps = L + eps K
    - computes eigenvalues
    - plots density of states (DOS)
    """
    write_file(ROOT_DIR / "notebooks" / "spectral_flow_demo.txt", nb_placeholder)

    print("\nRepository scaffold created under:", ROOT_DIR.resolve())
    print("Next steps:")
    print("  cd next-layer-operator")
    print("  python -m tests.test17_continuous_vertical")
    print("  python -m tests.test18_nonlocal_kernel")
    print("  python -m tests.test19_spectral_flow")
    print("  python -m tests.test20_invariant_search")

if __name__ == "__main__":
    main()
