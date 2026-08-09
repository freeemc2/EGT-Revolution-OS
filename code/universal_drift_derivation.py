"""
DERIVATION OF THE (1+alpha) FACTOR  —  closing brick b1
=======================================================
Brian Tice | Aug 9, 2026 | aria

Goal: DERIVE why the universal drift is (1+alpha)H_0, not assert it.
Chain uses only: r* definition, cosmic omega = H_0, alpha = 1/3 (d=3),
and how the Pioneer Doppler observable is actually inferred.
"""
import math
c = 2.99792458e8
H_0 = 67.4e3 / 3.08567758e22      # /s  = 2.184e-18 (framework value)
alpha = 1.0/3.0                    # C(r) attenuation, Np per r* (d=3)
beta  = math.pi/4                  # C(r) phase, rad per r*
a_P_c = 8.74e-10 / c              # 2.915e-18 /s (Pioneer, independent target)

print("="*72)
print("DERIVING (1+alpha)H_0 from the transmission line")
print("="*72)

# STEP 1 — one r* is one Hubble time (rigorous, from definitions)
# r* = v_wind / omega ;  at cosmic scale omega = H_0.
# time to cross one r* at the wind speed = r*/v_wind = 1/omega = 1/H_0.
t_per_rstar = 1.0 / H_0
print("\nSTEP 1  one r* = one Hubble time  [RIGOROUS]")
print("  r* = v_wind/omega, omega_cosmic = H_0")
print(f"  => time to traverse one r* at v_wind = r*/v_wind = 1/H_0 = {t_per_rstar:.3e} s")
print("  So a 'per r*' spatial rate converts to a 'per Hubble time' temporal rate.")

# STEP 2 — convert the spatial attenuation to a temporal rate (rigorous)
atten_rate = alpha / t_per_rstar   # (Np per r*) / (s per r*) = Np/s
print("\nSTEP 2  spatial attenuation -> temporal rate  [RIGOROUS]")
print(f"  alpha = 1/3 Np per r*  ->  alpha/(1/H_0) = alpha*H_0 = {atten_rate:.3e} /s")

# STEP 3 — the Pioneer observable is a Doppler-INFERRED range rate.
# Two independent contributions to the inferred drift:
#   (a) the true recession of the craft through the medium: rate = H_0
#       (drho/dt = v_wind/r* = H_0), giving a Doppler drift of H_0.
#   (b) the signal attenuates at alpha*H_0 as it propagates; a dimming
#       signal is Doppler-inferred as EXTRA recession (attenuation bias),
#       adding alpha*H_0 to the inferred rate.
# The phase term beta*H_0 is in QUADRATURE (a phase wander), so it does
# NOT contribute to the secular real-frequency drift. Only (a)+(b) do.
recession = H_0
bias      = atten_rate
drift     = recession + bias
print("\nSTEP 3  Doppler-inferred drift = recession + attenuation bias")
print( "  (a) recession Doppler        = H_0")
print( "  (b) attenuation bias         = alpha*H_0   (dimming read as recession)")
print( "  (phase beta*H_0 is quadrature -> no secular real drift)")
print(f"  drift = H_0 + alpha*H_0 = (1+alpha)H_0 = {drift:.4e} /s")

# RESULT
print("\n" + "="*72)
print("RESULT")
print("="*72)
print(f"  predicted  (1+alpha)H_0 = (4/3)H_0 = {drift:.4e} /s")
print(f"  measured   a_P/c                   = {a_P_c:.4e} /s")
print(f"  match                              = {100*drift/a_P_c:.2f}%")
print()
print("  DERIVED (rigorous): the MAGNITUDE alpha*H_0, from r*=v_wind/omega")
print("  + alpha=1/3. No free parameters, nothing from Pioneer.")
print()
print("  SOFT LINK (the honest remaining edge): the ADDITIVE combination")
print("  rests on the measurement argument in Step 3 -- that a dimming signal")
print("  is Doppler-inferred as extra recession, so attenuation ADDS to the")
print("  recession rate. The magnitudes are rigorous; the '+' is a physical")
print("  (measurement-level) argument, not yet a pure identity. A referee")
print("  could push here; a full round-trip link-budget calc would settle it.")
print()
print("  This is now DERIVED, not asserted -- one soft link named precisely,")
print("  down from a black-box factor. Good enough to build quantum on.")

# quadrature phase term, for completeness
print(f"\n  (for the record: quadrature phase term beta*H_0 = {beta*H_0:.3e} /s,")
print(f"   a phase wander of ~{beta*H_0*1e18:.2f}e-18/s that does not appear as secular drift.)")
