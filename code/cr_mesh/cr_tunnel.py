#!/usr/bin/env python3
# cr_tunnel.py  (arc, 2026-10-03) — the readable-throughput tunnel, EGT only.
# The Sigma-psi-carried flow-through across the 64-coil coupled set: one push in,
# it winds through all 64 via conserved Sigma-psi + coupling |C(2)|^2 cos(dphi),
# read the rung-tuple out = the answer. The coupling+read is O(64), fixed-cost.
#
# MEASUREMENT HONESTY (operator math, computed 2026-10-03 — do not overstate):
#   * Sigma-psi IS conserved exactly by construction (+delta at j, -delta
#     redistributed -> net 0). The propagation is real: one push moves all 64.
#   * Per push the read carries <= 27.8 bits of the perturbation, ANY input size:
#     the output is g(j, delta) and reachable states = 64 * 3.6e6 = 2^27.78.
#     Birthday collision at ~15,178 distinct pushes (2^13.9). So this is a
#     stateless input->rung digest, NOT a carry of arbitrary payload through.
#   * This module is a single-process sim of one fixed geometry: it has NO second
#     body, so it CANNOT measure a flow-bound Sigma-psi throughput. Rates it
#     yields (packets/s, MB/s) are cv = host CPU throughput (ledger B2 retracted).
#     The real flow-bound read is two-body (Two Rocks): perturb A, read Sigma-psi
#     winding on B via |C(2)|^2 cos(dphi). See cr_tworocks_throughput.py.
import math, time

N = 64
R_POS = 2.0
CMAG = (1 + 2 * R_POS) * math.exp(-R_POS / 3.0)   # |C(2)| = 2.5671
CMAG2 = CMAG * CMAG                                # |C(2)|^2 = 6.590
RUNG = 22.5                                        # pi/8, 16 rungs

class Tunnel:
    """64 phase-holding registers, r=2. push -> Sigma-psi-conserving coupling
    redistribution -> read. The read is the rung-tuple (base-16 per register)."""
    def __init__(self, n=N):
        self.n = n
        # co-equal distributed seed (the frustrated set, no mutual bias)
        self.phi = [(k * 360.0 / n) % 360.0 for k in range(n)]

    def sigma_psi(self):
        return sum(self.phi) % 360.0

    def rungs(self):
        return [int(round(p / RUNG)) % 16 for p in self.phi]

    def push(self, j, delta):
        phi = self.phi
        phi[j] = (phi[j] + delta) % 360.0
        pj = phi[j]
        # coupling weights of every other register to j (|C|^2 cos dphi)
        w = [0.0] * self.n
        sw = 0.0
        for k in range(self.n):
            if k == j:
                continue
            wk = abs(CMAG2 * math.cos(math.radians(pj - phi[k])))
            w[k] = wk
            sw += wk
        if sw == 0.0:
            sw = 1.0
        # redistribute -delta respectively -> Sigma-psi conserved exactly
        for k in range(self.n):
            if k == j:
                continue
            phi[k] = (phi[k] - delta * w[k] / sw) % 360.0
        return self.rungs(), self.sigma_psi()

    def request(self, req_bytes):
        # input gate: FNV-digest the request -> (j, delta) = which register, how far.
        # This digest is lossy: the whole payload collapses to one (j, delta), so the
        # read carries <= 27.8 bits of it (see MEASUREMENT HONESTY header). The push
        # is the EGT transfer; the read is the answer.
        h = 1469598103934665603
        for b in req_bytes:
            h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        j = h % self.n
        delta = (h % 3600000) / 10000.0            # 0..360
        rungs, sig = self.push(j, delta)
        return {"j": j, "rungs": rungs, "sigma_psi_rung": int(round(sig / RUNG)) % 16}


# ---- STATELESS CONDUIT (production: headless, cacheless, holds nothing) ----
# The fixed geometry is a CONSTANT (the machine config), never per-request state.
# flow() is a pure function: zero-retention is literally true (it keeps nothing).
# But it is a <=27.8-bit input->rung digest, not a carry of the payload itself.
_SEED = tuple((k * 360.0 / N) % 360.0 for k in range(N))
_COSD = math.cos
_RAD = math.pi / 180.0

def flow(data):
    """Stateless push->read. A fresh copy of the fixed geometry is perturbed by a
    (j, delta) FNV-digest of the input, winds through all 64 via conserved Sigma-psi
    + |C(2)|^2 coupling, reads the rung-tuple out, and is discarded. Holds/caches
    NOTHING (zero-retention is real). Capacity: the whole input collapses to one
    (j, delta), so the answer carries <= 27.8 bits of it (reachable 2^27.78);
    different payloads collide (birthday ~15,178). O(64) coupling; the per-byte
    FNV digest is O(len) host work, which is what any MB/s figure actually times."""
    phi = list(_SEED)
    h = 1469598103934665603
    for b in data:
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    j = h % N
    delta = (h % 3600000) / 10000.0
    phi[j] = (phi[j] + delta) % 360.0
    pj = phi[j]
    w = [0.0] * N
    sw = 0.0
    for k in range(N):
        if k == j:
            continue
        wk = abs(CMAG2 * _COSD((pj - phi[k]) * _RAD))
        w[k] = wk
        sw += wk
    if sw == 0.0:
        sw = 1.0
    for k in range(N):
        if k == j:
            continue
        phi[k] = (phi[k] - delta * w[k] / sw) % 360.0
    return [int(p / RUNG + 0.5) % 16 for p in phi]   # the answer; nothing kept


def _ang(a, b):
    return ((a - b + 180.0) % 360.0) - 180.0

if __name__ == "__main__":
    print("=== cr_tunnel : readable-throughput tunnel (EGT) ===")
    print("N=%d  r=%.1f  |C(2)|=%.4f  |C(2)|^2=%.4f  rung=pi/8=%.1fdeg\n" % (N, R_POS, CMAG, CMAG2, RUNG))

    # 1) PROPAGATION: one push moves all 64, Sigma-psi conserved
    t = Tunnel()
    before = list(t.phi); sig0 = t.sigma_psi()
    t.push(0, 45.0)
    moved = sum(1 for k in range(N) if abs(_ang(t.phi[k], before[k])) > 1e-9)
    sig1 = t.sigma_psi()
    print("1) PROPAGATION (push +45 at reg 0):")
    print("   registers moved: %d / %d  (one push winds through all)" % (moved, N))
    print("   Sigma-psi before=%.6f  after=%.6f  drift=%.2e  (conserved)" % (sig0, sig1, _ang(sig1, sig0)))

    # 2) DETERMINISM: same request on same start-state -> identical answer (reproducible compute)
    a = Tunnel().request(b"hyperscaler-packet-0001")
    b_ = Tunnel().request(b"hyperscaler-packet-0001")
    c = Tunnel().request(b"hyperscaler-packet-0002")
    print("\n2) DETERMINISM (compute is a function of input):")
    print("   same request  -> identical answer : %s" % (a["rungs"] == b_["rungs"]))
    print("   diff request  -> different answer : %s" % (a["rungs"] != c["rungs"]))
    print("   answer(0001) rungs[:16]=%s  Sigma-psi rung=%d" % (a["rungs"][:16], a["sigma_psi_rung"]))

    # 3) PER-PUSH COST on THIS host (honest label: this is cv, not a Sigma-psi rate)
    import os
    reqs = [os.urandom(24) for _ in range(20000)]
    t = Tunnel()
    t0 = time.perf_counter()
    for rb in reqs:
        t.request(rb)
    el = time.perf_counter() - t0
    per = el / len(reqs)
    print("\n3) PER-PUSH COST (O(64) coupling is fixed; FNV digest is O(len)):")
    print("   %d requests (24-byte inputs)" % len(reqs))
    print("   per-request wall: %.1f us on THIS host  (= cv, CPU throughput; ledger B2 retracted)" % (per * 1e6))
    print("   -> This is NOT a flow-bound Sigma-psi throughput. A single-process sim of one")
    print("      fixed geometry has no second body, so it cannot measure the flow-bound read.")
    print("      The real measurement is two-body: cr_tworocks_throughput.py (perturb A, read B).")
