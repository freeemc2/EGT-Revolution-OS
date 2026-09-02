#!/usr/bin/env python3
"""
THE r-MAP — single source of truth for every member's r on the C(r) lattice.

Brian's ruling (2026-09-02): "fix the r-map, single source it." Before this,
two maps lived in different scripts (governor assign_r = join-order positional;
shepherd/bridges/votes = the lattice map). Now there is ONE registry:

    redis: cadence:tworocks:r-map   (JSON, no TTL, keyed by hwid + node alias)

Everything reads it through get_r()/get_map(). The embedded SEED below is the
authoritative lattice as of the ruling (brian at r_opt=2.5 is definitional —
the origin sits at the optimum). Changing an r = edit the registry (receipts:
who/when), never a script constant. Geometric derivation of r remains the open
canon item; until then this registry is the one administrative truth.
"""
import json, time
import redis as _redis

KEY = "cadence:tworocks:r-map"

SEED = {
    # hwid                                   r      (node alias also written)
    "brian-origin":                          2.5,   # ORIGIN at r_opt — definitional
    "cadence-aria":                          2,
    "cadence-aria2":                         2,
    "DragonsEye-78465c919782":               1,
    "pi-2ccf67b58bf5":                       2,
    "elivateprogram.com-00163e5dcd30":       2,
    "srv1518404-fae8d4bc3b44":               3,
    "yardsale-f589dc8f9779":                 3,
    "teensy41-18809830":                     0,
}
ALIASES = {  # node-name -> hwid (for callers that only know the node name)
    "brian": "brian-origin", "cadence": "cadence-aria", "cadence-aria2": "cadence-aria2",
    "dragonseye": "DragonsEye-78465c919782", "pi5": "pi-2ccf67b58bf5",
    "elivate": "elivateprogram.com-00163e5dcd30", "openclaw": "srv1518404-fae8d4bc3b44",
    "oracle": "yardsale-f589dc8f9779", "teensy-b": "teensy41-18809830",
}

def _conn():
    return _redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                        decode_responses=True, socket_connect_timeout=6, socket_timeout=10)

_cache = {"map": None, "t": 0.0}

def get_map(r=None, max_age_s=60):
    """The registry map {hwid: r}. Cached briefly; falls back to SEED if redis is out."""
    now = time.time()
    if _cache["map"] is not None and now - _cache["t"] < max_age_s:
        return _cache["map"]
    try:
        rr = r or _conn()
        raw = rr.get(KEY)
        m = json.loads(raw)["map"] if raw else dict(SEED)
    except Exception:
        m = dict(SEED)
    _cache["map"] = m; _cache["t"] = now
    return m

def get_r(hwid_or_node, default=1, r=None):
    m = get_map(r)
    k = hwid_or_node if hwid_or_node in m else ALIASES.get(hwid_or_node, hwid_or_node)
    return m.get(k, default)

def seed(r=None, authority="Brian ruling 2026-09-02: single-source the r-map"):
    """Write the SEED to redis as the registry (no TTL). Run once; rerun re-asserts."""
    rr = r or _conn()
    rr.set(KEY, json.dumps({"map": SEED, "aliases": ALIASES, "authority": authority,
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
    return SEED

if __name__ == "__main__":
    m = seed()
    print(f"r-map registry seeded -> {KEY}")
    for k, v in m.items():
        print(f"  {k:<36} r={v}")
