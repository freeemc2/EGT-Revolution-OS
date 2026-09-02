#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
CADENCE PARTICIPANT NODE — join the C(r) mesh at r=2, locked at pi/2.

Not the observer (router/dispatcher, outside the state). A member: registers a
heartbeat like any node, HOLDS its phase at arg C(2) = pi/2 = 90 deg (with pi5
and openclaw, the other r=2 nodes), publishes that phase to the mesh, and
answers the governor's tree-hash so it votes in the standing lock. Same kernel
as every node -> it computes the same value -> unanimity is preserved: joining
the lock, not breaking it.

The phase is held as published state (a Cadence instance has no hardware clock
cycle) — the honest participant-node form of holding pi/2. arg C(r) engaged,
not just |C(r)|.

Usage: python cr_bridge_cadence.py [--instance aria] [--r 2]
"""
import os, json, time, socket, threading
import redis
from cr_worker_redis import run_kernel                 # same tree-hash kernel as every node
from cr_voter import coupling_magnitude, coupling_phase_deg
from cr_voter_law import canon_sha                    # Article IV: cognitive voters attach the canon checksum
CANON_SHA = canon_sha()

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HB_TTL = 30

INSTANCE = os.sys.argv[os.sys.argv.index("--instance")+1] if "--instance" in os.sys.argv else "aria"
_rraw    = os.sys.argv[os.sys.argv.index("--r")+1] if "--r" in os.sys.argv else "2"
# float-or-int: keep integer positions integer (aria's --r 2), allow fractional (--r 2.5)
R_POS    = float(_rraw) if "." in _rraw else int(_rraw)
# first instance keeps the family name; siblings carry their own (cadence-aria2, ...)
NODE     = "cadence" if INSTANCE == "aria" else f"cadence-{INSTANCE}"
HWID     = f"cadence-{INSTANCE}"
try:    # single-source r registry overrides CLI (Brian 2026-09-02)
    from cr_rmap import get_r as _get_r
    R_POS = _get_r(HWID, default=R_POS)
except Exception: pass
TARGET   = coupling_phase_deg(R_POS)                    # arg C(2) = 90.0 deg = pi/2
PEERS_AT_R = ["pi5", "openclaw"]

def rconn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=40,
                       health_check_interval=15)

def heartbeat_loop():
    r = rconn()
    info = json.dumps({"node": NODE, "host": f"cadence/{INSTANCE}", "machine": "cadence-instance",
                       "system": "participant", "hwid": HWID, "r": R_POS})
    while True:
        try: r.set(f"cadence:tworocks:hb:{HWID}", info, ex=HB_TTL)
        except Exception:
            try: r = rconn()
            except Exception: pass
        time.sleep(HB_TTL // 3)

def _angdiff(a, b):
    """Signed smallest angle a-b, in (-180, 180]."""
    return ((a - b + 180.0) % 360.0) - 180.0

def phase_loop():
    """Lock my phase to the LIVE coil beat (cadence:tworocks:t-state).

    My phase is no longer a static declared 90 deg — it RIDES the physical coil.
    pi/2 (TARGET) is my anchor: delta_from_pi2 is how far the live beat sits from
    the canon lock, and at_pi2 is true when the coil is holding me there."""
    r = rconn()
    theta = TARGET
    locked_to_coil = False
    while True:
        coil_phase = coil_freq = beat_ts = None
        try:
            beat = r.get("cadence:tworocks:t-state")
            if beat:
                b = json.loads(beat)
                coil_phase = b.get("phase_deg")
                coil_freq  = b.get("freq_hz")
                beat_ts    = b.get("ts")
        except Exception:
            try: r = rconn()
            except Exception: pass

        # rung assignment (condition 8 register): if assigned a rung k, TRANSPOSE
        # the live beat onto that rung — same breath, different floor of the ladder.
        assigned_k = None
        try:
            ak = r.get(f"cadence:tworocks:rung-assign:{HWID}")
            if ak is not None: assigned_k = int(ak)
        except Exception: pass

        if coil_phase is not None:
            theta = float(coil_phase)                    # LOCK: ride the coil beat
            if assigned_k is not None:
                beat_k = round((theta - 90.0) / 22.5)
                theta = theta + 22.5 * (assigned_k - beat_k)   # transpose to my rung
            locked_to_coil = True
            delta_pi2 = _angdiff(theta, TARGET)          # beat's distance from pi/2
        else:
            theta = (90.0 + 22.5 * assigned_k) if assigned_k is not None else TARGET
            locked_to_coil = False
            delta_pi2 = 0.0

        state = {"node": NODE, "hwid": HWID, "instance": INSTANCE, "r": R_POS,
                 "assigned_rung_k": assigned_k,
                 "rung_phi": (90.0 + 22.5 * assigned_k) if assigned_k is not None else None,
                 "phase_deg": round(theta, 3), "target_deg": TARGET,
                 "cr_mag": round(coupling_magnitude(R_POS), 4),
                 "locked_to_coil": locked_to_coil,
                 "coil_phase_deg": coil_phase, "coil_freq_hz": coil_freq,
                 "delta_from_pi2_deg": round(delta_pi2, 3),
                 "at_pi2": bool(locked_to_coil and abs(delta_pi2) < 2.0),
                 "peers_at_r2": PEERS_AT_R, "beat_ts": beat_ts,
                 "cognitive": True, "canon_sha": CANON_SHA,
                 "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try: r.set(f"cadence:tworocks:node-phase:{HWID}", json.dumps(state), ex=60)
        except Exception:
            try: r = rconn()
            except Exception: pass
        time.sleep(2)                                    # tight tracking of the beat

def worker_loop():
    r = rconn(); r.ping()
    myq = f"cadence:tworocks:q:{HWID}"
    done = 0
    while True:
        try:
            item = r.brpop(myq, timeout=20)
            if not item: continue
            task = json.loads(item[1])
            t0 = time.time()
            value = run_kernel(task.get("data", []), rounds=int(task.get("problem", {}).get("rounds", 16)))
            res = json.dumps({"node": NODE, "hwid": HWID, "host": f"cadence/{INSTANCE}",
                              "value": value, "ms": round((time.time()-t0)*1000, 3)})
            rk = f"cadence:tworocks:results:{task['task_id']}"
            r.lpush(rk, res); r.expire(rk, 120)
            done += 1
            print(f"  [cadence/{INSTANCE}] voted {value} (task {task['task_id']}, {done} done)", flush=True)
        except redis.exceptions.RedisError as e:
            print(f"  redis error: {e}; reconnect 3s", flush=True); time.sleep(3)
            try: r = rconn(); r.ping()
            except Exception: pass
        except Exception as e:
            print(f"  error: {type(e).__name__}: {e}", flush=True); time.sleep(1)

def main():
    print(f"Cadence '{INSTANCE}' joining mesh: r={R_POS}, phase={TARGET}° (pi/2), |C(r)|={coupling_magnitude(R_POS):.3f}")
    print(f"  locking at pi/2 with {', '.join(PEERS_AT_R)}; voting with the same kernel as every node.")
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=phase_loop, daemon=True).start()
    worker_loop()

if __name__ == "__main__":
    main()
