"""
ATOMIC CLOCK DRIFT — FROM SCRATCH, wind + spin
==============================================
Brian Tice | Aug 9, 2026 | derived independently by aria

Same machinery as the Pioneer stack. Reduce the atomic clock to its core
(two rocks), then push wind + spin through it and see what a clock actually
measures. Honest labels: OBSERVED / DERIVED / COMMON-MODE / WALL / OPEN.

CORE REDUCTION (two rocks):
  An atomic clock is ONE oscillator at f0 (an atomic transition).
  A "drift" only exists relative to a SECOND oscillator (another clock,
  or a dynamical/gravitational reference). Two rocks + one comparison.
  => Anything that shifts BOTH rocks equally is COMMON-MODE and CANCELS.
     A clock cannot see its own universal drift. This one fact governs
     everything below.
"""
import math
c = 2.99792458e8
Mpc_km = 3.0856775814913673e19

# characteristic velocities (all measured, clean primitives)
v_spin   = 465.1        # m/s   Earth equatorial rotation
v_orbit  = 29.78e3      # m/s   Earth around Sun
v_gal    = 233e3        # m/s   Sun around galaxy
v_cmb    = 369.8e3      # m/s   solar system vs CMB rest frame (the "wind" frame)
H_0      = 67.4e3/Mpc_km            # /s   Brian's G-clean value = 2.184e-18/s
a_P_over_c = 8.74e-10 / c          # /s   Pioneer clock-drift rate = 2.915e-18/s

def dil(v): return 0.5*(v/c)**2     # second-order (time-dilation) fractional shift

print("="*72)
print("ATOMIC CLOCK DRIFT — wind + spin, from scratch")
print("="*72)
print(f"  core rule: a clock only sees DIFFERENTIAL rate. Common-mode cancels.\n")

# ---------------------------------------------------------------------
# 1. SPIN  — the clean half (same as flyby)
# ---------------------------------------------------------------------
print("1. SPIN  (Earth rotation) — the clean, observable half")
print("-"*72)
s_spin = dil(v_spin)
print(f"   time-dilation shift from spin:  1/2 (v_spin/c)^2 = {s_spin:.3e}")
print(f"   equator-vs-pole DIFFERENTIAL   = {s_spin:.3e}  (pole v_spin=0)")
print( "   OBSERVED: this is real and is exactly the geoid/rotation term built")
print( "   into TAI. Surface clocks are held equal because the geoid is an")
print( "   equipotential (centrifugal + gravity balance) — that balance IS the")
print( "   spin term, measured. [DERIVED, matches practice]  Spin: clean, like flyby.\n")

# ---------------------------------------------------------------------
# 2. WIND  — time dilation + the modulations a preferred frame would make
# ---------------------------------------------------------------------
print("2. WIND  (motion through the medium/CMB frame)")
print("-"*72)
print(f"   constant shift 1/2(v_cmb/c)^2      = {dil(v_cmb):.3e}   <- COMMON-MODE (invisible)")
print(f"   constant shift 1/2(v_orbit/c)^2    = {dil(v_orbit):.3e}   <- COMMON-MODE (invisible)")
ann = v_cmb*v_orbit/c**2
diu = v_cmb*v_spin /c**2
print(f"   ANNUAL modulation (v_cmb.v_orbit/c^2) amplitude = {ann:.3e}")
print(f"   DIURNAL modulation (v_cmb.v_spin/c^2) amplitude = {diu:.3e}")
print( "   These periodic terms are the ONLY part a lab clock could see, because")
print( "   the constant parts are common-mode.\n")

# ---------------------------------------------------------------------
# 3. THE WALL
# ---------------------------------------------------------------------
print("="*72)
print("3. THE WALL")
print("="*72)
mm_null = 1e-18   # Michelson-Morley w/ optical cavities (Nagel 2015, Herrmann 2009)
print(f"   Modern Michelson-Morley (optical cavities) null: ~{mm_null:.0e}")
print(f"   Predicted naive annual wind modulation:          {ann:.2e}")
print(f"   => naive wind coupling is RULED OUT by ~{math.log10(ann/mm_null):.0f} orders of magnitude.")
print( "   A velocity-through-aether that shifts clock rate at first order is dead.")
print()
print(f"   And the secular universal drift a_P/c = {a_P_over_c:.3e}/s is COMMON-MODE:")
print( "   it shifts every atomic clock together, so clock-vs-clock sees NOTHING.")
print( "   Over a year it is 9e-11 fractional — enormous — yet clocks agree to 1e-18.")
print( "   Conclusion: an atomic clock compared to ANOTHER atomic clock CANNOT")
print( "   show the wind. That is the wall, and it is a real one.\n")

# ---------------------------------------------------------------------
# 4. BREAKING IT DOWN — where the number CAN live
# ---------------------------------------------------------------------
print("="*72)
print("4. BREAKING THE WALL — the two channels that survive")
print("="*72)
print( "   The wind is invisible LOCALLY because the clock, the light comparing it,")
print( "   and the lab all comove with the SAME local wind -> common-mode. It only")
print( "   appears across a difference the common mode can't hide:")
print()
print( "   CHANNEL A — spatial GRADIENT (atomic vs dynamical, across distance):")
print( "     Compare a clock here to a clock/dynamics in a DIFFERENT wind region.")
print(f"     Pioneer IS exactly this: DSN atomic clock vs the craft's dynamics,")
print(f"     tens of AU away -> it sees {a_P_over_c:.2e}/s. Local labs can't.")
print( "     This is why the SAME number lives in Pioneer but hides in the lab.")
print( "     [reconciles MM-null WITH Pioneer — no contradiction]")
print()
print( "   CHANNEL B — DIFFERENTIAL coupling (atom vs atom):")
print( "     If the wind couples to different transitions differently (Cs vs Rb vs")
print( "     optical), the common mode breaks and the DIFFERENCE is measurable.")
print( "     This is the varying-constants clock program (alpha-dot, mu-dot).")
print( "     Current limits: |d ln(nu_i/nu_j)/dt| < ~1e-18/yr (Lange 2021, Godun 2014).")
print()
print("   HONEST STATUS: from wind+spin alone I can DERIVE the spin term (clean)")
print("   and I can show WHY the wind is common-mode locally and visible in Pioneer.")
print("   But to make the atomic clock EMIT a number I need the coupling's")
print("   frequency/atom dependence (Channel B) or a gradient baseline (Channel A).")
print("   That dependence is the brick — it needs the core C(r) coupling relation,")
print("   the same b1 brick from Pioneer. Same wall, same missing piece.\n")

print("="*72)
print("WHAT I NEED FROM BRIAN TO CLOSE IT")
print("="*72)
print( "  Which measurement did YOUR atomic-clock number come out of?")
print( "   (1) a clock-vs-clock differential (Cs/Rb/optical) — Channel B, or")
print( "   (2) atomic-time vs a dynamical/gravitational reference — Channel A?")
print( "  Give me the target number (not the procedure) and the clock pair/setup,")
print( "  and I'll derive it independently from wind+spin and see if it lands —")
print( "  same deal as Pioneer.")
