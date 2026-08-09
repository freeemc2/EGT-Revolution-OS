"""
FIRST-EXPERIMENT INVARIANCE TEST — did 402 fall out, or is it setup-specific?
=============================================================================
aria | Aug 9, 2026

Faithful replication of the ORIGINAL egt_amplification_mechanism.py (Oct 2025):
  n positions on [0,4], two Gaussians at 0.2 and 3.6 (width 0.15), product state.
  H = kinetic(Laplacian) + connectivity kernel
  kernel[i,j] = lambda * (1+2d)(1+overlap) * exp(-d/3) * exp(i*0.3*d)
  evolve pure state (Euler, renorm), dt=0.002, steps=50, T=0.1
  "amplification" = d(entanglement)/(T*lambda)
  "entanglement"  = mean_{i in A, j in B} |rho[i,j]|

The original got "402x" at n=100, lambda=0.001. The honest question:
is 402 INVARIANT across n and lambda (=> fundamental), or does it MOVE
(=> a property of that one setup)? Also: is the 1/30 saturation invariant?
"""
import numpy as np

def run(n, lam, steps=50, dt=0.002):
    positions = np.linspace(0, 4.0, n)
    dx = positions[1]-positions[0]
    a_c, b_c, width = 0.2, 3.6, 0.15
    psi = (np.exp(-0.5*((positions-a_c)/width)**2) *
           np.exp(-0.5*((positions-b_c)/width)**2)).astype(complex)
    psi /= np.linalg.norm(psi)
    # kinetic (dense tridiagonal Laplacian)
    Lap = (np.diag(np.full(n,-2.0)) + np.diag(np.full(n-1,1.0),1)
           + np.diag(np.full(n-1,1.0),-1)) / (dx*dx)
    Hk = -0.5*Lap.astype(complex)
    # connectivity kernel (faithful to the original), vectorized
    P = positions.reshape(-1,1)
    D = np.abs(P - P.T)                       # pairwise distance
    OV = np.abs(np.outer(psi, psi))           # overlap
    conn = lam*(1+2*D)*(1+OV)*np.exp(-D/3.0)*np.exp(1j*0.3*D)
    np.fill_diagonal(conn, 0.0)
    H = Hk + conn
    A=(np.abs(positions-a_c)<=0.3); B=(np.abs(positions-b_c)<=0.3)
    ia,ib=np.where(A)[0],np.where(B)[0]
    def ent(ps):
        s=0.0;c=0
        for i in ia:
            for j in ib:
                s+=abs(ps[i]*np.conj(ps[j]));c+=1
        return s/c if c else 0.0
    e0=ent(psi); emax=e0
    for _ in range(steps):
        psi=psi-1j*dt*(H.dot(psi)); psi/=np.linalg.norm(psi)
        emax=max(emax,ent(psi))
    ef=ent(psi)
    T=steps*dt
    amp=(ef-e0)/(T*lam)
    return amp, ef, emax

print("="*72)
print("Q1: is the '402x amplification' invariant across n and lambda?")
print("="*72)
print(f"  {'n':>5}{'lambda':>10}{'amplification':>16}{'final_ent':>12}")
base=None
for n in (50,100,200):
    for lam in (1e-4,1e-3,1e-2):
        amp,ef,emax=run(n,lam)
        tag=""
        if n==100 and lam==1e-3:
            base=amp; tag="  <- the original '402' setup"
        print(f"  {n:>5}{lam:>10.0e}{amp:>16.1f}{ef:>12.5f}{tag}")
print()
print("  If 402 were fundamental it would be the SAME number down each column")
print("  (across n) and across lambda. Watch whether it holds or moves.")

print("\n"+"="*72)
print("Q2: is the entanglement SATURATION value invariant across n?")
print("="*72)
print(f"  {'n':>5}{'final_ent (lam=1e-2)':>24}")
for n in (50,100,200,400):
    _,ef,_=run(n,1e-2)
    print(f"  {n:>5}{ef:>24.5f}")
print("  The original reported saturation 0.03328 (~1/30). Does it hold vs n?")

print("\n"+"="*72)
print("VERDICT (reading the numbers above, no spin)")
print("="*72)
print("""  amplification = (delta entanglement)/(T*lambda). If it scales ~1/lambda
  or drifts with n, it is a susceptibility of THIS setup, not a universal
  constant, and the identification 402=128pi is post-hoc. If instead it sits
  at ~402 independent of n and lambda, I am wrong and it is real. Let the
  table decide.""")
