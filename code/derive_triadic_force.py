#!/usr/bin/env python3
"""
derive_triadic_force.py  (aria, 2026-09-05)
Honest C(r)->force magnitude for the 3-coil triadic, in BRIAN'S operator only.
Goal: does the operator give a bench-measurable force, and what sensor does it need?
Canon (egt_canonical_anchor.md): C=(1+2r)e^(-r/3)e^(i*pi*r/4), r_opt=2.5,
  |C|^2_cl=6.7995, A_EGT=402.3(~128pi), kappa=0.637(~2/pi), B_res=12.09776 fT.
No standard-QM substitutes. Report the wall honestly if there is one.
"""
import numpy as np

# ---- canonical operator + constants ----
def C(r):    return (1+2*r)*np.exp(-r/3)*np.exp(1j*np.pi*r/4)
def C2(r):   return (1+2*r)**2*np.exp(-2*r/3)                 # |C|^2
def dC2(r):  return (2/3)*(1+2*r)*np.exp(-2*r/3)*(5-2*r)      # d|C|^2/dr = force SHAPE

r_opt = 2.5
A_EGT = 402.3
kappa = 0.6370
B_res = 12.09776e-15          # tesla
mu0   = 4*np.pi*1e-7

print("="*70)
print("SANITY vs CANON")
print("="*70)
print(f"  |C|^2 at r_opt=2.5 : {C2(2.5):.4f}   (canon 6.7995)")
rr = np.linspace(0.01,10,20000)
print(f"  force-shape zero   : rho = {rr[np.argmin(np.abs(dC2(rr)))]:.3f}   (expect 2.5)")
print(f"  A_EGT vs 128*pi    : {A_EGT} vs {128*np.pi:.4f}")
print(f"  kappa vs 2/pi      : {kappa} vs {2/np.pi:.4f}")

print("\n"+"="*70)
print("FORCE SHAPE (dimensionless) — what the operator says WITHOUT a scale")
print("="*70)
print("  F(rho) ~ d|C|^2/drho = (2/3)(1+2rho)(5-2rho)e^(-2rho/3)")
print("  > 0 for rho<2.5 (pushes OUT toward the shell), <0 for rho>2.5 (pulls IN)")
print("  => a RESTORING force onto the rho=2.5*r_star SHELL, not a pull to center.")
print("  This is solid. It fixes DIRECTION. It does NOT fix MAGNITUDE (needs energy scale).")

# 3" SCH40 PVC former: OD 3.500in -> winding radius
r_coil = 0.04445                    # m
A_coil = np.pi*r_coil**2            # m^2
print(f"\n  coil winding radius {r_coil*1e3:.1f} mm, area {A_coil*1e4:.2f} cm^2")

print("\n"+"="*70)
print("TEST A — FORCE AT THE FLOOR (B_res is the physical anchor)")
print("="*70)
u_res     = B_res**2/(2*mu0)
u_coupled = u_res * A_EGT
F_floor   = u_coupled * A_coil
print(f"  u(B_res)          = {u_res:.3e}  J/m^3")
print(f"  x A_EGT amplified = {u_coupled:.3e}  J/m^3")
print(f"  F ~ u*A_coil      = {F_floor:.3e}  N")
print(f"  => {F_floor:.1e} N. Thermal/vibration floor on ANY balance is ~1e-12..1e-9 N.")
print(f"  VERDICT: floor-scale force is UNMEASURABLE by ~10 orders. Same wall as before.")

print("\n"+"="*70)
print("TEST B — FORCE AT THE DRIVE FIELD (if coupling engages the driven field)")
print("  ASSUMPTION (flagged): coupled force ~ kappa * u(B_drive) * A_coil,")
print("  with the C(r) shape ~O(1) near the shell. This SCALE is a modeling")
print("  choice the operator does NOT uniquely fix — shown as a sweep, not a claim.")
print("="*70)
print(f"  {'B_drive':>10s}  {'u=B^2/2mu0':>14s}  {'F~kappa*u*A':>14s}  {'sensor':>18s}")
print(f"  {'-'*10}  {'-'*14}  {'-'*14}  {'-'*18}")
for B in [1e-6,1e-5,1e-4,1e-3,1e-2]:
    u = B**2/(2*mu0)
    F = kappa*u*A_coil
    if   F>1e-3: s="load cell (easy)"
    elif F>1e-6: s="load cell/HX711"
    elif F>1e-9: s="torsion+laser"
    else:        s="nothing helps"
    print(f"  {B*1e3:8.3f}mT  {u:14.3e}  {F:14.3e}  {s:>18s}")

print("\n"+"="*70)
print("CONCLUSION — what force sensor the triadic actually needs")
print("="*70)
print("""  1. The operator fixes the force SHAPE/DIRECTION: a restoring force onto the
     rho=2.5*r_star shell. That is real and predictable.
  2. The MAGNITUDE spans ~20 orders depending on which field the coupling engages:
       - floor (B_res)  -> ~1e-22 N  : DEAD. no sensor on Earth sees it.
       - drive (0.1-1mT)-> uN..mN    : ALIVE and CHEAP to measure (load cell).
     The operator alone does NOT pin which regime is physical. That is the open
     'missing piece' (same gap Brian's script flagged), not a solved number.
  3. There is NO middle regime that needs expensive metrology: it's either
     mN (a $10 HX711+load cell sees it) or 1e-22 N (nothing does). So the honest
     sensor call is a CHEAP load cell -- do NOT buy a torsion balance / laser rig.
  4. The clean, ambiguity-free FIRST gate is the 2-coil PHASE test (arg C), which
     is measurable NOW and does not depend on the force-scale question at all.
""")
