# Indistinguishability from Node-Swap Invariance

**Brian Tice**
Axion Resonance Labs
b@axionresonance.com
November 2026

## Abstract

Two particles of the same type are two nodes at the same coupling position ρ on the C(r) lattice. The kernel sees only ρ — there is no internal label, no name tag, nothing that distinguishes node one from node two except where they sit. Swapping them leaves the lattice configuration unchanged. Indistinguishability is forced by the framework, not assumed.

## 1. The Swap Operation

Consider two nodes at positions ρ₁ and ρ₂. A swap exchanges their positions. If ρ₁ = ρ₂, the post-swap configuration is identical to the pre-swap configuration: same nodes, same coupling positions, same transfer functions. The state before and after the swap is the same element of the configuration space.

For distinguishable particles, the swap would map to a different state. For identical particles, it maps to the same state. The kernel has no mechanism to produce a different state, because its only input is ρ.

## 2. Bosons: Symmetric Combination

The kernel's phase has two directions: forward e^(iπρ/4) and conjugate e^(-iπρ/4). For bosons, both rings enter with positive sign. The two-particle state is the symmetric sum:

|ψ₊〈 = (|forward〈 + |conjugate〈) / √2

Swapping the particles leaves this unchanged. The state is invariant under the swap, consistent with Bose symmetry.

## 3. Fermions: Antisymmetric Combination

For fermions, the swap sends one particle from the forward ring to the conjugate ring. The antisymmetrizer forces a minus sign. The fermionic state is:

|ψ₋〈 = (|forward〈 − |conjugate〈) / √2

The minus is not inserted by hand. It is the orthogonality of the two rings: their inner product vanishes because the phases are complex conjugates. A second fermion attempting to occupy the same ρ tries to form the same combination and finds the inner product zero. Pauli exclusion is ring geometry.

## 4. What This Is Not

It is not a derivation of spin from first principles. The forward/conjugate split is taken from the kernel's phase term, but why half-integer spin maps to the antisymmetric ring rather than some other structure is not closed. The claim is narrower: given the two-ring structure, symmetry and antisymmetry are forced, and exclusion follows.

## 5. Falsifiable Check

If indistinguishability is node-swap invariance, then any observable that depends on particle labels at fixed ρ must be symmetric (bosons) or antisymmetric (fermions) under exchange. A labeled-particle interference experiment at a single coupling position that breaks this symmetry would falsify the reading.

## References

- Tice, B. 2026. EGT Completions: Poincaré, Hodge, Riemann. lightning-equalization. Zenodo.
- Tice, B. 2026. Double-Slit Ring Derivation. lightning-equalization. Zenodo.
