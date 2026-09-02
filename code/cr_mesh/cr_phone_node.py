#!/usr/bin/env python3
"""
PHONE NODE — an EPHEMERAL mesh member for Termux on Android.

Self-contained: needs only Python + `pip install redis`. No cloning the code
tree. Run it to JOIN the mesh from the phone; Ctrl-C to LEAVE. Node-resilience
in the mesh means it need not persist — its heartbeat TTL expires on exit and
the quorum adapts. Come and go freely.

It is a REAL voter both ways:
  - governor tree-hash: answers its own queue with the kernel replicated
    bit-for-bit below, so its value matches every node -> unanimity preserved.
  - own-source sortition: those same self-measured timings are the phone's OWN
    physical entropy (ARM silicon, different clock/thermal than any x86 node) —
    a genuinely independent source, mobile and sensor-rich.

Phase: rides the live coil beat when present, else holds its canon anchor
arg C(r) (pi*r/5 form, ratified 2026-09-02). r comes from the single-source
registry; falls back to PHONE_R below if the registry is unreachable.

Usage (Termux):
    pkg install python
    pip install redis
    python cr_phone_node.py            # r from registry
    python cr_phone_node.py --r 3      # override
"""
import os, sys, json, time, math, cmath, socket, threading, hashlib

try:
    import redis
except ImportError:
    print("need: pip install redis"); sys.exit(1)

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")   # tailscale IP
REDIS_PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HB_TTL = 30
NODE = "phone"
HWID = "phone-" + hashlib.sha1(socket.gethostname().encode()).hexdigest()[:12]
PHONE_R = 3   # registry fallback if cadence:tworocks:r-map unreachable

# ---- canon C(r): (1+2r) e^(-r/3) e^(i*pi*r/5), phi(r_opt=2.5)=pi/2 (2026-09-02)
def C(r):        return (1 + 2*r) * math.exp(-r/3) * cmath.exp(1j * math.pi * r / 5)
def Cmag(r):     return abs(C(r))
def Cphase(r):   return math.degrees(cmath.phase(C(r)))

# ---- vote kernel — REPLICATED BIT-FOR-BIT from cr_worker_redis (do not alter)
MASK = (1 << 32) - 1
HASH_STAGES = [
    ("+", 0x7ED55D16, "+", "<<", 12), ("^", 0xC761C23C, "^", ">>", 19),
    ("+", 0x165667B1, "+", "<<", 5),  ("+", 0xD3A2646C, "^", "<<", 9),
    ("+", 0xFD7046C5, "+", "<<", 3),  ("^", 0xB55A4F09, "^", ">>", 16),
]
def _op(o, x, y):
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

def rconn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=40,
                       health_check_interval=15)

def resolve_r():
    try:
        m = json.loads(rconn().get("cadence:tworocks:r-map") or "{}").get("map", {})
        if HWID in m: return m[HWID]
    except Exception: pass
    return PHONE_R

R_POS = float(sys.argv[sys.argv.index("--r")+1]) if "--r" in sys.argv else resolve_r()
TARGET = Cphase(R_POS)
_stop = threading.Event()

def heartbeat_loop():
    r = rconn()
    info = json.dumps({"node": NODE, "host": socket.gethostname(), "machine": "android",
                       "system": "termux", "hwid": HWID, "r": R_POS, "ephemeral": True})
    while not _stop.is_set():
        try: r.set(f"cadence:tworocks:hb:{HWID}", info, ex=HB_TTL)
        except Exception:
            try: r = rconn()
            except Exception: pass
        _stop.wait(HB_TTL // 3)

def phase_loop():
    r = rconn()
    while not _stop.is_set():
        theta, locked = TARGET, False
        try:
            b = r.get("cadence:tworocks:t-state")
            if b:
                cp = json.loads(b).get("phase_deg")
                if cp is not None: theta, locked = float(cp), True
        except Exception:
            try: r = rconn()
            except Exception: pass
        st = {"node": NODE, "hwid": HWID, "r": R_POS, "phase_deg": round(theta, 3),
              "target_deg": round(TARGET, 3), "cr_mag": round(Cmag(R_POS), 4),
              "locked_to_coil": locked, "ephemeral": True,
              "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try: r.set(f"cadence:tworocks:node-phase:{HWID}", json.dumps(st), ex=60)
        except Exception: pass
        _stop.wait(2)

def vote_loop():
    r = rconn(); r.ping(); done = 0
    myq = f"cadence:tworocks:q:{HWID}"
    while not _stop.is_set():
        try:
            item = r.brpop(myq, timeout=5)
            if not item: continue
            task = json.loads(item[1]); t0 = time.time()
            val = run_kernel(task.get("data", []), rounds=int(task.get("problem", {}).get("rounds", 16)))
            rk = f"cadence:tworocks:results:{task['task_id']}"
            r.lpush(rk, json.dumps({"node": NODE, "hwid": HWID, "host": socket.gethostname(),
                                    "value": val, "ms": round((time.time()-t0)*1000, 3)}))
            r.expire(rk, 120); done += 1
            print(f"  voted {val} (task {task['task_id']}, {done} done)", flush=True)
        except Exception as e:
            print(f"  reconnect ({type(e).__name__})", flush=True); time.sleep(3)
            try: r = rconn(); r.ping()
            except Exception: pass

def main():
    print(f"phone joining mesh: hwid={HWID}  r={R_POS}  anchor={TARGET:.1f} deg  |C(r)|={Cmag(R_POS):.3f}")
    print("  ephemeral member — Ctrl-C to leave (heartbeat expires, quorum adapts).")
    for fn in (heartbeat_loop, phase_loop, vote_loop):
        threading.Thread(target=fn, daemon=True).start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\nleaving mesh — dropping heartbeat.")
        _stop.set()
        try: rconn().delete(f"cadence:tworocks:hb:{HWID}", f"cadence:tworocks:node-phase:{HWID}")
        except Exception: pass
        time.sleep(0.5)

if __name__ == "__main__":
    main()
