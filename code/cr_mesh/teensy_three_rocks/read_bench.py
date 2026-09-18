"""READ THE BENCH — one-scale reader for three-rocks session data.

Ingests a state_session_*.jsonl, applies ADC engine gains (calib_clock.py 2026-09-17),
puts every channel on the ADC0 scale, and writes two CSVs:
  1. read_bench_<ts>.csv  — every corrected data packet (open in Excel, filter by tag)
  2. read_bench_summary_<ts>.csv — per-tag-window medians with anchor ratios

ADC engine gains (measured): ADC1/ADC0 = 3.10 (A0), 3.05 (A1), 2.62 (A2).
Pair convention: C a b → SENSE_PINS[a] on ADC0, SENSE_PINS[b] on ADC1.
Only channels in the active pair are measured; the third is blank.

Usage: python read_bench.py [session.jsonl] [--anchor-tag OPEN]
"""
import json, math, sys, glob, pathlib, statistics as st, csv, time as _time
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
LIVE = 0.009
DROP = 2

GAIN = {0: 3.10, 1: 3.05, 2: 2.62}


def correct(ch, pair, raw_mag):
    if ch == pair[1]:
        return raw_mag / GAIN[ch]
    if ch == pair[0]:
        return raw_mag
    return None


def load(fn):
    return [json.loads(l) for l in open(fn, encoding="utf-8") if l.strip()]


def walk(recs):
    pair = None; since = 0; tag = ""
    for r in recs:
        if "tag_set" in r:
            tag = r["tag_set"]; continue
        if "cmd" in r:
            ack = r.get("ack") or ""
            if ack.startswith("R PAIR"):
                pair = [int(x) for x in ack.split()[2:4]]; since = 0
            elif ack.startswith("R MODE") or ack.startswith("R K") or ack.startswith("R U"):
                since = 0
            continue
        if "A0" not in r:
            continue
        since += 1
        p = pair or r.get("pair")
        if p is None or since <= DROP:
            continue
        row = {"t": r["t"], "tag": r.get("tag", tag), "f": r.get("f", 0),
               "pair": f"{p[0]},{p[1]}"}
        for ch in range(3):
            raw_m, raw_p = r[f"A{ch}"]
            cm = correct(ch, p, raw_m)
            row[f"A{ch}_mag"] = round(cm, 6) if cm is not None else ""
            row[f"A{ch}_phase"] = round(raw_p, 2) if cm is not None else ""
            row[f"A{ch}_measured"] = 1 if cm is not None else 0
        yield row


def anchor_meds(rows, tag_match):
    vals = {ch: [] for ch in range(3)}
    for r in rows:
        if tag_match not in r.get("tag", ""):
            continue
        for ch in range(3):
            m = r[f"A{ch}_mag"]
            if m != "" and m > LIVE:
                vals[ch].append(m)
    return {ch: (round(st.median(v), 6) if v else None) for ch, v in vals.items()}


def main():
    fn = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
          else max(glob.glob(str(DATA / "state_session_*.jsonl")),
                   key=lambda p: pathlib.Path(p).stat().st_mtime))
    atag = "OPEN"
    if "--anchor-tag" in sys.argv:
        atag = sys.argv[sys.argv.index("--anchor-tag") + 1]

    recs = load(fn)
    corrected = list(walk(recs))
    anc = anchor_meds(corrected, atag)
    ts = _time.strftime("%Y%m%d_%H%M%S")

    fields = ["timestamp_utc", "epoch_s", "tag", "freq_hz", "pair",
              "A0_mag", "A0_phase", "A0_measured",
              "A1_mag", "A1_phase", "A1_measured",
              "A2_mag", "A2_phase", "A2_measured"]
    csv_fn = DATA / f"read_bench_{ts}.csv"
    with open(csv_fn, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in corrected:
            utc = datetime.fromtimestamp(r["t"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow({"timestamp_utc": utc, "epoch_s": f"{r['t']:.2f}",
                         "tag": r["tag"], "freq_hz": r["f"], "pair": r["pair"],
                         "A0_mag": r["A0_mag"], "A0_phase": r["A0_phase"], "A0_measured": r["A0_measured"],
                         "A1_mag": r["A1_mag"], "A1_phase": r["A1_phase"], "A1_measured": r["A1_measured"],
                         "A2_mag": r["A2_mag"], "A2_phase": r["A2_phase"], "A2_measured": r["A2_measured"]})

    by_tag = {}
    for r in corrected:
        by_tag.setdefault(r["tag"], []).append(r)

    sum_fn = DATA / f"read_bench_summary_{ts}.csv"
    with open(sum_fn, "w", newline="", encoding="utf-8") as f:
        sw = csv.writer(f)
        sw.writerow(["tag", "n_packets", "freq_hz",
                      "A0_median", "A1_median", "A2_median",
                      "A0_over_anchor", "A1_over_anchor", "A2_over_anchor",
                      "A0_live_frac", "A1_live_frac", "A2_live_frac",
                      "A0_phase_median", "A1_phase_median", "A2_phase_median"])
        for tname in by_tag:
            rows = by_tag[tname]
            n = len(rows)
            freqs = [r["f"] for r in rows if r["f"]]
            freq = round(st.median(freqs), 1) if freqs else ""
            meds = {}; live_frac = {}; anc_r = {}; ph_med = {}
            for ch in range(3):
                vals = [r[f"A{ch}_mag"] for r in rows if r[f"A{ch}_mag"] != "" and r[f"A{ch}_mag"] > LIVE]
                phs = [r[f"A{ch}_phase"] for r in rows if r[f"A{ch}_phase"] != "" and r[f"A{ch}_mag"] != "" and r[f"A{ch}_mag"] > LIVE]
                meds[ch] = round(st.median(vals), 6) if vals else ""
                live_frac[ch] = round(len(vals) / n, 3) if n else 0
                anc_r[ch] = round(meds[ch] / anc[ch], 4) if meds[ch] != "" and anc.get(ch) else ""
                ph_med[ch] = round(st.median(phs), 2) if phs else ""
            sw.writerow([tname, n, freq,
                          meds[0], meds[1], meds[2],
                          anc_r[0], anc_r[1], anc_r[2],
                          live_frac[0], live_frac[1], live_frac[2],
                          ph_med[0], ph_med[1], ph_med[2]])

    print(f"Session: {pathlib.Path(fn).name}  ({len(corrected)} corrected packets)", flush=True)
    print(f"Anchor ('{atag}' tag, ADC0 scale):  A0 = {anc.get(0, '—')}   A1 = {anc.get(1, '—')}   A2 = {anc.get(2, '—')}", flush=True)
    print(flush=True)

    def fmt(v):
        return f"{v:.4f}" if isinstance(v, float) else "—"
    def fmtr(v):
        return f"{v:.3f}" if isinstance(v, float) else "—"

    print(f"{'tag':<60} {'n':>5} {'A0':>8} {'A1':>8} {'A2':>8} {'A0/anc':>7} {'A1/anc':>7} {'A2/anc':>7}", flush=True)
    print("-" * 120, flush=True)
    for tname in by_tag:
        rows = by_tag[tname]; n = len(rows)
        m = {}; ar = {}
        for ch in range(3):
            vals = [r[f"A{ch}_mag"] for r in rows if r[f"A{ch}_mag"] != "" and r[f"A{ch}_mag"] > LIVE]
            m[ch] = st.median(vals) if vals else None
            ar[ch] = m[ch] / anc[ch] if m[ch] and anc.get(ch) else None
        print(f"{tname[:60]:<60} {n:>5} {fmt(m[0]):>8} {fmt(m[1]):>8} {fmt(m[2]):>8} {fmtr(ar[0]):>7} {fmtr(ar[1]):>7} {fmtr(ar[2]):>7}", flush=True)

    print(f"\nWrote:\n  {csv_fn.name}\n  {sum_fn.name}", flush=True)


if __name__ == "__main__":
    main()
