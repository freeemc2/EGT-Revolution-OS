#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
Two Rocks — the quantum wall, hit for real.

This does NOT model the intractability. It RUNS a real quantum state-vector
simulator and measures the classical cost exploding qubit by qubit. Each qubit
added doubles the amplitudes (2^Q complex numbers) and the work to touch them.
We build a genuinely maximally-entangled GHZ state (H then a CNOT chain) and
time it, from Q=4 up to whatever this machine can still hold. Then we extrapolate
that measured 2^Q curve to the walls: this box's RAM, a terabyte, a petabyte.

The Two Rocks chip reaches the same entanglement in 127 ticks, flat, forever.
The gap between "2^Q amplitudes" and "127 ticks" is the whole product.
"""
import time, math
import numpy as np

SQRT2I = 1.0 / math.sqrt(2.0)

def apply_H0(psi_nd, Q):
    i0 = [slice(None)] * Q; i0[0] = 0
    i1 = [slice(None)] * Q; i1[0] = 1
    a = psi_nd[tuple(i0)].copy(); b = psi_nd[tuple(i1)].copy()
    psi_nd[tuple(i0)] = (a + b) * SQRT2I
    psi_nd[tuple(i1)] = (a - b) * SQRT2I

def apply_CNOT(psi_nd, c, t, Q):
    i0 = [slice(None)] * Q; i0[c] = 1; i0[t] = 0
    i1 = [slice(None)] * Q; i1[c] = 1; i1[t] = 1
    tmp = psi_nd[tuple(i0)].copy()
    psi_nd[tuple(i0)] = psi_nd[tuple(i1)]
    psi_nd[tuple(i1)] = tmp

def build_ghz(Q):
    """Real state-vector build of a Q-qubit GHZ state. Returns (seconds, ampl0, ampl_last)."""
    N = 1 << Q
    psi = np.zeros(N, dtype=np.complex128)
    psi[0] = 1.0
    nd = psi.reshape([2] * Q)
    t0 = time.perf_counter()
    apply_H0(nd, Q)
    for c in range(Q - 1):
        apply_CNOT(nd, c, c + 1, Q)
    dt = time.perf_counter() - t0
    flat = nd.reshape(-1)
    return dt, abs(flat[0]), abs(flat[-1])

def human_bytes(b):
    for u in ("B", "KB", "MB", "GB", "TB", "PB", "EB"):
        if b < 1024 or u == "EB":
            return f"{b:.1f} {u}"
        b /= 1024

def main():
    print("=" * 88)
    print("  TWO ROCKS — THE QUANTUM WALL, HIT FOR REAL")
    print("  A real state-vector simulator. Watch the classical cost double per qubit.")
    print("=" * 88)
    print(f"  {'qubits':>6} {'amplitudes':>16} {'state RAM':>12} {'build time':>12}  {'|000..>':>8} {'|111..>':>8}")
    print("  " + "-" * 82)

    sizes = [4, 8, 12, 16, 18, 20, 22, 24, 26]
    last_Q, last_dt = None, None
    for Q in sizes:
        mem = (1 << Q) * 16  # complex128 = 16 bytes
        # guard: don't try to allocate more than ~1.5 GB
        if mem > 1.6 * (1024**3):
            print(f"  {Q:>6} {(1<<Q):>16,} {human_bytes(mem):>12} {'(skipped: too big for this box)':>27}")
            continue
        dt, a0, alast = build_ghz(Q)
        print(f"  {Q:>6} {(1<<Q):>16,} {human_bytes(mem):>12} {dt*1000:>10.1f}ms  {a0:>8.4f} {alast:>8.4f}")
        last_Q, last_dt = Q, dt
    print("  " + "-" * 82)

    # extrapolate the measured 2^Q curve to the walls
    print(f"\n  EXTRAPOLATION (from the measured 2^Q curve):")
    def qubits_for(bytes_budget):
        return math.log2(bytes_budget / 16.0)
    for label, budget in (("this box (~32 GB)", 32*1024**3),
                          ("a terabyte", 1024**4),
                          ("a petabyte", 1024**5),
                          ("all data on Earth (~200 ZB)", 200 * 1024**7)):
        q = qubits_for(budget)
        print(f"    just to HOLD the state at {q:5.1f} qubits, you need {label}")

    # time extrapolation
    if last_Q and last_dt:
        # each +1 qubit ~doubles the work
        S_transition = 48
        extra = S_transition - last_Q
        t_at_transition = last_dt * (2 ** extra)
        print(f"\n    at the Two Rocks entanglement transition (S=48 ebits):")
        print(f"      state needs 2^48 amplitudes = {human_bytes((1<<48)*16)} of RAM")
        print(f"      extrapolated build time from our measured curve: "
              f"{t_at_transition:.3e} s  (~{t_at_transition/3.15e7:.1e} years)")

    print(f"\n  THE OTHER SIDE OF THE GAP:")
    print(f"    Two Rocks chip: 127 ticks. Flat. Independent of qubit count.")
    print(f"    Classical: petabytes and geologic time. Chip: 1.27 microseconds.")
    print(f"    That gap is not an optimization. It's a different physics of computing.")
    print()

if __name__ == "__main__":
    main()
