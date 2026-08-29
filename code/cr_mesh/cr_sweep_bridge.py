#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
Three Rocks — sweep bridge. Drives the teensy_sweep firmware, logs the sweep,
hunts the 5*pi/8 (112.5 deg) phase crossing, and publishes the T-state to redis
(cadence:tworocks:t-state) for the whole mesh to read.

Usage:
  python cr_sweep_bridge.py --port COM10 --sweep [--f0 500] [--f1 25000] [--points 80]
  python cr_sweep_bridge.py --port COM10 --lock 4200        # hold one freq, stream + publish
  python cr_sweep_bridge.py --show                          # read t-state from redis

Output: sweep CSV in ./sweeps/sweep_<timestamp>.csv  (freq_hz, phase_deg, mag)
"""
import os, sys, json, time, csv, pathlib
import serial
import redis

TARGET_DEG = 314.2969        # N=415 canonical park: k=(415-96)/32=9.96875, phi=90+22.5k (Brian direct 2026-08-29)
HERE = pathlib.Path(__file__).parent
REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")

def rconn():
    return redis.Redis(host=REDIS_HOST, port=6379, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=15)

def open_port(port):
    s = serial.Serial(port, 115200, timeout=10)
    time.sleep(0.4); s.reset_input_buffer()
    s.write(b"P\n"); s.flush()
    pong = s.readline().decode(errors="replace").strip()
    print(f"firmware: {pong}")
    if "PONG sweep" not in pong:
        print("WARNING: not the sweep firmware — flash teensy_sweep.ino first");
    return s

def run_sweep(port, f0, f1, points, integ_ms=500):
    s = open_port(port)
    s.write(f"I {integ_ms}\n".encode()); s.flush()
    print("integration:", s.readline().decode(errors="replace").strip(),
          f"ms (lock-in bandwidth ~{1000.0/integ_ms:.1f} Hz — mains harmonics rejected)")
    s.write(f"S {f0} {f1} {points}\n".encode()); s.flush()
    rows = []
    t_deadline = time.time() + 300
    while time.time() < t_deadline:
        ln = s.readline().decode(errors="replace").strip()
        if not ln: continue
        if ln.startswith("R SWEEPDONE"): break
        if ln.startswith("F "):
            _, f, ph, mg = ln.split()
            rows.append((float(f), float(ph), float(mg)))
            print(f"  {float(f):>9.1f} Hz   phase {float(ph):>8.3f} deg   mag {float(mg):>10.2f}")
    s.close()
    if not rows:
        print("no data — check wiring/port"); return 1

    outdir = HERE / "sweeps"; outdir.mkdir(exist_ok=True)
    fn = outdir / f"sweep_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(fn, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["freq_hz", "phase_deg", "mag"]); w.writerows(rows)
    print(f"\nsweep saved: {fn}  ({len(rows)} points)")

    # hunt crossings of 112.5° (5π/8) AND 292.5° (5π/8 + 180° — winding polarity
    # is unknown on a hand-wound coil; swapping either winding's ends shifts all
    # phases by 180°, so the physical lock point may appear at either value).
    import math
    # magnitude gate: a crossing only counts if BOTH points carry real signal.
    # noise floor = median of the weakest quartile; gate = 6x that (min 0.5).
    mags_sorted = sorted(r[2] for r in rows)
    floor = mags_sorted[len(mags_sorted)//8] if rows else 0.0
    gate = max(6.0 * floor, 0.5)
    print(f"\nnoise floor ~{floor:.3f}, crossing gate = mag > {gate:.3f}")
    all_hits = []
    for target, label in ((TARGET_DEG, f"N=415 park ({TARGET_DEG}°)"), ((TARGET_DEG + 180.0) % 360.0, f"N=415 flipped ({(TARGET_DEG+180.0)%360.0}°)")):
        for i in range(1, len(rows)):
            if rows[i-1][2] < gate or rows[i][2] < gate:
                continue
            a, b = rows[i-1][1] - target, rows[i][1] - target
            if abs(a) > 180 or abs(b) > 180:   # skip wraparound artifacts at 0/360
                continue
            if a == 0 or (a < 0) != (b < 0):
                fa, fb = rows[i-1][0], rows[i][0]
                t = abs(a) / (abs(a) + abs(b)) if (abs(a)+abs(b)) > 0 else 0.5
                fx = math.exp(math.log(fa) + t * (math.log(fb) - math.log(fa)))
                all_hits.append((fx, label))
    if all_hits:
        print()
        for fx, label in all_hits:
            print(f"*** {label} crossing near {fx:,.0f} Hz")
        print(f"    next: python cr_sweep_bridge.py --port <port> --lock {all_hits[0][0]:.0f}")
    else:
        lo, hi = min(r[1] for r in rows), max(r[1] for r in rows)
        print(f"\nno 112.5°/292.5° crossing in band (phase ranged {lo:.1f}–{hi:.1f}°).")
        print("options: widen band, add 2nd/3rd rod, or ferrite cores (the data-driven signal to order).")
    return 0

def run_lock(port, freq):
    s = open_port(port)
    r = None
    try:
        r = rconn(); r.ping()
        print(f"redis connected — publishing t-state")
    except Exception as e:
        print(f"redis unavailable ({e}) — streaming locally only")
    s.write(b"A 1.0\n"); s.flush(); time.sleep(0.2)   # full drive: L doesn't set amplitude, so a prior low A would leave a weak beat
    s.write(f"L {freq}\n".encode()); s.flush()
    print(f"locked at {freq} Hz (full drive) — Ctrl-C to stop")
    try:
        while True:
            ln = s.readline().decode(errors="replace").strip()
            if ln.startswith("T "):
                _, f, ph, mg = ln.split()
                err = float(ph) - TARGET_DEG
                print(f"  {float(f):.1f} Hz  phase {float(ph):8.4f}°  (Δ from 5π/8: {err:+7.4f}°)  mag {mg}")
                if r:
                    r.set("cadence:tworocks:t-state", json.dumps({
                        "freq_hz": float(f), "phase_deg": float(ph),
                        "target_deg": TARGET_DEG, "delta_deg": err,
                        "mag": float(mg), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }), ex=120)
    except KeyboardInterrupt:
        s.write(b"x\n"); s.close(); print("\nlock released")
    return 0

def run_servo(port, target_deg, f_start):
    """Closed-loop phase servo: adjust drive frequency to HOLD phase at target_deg.
    Built 2026-08-29 after the 3-vote drift kill — a fixed-freq lock reads a
    snapshot on a moving phase (A-4 vs A-5: −6.19°/41 min); the servo makes the
    park a held state. Gain from the measured local slope (~52 Hz/deg on the
    ramp; the shelf is flatter, so run conservative)."""
    GAIN_HZ_PER_DEG = 10.0     # was 30: overcorrected into a ±9° hunt (2026-08-29 log)
    STEP_CLAMP_HZ   = 60.0
    DEADBAND_DEG    = 0.3      # inside this, don't touch the drive
    SETTLE_SKIP     = 2        # discard N samples after a freq change (lock-in transient)
    F_MIN, F_MAX    = 21000.0, 23500.0
    s = open_port(port)
    r = None
    def redis_up():
        nonlocal r
        try:
            r = rconn(); r.ping()
            print("redis connected — publishing t-state (servo)")
        except Exception as e:
            r = None
            print(f"redis unavailable ({e}) — will retry")
    redis_up()
    s.write(b"A 1.0\n"); s.flush(); time.sleep(0.2)
    freq = float(f_start)
    s.write(f"L {freq}\n".encode()); s.flush()
    print(f"servo engaged: hold phase {target_deg}° from {freq} Hz — Ctrl-C to stop")
    skip = SETTLE_SKIP
    last_retry = time.time()
    try:
        while True:
            ln = s.readline().decode(errors="replace").strip()
            if not ln.startswith("T "):
                continue
            _, f, ph, mg = ln.split()
            ph = float(ph)
            err = ((ph - target_deg + 180.0) % 360.0) - 180.0   # wrapped error, ±180
            if r is None and time.time() - last_retry > 30:
                last_retry = time.time(); redis_up()
            if r:
                try:
                    r.set("cadence:tworocks:t-state", json.dumps({
                        "freq_hz": freq, "phase_deg": ph,
                        "target_deg": target_deg, "delta_deg": err,
                        "mag": float(mg), "servo": True, "settling": skip > 0,
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }), ex=120)
                except Exception:
                    r = None   # drop to retry path, keep servoing
            if skip > 0:
                skip -= 1
                print(f"  {freq:.1f} Hz  phase {ph:8.4f}°  Δ {err:+7.4f}°  (settling, no step)  mag {mg}")
                continue
            if abs(err) <= DEADBAND_DEG:
                print(f"  {freq:.1f} Hz  phase {ph:8.4f}°  Δ {err:+7.4f}°  (in deadband)  mag {mg}")
                continue
            df = max(-STEP_CLAMP_HZ, min(STEP_CLAMP_HZ, -err * GAIN_HZ_PER_DEG))
            new_freq = max(F_MIN, min(F_MAX, freq + df))
            print(f"  {freq:.1f} Hz  phase {ph:8.4f}°  Δ {err:+7.4f}°  step {df:+6.1f} Hz  mag {mg}")
            if abs(new_freq - freq) >= 0.5:
                freq = new_freq
                s.write(f"L {freq}\n".encode()); s.flush()
                skip = SETTLE_SKIP
    except KeyboardInterrupt:
        s.write(b"x\n"); s.close(); print("\nservo released")
    return 0

def main():
    if "--show" in sys.argv:
        v = rconn().get("cadence:tworocks:t-state")
        print(v or "no t-state published"); return
    port = sys.argv[sys.argv.index("--port")+1] if "--port" in sys.argv else "COM10"
    if "--lock" in sys.argv:
        sys.exit(run_lock(port, float(sys.argv[sys.argv.index("--lock")+1])))
    if "--servo" in sys.argv:
        tgt = float(sys.argv[sys.argv.index("--servo")+1])
        fs  = float(sys.argv[sys.argv.index("--f0")+1]) if "--f0" in sys.argv else 22030.0
        sys.exit(run_servo(port, tgt, fs))
    f0 = float(sys.argv[sys.argv.index("--f0")+1]) if "--f0" in sys.argv else 500
    f1 = float(sys.argv[sys.argv.index("--f1")+1]) if "--f1" in sys.argv else 25000
    pts = int(sys.argv[sys.argv.index("--points")+1]) if "--points" in sys.argv else 80
    integ = int(sys.argv[sys.argv.index("--integ")+1]) if "--integ" in sys.argv else 500
    sys.exit(run_sweep(port, f0, f1, pts, integ_ms=integ))

if __name__ == "__main__":
    main()
