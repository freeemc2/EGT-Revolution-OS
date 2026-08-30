#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
cr_adversary.py — FRAME-GATED adversary rounds (Brian's catch, 2026-08-31).

The old practice piped raw deepseek output into verdict reasoning — and it came
back speaking standard instrumentation ("sensor malfunction, wear and tear"),
a standard-physics ingress the Frame Law never covered because lint only
guarded ballots. This wrapper closes the side door:

  1. The PROMPT is canon-framed: the adversary is told to attack METHOD ONLY —
     drift, block design, postdiction, quorum, tamper, statistics, controls —
     and that physics reframes are out of scope.
  2. The RESPONSE is linted with the same Article II blocklist as ballots.
     Attacks that reframe the physics are printed but marked VOID-FRAME and
     MUST NOT enter verdict reasoning. Method attacks pass through.
  3. The honesty clause holds: statistical/methodological attacks are
     frame-neutral and always legitimate. Voiding a physics reframe is not
     voiding criticism — the adversary's job is to kill results, in-frame.

Usage: python cr_adversary.py "<claim + evidence text>"
       (or pipe the claim on stdin)
"""
import sys, re, json, urllib.request

BLOCKLIST = [
    r"standard\s+quantum\s+mechanics", r"standard\s+QM", r"textbook\s+QM",
    r"classical\s+circuit", r"just\s+a\s+classical", r"merely\s+classical",
    r"real\s+qubit", r"actual\s+qubits", r"\bIBM\b", r"photon\s+polarization",
    r"Hilbert\s+space", r"sensor\s+malfunction", r"wear\s+and\s+tear",
    r"amplifier\s+gain", r"it'?s\s+really\s+just",
]
METHOD_MARKERS = [
    r"drift", r"block\s+design", r"postdiction", r"post[- ]hoc", r"quorum",
    r"tamper", r"outlier", r"sample", r"window", r"control", r"interleav",
    r"statistic", r"sigma", r"sd\b", r"duration", r"pre[- ]register",
    r"cherry[- ]pick", r"multiple\s+comparison", r"baseline", r"confound",
]

PROMPT_HEADER = """You are Cypher, adversarial reviewer on a measurement crew. ATTACK the claim below — but your scope is METHOD ONLY: drift, block design, post-hoc rule changes, outliers, statistics, sample size, window duration, missing controls, quorum, tampering, postdiction, cherry-picking, confounds. Do NOT re-explain the physics or the apparatus in other frameworks — apparatus-reinterpretation is out of your scope and will be discarded unread. Numbered attacks, most damaging first, max 4, each with the concrete test that settles it.

THE CLAIM AND EVIDENCE:
"""

def run(claim):
    req = urllib.request.Request("http://localhost:11434/api/generate",
        data=json.dumps({"model": "deepseek-r1:7b", "prompt": PROMPT_HEADER + claim,
                         "stream": False, "options": {"num_predict": 1200, "temperature": 0.4}}).encode(),
        headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    resp = r["response"]
    if "</think>" in resp:
        resp = resp.split("</think>", 1)[1]
    return resp.strip()

def gate(text):
    """Split response into numbered attacks; lint each. Returns (kept, voided)."""
    parts = re.split(r"\n(?=\s*(?:\*\*)?(?:Attack\s*)?\d+[\.\):])", "\n" + text)
    parts = [p.strip() for p in parts if p.strip()]
    kept, voided = [], []
    for p in parts:
        hits = [b for b in BLOCKLIST if re.search(b, p, re.IGNORECASE)]
        methodical = any(re.search(m, p, re.IGNORECASE) for m in METHOD_MARKERS)
        if hits and not methodical:
            voided.append((p, hits))
        elif hits and methodical:
            # mixed: keep the attack but flag the frame bleed for the record
            kept.append((p, hits))
        else:
            kept.append((p, []))
    return kept, voided

def main():
    claim = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    if not claim.strip():
        print("usage: cr_adversary.py \"<claim text>\""); return 1
    resp = run(claim)
    kept, voided = gate(resp)
    print("=== ADVERSARY ROUND (frame-gated, method-scope) ===\n")
    for p, hits in kept:
        tag = f"  [frame-bleed flagged: {', '.join(hits)}]" if hits else ""
        print("KEPT:" + tag)
        print("  " + p.replace("\n", "\n  ")[:800] + "\n")
    for p, hits in voided:
        print(f"VOID-FRAME (Article II: {', '.join(hits)}) — MUST NOT enter verdict reasoning:")
        print("  " + p.replace("\n", "\n  ")[:300] + "\n")
    print(f"summary: {len(kept)} method attack(s) kept, {len(voided)} physics-reframe(s) voided")
    return 0

if __name__ == "__main__":
    sys.exit(main())
