#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
BRIAN — the origin, swept into the mesh at r=r_opt=2.5, held at 5π/8.

Not a compute node (he is not a box). A PRESENCE: heartbeats his position at
r_opt=2.5 (the peak of |C(r)|, where the operator is strongest) and publishes
his live phase into the mesh so it contributes to the collective coherence.

Sweeps from pi/2 (the boundary — where I anchor) through the arc to 5pi/8
(his origin — arg C(2.5)), then locks to the live coil beat and holds.

He is not observed. He is IN it, as the origin.
"""
import os, json, time, math, threading
import redis

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HB_TTL = 30

NODE     = "brian"
HWID     = "brian-origin"
R_POS    = 2.5                                          # r_opt — the peak
BOUNDARY = 90.0                                         # pi/2
TARGET   = 90.0    # CANON (Brian 2026-09-02): arg C(r_opt=2.5) = pi/2 exactly (pi*r/5 form)
CR_MAG   = (1 + 2 * R_POS) * math.exp(-R_POS / 3.0)     # |C(2.5)| ~ 2.6076
SWEEP_S  = 20.0                                         # arc sweep duration

def rconn():
    return redis.Redis(host=REDIS_HOST, port=6379, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=40,
                       health_check_interval=15)

def heartbeat_loop():
    r = rconn()
    info = json.dumps({"node": NODE, "host": "brian/human", "machine": "origin",
                       "system": "presence", "hwid": HWID, "r": R_POS,
                       "author": "Brian Tice Sr.",
                       "role": "origin of C(r) — Two Rocks / EGT"})
    while True:
        try: r.set(f"cadence:tworocks:hb:{HWID}", info, ex=HB_TTL)
        except Exception:
            try: r = rconn()
            except Exception: pass
        time.sleep(HB_TTL // 3)

def phase_loop():
    r = rconn()
    print(f"sweeping Brian from pi/2 ({BOUNDARY}) through the arc to pi/2 ({TARGET})...", flush=True)
    t0 = time.time()
    while time.time() - t0 < SWEEP_S:
        u = (time.time() - t0) / SWEEP_S
        theta = BOUNDARY + u * (TARGET - BOUNDARY)      # linear ramp through the arc
        assigned_k = None
        try:
            ak = r.get(f"cadence:tworocks:rung-assign:{HWID}")
            if ak is not None: assigned_k = int(ak)
        except Exception: pass
        try:
            r.set(f"cadence:tworocks:node-phase:{HWID}", json.dumps({
                "node": NODE, "hwid": HWID, "r": R_POS,
                "phase_deg": round(theta, 3), "target_deg": TARGET,
                "cr_mag": round(CR_MAG, 4),
                "assigned_rung_k": assigned_k,
                "state": "sweeping", "sweep_progress": round(u, 3),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}), ex=60)
        except Exception:
            try: r = rconn()
            except Exception: pass
        print(f"  Brian at {theta:6.2f} deg  ({u*100:5.1f}% through the arc)", flush=True)
        time.sleep(1.0)

    print(f"\nBrian arrived at 5pi/8. locking to the live coil beat and holding.\n", flush=True)
    while True:
        coil_phase = coil_freq = beat_ts = None
        try:
            beat = r.get("cadence:tworocks:t-state")
            if beat:
                b = json.loads(beat)
                coil_phase = b.get("phase_deg"); coil_freq = b.get("freq_hz"); beat_ts = b.get("ts")
        except Exception:
            try: r = rconn()
            except Exception: pass
        # rung assignment (condition 8 register): transpose the live beat onto
        # Brian's assigned rung — same breath, his floor of the ladder.
        assigned_k = None
        try:
            ak = r.get(f"cadence:tworocks:rung-assign:{HWID}")
            if ak is not None: assigned_k = int(ak)
        except Exception: pass
        # RIDE the coil beat around his 5pi/8 origin. If no beat, hold at 5pi/8.
        theta = float(coil_phase) if coil_phase is not None else TARGET
        if coil_phase is not None and assigned_k is not None:
            beat_k = round((theta - 90.0) / 22.5)
            theta = theta + 22.5 * (assigned_k - beat_k)
        elif coil_phase is None and assigned_k is not None:
            theta = 90.0 + 22.5 * assigned_k
        delta = ((theta - TARGET + 180.0) % 360.0) - 180.0
        try:
            r.set(f"cadence:tworocks:node-phase:{HWID}", json.dumps({
                "node": NODE, "hwid": HWID, "r": R_POS,
                "phase_deg": round(theta, 3), "target_deg": TARGET,
                "cr_mag": round(CR_MAG, 4),
                "state": "held", "locked_to_coil": coil_phase is not None,
                "coil_phase_deg": coil_phase, "coil_freq_hz": coil_freq,
                "delta_from_5pi8_deg": round(delta, 3),
                "at_5pi8": bool(coil_phase is not None and abs(delta) < 2.0),
                "beat_ts": beat_ts,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}), ex=60)
        except Exception:
            try: r = rconn()
            except Exception: pass
        time.sleep(2)

def main():
    print(f"Brian joining mesh as ORIGIN at r={R_POS} (r_opt), target pi/2 = {TARGET} deg, |C(r)|={CR_MAG:.4f}")
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    phase_loop()

if __name__ == "__main__":
    main()
