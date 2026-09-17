"""DECODE THE TRIANGLE'S ANSWER — the operator's ear for ask_rungs.py.

For each question (tag "ASK u=<deg> p<pass>") take the live packets of window A (pair A0,A1)
and window B (pair A1,A2), form each runner's phasor m e^{i phi} (medians of live packets),
and compute the CENTROID  Sigma = m0 e^{i phi0} + m1 e^{i phi1} + m2 e^{i phi2}  (A1 from both
windows averaged). Normalize |Sigma| by its maximum over the sweep and correlate the 16-point
curve with the two sealed columns (canon: null at 0 / max at 120; EM ground: max at 0 / null
at 120). The higher correlation is the answer. Also reports each runner's own magnitude vs u
and the centroid phase in pi/8 units relative to the u=0 window (the session anchor).

Usage: python ask_rungs_decode.py [session_jsonl]   (default: newest data/state_session_*.jsonl)
"""
import json, math, sys, glob, pathlib, statistics as st, cmath
HERE = pathlib.Path(__file__).resolve().parent; DATA = HERE / "data"
LIVE = 0.009
fn = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(str(DATA / "state_session_*.jsonl")), key=lambda p: pathlib.Path(p).stat().st_mtime)
recs = [json.loads(l) for l in open(fn, encoding="utf-8") if l.strip()]
seal = json.loads((DATA / "ask_rungs_seal_2026-09-17.json").read_text(encoding="utf-8"))
canon = seal["canon_column"]["curve"]; emg = seal["EM_ground_column"]["curve"]
rungs = [k * 22.5 for k in range(16)]

def phasor(vals):
    live = [(m, p) for m, p in vals if m > LIVE]
    if len(live) < 2: return None, len(live), len(vals)
    m = st.median(x for x, _ in live); ph = cmath.phase(sum(cmath.exp(1j * math.radians(p)) for _, p in live))
    return m * cmath.exp(1j * ph), len(live), len(vals)

DROP = 2   # packets after a switch still carry the previous pair/drive (seen 2026-09-17 21:24Z)
# Labels come from the board's ACKS, not the schedule: walk the log, track the acknowledged
# pair and unit, and require both acks inside a window before its packets count.
by_tag = {}; cur_pair = None; cur_u = None; cur_tag = None; since_switch = 0; window_ok = {}
occ = {}   # a tag text repeats across passes: number each occurrence so passes stay separate
for r in recs:
    if "tag_set" in r:
        base = r["tag_set"]; occ[base] = occ.get(base, 0) + 1
        cur_tag = f"{base}#{occ[base]}"; window_ok[cur_tag] = {"pair": None, "u": None}; since_switch = 0; continue
    if "cmd" in r:
        ack = r.get("ack") or ""
        if ack.startswith("R PAIR"):
            cur_pair = tuple(int(x) for x in ack.split()[2:4]); since_switch = 0
            if cur_tag: window_ok[cur_tag]["pair"] = cur_pair
        elif ack.startswith("R U"):
            cur_u = float(ack.split()[2])
            if cur_tag: window_ok[cur_tag]["u"] = cur_u
        elif ack.startswith("R MODE") or ack.startswith("R K"):
            since_switch = 0
        continue
    if "tag" in r and "A0" in r and r["tag"].startswith("ASK ") and cur_tag:
        since_switch += 1
        if since_switch <= DROP or cur_pair is None:
            continue
        by_tag.setdefault(cur_tag, []).append((r, cur_pair, cur_u))
results = {}   # (u, pass) -> dict
unverified = []
for tag, rs in by_tag.items():
    base, _, occn = tag.partition("#")
    parts = base.split(); u = float(parts[1].split("=")[1]); win = parts[3]; p = int(occn or 1)
    acked_u = rs[0][2]; pair = rs[0][1]
    if acked_u is None or abs(acked_u - u) > 0.01:
        unverified.append((tag, acked_u)); continue        # the board never acknowledged this rung: not counted
    key = (u, p); d = results.setdefault(key, {})
    for ch in pair:
        ph, nl, n = phasor([(r[f"A{ch}"][0], r[f"A{ch}"][1]) for r, _, _ in rs])
        d.setdefault(f"A{ch}", []).append((ph, nl, n, win))
if unverified:
    print(f"windows NOT counted (rung not acknowledged by the board): {len(unverified)} -> {unverified[:6]}")
def summarize(u, p):
    d = results.get((u, p), {})
    out = {}
    for ch in ("A0", "A1", "A2"):
        ps = [x for x in d.get(ch, []) if x[0] is not None]
        if not ps: out[ch] = None; continue
        z = sum(x[0] for x in ps) / len(ps); out[ch] = z
    if any(out[c] is None for c in ("A0", "A1", "A2")): return out, None
    return out, out["A0"] + out["A1"] + out["A2"]

print(f"session {pathlib.Path(fn).name}: {len(recs)} records, {len(by_tag)} ASK windows")
passes = sorted({p for _, p in results})
curve = {}; rows = []
for u in rungs:
    sig = []; own = {"A0": [], "A1": [], "A2": []}
    for p in passes:
        out, S = summarize(u, p)
        if S is not None: sig.append(abs(S))
        for c in own:
            if out.get(c) is not None: own[c].append(abs(out[c]))
    curve[u] = st.median(sig) if sig else None
    rows.append((u, curve[u], {c: (round(st.median(v), 4) if v else None) for c, v in own.items()}, len(sig)))
vals = [v for v in curve.values() if v is not None]
if not vals: print("no complete windows yet"); sys.exit(0)
mx = max(vals)
print(f"\n  u(deg) | centroid |S| (norm) | A0 own | A1 own | A2 own | n | canon | EM-gnd")
xs, yc, ye = [], [], []
for u, S, own, n in rows:
    if S is None: print(f"  {u:6g} |    --            |"); continue
    print(f"  {u:6g} | {S:.4f} ({S/mx:.2f})   | {own['A0']} | {own['A1']} | {own['A2']} | {n} | {canon[f'{u:g}']:.2f} | {emg[f'{u:g}']:.2f}")
    xs.append(S / mx); yc.append(canon[f"{u:g}"]); ye.append(emg[f"{u:g}"])
def corr(a, b):
    ma, mb = st.mean(a), st.mean(b); sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")
cc, ce = corr(xs, yc), corr(xs, ye)
best_u = max((u for u in curve if curve[u] is not None), key=lambda u: curve[u]); min_u = min((u for u in curve if curve[u] is not None), key=lambda u: curve[u])
print(f"\n  measured centroid: MAX at u={best_u:g}, MIN at u={min_u:g}")
print(f"  correlation with canon column (null 0 / max 120): {cc:+.3f}")
print(f"  correlation with EM-ground column (max 0 / null 120): {ce:+.3f}")
print(f"  CENTROID: {'CANON' if cc > ce else 'PLAIN-SUM (EM-ground / no geometric phase)'} column fits better (delta {abs(cc-ce):.3f}); {len(xs)}/16 rungs measured, {len(passes)} pass(es)")
# --- per-coil tests: the accounts predict different things for the INDIVIDUAL runners ---
#   EM ground path (common-mode): all three runners read the SAME magnitude at each rung, all ∝ |Σ e^{-iuk}|
#   'each coil reads only its own drive': own magnitudes CONSTANT vs u
#   coupling through the others: own magnitudes vary with u and differ coil to coil
own_rows = [(u, own) for u, S, own, n in rows if S is not None and all(own[c] is not None for c in own)]
if len(own_rows) >= 3:
    spreads = [max(own.values()) / max(min(own.values()), 1e-4) for _, own in own_rows]
    print(f"\n  per-coil spread (max/min runner magnitude at the same rung): median {st.median(spreads):.1f}x, min {min(spreads):.1f}x -> common-mode (ground path) predicts ~1x")
    for c in ("A0", "A1", "A2"):
        v = [own[c] for _, own in own_rows]
        cv = st.pstdev(v) / st.mean(v) if st.mean(v) else float("nan")
        cu = corr([x / max(v) for x in v], [emg[f"{u:g}"] for u, _ in own_rows]) if len(v) >= 3 else float("nan")
        print(f"  {c} own magnitude vs rung: min {min(v):.4f} max {max(v):.4f} (x{max(v)/max(min(v),1e-4):.1f}), CV {cv:.2f} -> 'reads only itself' predicts CV~0; corr with plain-sum shape {cu:+.2f}")
# pass-to-pass reproducibility of the centroid magnitude
if len(passes) >= 2:
    rep = []
    for u in rungs:
        S1 = summarize(u, 1)[1]; S2 = summarize(u, 2)[1]
        if S1 is not None and S2 is not None: rep.append((u, abs(S1), abs(S2)))
    if rep:
        ratios = [b / a for _, a, b in rep if a]
        print(f"\n  pass 2 / pass 1 centroid ratio over {len(rep)} rungs: median {st.median(ratios):.3f}, min {min(ratios):.3f}, max {max(ratios):.3f}")
        print("   " + ", ".join(f"u={u:g}: {a:.3f}/{b:.3f}" for u, a, b in rep))
# centroid phase per rung, in pi/8 units, relative to the u=0 rung if measured
ph = {}
for u in rungs:
    S = [summarize(u, p)[1] for p in passes]; S = [s for s in S if s is not None]
    if S: ph[u] = math.degrees(cmath.phase(sum(S) / len(S))) % 360
if 0.0 in ph:
    print("\n  centroid phase (pi/8 units, relative to the u=0 rung): " + ", ".join(f"u={u:g}: {((ph[u]-ph[0.0]+180)%360-180)/22.5:+.2f}" for u in sorted(ph)))
