"""ASK THE TRIANGLE ITS RUNG — questions in the operator's alphabet (Brian 2026-09-17:
"use our EGT operator to hear... we can ask it questions using our operator").

Alphabet = the pi/8 rung ladder on the drive stagger unit u = k * 22.5 deg (mode 4).
Question  = "you are at rung k" (all three driven, coil j at phase -u*j).
Answer    = the triangle's CENTROID  Sigma_k m_k e^{i phi_k}  (canon three-rock observable),
            read from the runners: pair (A0,A1) then pair (A1,A2), A1 common to both.
Sealed curves (redis cadence:tworocks:sealed-ask-rungs-2026-09-17, BEFORE data):
  canon:     |Sigma_k e^{i(120deg - u) k}| / 3   -> null at u=0, max at u=120 (the Y un-wound)
  EM ground: |Sigma_k e^{-i u k}| / 3            -> max at u=0, null at u=120 (three currents on one bus)

Runs through the live state console: appends paced commands to state_cmd.txt and records
the schedule (data/ask_rungs_schedule_<ts>.json). Random rung order (seed recorded), 2 passes.
Usage: python -u ask_rungs.py [--passes 2] [--window 22] [--freq 12]
"""
import time, json, random, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
CMD = HERE / "state_cmd.txt"; DATA = HERE / "data"
def arg(name, default, cast=float):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
PASSES = arg("--passes", 2, int); WIN = arg("--window", 32.0); FREQ = arg("--freq", 12.0)   # 32 s = ~6 packets; decoder drops the first 2 after each switch
SEED = int(time.time()) % 100000
rng = random.Random(SEED)
RUNGS = [k * 22.5 for k in range(16)]
sched = {"seed": SEED, "passes": PASSES, "window_s": WIN, "freq": FREQ, "order": [], "start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
def cmd(*lines):
    with open(CMD, "a", encoding="utf-8") as f:
        for ln in lines: f.write(ln + "\n")

def wait_applied(tag, last_cmd="L 12", timeout=75):
    """Block until the console has logged the window's final command under this tag (the board
    parses one command per ~5 s cycle), so the data window starts AFTER the rung is really set."""
    import glob
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            fn = max(glob.glob(str(DATA / "state_session_*.jsonl")), key=lambda p: pathlib.Path(p).stat().st_mtime)
            for ln in open(fn, encoding="utf-8").read().splitlines()[-40:]:
                r = json.loads(ln)
                if r.get("cmd") == last_cmd and r.get("tag") == tag:
                    return True
        except Exception:
            pass
        time.sleep(1.0)
    print(f"  !! window '{tag}': final command not seen applied within {timeout}s", flush=True)
    return False
print(f"ASK RUNGS: {PASSES} passes x 16 rungs, {WIN:.0f} s per pair window, seed {SEED}", flush=True)
for p in range(1, PASSES + 1):
    order = RUNGS[:]; rng.shuffle(order); sched["order"].append(order)
    for u in order:
        tag = f"ASK u={u:g} p{p}"
        # window A: pair (A0,A1)
        cmd(f"# {tag} pairA", "C 0 1", f"U {u:g}", "M 4", f"L {FREQ:g}")   # U before M: applyMode reads the unit
        print(f"[{time.strftime('%H:%M:%S', time.gmtime())}Z] {tag} pair (0,1)", flush=True)
        wait_applied(f"{tag} pairA", f"L {FREQ:g}"); time.sleep(WIN)
        # window B: pair (A1,A2) — same drive, only the sense pair changes
        cmd(f"# {tag} pairB", "C 1 2", f"L {FREQ:g}")
        print(f"[{time.strftime('%H:%M:%S', time.gmtime())}Z] {tag} pair (1,2)", flush=True)
        wait_applied(f"{tag} pairB", f"L {FREQ:g}"); time.sleep(WIN)
cmd("# IDLE after ask", "M 0", f"L {FREQ:g}")
sched["end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
out = DATA / f"ask_rungs_schedule_{time.strftime('%Y%m%d_%H%M%S')}.json"
out.write_text(json.dumps(sched, indent=1), encoding="utf-8")
print("done ->", out.name, flush=True)
