#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Redis Router — pull-based dispatch + C(r)-weighted vote over redis.

Discovers live workers from their heartbeats, fans a task out to each worker's
own queue, collects results, dedups by hwid (one physical box = one vote), and
reconciles with the C(r)-weighted vote. No inbound ports anywhere.

Usage:
  python cr_router_redis.py --list                 # show live workers
  python cr_router_redis.py --dispatch [--n 256] [--redundancy K] [--fault]
"""
import json, os, sys, time, uuid, math, cmath
import redis
from cr_voter import cr_vote

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")

def connect():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=15)

def live_workers(r):
    """Return [{hwid,node,host,machine}] from heartbeat keys."""
    out = []
    for k in r.scan_iter(match="cadence:tworocks:hb:*", count=200):
        v = r.get(k)
        if v:
            try: out.append(json.loads(v))
            except Exception: pass
    # dedup by hwid (belt-and-suspenders; keys are already per-hwid)
    seen = {}
    for w in out:
        seen.setdefault(w.get("hwid", w.get("host")), w)
    return list(seen.values())

def assign_r(workers):
    """r from the SINGLE-SOURCE registry (cadence:tworocks:r-map) — Brian ruling
    2026-09-02. The old join-order positional assignment is retired; a worker
    absent from the registry gets r=1 (flag it and add it to the registry)."""
    from cr_rmap import get_r
    return {w["hwid"]: get_r(w["hwid"], default=1) for w in workers}

def dispatch(r, n=256, redundancy=None, fault=False):
    workers = live_workers(r)
    if not workers:
        print("  no live workers (no heartbeats). Start cr_worker_redis.py on nodes."); return 1
    rmap = assign_r(workers)
    if redundancy:
        workers = workers[:redundancy]
    task_id = uuid.uuid4().hex[:12]
    data = [(i * 2654435761) & 0xFFFFFFFF for i in range(n)]
    task = json.dumps({"task_id": task_id, "problem": {"kind": "tree_hash", "rounds": 16}, "data": data})

    print(f"  dispatching task {task_id} (N={n}) to {len(workers)} live workers via redis...")
    rk = f"cadence:tworocks:results:{task_id}"
    r.delete(rk)
    for w in workers:
        r.lpush(f"cadence:tworocks:q:{w['hwid']}", task)

    # collect
    results, deadline = [], time.time() + 30
    need = len(workers)
    while len(results) < need and time.time() < deadline:
        item = r.brpop(rk, timeout=2)
        if item:
            results.append(json.loads(item[1]))
    got = {x["hwid"]: x for x in results}   # dedup by hwid

    votes = []
    for w in workers:
        x = got.get(w["hwid"])
        rr = rmap.get(w["hwid"], 1)
        status = f"value={x['value']} {x['ms']}ms" if x else "NO RESPONSE"
        print(f"    {w['node']:12s} host={w.get('host','?'):18s} r={rr}  {status}")
        if x:
            votes.append({"node": w["node"], "result": {"value": x["value"]}, "r": rr})

    if not votes:
        print("  no results collected."); return 1
    final, conf, details = cr_vote(votes)
    agree = len({v["result"]["value"] for v in votes}) == 1
    print(f"\n  C(r) vote -> {final}  confidence={round(conf,4)}  unanimous={details['unanimous']}")
    print(f"  distinct machines: {len(votes)}  |  cross-arch agreement: {'YES' if agree else 'NO'}")

    if fault and len(votes) >= 3:
        good = votes[0]["result"]["value"]
        inj = [dict(v) for v in votes]; inj[1] = {**inj[1], "result": {"value": good ^ 0xDEAD}}
        f2, c2, d2 = cr_vote(inj)
        print(f"\n  fault injected on '{votes[1]['node']}' -> {f2} conf={round(c2,4)} "
              f"corrected={'YES' if f2=={'value':good} else 'NO'} dissent={[d['voters'] for d in d2['disagreements']]}")
    return 0

def main():
    r = connect(); r.ping()
    if "--list" in sys.argv:
        ws = live_workers(r)
        print(f"live workers ({len(ws)}):")
        for w in ws:
            print(f"  {w.get('node'):12s} host={w.get('host'):18s} {w.get('machine')}  hwid={w.get('hwid')}")
        return
    n = int(sys.argv[sys.argv.index("--n")+1]) if "--n" in sys.argv else 256
    red = int(sys.argv[sys.argv.index("--redundancy")+1]) if "--redundancy" in sys.argv else None
    sys.exit(dispatch(r, n=n, redundancy=red, fault=("--fault" in sys.argv)))

if __name__ == "__main__":
    main()
