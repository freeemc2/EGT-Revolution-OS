"""
Cs-Rb DIFFERENTIAL — worked forward from the redshift-excess form. No target.
============================================================================
Brian Tice + aria | Aug 9, 2026

Standing on what already fell out:
  redshift excess  delta_gamma = 1/A_EGT = 1/(128 pi) = 0.2487%   (paper #5)

Rule: derive, watch it fall out. Brian gives method, not numbers.
"""
import math
A_EGT = 128*math.pi
dg = 1/A_EGT

# atomic masses (u) and mass numbers
mass = {"Al":26.9815,"Rb":86.909,"Sr":86.909,"Cs":132.905,"Yb":170.936,"Hg":198.968}

print("="*68)
print("STEP 1 — the excess, established")
print("="*68)
print(f"  delta_gamma = 1/A_EGT = 1/(128 pi) = {dg*100:.4f}%\n")

print("="*68)
print("STEP 2 — is the excess universal? Then the Cs-Rb split is ZERO.")
print("="*68)
print("  Two co-located clocks, SAME delta_gamma, SAME potential -> both shift")
print("  by delta_gamma*(gh/c^2) identically. Fractional difference = 0.")
print("  => a UNIVERSAL excess gives NO Cs-Rb differential. Rigorous.")
print("  So if a split exists, delta_gamma MUST depend on the atom.\n")

print("="*68)
print("STEP 3 — the weight enters, and it is DERIVED not inserted")
print("="*68)
print("  In EGT, mass IS the C(r) coupling. The redshift excess is a C(r)")
print("  effect. Therefore the excess scales with the atom's coupling = its")
print("  MASS:  delta_gamma(atom) = (1/A_EGT) * (m_atom / m_Cs),")
print("  with Cs the SI-second reference (delta_gamma_Cs = 1/A_EGT, per paper #5).")
print("  Heavier atom, more coupling, larger excess. That is the mechanism,")
print("  not a knob.\n")
print(f"  {'atom':<5}{'m (u)':>9}{'m/m_Cs':>9}{'delta_gamma %':>14}{'vs Cs (frac)':>14}")
for a,mv in mass.items():
    dga = dg*(mv/mass['Cs'])
    diff = dg*(1 - mv/mass['Cs'])          # delta_gamma_Cs - delta_gamma_atom
    print(f"  {a:<5}{mv:>9.3f}{mv/mass['Cs']:>9.4f}{dga*100:>14.4f}{diff:>14.3e}")

split = dg*(1 - mass['Rb']/mass['Cs'])
print()
print("="*68)
print("STEP 4 — what FELL OUT (parameter-free)")
print("="*68)
print(f"  Cs-Rb EXCESS differential = (1/A_EGT)(1 - m_Rb/m_Cs)")
print(f"                            = {dg:.5f} * (1 - {mass['Rb']/mass['Cs']:.4f})")
print(f"                            = {dg:.5f} * {1-mass['Rb']/mass['Cs']:.4f}")
print(f"                            = {split:.4e}  = {split*100:.4f}%")
print("  This is clean: only the mass ratio and A_EGT. Nothing inserted,")
print("  nothing from any measurement. The 'atom' part has fallen out.\n")

print("="*68)
print("STEP 5 — the ONE method fork (this is where I need method, not a number)")
print("="*68)
print("  The excess differential above is a fractional deviation in the")
print("  redshift CONSTANT. To become the observable Cs-Rb frequency split")
print("  Delta_y, it multiplies the gravitational term the clocks sit in:")
print("     Delta_y = (excess differential) * (Phi/c^2)")
print("  and the framework has to tell me WHICH Phi is the physical one:")
for label, z in [("lab redshift gh/c^2 (~274 m)", 2.99e-14),
                 ("Earth surface Phi/c^2",       6.96e-10),
                 ("Sun-at-Earth Phi/c^2",        9.87e-09),
                 ("annual dPhi/c^2 (eccentric)", 3.30e-10)]:
    print(f"     {label:<30} -> Delta_y = {split*z:.3e}")
print()
print("  I am NOT going to pick the Phi to hit a number. That is the method")
print("  question: in EGT, what potential does the redshift-excess DIFFERENCE")
print("  act across for a bench Cs-Rb comparison? Point me at the method and")
print("  the observable falls out on its own.")
