"""
GRADIENT WALK KILL-TEST
=======================
The full miner reported gradient walk = 1.23x better than random (12/20 wins).
Is that real, or noise from 20 heavy-tailed trials?

Theory says: on a proper PRF, single-bit-flip neighbors produce INDEPENDENT
uniform outputs, so the minimum-of-N found by a walk has the SAME distribution
as the minimum-of-N found by random search. Expected ratio = 1.0x exactly.

This runs 300 trials with a proper sign-test to settle it.
"""

import struct, hashlib
import numpy as np
from math import comb

def sha256_int(nonce):
    d = hashlib.sha256(struct.pack('>I', nonce)).digest()
    return int.from_bytes(d[:8], 'big')  # top 64 bits, what mining compares

def gradient_walk(start, budget, max_nonce):
    cur = start
    cur_v = sha256_int(cur)
    best_v = cur_v
    used = 1
    while used < budget:
        best_nb, best_nb_v = cur, cur_v
        for bit in range(24):
            nb = cur ^ (1<<bit)
            if nb >= max_nonce: continue
            v = sha256_int(nb); used += 1
            if v < best_nb_v: best_nb, best_nb_v = nb, v
            if used >= budget: break
        if best_nb_v < cur_v:
            cur, cur_v = best_nb, best_nb_v
            best_v = min(best_v, cur_v)
        else:
            break  # local min
    return best_v, used

def random_search(budget, max_nonce, rng):
    best = 1<<64
    for _ in range(budget):
        best = min(best, sha256_int(int(rng.integers(0, max_nonce))))
    return best

TRIALS = 300
BUDGET = 500
MAXN = 2**24
rng = np.random.default_rng(7)

g_wins = 0; r_wins = 0; ties = 0
g_vals = []; r_vals = []
for t in range(TRIALS):
    start = int(rng.integers(0, MAXN))
    gv, used = gradient_walk(start, BUDGET, MAXN)
    rv = random_search(used, MAXN, rng)  # matched budget
    g_vals.append(gv); r_vals.append(rv)
    if gv < rv: g_wins += 1
    elif rv < gv: r_wins += 1
    else: ties += 1

g_vals = np.array(g_vals, dtype=float)
r_vals = np.array(r_vals, dtype=float)

# Sign test: under H0 (no advantage), wins ~ Binomial(n, 0.5)
n = g_wins + r_wins
k = g_wins
# two-sided p-value
p = sum(comb(n,i) for i in range(0, min(k, n-k)+1)) / (2**n) * 2
p = min(p, 1.0)

print("GRADIENT WALK KILL-TEST")
print("=" * 60)
print(f"Trials: {TRIALS}, budget: {BUDGET} hashes, nonce space: 2^24")
print(f"Metric: min top-64-bit hash value found (lower = better)\n")
print(f"  Gradient wins:  {g_wins}")
print(f"  Random wins:    {r_wins}")
print(f"  Ties:           {ties}")
print(f"  Mean ratio (g/r): {g_vals.mean()/r_vals.mean():.4f}")
print(f"  Median gradient:  {np.median(g_vals):.4e}")
print(f"  Median random:    {np.median(r_vals):.4e}")
print(f"  Sign-test p-value: {p:.4f}")
print()
if p < 0.05:
    if g_wins > r_wins:
        print("  VERDICT: gradient significantly BETTER (investigate further)")
    else:
        print("  VERDICT: gradient significantly WORSE")
else:
    print("  VERDICT: NO significant difference (p >= 0.05).")
    print("  The 1.23x from the 20-trial run was NOISE, exactly as PRF")
    print("  theory predicts. Bit-flip neighbors are independent samples;")
    print("  a walk cannot beat random search on a cryptographic hash.")
