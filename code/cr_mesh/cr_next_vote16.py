#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
VOTE 16 — HELD-STATE RATIFICATION: is OG Coil 1 HELD at N=415?

Written BEFORE the Phase-3 window verdict was computed (2026-08-30), so the
framing cannot be tuned to the outcome. First vote under the Held-State Rule
(canon_held_state_rule.md) and the re-declared Phase-2 hold rule:
  over the 60-min servo window: |mean delta| < 0.5 deg, |trend| < 1.0 deg/hour,
  window sd <= 4.662 deg (1.5x the servo-off instrument-noise control, ledger A-7).

  A = HELD: the Phase-3 window satisfies the declared rule -> "held N=415"
      enters the record (first held state under the rule)
  B = NOT HELD / rule FAILS: the window does not satisfy the rule, the claim
      dies here, coil keeps its servo but the record says "touched" only

Framer (aria) abstains. Mapping disclosed before any phase is read: each
node's phase cell fraction frac = ((phase-90) mod 22.5)/22.5; frac >= 0.5 -> A,
else B — A is the first-stated option, same fixed convention as votes 1-15.
Weights: C_mag(r) per node, machine nodes via their published node-phase.
Sealed to redis cadence:tworocks:next-vote-16 with the mechanical window
verdict attached alongside (the mesh ratifies or rejects; it cannot alter the
mechanical numbers).

Run ONLY after: (1) cr_ballot_lint.py passes on this file, (2) the Phase-3
window verdict is computed and passed to --verdict HELD|FAILED.
"""
import redis, json, math, sys, time
from cr_voter_law import check_ballot   # Article IV: quarantine drifted cognitive voters

R = redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                decode_responses=True, socket_timeout=10)
def C_mag(r): return (1.0 + 2.0*r) * math.exp(-r/3.0)
FRAMER = "cadence-aria"

if "--verdict" not in sys.argv:
    print("usage: cr_next_vote16.py --verdict HELD|FAILED   (the mechanical window result)")
    sys.exit(1)
mech = sys.argv[sys.argv.index("--verdict")+1].upper()

print("VOTE 16 — HELD-STATE RATIFICATION (framed before the verdict existed)")
print(" A = HELD (window satisfies the declared rule)")
print(" B = NOT HELD (rule fails — the claim dies, record says touched only)")
print(f" mechanical window verdict (computed separately): {mech}")
print(" framer aria abstains; mapping disclosed (frac>=0.5 -> A, fixed convention)\n")

Aw = 0.0; Bw = 0.0; ballots = []
for k in sorted(R.scan_iter("cadence:tworocks:node-phase:*")):
    d = json.loads(R.get(k) or "{}")
    ph = d.get("phase_deg"); r = d.get("r"); node = d.get("node","?"); hw = d.get("hwid","")
    if ph is None or r is None: continue
    if node == "brian": continue
    if hw == FRAMER: continue
    ok, why = check_ballot(d)
    if not ok:
        print(f" {node:16s} -- {why} -- BALLOT NOT COUNTED")
        continue
    frac = ((float(ph) - 90.0) % 22.5) / 22.5
    w = C_mag(float(r))
    vote = "A" if frac >= 0.5 else "B"
    if vote == "A": Aw += w
    else: Bw += w
    ballots.append((node, round(float(ph),2), round(frac,3), vote, round(w,3)))

if len(ballots) < 2:
    print(f"NO QUORUM — only {len(ballots)} voter(s). Vote VOID, not sealed. (Article IV / 08-29 lesson)")
    sys.exit(1)

print(f" {'node':16s} {'phase':>8s} {'cell':>6s}  vote {'weight':>7s}")
for n, ph, frac, vote, w in ballots:
    print(f" {n:16s} {ph:>8.2f} {frac:>6.3f}     {vote} {w:>7.3f}")

tot = Aw + Bw if (Aw + Bw) > 0 else 1
print(f"\n A HELD     : {Aw:.3f}  ({100*Aw/tot:.0f}%)")
print(f" B NOT HELD : {Bw:.3f}  ({100*Bw/tot:.0f}%)")
mesh_says = "HELD" if Aw > Bw else "NOT HELD"
print(f"\n mesh ratification: {mesh_says}   mechanical verdict: {mech}")
if (mesh_says == "HELD") != (mech == "HELD"):
    print(" DISCREPANCY between mesh and mechanical verdict — a FINDING, not a negotiation (lab rule).")

R.set("cadence:tworocks:next-vote-16", json.dumps({
    "question": "held-state ratification: OG Coil 1 HELD at N=415 per declared rule",
    "framed_before_verdict": True, "framer_abstained": FRAMER,
    "mechanical_verdict": mech, "mesh_says": mesh_says,
    "A_weight": round(Aw,3), "B_weight": round(Bw,3),
    "ballots": ballots, "voters": len(ballots),
    "mapping_disclosed": "frac>=0.5 -> A (first-stated option), fixed convention",
    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}))
print(" sealed: cadence:tworocks:next-vote-16")
