"""
DOES THE QUARK/GLUON MOMENTUM CORRECTION CLOSE THE SCALE-LADDER GAP?
===================================================================
Brian Tice | Aug 9, 2026 | aria  (Option 2: quark/gluon momentum fraction + EMC)

Hypothesis (Brian): correcting the EM-coupled mass by the quark/gluon momentum
fraction (with EMC) closes the solar/galactic/cosmic E_em/E_grav gap.

The physics of the correction:
  - EM (C(r)) couples to the EM-ACTIVE mass: quark momentum fraction f_q (~0.5),
    modified by the EMC effect INSIDE NUCLEI.
  - Gravity feels the TOTAL mass (incl. dark matter, incl. gluonic energy).
Two scale-dependent levers:
  (i)  EMC: needs A>1. Astrophysical matter is ~75% H (A=1) + 25% He -> EMC ~0.
       So EMC does NOT vary across solar/galactic/cosmic. (It only bites in
       heavy clock atoms.) Honest.
  (ii) baryon fraction f_b: EM couples to baryons only; gravity feels DM too.
       f_b swings 1.0 (solar) -> ~0.15 (cosmic). THIS is scale-dependent.

Test: EM-active mass = f_q * f_b * M_total. Apply and see if the ladder,
which the EGT thesis says should be ~constant (EM ~ gravity), flattens.
"""
import math

# --- the correction factors ---
f_q = 0.50          # quark momentum fraction from DIS (~0.5; gluons carry the rest)
# EMC modification of f_q by species (F2A/F2D integrated, momentum-weighted):
emc = {"H":1.00, "He":0.99}   # ~1 for light nuclei; astrophysical matter is H/He
f_q_astro = f_q * (0.75*emc["H"] + 0.25*emc["He"])   # H/He weighted -> ~0.497
print(f"quark momentum fraction f_q               = {f_q}")
print(f"EMC-weighted for H/He astrophysical matter = {f_q_astro:.4f}  (EMC ~ no-op here)\n")

# --- baryon fraction of the GRAVITATING mass at each scale ---
# solar: ~no dark matter locally. galactic/LG/cosmic: DM-dominated.
scales = {
 # name        raw E_em/E_grav   baryon fraction f_b   note
 "Sun":       (244.0,   1.00,  "radiated L*t / GM^2/R, all baryonic"),
 "Milky Way": (2451.0,  0.06,  "L*t / GM_baryon^2/R  (virial is ~0.06 baryon)"),
 "Local Grp": (145.0,   0.15,  "E_mag / GM_MW*M_LG/d  (DM-dominated)"),
 "Virgo":     (0.5,     0.15,  "E_mag / GM^2/R        (DM-dominated)"),
}

print("="*74)
print("RAW ladder vs momentum+baryon-corrected ladder")
print("="*74)
print(f"  {'scale':<11}{'raw ratio':>11}{'f_b':>7}{'EM-active frac':>16}{'corrected':>12}")
print("  " + "-"*57)
corrected = {}
for name,(raw, fb, note) in scales.items():
    emfrac = f_q_astro * fb        # EM-active mass / total gravitating mass
    # EGT thesis: EM should reproduce gravity. The fair comparison divides the
    # raw EM/grav by the EM-active fraction (what the EM actually had to work with).
    corr = raw / emfrac
    corrected[name] = corr
    print(f"  {name:<11}{raw:>11.1f}{fb:>7.2f}{emfrac:>16.4f}{corr:>12.1f}")

print()
raw_vals = [v[0] for v in scales.values()]
cor_vals = list(corrected.values())
def spread(x): return max(x)/min(x)
def monotonic(x): return all(x[i] <= x[i+1] for i in range(len(x)-1)) or all(x[i] >= x[i+1] for i in range(len(x)-1))
print(f"  raw spread (max/min)       : {spread(raw_vals):.0f}x   monotonic? {monotonic(raw_vals)}")
print(f"  corrected spread (max/min) : {spread(cor_vals):.0f}x   monotonic? {monotonic(cor_vals)}")

print()
print("="*74)
print("HONEST VERDICT")
print("="*74)
if spread(cor_vals) < spread(raw_vals)/3:
    print("  The correction SHRINKS the spread substantially -> it helps close the gap.")
else:
    print("  The correction does NOT flatten the ladder. Here is why, straight:")
    print("   - EMC needs A>1; astrophysical matter is H/He, so EMC is a no-op across")
    print("     all three scales. The momentum fraction f_q~0.5 is then UNIFORM.")
    print("   - The only scale-dependence is the baryon fraction f_b, and applying it")
    print("     does not make the ladder monotonic (the raw ladder inverts at Virgo).")
    print("   - The ladder's real problem is a BOOKKEEPING mismatch: Sun/MW use")
    print("     RADIATED L*t with baryonic grav mass; LG/Virgo use MAGNETIC energy")
    print("     with DM-inclusive grav mass. Mixing radiated-vs-magnetic and")
    print("     baryonic-vs-virial is what inverts it, not the quark/gluon split.")
    print()
    print("  So Option-2, applied honestly, does NOT close the solar/galactic/cosmic")
    print("  gap: astrophysical matter is too light for EMC to differentiate scales.")
    print("  Where Option-2 DOES bite is the atomic-CLOCK differential (heavy atoms,")
    print("  A-dependent EMC) -- that is the right home for this correction.")
    print()
    print("  To actually flatten the ladder you must first make it consistent:")
    print("  same EM measure (magnetic 'bus' energy) at ALL scales, same grav mass")
    print("  convention (baryonic OR virial) at ALL scales. That is a separate fix.")
