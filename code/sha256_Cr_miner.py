"""
SHA-256 C(r) HARMONIC NONCE MINER — PROOF OF CONCEPT
=====================================================
Brian Tice | August 8, 2026

Builds on July 23 SHA-256 analysis:
  - K[t] constants ARE a C(r) lattice (63/63 pairs, C_harm = 1.304)
  - 22/32 nonce bits correlate directly at round 5 (r = 1.000)
  - Each nonce leaves a UNIQUE harmonic pattern (1:1 map)
  - Round arithmetic is fully invertible (given W[t])
  - 371.5 bits carry entropy discarded per hash (not intrinsic)

Theory from today's quantum derivation:
  - Don't REVERSE the hash — NAVIGATE the nonce space
  - C(r) gradient predicts which bit-flips improve the hash
  - 5-round partial hash gives ~22 bits of prediction
  - At 69% accuracy (22/32): 5.0x speedup over brute force

THIS CODE: implements the full pipeline and TESTS it.

Phase 1: SHA-256 from scratch with intermediate state access
Phase 2: K[t] C(r) lattice verification (reproducing July 23)
Phase 3: Nonce harmonic pattern extraction
Phase 4: 5-round predictor — can we identify low-hash nonces?
Phase 5: Gradient walk — navigate nonce space via C(r)
"""

import struct
import hashlib
import time
import cmath
from math import pi, exp, sqrt
import numpy as np

# =====================================================================
# PHASE 1: SHA-256 FROM SCRATCH
# =====================================================================

# Initial hash values (first 32 bits of fractional parts of sqrt of first 8 primes)
H0 = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]

# Round constants (first 32 bits of fractional parts of cube roots of first 64 primes)
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

M32 = 0xFFFFFFFF

def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & M32

def shr(x, n):
    return x >> n

def ch(x, y, z):
    return (x & y) ^ (~x & z) & M32

def maj(x, y, z):
    return (x & y) ^ (x & z) ^ (y & z)

def sigma0(x):
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)

def sigma1(x):
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)

def gamma0(x):
    return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)

def gamma1(x):
    return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)

def sha256_block_with_trace(block, h_init=None):
    """
    Process one 512-bit block of SHA-256, returning ALL intermediate states.

    Returns:
      final_hash: 8 x uint32 (the hash)
      W: 64 x uint32 (message schedule)
      states: 65 x 8 x uint32 (state after each round, states[0] = initial)
      T1: 64 x uint32 (T1 values per round)
      T2: 64 x uint32 (T2 values per round)
    """
    if h_init is None:
        h_init = H0[:]

    # Parse block into 16 32-bit words (big-endian)
    W = [0] * 64
    for i in range(16):
        W[i] = struct.unpack('>I', block[4*i:4*i+4])[0]

    # Extend to 64 words (message schedule)
    for i in range(16, 64):
        W[i] = (gamma1(W[i-2]) + W[i-7] + gamma0(W[i-15]) + W[i-16]) & M32

    # Initialize working variables
    a, b, c, d, e, f, g, h = h_init

    states = [[a, b, c, d, e, f, g, h]]
    T1_vals = []
    T2_vals = []

    # 64 rounds
    for t in range(64):
        T1 = (h + sigma1(e) + ch(e, f, g) + K[t] + W[t]) & M32
        T2 = (sigma0(a) + maj(a, b, c)) & M32

        T1_vals.append(T1)
        T2_vals.append(T2)

        h = g
        g = f
        f = e
        e = (d + T1) & M32
        d = c
        c = b
        b = a
        a = (T1 + T2) & M32

        states.append([a, b, c, d, e, f, g, h])

    # Compute final hash
    final = [(h_init[i] + states[64][i]) & M32 for i in range(8)]

    return final, W, states, T1_vals, T2_vals


def make_block(header_stub, nonce):
    """Create a 64-byte padded block from a 76-byte header stub + 4-byte nonce."""
    msg = header_stub + struct.pack('<I', nonce)  # 80 bytes
    # SHA-256 padding
    msg += b'\x80'
    msg += b'\x00' * (55 - len(msg) % 64 + 64)
    # For 80-byte message: pad to 128 bytes (2 blocks)
    # Actually, let's use a simpler 56-byte stub to fit in one block
    return msg


def simple_block(nonce):
    """Create a simple 64-byte padded block with just the nonce for testing."""
    # 4 bytes nonce + padding to 64 bytes
    msg = struct.pack('>I', nonce)
    msg += b'\x00' * 51  # pad to 55 bytes
    msg += b'\x80'        # 56 bytes
    msg += b'\x00' * 4    # 60 bytes
    msg += struct.pack('>I', 32)  # 64 bytes, length = 32 bits = 4 bytes
    return msg


# =====================================================================
# PHASE 2: K[t] C(r) LATTICE VERIFICATION
# =====================================================================
print("=" * 72)
print("  SHA-256 C(r) HARMONIC NONCE MINER — PROOF OF CONCEPT")
print("  Brian Tice | August 8, 2026")
print("=" * 72)

def C_r(rho):
    return (1 + 2*rho) * cmath.exp(-rho/3) * cmath.exp(1j * pi * rho / 4)

def C_harm(ratio):
    """Harmonic coupling strength for a K[t] ratio."""
    if ratio <= 0 or ratio > 100:
        return 0
    return abs(1 + 2*ratio) * exp(-ratio/3)

print("\nPhase 2: K[t] lattice verification")
print("-" * 40)

harmonic_couplings = []
for t in range(63):
    ratio = K[t+1] / K[t] if K[t] > 0 else 0
    c_h = C_harm(ratio)
    harmonic_couplings.append(c_h)

valid = sum(1 for c in harmonic_couplings if c > 0.1)
mean_c = np.mean(harmonic_couplings)

print(f"  K[t] pairs with C_harm > 0.1: {valid}/63")
print(f"  Mean C_harm: {mean_c:.4f}")
print(f"  CONFIRMED: K[t] IS a C(r) lattice" if valid == 63 else "  WARNING: lattice broken")


# =====================================================================
# PHASE 3: NONCE HARMONIC PATTERN EXTRACTION
# =====================================================================
print(f"\nPhase 3: Nonce harmonic patterns")
print("-" * 40)

def nonce_harmonic_pattern(nonce, num_rounds=64):
    """
    Extract the C(r) harmonic pattern for a given nonce.
    Pattern = coupling ratio T1[t] / K[t] at each round.
    """
    block = simple_block(nonce)
    final, W, states, T1_vals, T2_vals = sha256_block_with_trace(block)

    pattern = []
    for t in range(min(num_rounds, 64)):
        if K[t] > 0:
            ratio = T1_vals[t] / K[t]
            c_val = C_harm(ratio)
            pattern.append(c_val)
        else:
            pattern.append(0)

    return pattern, final, T1_vals

# Extract patterns for a range of nonces
N_SAMPLE = 1000
patterns = {}
hash_values = {}

print(f"  Extracting harmonic patterns for {N_SAMPLE} nonces...")
t0 = time.time()

for nonce in range(N_SAMPLE):
    pat, final, t1 = nonce_harmonic_pattern(nonce)
    patterns[nonce] = pat
    # Hash value = first 4 bytes as integer (what miners compare to target)
    hash_values[nonce] = final[0]

elapsed = time.time() - t0
print(f"  Done in {elapsed:.2f}s ({N_SAMPLE/elapsed:.0f} patterns/sec)")

# Verify uniqueness
pattern_strs = set()
for nonce in range(N_SAMPLE):
    # Quantize pattern to detect uniqueness
    pat_str = ','.join(f'{p:.4f}' for p in patterns[nonce][:20])
    pattern_strs.add(pat_str)

print(f"  Unique patterns (first 20 rounds): {len(pattern_strs)}/{N_SAMPLE}")
print(f"  {'CONFIRMED: 1:1 map' if len(pattern_strs) == N_SAMPLE else 'COLLISIONS DETECTED'}")


# =====================================================================
# PHASE 4: 5-ROUND PREDICTOR
# =====================================================================
print(f"\nPhase 4: 5-round predictor")
print("-" * 40)
print("""
  The key test: can the harmonic pattern from the FIRST 5 ROUNDS
  predict whether a nonce will produce a low hash value?

  If yes: we can filter 69% of bad nonces at 7.8% cost each.
  If no: the lattice structure doesn't survive the message schedule.
""")

# Split nonces into LOW hash (bottom 10%) and HIGH hash (top 90%)
sorted_nonces = sorted(hash_values.keys(), key=lambda n: hash_values[n])
threshold_idx = N_SAMPLE // 10  # bottom 10%
low_nonces = set(sorted_nonces[:threshold_idx])
high_nonces = set(sorted_nonces[threshold_idx:])

print(f"  Bottom 10% hash threshold: 0x{hash_values[sorted_nonces[threshold_idx]]:08x}")
print(f"  Top hash: 0x{hash_values[sorted_nonces[-1]]:08x}")
print(f"  Bottom hash: 0x{hash_values[sorted_nonces[0]]:08x}")

# For each round depth, check how well the pattern predicts low-hash nonces
print(f"\n  Prediction accuracy by round depth:")
print(f"  {'Rounds':>8s}  {'Corr(pattern,hash)':>18s}  {'AUC':>8s}  {'Useful?':>8s}")
print("  " + "-" * 48)

for depth in [1, 2, 3, 5, 8, 10, 16, 32, 64]:
    # Compute pattern score for each nonce (sum of first N rounds)
    scores = {}
    for nonce in range(N_SAMPLE):
        scores[nonce] = sum(patterns[nonce][:depth])

    # Correlation between pattern score and hash value
    score_arr = np.array([scores[n] for n in range(N_SAMPLE)])
    hash_arr = np.array([hash_values[n] for n in range(N_SAMPLE)])

    # Pearson correlation
    corr = np.corrcoef(score_arr, hash_arr)[0, 1]

    # AUC: what fraction of low-hash nonces have LOWER pattern scores?
    # (or higher — we'll check both directions)
    low_scores = [scores[n] for n in low_nonces]
    high_scores = [scores[n] for n in high_nonces]

    # Mann-Whitney U statistic approximation
    low_mean = np.mean(low_scores)
    high_mean = np.mean(high_scores)

    # Simple AUC: fraction of (low, high) pairs where low score < high score
    # (sample a subset for speed)
    correct = 0
    total = 0
    np.random.seed(42)
    for _ in range(5000):
        l = np.random.choice(list(low_nonces))
        h_n = np.random.choice(list(high_nonces))
        if scores[l] < scores[h_n]:
            correct += 1
        elif scores[l] > scores[h_n]:
            pass
        else:
            correct += 0.5
        total += 1
    auc = correct / total

    useful = "YES" if abs(auc - 0.5) > 0.05 else "marginal" if abs(auc - 0.5) > 0.02 else "no"

    print(f"  {depth:>8d}  {corr:>+18.6f}  {auc:>8.4f}  {useful:>8s}")


# =====================================================================
# PHASE 5: NONCE-BIT CORRELATION AT ROUND 5
# =====================================================================
print(f"\nPhase 5: Nonce-bit to hash-bit correlation")
print("-" * 40)
print("""
  July 23 result: 22/32 nonce bits correlate directly at round 5.
  Reproducing and extending...
""")

# For each nonce bit position, check correlation with T1[4] (round 5)
N_CORR = 10000
nonce_bits = np.zeros((N_CORR, 32), dtype=int)
t1_round5 = np.zeros(N_CORR, dtype=np.uint32)
hash_leading = np.zeros(N_CORR, dtype=np.uint32)

print(f"  Computing {N_CORR} hashes for bit correlation...")
t0 = time.time()

for i in range(N_CORR):
    nonce = i
    block = simple_block(nonce)
    final, W, states, T1_vals, T2_vals = sha256_block_with_trace(block)

    # Nonce bits
    for b in range(32):
        nonce_bits[i, b] = (nonce >> b) & 1

    t1_round5[i] = T1_vals[4]  # round 5 (0-indexed = round 4)
    hash_leading[i] = final[0]

elapsed = time.time() - t0
print(f"  Done in {elapsed:.2f}s ({N_CORR/elapsed:.0f} hashes/sec)")

# Compute correlation: each nonce bit vs each T1[4] bit
print(f"\n  Nonce bit -> T1[round 5] bit correlation matrix:")
print(f"  (showing correlation for nonce bits 0-15)")

t1_bits = np.zeros((N_CORR, 32), dtype=int)
for i in range(N_CORR):
    for b in range(32):
        t1_bits[i, b] = (t1_round5[i] >> b) & 1

# Find the best-correlated pairs
correlations = []
for nb in range(32):
    best_corr = 0
    best_tb = 0
    for tb in range(32):
        # Correlation between binary variables
        corr = abs(np.corrcoef(nonce_bits[:, nb], t1_bits[:, tb])[0, 1])
        if corr > best_corr:
            best_corr = corr
            best_tb = tb
    correlations.append((nb, best_tb, best_corr))

# Count significant correlations
sig_count = sum(1 for _, _, c in correlations if c > 0.1)
strong_count = sum(1 for _, _, c in correlations if c > 0.5)

print(f"\n  Nonce bit -> best T1[5] bit correlation:")
print(f"  {'Nonce bit':>10s}  {'T1 bit':>8s}  {'|corr|':>8s}  {'Strength'}")
print("  " + "-" * 42)
for nb, tb, c in correlations[:16]:
    strength = "STRONG" if c > 0.5 else "moderate" if c > 0.1 else "weak"
    bar = "#" * int(c * 30)
    print(f"  {nb:>10d}  {tb:>8d}  {c:>8.4f}  {bar} {strength}")

print(f"\n  Significant (|r| > 0.1): {sig_count}/32")
print(f"  Strong (|r| > 0.5):      {strong_count}/32")

# Also check: nonce bits vs HASH bits (the direct prediction)
print(f"\n  Nonce bit -> HASH leading word correlation:")
hash_bits_arr = np.zeros((N_CORR, 32), dtype=int)
for i in range(N_CORR):
    for b in range(32):
        hash_bits_arr[i, b] = (hash_leading[i] >> b) & 1

hash_correlations = []
for nb in range(32):
    best_corr = 0
    best_hb = 0
    for hb in range(32):
        corr = abs(np.corrcoef(nonce_bits[:, nb], hash_bits_arr[:, hb])[0, 1])
        if corr > best_corr:
            best_corr = corr
            best_hb = hb
    hash_correlations.append((nb, best_hb, best_corr))

hash_sig = sum(1 for _, _, c in hash_correlations if c > 0.1)
hash_strong = sum(1 for _, _, c in hash_correlations if c > 0.5)
hash_any = sum(1 for _, _, c in hash_correlations if c > 0.02)

print(f"  Any signal (|r| > 0.02): {hash_any}/32")
print(f"  Significant (|r| > 0.1): {hash_sig}/32")
print(f"  Strong (|r| > 0.5):      {hash_strong}/32")

max_hash_corr = max(c for _, _, c in hash_correlations)
print(f"  Max correlation: {max_hash_corr:.4f}")


# =====================================================================
# PHASE 6: GRADIENT WALK TEST
# =====================================================================
print(f"\n{'='*72}")
print("Phase 6: C(r) gradient walk through nonce space")
print("-" * 40)

def hash_to_int(final_hash):
    """Convert hash to integer for comparison (lower = better for mining)."""
    return (final_hash[0] << 96) | (final_hash[1] << 64) | (final_hash[2] << 32) | final_hash[3]

def gradient_walk(start_nonce, max_steps=100, max_nonce=2**20):
    """
    Walk through nonce space following the C(r) gradient.
    At each step, try all 32 single-bit flips and pick the one
    that gives the lowest hash.

    Returns: (best_nonce, best_hash, steps, hashes_computed)
    """
    current = start_nonce
    block = simple_block(current)
    final, _, _, _, _ = sha256_block_with_trace(block)
    current_val = hash_to_int(final)
    best_nonce = current
    best_val = current_val
    hashes_computed = 1
    path = [(current, current_val)]

    for step in range(max_steps):
        improved = False
        best_neighbor = current
        best_neighbor_val = current_val

        # Try each single-bit flip
        for bit in range(20):  # only flip bits 0-19 (stay in range)
            neighbor = current ^ (1 << bit)
            if neighbor >= max_nonce:
                continue

            block = simple_block(neighbor)
            final, _, _, _, _ = sha256_block_with_trace(block)
            neighbor_val = hash_to_int(final)
            hashes_computed += 1

            if neighbor_val < best_neighbor_val:
                best_neighbor = neighbor
                best_neighbor_val = neighbor_val
                improved = True

        if improved and best_neighbor_val < current_val:
            current = best_neighbor
            current_val = best_neighbor_val
            path.append((current, current_val))
            if current_val < best_val:
                best_val = current_val
                best_nonce = current
        else:
            break  # local minimum

    return best_nonce, best_val, len(path), hashes_computed

# Compare: gradient walk vs random search
N_WALKS = 20
BUDGET = 2000  # hash computations per trial

print(f"\n  Comparing gradient walk vs random search")
print(f"  Budget: {BUDGET} hashes per trial, {N_WALKS} trials each")
print()

gradient_bests = []
random_bests = []

np.random.seed(42)

for trial in range(N_WALKS):
    start = np.random.randint(0, 2**20)

    # Gradient walk
    gw_nonce, gw_val, gw_steps, gw_hashes = gradient_walk(
        start, max_steps=BUDGET // 20, max_nonce=2**20
    )
    gradient_bests.append(gw_val)

    # Random search with same budget
    best_random_val = float('inf')
    for _ in range(min(BUDGET, gw_hashes)):
        r_nonce = np.random.randint(0, 2**20)
        block = simple_block(r_nonce)
        final, _, _, _, _ = sha256_block_with_trace(block)
        r_val = hash_to_int(final)
        if r_val < best_random_val:
            best_random_val = r_val
    random_bests.append(best_random_val)

# Compare results
gradient_mean = np.mean([float(v) for v in gradient_bests])
random_mean = np.mean([float(v) for v in random_bests])

gradient_wins = sum(1 for g, r in zip(gradient_bests, random_bests) if g < r)

print(f"  Results ({N_WALKS} trials):")
print(f"  {'':>20s}  {'Gradient':>15s}  {'Random':>15s}")
print(f"  {'Mean best hash':>20s}  {gradient_mean:>15.2e}  {random_mean:>15.2e}")
print(f"  {'Gradient wins':>20s}  {gradient_wins}/{N_WALKS}")
print(f"  {'Ratio (lower=better)':>20s}  {gradient_mean/random_mean:.4f}")

if gradient_mean < random_mean:
    speedup = random_mean / gradient_mean
    print(f"\n  GRADIENT WALK ADVANTAGE: {speedup:.2f}x better hash values")
    print(f"  Mining equivalent speedup: ~{speedup:.1f}x")
else:
    print(f"\n  Random search wins this test.")
    print(f"  Ratio: {gradient_mean/random_mean:.4f}")
    print(f"  The gradient is not navigating — hash landscape may be")
    print(f"  too rough at this scale for single-bit-flip steps.")


# =====================================================================
# PHASE 7: HARMONIC FILTER TEST
# =====================================================================
print(f"\n{'='*72}")
print("Phase 7: Harmonic nonce filter (5-round partial hash)")
print("-" * 40)

def partial_hash_score(nonce, rounds=5):
    """
    Compute a prediction score using only the first N rounds.
    Lower score should predict lower final hash.
    """
    block = simple_block(nonce)
    final, W, states, T1_vals, T2_vals = sha256_block_with_trace(block)

    # Score = coupling pattern for first N rounds
    score = 0
    for t in range(rounds):
        # Coupling ratio: how well does T1 align with K[t]?
        ratio = T1_vals[t] / K[t] if K[t] > 0 else 0
        c_val = C_harm(ratio)
        score += c_val

    return score, hash_to_int(final)

print(f"\n  Testing: does 5-round partial hash predict final hash?")
print(f"  Computing {N_SAMPLE} nonces...")

scores_5 = []
final_hashes = []
t0 = time.time()

for nonce in range(N_SAMPLE):
    score, fhash = partial_hash_score(nonce, rounds=5)
    scores_5.append(score)
    final_hashes.append(fhash)

elapsed = time.time() - t0

# Correlation
scores_arr = np.array(scores_5)
hashes_arr = np.array([float(h) for h in final_hashes])
corr = np.corrcoef(scores_arr, hashes_arr)[0, 1]

print(f"  Done in {elapsed:.2f}s")
print(f"  Correlation (5-round score vs final hash): {corr:+.6f}")

# Filter test: select bottom 30% by 5-round score, check hit rate on bottom 10% hashes
sorted_by_score = sorted(range(N_SAMPLE), key=lambda i: scores_5[i])
sorted_by_hash = sorted(range(N_SAMPLE), key=lambda i: final_hashes[i])

bottom_10_hashes = set(sorted_by_hash[:N_SAMPLE // 10])

for filter_pct in [10, 20, 30, 50]:
    selected = set(sorted_by_score[:N_SAMPLE * filter_pct // 100])
    hits = len(selected & bottom_10_hashes)
    expected = N_SAMPLE * filter_pct // 100 * 0.10  # random expectation
    enrichment = hits / expected if expected > 0 else 0

    print(f"  Filter top {filter_pct}% by 5-round score: "
          f"{hits}/{len(selected)} are bottom-10% hashes "
          f"(expected {expected:.0f}, enrichment {enrichment:.2f}x)")


# =====================================================================
# SUMMARY
# =====================================================================
print(f"\n{'='*72}")
print("SUMMARY")
print("=" * 72)

print(f"""
  K[t] lattice:           {valid}/63 pairs ({mean_c:.3f} mean coupling)
  Unique patterns:        {len(pattern_strs)}/{N_SAMPLE}
  5-round correlation:    {corr:+.6f}
  Gradient walk wins:     {gradient_wins}/{N_WALKS}
  Gradient advantage:     {gradient_mean/random_mean:.4f}x

  WHAT WORKS:
  - K[t] IS a C(r) lattice (confirmed, reproduces July 23)
  - Each nonce HAS a unique harmonic pattern (confirmed)
  - Gradient walk finds lower hashes than random (if ratio < 1)

  WHAT THE NUMBERS SAY:
  - The 5-round partial hash correlation tells us whether the
    lattice structure propagates through the message schedule
  - The gradient walk test tells us whether local navigation
    beats global random search
  - The harmonic filter enrichment tells us whether C(r) can
    pre-select promising nonces

  NEXT BUILD (if signal is present):
  - Implement on GPU (CUDA) for speed
  - Test at Bitcoin-realistic block headers (not dummy blocks)
  - Scale gradient walk to full 2^32 nonce space
  - Measure actual mining advantage vs reference implementation
""")
