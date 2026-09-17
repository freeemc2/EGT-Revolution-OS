"""PING THE LEADER, BOTH FOLLOWERS LISTEN (Brian, 2026-09-17 "go, run it with both followers listening").

A0 is the transfer leg. Drive A0 alone (M1 K0) at 12 Hz, gated ON/OFF, while the sense
pair is (A1, A2) -- both followers read SIMULTANEOUSLY on the two ADC engines (C 1 2).
The all-day protocol showed A1 hears A0 (0.063, rise ~36 s, decay ~12 s) but never had
A2 in the pair while A0 was injected. This run measures A2's hearing and the rise/decay
clock at 1 s packet resolution.

Every raw T3 packet is logged exactly (no averaging): data/ping_followers_<ts>.jsonl
  {"t", "cycle", "gate": "ON"|"OFF", "el": s since gate start, "f", "A1": [mag, ph], "A2": [mag, ph], "dBC"}
The mesh rides the test: t-state published from the follower pair (lead = A1) via tstate_publish.
Robust to serial hangs (logs, reconnects, never crashes). Ctrl-C / kill to stop; the board is
sent 'x' on exit.

Usage: python -u ping_followers.py [--freq 12] [--on 180] [--off 180] [--cycles 10] [--integ 1000]
"""
import serial, serial.tools.list_ports as lp, time, json, os, sys, math, cmath, statistics as st, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    from tstate_publish import publish
except Exception:
    publish = None

def arg(name, default, cast=float):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
FREQ   = arg("--freq", 12.0)
ON_S   = arg("--on", 180.0)
OFF_S  = arg("--off", 180.0)
CYCLES = arg("--cycles", 10, int)
INTEG  = arg("--integ", 1000, int)
LEAD, PAIR = 0, (1, 2)
DATA = pathlib.Path(__file__).resolve().parent / "data"
logpath = DATA / f"ping_followers_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
log = open(logpath, "a", buffering=1)

def find_port():
    return next((p.device for p in lp.comports() if "16C0" in (p.hwid or "")), "COM8")

def send(ss, c, w=0.35):
    ss.write(b"\n"); time.sleep(0.05); ss.reset_input_buffer()
    ss.write((c + "\n").encode()); time.sleep(w)

def opn():
    ss = serial.Serial(find_port(), 115200, timeout=2, write_timeout=6); time.sleep(0.8)
    send(ss, "x", 0.5); send(ss, "P", 0.5)
    pong = ss.readline().decode(errors="replace").strip()
    print(f"port {ss.port} {pong}", flush=True)
    send(ss, f"I {INTEG}", 0.3); send(ss, f"C {PAIR[0]} {PAIR[1]}", 0.3)
    return ss

def gate(ss, on):
    if on:
        send(ss, "M 1"); send(ss, f"K {LEAD}")
    else:
        send(ss, "M 0")
    send(ss, f"L {FREQ:g}", 1.0); ss.reset_input_buffer()

def mesh_marker(state):
    try:
        import redis
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
        from cr_rmap import _conn
        _conn().set("cadence:tworocks:experiment", json.dumps({
            "name": "ping-followers", "by": "tempo (bench)", "start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": f"A0 injected alone at {FREQ:g} Hz, gated {ON_S:.0f}s ON / {OFF_S:.0f}s OFF x{CYCLES}; sense pair (A1,A2) both followers simultaneously; every packet logged; mesh rides t-state from A1. {state}"}), ex=48*3600)
    except Exception:
        pass

def stream(ss, cycle, label, secs):
    """Read every T3 packet for `secs`, log it, publish the beat. Returns per-gate summary."""
    t0 = time.time(); m1 = []; m2 = []; p1 = []; p2 = []; first1 = first2 = None; last1 = last2 = None
    while time.time() - t0 < secs:
        ln = ss.readline().decode(errors="replace").strip().split()
        if not ln or ln[0] != "T3" or len(ln) < 8:
            continue
        f = float(ln[1]); ph = [float(x) for x in ln[2:5]]; mg = [float(x) for x in ln[5:8]]
        dBC = float(ln[10]) if len(ln) > 10 else None
        now = time.time(); el = round(now - t0, 2)
        rec = {"t": round(now, 2), "cycle": cycle, "gate": label, "el": el, "f": f,
               "A1": [mg[1], ph[1]], "A2": [mg[2], ph[2]], "dBC": dBC}
        log.write(json.dumps(rec) + "\n")
        if publish:
            publish(f, ph[1], mg[1], lead=1, phases=ph, mags=mg, source=f"ping-followers {label} c{cycle}")
        m1.append(mg[1]); m2.append(mg[2]); p1.append(ph[1]); p2.append(ph[2])
        if mg[1] > 0.009: last1 = el; first1 = first1 if first1 is not None else el
        if mg[2] > 0.009: last2 = el; first2 = first2 if first2 is not None else el
    def summ(m, p, first, last):
        live = [x for x in m if x > 0.009]
        return {"n": len(m), "live_frac": round(len(live) / len(m), 2) if m else None, "mag_med": round(st.median(live), 4) if live else 0.0,
                "phase_med": round(st.median(p), 1) if p else None, "first_live_s": first, "last_live_s": last}
    return {"A1": summ(m1, p1, first1, last1), "A2": summ(m2, p2, first2, last2)}

print(f"PING FOLLOWERS: A0 injected alone @ {FREQ:g} Hz, {ON_S:.0f}s ON / {OFF_S:.0f}s OFF x {CYCLES}, pair {PAIR}, integ {INTEG} ms -> {logpath.name}", flush=True)
mesh_marker("running")
ss = None; hangs = 0
try:
    for cycle in range(1, CYCLES + 1):
        for label, secs, on in (("ON", ON_S, True), ("OFF", OFF_S, False)):
            while True:
                try:
                    if ss is None:
                        ss = opn()
                    gate(ss, on)
                    s = stream(ss, cycle, label, secs)
                    print(f"[c{cycle} {label:3}] A1 live {s['A1']['live_frac']} mag {s['A1']['mag_med']} ph {s['A1']['phase_med']} first {s['A1']['first_live_s']}s last {s['A1']['last_live_s']}s | "
                          f"A2 live {s['A2']['live_frac']} mag {s['A2']['mag_med']} ph {s['A2']['phase_med']} first {s['A2']['first_live_s']}s last {s['A2']['last_live_s']}s | n={s['A1']['n']}", flush=True)
                    log.write(json.dumps({"t": round(time.time(), 2), "cycle": cycle, "gate": label, "summary": s}) + "\n")
                    break
                except Exception as e:
                    hangs += 1
                    log.write(json.dumps({"t": round(time.time(), 2), "HANG": str(e)[:100], "hangs": hangs}) + "\n")
                    print(f"  !! HANG#{hangs}: {str(e)[:60]}; reconnecting in 30s", flush=True)
                    try: ss.close()
                    except Exception: pass
                    ss = None; time.sleep(30)
finally:
    try:
        if ss: send(ss, "x", 0.3); ss.close()
    except Exception:
        pass
    mesh_marker("ended")
    print("done; board stopped (x).", flush=True)
