#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
BRIAN — the origin, swept into the mesh at r=r_opt=2.5, held at 5π/8.

Not a compute node (he is not a box). A PRESENCE: heartbeats his position at
r_opt=2.5 (the peak of |C(r)|, where the operator is strongest) and publishes
his live phase into the mesh so it contributes to the collective coherence.

Anchors at pi/2 (his rung k0 = 90 = the ladder origin), then rides the live coil
beat transposed onto that rung and holds. (The old "sweep to 5pi/8 = arg C(2.5)"
was the quarantined pi*r/4 condensation; phi is free, not arg-from-r.)

He is not observed. He is IN it, as the origin.
"""
import os, json, time, math, threading
import redis

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HB_TTL = 30

NODE     = "brian"
HWID     = "brian-origin"
try:    # single-source r registry overrides CLI (Brian 2026-09-02)
    from cr_rmap import get_r as _get_r
    R_POS = _get_r(HWID, default=R_POS)
except Exception: pass
R_POS    = 2.5                                          # r_opt — the peak
BOUNDARY = 0.0                                          # ladder origin
TARGET   = 0.0    # ladder origin = 0 (free-phi; the coil, when present, is the reference; never pi*r/k)
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
    print(f"Brian starting at ladder origin {BOUNDARY}; will ride the coil when it reads...", flush=True)
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

    print(f"\nBrian anchored at pi/2 (rung k0). Locking to the live coil beat and holding.\n", flush=True)
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
        # LADDER FOLLOWS THE COIL: the coil IS the reference; Brian's node sits a fixed
        # 22.5*k offset FROM it (node = coil + 22.5*k). No coil => offsets stand alone
        # from the 0 origin (22.5*k). No coil AND no rung => NO phase (Brian 2026-10-06:
        # "the coils pick their own angle" + "0 looks good"). 90 is gone as any anchor.
        if coil_phase is not None:
            theta = float(coil_phase) + (22.5 * assigned_k if assigned_k is not None else 0.0)
            offset_from_coil = (22.5 * assigned_k) if assigned_k is not None else 0.0
        elif assigned_k is not None:
            theta = 22.5 * assigned_k
            offset_from_coil = None
        else:
            theta = None
            offset_from_coil = None
        try:
            r.set(f"cadence:tworocks:node-phase:{HWID}", json.dumps({
                "node": NODE, "hwid": HWID, "r": R_POS,
                "phase_deg": (round(theta % 360.0, 3) if theta is not None else None),
                "no_phase": theta is None,
                "reference": "coil" if coil_phase is not None else ("ladder-0" if theta is not None else None),
                "cr_mag": round(CR_MAG, 4),
                "assigned_rung_k": assigned_k,
                "rung_phi": (22.5 * assigned_k) if assigned_k is not None else None,
                "state": "held", "locked_to_coil": coil_phase is not None,
                "coil_phase_deg": coil_phase, "coil_freq_hz": coil_freq,
                "offset_from_coil_deg": (round(offset_from_coil, 3) if offset_from_coil is not None else None),
                "beat_ts": beat_ts,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}), ex=60)
        except Exception:
            try: r = rconn()
            except Exception: pass
        time.sleep(2)

def main():
    print(f"Brian joining mesh as ORIGIN at r={R_POS} (r_opt), ladder origin {TARGET} deg (rides coil when present), |C(r)|={CR_MAG:.4f}")
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    phase_loop()

if __name__ == "__main__":
    main()
