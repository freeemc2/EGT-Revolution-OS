#!/usr/bin/env python3
"""
connectivity_amplification_v2.py
================================
Redo of the original connectivity_amplification_scan.py.

The original applied C = weight * adjacency, which trivially gives d².
This version applies C(r) to graph DISTANCES — the actual operator.

    C(r) = (1 + 2r) * exp(-r/3) * exp(i*pi*r/4)

(Prefactor lambda omitted — it just scales everything by lambda².)

For each graph:
  1. Compute all-pairs shortest paths (BFS)
  2. Build C_ij = C(dist(i,j)) for i != j
  3. Amplification = lambda_max(C†C)

Questions:
  - What amplification falls out of different graph families?
  - Does any family produce ~402 naturally?
  - Does the amplification converge as N -> infinity?
  - What's structural vs what's from the constants?

No imported physics. No Coulomb potential. No Schrodinger equation.
Just the operator on graphs. Honest numbers.
"""

import numpy as np
from collections import deque
import sys
import os

def Cr(r):
    """C(r) operator magnitude and phase, lambda=1."""
    if r == 0:
        return 0.0 + 0.0j
    return (1 + 2*r) * np.exp(-r/3.0) * np.exp(1j * np.pi * r / 4.0)

def Cr_mag_sq(r):
    """|C(r)|^2 = (1+2r)^2 * exp(-2r/3)."""
    if r == 0:
        return 0.0
    return (1 + 2*r)**2 * np.exp(-2*r/3.0)


# ===================== Graph builders =====================

def ring_graph_adj(N, degree):
    """Circulant graph: node i connects to i +/- 1..degree/2."""
    h = degree // 2
    adj = np.zeros((N, N), dtype=np.int8)
    for i in range(N):
        for k in range(1, h + 1):
            adj[i, (i + k) % N] = 1
            adj[i, (i - k) % N] = 1
    return adj

def complete_graph_adj(N):
    return (np.ones((N, N), dtype=np.int8) - np.eye(N, dtype=np.int8))

def hypercube_adj(dim):
    """Q_dim: 2^dim nodes, degree=dim, diameter=dim."""
    N = 2**dim
    adj = np.zeros((N, N), dtype=np.int8)
    for i in range(N):
        for b in range(dim):
            adj[i, i ^ (1 << b)] = 1
    return adj

def petersen_adj():
    """Petersen graph: 10 nodes, 3-regular, diameter 2."""
    edges = [
        (0,1),(1,2),(2,3),(3,4),(4,0),
        (5,7),(7,9),(9,6),(6,8),(8,5),
        (0,5),(1,6),(2,7),(3,8),(4,9),
    ]
    adj = np.zeros((10, 10), dtype=np.int8)
    for i, j in edges:
        adj[i, j] = adj[j, i] = 1
    return adj


# ===================== Distance matrix (BFS) =====================

def all_pairs_bfs(adj):
    N = adj.shape[0]
    dist = np.zeros((N, N), dtype=np.int32)
    for source in range(N):
        d = np.full(N, -1, dtype=np.int32)
        d[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v in np.where(adj[u] > 0)[0]:
                if d[v] == -1:
                    d[v] = d[u] + 1
                    queue.append(v)
        dist[source] = d
    return dist


# ===================== Build C matrix and amplification =====================

def build_C_from_dist(dist):
    """Apply C(r) element-wise to distance matrix. Lambda=1, skip diagonal."""
    N = dist.shape[0]
    r = dist.astype(np.float64)
    C = np.zeros((N, N), dtype=np.complex128)
    mask = r > 0
    C[mask] = (1 + 2*r[mask]) * np.exp(-r[mask]/3.0) * np.exp(1j * np.pi * r[mask] / 4.0)
    return C

def amplification(C):
    """lambda_max(C†C). Uses eigvalsh since C†C is Hermitian PSD."""
    M = C.conj().T @ C
    evals = np.linalg.eigvalsh(M)
    return float(evals[-1])

def trace_amplification(C):
    """tr(C†C) / N = average eigenvalue = Frobenius norm² / N."""
    N = C.shape[0]
    return float(np.real(np.trace(C.conj().T @ C))) / N

def top_eigenvalues(C, k=5):
    """Return top k eigenvalues of C†C."""
    M = C.conj().T @ C
    evals = np.linalg.eigvalsh(M)
    return evals[-k:][::-1]


# ===================== Analytical reference =====================

def Cr_opt_mag_sq():
    """|C(r_opt)|^2 where r_opt = 2.5. The per-pair peak coherence."""
    return Cr_mag_sq(2.5)

def infinite_sum_per_degree():
    """
    Sum_{k=1}^{inf} |C(k)|^2 = Sum (1+2k)^2 exp(-2k/3).
    This times d gives tr(C†C)/N for a d-regular graph (large N).
    """
    total = 0.0
    for k in range(1, 200):
        total += Cr_mag_sq(k)
    return total


# ===================== Scans =====================

def scan_ring_graphs():
    """Ring graphs: vary N and degree d. Report amplification."""
    print("=" * 78)
    print("SCAN 1: RING GRAPHS — C(r) on distances, lambda=1")
    print("=" * 78)
    print()

    degrees = [2, 4, 6, 8, 10, 12, 16, 20]
    sizes = [32, 64, 128, 256]

    print(f"{'d':>4} |", end="")
    for N in sizes:
        print(f"{'N='+str(N):>12}", end="")
    print(f"{'converged?':>14}")
    print("-" * (4 + 1 + 12*len(sizes) + 14))

    converged = {}
    for d in degrees:
        print(f"{d:4d} |", end="")
        row = []
        for N in sizes:
            if d >= N:
                print(f"{'—':>12}", end="")
                continue
            adj = ring_graph_adj(N, d)
            dist = all_pairs_bfs(adj)
            C = build_C_from_dist(dist)
            A = amplification(C)
            row.append(A)
            print(f"{A:12.2f}", end="")

        if len(row) >= 2:
            drift = abs(row[-1] - row[-2]) / max(abs(row[-1]), 1e-10)
            tag = "YES" if drift < 0.01 else f"drift {drift:.1%}"
            converged[d] = row[-1]
        else:
            tag = "—"
        print(f"{tag:>14}")

    return converged

def scan_convergence_detail():
    """Fix d, increase N, show convergence behavior."""
    print()
    print("=" * 78)
    print("SCAN 2: CONVERGENCE IN N (does amplification stabilize?)")
    print("=" * 78)
    print()

    for d in [4, 8, 12]:
        sizes = [16, 32, 64, 128, 256, 512]
        print(f"  d = {d}:")
        prev = None
        for N in sizes:
            if d >= N:
                continue
            adj = ring_graph_adj(N, d)
            dist = all_pairs_bfs(adj)
            C = build_C_from_dist(dist)
            A = amplification(C)
            delta = f"  (delta {A - prev:+.4f})" if prev is not None else ""
            print(f"    N = {N:4d}:  A = {A:10.4f}{delta}")
            prev = A
        print()

def scan_other_families():
    """Complete graphs, hypercubes, Petersen."""
    print("=" * 78)
    print("SCAN 3: OTHER GRAPH FAMILIES")
    print("=" * 78)
    print()

    # Complete graphs
    print("  Complete graphs K_N (all distances = 1):")
    for N in [4, 8, 16, 32, 64]:
        adj = complete_graph_adj(N)
        dist = all_pairs_bfs(adj)
        C = build_C_from_dist(dist)
        A = amplification(C)
        print(f"    K_{N:3d}:  d={N-1:3d}, diam=1, A = {A:10.2f}")

    print()
    print("  Hypercubes Q_k (N=2^k, d=k, diam=k):")
    for k in range(2, 10):
        N = 2**k
        adj = hypercube_adj(k)
        dist = all_pairs_bfs(adj)
        C = build_C_from_dist(dist)
        A = amplification(C)
        print(f"    Q_{k:2d}:  N={N:4d}, d={k:2d}, diam={k:2d}, A = {A:10.2f}")

    print()
    print("  Petersen graph (N=10, d=3, diam=2):")
    adj = petersen_adj()
    dist = all_pairs_bfs(adj)
    C = build_C_from_dist(dist)
    A = amplification(C)
    print(f"    Petersen:  A = {A:10.2f}")

def find_402_degree():
    """What degree d in a ring graph gives A ≈ 402?"""
    print()
    print("=" * 78)
    print("SCAN 4: HUNTING FOR 402 — what ring-graph degree produces it?")
    print("=" * 78)
    print()

    N = 256
    best_d = None
    best_diff = float('inf')

    print(f"  N = {N}, scanning d = 2..120:")
    print(f"  {'d':>4}  {'A':>12}  {'|A-402|':>10}  note")
    print(f"  {'-'*4}  {'-'*12}  {'-'*10}  {'-'*20}")

    for d in range(2, 122, 2):
        if d >= N:
            break
        adj = ring_graph_adj(N, d)
        dist = all_pairs_bfs(adj)
        C = build_C_from_dist(dist)
        A = amplification(C)
        diff = abs(A - 402.3)

        note = ""
        if diff < best_diff:
            best_diff = diff
            best_d = d
            if diff < 5:
                note = "<-- CLOSE"
            elif diff < 20:
                note = "<-- warm"

        if d <= 30 or d % 10 == 0 or diff < 20:
            print(f"  {d:4d}  {A:12.2f}  {diff:10.2f}  {note}")

    print()
    print(f"  Closest to 402.3: d = {best_d}, A = {best_diff + 402.3:.2f} (off by {best_diff:.2f})")

def structural_multiplier():
    """
    A / |C(r_opt)|^2 for each graph.
    This factors out the per-pair coherence and shows the structural contribution.
    If T^2 * kappa = A / 6.7995, what does the graph structure give us?
    """
    print()
    print("=" * 78)
    print("SCAN 5: STRUCTURAL MULTIPLIER  A / |C(r_opt)|^2")
    print("=" * 78)
    print()

    Cr_opt = Cr_opt_mag_sq()
    print(f"  |C(r_opt=2.5)|^2 = {Cr_opt:.4f}")
    print(f"  To get A_EGT = 402.3, need multiplier = {402.3 / Cr_opt:.2f}")
    print()

    N = 256
    print(f"  Ring graphs (N={N}):")
    print(f"  {'d':>4}  {'A':>12}  {'A/|C_opt|^2':>14}  {'tr/N':>12}  {'tr/(N*|C_opt|^2)':>18}")
    print(f"  {'-'*4}  {'-'*12}  {'-'*14}  {'-'*12}  {'-'*18}")

    for d in [2, 4, 6, 8, 10, 12, 16, 20, 30, 40]:
        if d >= N:
            break
        adj = ring_graph_adj(N, d)
        dist = all_pairs_bfs(adj)
        C = build_C_from_dist(dist)
        A = amplification(C)
        tr = trace_amplification(C)
        print(f"  {d:4d}  {A:12.2f}  {A/Cr_opt:14.2f}  {tr:12.2f}  {tr/Cr_opt:18.2f}")

def eigenvalue_anatomy():
    """Look at the top eigenvalues, not just the max."""
    print()
    print("=" * 78)
    print("SCAN 6: EIGENVALUE ANATOMY — top 5 eigenvalues of C†C")
    print("=" * 78)
    print()

    N = 128
    for d in [4, 8, 12, 20]:
        adj = ring_graph_adj(N, d)
        dist = all_pairs_bfs(adj)
        C = build_C_from_dist(dist)
        top = top_eigenvalues(C, k=5)
        print(f"  Ring N={N}, d={d}:")
        for i, ev in enumerate(top):
            ratio = ev / top[0] if top[0] > 0 else 0
            print(f"    lambda_{i}: {ev:12.4f}  (ratio to max: {ratio:.4f})")
        print(f"    gap lambda_0/lambda_1: {top[0]/top[1]:.2f}x" if top[1] > 0 else "")
        print()

def constant_sensitivity():
    """
    Vary the C(r) constants one at a time.
    Which ones does the amplification depend on?
    """
    print()
    print("=" * 78)
    print("SCAN 7: CONSTANT SENSITIVITY — vary one constant, fix the rest")
    print("=" * 78)
    print()

    N = 128
    d = 8

    adj = ring_graph_adj(N, d)
    dist_mat = all_pairs_bfs(adj)
    r = dist_mat.astype(np.float64)
    mask = r > 0

    def build_custom_C(linear_coeff, decay_rate, phase_rate):
        C = np.zeros((N, N), dtype=np.complex128)
        C[mask] = (1 + linear_coeff * r[mask]) * np.exp(-r[mask] * decay_rate) * \
                  np.exp(1j * np.pi * r[mask] * phase_rate)
        return C

    # Baseline
    C0 = build_custom_C(2.0, 1/3, 1/4)
    A0 = amplification(C0)
    print(f"  Baseline (linear=2, decay=1/3, phase=pi/4): A = {A0:.2f}")
    print()

    # Vary linear coefficient
    print("  Varying LINEAR coefficient (default=2):")
    for lc in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
        C = build_custom_C(lc, 1/3, 1/4)
        A = amplification(C)
        print(f"    linear={lc:.1f}: A = {A:10.2f}  (ratio to baseline: {A/A0:.2f})")
    print()

    # Vary decay rate
    print("  Varying DECAY rate (default=1/3):")
    for dr in [0.1, 0.2, 1/3, 0.5, 0.7, 1.0]:
        C = build_custom_C(2.0, dr, 1/4)
        A = amplification(C)
        print(f"    decay={dr:.3f}: A = {A:10.2f}  (ratio: {A/A0:.2f})")
    print()

    # Vary phase rate
    print("  Varying PHASE rate (default=1/4, giving pi/4 per unit r):")
    for pr in [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5]:
        C = build_custom_C(2.0, 1/3, pr)
        A = amplification(C)
        print(f"    phase_rate={pr:.2f}: A = {A:10.2f}  (ratio: {A/A0:.2f})")


# ===================== Main =====================

def main():
    print()
    print("=" * 78)
    print("  C(r) ON GRAPH DISTANCES — what amplification actually falls out?")
    print("  C(r) = (1+2r) exp(-r/3) exp(i*pi*r/4),  lambda=1 throughout")
    print("=" * 78)
    print()

    # Reference values
    print("Reference:")
    print(f"  |C(r_opt=2.5)|^2 = {Cr_opt_mag_sq():.4f}")
    print(f"  Sum_k |C(k)|^2 (k=1..inf) = {infinite_sum_per_degree():.4f}")
    print(f"  Target: A_EGT = 402.3")
    print()

    scan_ring_graphs()
    scan_convergence_detail()
    scan_other_families()
    find_402_degree()
    structural_multiplier()
    eigenvalue_anatomy()
    constant_sensitivity()

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print("""
What this script measures:
  lambda_max(C†C) where C_ij = C(dist(i,j)) on various graphs.
  This is the maximum collective amplification from the connectivity structure.

What "402 emerging from structure" would mean:
  A specific graph family produces lambda_max ≈ 402 for natural/canonical
  parameter values, independent of N (scale-invariant).

What "402 NOT emerging" would mean:
  The amplification depends on degree d (a choice), and 402 requires
  a specific d — meaning the graph structure doesn't uniquely select 402.
  The number would still need to come from somewhere else.

The numbers above tell you which case we're in.
""")


if __name__ == "__main__":
    main()
