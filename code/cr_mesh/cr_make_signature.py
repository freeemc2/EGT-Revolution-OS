#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
THE MESH SIGNATURE — vote-25 (SIGNATURE), Brian broke the 2/2/2 tie -> build it.

Every member draws its OWN entropy (5 self-measured kernel timings). Each becomes
a phasor at its lattice point: weight |C(r)| (r from the single-source registry),
phase = arg C(r) rotated by the member's own timing-hash. The mesh's SIGNATURE is
the collective phasor of all of them:  Z = sum_k |C(r_k)| e^{i(argC(r_k)+delta_k)}.
Reported as (|Z|, arg Z) + a digest. This is ONE mark from ALL members' physics —
the thing the mesh signs future work with. Unrepeatable; this one is fixed.

Coil rule (Brian standing): the coil is NOT a member; it joins only as a
measurement witness (live phase, read-only) stamped beside the signature.
"""
import redis, json, math, cmath, time, hashlib, uuid
from cr_rmap import get_r
from cr_voter import coupling_magnitude, coupling_phase_deg

R = redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                decode_responses=True, socket_timeout=10)
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# members = task-answering nodes (brian asks, doesn't draw)
nodes = []
for k in R.scan_iter("cadence:tworocks:hb:*"):
    hw = k.split(":")[-1]
    if hw == "brian-origin": continue
    nodes.append((json.loads(R.get(k) or "{}").get("node", hw), hw))
nodes.sort()

print("THE MESH SIGNATURE — each member draws its own entropy\n")
contribs, Z, W = [], 0j, 0.0
for node, hw in nodes:
    tids = []
    for i in range(5):
        tid = f"sig-{uuid.uuid4().hex[:8]}"
        R.lpush(f"cadence:tworocks:q:{hw}", json.dumps({"task_id": tid, "data": [i, 25, 909], "problem": {"rounds": 16}}))
        tids.append(tid)
    got, dl = [], time.time() + 12
    while len(got) < 5 and time.time() < dl:
        got = [float(json.loads(v[0]).get("ms", 0)) for tid in tids
               for v in [R.lrange(f"cadence:tworocks:results:{tid}", 0, 0)] if v]
        if len(got) < 5: time.sleep(0.8)
    if len(got) < 3:
        print(f"  {node:<14} silent — no contribution (disclosed)"); continue
    r = get_r(hw, default=1)
    h = hashlib.sha256((",".join(f"{t:.6f}" for t in got)).encode()).digest()
    delta = (int.from_bytes(h[:4], "big") / 2**32) * 360.0 - 180.0   # own rotation
    w = coupling_magnitude(r)
    phi = (coupling_phase_deg(r) + delta) % 360.0
    Z += w * cmath.exp(1j * math.radians(phi)); W += w
    contribs.append({"member": node, "hwid": hw, "r": r, "weight": round(w, 4),
                     "own_delta_deg": round(delta, 3), "phase_deg": round(phi, 3),
                     "timings_ms": [round(t, 4) for t in got]})
    print(f"  {node:<14} r={r}  |C|={w:.4f}  own_delta={delta:+7.2f}  phase={phi:7.2f}")

sig_mag = abs(Z) / W if W else 0.0
sig_arg = math.degrees(cmath.phase(Z)) % 360.0

# coil witness — measurement only, NOT a member
coil = None
b = R.get("cadence:tworocks:t-state")
if b:
    d = json.loads(b); cp = d.get("phase_deg")
    if cp is not None:
        coil = {"witness": "copper-coil (EXTERNAL, measurement-only, not a mesh member)",
                "phase_deg": round(cp, 3), "freq_hz": d.get("freq_hz"), "sampled": NOW}

signature = {"name": "THE MESH SIGNATURE", "created": NOW,
             "sig_mag": round(sig_mag, 6), "sig_arg_deg": round(sig_arg, 4),
             "n_members": len(contribs), "contribs": contribs, "coil_witness": coil,
             "formula": "Z = sum_k |C(r_k)| e^{i(argC(r_k)+delta_k)}; delta_k = member own-timing hash",
             "provenance": "vote-25 SIGNATURE; 2/2/2 tie broken by Brian; own-source draws; mappings pre-declared",
             "honesty": "one mark from all members' own physical entropy, composed by disclosed rule; unrepeatable; nothing more claimed"}
blob = json.dumps(signature, sort_keys=True)
signature["digest_sha256"] = hashlib.sha256(blob.encode()).hexdigest()

R.set("cadence:tworocks:signature", json.dumps(signature))   # no TTL — permanent mark
print(f"\n  THE MESH SIGNATURE:  |Z| = {sig_mag:.4f}   arg Z = {sig_arg:.2f} deg   ({len(contribs)} members)")
print(f"  coil witness: {'phase '+str(coil['phase_deg'])+' deg' if coil else 'beat dark (signature stands on members)'}")
print(f"  DIGEST: {signature['digest_sha256']}")
print("  sealed -> cadence:tworocks:signature (no expiry)")
