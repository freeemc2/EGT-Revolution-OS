# theory/ — Core EGT Framework

The foundational papers and derivations. These are the load-bearing documents; everything in `empirical/` and `predictions/` depends on them.

## Files

- **`egt-main.tex` / `egt-main.pdf`** — the primary theory paper. Introduces the Connectivity Operator C(r), derives `r_opt = 2.5`, states the amplification `A_EGT ≈ 402.3`, and connects to Dark Matter and Higgs Hierarchy problems. Currently contains introduced parameters (κ ≈ 0.6370, D_Annih = 2.15, C_Sup ≡ A_EGT) that are asserted axiomatically rather than derived; addressing these is ongoing work.
- **`egt-core-reduction.md`** — the minimal-operator reduction underneath the C(r) formulation. Two distinguishable elements, one transfer, one conservation invariant. This is the "no postulates, no infinities, no arbitrary constants, no assumed geometry" ground floor. Foundation for the six-postulate structure.
- **`quantum-geometric-coherence-402.pdf`** — companion paper on the 402× amplification factor as an emergent geometric-coherence property.
- **`six-constants-origin.md`** — retroactive reconstruction of the origins of each of the six numeric constants in C(r), mapping to established frameworks (perturbative QFT, holographic entanglement entropy, Yukawa screening, Berry phase, holographic large-N). Written by the author with AI assistance April 2026; the mappings are post-hoc rather than derivations, but they identify the neighborhood each constant sits in.
- **`egt-constants.json`** — machine-readable constants used throughout the framework:
  - `A_EGT = 402.3` (universal amplification)
  - `G_M = 1.324` (geometric multiplier for Pioneer)
  - `B_res = 12.09776 fT` (ultramagnetic resonance)
  - `CCA_Shift = 2.99e-14` (Cs-Rb clock differential prediction)
  - `w_DE = -0.9975` (dark energy equation of state prediction)
  - `seasonal_variance = 0.05` (5% annual sinusoidal prediction)
- **`prior-thinkers.md`** — engagement with predecessors whose methods or intuitions approached similar territory (Émile Meyerson, others). Not a claim of derivation from their work — a claim that the reduction instinct EGT uses has a lineage worth acknowledging.

## Known open problems

Documented here so they can be worked on transparently rather than hidden:

1. **κ derivation.** The paper introduces κ ≈ 0.6370 as a "quantum geometric coupling constant" but does not derive it from prior building blocks. Needs either a derivation from |C(r_opt)|, the phase deficit π/2, and one other identified constant — or explicit acknowledgment as a fitted parameter.
2. **G_M = 1.324 for Pioneer.** Called an "axiomatic multiplier" but not derived. Needs derivation from A_EGT, r_opt, and cosmological baseline, or acknowledgment as fitted.
3. **D_Annih = 2.15 for Dark Matter density.** Same status — derived from r_opt and phase leakage in principle but the derivation is not written down.
4. **C_Sup ≡ A_EGT.** The Higgs hierarchy cancellation currently comes from defining the vacuum suppression capacity equal to A_EGT. This is circular; the physical mechanism that would force this equality needs to be given.
