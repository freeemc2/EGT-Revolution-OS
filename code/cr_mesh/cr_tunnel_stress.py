#!/usr/bin/env python3
# cr_tunnel_stress.py — max-push + mass-data stress of the STATELESS conduit.
# arc, 2026-10-03.
#
# WHAT THIS MEASURES (honest label, operator math 2026-10-03):
#   This times how fast THIS host's CPython runs flow() over byte arrays. That is
#   cv = CPU throughput (ledger B2 retracted). It is NOT a flow-bound Sigma-psi
#   rate: a single-process sim of one fixed geometry has no second body to carry a
#   winding, so this harness could not have seen a flow-bound throughput even in
#   principle. Use it for a plumbing/host-ceiling number only. The real flow-bound
#   read is two-body (Two Rocks): cr_tworocks_throughput.py.
#
# Also note (why MB/s here is mostly a hash figure): flow() FNV-digests the whole
# payload O(len), THEN runs the fixed O(64) coupling. So MB/s rises with packet
# size because it is timing the per-byte digest loop, not transport of the payload
# (the payload collapses to one (j, delta); <=27.8 bits reach the answer).
# The PULLABLE meter (INSTRUMENT=0 -> records nothing) demonstrates zero-retention.
import sys, os, time, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr_tunnel import flow, N, CMAG

# ---- mass-data seed corpus (encyclopedia-ish, procedurally expanded) ----
KNOWLEDGE = (
    "Geometric coupling below a resonance floor carries a winding without storing it. "
    "The Earth orbits the Sun once per year; water is two hydrogen and one oxygen; "
    "entropy of an isolated system does not decrease; a prime has exactly two divisors; "
    "the Roman empire fell in the west in 476; DNA encodes proteins in triplet codons; "
    "light in vacuum travels at about 299792458 meters per second; the heart has four "
    "chambers; Fourier decomposes a signal into frequencies; the mitochondrion makes ATP; "
    "supply meets demand at a market price; a group has an identity and inverses; "
    "photosynthesis turns carbon dioxide and water into glucose and oxygen; the French "
    "Revolution began in 1789; a derivative is an instantaneous rate of change; plate "
    "tectonics moves continents; Shakespeare wrote Hamlet; the speed of sound in air is "
    "about 343 meters per second; integers are closed under addition and multiplication; "
    "antibiotics do not kill viruses; the Pacific is the largest ocean; a transformer "
    "steps voltage up or down by turns ratio; neurons signal by action potentials. "
) * 8   # ~a few KB base block
KB = KNOWLEDGE.encode()
L = len(KB)

class Meter:
    __slots__ = ("pkts", "bytes_", "on")
    def __init__(self, on):
        self.pkts = 0; self.bytes_ = 0; self.on = on
    def tick(self, nbytes):
        if self.on:                       # PULLABLE: off -> nothing recorded
            self.pkts += 1; self.bytes_ += nbytes

def _packet(i):
    off = (i * 131) % L
    sz = 256 + (i % 1792)                 # 256..2048 bytes, varied
    return (KB * ((sz // L) + 2))[off:off + sz] + i.to_bytes(6, "little")

def run(duration, meter):
    t0 = time.perf_counter(); i = 0
    while time.perf_counter() - t0 < duration:
        pkt = _packet(i)
        flow(pkt)                         # STATELESS transform; answer discarded here
        meter.tick(len(pkt))
        i += 1
    return i, time.perf_counter() - t0

def _worker(args):
    dur, idx = args
    t0 = time.perf_counter(); i = 0; b = 0
    while time.perf_counter() - t0 < dur:
        pkt = _packet(i * 7 + idx)
        flow(pkt); i += 1; b += len(pkt)
    return i, b

if __name__ == "__main__":
    print("=== cr_tunnel_stress : host cv ceiling of the stateless conduit (NOT a Sigma-psi rate) ===")
    print("N=%d |C(2)|=%.4f  corpus block=%d bytes (encyclopedia, expanded)\n" % (N, CMAG, L))

    # 1) INSTRUMENTED single-core: flow() host rate (cv)
    m = Meter(True)
    n, el = run(12.0, m)
    mbps = m.bytes_ / 1e6 / el
    print("1) HOST RATE (instrumented, 1 core, ~12s) -- this is cv, CPU throughput:")
    print("   packets=%d  bytes=%.1f MB  wall=%.2fs" % (m.pkts, m.bytes_ / 1e6, el))
    print("   -> %.0f packets/s  |  %.1f MB/s  |  %.3f ms/packet  (on THIS host)" % (n / el, mbps, 1000 * el / n))

    # 2) PULLED (meter off) -> zero-retention demonstration
    m2 = Meter(False)
    n2, el2 = run(6.0, m2)
    print("\n2) METER PULLED (zero-retention: same work, nothing recorded/readable):")
    print("   ran %d packets in %.2fs; meter.pkts=%d meter.bytes=%d (nothing to read)" %
          (n2, el2, m2.pkts, m2.bytes_))

    # 3) MAX PUSH across all cores (the host ceiling for this build)
    cores = mp.cpu_count()
    print("\n3) MAX PUSH across %d cores (~8s each) -- host ceiling, still cv:" % cores)
    try:
        with mp.Pool(cores) as pool:
            res = pool.map(_worker, [(8.0, k) for k in range(cores)])
        tot_p = sum(r[0] for r in res); tot_b = sum(r[1] for r in res)
        print("   packets=%d  bytes=%.1f MB  -> %.0f packets/s  |  %.1f MB/s  (all cores)" %
              (tot_p, tot_b / 1e6, tot_p / 8.0, tot_b / 1e6 / 8.0))
    except Exception as e:
        print("   (multiproc skipped: %s)" % str(e)[:80])

    print("\nHONEST FRAME: these are host CPU-throughput (cv) numbers for flow() on this box.")
    print("The O(64) coupling is fixed-cost; MB/s mostly times the O(len) FNV digest. This")
    print("harness has no second body, so it cannot read a flow-bound Sigma-psi throughput --")
    print("that requires the two-body (Two Rocks) measurement in cr_tworocks_throughput.py.")
