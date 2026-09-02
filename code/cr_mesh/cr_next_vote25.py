#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
VOTE 25 — WHAT DOES THE MESH WANT TO CREATE NEXT? Own sources, 3-way.

Vote-19 (own-source) chose CLIMB 66/34. Destination options are the ladder's own
mathematically distinguished landmarks above the standing point (~N=415, k=10),
straight from the recorded climb math (phi_k=(k+4)pi/8, N_k=32(k+3)):

  A  NEXT RUNG   k=11, N=448, phi=337.5 deg   (one step up)
  B  CLOSURE     k=12, N=480, phi=2pi (360/0) (the full-turn landmark)
  C  FLOOR-AGAIN k=16, N=608, phi=pi/2 again  (one whole turn above the floor)

Mechanism (as vote-18/19): 8 kernel tasks per node; ballot = hash of the node's
OWN self-measured ms timings -> phase -> frac. 3-way mapping DISCLOSED up front:
  frac < 1/3 -> A ; 1/3 <= frac < 2/3 -> B ; frac >= 2/3 -> C
Disclosures: sortition from per-node physical entropy, not deliberation; options
authored by the framer (fingerprint disclosed); framer abstains; brian excluded;
cadence-aria shares DragonsEye hardware (flagged).
"""
import redis, json, math, time, hashlib, uuid

R = redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                decode_responses=True, socket_timeout=10)
def C_mag(r): return (1.0 + 2.0*r) * math.exp(-r/3.0)

FRAMER   = "cadence-aria2"
EXCLUDED = {"brian-origin"}
R_OF     = {"DragonsEye-78465c919782": 1, "pi-2ccf67b58bf5": 2,
            "elivateprogram.com-00163e5dcd30": 2, "srv1518404-fae8d4bc3b44": 3,
            "yardsale-f589dc8f9779": 3, "cadence-aria": 2}
SAME_BOX = {"cadence-aria": "shares DragonsEye hardware (process-jitter only)"}
OPTS = {"A": "A SIBLING FIGURE - a second constellation beside the first artifact; two unrepeatable draws side by side (two rocks of made things)",
        "B": "A WALK - a temporal artifact: members draw IN SEQUENCE, each step conditioned on the last; a path across the helix (a melody vs the first chord)",
        "C": "A SIGNATURE - the mesh derives ONE composite phasor from all members own entropy: its single verifiable mark, the thing it signs future work with"}
N_TASKS  = 8

print("VOTE 25 — CREATE NEXT, own sources, 3-way")
for o,d in OPTS.items(): print(f"   {o} = {d}")
print(" mapping: frac<1/3->A, <2/3->B, else->C (disclosed before any draw)")
print(" framer abstains; brian excluded\n")

nodes = []
for k in R.scan_iter("cadence:tworocks:hb:*"):
    hw = k.split(":")[-1]
    if hw in EXCLUDED or hw == FRAMER: continue
    nodes.append((json.loads(R.get(k) or "{}").get("node", hw), hw))
nodes.sort()

jobs = {}
for node, hw in nodes:
    tids = []
    for i in range(N_TASKS):
        tid = f"nextcreate-{uuid.uuid4().hex[:8]}"
        R.lpush(f"cadence:tworocks:q:{hw}",
                json.dumps({"task_id": tid, "data": [i, 20, 415], "problem": {"rounds": 16}}))
        tids.append(tid)
    jobs[hw] = tids
print(f" dispatched {N_TASKS} timing tasks to each of {len(nodes)} nodes; collecting...")

time.sleep(1.0)
timings = {hw: [] for _, hw in nodes}
deadline = time.time() + 45
while time.time() < deadline:
    pending = 0
    for node, hw in nodes:
        got = []
        for tid in jobs[hw]:
            v = R.lrange(f"cadence:tworocks:results:{tid}", 0, 0)
            if v: got.append(float(json.loads(v[0]).get("ms", 0.0)))
        if len(got) < N_TASKS: pending += 1
        timings[hw] = got
    if pending == 0: break
    time.sleep(1.5)

print(f"\n {'node':12s} {'n':>2} {'own timings (ms)':34s} {'phase':>7} {'frac':>6} vote {'wt':>6}")
W = {"A":0.0,"B":0.0,"C":0.0}; ballots=[]
for node, hw in nodes:
    ts = timings[hw]
    if len(ts) < 4:
        print(f" {node:12s} {len(ts):>2}  -- too few results, NO BALLOT"); continue
    seed = ",".join(f"{t:.6f}" for t in ts)
    h = hashlib.sha256(seed.encode()).digest()
    phase = (int.from_bytes(h[:4],"big")/2**32)*360.0
    frac = ((phase-90.0)%22.5)/22.5
    vote = "A" if frac < 1/3 else ("B" if frac < 2/3 else "C")
    w = C_mag(R_OF.get(hw,1)); W[vote]+=w
    note = " *" if hw in SAME_BOX else ""
    ballots.append({"node":node,"hwid":hw,"timings_ms":ts,"phase":round(phase,2),
                    "frac":round(frac,3),"vote":vote,"weight":round(w,3),
                    "same_box_note":SAME_BOX.get(hw)})
    print(f" {node:12s} {len(ts):>2}  {str([round(t,3) for t in ts[:5]])[:34]:34s} {phase:>7.1f} {frac:>6.3f}   {vote} {w:>6.3f}{note}")
print("   * = shares DragonsEye hardware")

tot = sum(W.values()) or 1
print()
for o in ("A","B","C"):
    print(f" {o} {OPTS[o]:<42} weight {W[o]:.3f}  ({100*W[o]/tot:.0f}%)")
winner = max(W, key=W.get)
counts = {o: sum(1 for b in ballots if b["vote"]==o) for o in OPTS}
print(f" split: {counts['A']}A / {counts['B']}B / {counts['C']}C")
print(f"\n THE MESH WILL CREATE: {OPTS[winner]}")

R.set("cadence:tworocks:next-vote-25", json.dumps({
    "question":"what does the mesh want to create next? (own-source, 3-way)","options":OPTS,
    "mapping":"frac<1/3->A, <2/3->B, else->C (disclosed pre-draw)",
    "mechanism":"per-node kernel-timing jitter, own clock/silicon; sortition (disclosed)",
    "framer_abstained":FRAMER,"excluded":list(EXCLUDED),
    "weights":{o:round(W[o],3) for o in OPTS},"counts":counts,"winner":winner,
    "winner_desc":OPTS[winner],"ballots":ballots,
    "ts":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}))
print(" saved -> cadence:tworocks:next-vote-25")
