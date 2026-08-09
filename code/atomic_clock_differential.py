"""
ATOMIC CLOCK DIFFERENTIAL — chasing the Bohr-radius coupling lead
================================================================
Brian Tice | Aug 9, 2026 | aria (took the lead, clean run)

Lead: put different clock atoms on the C(r) curve and see if a differential
drift falls out. Honest labels throughout. No fudging to hit a target.

C(r) coupling strength: g(rho) = (1+2 rho) exp(-rho/3)   [real envelope]
Pioneer secular rate (done):  (4/3)H_0 = 2.912e-18 /s
"""
import math
c = 2.99792458e8
alpha_fs = 1/137.035999           # fine-structure constant (NOT the C(r) alpha=1/3)
H_0 = 67.4e3/3.08567758e22        # /s
drift_43H0 = (4/3)*H_0            # 2.912e-18 /s
yr = 3.1557e7
v_wind = 447.4e3                  # m/s  solar wind (framework value)

def g(rho): return (1+2*rho)*math.exp(-rho/3)

# clock species: name -> Z
clocks = {"Al+":13, "H":1, "Rb":37, "Sr":38, "Cs":55, "Yb+":70, "Hg+":80}

print("="*72)
print("STEP 0  the 'r*_atom = Bohr radius' lead — is it deep or trivial?")
print("="*72)
a0 = 5.29177e-11
v_e = alpha_fs*c                  # Bohr velocity
w_e = v_e/a0                      # Bohr angular frequency
print(f"  v_e = alpha*c = {v_e:.3e} m/s ;  w_e = v_e/a0 = {w_e:.3e} /s")
print(f"  r*_atom = v_e/w_e = {v_e/w_e:.3e} m  (= a0)")
print("  HONEST: r* = v/omega = v/(v/r) = r for ANY circular orbit. So r*_atom=a0")
print("  is a TAUTOLOGY, not a new result. (At solar/cosmic scale r* is deep")
print("  because v_wind and omega are DIFFERENT physical quantities; at the atom")
print("  they are the same orbit.) Not overselling this.\n")

print("="*72)
print("STEP 1  atoms on the C(r) curve at rho = Z*alpha")
print("="*72)
print(f"  {'clock':<6}{'Z':>4}{'rho=Z*alpha':>13}{'g(rho)':>10}")
gvals = {}
for name,Z in clocks.items():
    rho = Z*alpha_fs
    gvals[name] = g(rho)
    print(f"  {name:<6}{Z:>4}{rho:>13.4f}{gvals[name]:>10.4f}")
print("  Real Z-dependent coupling: g ranges ~1.15 (Al+) to ~1.78 (Hg+).")
print("  So the atoms DO sit at genuinely different points on C(r). Good.\n")

print("="*72)
print("STEP 2  the differential drift — two candidate base rates")
print("="*72)
pairs = [("Yb+","Cs"),("Cs","Rb"),("Hg+","Al+"),("Sr","Cs")]
print("  (A) if it rides the secular (4/3)H_0 rate:")
print(f"    {'pair':<12}{'dg':>8}{'drift /yr':>14}")
for i,j in pairs:
    dg = gvals[i]-gvals[j]
    d = dg*drift_43H0*yr
    print(f"    {i+'/'+j:<12}{dg:>8.3f}{d:>14.2e}")
print("    measured clock-comparison limits: ~1e-17 to 1e-18 /yr")
print("    => (A) OVERPREDICTS by ~5-6 orders. RULED OUT as written.")
print("    Resolution: lab clocks have NO receding baseline. The (4/3)H_0 drift")
print("    is a path-length effect (Pioneer's medium column GROWS as it recedes).")
print("    A lab clock's column is fixed -> the secular term does NOT apply to it.")
print("    So the correct lab prediction from this channel is ZERO, not 1e-12.\n")

vc2 = (v_wind/c)**2
print("  (B) if it is a preferred-frame shift ~ (v_wind/c)^2:")
print(f"    (v_wind/c)^2 = {vc2:.3e}")
for i,j in pairs:
    dg = gvals[i]-gvals[j]
    print(f"    {i+'/'+j:<12} static differential = {dg*vc2:.2e}")
print("    This is a STATIC offset (absorbed in calibration). Its only")
print("    observable is annual/diurnal MODULATION as Earth's velocity turns —")
print("    and optical-cavity Michelson-Morley bounds that to ~1e-18.")
print("    => (B) is bounded below detection. No positive number.\n")

print("="*72)
print("HONEST VERDICT")
print("="*72)
print("""  Chasing the lead cleanly, the atomic clock does NOT hand over a new
  positive number the way Pioneer did. Both channels close:
   - secular (4/3)H_0 needs a growing medium column (Pioneer has it; a lab
     clock does not) -> lab prediction ZERO, consistent with every null.
   - preferred-frame (v/c)^2 differential is real but its observable
     modulation is MM-bounded to ~1e-18 -> below detection.
  The framework is CONSISTENT with all atomic-clock nulls (it does not
  overpredict once the baseline point is handled), and it makes a FRONTIER
  prediction: any real lab clock-vs-clock differential sits at ~<=1e-18,
  right where BACON/Lange 2021 are now probing. That is a prediction, not
  a retrodicted match.

  So: I did not manufacture a '2.9 falls out here' — because honestly it
  doesn't fall out of a LAB clock. Pioneer needed a receding baseline;
  the lab clock has none. The number that 'dropped out' of your clock data
  must come from a specific comparison (which clocks, vs WHAT reference,
  over what baseline). Point me at that and I'll reconstruct it exactly.""")
