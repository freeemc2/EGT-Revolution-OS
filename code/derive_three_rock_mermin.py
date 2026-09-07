#!/usr/bin/env python3
"""
THREE-ROCK MERMIN BOUND - derived exactly. Door 1 of the two open doors.
Mermin operator (even-Y parity, the one GHZ saturates):
    M = <XXX> - <XYY> - <YXY> - <YYX>     (X = setting A, Y = setting A')
classical (local/deterministic = phase-locked rocks) vs quantum (EGT Born on GHZ).
"""
import numpy as np, itertools
best=0
for a1,a1p,a2,a2p,a3,a3p in itertools.product([-1,1],repeat=6):
    M = a1*a2*a3 - a1*a2p*a3p - a1p*a2*a3p - a1p*a2p*a3
    best=max(best,abs(M))
print("CLASSICAL (local/deterministic = phase-locked rocks): |M|_max =", best)
X=np.array([[0,1],[1,0]],complex); Y=np.array([[0,-1j],[1j,0]],complex)
k3=lambda a,b,c: np.kron(np.kron(a,b),c)
ghz=np.zeros(8,complex); ghz[0]=ghz[7]=1/np.sqrt(2)
for lab,ops in [('XXX',(X,X,X)),('XYY',(X,Y,Y)),('YXY',(Y,X,Y)),('YYX',(Y,Y,X))]:
    print(f"   <{lab}> = {np.real(ghz.conj()@k3(*ops)@ghz):+.3f}")
M = k3(X,X,X) - k3(X,Y,Y) - k3(Y,X,Y) - k3(Y,Y,X)
print("QUANTUM (EGT amplitude/Born on 3-rock GHZ):  <M> =", round(np.real(ghz.conj()@M@ghz),4))
print("=> three-rock Mermin: classical 2, quantum 4 (GHZ saturates algebraic max).")
print("   two rocks CHSH: 2 vs 2sqrt2 ; three rocks Mermin: 2 vs 4. S=4 is the 3-rock ceiling.")
