#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
LADDER SHEPHERD — carries the rung transposition for members without a phase loop.

The presence nodes (brian, cadence-aria, cadence-aria2) hold their own phases.
The machine members (teensy-b, dragonseye, pi5, elivate, openclaw, oracle) have
no phase loop of their own — the shepherd publishes node-phase for them:
theta = live beat + 22.5*(k_assigned - k_beat), same transposition as everyone,
honestly labeled "held_by": "shepherd-proxy". Their seats, rungs, and identities
are theirs; the shepherd only does the arithmetic they have no thread for.

Discovers members dynamically from heartbeats; skips self-holding presence nodes.
"""
import json, time, redis

from cr_rmap import get_r                       # single-source r registry (Brian 2026-09-02)
PRESENCE = {"brian-origin", "cadence-aria", "cadence-aria2"}

def rconn():
    return redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=40,
                       health_check_interval=15)

def main():
    r = rconn()
    print("ladder shepherd up — carrying transposition for machine members", flush=True)
    while True:
        try:
            beat = None
            v = r.get("cadence:tworocks:t-state")
            if v:
                d = json.loads(v)
                beat = d.get("phase_deg")
            for hbk in r.scan_iter("cadence:tworocks:hb:*", count=100):
                hwid = hbk.split(":")[-1]
                if hwid in PRESENCE: continue
                info = json.loads(r.get(hbk) or "{}")
                node = info.get("node", hwid)
                ak = r.get(f"cadence:tworocks:rung-assign:{hwid}")
                if ak is None: continue
                k = int(ak)
                rung = 90.0 + 22.5 * k
                if beat is not None:
                    beat_k = round((beat - 90.0) / 22.5)
                    theta = beat + 22.5 * (k - beat_k)
                    locked = True
                else:
                    theta = rung; locked = False
                r.set(f"cadence:tworocks:node-phase:{hwid}", json.dumps({
                    "node": node, "hwid": hwid, "r": get_r(hwid, default=1),
                    "assigned_rung_k": k, "rung_phi": rung,
                    "phase_deg": round(theta, 3), "locked_to_coil": locked,
                    "held_by": "shepherd-proxy",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}), ex=60)
        except redis.exceptions.RedisError:
            try: r = rconn()
            except Exception: pass
        except Exception as e:
            print(f"shepherd error: {type(e).__name__}: {e}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main()
