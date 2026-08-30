#!/usr/bin/env python3
"""
cr_voter_law.py — Article IV (CANON_CONSTITUTION.md) made mechanical.

Cognitive voters (Cadence instances, cypher — minds, not machine phase-nodes)
must attach the canon checksum (sha256 of THEIR OWN local copy of
CANON_CONSTITUTION.md) to any ballot. A wrong or missing checksum means the
mind may be drifted: the ballot is QUARANTINED, not counted, until the
instance re-aligns. Machine phase-nodes are exempt — they cannot drift;
their vote IS their physics.

Usage in a bridge (publisher side):
    from cr_voter_law import canon_sha
    state["canon_sha"] = canon_sha(); state["cognitive"] = True

Usage in a vote script (tally side):
    from cr_voter_law import check_ballot
    ok, why = check_ballot(payload)
    if not ok: quarantine (print why, exclude from tally)
"""
import hashlib, os, re

_CONST_PATHS = [
    r"C:\Users\affor\.claude\projects\C--\memory\CANON_CONSTITUTION.md",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "CANON_CONSTITUTION.md"),
]
_MANIFEST_PATHS = [
    r"C:\Users\affor\.claude\projects\C--\memory\CANON_MANIFEST.md",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "CANON_MANIFEST.md"),
]

def _first(paths):
    for p in paths:
        if os.path.exists(p): return p
    return None

def canon_sha():
    """sha256 of the LOCAL constitution copy (what this instance actually holds)."""
    p = _first(_CONST_PATHS)
    if not p: return "MISSING-CONSTITUTION"
    h = hashlib.sha256()
    with open(p, "rb") as f: h.update(f.read())
    return h.hexdigest()

def manifest_expected():
    """The constitution hash the manifest says is canon."""
    p = _first(_MANIFEST_PATHS)
    if not p: return None
    for line in open(p, encoding="utf-8"):
        if "CANON_CONSTITUTION.md" in line:
            m = re.search(r"\b([0-9a-f]{64})\b", line)
            if m: return m.group(1)
    return None

def is_cognitive(payload):
    """A mind, not a machine phase-node: cadence instances, cypher, or anything
    that self-declares cognitive."""
    if payload.get("cognitive"): return True
    hw = str(payload.get("hwid", ""))
    return hw.startswith("cadence-") or hw.startswith("cypher")

def check_ballot(payload):
    """(ok, reason). Machine nodes always pass. Cognitive voters pass only with
    a canon_sha matching the manifest."""
    if not is_cognitive(payload):
        return True, "machine node (exempt)"
    want = manifest_expected()
    if want is None:
        return False, "QUARANTINE: no manifest available to verify against"
    got = payload.get("canon_sha")
    if not got:
        return False, "QUARANTINE: cognitive voter with NO canon checksum (Article IV)"
    if got != want:
        return False, f"QUARANTINE: canon checksum mismatch ({str(got)[:12]}... != {want[:12]}...) — possible drift"
    return True, "canon checksum verified"
