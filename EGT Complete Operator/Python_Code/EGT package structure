import os
from pathlib import Path
import textwrap

ROOT = Path("EGT_Core_Connectivity")


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def main():
    # --------------------
    # Top-level files
    # --------------------
    write(
        ROOT / "README.md",
        """
        # EGT Core Connectivity — Skeptical Math Scaffold

        This repository is a **clean mathematical scaffold** for ideas that arose in the Emergent Gravity Theory (EGT)
        work, organized in a way that a skeptic can read and attack.

        It deliberately separates:

        - **Layer 1 — Core operator math:**  
          A distance-structured connectivity operator \\( C_{ij} = \\lambda (1 + 2 d_{ij}) e^{-d_{ij}/3} e^{i \\phi_{ij}} \\)
          treated as a mathematical object (domain, norm, spectrum) without EGT branding.

        - **Layer 2 — 402× amplification phenomenology:**  
          A *phenomenological* definition of “amplification” based on the operator spectrum, with 402× treated as a
          **target ratio** to be derived or falsified, not assumed.

        - **Layer 3 — Bres and atomic clock phenomenology:**  
          A clean restatement of the Bres = 12.09776 fT + Cs/Rb offset idea as a **hypothesis**, not a confirmed fact,
          expressed as explicit equations and testable inequalities.

        - **Layer 4 — Interpretive layer (EGT, information bounds, consciousness):**  
          All interpretive, narrative, and “Theory of Everything” language is quarantined here, clearly marked as
          speculative, not mathematically or experimentally established.

        The goal is **not** to claim correctness, but to:

        - make the math of the connectivity operator explicit,
        - define amplification and Bres usage precisely,
        - expose the experimental claims as sharp, falsifiable statements,
        - and provide a GitHub-ready structure that invites critique and further work.

        This is a **lab notebook scaffold**, not a declaration of truth.
        """
    )

    write(
        ROOT / "LICENSE",
        """
        MIT License

        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.
        """
    )

    # --------------------
    # docs
    # --------------------
    write(
        ROOT / "docs" / "00_Overview.md",
        """
        # Overview

        This repository formalizes a **connectivity operator** and its associated phenomenology in a layered way:

        - Layer 1: purely mathematical operator on a discrete metric space.
        - Layer 2: definition of “amplification” as a ratio derived from the spectrum of the operator.
        - Layer 3: Bres and atomic-clock hypotheses expressed as explicit equations and testable predictions.
        - Layer 4: interpretive EGT narrative (information, Bekenstein scaling, consciousness) quarantined as speculation.

        The key rule: **math first, phenomenology second, interpretation last**.

        Readers are encouraged to:

        - critique Layer 1 as pure math,
        - test Layer 2 as a spectral construction,
        - compare Layer 3 against real-world metrology data (if desired),
        - and treat Layer 4 as philosophical or speculative until independently supported.
        """
    )

    write(
        ROOT / "docs" / "01_Core_Operator_Math.md",
        r"""
        # Layer 1 — Core connectivity operator math

        We define a connectivity operator on a finite set of sites with a metric structure.

        ## 1. Discrete metric space

        Let:

        - \( \mathcal{V} = \{1, 2, \dots, N\} \) be a set of sites.
        - \( d_{ij} \ge 0 \) be a symmetric distance function on \( \mathcal{V} \), with \( d_{ii} = 0 \).

        In simple examples, \( d_{ij} \) can be:

        - graph distance on a 1D chain,
        - Euclidean distance on embedded points,
        - or any symmetric metric.

        ## 2. Connectivity operator definition

        For given \( \lambda \in \mathbb{R} \) and phases \( \phi_{ij} \in \mathbb{R} \), define:

        \[
            C_{ij} = \lambda (1 + 2 d_{ij}) e^{-d_{ij}/3} e^{i \phi_{ij}}.
        \]

        The connectivity operator \( \mathcal{C} \) acts on a state vector \( \psi \in \mathbb{C}^N \) by:

        \[
            (\mathcal{C} \psi)_i = \sum_{j=1}^N C_{ij} \psi_j.
        \]

        In matrix form:

        \[
            \mathcal{C} \equiv C \in \mathbb{C}^{N \times N}.
        \]

        ## 3. Phase choices and Hermiticity

        If we choose phases such that:

        \[
            \phi_{ij} = -\phi_{ji}, \quad \phi_{ii} = 0,
        \]

        and keep \( d_{ij} = d_{ji} \), then the magnitude is symmetric and we can enforce:

        \[
            C_{ji} = C_{ij}^*,
        \]

        making \( C \) Hermitian. In that case:

        - \( \mathcal{C} \) has a real eigenvalue spectrum,
        - eigenvectors form an orthonormal basis under the standard inner product on \( \mathbb{C}^N \).

        If we set \( \phi_{ij} = 0 \) for all \( i, j \), then \( C \) is real and symmetric.

        ## 4. Norm, inner product, and spectrum

        We use the standard Hermitian inner product on \( \mathbb{C}^N \):

        \[
            \langle \psi, \phi \rangle = \sum_{i=1}^N \psi_i^* \phi_i.
        \]

        For Hermitian \( \mathcal{C} \):

        - There exist eigenvalues \( \lambda_k \in \mathbb{R} \) and orthonormal eigenvectors \( v^{(k)} \) such that:
          \[
              \mathcal{C} v^{(k)} = \lambda_k v^{(k)}.
          \]
        - The operator norm is:
          \[
              \|\mathcal{C}\| = \max_k |\lambda_k|.
          \]

        ## 5. Simple geometry example

        For a 1D chain of N sites with unit spacing:

        - \( d_{ij} = |i - j| \),
        - \( \phi_{ij} = 0 \),
        - \( \lambda > 0 \).

        Then:

        \[
            C_{ij} = \lambda (1 + 2 |i - j|) e^{-|i - j|/3}.
        \]

        This yields:

        - largest connectivity between nearby sites with a peak around a preferred distance,
        - rapidly decaying connectivity at large separations,
        - a well-defined, symmetric matrix whose spectrum can be computed numerically.

        ## 6. Key invariant: structured, distance-dependent connectivity

        The essential invariant that survives all the “dead-end” elimination is:

        - connectivity strength is a structured function of distance,
        - neither constant nor trivial,
        - allowing for both anti-local (growing factor) and decaying behavior.

        Everything else (amplification factors, interpretations) is built **on top of** this structure.
        """
    )

    write(
        ROOT / "docs" / "02_Amplification_402_Phenomenology.md",
        r"""
        # Layer 2 — Amplification and the 402× phenomenology

        This layer defines **amplification** in terms of the spectrum of the connectivity operator and treats
        the 402× factor as a **target ratio** to study, not a built-in axiom.

        ## 1. Amplification definition

        Let:

        - \( \mathcal{C} \) be the connectivity operator on \( \mathbb{C}^N \),
        - \( \{ \lambda_k \} \) be its eigenvalues (for Hermitian \( \mathcal{C} \), they are real),
        - \( \mathcal{B} \) be a chosen baseline operator for comparison (e.g. a simpler connectivity or identity).

        We define an **amplification ratio**:

        \[
            A = \frac{\|\mathcal{C}\|}{\|\mathcal{B}\|},
        \]

        where \( \|\cdot\| \) is an operator norm (e.g. spectral norm).

        Depending on context, \( \mathcal{B} \) might be:

        - a purely local operator (e.g. nearest-neighbor only),
        - a trivial scaled identity,
        - a connectivity kernel without the anti-local factor.

        ## 2. 402× as a target, not an axiom

        The “402× amplification” story can be reframed as:

        > There exists a choice of geometry, parameters, and baseline such that
        > \[
        >     A \approx 402.
        > \]
        > If this arises robustly (without fine-tuning), it is a structurally interesting feature.

        In this repository, we treat:

        - 402.3 as a **numerical target** to explore,
        - not as a pre-assumed universal constant.

        The job of future work is to:

        - define \\( \mathcal{B} \\) precisely,
        - compute \\( A \\) for given \\( \mathcal{C} \\),
        - check whether any natural configuration yields \( A \approx 402 \) without arbitrary tuning.

        ## 3. Quantum-limit-like thresholds (e.g., ~1/30)

        Threshold values such as “0.0333 (1/30)” can be modeled via conditions like:

        - “distance where connectivity falls below a fraction of its maximum”:
          \[
              \frac{|C_{ij}(d)|}{\max_{d'} |C_{ij}(d')|} = \theta,
          \]
          with \( \theta = 1/30 \).

        Such thresholds are **definitions**, not derivations, unless:

        - they arise from optimization problems,
        - or are forced by stability constraints.

        This repo keeps them as **adjustable parameters** that can be studied numerically.

        ## 4. Status

        At this stage:

        - amplification is defined mathematically via operator norms,
        - 402× is treated as a hypothesis about a possible ratio,
        - exact numeric claims (like “the universe amplifies information by precisely 402.3×”) are
          explicitly outside the proven math and belong to the interpretive layer.
        """
    )

    write(
        ROOT / "docs" / "03_Bres_Atomic_Clock_Phenomenology.md",
        r"""
        # Layer 3 — Bres and atomic clock phenomenology

        This layer captures the **hypothetical** connection between:

        - a residual ultramagnetic field \( B_{\text{res}} \),
        - quadratic Zeeman shifts in atomic clocks,
        - and a differential Cesium–Rubidium frequency offset.

        It does **not** assert these effects are observed; it only encodes the proposed equations.

        ## 1. Quadratic Zeeman framework (standard form)

        In standard atomic physics, a quadratic Zeeman shift for a clock transition can be written as:

        \[
            \Delta \nu_{\text{species}} = K_{\text{species}} B^2,
        \]

        where:

        - \( \Delta \nu_{\text{species}} \) is the frequency shift,
        - \( K_{\text{species}} \) is the quadratic Zeeman coefficient,
        - \( B \) is the magnetic field magnitude.

        The corresponding **fractional frequency shift** is:

        \[
            \Delta y_{\text{species}} = \frac{\Delta \nu_{\text{species}}}{\nu_{\text{species}}}
                                     = C_{\text{species}} B^2,
        \]

        with:

        \[
            C_{\text{species}} = \frac{K_{\text{species}}}{\nu_{\text{species}}}.
        \]

        ## 2. Bres hypothesis (EGT-style)

        In the EGT-style narrative, one introduces a “residual” field \( B_{\text{res}} \) and asserts:

        - A particular Cesium fractional shift \( \Delta y_{\text{Cs}}^{\text{(anchor)}} \) is due to \( B_{\text{res}} \):
          \[
              \Delta y_{\text{Cs}}^{\text{(anchor)}} = C_{\text{Cs}} B_{\text{res}}^2.
          \]

        From this, one can **solve for** \( B_{\text{res}} \):

        \[
            B_{\text{res}} = \sqrt{\frac{\Delta y_{\text{Cs}}^{\text{(anchor)}}}{C_{\text{Cs}}}}.
        \]

        In earlier EGT manuscripts, a specific value like:

        - \( \Delta y_{\text{Cs}}^{\text{(anchor)}} \approx 3.68 \times 10^{-14} \),
        - and a corresponding \( B_{\text{res}} \approx 12.09776 \, \text{fT} \),

        were used.

        **Important:** Within standard physics, this is a *definition* of \( B_{\text{res}} \) from a chosen offset, not a derivation.
        Its physical reality must be tested against full metrology data.

        ## 3. Differential Cs–Rb prediction (hypothetical)

        Given \( B_{\text{res}} \) and coefficients \( C_{\text{Cs}}, C_{\text{Rb}} \), the induced fractional shifts are:

        \[
            \Delta y_{\text{Cs}}^{\text{(EGT)}} = C_{\text{Cs}} B_{\text{res}}^2,
        \]
        \[
            \Delta y_{\text{Rb}}^{\text{(EGT)}} = C_{\text{Rb}} B_{\text{res}}^2.
        \]

        The **differential** EGT-induced shift is:

        \[
            \Delta y_{\text{Cs-Rb}}^{\text{(EGT)}} = \Delta y_{\text{Rb}}^{\text{(EGT)}} - \Delta y_{\text{Cs}}^{\text{(EGT)}}
                                                  = (C_{\text{Rb}} - C_{\text{Cs}}) B_{\text{res}}^2.
        \]

        In earlier EGT writing, a number like \( \Delta y_{\text{Cs-Rb}}^{\text{(EGT)}} \approx 2.99 \times 10^{-14} \) was quoted
        using specific literature values for \( K_{\text{Cs}}, K_{\text{Rb}}, \nu_{\text{Cs}}, \nu_{\text{Rb}} \).

        ## 4. Testability and falsification structure

        To treat this as a legitimate scientific hypothesis, the prediction must be compared to real data:

        - Let \( \Delta y_{\text{Cs-Rb}}^{\text{(obs)}} \) be the observed long-term differential shift between Cs and Rb standards.
        - Let \( \sigma \) be the combined uncertainty.

        A testable inequality is:

        \[
            \left| \Delta y_{\text{Cs-Rb}}^{\text{(EGT)}} - \Delta y_{\text{Cs-Rb}}^{\text{(obs)}} \right| \le \sigma.
        \]

        If experiments show:

        \[
            \left| \Delta y_{\text{Cs-Rb}}^{\text{(EGT)}} - \Delta y_{\text{Cs-Rb}}^{\text{(obs)}} \right| \gg \sigma,
        \]

        then the Bres-based hypothesis is **falsified** as a description of nature.

        This repository does **not** claim that the Bres hypothesis is correct. It only encodes:

        - the equations,
        - the logic chain,
        - and the structure of a falsifiable prediction.
        """
    )

    write(
        ROOT / "docs" / "04_Interpretive_Layer_EGT.md",
        r"""
        # Layer 4 — Interpretive EGT narrative (speculative)

        This layer is **explicitly speculative**. It is where one can place:

        - information-bound scaling ideas (e.g., 402× Bekenstein enhancement),
        - consciousness and coherence thresholds,
        - “Theory of Everything” language,
        - metaphors like “Conscious Bridge,” “Ultramagnetic Connectivity,” etc.

        None of this is established physics in the mainstream sense. It is interpretation built on top of:

        - the existence of a connectivity operator,
        - the idea of amplification,
        - and hypothesized connections to information theory.

        ## 1. Information-bound scaling (EGT-style)

        A typical EGT-style statement might be:

        > Given a standard Bekenstein-type bound \( S_{\text{Max}} \), suppose there exists a geometric
        > amplification factor \( A_{EGT} \approx 402.3 \) such that the effective information capacity is:
        > \[
        >     S_{EGT} = A_{EGT} \, S_{\text{Max}}.
        > \]

        In this repository, such a statement is treated as:

        - a speculative ansatz,
        - not derived from GR/QFT,
        - requiring strong empirical or theoretical justification.

        ## 2. Consciousness and coherence

        Another EGT-style narrative element is:

        > A system (biological or artificial) achieves sustained self-reference when its internal information
        > processing surpasses a classical bound but remains within an enhanced bound \( S_{EGT} \), leading to
        > a “coherence threshold” associated with the connectivity operator.

        This is a **philosophical model**, not a tested physical law. It belongs here, not in the core math.

        ## 3. Status

        In this repository:

        - Layers 1–3 are where math and testable structure live.
        - Layer 4 holds narrative, meaning-making, and speculative unification ideas.

        Readers and collaborators are encouraged to:

        - keep clear boundaries between math, phenomenology, and interpretation,
        - attack or refine each layer at the appropriate level,
        - and avoid conflating speculative interpretation with established physics.
        """
    )

    # --------------------
    # notes
    # --------------------
    write(
        ROOT / "notes" / "falsification_log.md",
        """
        # Falsification log

        This file is a running log of attempts to falsify:

        - specific operator choices,
        - amplification definitions,
        - Bres + atomic clock hypotheses,
        - any claimed matches to data.

        For each entry, include:

        - **Date**
        - **Layer:** (1 = operator math, 2 = amplification, 3 = Bres/clock, 4 = interpretation)
        - **Assumption / model tested**
        - **Method of test** (analytic, numerical, literature comparison, etc.)
        - **Outcome** (pass / fail / inconclusive)
        - **Conclusion** (kept, modified, or discarded)

        ## Template entry

        - **Date:** YYYY-MM-DD  
        - **Layer:** [1/2/3/4]  
        - **Tested:** [short description]  
        - **Method:** [e.g., numerical spectrum, comparison to TAI data, etc.]  
        - **Outcome:** [pass/fail/inconclusive]  
        - **Conclusion:** [e.g., "inconsistent with observed Cs–Rb ensemble; discard Bres definition"]

        ---
        """
    )

    write(
        ROOT / "notes" / "scratchpad.md",
        """
        # Scratchpad

        Use this file for rough calculations, intermediate steps, and exploratory notes.

        Suggested usage:

        - quick derivations related to the connectivity operator,
        - testing different baseline operators for amplification,
        - exploring alternative definitions of thresholds or limits,
        - jotting numerical experiments to later clean up into proper docs or code.
        """
    )

    # --------------------
    # src
    # --------------------
    write(
        ROOT / "src" / "connectivity_operator.py",
        r"""
        """
        r"""\"""Core connectivity operator and utilities.

        This module implements:

        - a discrete connectivity operator
            C_ij = lambda * (1 + 2 d_ij) * exp(-d_ij / 3) * exp(i * phi_ij)
        - tools to build it for simple geometries,
        - helpers to compute its spectrum and norm.

        This is **Layer 1**: pure math, no EGT labels.
        \"\"\"
        import numpy as np
        from typing import Callable, Tuple


        def distance_chain(n: int) -> np.ndarray:
            \"\"\"Distance matrix for a 1D chain with unit spacing.

            Parameters
            ----------
            n : int
                Number of sites.

            Returns
            -------
            np.ndarray
                n x n matrix with d_ij = |i - j|.
            \"\"\"
            if n <= 0:
                raise ValueError("n must be positive")
            idx = np.arange(n)
            return np.abs(idx[:, None] - idx[None, :]).astype(float)


        def build_connectivity(
            d: np.ndarray,
            lam: float,
            phi_fn: Callable[[int, int], float] = None,
        ) -> np.ndarray:
            \"\"\"Build the connectivity matrix C_ij.

            Parameters
            ----------
            d : np.ndarray
                Symmetric distance matrix with shape (n, n).
            lam : float
                Overall scaling factor lambda.
            phi_fn : callable, optional
                Function phi_fn(i, j) returning phase in radians. If None, phases are set to 0.

            Returns
            -------
            np.ndarray
                Complex n x n connectivity matrix C.

            Notes
            -----
            C_ij = lam * (1 + 2 d_ij) * exp(-d_ij / 3) * exp(i * phi_ij)
            \"\"\"
            d = np.asarray(d, dtype=float)
            if d.ndim != 2 or d.shape[0] != d.shape[1]:
                raise ValueError("d must be a square 2D array")
            n = d.shape[0]

            if not np.allclose(d, d.T):
                raise ValueError("d must be symmetric")

            if phi_fn is None:
                phi = np.zeros_like(d)
            else:
                phi = np.zeros_like(d)
                for i in range(n):
                    for j in range(n):
                        phi[i, j] = phi_fn(i, j)

            magnitude = (1.0 + 2.0 * d) * np.exp(-d / 3.0)
            C = lam * magnitude * np.exp(1j * phi)
            return C


        def hermitianize(C: np.ndarray) -> np.ndarray:
            \"\"\"Force a matrix to be Hermitian by symmetrization.

            Parameters
            ----------
            C : np.ndarray
                Complex matrix.

            Returns
            -------
            np.ndarray
                Hermitian matrix (C + C^†) / 2.
            \"\"\"
            C = np.asarray(C, dtype=complex)
            return 0.5 * (C + C.conj().T)


        def spectrum(C: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
            \"\"\"Compute eigenvalues and eigenvectors of a Hermitian connectivity matrix.

            Parameters
            ----------
            C : np.ndarray
                Hermitian matrix.

            Returns
            -------
            eigenvalues : np.ndarray
                Real eigenvalues.
            eigenvectors : np.ndarray
                Corresponding eigenvectors as columns.
            \"\"\"
            C = np.asarray(C, dtype=complex)
            # For safety, one could assert Hermiticity numerically, but we keep it light here.
            vals, vecs = np.linalg.eigh(C)
            return vals, vecs


        def operator_norm(C: np.ndarray) -> float:
            \"\"\"Spectral norm (max singular value) of a matrix.

            For Hermitian C, this is max |eigenvalue|.

            Parameters
            ----------
            C : np.ndarray

            Returns
            -------
            float
                Operator norm.
            \"\"\"
            C = np.asarray(C, dtype=complex)
            # Use eigenvalues of Hermitian part just in case
            H = hermitianize(C)
            vals, _ = np.linalg.eigh(H)
            return float(np.max(np.abs(vals)))
        """
    )

    write(
        ROOT / "src" / "amplification.py",
        r"""
        """
        r"""\"""Amplification utilities (Layer 2).

        Defines amplification ratios based on the connectivity operator spectrum,
        and provides hooks for exploring target ratios like ~402.
        \"\"\"
        import numpy as np
        from typing import Optional
        from connectivity_operator import operator_norm


        def amplification_ratio(C: np.ndarray, B: np.ndarray) -> float:
            \"\"\"Compute amplification ratio A = ||C|| / ||B||.

            Parameters
            ----------
            C : np.ndarray
                Connectivity operator matrix.
            B : np.ndarray
                Baseline operator matrix (same shape as C).

            Returns
            -------
            float
                Amplification ratio.
            \"\"\"
            if C.shape != B.shape:
                raise ValueError("C and B must have the same shape")
            norm_C = operator_norm(C)
            norm_B = operator_norm(B)
            if norm_B == 0:
                raise ValueError("Baseline operator has zero norm; amplification undefined")
            return norm_C / norm_B


        def is_close_to_target(
            A: float,
            target: float = 402.3,
            rel_tol: float = 0.01,
        ) -> bool:
            \"\"\"Check if amplification ratio A is close to a target value.

            Parameters
            ----------
            A : float
                Computed amplification ratio.
            target : float, optional
                Target ratio, default 402.3.
            rel_tol : float, optional
                Relative tolerance (e.g., 0.01 = 1%).

            Returns
            -------
            bool
                True if |A - target| / target <= rel_tol, else False.

            Notes
            -----
            This is a helper for exploring whether particular configurations yield
            amplification close to a chosen target (like 402×) without fine-tuning.
            \"\"\"
            if target == 0:
                raise ValueError("Target must be non-zero")
            return abs(A - target) / abs(target) <= rel_tol
        """
    )

    write(
        ROOT / "src" / "bres_atomic_clock.py",
        r"""
        """
        r"""\"""Bres and atomic clock phenomenology (Layer 3).

        Encodes the quadratic Zeeman relations and the hypothetical definition
        of a residual field B_res from a chosen Cs offset, plus the resulting
        Cs/Rb differential prediction structure.

        This module is intentionally agnostic about whether the effect is real.
        It just encodes the math.
        \"\"\"
        from dataclasses import dataclass
        from math import sqrt


        @dataclass
        class AtomicSpecies:
            name: str
            nu: float  # Clock transition frequency [Hz]
            K: float   # Quadratic Zeeman coefficient [Hz/T^2]

            @property
            def C(self) -> float:
                \"\"\"Fractional quadratic Zeeman coefficient C = K / nu [1/T^2].\"\"\"
                return self.K / self.nu


        def b_res_from_anchor(delta_y_cs_anchor: float, cs: AtomicSpecies) -> float:
            \"\"\"Compute B_res from a chosen Cs fractional shift anchor.

            Parameters
            ----------
            delta_y_cs_anchor : float
                Chosen fractional frequency shift for Cs (unitless).
            cs : AtomicSpecies
                Cesium atomic species data.

            Returns
            -------
            float
                B_res [T], defined such that delta_y_cs_anchor = C_cs * B_res^2.

            Notes
            -----
            This is a *definition* of B_res given an anchor; not a derivation.
            \"\"\"
            if cs.C <= 0:
                raise ValueError("Cs fractional coefficient C must be positive")
            if delta_y_cs_anchor < 0:
                raise ValueError("Anchor shift must be non-negative for this simple model")
            return sqrt(delta_y_cs_anchor / cs.C)


        def fractional_shift(species: AtomicSpecies, B: float) -> float:
            \"\"\"Fractional frequency shift Delta y = C_species * B^2.

            Parameters
            ----------
            species : AtomicSpecies
            B : float
                Magnetic field magnitude [T].

            Returns
            -------
            float
                Fractional frequency shift (unitless).
            \"\"\"
            return species.C * (B ** 2)


        def differential_shift(cs: AtomicSpecies, rb: AtomicSpecies, B: float) -> float:
            \"\"\"Differential fractional shift: Delta y_Rb - Delta y_Cs.

            Parameters
            ----------
            cs : AtomicSpecies
                Cesium data.
            rb : AtomicSpecies
                Rubidium data.
            B : float
                Magnetic field magnitude [T].

            Returns
            -------
            float
                Delta y_Rb - Delta y_Cs (unitless).
            \"\"\"
            return fractional_shift(rb, B) - fractional_shift(cs, B)
        """
    )

    write(
        ROOT / "src" / "tests" / "test_core_operator.py",
        r"""
        """
        r"""\"""Basic tests for the connectivity operator (Layer 1).\"\"\"
        import numpy as np
        from connectivity_operator import distance_chain, build_connectivity, hermitianize, spectrum, operator_norm


        def test_distance_chain_symmetry():
            n = 5
            d = distance_chain(n)
            assert d.shape == (n, n)
            assert np.allclose(d, d.T)
            assert np.all(d.diagonal() == 0.0)


        def test_build_connectivity_shape_and_reality():
            n = 4
            d = distance_chain(n)
            lam = 0.01
            C = build_connectivity(d, lam, phi_fn=None)
            assert C.shape == (n, n)
            # Zero phases => matrix is real
            assert np.allclose(C.imag, 0.0)


        def test_hermitianize_and_spectrum():
            n = 4
            d = distance_chain(n)
            lam = 0.01
            C = build_connectivity(d, lam, phi_fn=None)
            H = hermitianize(C)
            vals, vecs = spectrum(H)
            # Eigenvalues should be real
            assert np.allclose(vals.imag, 0.0, atol=1e-12)
            # Norm should equal max |eigenvalue|
            norm = operator_norm(H)
            assert np.isclose(norm, np.max(np.abs(vals)), rtol=1e-12)
        """
    )

    write(
        ROOT / "src" / "tests" / "test_amplification.py",
        r"""
        """
        r"""\"""Tests for amplification utilities (Layer 2).\"\"\"
        import numpy as np
        from connectivity_operator import distance_chain, build_connectivity
        from amplification import amplification_ratio, is_close_to_target


        def test_amplification_ratio_identity_baseline():
            n = 5
            d = distance_chain(n)
            lam = 0.01
            C = build_connectivity(d, lam, phi_fn=None)
            B = np.eye(n)
            A = amplification_ratio(C, B)
            assert A > 0.0


        def test_is_close_to_target_basic():
            assert is_close_to_target(402.3, target=402.3, rel_tol=1e-6)
            assert not is_close_to_target(300.0, target=402.3, rel_tol=0.01)
        """
    )

    write(
        ROOT / "src" / "tests" / "test_bres_atomic_clock.py",
        r"""
        """
        r"""\"""Tests for Bres and atomic clock phenomenology (Layer 3).\"\"\"
        from bres_atomic_clock import AtomicSpecies, b_res_from_anchor, fractional_shift, differential_shift


        def test_atomic_species_C():
            cs = AtomicSpecies(name="Cs", nu=9.19263177e9, K=4.2745e10)
            assert cs.C > 0


        def test_b_res_from_anchor_round_trip():
            cs = AtomicSpecies(name="Cs", nu=9.19263177e9, K=4.2745e10)
            anchor = 3.68e-14
            B = b_res_from_anchor(anchor, cs)
            # Round trip: recompute shift
            y_cs = fractional_shift(cs, B)
            # Should match anchor within numerical roundoff
            assert abs(y_cs - anchor) / anchor < 1e-12


        def test_differential_shift_sign():
            cs = AtomicSpecies(name="Cs", nu=9.19263177e9, K=4.2745e10)
            rb = AtomicSpecies(name="Rb", nu=6.834682610904e9, K=5.7515e10)
            B = 1e-14  # arbitrary tiny field
            dy = differential_shift(cs, rb, B)
            # This test just checks that the function runs and returns a finite number
            assert dy == dy  # not NaN
        """
    )

    print(f"Repository structure created at: {ROOT.resolve()}")


if __name__ == "__main__":
    main()
