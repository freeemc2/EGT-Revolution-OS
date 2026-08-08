"""
SHA-256 AVALANCHE TRACE
=======================
Where does the nonce signal live, and where does it die?

The July 23 note claimed "22/32 nonce bits correlate at round 5 (r=1.000)."
The full miner test got 0/32 at round 5 (max r=0.03).

This resolves the discrepancy: it traces the nonce -> state correlation
round by round, so we can see the avalanche happen and pinpoint exactly
which round the signal survives to.
"""

import struct
import numpy as np

M32 = 0xFFFFFFFF
def rotr(x, n): return ((x >> n) | (x << (32 - n))) & M32
def shr(x, n): return x >> n
def ch(x, y, z): return (x & y) ^ (~x & z)
def maj(x, y, z): return (x & y) ^ (x & z) ^ (y & z)
def sig0(x): return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)
def sig1(x): return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)
def gam0(x): return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)
def gam1(x): return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)

H0 = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
     0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
     0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
     0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
     0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
     0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
     0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
     0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]

def block(nonce):
    msg = struct.pack('>I', nonce) + b'\x00'*51 + b'\x80' + b'\x00'*4 + struct.pack('>I', 32)
    return msg

def run(nonce):
    W = [0]*64
    for i in range(16):
        W[i] = struct.unpack('>I', block(nonce)[4*i:4*i+4])[0]
    for i in range(16,64):
        W[i] = (gam1(W[i-2]) + W[i-7] + gam0(W[i-15]) + W[i-16]) & M32
    a,b,c,d,e,f,g,h = H0
    A_reg = []  # state register 'a' after each round
    for t in range(64):
        T1 = (h + sig1(e) + (ch(e,f,g)&M32) + K[t] + W[t]) & M32
        T2 = (sig0(a) + maj(a,b,c)) & M32
        h=g; g=f; f=e; e=(d+T1)&M32; d=c; c=b; b=a; a=(T1+T2)&M32
        A_reg.append(a)
    return A_reg

N = 20000
print("SHA-256 avalanche: nonce-bit -> state-register 'a' correlation by round")
print("=" * 70)
print(f"Samples: {N}\n")

# Collect
nonce_bits = np.zeros((N,32), dtype=np.int8)
a_regs = np.zeros((N,64), dtype=np.uint32)
for i in range(N):
    nonce_bits[i] = [(i>>b)&1 for b in range(32)]
    a_regs[i] = run(i)

print(f"{'Round':>6s}  {'bits |r|>0.1':>12s}  {'bits |r|>0.5':>12s}  {'max |r|':>10s}  {'note'}")
print("-"*70)
for rnd in [0,1,2,3,4,5,6,8,10,16]:
    a_bits = np.zeros((N,32), dtype=np.int8)
    for i in range(N):
        for bb in range(32):
            a_bits[i,bb] = (int(a_regs[i,rnd])>>bb)&1
    best = []
    for nb in range(32):
        mx = 0.0
        col_n = nonce_bits[:,nb].astype(float)
        if col_n.std()==0:
            best.append(0.0); continue
        for ab in range(32):
            col_a = a_bits[:,ab].astype(float)
            if col_a.std()==0: continue
            r = abs(np.corrcoef(col_n,col_a)[0,1])
            if r>mx: mx=r
        best.append(mx)
    best = np.array(best)
    sig = int((best>0.1).sum())
    strong = int((best>0.5).sum())
    note = ""
    if rnd==0: note="nonce enters as W[0]"
    if strong>0 and rnd<=2: note="input still in register"
    if strong==0 and sig==0: note="AVALANCHE COMPLETE - noise"
    print(f"{rnd:>6d}  {sig:>12d}  {strong:>12d}  {best.max():>10.4f}  {note}")

print()
print("Interpretation:")
print("  If 'r=1.000, 22/32 bits' ever held, it was at round 0-1 where the")
print("  nonce word literally sits in a state register before diffusion.")
print("  That is the IDENTITY (input=input), not a crack. The message-schedule")
print("  diffusion + modular carries destroy it within a few rounds.")
