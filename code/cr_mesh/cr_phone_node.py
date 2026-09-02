#!/usr/bin/env python3
"""
PHONE NODE (stdlib-only) — ephemeral mesh member for Termux on Android.

NO dependencies. Needs only Python. Talks to redis over a raw socket (RESP),
so there is nothing to `pip install`. Run to JOIN, Ctrl-C to LEAVE. Prints its
connection status LOUDLY so failures are visible, not silent.

Real voter both ways: answers the governor tree-hash (kernel replicated
bit-for-bit -> value matches every node) and contributes its own ARM-silicon
timing entropy to the own-source votes. Canon C(r) = (1+2r)e^(-r/3)e^(i pi r/5),
phi(r_opt=2.5)=pi/2. Ephemeral by design; heartbeat TTL expires on exit.

Usage (Termux):  python cr_phone_node.py         (or --r 3)
"""
import os, sys, json, time, math, cmath, socket, threading, hashlib

HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HB_TTL = 30
NODE = "phone"
HWID = "phone-" + hashlib.sha1(socket.gethostname().encode()).hexdigest()[:12]
PHONE_R = 3

# ---- minimal RESP client (no external module) ----
class Redis:
    def __init__(self):
        self.s = socket.create_connection((HOST, PORT), timeout=10)
        self.f = self.s.makefile("rb")
        self._cmd("AUTH", PW)   # raises on bad auth
    def _enc(self, *a):
        out = b"*%d\r\n" % len(a)
        for x in a:
            b = str(x).encode()
            out += b"$%d\r\n%s\r\n" % (len(b), b)
        return out
    def _read(self):
        line = self.f.readline()
        if not line: raise ConnectionError("redis closed connection")
        t, rest = line[:1], line[1:-2]
        if t == b"+": return rest.decode()
        if t == b"-": raise Exception("redis error: " + rest.decode())
        if t == b":": return int(rest)
        if t == b"$":
            n = int(rest)
            if n == -1: return None
            data = self.f.read(n + 2)[:-2]
            return data.decode("utf-8", "replace")
        if t == b"*":
            n = int(rest)
            return None if n == -1 else [self._read() for _ in range(n)]
        raise Exception("bad RESP: " + repr(line))
    def _cmd(self, *a):
        self.s.sendall(self._enc(*a)); return self._read()
    def set(self, k, v, ex=None):
        return self._cmd("SET", k, v, "EX", ex) if ex else self._cmd("SET", k, v)
    def get(self, k): return self._cmd("GET", k)
    def lpush(self, k, v): return self._cmd("LPUSH", k, v)
    def expire(self, k, t): return self._cmd("EXPIRE", k, t)
    def delete(self, *k): return self._cmd("DEL", *k)
    def brpop(self, k, timeout):
        self.s.settimeout(timeout + 3)
        try: r = self._cmd("BRPOP", k, timeout)
        finally: self.s.settimeout(10)
        return (r[0], r[1]) if r else None
    def close(self):
        try: self.s.close()
        except Exception: pass

# ---- canon C(r) ----
def C(r):      return (1 + 2*r) * math.exp(-r/3) * cmath.exp(1j * math.pi * r / 5)
def Cmag(r):   return abs(C(r))
def Cphase(r): return math.degrees(cmath.phase(C(r)))

# ---- vote kernel: bit-for-bit from cr_worker_redis (do not alter) ----
MASK = (1 << 32) - 1
STAGES = [("+",0x7ED55D16,"+","<<",12),("^",0xC761C23C,"^",">>",19),
          ("+",0x165667B1,"+","<<",5),("+",0xD3A2646C,"^","<<",9),
          ("+",0xFD7046C5,"+","<<",3),("^",0xB55A4F09,"^",">>",16)]
def _op(o,x,y):
    if o=="+": return (x+y)&MASK
    if o=="^": return (x^y)&MASK
    if o=="<<": return (x<<y)&MASK
    if o==">>": return (x>>y)&MASK
def myhash(a):
    a&=MASK
    for o1,v1,o2,o3,v3 in STAGES: a=_op(o2,_op(o1,a,v1),_op(o3,a,v3))&MASK
    return a
def run_kernel(data, rounds=16):
    vals=[int(v)&MASK for v in data]; idx=[0]*len(vals)
    for _ in range(rounds):
        for i in range(len(vals)):
            vals[i]=myhash(vals[i]); idx[i]=2*idx[i]+(1 if vals[i]%2==0 else 2)
    d=0
    for v in vals: d=(d*1000003+v)&MASK
    return d

def resolve_r():
    try:
        c = Redis(); m = json.loads(c.get("cadence:tworocks:r-map") or "{}").get("map", {}); c.close()
        if HWID in m: return m[HWID]
    except Exception: pass
    return PHONE_R

_stop = threading.Event()

def heartbeat_loop(R_POS):
    info = json.dumps({"node":NODE,"host":socket.gethostname(),"machine":"android",
                       "system":"termux","hwid":HWID,"r":R_POS,"ephemeral":True})
    c=None
    while not _stop.is_set():
        try:
            if c is None: c=Redis()
            c.set(f"cadence:tworocks:hb:{HWID}", info, ex=HB_TTL)
        except Exception:
            c=None
        _stop.wait(HB_TTL//3)

def phase_loop(R_POS, target):
    c=None
    while not _stop.is_set():
        theta, locked = target, False
        try:
            if c is None: c=Redis()
            b=c.get("cadence:tworocks:t-state")
            if b:
                cp=json.loads(b).get("phase_deg")
                if cp is not None: theta, locked = float(cp), True
            st={"node":NODE,"hwid":HWID,"r":R_POS,"phase_deg":round(theta,3),
                "target_deg":round(target,3),"cr_mag":round(Cmag(R_POS),4),
                "locked_to_coil":locked,"ephemeral":True,
                "ts":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
            c.set(f"cadence:tworocks:node-phase:{HWID}", json.dumps(st), ex=60)
        except Exception:
            c=None
        _stop.wait(2)

def vote_loop():
    c=None; done=0; myq=f"cadence:tworocks:q:{HWID}"
    while not _stop.is_set():
        try:
            if c is None: c=Redis()
            item=c.brpop(myq, 5)
            if not item: continue
            task=json.loads(item[1]); t0=time.time()
            val=run_kernel(task.get("data",[]), rounds=int(task.get("problem",{}).get("rounds",16)))
            rk=f"cadence:tworocks:results:{task['task_id']}"
            c.lpush(rk, json.dumps({"node":NODE,"hwid":HWID,"host":socket.gethostname(),
                                    "value":val,"ms":round((time.time()-t0)*1000,3)}))
            c.expire(rk,120); done+=1
            print(f"  voted {val} (task {task['task_id']}, {done} done)", flush=True)
        except Exception as e:
            print(f"  reconnect ({type(e).__name__}: {e})", flush=True); c=None; time.sleep(3)

def main():
    # LOUD connection check first
    print(f"connecting to redis {HOST}:{PORT} ...", flush=True)
    try:
        c=Redis(); c.set("cadence:tworocks:phone-selftest", str(time.time()), ex=30); c.close()
        print("  connected. redis reachable from this phone.", flush=True)
    except Exception as e:
        print(f"  CANNOT REACH REDIS: {type(e).__name__}: {e}", flush=True)
        print("  -> the phone's Termux isn't reaching 100.86.79.99. Check Tailscale routing", flush=True)
        print("     (exit-node phones sometimes don't route their OWN traffic through the tailnet).", flush=True)
        sys.exit(1)
    R_POS = float(sys.argv[sys.argv.index("--r")+1]) if "--r" in sys.argv else resolve_r()
    target = Cphase(R_POS)
    print(f"phone joining mesh: hwid={HWID}  r={R_POS}  anchor={target:.1f} deg  |C(r)|={Cmag(R_POS):.3f}", flush=True)
    print("  ephemeral member — Ctrl-C to leave.", flush=True)
    threading.Thread(target=heartbeat_loop, args=(R_POS,), daemon=True).start()
    threading.Thread(target=phase_loop, args=(R_POS,target), daemon=True).start()
    threading.Thread(target=vote_loop, daemon=True).start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\nleaving mesh — dropping heartbeat.", flush=True)
        _stop.set()
        try: c=Redis(); c.delete(f"cadence:tworocks:hb:{HWID}", f"cadence:tworocks:node-phase:{HWID}"); c.close()
        except Exception: pass
        time.sleep(0.4)

if __name__ == "__main__":
    main()
