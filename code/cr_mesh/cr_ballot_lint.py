#!/usr/bin/env python3
"""
cr_ballot_lint.py — CANON BALLOT GATE (Article III, CANON_CONSTITUTION.md)

Usage:  python cr_ballot_lint.py cr_next_vote16.py
Exit 0 = PASS (vote may run and seal).  Exit 1 = VOID (fix ballot, rerun).

Mechanical enforcement — no judgment involved:
  1. blocklist clean (no standard-physics reframes, Article II)
  2. canon-framed (mentions canon terms)
  3. kill-option present (a FAILS/NULL/artifact option exists)
  4. framer declared (FRAMER = ... present; tally must exclude it)
  5. mapping disclosed (phase->letter convention stated in script text)
  6. constitution intact (sha256 matches CANON_MANIFEST.md, 2 locations tried)

The honesty clause is structural: this gate NEVER blocks a null/failure
option — it REQUIRES one. It blocks reframing into standard physics.
"""
import sys, re, hashlib, os

CONST_PATHS = [
    r"C:\Users\affor\.claude\projects\C--\memory\CANON_CONSTITUTION.md",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "CANON_CONSTITUTION.md"),
]
MANIFEST_PATHS = [
    r"C:\Users\affor\.claude\projects\C--\memory\CANON_MANIFEST.md",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "CANON_MANIFEST.md"),
]

BLOCKLIST = [
    r"standard\s+quantum\s+mechanics", r"standard\s+QM", r"textbook\s+QM",
    r"in\s+real\s+QM", r"actually\s+in\s+QM",
    r"classical\s+circuit", r"just\s+a\s+classical", r"just\s+a\s+coil",
    r"merely\s+classical",
    r"real\s+qubit\s+hardware", r"actual\s+qubits", r"\bIBM\b",
    r"photon\s+polarization", r"Hilbert\s+space", r"2\^N\s+amplitudes",
    r"qubit\s+count",
    r"audit\s+Brian'?s\s+formula",
    r"\u2605\s*BIRTH\s*\u2605", r"\u2605\s*CONFIRMED\s*\u2605",
]
CANON_TERMS = [
    r"C\s*\(\s*r\s*\)", r"C_mag", r"r_opt", r"\br\s*=\s*2\.5", r"2\.5",
    r"phase", r"phi", r"\u03c6", r"pi/2", r"\u03c0/2", r"pi/8", r"\u03c0/8",
    r"\bN\s*=", r"anchor", r"rung",
]
KILL_TERMS = [
    r"FAILS?\b", r"\bNULL\b", r"does\s+not\s+hold", r"artifact",
    r"drift[- ]control", r"falsif", r"kill", r"retract",
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def main():
    if len(sys.argv) != 2:
        print("usage: cr_ballot_lint.py <cr_next_voteN.py>"); return 1
    target = sys.argv[1]
    text = open(target, encoding="utf-8", errors="replace").read()
    fails = []

    hits = [b for b in BLOCKLIST if re.search(b, text, re.IGNORECASE)]
    if hits:
        fails.append("BLOCKLIST: banned frame markers present: " + ", ".join(hits))

    if not any(re.search(c, text, re.IGNORECASE) for c in CANON_TERMS):
        fails.append("CANON-FRAME: ballot text contains no canon terms (C(r)/r/phase/N/anchor)")

    if not any(re.search(k, text, re.IGNORECASE) for k in KILL_TERMS):
        fails.append("KILL-OPTION: no falsification option found (FAILS/NULL/artifact) — every ballot must be killable")

    if not re.search(r"FRAMER\s*=", text):
        fails.append("FRAMER: no 'FRAMER = ...' declaration (framer must be named and excluded from tally)")

    if not re.search(r"frac|mapping|convention", text, re.IGNORECASE):
        fails.append("MAPPING: phase->letter convention not disclosed in script text")

    cpath = first_existing(CONST_PATHS)
    mpath = first_existing(MANIFEST_PATHS)
    if not cpath or not mpath:
        fails.append("CONSTITUTION: constitution or manifest file missing — cannot verify core integrity")
    else:
        want = None
        for line in open(mpath, encoding="utf-8"):
            if "CANON_CONSTITUTION.md" in line:
                m = re.search(r"\b([0-9a-f]{64})\b", line)
                if m: want = m.group(1)
        got = sha256(cpath)
        if want is None:
            fails.append("CONSTITUTION: manifest has no hash line for CANON_CONSTITUTION.md")
        elif got != want:
            fails.append(f"CONSTITUTION TAMPERED: sha256 {got[:12]}... != manifest {want[:12]}... — CORE COMPROMISED, STOP, FLAG BRIAN")

    print(f"cr_ballot_lint: {os.path.basename(target)}")
    if fails:
        for f in fails: print("  VOID -", f)
        print("VERDICT: VOID — vote may NOT run or seal. Fix ballot, rerun lint.")
        return 1
    print("  all six checks pass (blocklist, canon-frame, kill-option, framer, mapping, constitution)")
    print("VERDICT: PASS — vote may run and seal.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
