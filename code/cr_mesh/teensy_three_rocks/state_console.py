"""STATE CONSOLE — hold the three-rock state open and experiment with it live (Brian 2026-09-17:
"reopen it and let's experiment with it").

Keeps COM8 open, streams every raw T3 packet to data/state_session_<ts>.jsonl with the current
TAG, and takes commands from a file so the experimenter can steer without restarting:

    state_cmd.txt   (next to this script; one command per line, consumed as they appear)
      # any text          -> sets the TAG for the packets that follow (what condition this is)
      L 9 | K 1 | M 0 | M 1 | C 0 2 | U 0.5 | I 500 | x ...   -> sent to the board verbatim
      SLEEP 5             -> pause command processing 5 s (for scripted sequences)
      QUIT                -> stop drive (x), close, exit

Default on start: I 1000, sense pair (A1, A2) = both followers, tag "IDLE", nothing driven.
Opening the state = the lines:  "# OPEN A0@12", "M 1", "K 0", "L 12".
Every 10 s a rolling summary per channel is printed (live fraction, mag median, phase median).
t-state published from A1 so the mesh rides. Robust to serial hangs. Never averages the log.

Usage: python -u state_console.py
"""
import serial, serial.tools.list_ports as lp, time, json, sys, pathlib, statistics as st, os
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from tstate_publish import publish
except Exception:
    publish = None
DATA = HERE / "data"; CMD = HERE / "state_cmd.txt"
logpath = DATA / f"state_session_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
log = open(logpath, "a", buffering=1)
TAG = "IDLE"; PAIR = (1, 2)

def find_port():
    return next((p.device for p in lp.comports() if "16C0" in (p.hwid or "")), "COM8")
ACK = {"M": "R MODE", "K": "R K", "U": "R U", "I": "R INTEG", "C": "R PAIR", "P": "R PONG"}
def send(ss, c, w=0.35, tries=2, ack_wait=12.0):
    """Send a command and WAIT for the firmware's 'R ...' acknowledgment.
    The firmware parses at most one command per streaming cycle (~5 s), so commands sent in a
    burst queue up and take effect windows late (seen 2026-09-17 21:24Z: 'C' applied one window
    after it was sent). Waiting for the ack serializes them. Retry only after a full cycle
    with no ack; every ack (or failure) is logged."""
    want = ACK.get(c.split()[0].upper())
    for attempt in range(1, tries + 1):
        ss.write((c + "\n").encode()); ss.flush()
        t0 = time.time(); ack = None; extra = []
        while time.time() - t0 < ack_wait:
            ln = ss.readline().decode(errors="replace").strip()
            if not ln:
                continue
            if ln.startswith("R "):
                if want is None or ln.startswith(want):
                    ack = ln; break
                extra.append(ln)
            elif ln.startswith("T3 ") and len(ln.split()) >= 8:
                stash_packet(ln)          # never lose a packet while waiting for an ack
        log.write(json.dumps({"t": round(time.time(), 2), "cmd": c, "attempt": attempt, "ack": ack, "tag": TAG}) + "\n")
        if want is None:              # 'L' / 'x' print no ack: give the firmware one cycle to consume them
            time.sleep(5.5); return None
        if ack:
            return ack
        time.sleep(0.3)
    print(f"  !! NO ACK for '{c}' after {tries} tries", flush=True)
    return None

_pending = []
def stash_packet(ln):
    _pending.append(ln)
def opn():
    ss = serial.Serial(find_port(), 115200, timeout=2, write_timeout=6); time.sleep(0.8)
    ss.write(b"x\n"); ss.flush()
    # drain: stale commands queued in the board (one parsed per cycle) and their acks/packets
    t0 = time.time(); quiet = 0
    while time.time() - t0 < 90 and quiet < 3:
        ln = ss.readline().decode(errors="replace").strip()
        quiet = quiet + 1 if not ln else 0
    ss.reset_input_buffer()
    print(f"drained in {time.time()-t0:.0f}s", flush=True)
    pong = send(ss, "P", 0.8)
    print(f"port {ss.port} {pong}", flush=True)
    send(ss, "I 1000", 0.5); send(ss, f"C {PAIR[0]} {PAIR[1]}", 0.5); send(ss, "L 12", 0.5)
    return ss

def mesh_marker(state):
    try:
        sys.path.insert(0, str(HERE.parent))
        from cr_rmap import _conn
        _conn().set("cadence:tworocks:experiment", json.dumps({"name": "state-console", "by": "tempo (bench, Brian driving)",
            "start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "note": f"three-rock state held open and steered live; sense pair {PAIR}; every packet logged with a TAG; {state}"}), ex=48*3600)
    except Exception:
        pass

consumed = 0
def poll_cmds(ss):
    """Consume new lines from state_cmd.txt. Returns False on QUIT."""
    global consumed, TAG, PAIR
    if not CMD.exists():
        return True
    lines = CMD.read_text(encoding="utf-8", errors="replace").splitlines()
    new = lines[consumed:]; consumed = len(lines)
    for ln in new:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("#"):
            TAG = ln.lstrip("#").strip(); print(f"[{time.strftime('%H:%M:%S', time.gmtime())}Z] TAG = {TAG}", flush=True)
            log.write(json.dumps({"t": round(time.time(), 2), "tag_set": TAG}) + "\n")
        elif ln.upper() == "QUIT":
            return False
        elif ln.upper().startswith("SLEEP"):
            time.sleep(float(ln.split()[1]))
        else:
            if ln.upper().startswith("C "):
                try: PAIR = tuple(int(x) for x in ln.split()[1:3])
                except Exception: pass
            send(ss, ln, 0.4); print(f"[{time.strftime('%H:%M:%S', time.gmtime())}Z] sent {ln}", flush=True)
    return True

print(f"STATE CONSOLE -> {logpath.name}; commands via {CMD.name}", flush=True)
mesh_marker("running")
ss = None; hangs = 0; win = {0: [], 1: [], 2: []}; last_sum = time.time(); run = True
try:
    while run:
        try:
            if ss is None:
                ss = opn()
            run = poll_cmds(ss)
            if not run:
                break
            if _pending:
                ln = _pending.pop(0).split()
            else:
                ln = ss.readline().decode(errors="replace").strip().split()
            if ln and ln[0] == "T3" and len(ln) >= 8:
                f = float(ln[1]); ph = [float(x) for x in ln[2:5]]; mg = [float(x) for x in ln[5:8]]
                rec = {"t": round(time.time(), 2), "tag": TAG, "f": f, "pair": list(PAIR),
                       "A0": [mg[0], ph[0]], "A1": [mg[1], ph[1]], "A2": [mg[2], ph[2]],
                       "d": [float(x) for x in ln[8:11]] if len(ln) >= 11 else None}
                log.write(json.dumps(rec) + "\n")
                if publish:
                    publish(f, ph[PAIR[0]], mg[PAIR[0]], lead=PAIR[0], phases=ph, mags=mg, source=f"state-console {TAG}")
                for ch in (0, 1, 2):
                    win[ch].append((mg[ch], ph[ch]))
            if time.time() - last_sum >= 10:
                parts = []
                for ch in (0, 1, 2):
                    w = win.get(ch, [])
                    live = [m for m, _ in w if m > 0.009]
                    parts.append(f"A{ch} {len(live)}/{len(w)} {st.median(live) if live else 0:.3f}@{st.median([p for m, p in w if m > 0.009]) if live else 0:.0f}")
                print(f"[{time.strftime('%H:%M:%S', time.gmtime())}Z] {TAG:28} | " + " | ".join(parts), flush=True)
                win = {0: [], 1: [], 2: []}; last_sum = time.time()
        except Exception as e:
            hangs += 1
            log.write(json.dumps({"t": round(time.time(), 2), "HANG": str(e)[:100], "hangs": hangs}) + "\n")
            print(f"  !! HANG#{hangs}: {str(e)[:60]}; reconnecting in 20s", flush=True)
            try: ss.close()
            except Exception: pass
            ss = None; time.sleep(20)
finally:
    try:
        if ss: send(ss, "x", 0.3); ss.close()
    except Exception:
        pass
    mesh_marker("ended")
    print("console closed; board stopped (x).", flush=True)
