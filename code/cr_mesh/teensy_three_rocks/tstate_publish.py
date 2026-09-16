"""THE TEST'S BEAT -> THE MESH. Publishes the three-rocks rig's live phase to
cadence:tworocks:t-state so every mesh member RIDES the test (Brian 2026-09-16:
"activate the mesh nodes, they can ride with the test").

Opens NO port. The bench script that owns COM8 calls this from its read loop;
the mesh follows the beat and never reaches for the rig (cadence:bench:claim).

Wiring inside a three_rocks sweep (one line in the T3 read loop):

    from tstate_publish import publish_t3
    ...
    line = s.readline().decode(errors="replace").strip()
    publish_t3(line, lead=DRIVEN)          # lead = the driven coil's channel

or, from already-parsed values:  publish(freq_hz, phase_deg, mag, lead=K, phases=[..], mags=[..])

Riders read phase_deg / freq_hz / ts (cr_bridge_cadence, cr_bridge_brian,
cr_ladder_shepherd). target_deg defaults to the canonical coil target pi/2.
Throttled to one write per 0.5 s; a redis hiccup never touches the sweep.
"""
import json, time, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))   # code/cr_mesh
from cr_rmap import _conn as _mesh_conn

KEY = "cadence:tworocks:t-state"
TARGET_DEG = 90.0          # canonical coil target pi/2 (egt_canonical_anchor)
MIN_INTERVAL_S = 0.5
_last = {"t": 0.0, "r": None}

def _angdiff(a, b):
    return ((a - b + 180.0) % 360.0) - 180.0

def build(freq_hz, phase_deg, mag, lead=None, phases=None, mags=None, source="three-rocks COM8", target_deg=TARGET_DEG):
    return {"freq_hz": float(freq_hz), "phase_deg": round(float(phase_deg) % 360.0, 3),
            "target_deg": float(target_deg), "delta_deg": round(_angdiff(float(phase_deg), float(target_deg)), 3),
            "mag": float(mag), "lead": lead,
            "phases": [round(float(p), 2) for p in (phases or [])], "mags": [round(float(m), 4) for m in (mags or [])],
            "source": source, "servo": False,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

def publish(freq_hz, phase_deg, mag, dry_run=False, **kw):
    """Write the beat. Returns the payload, or None when throttled / redis unreachable."""
    now = time.time()
    if now - _last["t"] < MIN_INTERVAL_S:
        return None
    payload = build(freq_hz, phase_deg, mag, **kw)
    if dry_run:
        _last["t"] = now
        return payload
    try:
        if _last["r"] is None:
            _last["r"] = _mesh_conn()
        _last["r"].set(KEY, json.dumps(payload), ex=120)
        _last["t"] = now
        return payload
    except Exception:
        _last["r"] = None      # reconnect next time; the sweep keeps going
        return None

def parse_t3(line):
    """'T3 <freq> ph0 ph1 ph2 mg0 mg1 mg2 ...' -> (freq, [ph0,ph1,ph2], [mg0,mg1,mg2]) or None."""
    p = line.split()
    if len(p) < 8 or p[0] != "T3":
        return None
    try:
        return float(p[1]), [float(x) for x in p[2:5]], [float(x) for x in p[5:8]]
    except ValueError:
        return None

def publish_t3(line, lead=0, **kw):
    """One call per serial line; ignores anything that is not a T3 record."""
    rec = parse_t3(line)
    if rec is None:
        return None
    freq, phases, mags = rec
    return publish(freq, phases[lead], mags[lead], lead=lead, phases=phases, mags=mags, **kw)

if __name__ == "__main__":
    demo = "T3 7878 185.2 131.0 72.4 0.033 0.052 0.008"
    print(json.dumps(publish_t3(demo, lead=0, dry_run=True), indent=1))
