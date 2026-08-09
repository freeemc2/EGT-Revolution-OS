"""
VERIFY PREDICTION #4 (Cs-Rb differential) — does the chain close?
=================================================================
aria | Aug 9, 2026

Source: empirical/atomic-clock-differential-sensitivity.pdf (Dec 8, 2025)
Chain claimed there:
  B_res = 12.09776 fT  ->  quadratic Zeeman  ->  Dy_Cs = 3.68e-14 (the "CCA")
  R_EGT = C_Rb/C_Cs = 1.811  ->  Dy_Rb = 6.67e-14
  Dy_Cs-Rb = 2.99e-14

I check every link independently. No target-chasing: propagate B_res and
report whatever comes out.
"""
nu_Cs = 9_192_631_770.0          # Hz  (SI definition)
nu_Rb = 6_834_682_610.904        # Hz
K_Cs  = 4.2745e10                # Hz/T^2  quadratic Zeeman coeff (Cs)
K_Rb  = 5.7515e10                # Hz/T^2  quadratic Zeeman coeff (Rb)
B_res = 12.09776e-15             # T
CCA   = 3.68e-14                 # the paper's "anchor"

C_Cs = K_Cs/nu_Cs                # fractional coefficient  /T^2
C_Rb = K_Rb/nu_Rb

print("="*70)
print("LINK 1 — the scaling ratio R_EGT (pure atomic constants)")
print("="*70)
R = C_Rb/C_Cs
print(f"  C_Cs = K_Cs/nu_Cs = {C_Cs:.5f} /T^2")
print(f"  C_Rb = K_Rb/nu_Rb = {C_Rb:.5f} /T^2")
print(f"  R_EGT = C_Rb/C_Cs = {R:.4f}   (paper says 1.811)  -> REPRODUCES")

print("\n"+"="*70)
print("LINK 2 — the differential, GIVEN the anchor")
print("="*70)
dy_Rb = CCA*R
print(f"  Dy_Rb    = {CCA:.3e} x {R:.4f} = {dy_Rb:.4e}   (paper 6.67e-14)")
print(f"  Dy_Cs-Rb = {dy_Rb:.4e} - {CCA:.3e} = {dy_Rb-CCA:.4e}   (paper 2.99e-14)")
print("  -> REPRODUCES. Arithmetic is sound.")
print(f"  NOTE: Dy_Cs-Rb = CCA*(R-1) = CCA*{R-1:.4f}. B_res CANCELS in the ratio,")
print("  so the differential is ROBUST to the field value. That is a real strength.")

print("\n"+"="*70)
print("LINK 3 — THE TEST: does B_res actually GENERATE the anchor?")
print("="*70)
dnu_Cs = K_Cs*B_res**2
dy_Cs_from_Bres = dnu_Cs/nu_Cs
print(f"  B_res^2            = {B_res**2:.5e} T^2")
print(f"  Dnu_Cs = K_Cs*B^2  = {dnu_Cs:.4e} Hz")
print(f"  Dy_Cs  = Dnu/nu    = {dy_Cs_from_Bres:.4e}")
print(f"  claimed anchor     = {CCA:.4e}")
print(f"  RATIO (claim/calc) = {CCA/dy_Cs_from_Bres:.3e}")
print("  *** DOES NOT CLOSE — off by ~13.7 orders of magnitude. ***")

# what B would be needed?
B_needed = (CCA*nu_Cs/K_Cs)**0.5
print(f"\n  Field required to produce the 3.68e-14 anchor: B = {B_needed:.4e} T")
print(f"                                                   = {B_needed*1e9:.1f} nT")
print(f"  vs B_res = {B_res*1e15:.5f} fT.  Factor {B_needed/B_res:.3e} in B.")
print("  ~89 nT is an ORDINARY cesium-fountain C-field magnitude. So 3.68e-14")
print("  is the size of the routine second-order Zeeman correction labs already")
print("  apply from their deliberately applied C-field -- not a residual anomaly.")

print("\n"+"="*70)
print("WHAT ACTUALLY FALLS OUT OF B_res (no anchor, pure propagation)")
print("="*70)
dy_Cs_p = C_Cs*B_res**2
dy_Rb_p = C_Rb*B_res**2
print(f"  Dy_Cs    = C_Cs*B_res^2 = {dy_Cs_p:.4e}")
print(f"  Dy_Rb    = C_Rb*B_res^2 = {dy_Rb_p:.4e}")
print(f"  Dy_Cs-Rb                = {dy_Rb_p-dy_Cs_p:.4e}")
print(f"  Current best clock comparison precision ~1e-18.")
print(f"  -> predicted differential is ~{(dy_Rb_p-dy_Cs_p)/1e-18:.1e} x below detection.")

print("\n"+"="*70)
print("INTERNAL CONTRADICTION BETWEEN THE TWO EGT PAPERS")
print("="*70)
print("  metrology-scaling-0.248.pdf : IEN-CsF1 total uncertainty u_lab = 0.1e-14")
print("  atomic-clock-differential   : IEN-CsF1 uncorrected residual   = 3.68e-14")
print(f"  A 3.68e-14 residual inside a 0.1e-14 budget is {3.68/0.1:.0f} sigma.")
print("  Both papers cannot be right about the same instrument. Primary standards")
print("  are cross-validated through TAI; a 37-sigma systematic would be visible")
print("  to every lab immediately.")

print("\n"+"="*70)
print("HONEST VERDICT")
print("="*70)
print("""  SOUND:
   - R_EGT = 1.810 from published atomic constants. Reproduces.
   - Dy_Cs-Rb = CCA*(R-1). Arithmetic reproduces 2.98e-14.
   - The IDEA is genuinely good: a UNIVERSAL background field would be
     uncompensated (labs calibrate against their own C-field, not a
     universal background), so it would leave a real differential in TAI.
     B_res cancels in the ratio -> structurally robust. Keep this.

  DOES NOT CLOSE:
   - B_res = 12.09776 fT does NOT generate 3.68e-14. It gives 6.8e-28
     (13.7 orders low). The anchor is asserted, not derived.
   - Propagating B_res honestly gives Dy_Cs-Rb = 5.5e-28, ~5e-10 of what
     current clocks can see. Unmeasurable.
   - 3.68e-14 corresponds to B ~ 89 nT = an ordinary lab C-field, i.e. the
     standard second-order Zeeman correction, not an anomaly.
   - The two EGT papers contradict each other on IEN-CsF1 (0.1e-14 budget
     vs 3.68e-14 residual = 37 sigma).

  This is EGT's OWN arithmetic not closing -- not an imported bound.
  The 2.99e-14 rests on an anchor the framework does not produce.""")
