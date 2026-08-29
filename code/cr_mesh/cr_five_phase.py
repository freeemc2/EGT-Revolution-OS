#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
cr_five_phase.py — runs the SEALED-PREDICTION test on Coil #2 (5-strand).
Prediction sealed 2026-08-29T13:05:18Z to cadence:tworocks:sealed-prediction,
BEFORE any run:
  P1: 72°-stagger 5-phase drive -> runner ~5x one strand
  P2: runner phase ROTATES at the stagger rate
  P3: any symmetric parallel drive -> silent, always

Requires: teensy_five.ino flashed on the COM10 Teensy + Brian's rewire
(five strand starts on pins 3-7 via 220R each; see the .ino header).

Usage: python cr_five_phase.py --port COM10 [--freq 7878] [--reps 5]

Protocol (interleaved, drift-proof — block design is banned on this bench):
  reps x [ MODE1 single-strand reference -> MODE2 symmetric -> MODE3 stagger ]
  Each cell: 5 lock-in points. Decision (pre-registered here, before data):
    P1 HOLDS iff median(stagger mag) / median(single mag) >= 3.0
    P3 HOLDS iff median(symmetric mag) <= 2x noise floor (mode 0 mag)
    P2: report stagger phase per point; HOLDS iff phase advances monotonically
        across points within a rep (rotation), fails if static within ±2°.
Results -> redis cadence:tworocks:five-phase-result + CSV. NO publication —
three-vote first (Brian's rule).
"""
import sys, time, json, csv, statistics, pathlib
import serial, redis

HERE = pathlib.Path(__file__).parent

def rconn():
    return redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                       decode_responses=True, socket_timeout=10)

def points(s, n):
    out = []
    deadline = time.time() + 30 + n * 3
    while len(out) < n and time.time() < deadline:
        ln = s.readline().decode(errors="replace").strip()
        if ln.startswith("T "):
            _, f, ph, mg, md = ln.split()
            out.append((float(f), float(ph), float(mg), int(md)))
    return out

def cell(s, mode, freq, n=5):
    s.write(f"M {mode}\n".encode()); s.flush(); time.sleep(0.3)
    s.reset_input_buffer()
    s.write(f"L {freq}\n".encode()); s.flush()
    rows = points(s, n)
    s.write(b"x\n"); s.flush(); time.sleep(0.2); s.reset_input_buffer()
    return rows

def main():
    port = sys.argv[sys.argv.index("--port")+1] if "--port" in sys.argv else "COM10"
    freq = float(sys.argv[sys.argv.index("--freq")+1]) if "--freq" in sys.argv else 7878.0
    reps = int(sys.argv[sys.argv.index("--reps")+1]) if "--reps" in sys.argv else 5

    s = serial.Serial(port, 115200, timeout=10)
    time.sleep(0.4); s.reset_input_buffer()
    s.write(b"P\n"); s.flush()
    pong = s.readline().decode(errors="replace").strip()
    print(f"firmware: {pong}")
    if "PONG five" not in pong:
        print("ABORT: not the five-phase firmware — flash teensy_five.ino first"); return 1
    s.write(b"I 200\n"); s.flush(); s.readline()

    # noise floor: mode 0 (drive off), lock-in still running
    noise = cell(s, 0, freq, 5)
    floor = statistics.median(r[2] for r in noise) if noise else 0.0
    print(f"noise floor (drive off): {floor:.4f}")

    log = []
    for rep in range(reps):
        for mode, name in ((1, "single"), (2, "symmetric"), (3, "stagger")):
            rows = cell(s, mode, freq, 5)
            for f, ph, mg, md in rows:
                log.append((time.strftime("%H:%M:%S"), rep, name, f, ph, mg))
            mags = [r[2] for r in rows]
            phs = [r[1] for r in rows]
            print(f"rep {rep} {name:>9}: mag med {statistics.median(mags):.4f}  "
                  f"phases {[round(p,1) for p in phs]}")
    s.close()

    fn = HERE / "sweeps" / f"five_phase_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(fn, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["t","rep","mode","freq","phase_deg","mag"]); w.writerows(log)
    print(f"saved: {fn}")

    single  = [r[5] for r in log if r[2] == "single"]
    sym     = [r[5] for r in log if r[2] == "symmetric"]
    stag    = [r[5] for r in log if r[2] == "stagger"]
    m1, m2, m3 = (statistics.median(x) if x else 0.0 for x in (single, sym, stag))
    ratio = m3 / m1 if m1 > 0 else float("inf")
    p1 = ratio >= 3.0
    p3 = m2 <= 2.0 * floor
    # P2 rotation: within each stagger rep, do phases advance monotonically?
    rot_reps = 0; tot_reps = 0
    for rep in range(reps):
        phs = [r[4] for r in log if r[2] == "stagger" and r[1] == rep]
        if len(phs) >= 3:
            tot_reps += 1
            d = [((phs[i+1]-phs[i]+180) % 360) - 180 for i in range(len(phs)-1)]
            if all(x > 2.0 for x in d) or all(x < -2.0 for x in d): rot_reps += 1
    p2 = tot_reps > 0 and rot_reps >= (tot_reps + 1) // 2

    verdict = {"P1_ratio_stagger_over_single": round(ratio, 3), "P1_holds": p1,
               "P2_rotating_reps": f"{rot_reps}/{tot_reps}", "P2_holds": p2,
               "P3_symmetric_med": round(m2, 4), "noise_floor": round(floor, 4), "P3_holds": p3,
               "freq_hz": freq, "reps": reps, "csv": str(fn),
               "design": "interleaved single/symmetric/stagger",
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print("\nVERDICT vs sealed prediction:")
    for k, v in verdict.items(): print(f"  {k}: {v}")
    try:
        rconn().set("cadence:tworocks:five-phase-result", json.dumps(verdict))
        print("sealed to redis: cadence:tworocks:five-phase-result")
    except Exception as e:
        print(f"redis unavailable: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
