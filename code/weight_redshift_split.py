"""
WEIGHT-DRIVEN REDSHIFT EXCESS + ATOM SPLIT (Option 2)
=====================================================
Brian Tice | Aug 9, 2026 | aria

Mechanism (Brian): in EGT mass IS the C(r) coupling, so the gravitational-
redshift EXCESS rides the atom's WEIGHT. One lever solves both:
  - EXCESS: universal amplitude 1/A_EGT = 1/(128pi) = 0.248%  (already clean)
  - ATOM:   the excess scales with weight -> Cs and Rb split by their mass diff.

Test it honestly against the target(s) and the equivalence-principle (LPI) bound.
"""
import math
A_EGT = 128*math.pi
excess0 = 1/A_EGT                      # 0.2487%  universal amplitude (C(r) fingerprint)
c = 2.99792458e8; g = 9.80665

# atomic masses (u)
m = {"Al":26.9815,"Rb":86.909,"Sr":86.9089,"Cs":132.905,"Yb":170.936,"Hg":198.968,"H":1.00783}

print("="*70)
print("PART 1 — the EXCESS (universal amplitude), already parameter-free")
print("="*70)
print(f"  1/A_EGT = 1/(128 pi) = {excess0*100:.4f}%  == matrix #7 (0.248%)  [SOLVED]\n")

print("="*70)
print("PART 2 — WEIGHT scaling makes the excess atom-dependent")
print("="*70)
print("  Model: excess(atom) = (1/128pi) * (m_atom / m_Cs), calibrated so the")
print("  SI-defining atom (Cs) carries exactly 0.248%. Heavier -> more, lighter")
print("  -> less. The Cs-X difference is the predicted split.\n")
print(f"  {'atom':<5}{'mass(u)':>9}{'excess %':>10}{'Cs-X diff (frac)':>18}")
for name,mass in m.items():
    ex = excess0*(mass/m['Cs'])
    diff = excess0*(1 - mass/m['Cs'])   # Cs minus this atom, in excess fraction
    print(f"  {name:<5}{mass:>9.3f}{ex*100:>10.4f}{diff:>18.3e}")

# Cs-Rb specifically
dEx_CsRb = excess0*(1 - m['Rb']/m['Cs'])
print(f"\n  Cs-Rb excess difference (fractional) = {dEx_CsRb:.3e}  ({dEx_CsRb*100:.4f}%)")

print("\n" + "="*70)
print("PART 3 — turn the split into an OBSERVABLE, check against LPI bound")
print("="*70)
# A composition-dependent redshift excess shows up when the potential changes.
# Observable Cs-Rb frequency-ratio variation = dEx_CsRb * (redshift depth probed)
for label, z in [("Earth surface Phi/c^2", 6.96e-10),
                 ("Sun-at-Earth Phi/c^2", 9.87e-9),
                 ("annual dPhi/c^2 (eccentric orbit)", 3.3e-10)]:
    obs = dEx_CsRb * z
    print(f"  {label:<34} z={z:.2e} -> Cs-Rb shift = {obs:.2e}")
print()
print("  LPI (null-redshift) bound on composition-dependent redshift: ~1e-6.")
print(f"  Our Cs-Rb excess difference {dEx_CsRb:.2e} ({dEx_CsRb*100:.3f}%) is ~{dEx_CsRb/1e-6:.0f}x")
print("  ABOVE that bound -> naive FULL-weight scaling is RULED OUT by LPI tests.")
print("  => the weight-dependence must be strongly SUPPRESSED (the excess is")
print("     ~universal with only a tiny weight tail). The split is real but small.")

print("\n" + "="*70)
print("PART 4 — what 2.99e-14 is, and the honest state")
print("="*70)
z_lab = g*274/c**2
print(f"  g*(274 m)/c^2 = {z_lab:.3e}  == 2.99e-14 == matrix #6 (Levi 2004).")
print("  So #6 is the STANDARD gravitational redshift at the lab height, which")
print("  EGT reproduces (gravity = C(r) gain). It is NOT the Cs-Rb weight split.")
print()
print("  HONEST SCORECARD on 'weight difference solves both':")
print("   - EXCESS (0.248%) : SOLVED, = 1/(128pi), parameter-free. YES.")
print("   - #6 (2.99e-14)   : the lab-altitude redshift, reproduced. YES (trivially).")
print("   - ATOM split      : weight-scaling gives the RIGHT SIGN and a real split,")
print("     but FULL-weight scaling overshoots the LPI bound by ~800x. So the")
print("     magnitude needs a suppression I have not derived (or the split is a")
print("     tiny weight-tail, testable at ~1e-7 by optical-clock LPI tests).")
print()
print("  To pin the split magnitude I need ONE thing: is the Cs-Rb number a")
print("  redshift correction (=#6, done) or a measured frequency-RATIO drift, and")
print("  over what potential? That sets the suppression and closes it.")
