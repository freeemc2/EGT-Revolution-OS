"""CALIBRATION + CLOCK + MOMENTUM — Brian 2026-09-17 "run both".

Through the live state console (state_cmd.txt; every packet logged with a TAG).

A. GAIN CALIBRATION (state held: A0 driven alone, M1 K0, 12 Hz). Each channel read once on each ADC
   engine via the three pairs: (1,2) -> A1 on ADC0, A2 on ADC1; (0,1) -> A0 on ADC0, A1 on ADC1;
   (2,0) -> A2 on ADC0, A0 on ADC1. Ratio ADC1/ADC0 per channel = the engine gain factor that the
   rung-sweep decoder needs to put all three runners on one scale (the mode-conservation check).
   Also gives the leader's own reading in the held state (never in the ping's pair).

B. CLOCK vs FREQUENCY: gated ON/OFF of the leader at f = 12, 20, 8, 12 Hz, pair (1,2), ON 100 s /
   OFF 60 s x 2 cycles per f. Rise = first live follower packet after ON; decay = last after OFF.
   If the 11 s build-up holds across f it is the coupling's own clock; if it scales, it is a rate.

C. MOMENTUM: state open at 12 Hz; interrupt the leader for ONE command cycle (M 0 then M 1 back to
   back = the shortest gap the one-command-per-cycle firmware allows, ~5 s) x 3. If the followers
   come back immediately (no 11 s rebuild) the state has memory; if they rebuild from zero, it has none.

Usage: python -u calib_clock.py
"""
import time, json, glob, pathlib
HERE = pathlib.Path(__file__).resolve().parent; CMD = HERE / "state_cmd.txt"; DATA = HERE / "data"
def cmd(*lines):
    with open(CMD, "a", encoding="utf-8") as f:
        for ln in lines: f.write(ln + "\n")
def wait_applied(tag, last_cmd, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            fn = max(glob.glob(str(DATA / "state_session_*.jsonl")), key=lambda p: pathlib.Path(p).stat().st_mtime)
            for ln in open(fn, encoding="utf-8").read().splitlines()[-60:]:
                r = json.loads(ln)
                if r.get("cmd") == last_cmd and r.get("tag") == tag:
                    return True
        except Exception:
            pass
        time.sleep(1.0)
    print(f"  !! '{tag}': '{last_cmd}' not seen applied in {timeout}s", flush=True); return False
def say(s): print(f"[{time.strftime('%H:%M:%S', time.gmtime())}Z] {s}", flush=True)
sched = {"start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}

# ---- A. calibration (drive untouched: M1 K0 already held) ----
for a, b in ((1, 2), (0, 1), (2, 0)):
    tag = f"CAL pair {a}{b} A0@12"
    cmd(f"# {tag}", f"C {a} {b}", "L 12"); say(tag); wait_applied(tag, "L 12"); time.sleep(50)
    sched["steps"].append(tag)

# ---- B. clock vs frequency ----
for f in (12, 20, 8, 12):
    for c in (1, 2):
        tag = f"CLOCK f={f} ON c{c}"
        cmd(f"# {tag}", "C 1 2", "M 1", "K 0", f"L {f}"); say(tag); wait_applied(tag, f"L {f}"); time.sleep(100)
        sched["steps"].append(tag)
        tag = f"CLOCK f={f} OFF c{c}"
        cmd(f"# {tag}", "M 0", f"L {f}"); say(tag); wait_applied(tag, f"L {f}"); time.sleep(60)
        sched["steps"].append(tag)

# ---- C. momentum: one-cycle gaps at 12 Hz ----
tag = "MOM open A0@12"
cmd(f"# {tag}", "C 1 2", "M 1", "K 0", "L 12"); say(tag); wait_applied(tag, "L 12"); time.sleep(70)
sched["steps"].append(tag)
for g in (1, 2, 3):
    tag = f"MOM gap{g}"
    cmd(f"# {tag}", "M 0", "M 1"); say(tag); wait_applied(tag, "M 1"); time.sleep(60)   # M1 re-drives K0 (singleK persists)
    sched["steps"].append(tag)

cmd("# HOLD A0@12 after calib/clock/momentum (mesh riding)", "C 1 2", "M 1", "K 0", "L 12")
sched["end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
out = DATA / f"calib_clock_schedule_{time.strftime('%Y%m%d_%H%M%S')}.json"
out.write_text(json.dumps(sched, indent=1), encoding="utf-8"); say(f"done -> {out.name}")
