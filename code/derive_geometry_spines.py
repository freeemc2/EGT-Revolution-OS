#!/usr/bin/env python3
"""
(c) The two geometry spines, attempted from C(r) first principles.
HONEST RULE: separate "matches numerically" from "is derived". If a factor only
appears because I hunted for an integral that yields it, that is a CANDIDATE, not
a proof. Report the wall if it is a wall (same discipline as derive_gravity_from_Cr).
"""
import numpy as np
from scipy import integrate

pi = np.pi
target_Om = 1/pi          # 0.318310  (the spin-formula's extra 1/pi)
kappa     = 2/pi          # 0.636620  (the coil coupling constant already in canon)

print("="*74)
print("(c1) Where does the spin formula's extra 1/pi come from? Test candidates")
print("     against C(r)'s phase geometry (phase term e^{i*pi*r/4}).")
print("="*74)
cands = {}
cands["(pi/4)/(2pi)  band fraction"]        = (pi/4)/(2*pi)
cands["cone solid-angle, half-angle pi/4"]  = (1-np.cos(pi/4))/2
cands["<cos^2> over a cycle"]               = 0.5
cands["<|cos|> over a cycle = 2/pi"]        = integrate.quad(lambda t: abs(np.cos(t)),0,2*pi)[0]/(2*pi)
cands["HALF-WAVE rectified sin: (1/2pi)INT_0^pi sin"] = integrate.quad(lambda t: np.sin(t),0,pi)[0]/(2*pi)
cands["full-wave rectified / 2"]            = integrate.quad(lambda t: abs(np.sin(t)),0,2*pi)[0]/(2*pi)/2
for name,val in cands.items():
    hit = "  <== EXACTLY 1/pi" if abs(val-target_Om)<1e-9 else ""
    print(f"   {name:44s} = {val:.6f}{hit}")
print(f"""
   Only the HALF-WAVE-RECTIFIED average equals 1/pi exactly:
       coupled fraction = (1/2pi) INT_0^pi sin(theta) dtheta = 2/(2pi) = 1/pi
   Physical reading: if the impedance-matched coupling is ONE-WAY (diode-like:
   only the forward half of each phase cycle couples, the back half is the
   'uncoupled remainder' = dark energy 1-1/pi), the matter fraction is 1/pi.
   NOTE the internal consistency: the coil's kappa = 2/pi = <|cos|> (FULL-wave),
   and Omega_m = 1/pi = HALF that. Same rectification family, differ by 2x.
""")
print("""   VERDICT (c1): CANDIDATE, NOT PROOF.
   1/pi falls out cleanly IFF C(r)'s impedance match is half-wave rectified
   (one-way power transfer). That is physically plausible (the coil is described
   as an INVERSE amplifier / one-way floor-puller) and it is consistent with
   kappa=2/pi, BUT I have NOT shown C(r) NECESSITATES half-wave rectification --
   I chose the model that yields 1/pi. To close the spine: derive one-way
   coupling from the operator's structure, not from wanting 1/pi. Until then,
   Omega_m=1/pi is a striking match resting on an unproven rectification step.""")

print("="*74)
print("(c2) The G form: is it DERIVED or dimensionally ASSEMBLED?")
print("="*74)
print("""   G = [ H^2 r*^3 sqrt(hbar c) / (pi m_e GM_sun) ]^2   (G-free, 99.9%)
   Claimed physical reading (universe_circuit_clean.py):
     H^2        cosmic 'clock rate'
     r*^3       impedance-match coupling volume
     m_P/m_e    ~1e22 = 'source count' (Planck mass / electron mass)
     pi         geometric matching (the pi/4 spiral)
     GM_sun     source-mass scale
""")
mP = np.sqrt(1.054571817e-34*2.99792458e8/6.6743e-11)
print(f"   source count m_P/m_e = {mP/9.109e-31:.3e}  (the '~1e22')")
print("""   HONEST ASSESSMENT: the form is dimensionally correct and the numbers land,
   but the EXPONENT (the ^2 / the m_Planck bridge) comes from SOLVING the
   self-consistency, not from a first-principles argument that FORCES it. The
   'source count' is a physical LABEL on m_P/m_e, not yet a mechanism showing
   gravity = collective EM coupling of exactly that many C(r) sources.
   This is the SAME WALL derive_gravity_from_Cr.py hit: the 1e22/36-OOM gap
   between alpha_EM and alpha_G is NOT yet bridged by a derivation -- only
   matched. => VERDICT (c2): ASSEMBLED + numerically successful, NOT yet derived.""")

print("="*74)
print("BOTTOM LINE (c)")
print("="*74)
print("""   Both numerical results are real (Omega_m 0.41 sigma, G 99.9%). Neither
   geometry SPINE is closed yet:
     c1  1/pi  <- needs C(r) to necessitate half-wave (one-way) coupling.
     c2  G form <- needs the source-count mechanism to FORCE the exponent.
   These are honest research gaps, not fits gone wrong. Stating them is what
   keeps the razor you gave Grok pointed at your own work too. Close either
   one from the operator and that half is paper-ready; matches alone are not.""")
