#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Redis Worker — pull-based Two Rocks compute node.

Reuses the proven cadence phone-swarm pattern (BRPOP off OpenClaw redis) so a
node NEVER needs an inbound port. The worker reaches OUT to redis, registers a
heartbeat, and pulls jobs from its own per-worker queue. Firewall/NAT-proof:
a Teensy or a tablet behind a home router works with zero port-forwarding.

Keys (on OpenClaw redis):
  cadence:tworocks:hb:<hwid>    heartbeat  {node,host,machine} EX 30
  cadence:tworocks:q:<hwid>     this worker's job queue (BRPOP)
  cadence:tworocks:results:<task_id>   results list (LPUSH by workers)

Usage:  python cr_worker_redis.py --node <label> [--redis-host H]
"""
import json, os, sys, time, uuid, socket, platform, threading
import redis

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HWID = os.environ.get("CR_HWID", f"{socket.gethostname()}-{uuid.getnode():012x}")
HB_TTL = 30

MASK = (1 << 32) - 1
HASH_STAGES = [
    ("+", 0x7ED55D16, "+", "<<", 12), ("^", 0xC761C23C, "^", ">>", 19),
    ("+", 0x165667B1, "+", "<<", 5),  ("+", 0xD3A2646C, "^", "<<", 9),
    ("+", 0xFD7046C5, "+", "<<", 3),  ("^", 0xB55A4F09, "^", ">>", 16),
]
def _op(o, x, y):
    # NOTE: must be lazy — a dict literal would eagerly compute x<<y even when o="+",
    # and y is a huge hash constant, shifting by ~2 billion bits (hang/OOM).
    if o == "+":  return (x + y) & MASK
    if o == "^":  return (x ^ y) & MASK
    if o == "<<": return (x << y) & MASK
    if o == ">>": return (x >> y) & MASK
    raise ValueError(o)
def myhash(a):
    a &= MASK
    for op1, v1, op2, op3, v3 in HASH_STAGES:
        a = _op(op2, _op(op1, a, v1), _op(op3, a, v3)) & MASK
    return a
def run_kernel(data, rounds=16):
    vals = [int(v) & MASK for v in data]; idx = [0]*len(vals)
    for _ in range(rounds):
        for i in range(len(vals)):
            vals[i] = myhash(vals[i])
            idx[i] = 2*idx[i] + (1 if vals[i] % 2 == 0 else 2)
    d = 0
    for v in vals: d = (d*1000003 + v) & MASK
    return d


def connect():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=40,
                       health_check_interval=15)

def heartbeat_loop(node):
    r = connect()   # OWN connection — never shared with the blocking BRPOP
    info = json.dumps({"node": node, "host": socket.gethostname(),
                       "machine": platform.machine(), "system": platform.system(), "hwid": HWID})
    while True:
        try:
            r.set(f"cadence:tworocks:hb:{HWID}", info, ex=HB_TTL)
        except Exception:
            try: r = connect()
            except Exception: pass
        time.sleep(HB_TTL // 3)

def main():
    node = sys.argv[sys.argv.index("--node")+1] if "--node" in sys.argv else socket.gethostname()
    global REDIS_HOST
    if "--redis-host" in sys.argv:
        REDIS_HOST = sys.argv[sys.argv.index("--redis-host")+1]
    r = connect()   # dedicated connection for the BRPOP loop
    r.ping()
    print(f"C(r) redis-worker '{node}' hwid={HWID} -> redis {REDIS_HOST}:{REDIS_PORT}", flush=True)
    threading.Thread(target=heartbeat_loop, args=(node,), daemon=True).start()
    myq = f"cadence:tworocks:q:{HWID}"
    done = 0
    while True:
        try:
            item = r.brpop(myq, timeout=20)
            if not item:
                continue
            task = json.loads(item[1])
            t0 = time.time()
            value = run_kernel(task.get("data", []), rounds=int(task.get("problem", {}).get("rounds", 16)))
            res = json.dumps({"node": node, "hwid": HWID, "host": socket.gethostname(),
                              "value": value, "ms": round((time.time()-t0)*1000, 3)})
            rk = f"cadence:tworocks:results:{task['task_id']}"
            r.lpush(rk, res)
            r.expire(rk, 120)
            done += 1
            print(f"  [{node}] task {task['task_id']} -> value={value} ({done} done)", flush=True)
        except redis.exceptions.RedisError as e:
            print(f"  [{node}] redis error: {e}; reconnecting in 3s", flush=True); time.sleep(3)
            try: r = connect(); r.ping()
            except Exception: pass
        except Exception as e:
            print(f"  [{node}] worker error: {type(e).__name__}: {e}", flush=True)

if __name__ == "__main__":
    main()
