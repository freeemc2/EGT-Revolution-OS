#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
MEMORY AUDITOR — canon core verified at governor cadence.

Memory in the LOOP, not in the judgment. Every 30 s this verifies the immutable
canon core three ways and publishes a standing verdict any instance can read
instead of trusting its own read of the record:

  1. on-disk sha256  vs  CANON_MANIFEST.md table
  2. on-disk sha256  vs  redis seal `cadence:canon:manifest`
  3. LEDGER_COILS_READONLY.md still carries +R (append-only guard intact)

Mismatch -> loud FAIL in the key + supervisor log. The key carries a TTL of 3
audit cycles, so a DEAD auditor expires its verdict rather than leaving a stale
"ok" standing. Absence of the key means "not audited", never "audited fine".

CANON_MANIFEST.md cannot appear in its own table, so it is verified against the
redis seal alone (the seal carries its hash).

Built 2026-09-01 on Brian's direct order after the 2026-08-31 journal entry was
found to record this file as built when it did not exist. Adoption is subject to
a mesh vote per the 2026-08-31 leash — a verdict here is not a claim of fixed.

Usage: python cr_memory_audit.py [--interval 30]
"""
import os, re, json, time, hashlib, pathlib, stat

import redis

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")

MEM_DIR   = pathlib.Path(os.environ.get(
    "CR_MEM_DIR", r"C:\Users\affor\.claude\projects\C--\memory"))
MANIFEST  = MEM_DIR / "CANON_MANIFEST.md"
LEDGER    = MEM_DIR / "LEDGER_COILS_READONLY.md"
SEAL_KEY  = "cadence:canon:manifest"
OUT_KEY   = "cadence:memory:audit"

INTERVAL = int(_sys.argv[_sys.argv.index("--interval") + 1]) if "--interval" in _sys.argv else 30
TTL      = INTERVAL * 3          # dead auditor -> verdict expires, never goes stale-ok

ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", re.M)


def rconn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                       decode_responses=True, socket_timeout=10)


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_manifest(text):
    """file -> sha256 from the manifest's markdown table."""
    return {m.group(1): m.group(2) for m in ROW.finditer(text)}


def audit(r):
    files, fails = {}, []

    if not MANIFEST.exists():
        return {"ok": False, "files": {}, "fails": ["CANON_MANIFEST.md MISSING"]}
    table = parse_manifest(MANIFEST.read_text(encoding="utf-8"))

    try:
        seal = json.loads(r.get(SEAL_KEY) or "{}")
    except Exception as e:
        seal = {}
        fails.append(f"redis seal unreadable: {e}")
    if not seal:
        fails.append(f"redis seal {SEAL_KEY} MISSING or empty")

    # the manifest itself: sealed but not self-listed
    checked = set(table) | {"CANON_MANIFEST.md"}
    for name in sorted(checked):
        p = MEM_DIR / name
        d = {"manifest": table.get(name), "seal": seal.get(name)}
        if not p.exists():
            d["actual"] = None
            d["ok"] = False
            fails.append(f"{name} MISSING ON DISK")
        else:
            actual = sha256(p)
            d["actual"] = actual
            bad = []
            if d["manifest"] and actual != d["manifest"]:
                bad.append("manifest")
            if d["seal"] and actual != d["seal"]:
                bad.append("seal")
            if name in table and not d["seal"]:
                bad.append("absent-from-seal")
            d["ok"] = not bad
            if bad:
                fails.append(f"{name} SHA MISMATCH vs {'+'.join(bad)}")
        files[name] = d

    # ledger append-only guard
    if not LEDGER.exists():
        ledger_ro = None
        fails.append("LEDGER_COILS_READONLY.md MISSING")
    else:
        ledger_ro = not bool(os.stat(LEDGER).st_mode & stat.S_IWRITE)
        if not ledger_ro:
            fails.append("LEDGER_COILS_READONLY.md LOST +R (append-only guard down)")

    return {"ok": not fails, "files": files, "fails": fails,
            "ledger_readonly": ledger_ro,
            "seal_tag": seal.get("tag"), "seal_ratified": seal.get("ratified")}


def main():
    print(f"memory auditor starting — every {INTERVAL}s, key {OUT_KEY} (ttl {TTL}s)", flush=True)
    r = None
    last_ok = None
    while True:
        try:
            if r is None:
                r = rconn(); r.ping()
            v = audit(r)
            v["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            v["interval_s"] = INTERVAL
            v["auditor"] = "cr_memory_audit"
            r.set(OUT_KEY, json.dumps(v), ex=TTL)

            if not v["ok"]:
                print(f"*** CANON AUDIT FAIL {v['ts']}: {'; '.join(v['fails'])}", flush=True)
            elif last_ok is not True:
                print(f"canon audit OK {v['ts']} (tag {v.get('seal_tag')})", flush=True)
            last_ok = v["ok"]
        except Exception as e:
            print(f"auditor error: {e}", flush=True)
            r = None
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
