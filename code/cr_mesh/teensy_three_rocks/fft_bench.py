"""FFT of three-rocks bench data — Lomb-Scargle periodogram to CSV.

Unevenly sampled (~5 s packets with gaps), so standard FFT does not apply.
Lomb-Scargle handles the gaps correctly. Outputs a CSV Brian can open and
plot in Excel: frequency_Hz, period_s, power per channel, plus FAP (false
alarm probability) at the 1% level for reference.

ADC gains applied (calib_clock.py 2026-09-17): ADC1/ADC0 = 3.10/3.05/2.62.

Usage: python fft_bench.py [session.jsonl] [--tag OPEN] [--min-period 10] [--max-period 7200] [--n-freqs 500]
"""
import json, math, sys, glob, pathlib, csv, time as _time

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
LIVE = 0.009
DROP = 2
GAIN = {0: 3.10, 1: 3.05, 2: 2.62}

try:
    import numpy as _np
    HAS_NP = True
except ImportError:
    HAS_NP = False


def correct(ch, pair, raw_mag):
    if ch == pair[1]:
        return raw_mag / GAIN[ch]
    if ch == pair[0]:
        return raw_mag
    return None


def load(fn):
    return [json.loads(l) for l in open(fn, encoding="utf-8") if l.strip()]


def extract_series(recs, tag_filter=None):
    series = {ch: {"t": [], "m": []} for ch in range(3)}
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
        rtag = r.get("tag", tag)
        if tag_filter and tag_filter not in rtag:
            continue
        for ch in range(3):
            cm = correct(ch, p, r[f"A{ch}"][0])
            if cm is not None and cm > LIVE:
                series[ch]["t"].append(r["t"])
                series[ch]["m"].append(cm)
    return series


def lomb_scargle_np(times, values, freqs):
    t = _np.asarray(times)
    y = _np.asarray(values)
    y = y - _np.mean(y)
    var_y = _np.var(y)
    if var_y < 1e-20:
        return _np.zeros(len(freqs))
    power = _np.empty(len(freqs))
    for i, f in enumerate(freqs):
        w = 2.0 * _np.pi * f
        wt = w * t
        tau = _np.arctan2(_np.sum(_np.sin(2.0 * wt)),
                          _np.sum(_np.cos(2.0 * wt))) / (2.0 * w)
        d = w * (t - tau)
        cos_d = _np.cos(d)
        sin_d = _np.sin(d)
        yc = _np.sum(y * cos_d)
        ys = _np.sum(y * sin_d)
        cc = _np.sum(cos_d ** 2)
        ss = _np.sum(sin_d ** 2)
        power[i] = (yc * yc / cc + ys * ys / ss) / (2.0 * var_y) if cc > 0 and ss > 0 else 0
    return power


def lomb_scargle_py(times, values, freqs):
    N = len(times)
    mean_y = sum(values) / N
    y = [v - mean_y for v in values]
    var_y = sum(v * v for v in y) / N
    if var_y < 1e-20:
        return [0.0] * len(freqs)
    power = []
    for f in freqs:
        w = 2.0 * math.pi * f
        s2 = sum(math.sin(2.0 * w * t) for t in times)
        c2 = sum(math.cos(2.0 * w * t) for t in times)
        tau = math.atan2(s2, c2) / (2.0 * w) if w > 0 else 0
        cos_t = [math.cos(w * (t - tau)) for t in times]
        sin_t = [math.sin(w * (t - tau)) for t in times]
        yc = sum(yi * ci for yi, ci in zip(y, cos_t))
        ys = sum(yi * si for yi, si in zip(y, sin_t))
        cc = sum(ci * ci for ci in cos_t)
        ss = sum(si * si for si in sin_t)
        power.append((yc * yc / cc + ys * ys / ss) / (2.0 * var_y) if cc > 0 and ss > 0 else 0)
    return power


def lomb_scargle(times, values, freqs):
    if HAS_NP:
        return lomb_scargle_np(times, values, freqs)
    return lomb_scargle_py(times, values, freqs)


def fap_threshold(n_points, n_freqs, p=0.01):
    """Approximate false-alarm probability threshold (Baluev 2008 upper bound)."""
    if n_points < 4:
        return float("inf")
    z = -math.log(1.0 - (1.0 - p) ** (1.0 / n_freqs))
    return z


def arg(name, default, cast=float):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    fn = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
          else max(glob.glob(str(DATA / "state_session_*.jsonl")),
                   key=lambda p: pathlib.Path(p).stat().st_mtime))
    tag_filter = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else None
    min_period = arg("--min-period", 10.0)
    max_period = arg("--max-period", 7200.0)
    n_freqs = arg("--n-freqs", 500, int)

    print(f"Loading {pathlib.Path(fn).name}...", flush=True)
    recs = load(fn)
    series = extract_series(recs, tag_filter)

    f_min = 1.0 / max_period
    f_max = 1.0 / min_period
    freqs = [f_min * (f_max / f_min) ** (i / max(n_freqs - 1, 1)) for i in range(n_freqs)]

    powers = {}
    fap_thresh = {}
    for ch in range(3):
        n = len(series[ch]["t"])
        if n >= 10:
            span = (series[ch]["t"][-1] - series[ch]["t"][0]) / 3600
            print(f"A{ch}: {n} live points, span {span:.1f} h — computing Lomb-Scargle...", flush=True)
            powers[ch] = lomb_scargle(series[ch]["t"], series[ch]["m"], freqs)
            fap_thresh[ch] = fap_threshold(n, n_freqs)
        else:
            print(f"A{ch}: only {n} points — skipping", flush=True)
            powers[ch] = [0.0] * n_freqs
            fap_thresh[ch] = float("inf")

    ts = _time.strftime("%Y%m%d_%H%M%S")
    tag_suffix = f"_{tag_filter.replace(' ', '_')}" if tag_filter else ""
    csv_fn = DATA / f"fft_bench{tag_suffix}_{ts}.csv"
    with open(csv_fn, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["frequency_Hz", "period_s",
                     "power_A0", "power_A1", "power_A2",
                     "above_1pct_FAP_A0", "above_1pct_FAP_A1", "above_1pct_FAP_A2"])
        for i, freq in enumerate(freqs):
            w.writerow([f"{freq:.8f}", f"{1.0 / freq:.2f}",
                         f"{powers[0][i]:.6f}", f"{powers[1][i]:.6f}", f"{powers[2][i]:.6f}",
                         1 if powers[0][i] > fap_thresh.get(0, float("inf")) else 0,
                         1 if powers[1][i] > fap_thresh.get(1, float("inf")) else 0,
                         1 if powers[2][i] > fap_thresh.get(2, float("inf")) else 0])

    print(f"\nFAP threshold (1%): A0 = {fap_thresh.get(0, '—'):.2f}  A1 = {fap_thresh.get(1, '—'):.2f}  A2 = {fap_thresh.get(2, '—'):.2f}", flush=True)
    for ch in range(3):
        if max(powers[ch]) > 0:
            pk = sorted(range(len(freqs)), key=lambda i, c=ch: powers[c][i], reverse=True)[:5]
            above = sum(1 for p in powers[ch] if p > fap_thresh.get(ch, float("inf")))
            print(f"A{ch} top 5 periods: " + ", ".join(
                f"{1.0 / freqs[i]:.1f}s (power {powers[ch][i]:.2f}{'*' if powers[ch][i] > fap_thresh.get(ch, float('inf')) else ''})"
                for i in pk), flush=True)
            print(f"  {above} frequencies above 1% FAP", flush=True)

    print(f"\nWrote: {csv_fn.name}", flush=True)


if __name__ == "__main__":
    main()
