"""
THE MISSING MASS — EM-visible vs gluonic (collider) mass in clock atoms
======================================================================
Brian's unblock: the atomic weight used in an EM coupling is wrong, because
~99% of nucleon mass is QCD/gluon energy the X-ray can't see but the collider
(DIS) did. C(r) is EM -> it couples to the charged/quark part, not the gluonic
dark inertia. The right coupling variable is EM-active mass / total mass, and
its ATOM-to-ATOM variation comes from collider data (parton/gluon structure,
EMC effect), not atomic tables.
"""
# nucleon mass budget (MeV), proton ~ 938.272
m_nucleon = 938.9              # avg nucleon
mq_rest   = 9.0               # sum of u,u,d rest masses (Higgs origin) ~1%
gluon_qcd = m_nucleon - mq_rest
print("="*70)
print("NUCLEON MASS BUDGET (what the X-ray misses)")
print("="*70)
print(f"  quark REST mass (Higgs, EM-adjacent) : {mq_rest:6.1f} MeV  ({100*mq_rest/m_nucleon:.1f}%)")
print(f"  QCD / gluon field + KE + anomaly     : {gluon_qcd:6.1f} MeV  ({100*gluon_qcd/m_nucleon:.1f}%)")
print("  -> ~99% of every nucleon is gluonic energy: neutral, EM-invisible,")
print("     only revealed by deep inelastic scattering (collider).")
print("  Momentum sum rule (DIS): quarks ~50%, GLUONS ~50% of momentum.\n")

# clock atoms: Z, A, binding energy per nucleon (MeV) [AME2020-ish]
# BE/A varies -> nuclear QCD binding differs per atom (collider/DIS territory)
atoms = {
 # name : (Z, A, BE_per_A MeV)
 "H-1"   : (1,   1, 0.00),
 "Al-27" : (13, 27, 8.332),
 "Rb-87" : (37, 87, 8.711),
 "Sr-87" : (38, 87, 8.705),
 "Cs-133": (55,133, 8.410),
 "Yb-171": (70,171, 8.022),
 "Hg-199": (80,199, 7.906),
}
print("="*70)
print("PER-ATOM: charge fraction Z/A and nuclear binding fraction")
print("="*70)
print(f"  {'atom':<8}{'Z':>4}{'A':>5}{'Z/A':>8}{'BE/A(MeV)':>11}{'BE massfrac':>12}")
for name,(Z,A,bea) in atoms.items():
    zoa = Z/A
    be_frac = bea/m_nucleon          # binding-energy mass fraction
    print(f"  {name:<8}{Z:>4}{A:>5}{zoa:>8.4f}{bea:>11.3f}{be_frac:>12.5f}")
print()
print("  Two atom-dependent handles the X-ray-only picture omits:")
print("   - Z/A (charge-per-nucleon): 0.50 (light) -> 0.40 (heavy). EM couples")
print("     to Z; inertia is A(+gluonic). So EM-coupling/inertia ~ Z/A falls")
print("     ~20% from Al to Hg. A real, monotonic, atom-dependent suppression.")
print("   - BE/A: nuclear binding per nucleon, 7.9-8.7 MeV (~10% spread). This")
print("     is the nucleus's QCD binding, and it is A-dependent (the collider's")
print("     EMC effect shows the parton structure itself shifts inside nuclei).")
print()
print("="*70)
print("WHAT THIS DOES TO THE COUPLING (direction, not final number)")
print("="*70)
print("""  Before: I treated coupling ~ g(Z*alpha) on the FULL atomic mass.
  Corrected: coupling ~ g(rho) * (EM-active mass / total mass).
  The EM-active fraction is dominated by Z/A (charge) x the quark momentum
  fraction (~0.5 universal) x nuclear modification (EMC, A-dependent).

  This is the piece that was missing 'the first time': the differential
  between clock species is not on their atomic weights, it is on their
  COLLIDER-measured mass structure (Z/A, gluon fraction, EMC), which the
  X-ray/atomic picture cannot supply. That reframes the whole differential.

  I can run the corrected differential once I know which correction you
  used before:
    (1) Z/A charge-per-nucleon suppression (cleanest, computable now)
    (2) quark/gluon momentum fraction (~50%) with EMC A-dependence
    (3) the trace-anomaly / gluon-condensate fraction
  and ideally the NUMBER it produced last time, so I reconstruct it exactly.""")
