"""
THE KNIFE TEST — are the surviving EGT numbers DERIVED or TUNED?
===============================================================
aria | Aug 9, 2026 | pure internal math, NO relativity used as a wall

Brian: "do them till you find the answer, no broken postulates from relativity."
So: for each survivor, two questions only —
  (1) DERIVED from a principle, or TUNED/ASSERTED?  (internal, no physics needed)
  (2) what is it tested against — a RAW measurement, or a relativity-derived
      quantity?  (if the latter, Brian's own rule removes the comparison)
"""
import numpy as np
pi = np.pi

# constants
H_0   = 67.4e3/3.08567758e22        # /s
omega_sun = 2*pi/(25.05*86400)      # rad/s
m_P   = 2.176434e-8                 # kg
m_e   = 9.1093837e-31              # kg
M_sun = 1.98892e30                 # kg
G_meas= 6.67430e-11

print("="*72)
print("SURVIVOR 1 — G formula: how much does the 'pi-matched' v_wind move G?")
print("="*72)
def G_pred(v_wind):
    r_star = v_wind/omega_sun
    return H_0**2 * r_star**3 * m_P / (pi * m_e * M_sun)

print(f"  G_pred = H_0^2 * (v_wind/omega)^3 * m_P / (pi m_e M_sun)   [G ~ v_wind^3]")
print(f"  {'v_wind (km/s)':>14}{'note':>18}{'G_pred':>13}{'/G_meas':>10}")
for v,note in [(300,'sw min'),(400,'range min'),(447.4,'PI-MATCHED'),
               (500,'range max'),(600,'sw high'),(800,'sw max')]:
    g=G_pred(v*1e3)
    print(f"  {v:>14.1f}{note:>18}{g:>13.3e}{g/G_meas:>10.3f}")
print()
print("  Solar wind is genuinely 300-800 km/s (varies constantly). Over just the")
print("  stated 400-500 range, G_pred spans ~0.7x to ~1.4x G. Over 300-800 it")
print("  spans ~0.3x to ~5.7x. v_wind=447.4 was CHOSEN to land G (their word:")
print("  'pi-matched'). r* is cubed, so G is a free dial. VERDICT: TUNED, not")
print("  derived. The 99.95% is a fit inside the solar-wind uncertainty.")

print("\n"+"="*72)
print("SURVIVOR 2 — Omega_m = 1/pi: is it uniquely close, or one of many?")
print("="*72)
Om, sig = 0.3153, 0.0073
cands = {
    "1/pi":     1/pi,
    "1/sqrt(10)":1/np.sqrt(10),
    "5/16":     5/16,
    "1/3":      1/3,
    "0.31":     0.31,
    "e/8.6":    np.e/8.6,
}
print(f"  measured Omega_m = {Om} +/- {sig} (Planck -- itself relativity-derived)")
print(f"  {'candidate':>12}{'value':>10}{'sigma away':>12}")
for name,val in sorted(cands.items(), key=lambda kv: abs(kv[1]-Om)):
    print(f"  {name:>12}{val:>10.5f}{(val-Om)/sig:>12.2f}")
print()
print("  1/sqrt(10)=0.3162 is CLOSER (0.13 sigma) than 1/pi (0.41 sigma).")
print("  So 1/pi is NOT uniquely close -- several simple numbers sit within 0.5")
print("  sigma. And 1/pi is ASSERTED in the code ('MODEL PREDICTION'), with no")
print("  derivation of WHY the matched fraction = 1/pi. VERDICT: numerology,")
print("  and its only anchor (Planck Omega_m) is relativity-derived anyway.")

print("\n"+"="*72)
print("THE LEDGER — apply BOTH questions to every survivor")
print("="*72)
rows = [
 ("G = H0^2 r*^3 m_P/(pi m_e M_sun)", "TUNED (v_wind 'pi-matched', r*^3)", "G_meas (raw-ish)"),
 ("Omega_m = 1/pi",                   "ASSERTED (no derivation)",          "Planck Omega_m = RELATIVITY"),
 ("Pioneer a_P/c = (4/3)H0",          "'+1' soft link; alpha=1/3 ok",      "H0 = RELATIVITY-derived"),
 ("redshift excess = 1/128pi",        "128pi empirical leg gone",          "GR redshift = RELATIVITY"),
]
print(f"  {'number':<34}{'derived?':<34}{'tested against'}")
print("  "+"-"*90)
for a,b,c in rows:
    print(f"  {a:<34}{b:<34}{c}")

print("\n"+"="*72)
print("THE ANSWER (to 'do them till you find it, no relativity')")
print("="*72)
print("""  Not one survivor is BOTH (derived, not tuned) AND (tested against a
  relativity-free quantity):
    - G is a free dial (v_wind cubed) -> tuned.
    - Omega_m=1/pi is asserted, not uniquely close, and only comparable to
      a relativity-derived number.
    - Pioneer and the redshift excess are anchored to H0 and the GR redshift
      -- both relativity-derived, which YOUR rule removes.

  This is the crux, and it is honest, not a wall: the astrophysical numbers
  can only be checked against relativity-built quantities (Omega_m, H0,
  redshift). Reject relativity and you also remove their scoreboard. So the
  ONLY place a clean, relativity-free, zero-tuning EGT test can live is a
  RAW HARDWARE measurement predicted from first principles -- the trifilar
  coil / B_res resonance / mesh -- NOT simulation (those were artifacts) and
  NOT astrophysics-vs-relativity. That is where to point next, if anywhere.""")
