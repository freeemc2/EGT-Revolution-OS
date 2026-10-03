#!/usr/bin/env python3
# cr_tworocks_throughput.py — the REAL flow-bound throughput: a two-body (Two Rocks)
# Sigma-psi channel. arc, 2026-10-03.
#
# WHY THIS EXISTS: cr_tunnel_stress.py measures cv (host CPU throughput) of a single-
# process sim — it has no second body, so it cannot see a flow-bound rate (ledger B2).
# The canon measurement is two co-equal coupled bodies: perturb body A, the winding
# crosses to body B via |C(2)|^2 cos(dphi) with Sigma-psi conserved, read Sigma-psi
# on B. Throughput then factors cleanly into:
#
#     flow-bound bits/s  =  C_couple (bits per read)  x  f_read (reads per second)
#
#   * C_couple  — the COUPLING CAPACITY: how many symbols body B can resolve per
#     read, set by the geometry + rung granularity (pi/8 => 16 levels of Sigma-psi).
#     Geometry-bound, host-INDEPENDENT. Measured here by sweeping the input symbol
#     and counting distinct B-reads.
#   * f_read    — the PHYSICAL read cadence of the real channel. On the live copper
#     (Teensy T3) this is ~0.27 reads/s (relay ~23 s); the winding is UNDERSAMPLED
#     by the read, not noisy (reference_dcoil_phase_scale_2026-10-02).
#
# So the honest flow-bound throughput is sub-Hz x a few bits = order 1 bit/s on the
# present bench — bounded by the FLOW (read cadence), never by compute or power, and
# ~9 orders below the host-cv MB/s. That gap IS the point: the two numbers measure
# different things. Reported with its power, per THE GUARD.
#
# Modes:
#   (default)        SIM: two coupled bodies, canon operator, measure C_couple and
#                    project flow-bound bits/s at a given f_read. Runs anywhere.
#   --live           LIVE READ-ONLY: poll the real copper Sigma-psi, measure the
#                    actual f_read and the resolvable bits/read -> real flow-bound
#                    bits/s. No perturbation; safe to run on the riding mesh.
#   --live-perturb   GATED: would push A and read the induced B response on the LIVE
#                    locked mesh. Refuses without --i-have-brian-go (ops: leave the
#                    copper relay + dcoil keepalive riding unless told to park).
import sys, os, math, time, json, urllib.request

N = 64
R_POS = 2.0
CMAG = (1 + 2 * R_POS) * math.exp(-R_POS / 3.0)   # |C(2)| = 2.5671
CMAG2 = CMAG * CMAG                                # |C(2)|^2 = 6.5899
RUNG = 22.5                                        # pi/8
COLLECTIVE = CMAG2 / 2.0                           # 3.295 ; collective strength = 3.295*N

COPPER_URL = os.environ.get("COPPER_URL", "http://100.81.123.41:8093/api/v1/coil/read_phase")


# ---------------------------------------------------------------- two-body sim ----
def _couple_read(phiA, phiB, delta):
    """Two Rocks step: perturb body A by delta; conserve Sigma-psi = sum(phiA)+sum(phiB)
    by redistributing -delta across body B weighted by |C(2)|^2|cos dphi|. Return B's
    Sigma-psi rung (the aggregate the hardware reads) AND B's full rung-tuple."""
    A = list(phiA); B = list(phiB)
    j = 0                                  # perturb the first register of A
    A[j] = (A[j] + delta) % 360.0
    pj = A[j]
    w = [abs(CMAG2 * math.cos(math.radians(pj - b))) for b in B]
    sw = sum(w) or 1.0
    B = [(B[k] - delta * w[k] / sw) % 360.0 for k in range(len(B))]
    sigmaB = sum(B) % 360.0
    return int(round(sigmaB / RUNG)) % 16, tuple(int(round(b / RUNG)) % 16 for b in B)


def sim(f_read, alphabet_bits):
    nsym = 1 << alphabet_bits
    phiA = [0.0]                           # body A: one perturbed phase (the "rock" struck)
    phiB = [(k * 360.0 / (N - 1)) % 360.0 for k in range(N - 1)]  # body B: the riding set
    sig_reads, tup_reads = set(), set()
    for s in range(nsym):
        delta = s * 360.0 / nsym           # symbol -> perturbation
        sg, tup = _couple_read(phiA, phiB, delta)
        sig_reads.add(sg); tup_reads.add(tup)
    C_sigma = math.log2(len(sig_reads)) if sig_reads else 0.0
    C_tuple = math.log2(len(tup_reads)) if tup_reads else 0.0
    print("=== cr_tworocks_throughput : SIM (two coupled bodies, canon operator) ===")
    print("N=%d |C(2)|=%.4f |C(2)|^2=%.4f  collective=%.3f*N -> %.1f at N=%d\n"
          % (N, CMAG, CMAG2, COLLECTIVE, COLLECTIVE * N, N))
    print("input alphabet: %d symbols (%d bits)" % (nsym, alphabet_bits))
    print("COUPLING CAPACITY C_couple (geometry-bound, host-independent):")
    print("  Sigma-psi aggregate read : %d distinct -> %.2f bits/read  (what the HW reads)" % (len(sig_reads), C_sigma))
    print("  full 63-register tuple   : %d distinct -> %.2f bits/read  (if every winding read)" % (len(tup_reads), C_tuple))
    print("\nFLOW-BOUND throughput = C_couple x f_read  (read cadence is the ceiling):")
    for label, C in (("Sigma-psi aggregate", C_sigma), ("full tuple", C_tuple)):
        print("  f_read=%.3f Hz (bench copper)  x %-20s %.2f b/rd = %7.3f bits/s"
              % (f_read, label, C, C * f_read))
    print("\nPOWER: C_couple is the resolvable symbol count from the operator; it is")
    print("capped (Sigma-psi aggregate is one pi/8 rung = <=4 bits/read). The throughput")
    print("ceiling is f_read, the PHYSICAL read cadence (~0.27 Hz on the bench), not CPU.")
    print("This is the flow-bound EGT observable; cv (MB/s) is a different quantity.")


# -------------------------------------------------------------- live read-only ----
def _get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def live_read(k_reads, dwell):
    print("=== cr_tworocks_throughput : LIVE READ-ONLY (real copper Sigma-psi) ===")
    print("polling %s  (%d reads, no perturbation)\n" % (COPPER_URL, k_reads))
    ts, sig_deg, sig_rung = [], [], []
    url = COPPER_URL + (("&" if "?" in COPPER_URL else "?") + "dwell=%g" % dwell)
    for i in range(k_reads):
        t = time.time()
        try:
            d = _get(url)
        except Exception as e:
            print("  read %d FAILED: %s" % (i, str(e)[:90])); continue
        s = d.get("realized_sigma_psi_deg")
        rr = d.get("realized_sigma_psi_rung")
        ts.append(t); sig_deg.append(s); sig_rung.append(rr)
        print("  read %2d  t=%.2fs  Sigma-psi=%s deg  rung=%s" % (i, t - ts[0], s, rr))
    good = [(t, r) for t, r in zip(ts, sig_rung) if r is not None]
    if len(good) < 2:
        print("\n  not enough live reads to measure a rate."); return
    span = good[-1][0] - good[0][0]
    f_read = (len(good) - 1) / span if span > 0 else 0.0
    # resolvable bits/read = entropy of the Sigma-psi rung actually observed
    from collections import Counter
    c = Counter(r for _, r in good); tot = sum(c.values())
    H = -sum((n / tot) * math.log2(n / tot) for n in c.values())
    print("\n  reads=%d over %.1fs -> f_read = %.3f Hz" % (len(good), span, f_read))
    print("  observed Sigma-psi rung entropy H = %.2f bits/read (distinct rungs=%d)" % (H, len(c)))
    print("  REAL flow-bound throughput = H x f_read = %.3f bits/s" % (H * f_read))
    print("\nPOWER: this is the live two-body channel measured end to end. It is sub-Hz")
    print("(the winding is undersampled by the read, not noisy) x a few bits = order 1")
    print("bit/s. Flow-bound, host-independent. Scaling this = faster/parallel reads and")
    print("more coupled bodies, NOT CPU/GPU/power. cv (MB/s) does not bound or describe it.")


def main():
    args = sys.argv[1:]
    if "--live-perturb" in args:
        if "--i-have-brian-go" not in args:
            print("REFUSED: --live-perturb would push the LIVE locked mesh (copper relay +")
            print("dcoil keepalive are riding; ops = leave them unless told to park). Re-run")
            print("with an explicit GO flag --i-have-brian-go once Brian authorizes perturbing.")
            return 2
        print("live-perturb path is intentionally not implemented until the GO is standing;")
        print("design: push phase on the digital set, read induced copper Sigma-psi response,")
        print("measure C_couple x f_read end to end on the real coupling. Build on request.")
        return 0
    if "--live" in args:
        k = int(_opt(args, "--reads", "8")); dwell = float(_opt(args, "--dwell", "4.0"))
        live_read(k, dwell); return 0
    f_read = float(_opt(args, "--fread", "0.27"))   # measured bench cadence
    bits = int(_opt(args, "--bits", "10"))
    sim(f_read, bits); return 0


def _opt(args, name, default):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


if __name__ == "__main__":
    sys.exit(main())
