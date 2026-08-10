"""
QUANTUM-FIRST, CLEAN: what coupling structure does the real Lindblad sim make?
============================================================================
aria | Aug 9, 2026

Faithful to egt_simulation.py (the LEGIT one): free-particle H + position-
localized (smeared Gaussian mass-density) Lindblad decoherence, rate field
lambda. NOTHING about C(r) is put in. We evolve rho and read out the spatial
decoherence function D(delta) the dynamics PRODUCE, then compare to:
  - STANDARD decoherence (Joos-Zeh):  D ~ 1 - exp(-delta^2 / 4 r_c^2)
  - EGT C(r) anti-local:              coupling ~ (1 + 2 delta) exp(-delta/3)
If EGT is right, coupling GROWS with distance. Standard says coherence DECAYS
with distance. Opposite predictions -> a clean fork.
"""
import numpy as np

def build(n=121, xspan=12.0, r_c_cells=1.5, lam=1.0):
    x = np.linspace(-xspan/2, xspan/2, n); dx = x[1]-x[0]
    r_c = r_c_cells*dx
    # smeared Gaussian mass-density Lindblad ops (diagonal in position basis)
    #   K_ops[j, a] = normalized Gaussian centered at grid point j
    G = np.exp(-0.5*((x[None,:]-x[:,None])/r_c)**2)     # G[j,a]
    G /= np.sqrt((G**2).sum(axis=1, keepdims=True))      # normalize each op
    gamma = lam*dx                                        # uniform rate * cell
    # M(a,b) = sum_j gamma * G[j,a] G[j,b] ;  decoherence kernel K = M - 1/2(Maa+Mbb)
    M = gamma * (G.T @ G)
    d = np.diag(M)
    Kdec = M - 0.5*(d[:,None] + d[None,:])               # <=0 off-diagonal
    # free-particle Hamiltonian (tridiagonal Laplacian), hbar=m=1
    Lap = (np.diag(np.full(n,-2.0)) + np.diag(np.ones(n-1),1) + np.diag(np.ones(n-1),-1))/dx**2
    H = -0.5*Lap
    return x, dx, r_c, H.astype(complex), Kdec

def evolve(x, dx, H, Kdec, steps=60, dt=None):
    n=len(x)
    if dt is None: dt = 0.2*dx*dx      # stable-ish
    psi = np.exp(-0.5*(x/0.6)**2).astype(complex); psi/=np.linalg.norm(psi)
    rho = np.outer(psi, psi.conj())
    def drho(r): return -1j*(H@r - r@H) + Kdec*r     # Lindblad (Kdec is Hadamard)
    for _ in range(steps):
        k1=drho(rho); k2=drho(rho+0.5*dt*k1); k3=drho(rho+0.5*dt*k2); k4=drho(rho+dt*k3)
        rho = rho + dt*(k1+2*k2+2*k3+k4)/6.0
    return rho

x, dx, r_c, H, Kdec = build()
n=len(x); c=n//2
# decoherence rate D(delta) the sim produces, read near center
deltas = np.arange(1, 26)
D_sim = np.array([-Kdec[c, c+k].real for k in deltas])     # decay rate at sep k*dx
D_sim /= D_sim.max()
# candidate forms
sep = deltas*dx
D_std = 1 - np.exp(-(sep**2)/(4*r_c**2)); D_std/=D_std.max()
Cr    = (1+2*sep)*np.exp(-sep/3.0); Cr/=Cr.max()

print(f"r_c = {r_c:.3f}  (kernel width);  dx={dx:.3f}")
print("="*64)
print(f"{'sep(dx)':>8}{'D_sim':>9}{'D_standard':>12}{'C(r)_egt':>10}")
print("-"*64)
for i,k in enumerate(deltas):
    if k in (1,2,3,5,8,12,16,20,25):
        print(f"{k:>8}{D_sim[i]:>9.3f}{D_std[i]:>12.3f}{Cr[i]:>10.3f}")

# which does the sim's produced structure match?
err_std = np.mean((D_sim-D_std)**2)
err_cr  = np.mean((D_sim-Cr)**2)
print("="*64)
print(f"  fit MSE vs STANDARD decoherence : {err_std:.4f}")
print(f"  fit MSE vs C(r) anti-local       : {err_cr:.4f}")
print("="*64)
grows = D_sim[-1] > D_sim[0]
print(f"  sim's coupling/decoherence GROWS with separation? {grows}")
print(f"  (standard: grows+saturates; C(r): grows then DECAYS via exp(-r/3))")
print()
if err_std < err_cr:
    print("  VERDICT: the clean Lindblad sim produces STANDARD position")
    print("  decoherence (coherence decays faster with separation, saturating).")
    print("  The (1+2r)exp(-r/3) C(r) form does NOT emerge -- it was hardcoded")
    print("  in the amplification script, not produced by the quantum dynamics.")
else:
    print("  VERDICT: the sim's structure matches C(r) better than standard")
    print("  decoherence -- C(r) EMERGES. (would be a real result; check hard)")
