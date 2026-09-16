#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Governor — autonomous dispatcher for the Two Rocks mesh.

Runs forever. Every INTERVAL it discovers the live workers (by heartbeat), fans a
job out to all of them, collects results, runs the C(r)-weighted vote, and
publishes mesh health (live nodes, per-node latency, agreement, correction
margin) to both a local status file and redis (cadence:tworocks:status) so any
node — or Brian — can see the mesh working without touching it.

This is the "deliver work to the rest of the nodes" layer: the nodes pull, the
governor feeds. Nodes are persistent (systemd on Linux, supervisor on Windows);
the governor keeps the whole fabric doing real work autonomously.

Usage:  python cr_governor.py [--interval 30] [--n 256]
"""
import json, os, sys, time, pathlib, uuid
import redis
from cr_voter import cr_vote, coupling_magnitude
from cr_router_redis import connect, live_workers, assign_r

HERE = pathlib.Path(__file__).parent
STATUS_FILE = HERE / "cr_mesh_status.json"

def dispatch_once(r, n, redundancy=None):
    workers = live_workers(r)
    if not workers:
        return None
    rmap = assign_r(workers)
    task_id = uuid.uuid4().hex[:12]
    data = [(i * 2654435761) & 0xFFFFFFFF for i in range(n)]
    task = json.dumps({"task_id": task_id, "problem": {"kind": "tree_hash", "rounds": 16}, "data": data})
    rk = f"cadence:tworocks:results:{task_id}"
    r.delete(rk)
    for w in workers:
        r.lpush(f"cadence:tworocks:q:{w['hwid']}", task)
    results, deadline, need = [], time.time() + 25, len(workers)
    while len(results) < need and time.time() < deadline:
        item = r.brpop(rk, timeout=2)
        if item:
            results.append(json.loads(item[1]))
    got = {x["hwid"]: x for x in results}
    votes, node_rows = [], []
    for w in workers:
        x = got.get(w["hwid"])
        rr = rmap.get(w["hwid"], 1)
        node_rows.append({"node": w["node"], "host": w.get("host"), "hwid": w["hwid"],
                          "r": rr, "responded": bool(x),
                          "value": x["value"] if x else None, "ms": x["ms"] if x else None})
        if x:
            votes.append({"node": w["node"], "result": {"value": x["value"]}, "r": rr})
    if not votes:
        return {"nodes": node_rows, "voted": 0}
    final, conf, details = cr_vote(votes)
    agree = len({v["result"]["value"] for v in votes}) == 1
    # correction margin: simulate the strongest non-root node going bad
    margin = None
    if len(votes) >= 3:
        good = votes[0]["result"]["value"]
        inj = [dict(v) for v in votes]; inj[1] = {**inj[1], "result": {"value": good ^ 0xDEAD}}
        _, mc, _ = cr_vote(inj); margin = round(mc, 4)
    return {
        "task_id": task_id, "value": final.get("value"), "unanimous": details["unanimous"],
        "confidence": round(conf, 4), "agreement": agree, "voted": len(votes),
        "distinct_machines": len(votes), "correction_margin": margin, "nodes": node_rows,
    }

def main():
    interval = int(sys.argv[sys.argv.index("--interval")+1]) if "--interval" in sys.argv else 30
    n = int(sys.argv[sys.argv.index("--n")+1]) if "--n" in sys.argv else 256
    r = connect(); r.ping()
    print(f"C(r) governor: interval={interval}s N={n} -> redis {r.connection_pool.connection_kwargs.get('host')}", flush=True)
    started = time.time()
    stats = {"dispatches": 0, "failures": 0}
    while True:
        t0 = time.time()
        try:
            res = dispatch_once(r, n)
            stats["dispatches"] += 1
            if not res or res.get("voted", 0) == 0:
                stats["failures"] += 1
                print(f"  [gov] no live workers / no results", flush=True)
            else:
                status = {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "uptime_s": int(time.time() - started),
                    "interval_s": interval, "n": n,
                    "dispatches": stats["dispatches"], "failures": stats["failures"],
                    **res,
                }
                STATUS_FILE.write_text(json.dumps(status, indent=2))
                try:
                    r.set("cadence:tworocks:status", json.dumps(status), ex=interval * 3)
                except Exception:
                    pass
                mk = res.get("correction_margin")
                print(f"  [gov] {res['distinct_machines']} nodes | value={res['value']} "
                      f"| unanimous={res['unanimous']} | margin={mk} "
                      f"| fastest={min((x['ms'] for x in res['nodes'] if x['ms']), default='?')}ms", flush=True)
        except redis.exceptions.RedisError as e:
            stats["failures"] += 1
            print(f"  [gov] redis error: {e}; reconnect", flush=True)
            try: r = connect(); r.ping()
            except Exception: pass
        except Exception as e:
            stats["failures"] += 1
            print(f"  [gov] error: {type(e).__name__}: {e}", flush=True)
        dt = time.time() - t0
        time.sleep(max(1, interval - dt))

if __name__ == "__main__":
    main()
