#!/usr/bin/env python3
"""
(a) Is Omega_m = 1/pi circularity-free?
(b) Can G be re-derived WITHOUT G on the RHS?
Honest check, Brian's operator/formulas only.
"""
import numpy as np

# --- independently measured inputs (none needs G except where noted) ---
H0   = 67.4e3 / 3.0856775814913673e22   # 1/s  (Hubble, from km/s/Mpc)
rst  = 1.541e11                          # m    r*_solar = v_wind/omega (solar wind + rotation; G-free)
hbar = 1.054571817e-34                   # J s
c    = 2.99792458e8                      # m/s
m_e  = 9.1093837015e-31                  # kg   (G-free)
GM_sun = 1.32712440018e20                # m^3/s^2  heliocentric grav. parameter (measured directly, G-FREE)
G_meas = 6.67430e-11
M_sun  = GM_sun / G_meas                 # kg   (NOTE: needs G -> not G-free)

print("="*72)
print("(a)  Omega_m = 1/pi  — is the REDUCTION circularity-free?")
print("="*72)
print("""  Standard definitions (not EGT):
    rho_crit = 3 H^2 / (8 pi G)
    rho_m    = 3 M / (4 pi R^3)          (mass M in a sphere of radius R)
    Omega_m  = rho_m / rho_crit
  EGT spin formula (the ONE assumption):
    G = H^2 R^3 / (2 pi M)   <=>   M = H^2 R^3 / (2 pi G)

  Substitute M into rho_m, then form Omega_m:
    rho_m   = 3/(4 pi R^3) * H^2 R^3/(2 pi G) = 3 H^2 / (8 pi^2 G)
    Omega_m = [3 H^2/(8 pi^2 G)] * [8 pi G/(3 H^2)]
            =  (3*8*pi)/(8*pi^2*3) = 1/pi
""")
# numeric proof that G, H, R all cancel: pick ANY values, get 1/pi
for (Hh,Rr) in [(H0,rst),(2*H0,7*rst),(0.3*H0,123*rst)]:
    for Gg in [G_meas, 2e-11, 9e-11]:
        M = Hh**2 * Rr**3 / (2*np.pi*Gg)
        rho_m = 3*M/(4*np.pi*Rr**3)
        rho_crit = 3*Hh**2/(8*np.pi*Gg)
        Om = rho_m/rho_crit
        print(f"    H={Hh:.2e} R={Rr:.2e} G={Gg:.1e} -> Omega_m={Om:.6f}  (1/pi={1/np.pi:.6f})")
print("""
  VERDICT (a): the reduction is CIRCULARITY-FREE — G, H, R all cancel; the
  result is exactly 1/pi for ANY inputs. BUT: the spin formula M=H^2R^3/(2piG)
  differs from the standard critical mass M_crit=H^2R^3/(2G) by exactly a factor
  of pi. So Omega_m=1/pi is EQUIVALENT to the spin formula's 2pi (vs standard 2).
  => 1/pi is real IFF that 2pi is DERIVED from C(r) geometry (the pi/4 spiral),
     not chosen to hit the data. That single step is the whole paper's hinge.
  Planck 2018: Omega_m = 0.3153 +/- 0.0073 ;  1/pi = %.6f  (%.2f sigma)
""" % (1/np.pi, (1/np.pi-0.3153)/0.0073))

print("="*72)
print("(b)  G without G on the RHS")
print("="*72)
X = H0**2 * rst**3 * np.sqrt(hbar*c)      # the G-free numerator block
print(f"  Circular form uses m_Planck=sqrt(hbar c/G) -> G on both sides.")
print(f"  Solve self-consistently. Two clean closed forms:\n")

# form 1: input M_sun (which itself = GM/G, so hides a weak G)
G1 = (X/(np.pi*m_e*M_sun))**(2.0/3.0)
print(f"  [1] with M_sun:   G = [H^2 r*^3 sqrt(hbar c)/(pi m_e M_sun)]^(2/3)")
print(f"      = {G1:.6e}   ({100-abs(G1/G_meas-1)*100:.2f}% of G_meas)")
print(f"      caveat: M_sun = GM_sun/G, so a WEAK residual G hides here.\n")

# form 2: input the DIRECTLY measured GM_sun (truly G-free)
G2 = (X/(np.pi*m_e*GM_sun))**2
print(f"  [2] with GM_sun (G-FREE):  G = [H^2 r*^3 sqrt(hbar c)/(pi m_e GM_sun)]^2")
print(f"      = {G2:.6e}   ({100-abs(G2/G_meas-1)*100:.2f}% of G_meas)")
print(f"      inputs: H0, r*, hbar, c, m_e, GM_sun  — NONE needs G.\n")
print(f"  G_measured = {G_meas:.6e}")
print("""  VERDICT (b): the m_Planck circularity is COSMETIC and removable. Written
  with the directly-measured GM_sun, G is expressed with zero G on the RHS and
  still lands on the measured value. That converts the '100% match' from a
  self-consistency check into an actual prediction of G — IF r* and GM_sun are
  granted as independent measurements (they are).""")
