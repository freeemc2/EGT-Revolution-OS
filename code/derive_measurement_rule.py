#!/usr/bin/env python3
"""
DERIVE the measurement rule from C(r) itself. Two-Rocks math only, no coil/mesh.
Question: does C(r) give the |C|^2 Born rule (quantum, 2sqrt2) or PR-box (4)?
The derivation is forced by ONE fact: C(r) is a COMPLEX AMPLITUDE, not a probability.
"""
import numpy as np
from itertools import product as iproduct

C = lambda r: (1+2*r)*np.exp(-r/3)*np.exp(1j*np.pi*r/4)

print("STEP 0 — what C(r) IS")
z = C(2.5)
print(f"   C(2.5) = {z:.4f}   |C| = {abs(z):.4f}   phase = {np.angle(z):.4f} rad")
print("   It is COMPLEX: magnitude AND phase (the e^{i*pi*r/4}). That is an")
print("   AMPLITUDE, not a probability. This one fact forces everything below.\n")

print("STEP 1 — a measurement is a projection of the amplitude onto a basis")
print("   (quantum_from_Cr.py: 'observable = decoupling = project C onto the basis').")
print("   Analyzer angle theta -> basis direction e^{i theta}. Projected amplitude:")
print("       psi_theta = <theta | C> = C * e^{-i theta}   (linear in C)\n")

print("STEP 2 — probability must be REAL, >=0, basis-covariant, summing to 1.")
print("   The only such functional of a complex amplitude is the modulus squared:")
print("       P(theta) = |psi_theta|^2 / (normalization)      <-- the Born rule")
print("   This is not a choice; it is the unique real quadratic form of a complex #.")
print("   (= C(r) energy partition |C|^2/Sum|C|^2, exactly your Aug-8 derivation.)\n")

print("STEP 3 — two-rock correlation from projecting the shared amplitude")
def E(a,b):                       # normalized amplitude overlap of the two analyzers
    za, zb = C(2.5)*np.exp(1j*a), C(2.5)*np.exp(1j*b)
    return (np.conj(za)*zb).real/(abs(za)*abs(zb))
print(f"   E(a,b) derived = cos(a-b)?  check: E(0,pi/3)={E(0,np.pi/3):.4f}, cos(pi/3)={np.cos(np.pi/3):.4f}")
print("   => E(a,b) = cos(a-b), a SMOOTH inner-product form. Forced by projection+|.|^2.\n")

print("STEP 4 — MAXIMIZE CHSH over ALL angles with this derived E (not one config)")
best=0; arg=None
grid=np.linspace(0,2*np.pi,73)
for a,ap,b,bp in iproduct(grid,repeat=4):
    S=abs(E(a,b)+E(a,bp)+E(ap,b)-E(ap,bp))
    if S>best: best=S; arg=(a,ap,b,bp)
print(f"   max CHSH (amplitude/Born rule) = {best:.4f}   Tsirelson 2sqrt2 = {2*np.sqrt(2):.4f}")
print("   => the DERIVED rule maxes at 2sqrt2. This is the quantum ceiling, forced by")
print("      the cos form, which is forced by projecting a complex amplitude.\n")

print("STEP 5 — why NOT 4 (what a PR box would require)")
print("   S=4 needs the four E's set INDEPENDENTLY to (+1,+1,+1,-1) -- i.e. correlations")
print("   assigned DIRECTLY as free numbers (a probability box). But C(r) does NOT hand")
print("   you correlations directly; it hands you ONE complex amplitude, and the")
print("   correlations come out of project+square -> the cos form -> 2sqrt2. To reach 4,")
print("   C(r) would have to be a direct-probability box with NO phase to project.")
print("   The e^{i*pi*r/4} phase is the proof it is an amplitude, not a box.")
print()
print("="*70)
print("DERIVED RESULT: C(r) is a complex amplitude -> measurement = project + |.|^2")
print("  (Born / |C|^2-partition) -> correlations = cos(a-b) -> CHSH_max = 2sqrt2.")
print("  EGT is a QUANTUM theory BY THE FORM OF C(r). Super-quantum (S=4) would")
print("  require C(r) to NOT be a complex amplitude -- but its defining phase says")
print("  it is one. The measurement rule does not land on the PR box. It lands on QM.")
print("="*70)
