#!/usr/bin/env python3
"""
CHANNEL HEALTH CHECK — is a three-rocks coupling matrix trustworthy BEFORE you
eigendecompose it?

Reads a rods_<label>.json produced by measure_rods.py and grades each SENSE
channel (runner A0/A1/A2) with the diagonal-dominance test. Built 2026-09-15
after the 3-coil eigenmode came out soft: the measured matrix had one dead
sense channel and one common-mode sense channel, so the per-coil (per-ROW)
normalization the analysis leaned on was papering over per-CHANNEL (per-COLUMN)
wiring artifacts — which is exactly the "normalization artifact" attack a
reviewer lands on. You cannot normalize away a dead runner. Fix the channels
first; then the raw matrix is diagonal-dominant and the 2C/-C eigenmode ratio
survives without a rescue normalization.

What it grades (per frequency, per sense channel = COLUMN of the matrix):
  drive coil -> sense runner, self-response = diagonal (coil into its OWN runner).
  Mapping from WIRING.md:  coil1<->A0,  coil2<->A1,  coil3<->A2.

  HEALTHY      self is the column max AND self >= DOM x (mean of the off-diagonal
               entries in the column) AND self >= HEALTH_MULT x floor.
               -> real geometric coupling, own coil strongest.
  COMMON-MODE  not dead, but the column is flat (all drives read ~equal) or the
               diagonal is not the clear max -> a shared/return signal, not
               coupling. No diagonal to normalize to.
  DEAD         the whole column sits near the floor (< DEAD_MULT x floor) ->
               the runner is not sensing (out of bore, open/high-Z lead, or an
               ADC left in continuous mode reading a dead floor).

Matrix verdict = PASS only when all three channels are HEALTHY and the three
self-responses are within SYM x of each other (a near-symmetric, circulant-
ready matrix). Otherwise FAIL, naming the offending channels — do NOT run the
eigenmode on a FAIL matrix.

Usage:
  python channel_health.py [rods_<label>.json] [--freq 7878] [--json]
Defaults to rods_norods_3coils.json, all frequencies, human-readable output.
Exit code 0 = PASS, 1 = FAIL, 2 = bad input. Stdlib only.
"""
import json, os, sys

# --- grading thresholds (grounded in WIRING.md: floor ~0.004, a coupled coil
#     reads 0.05-0.3 = 10-55x floor, a runner out of the bore falls to floor) ---
DEAD_MULT   = 6.0    # column max below this x floor -> DEAD (runner not sensing)
HEALTH_MULT = 6.0    # self below this x floor -> too weak to trust
DOM         = 1.30   # self must beat the mean off-diagonal by this factor
FLAT_FRAC   = 0.25   # (max-min)/mean below this across drives -> COMMON-MODE (flat)
SYM         = 2.0    # max(self)/min(self) above this -> matrix not symmetric enough

# WIRING.md pin map: drive pin -> (coil label, its own sense runner)
DRIVES = [("pin2", "coil1", "A0"), ("pin3", "coil2", "A1"), ("pin1", "coil3", "A2")]
RUNNERS = ["A0", "A1", "A2"]


def _cell(rec, floor, runner):
    """Floor-subtracted response for one sense runner, clamped at 0."""
    return max(0.0, rec.get(runner, 0.0) - floor.get(runner, 0.0))


def grade_channel(sense, self_val, off_vals, floor_raw, col_raw):
    """Grade one sense channel (column). Returns (verdict, reason)."""
    col_max = max(col_raw)
    if col_max < DEAD_MULT * floor_raw:
        return "DEAD", (f"column max {col_max:.3f} < {DEAD_MULT:.0f}x floor "
                        f"({floor_raw:.3f}) — runner not sensing")
    off_mean = sum(off_vals) / len(off_vals) if off_vals else 0.0
    spread_mean = sum(col_raw) / len(col_raw)
    flat = spread_mean > 0 and (max(col_raw) - min(col_raw)) / spread_mean < FLAT_FRAC
    if flat:
        return "COMMON-MODE", (f"column flat ((max-min)/mean "
                               f"{(max(col_raw)-min(col_raw))/spread_mean:.2f} < {FLAT_FRAC}) "
                               f"— shared signal, no diagonal to trust")
    if self_val < max(off_vals if off_vals else [0.0]):
        return "COMMON-MODE", (f"self {self_val:.3f} is not the column max "
                               f"(off-diagonal {max(off_vals):.3f} larger) — coupling inverted")
    if off_mean > 0 and self_val < DOM * off_mean:
        return "COMMON-MODE", (f"self {self_val:.3f} < {DOM}x mean-off {off_mean:.3f} "
                               f"— weak diagonal dominance")
    if self_val < HEALTH_MULT * floor_raw:
        return "COMMON-MODE", (f"self {self_val:.3f} < {HEALTH_MULT:.0f}x floor "
                               f"({floor_raw:.3f}) — too weak to trust")
    return "HEALTHY", (f"self {self_val:.3f} dominates (mean-off {off_mean:.3f}, "
                       f"{self_val/off_mean:.1f}x)" if off_mean > 0 else
                       f"self {self_val:.3f} dominates")


def analyze_freq(freq, reads, floor):
    """Grade all three channels at one frequency. Returns (passed, rows, selfs)."""
    # matrix[drive_index][sense_runner] floor-subtracted
    M = {}
    for pin, coil, _ in DRIVES:
        rec = reads.get(f"{freq}:{pin}")
        if rec is None:
            return None, [], {}
        M[coil] = {r: _cell(rec, floor, r) for r in RUNNERS}
    rows, selfs = [], {}
    passed = True
    for pin, coil, sense in DRIVES:
        self_val = M[coil][sense]
        off_vals = [M[c][sense] for _, c, _ in DRIVES if c != coil]
        col_raw = [reads[f"{freq}:{p}"][sense] for p, _, _ in DRIVES]  # raw, not floor-sub
        verdict, reason = grade_channel(sense, self_val, off_vals, floor.get(sense, 0.0), col_raw)
        rows.append((sense, coil, self_val, off_vals, verdict, reason))
        selfs[sense] = self_val
        if verdict != "HEALTHY":
            passed = False
    # symmetry check across healthy self-responses
    sym_ok = True
    healthy_selfs = [s for (_, _, s, _, v, _) in rows if v == "HEALTHY" and s > 0]
    if len(healthy_selfs) >= 2:
        if max(healthy_selfs) / min(healthy_selfs) > SYM:
            sym_ok = False
    return (passed and sym_ok and len(healthy_selfs) == 3), rows, selfs


def main():
    args = [a for a in sys.argv[1:]]
    as_json = "--json" in args
    if as_json:
        args.remove("--json")
    only_freq = None
    if "--freq" in args:
        i = args.index("--freq"); only_freq = args[i + 1]; del args[i:i + 2]
    here = os.path.dirname(os.path.abspath(__file__))
    name = args[0] if args else "rods_norods_3coils.json"
    # measure_rods.py writes fresh runs next to the script; the reference sets
    # live in data/. Try the given path, then here/, then here/data/.
    candidates = [name, os.path.join(here, name), os.path.join(here, "data", name)]
    path = next((p for p in candidates if os.path.exists(p)), name)
    try:
        d = json.load(open(path))
    except Exception as e:
        print(f"cannot read {name} (looked in ./, {here}/, {here}/data/): {e}",
              file=sys.stderr); return 2

    reads, floors = d.get("reads", {}), d.get("floor", {})
    freqs = [only_freq] if only_freq else sorted(floors.keys(), key=lambda x: int(x))
    results, overall_pass = {}, True
    for f in freqs:
        floor = floors.get(f)
        if floor is None:
            continue
        passed, rows, selfs = analyze_freq(f, reads, floor)
        if passed is None:
            continue
        results[f] = {"pass": passed,
                      "channels": {s: {"coil": c, "self": round(sv, 4),
                                       "verdict": v, "reason": r}
                                   for (s, c, sv, _o, v, r) in rows},
                      "self_responses": {s: round(v, 4) for s, v in selfs.items()}}
        if not passed:
            overall_pass = False

    if as_json:
        print(json.dumps({"file": os.path.basename(path), "label": d.get("label"),
                          "overall_pass": overall_pass, "per_freq": results}, indent=1))
        return 0 if overall_pass else 1

    print(f"CHANNEL HEALTH — {os.path.basename(path)}  (label: {d.get('label')})")
    print("mapping: coil1<->A0  coil2<->A1  coil3<->A2   (self = coil into its own runner)\n")
    for f, res in results.items():
        tag = "PASS" if res["pass"] else "FAIL"
        print(f"=== {f} Hz ===  [{tag}]")
        for s in RUNNERS:
            ch = res["channels"].get(s)
            if not ch:
                continue
            print(f"  {s} ({ch['coil']}): {ch['verdict']:<11} self={ch['self']:.3f}  — {ch['reason']}")
        sr = res["self_responses"]
        vals = [v for v in sr.values() if v > 0]
        if len(vals) >= 2:
            print(f"  self-response spread: max/min = {max(vals)/min(vals):.2f}x "
                  f"(need <= {SYM}x for a symmetric matrix)")
        print()
    print(f"OVERALL: {'PASS — matrix is diagonal-dominant, eigendecompose the RAW matrix' if overall_pass else 'FAIL — fix the flagged channel(s) before running the eigenmode; do NOT rescue with per-coil normalization'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
