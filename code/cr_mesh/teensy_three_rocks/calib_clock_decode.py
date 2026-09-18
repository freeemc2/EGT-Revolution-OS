"""Decode calib_clock.py: (A) ADC engine gains, (B) build-up clock vs frequency, (C) momentum gaps,
then (D) the mode-conservation check on the rung sweep with the gains applied.
Usage: python calib_clock_decode.py [session_jsonl]
"""
import json, math, sys, glob, pathlib, statistics as st, cmath
HERE = pathlib.Path(__file__).resolve().parent; DATA = HERE / "data"; LIVE = 0.009; DROP = 2
fn = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(str(DATA / "state_session_*.jsonl")), key=lambda p: pathlib.Path(p).stat().st_mtime)
recs = [json.loads(l) for l in open(fn, encoding="utf-8") if l.strip()]

# walk: windows keyed by tag occurrence; labels from acks; packets after DROP
wins = {}; order = []; cur = None; pair = None; since = 0; occ = {}
for r in recs:
    if "tag_set" in r:
        base = r["tag_set"]; occ[base] = occ.get(base, 0) + 1; cur = f"{base}#{occ[base]}"
        wins[cur] = {"base": base, "pair": None, "pk": [], "t0": r["t"], "cmds": []}; order.append(cur); since = 0; continue
    if "cmd" in r and cur:
        wins[cur]["cmds"].append((r["t"], r["cmd"], r.get("ack")))
        ack = r.get("ack") or ""
        if ack.startswith("R PAIR"):
            pair = tuple(int(x) for x in ack.split()[2:4]); wins[cur]["pair"] = pair; since = 0
        elif ack.startswith("R MODE") or ack.startswith("R K"): since = 0
        continue
    if "A0" in r and cur:
        since += 1
        if since <= DROP: continue
        wins[cur]["pk"].append(r)
def mag(r, ch): return float(r[f"A{ch}"][0])
def live_med(pk, ch):
    v = [mag(r, ch) for r in pk if mag(r, ch) > LIVE]; return (st.median(v) if v else 0.0), len(v), len(pk)

# ---- A. calibration ----
print("=== A. GAIN CALIBRATION (state A0@12 held; each channel on each engine) ===")
cal = {}   # ch -> {engine: (median, n, N)}
for k in order:
    w = wins[k]
    if not w["base"].startswith("CAL") or not w["pair"] or not w["pk"]: continue
    a, b = w["pair"]
    cal.setdefault(a, {})["ADC0"] = live_med(w["pk"], a); cal.setdefault(b, {})["ADC1"] = live_med(w["pk"], b)
    print(f"  {w['base']}: pair {w['pair']}: A{a}(ADC0) {live_med(w['pk'], a)[0]:.4f}  A{b}(ADC1) {live_med(w['pk'], b)[0]:.4f}  (live/total {live_med(w['pk'], a)[1]}/{live_med(w['pk'], a)[2]}, {live_med(w['pk'], b)[1]}/{live_med(w['pk'], b)[2]})")
gain = {}
for ch in (0, 1, 2):
    e = cal.get(ch, {})
    if "ADC0" in e and "ADC1" in e and e["ADC0"][0] > 0:
        gain[ch] = e["ADC1"][0] / e["ADC0"][0]
        print(f"  A{ch}: ADC0 {e['ADC0'][0]:.4f}  ADC1 {e['ADC1'][0]:.4f}  ratio ADC1/ADC0 = {gain[ch]:.3f}")
    else:
        print(f"  A{ch}: incomplete ({e})")
if gain:
    print(f"  engine factor (median over channels) = {st.median(gain.values()):.3f}; spread {min(gain.values()):.3f}-{max(gain.values()):.3f} (equal across channels -> engine; unequal -> sense chain x engine)")

# ---- B. clock vs frequency ----
print("\n=== B. BUILD-UP CLOCK vs FLOOR FREQUENCY (A0 gated, followers A1/A2 on pair (1,2)) ===")
clock = {}
for k in order:
    w = wins[k]; b = w["base"]
    if not b.startswith("CLOCK"): continue
    f = float(b.split("f=")[1].split()[0]); state = "ON" if " ON " in b else "OFF"; cyc = b.split("c")[-1]
    tL = next((t for t, c, _ in w["cmds"] if c.startswith("L ")), w["t0"])   # gate really starts when L is applied
    allpk = [r for r in recs if r.get("tag") == b and r.get("t", 0) >= tL and "A0" in r]
    row = {}
    for ch in (1, 2):
        lv = [(r["t"] - tL, mag(r, ch)) for r in allpk if mag(r, ch) > LIVE]
        if state == "ON":
            row[f"A{ch}"] = {"rise_s": round(lv[0][0], 1) if lv else None, "live_frac": round(len(lv) / max(len(allpk), 1), 2), "mag": round(st.median([m for _, m in lv]), 4) if lv else 0.0}
        else:
            row[f"A{ch}"] = {"decay_s": round(lv[-1][0], 1) if lv else 0.0, "live_frac": round(len(lv) / max(len(allpk), 1), 2)}
    clock[(f, state, cyc)] = row
    print(f"  f={f:g} Hz {state} c{cyc}: n={len(allpk)}  A1 {row['A1']}  A2 {row['A2']}")
rises = {}
for (f, s, c), row in clock.items():
    if s == "ON":
        for ch in ("A1", "A2"):
            if row[ch]["rise_s"] is not None: rises.setdefault(f, []).append(row[ch]["rise_s"])
if rises:
    print("  rise (s) by frequency: " + "; ".join(f"{f:g} Hz: {sorted(v)}" for f, v in sorted(rises.items())))

# ---- C. momentum ----
print("\n=== C. MOMENTUM: one-cycle leader gaps at 12 Hz ===")
for k in order:
    w = wins[k]; b = w["base"]
    if not b.startswith("MOM gap"): continue
    tM0 = next((t for t, c, _ in w["cmds"] if c == "M 0"), None); tM1 = next((t for t, c, _ in w["cmds"] if c == "M 1"), None)
    allpk = [r for r in recs if r.get("tag") == b and "A0" in r]
    if tM0 is None or tM1 is None: print(f"  {b}: commands not both acked"); continue
    seq = "".join(("L" if mag(r, 1) > LIVE or mag(r, 2) > LIVE else ".") for r in allpk)
    after = [r for r in allpk if r["t"] >= tM1]
    back = next((round(r["t"] - tM1, 1) for r in after if mag(r, 1) > LIVE and mag(r, 2) > LIVE), None)
    dark_during = sum(1 for r in allpk if tM0 <= r["t"] < tM1 and mag(r, 1) <= LIVE and mag(r, 2) <= LIVE)
    print(f"  {b}: gap = {tM1 - tM0:.1f} s (M0 -> M1); packets dark during gap: {dark_during}; both followers back {back} s after M1; sequence {seq}")

# ---- D. mode conservation on the rung sweep, gains applied ----
print("\n=== D. MODE CONSERVATION on the rung sweep (leader gain vs collective loss, one scale) ===")
try:
    from ask_rungs_decode import summarize, rungs, passes   # noqa (re-runs its decode on the same session)
except Exception as e:
    summarize = None; print("  rung decoder not importable:", e)
if summarize and gain:
    g1 = gain.get(1, 1.0); g2 = gain.get(2, 1.0)
    pts = []
    for u in rungs:
        S_list = []; A0_list = []
        for p in passes:
            out, S = summarize(u, p)
            if S is None: continue
            # A1 came from ADC1 in pair (0,1) and ADC0 in pair (1,2) (averaged); A2 from ADC1 only; A0 from ADC0 only.
            a1 = out["A1"] * (2.0 / (1.0 + g1)); a2 = out["A2"] / g2; a0 = out["A0"]
            S_list.append(abs(a0 + a1 + a2)); A0_list.append(abs(a0))
        if S_list: pts.append((u, st.median(S_list), st.median(A0_list)))
    if len(pts) >= 5:
        xs = [s for _, s, _ in pts]; ys = [a for _, _, a in pts]
        mx, my = st.mean(xs), st.mean(ys); sxx = sum((x - mx) ** 2 for x in xs); sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        slope = sxy / sxx if sxx else float("nan"); r = sxy / math.sqrt(sxx * sum((y - my) ** 2 for y in ys)) if sxx else float("nan")
        print(f"  {len(pts)} rungs: A0 = {my - slope*mx:.4f} + ({slope:+.3f}) x |Sigma|, corr {r:+.3f}")
        print("  " + ", ".join(f"u={u:g}: |S| {s:.3f} A0 {a:.3f}" for u, s, a in pts))
        print("  read: slope < 0 with |corr| near 1 = the leader carries what the collective loses at a fixed ratio (mode exchange); |corr| small = no fixed exchange")
    else:
        print("  not enough rung points")
