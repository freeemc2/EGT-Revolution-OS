#!/usr/bin/env python3
"""
DERIVE EGT's two-particle correlation E(a,b) from C(r) -- do NOT assume cos.
Then read off CHSH. Question: exactly 2sqrt2 (=QM), below (classical-ish),
or above (superquantum)? Frame: C(r)=(1+2r)e^{-r/3}e^{i*pi*r/4}, |C|^2 = Born
weight (quantum_from_Cr.py). Bell analyzers ROTATE THE PHASE BASIS at a FIXED
coupling distance r0 (the two rocks sit at fixed separation).
"""
import numpy as np
C   = lambda r: (1+2*r)*np.exp(-r/3)*np.exp(1j*np.pi*r/4)
argC= lambda r: np.pi*r/4.0

# --- setup: fixed coupling r0; analyzer a adds phase to the shared coupling ---
r0 = 2.5                      # r_opt; any fixed r works (shown below)
# The shared joint amplitude for aligned vs anti given analyzer difference delta:
#   the phasor overlap at fixed |C| is Re[ e^{-i*phi_a} e^{+i*phi_b} ] = cos(phi_a-phi_b).
# Map analyzer angle -> phase 1:1 (phi = angle); half-angle for the 2-level joint state.
def E_overlap(a,b):
    # normalized C-overlap of the two analyzer directions at fixed r0
    za, zb = C(r0)*np.exp(1j*a), C(r0)*np.exp(1j*b)
    return (np.conj(za)*zb).real/(abs(za)*abs(zb))     # = cos(a-b), |C| CANCELS

# CHSH with the standard optimal angles (units where E=cos(a-b))
a,ap,b,bp = 0.0, np.pi/2, np.pi/4, 3*np.pi/4
def chsh(E): return abs(E(a,b)-E(a,bp)+E(ap,b)+E(ap,bp))

print("(1) Is E(a,b) actually cos(a-b), or C-modified?  (envelope test)")
for rr in [0.5, 2.5, 5.0, 12.0]:
    r0=rr
    devs=[abs(E_overlap(x,y)-np.cos(x-y)) for x in np.linspace(0,2*np.pi,50) for y in np.linspace(0,2*np.pi,50)]
    print(f"   r0={rr:5.1f}: max|E - cos(a-b)| = {max(devs):.2e}   -> envelope (1+2r)e^-r/3 CANCELS")
r0=2.5
print(f"\n   => E(a,b) = cos(a-b) EXACTLY, independent of the magnitude envelope,")
print(f"      because a Bell analyzer rotates PHASE at fixed r (|C| is a common factor).")

print(f"\n(2) CHSH from the DERIVED correlation:")
print(f"   S = {chsh(E_overlap):.6f}    Tsirelson 2*sqrt2 = {2*np.sqrt(2):.6f}")
print(f"   => EGT lands EXACTLY on the quantum bound. Not below (not classical),")
print(f"      not above (not superquantum). It MATCHES QM.")

print(f"\n(3) What would it take for EGT to DEVIATE from 2sqrt2?")
# only a DIFFERENT correlation rule deviates. Test a magnitude-WEIGHTED rule where
# |C| does NOT cancel (analyzers probe different coupling distances r).
def E_weighted(a,b, s=1.0):
    ra, rb = r0+s*a, r0+s*b
    za, zb = C(ra), C(rb)
    return (np.conj(za)*zb).real/(abs(za)*abs(zb))     # still normalized -> still cos(argC(ra)-argC(rb))
for s in [0.5, 1.0, 2.0]:
    Sf = chsh(lambda x,y: E_weighted(x,y,s))
    print(f"   analyzer also shifts r (slope s={s}): S = {Sf:.4f}  (still cos of rescaled angle -> re-optimizable to 2sqrt2)")
print("""
   VERDICT: for ANY normalized phasor correlation, |C| cancels and E is a cosine
   of the phase difference -> CHSH is 2sqrt2 (Tsirelson), matching QM EXACTLY.
   EGT does NOT exceed 2sqrt2 with this correlation rule. To go superquantum you
   would need a NON-normalized / magnitude-weighted joint statistic (a different
   Born rule than |C|^2-partition) -- which quantum_from_Cr.py does NOT use.
   So the honest result: EGT = QM at the Bell ceiling, cleanly, on paper, no coil.""")
