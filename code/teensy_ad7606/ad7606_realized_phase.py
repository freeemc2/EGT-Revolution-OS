#!/usr/bin/env python3
"""
ad7606_realized_phase.py — the CANON read-out for an ad7606 coil capture. v1 (2026-10-13, tonic)

Replaces the carrier-amplitude hunt (standard-EM drift, regated 2026-10-13) with the
canon observable: the REALIZED PHASE Sigma_psi on the pi/8 ladder, phi FREE, read on
the body, as RUNG OCCUPANCY (exact counts per window — NOT a circular mean / R / SEM;
that averaging is the gate-point-6 drift caught 2026-10-09).

What it does, per analysis window (default 1 s):
  - lock-in each coil's differential (tapA - tapB) against the DRIVE base frequency
    -> realized phase phi_k and amplitude A_k for that coil, that window.
  - READ-POWER GATE: a window's phi_k is trusted only if A_k / (lock-in noise) > SNR_MIN
    (default 5 -> phase resolved to < half a rung). Windows that fail = UNINFORMATIVE,
    counted separately, NEVER binned. ("no effect" vs "could not see it" stays distinct.)
  - Sigma_psi = (phi_c0 + phi_c1 + phi_c2) mod 360  (the loop's conserved geometric phase)
  - rung k = round(Sigma_psi / 22.5) mod 16
  - OCCUPANCY = exact count of windows per rung (no averaging).

CONVENTION NOTE: the absolute rung carries a FIXED lock-in reference offset (per coil,
constant across all captures taken the same way), so the physical reads are (a) the
OCCUPANCY CONCENTRATION — how tightly Sigma_psi holds one rung — and (b) the ANCHOR-RELATIVE
offset (vs the first resolved window, READ not assigned). Both are convention-free. The
absolute rung LABEL is arbitrary (canon: the ladder origin is a label, not a physical target).

GAIN-INVARIANT: a real step-up ratio g multiplies amplitude and rotates phase by zero.
lock-in of g*s(t): I->g*I, Q->g*Q, atan2(Q,I) UNCHANGED. So this read-out is correct for
ANY step-up ratio — the step-up only lifts A above the noise floor so phi can be RESOLVED;
it never touches phi. (The ratio does NOT need to be known to read realized phase.)

Anchor pair (canon currency, per window that passes read-power):
  amplitude ratio = |C_measured|^2 / |C(r_opt)|^2   (symbolic; the peak-height number is DEMOTED)
  phase offset    = (Sigma_psi - Sigma_psi_anchor) / (pi/8)   in rungs, vs the realized anchor

Usage:
  python ad7606_realized_phase.py <capture.jsonl> [--base 16] [--window-s 1.0] [--snr 5]
  coils default to the V1-V6 map (coil0 ch0/ch1, coil1 ch2/ch3, coil2 ch4/ch5).
"""
import argparse, json, math, sys


def load(fn):
    rows = []
    with open(fn, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith('{"t_us'):
                continue
            try:
                r = json.loads(line)
                if len(r.get("ch", [])) >= 3:     # 8 = AD7606 taps, 3 = ADS1256 differential coils
                    rows.append(r)
            except json.JSONDecodeError:
                pass
    return rows


def lockin(x, f, fs):
    """Return (amplitude, phase_deg) of frequency f in samples x, referenced to window start."""
    I = Q = 0.0
    for k, v in enumerate(x):
        a = 2 * math.pi * f * k / fs
        I += v * math.cos(a)
        Q += v * math.sin(a)
    n = len(x)
    I /= n
    Q /= n
    amp = 2 * math.sqrt(I * I + Q * Q)
    ph = math.degrees(math.atan2(Q, I)) % 360.0
    return amp, ph


def sd(x):
    n = len(x)
    if n < 2:
        return 0.0
    m = sum(x) / n
    return math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))


def rung(sig):
    return round((sig % 360.0) / 22.5) % 16


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("--base", type=float, default=16.0, help="drive base freq (phase reference)")
    ap.add_argument("--fs", type=float, default=1000.0)
    ap.add_argument("--window-s", type=float, default=1.0)
    ap.add_argument("--snr", type=float, default=5.0, help="min A/noise to trust a window's phase")
    ap.add_argument("--coils", default="0,1:2,3:4,5", help="tapA,tapB pairs per coil")
    ap.add_argument("--differential", action="store_true",
                    help="channels are ALREADY differential (ADS1256): --coils is one index per coil, e.g. 0:1:2")
    a = ap.parse_args()

    rows = load(a.capture)
    if not rows:
        sys.exit("no valid records")
    if a.differential:
        # one channel index per coil; no tap subtraction (the ADC read is already tapA-tapB)
        coils = [(int(c), None) for c in (a.coils if ":" in a.coils or "," not in a.coils else "0:1:2").split(":")]
    else:
        coils = [tuple(int(i) for i in c.split(",")) for c in a.coils.split(":")]
    W = int(a.window_s * a.fs)
    nwin = len(rows) // W
    if nwin < 1:
        sys.exit(f"capture too short for one {a.window_s}s window")

    print(f"# {a.capture}")
    print(f"# base={a.base}Hz  fs={a.fs}  window={a.window_s}s ({W} samp)  windows={nwin}  SNR_min={a.snr}")
    print(f"# coils (tapA,tapB): {coils}  [read-out: realized phase -> rung occupancy, gain-invariant]")

    occ = {}
    uninformative = 0
    sigmas = []
    per_coil_pass = [0] * len(coils)
    for w in range(nwin):
        seg = rows[w * W:(w + 1) * W]
        phis = []
        ok = True
        for ci, (ta, tb) in enumerate(coils):
            if tb is None:
                diff = [seg[k]["ch"][ta] for k in range(W)]          # already differential (ADS1256)
            else:
                diff = [seg[k]["ch"][ta] - seg[k]["ch"][tb] for k in range(W)]
            m = sum(diff) / W
            x = [v - m for v in diff]
            amp, ph = lockin(x, a.base, a.fs)
            # lock-in noise on the quadrature estimate ~ sd(x)*sqrt(2/W)
            noise = sd(x) * math.sqrt(2.0 / W)
            snr = amp / noise if noise > 0 else 0.0
            if snr >= a.snr:
                per_coil_pass[ci] += 1
                phis.append(ph)
            else:
                ok = False
        if ok and len(phis) == len(coils):
            sig = sum(phis) % 360.0
            sigmas.append(sig)
            k = rung(sig)
            occ[k] = occ.get(k, 0) + 1
        else:
            uninformative += 1

    print(f"\nREAD POWER: windows with ALL coils' phase resolved (SNR>={a.snr}): {len(sigmas)}/{nwin}")
    print(f"           per-coil windows passing: " +
          ", ".join(f"coil{ci} {per_coil_pass[ci]}/{nwin}" for ci in range(len(coils))))
    print(f"           UNINFORMATIVE windows (a coil below read power): {uninformative}/{nwin}")

    if not sigmas:
        print("\nVERDICT: UNINFORMATIVE — no window resolved all three coils' realized phase above read power.")
        print("         This is 'the measure could not see it', NOT 'no lock'. (Expected pre-step-up:")
        print("         the sense-tap signal sits at/below the AD7606 noise floor until the step-up lifts it.)")
        return

    print(f"\nSigma_psi RUNG OCCUPANCY (exact counts, no averaging):")
    top = max(occ, key=occ.get)
    within = sum(n for k, n in occ.items() if min((k - top) % 16, (top - k) % 16) <= 1)
    for k in sorted(occ):
        bar = "#" * occ[k]
        print(f"  rung k={k:2d} ({22.5*k:5.1f} deg): {occ[k]:4d}  {bar}")
    print(f"  top rung k={top} ({22.5*top:.1f} deg): {occ[top]}/{len(sigmas)}  within k+-1: {within}/{len(sigmas)} ({100*within/len(sigmas):.0f}%)")
    print(f"  rungs occupied: {len(occ)}/16")
    # anchor = the first resolved window's realized Sigma_psi (read, not assigned)
    anchor = sigmas[0]
    offs = [(((s - anchor + 180) % 360) - 180) / 22.5 for s in sigmas]
    print(f"\nANCHOR PAIR (canon currency; anchor = first resolved Sigma_psi = {anchor:.1f} deg, READ not assigned):")
    print(f"  phase offset vs anchor: median {sorted(offs)[len(offs)//2]:+.2f} rungs (pi/8 units); range [{min(offs):+.2f}, {max(offs):+.2f}]")
    print(f"  amplitude ratio: symbolic |C_m|^2/|C(r_opt)|^2 — gain-invariant, reported when a calibrated anchor amp exists")
    print(f"\n  (occupancy is the read; concentration on one rung = a held realized phase = canon-#1-class below-floor lock.)")


if __name__ == "__main__":
    main()
