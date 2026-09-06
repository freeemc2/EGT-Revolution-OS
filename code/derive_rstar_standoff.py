#!/usr/bin/env python3
"""
derive_rstar_standoff.py  (aria, 2026-09-05)
What is r_star for the COIL, and where is the rho=2.5 standoff shell?
In Brian's operator only. r_opt=2.5 is a STABLE trap (|C|^2 max => V=-|C|^2 min).
Honest: r_star is a CHOICE of natural length; compute candidates, defend the best,
state what the measurement determines.
"""
import numpy as np

mu0 = 4*np.pi*1e-7
f   = 22030.0                 # coil operating freq (N=415 park)
a   = 0.04445                 # 3" SCH40 OD/2 = winding radius (m)
Lw  = 0.222                   # winding length 8.75 in (m)
rho_cu = 1.68e-8              # copper resistivity

def C2(r): return (1+2*r)**2*np.exp(-2*r/3)

print("r_opt=2.5 is a STABLE equilibrium: |C|^2 is MAX there (V=-|C|^2 is a well).")
print(f"  |C|^2(2.4)={C2(2.4):.4f}  |C|^2(2.5)={C2(2.5):.4f}  |C|^2(2.6)={C2(2.6):.4f}  -> peak at 2.5")
print("  => a test mass is TRAPPED at rho=2.5 from both sides. A standoff shell.\n")

print("WHY a loop HAS a natural length (not arbitrary):")
print("  On-axis loop field B(z)=mu0*I*a^2/(2(a^2+z^2)^1.5): flat for z<a, falls for z>a.")
print("  The loop's OWN field scale-length is its radius a. That is the physical r_star.\n")

print(f"{'candidate r_star':>28s} {'value (mm)':>12s} {'2.5*r_star (mm)':>16s}  note")
print("-"*80)
# A: coil radius (defended)
print(f"{'coil radius a (DEFENDED)':>28s} {a*1e3:12.2f} {2.5*a*1e3:16.1f}  loop field scale-length")
# B: skin depth (too small)
delta = np.sqrt(rho_cu/(np.pi*f*mu0))
print(f"{'skin depth delta':>28s} {delta*1e3:12.3f} {2.5*delta*1e3:16.3f}  sub-winding, not a mass shell")
# C: winding half-length
print(f"{'winding half-length':>28s} {Lw/2*1e3:12.2f} {2.5*(Lw/2)*1e3:16.1f}  axial extent variant")

print("\n"+"="*80)
print("SEALED PREDICTION")
print("="*80)
print(f"""  CORE (firm, EM-distinguishing, qualitative):
    A driven coil traps a test mass at a STABLE STANDOFF SHELL (rho=2.5) -- the
    mass parks at a distance and holds, it does NOT stick to the coil face.
    Ordinary EM pulls any magnetizable/conductive mass to the coil (standoff->0)
    and does nothing to a dielectric. So:
      (a) a stable nonzero standoff  => NOT pure EM attraction
      (b) the SAME standoff for a DIELECTRIC mass (glass/PTFE) as for metal
          => the coupling is material-independent (the C(r) signature)

  QUANTITATIVE (leading candidate, r_star = coil radius a):
    standoff ~ 2.5*a = {2.5*a*1e3:.0f} mm on-axis from the coil center (~11 cm).
    Scales as 2.5*a per coil, so OG and Quad (both 3" formers) predict the SAME shell.

  WHAT THE MEASUREMENT DETERMINES:
    The measured standoff distance = 2.5*r_star  =>  it DETERMINES r_star for the
    coil. If it lands at ~111 mm, r_star = coil radius (loop-field scale) confirmed.
    A different stable standoff tells us r_star is a different coil length -- still
    a result, still not EM (EM has no standoff at all).

  FALSIFIES: pure-EM explanation (no standoff / dielectric inert).
  DOES NOT PROVE: a gravity anomaly (that needs force-on-mass magnitude, still open).
""")
