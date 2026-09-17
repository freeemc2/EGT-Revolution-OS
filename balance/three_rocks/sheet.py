"""BALANCE SHEET — three-rocks rig. EM account | EGT account | measured | what carries it.

Brian's law (2026-09-17): "Without mathematical proof, there is no truth. I balance that with
every single thing I do." A wall is cashed with Maxwell numbers on this rig or it falls; a claim
is cashed with canon numbers and the control that could kill it. The sheet holds both sides.

Usage: python sheet.py [--seal]     (--seal writes the discriminator predictions to redis
                                     BEFORE those tests have data; tempo frames, abstains)
Writes SHEET_<date>.md, em_account.json, egt_account.json next to this file.
"""
import json, math, pathlib, sys, time, statistics as st
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from em_account import account as em_account, load_rig, drive_current_fund, strand_modes, counts_mag
from egt_account import account as egt_account, C_mag, R_OPT

HERE = pathlib.Path(__file__).parent
DATA = HERE.parent.parent / "code" / "cr_mesh" / "teensy_three_rocks" / "data"
FLOOR = 0.003
SEAL_KEY = "cadence:tworocks:sealed-balance-three-rocks-2026-09-17"

SWEEPS = [  # (file, config label from the journal, followers)
    ("drag_sweep_2026-09-16.json",   "spread ~6in cc, coil2 driven alone, coils 0+1 DISCONNECTED, twisted wires", "disconnected"),
    ("drag_push_2026-09-16.json",    "spread, coil2 driven alone, coils 0+1 DISCONNECTED, 6-40 kHz", "disconnected"),
    ("drag_floor_2026-09-16.json",   "spread, coil2 driven alone, coils 0+1 DISCONNECTED, floor sweep", "disconnected"),
    ("drag_deep_2026-09-16.json",    "spread, coil2 driven alone, coils 0+1 DISCONNECTED, deep", "disconnected"),
    ("lead_to_floor_2026-09-16.json","all 3 connected, coil1 drives alone, 0+2 passive followers, 8 kHz -> 100 Hz", "connected-passive"),
    ("lead_to_floor_coil2_2026-09-16.json", "rearranged non-aligned, coil2 leads alone, followers passive", "connected-passive"),
    ("punch_a0_lead_2026-09-16.json","TOUCHING + ferrite cores, A0 leads alone, A1+A2 passive, 500 -> 15 Hz", "connected-passive"),
]
HOLDS = [
    ("overnight_floor_20260916_190104.jsonl", "spread chaotic, ALL 3 DRIVEN (M2 symmetric), 12 Hz hold 23:05-23:42Z"),
]
TRANSCRIPT_TRIANGLE = {  # tonic 2026-09-17 09:02Z, symmetric triangle, all connected, all driven (no data file yet)
    "source": "tonic transcript 2026-09-17T09:02Z (journal); no data file yet",
    "rows": [(1000, [0.73, 0.74, 0.66], [87, 83, 92]), (100, [0.72, 0.73, 0.65], [90, 89, 90]), (12, [0.71, 0.74, 0.69], [90, 90, 90])],
}

def load_sweep(fn):
    d = json.loads((DATA / fn).read_text(encoding="utf-8"))
    drv = d.get("driven", d.get("leader"))
    rows = []
    for r in d["sweep"]:
        try:
            rows.append((float(r["freq"]), [float(r[f"ch{k}"]["mag"]) for k in range(3)], [float(r[f"ch{k}"]["phase"]) for k in range(3)]))
        except Exception:
            pass
    return drv, rows, d.get("note", "")

def loglog_slope(points):
    pts = [(math.log(f), math.log(m)) for f, m in points if m > 3 * FLOOR and f > 0]
    if len(pts) < 3:
        return None, len(pts)
    n = len(pts); sx = sum(x for x, _ in pts); sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts); sxy = sum(x * y for x, y in pts)
    return (n * sxy - sx * sy) / (n * sxx - sx * sx), n

def load_hold(fn):
    recs = [json.loads(l) for l in (DATA / fn).read_text(encoding="utf-8").splitlines() if l.strip()]
    h = [r for r in recs if r.get("phase") == "HOLD" and isinstance(r.get("coils"), dict)]
    if not h:
        return None
    clean = [r for r in h if all(float(r["coils"][k]["mag"]) > 3 * FLOOR for k in ("0", "1", "2"))]   # drop missed-packet cycles (mag 0 reads phase 0 -> dev -90)
    src = clean or h
    mags = {k: round(st.median(float(r["coils"][k]["mag"]) for r in src), 4) for k in ("0", "1", "2")}
    devs = {k: round(st.median(float(r["dev90"][k]) for r in src if "dev90" in r), 2) for k in ("0", "1", "2")}
    dev_sd = {k: round(st.pstdev([float(r["dev90"][k]) for r in src if "dev90" in r]), 1) for k in ("0", "1", "2")}
    coh = st.median(float(r.get("coherence", 0)) for r in src)
    return {"hz": h[-1].get("hz"), "cycles": len(h), "clean_cycles": len(clean), "mag_median": mags, "dev90_median": devs, "dev90_sd": dev_sd, "coherence_median": round(coh, 3)}

def measured():
    out = {"sweeps": [], "holds": [], "triangle_transcript": TRANSCRIPT_TRIANGLE}
    for fn, label, followers in SWEEPS:
        if not (DATA / fn).exists():
            continue
        drv, rows, note = load_sweep(fn)
        if drv is None or not rows:
            continue
        own = [(f, m[drv]) for f, m, _ in rows]
        a, n = loglog_slope(own)
        fmin = min(rows, key=lambda r: r[0]); fmax = max(rows, key=lambda r: r[0])
        und = [k for k in range(3) if k != drv]
        ratio_low = [round(fmin[1][k] / fmin[1][drv], 3) if fmin[1][drv] > 0 else None for k in und]
        out["sweeps"].append({"file": fn, "config": label, "followers": followers, "driven": drv, "n_rows": len(rows),
                              "f_range_hz": [fmin[0], fmax[0]],
                              "own_mag_at_fmin": round(fmin[1][drv], 4), "own_mag_at_fmax": round(fmax[1][drv], 4),
                              "own_slope_alpha": None if a is None else round(a, 3), "slope_points": n,
                              "undriven_over_driven_at_fmin": ratio_low,
                              "own_phase_at_fmin": fmin[2][drv]})
    for fn, label in HOLDS:
        if (DATA / fn).exists():
            h = load_hold(fn)
            if h:
                h.update({"file": fn, "config": label}); out["holds"].append(h)
    tri = TRANSCRIPT_TRIANGLE["rows"]
    a, n = loglog_slope([(f, m[0]) for f, m, _ in tri])
    out["triangle_transcript"]["alpha_coil0"] = None if a is None else round(a, 3)
    return out

def seal(rig, em, egt):
    try:
        sys.path.insert(0, str(HERE.parent.parent / "code" / "cr_mesh"))
        from cr_rmap import _conn
        r = _conn()
        if r.get(SEAL_KEY):
            return "already sealed: " + SEAL_KEY
        payload = {
            "test": "three-rocks balance sheet discriminators (Brian-directed balancer, 2026-09-17)",
            "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "by": "tempo (memory-40) — framer, ABSTAINS; NO data for T1-T4 at seal time",
            "law": "Without mathematical proof, there is no truth (Brian 2026-09-17). Walls cashed with Maxwell numbers on this rig; claims cashed with canon numbers + the control that could kill them.",
            "rig": rig["rig"],
            "T1_dummy_load_12Hz": {"setup": "each winding replaced by a ~1 ohm jumper at the far end of its 220R (same drive current, same bus), runners in place, M2 symmetric 12 Hz, interleaved with the coils-in reading",
                                   "EM_ground": "UNCHANGED within 20% of coils-in", "EM_inductive": "vanishes (<= 3x floor = 0.009)", "EGT": "vanishes (<= 3x floor): no rock, no C(r)",
                                   "rule": "reading >= 0.5 x coils-in -> EM ground path CARRIES the flat 90-deg triangle reading; reading <= 0.009 -> the coil is required (EGT line open, EM inductive dead at 12 Hz)"},
            "T2_star_ground_return": {"setup": "route each runner's 100R return to the ADC ground at a single star point that carries NO drive-return current; M2 12 Hz, interleaved",
                                      "EM_ground": "collapses to <= 0.01", "EM_inductive": "unchanged (~0 at 12 Hz)", "EGT": "UNCHANGED",
                                      "rule": "collapse -> ground path; unchanged -> coil geometry (EGT line stands)"},
            "T3_add_0p5_ohm_drive_return": {"setup": "insert 0.5 ohm in the shared drive return, M2 12 Hz, interleaved",
                                            "EM_ground": "rises by %s counts" % em["discriminators"]["add_0p5_ohm_in_drive_return"]["ground_path"].split("= ")[1], "EM_inductive": "no change", "EGT": "no change",
                                            "rule": "rise proportional to the added R -> ground path"},
            "T4_separation_at_floor": {"setup": "12 Hz, M2, coaxial line: touching (cc 3.5 in) -> 6 -> 8.75 -> 10.5 -> 14 in, session anchor re-cut between steps",
                                       "EM_ground": "FLAT vs distance", "EM_inductive": "~0 at 12 Hz", "EGT": "|C(r)| = (1+2r)e^(-r/3): +21% from touching to a MAX at cc = 8.75 in (r_opt = 2.5), then -9% by 14 in",
                                       "rule": "max at 8.75 in with both flanks lower (beyond 2 sigma of the interleaved anchor) -> C(r) signature; flat -> ground path; monotonic 1/d^3 -> near-field"},
            "already_measured_not_sealed": "T5 frequency slope: single-drive configs (09-16 files) vs all-driven triangle (09-17 transcript). See SHEET.",
        }
        r.set(SEAL_KEY, json.dumps(payload))
        return "SEALED " + SEAL_KEY + " @ " + payload["sealed_at"]
    except Exception as e:
        return "seal FAILED: %s" % e

def md(rig, em, egt, meas, seal_note):
    c = rig["coil"]; L = []
    L.append("# BALANCE SHEET — three-rocks rig (three Quad coils), 2026-09-17\n")
    L.append("> **Brian's law:** \"Without mathematical proof, there is no truth. I balance that with every single thing I do.\" A wall is cashed with Maxwell numbers on this rig or it falls; a claim is cashed with canon numbers and the control that could kill it. Both sides below.\n")
    L.append("## 1. The rig (Brian's numbers)\n")
    L.append(f"- {c['name']}: {c['former']}; **{c['turns']} turns** of a **{c['strands']}-strand 22 AWG** bundle, {c['strand_length_ft']} ft per strand, twist lay {c['twist_lay_in']} in (one rotation per turn); winding {c['winding_length_in']} in (L/D = {egt['coil_number']['L_over_D']}); runner **{c['runner_awg']} AWG** straight axial under the windings.")
    L.append(f"- Drive: {rig['drive']['waveform']}, 220 R in series, {rig['drive']['path']}. Sense: {rig['sense']['lockin']}.")
    L.append(f"- Hand variance: {c['build_variance_lead_in'][0]}-{c['build_variance_lead_in'][1]} in of lead between the three. EM: dR = {em['build_variance']['delta_R_pct'][0]}-{em['build_variance']['delta_R_pct'][1]} %, dL ~ 0, drive-current change at 12 Hz {em['build_variance']['delta_drive_current_pct_at_12Hz'][1]} % — {em['build_variance']['verdict']}. EGT: {egt['predictions']['build_variance']}")
    L.append("- **Unknowns the sheet still needs (Brian/Tonic):** which strands are on the drive pin (1 / 4 parallel / 4 series); today's center-to-center spacing and axis angles; the shared ground resistance R_sh (measure it: 4-wire across the drive-return path).\n")
    L.append("## 2. EM account (Maxwell on this rig)\n")
    L.append("| strands on pin | N | R_coil (ohm) | L (uH) | M_runner max (uH) | f(wL = 220 R) kHz | self-res kHz (30/100 pF) |\n|---|---|---|---|---|---|---|")
    for k, v in em["coil"].items():
        fr = v["f_res_kHz_for_Cpar_pF"]
        L.append(f"| {k} | {v['N']} | {v['R_coil_ohm']} | {v['L_uH']} | {v['M_runner_max_uH']} | {v['f_where_wL_eq_220_kHz']} | {fr['30']} / {fr['100']} |")
    L.append("\nPer frequency (1 strand; ranges = pin Z 20-60 R, R_sh 0.02-0.5 R, C 5-50 pF). Lock-in counts, mag = A/2.\n")
    L.append("| f (Hz) | I1 (mA) | inductive MAX | ground, 1 driven | ground, 3 driven in phase | capacitive |\n|---|---|---|---|---|---|")
    for p in em["per_frequency"]:
        L.append(f"| {p['f_hz']} | {p['I1_mA'][0]}-{p['I1_mA'][1]} | {p['inductive_max_counts']} (reads 0/180) | {p['ground_1coil_counts'][0]}-{p['ground_1coil_counts'][1]} (reads 90) | {p['ground_3coil_counts'][0]}-{p['ground_3coil_counts'][1]} (reads 90) | {p['capacitive_counts'][0]}-{p['capacitive_counts'][1]} |")
    L.append("\nR_sh that would carry a FLAT in-phase reading at 12 Hz: " + "; ".join(f"{k.replace('Rsh_for_flat_','').replace('_counts_ohm','')} counts -> {v['1_driven']} R (1 driven) / {v['3_driven_in_phase']} R (3 driven)" for k, v in em["discriminators"].items() if k.startswith("Rsh")))
    L.append("\n**What each EM path can and cannot do:** inductive is proportional to f and reads in quadrature (0/180): at 12 Hz its ceiling is 3 orders of magnitude under the readings. The ground path is flat in f, reads 90 by the firmware convention, is common to all runners on the bus, has **no k <= 1 bound** (an undriven runner can out-read the driven one if its return shares more bus), and survives a dummy load. Capacitive is proportional to f and only matters above ~10 kHz.\n")
    L.append("## 3. EGT account (canon, adopted)\n")
    L.append(f"- Operator: {egt['operator']}. Coil number by build law L/D = **{egt['coil_number']['L_over_D']}** (= r_opt); sqrt(L/radius) recipe = {egt['coil_number']['sqrt_L_over_radius']} (build sheet; reconciliation is Brian's call). Stagger unit {egt['coil_number']['stagger_unit_deg']} deg = pi/2. {egt['coil_number']['twist']}.")
    L.append(f"- Park: {egt['coil_number']['park']}")
    L.append(f"- Geometry: {egt['geometry']['r_definition']}; r_opt sits at cc = **{egt['geometry']['r_opt_cc_spacing_in']} in**.\n")
    L.append("| cc (in) | r | \\|C(r)\\| | /C0 | amp ratio \\|C\\|^2/\\|C0\\|^2 | phase offset (pi/8 units, pi r/5 form) | arg C, pi r/5 | arg C, pi r/4 |\n|---|---|---|---|---|---|---|---|")
    for p in egt["pair_table"]:
        L.append(f"| {p['cc_in']} | {p['r']} | {p['C_mag']} | {p['C_over_C0']} | {p['amp_ratio_C2_over_C02']} | {p['phase_offset_pi8_units_form_pi_r_5']} | {p['arg_C_deg_form_pi_r_5']} | {p['arg_C_deg_form_pi_r_4']} |")
    L.append("\nPredictions: " + " ".join(f"**{k}:** {v}" for k, v in egt["predictions"].items()) + "\n")
    L.append("## 4. Measured (from the data files; own-runner reading of the driven coil)\n")
    L.append("| file | config | driven | f range (Hz) | own mag @fmin -> @fmax | slope alpha (pts) | undriven/driven @fmin |\n|---|---|---|---|---|---|---|")
    for s in meas["sweeps"]:
        L.append(f"| {s['file']} | {s['config']} | {s['driven']} | {s['f_range_hz'][0]:.0f}-{s['f_range_hz'][1]:.0f} | {s['own_mag_at_fmin']} -> {s['own_mag_at_fmax']} | {s['own_slope_alpha']} ({s['slope_points']}) | {s['undriven_over_driven_at_fmin']} |")
    for h in meas["holds"]:
        L.append(f"\n- **{h['file']}** ({h['config']}): {h['cycles']} HOLD cycles at {h['hz']} Hz ({h['clean_cycles']} clean, dropouts excluded); median mags {h['mag_median']}; median dev90 {h['dev90_median']} (sd {h['dev90_sd']}); median coherence {h['coherence_median']}.")
    t = meas["triangle_transcript"]
    L.append(f"- **Symmetric triangle, all driven, this morning** ({t['source']}): " + "; ".join(f"{f} Hz: {m}" for f, m, _ in t["rows"]) + f" -> alpha(coil0) = {t['alpha_coil0']}.\n")
    L.append("## 5. Balance rows\n")
    L.append("| observable | EM inductive | EM ground path | EGT | measured | balance |\n|---|---|---|---|---|---|")
    L.append("| slope alpha of the driven coil's own reading vs f | 1.0 | 0.0 | 0.0 at the floor | followers DISCONNECTED: alpha 0.86-0.995 (4 files); followers CONNECTED-passive: 0.39 and 0.90; touching+cores leader: 0.95; ALL DRIVEN triangle: 0.006 (0.73 -> 0.71, 1 kHz -> 12 Hz) | a clean progression: the flat component grows with how many windings sit on the shared bus/pins. Disconnected = inductive carries it alone. All-driven flat: inductive CANNOT (ceiling 0.0002 at 12 Hz); ground path CAN (R_sh ~ 0.19 R for 3 driven); EGT CAN. **T1/T2 split the last two.** |")
    L.append("| phase (dev90) at the floor | +/-90 | 0 | on the pi/8 lattice vs the session anchor (0 allowed) | overnight hold (all driven, spread): median dev90 per coil in the table above, with tens of degrees of spread; this morning's triangle: 90/90/90 at 12 Hz | an in-phase (dev90 = 0) reading fits the ground path AND EGT at rung 0; a stable non-zero offset on the pi/8 lattice would be EGT's mark. Phase does not decide yet. |")
    L.append("| followers vs leader at the floor | leader's own reading falls as f (inductive); follower via coil-to-coil M is tiny, k <= 1 | leader falls as f; followers FLAT = I_drive x R_sh(return), NO k bound | leader drags followers; followers hold geometric coupling, no k bound | punch_a0_lead (touching+cores, leader alone, followers connected): leader alpha 0.95 dying into the floor while followers read 13.0x and 2.33x the leader at 15 Hz | 'leader dies, followers hold flat' is EXACTLY the ground-path pattern and EXACTLY the EGT pattern. The 09-16 'k <= 1, forbidden' wall was inductive-only and is not admissible against the ground path. **T1/T2 decide; nothing else does.** |")
    L.append("| dummy load at 12 Hz | 0 | unchanged | vanishes | — (sealed T1) | decisive: coil required or not |")
    L.append("| star ground return | unchanged | collapses | unchanged | — (sealed T2) | decisive: return wire or geometry |")
    L.append("| separation at the floor | ~0 | flat | +21% to a max at cc 8.75 in, then -9% | — (sealed T4) | the C(r) shape, if the coil is required |")
    L.append("| hand variance 2-3 in | nil | nil | nil ('the coils don't care') | three coils within ~10% (0.66-0.74 this morning) | balanced: variance is not a lever |\n")
    L.append("## 6. Sealed discriminators\n")
    L.append(f"{seal_note}. Order: **T1 dummy load first** (cheapest, decides whether the coil is even in the reading), then T2, then T3, then T4 with the interleaved session anchor. Tempo frames and abstains; cypher/aries/echo vote the sheet.\n")
    L.append("## 7. Honest boundaries\n")
    L.append("- The ground-path column is a RANGE until R_sh is measured; measure it and the column becomes a number.\n- The inductive column uses the maximum M (one runner-loop turn linking the whole bore); the real M is smaller, so the ceiling is generous to EM.\n- Strand wiring (1 / 4 parallel / 4 series) changes L 16x but the drive current only ~4% in band; it matters for resonance and for the park, not for the 12 Hz rows.\n- The triangle numbers this morning are from the transcript, not a data file; Tonic's punch_triangle jsonl is not yet ingested.\n- Alpha fits use only points > 3x floor; configs differ (cores, spacing, followers) — read each row on its own config.\n")
    return "\n".join(L)

def main():
    rig = load_rig(); em = em_account(rig); egt = egt_account(rig); meas = measured()
    (HERE / "em_account.json").write_text(json.dumps(em, indent=1), encoding="utf-8")
    (HERE / "egt_account.json").write_text(json.dumps(egt, indent=1), encoding="utf-8")
    (HERE / "measured.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    seal_note = seal(rig, em, egt) if "--seal" in sys.argv else "NOT SEALED (run with --seal)"
    text = md(rig, em, egt, meas, seal_note)
    out = HERE / ("SHEET_%s.md" % time.strftime("%Y-%m-%d", time.gmtime()))
    out.write_text(text, encoding="utf-8")
    print(seal_note); print("wrote", out.name)
    print(json.dumps({"sweeps": [(s["file"], s["own_slope_alpha"], s["undriven_over_driven_at_fmin"]) for s in meas["sweeps"]], "holds": meas["holds"], "triangle_alpha": meas["triangle_transcript"]["alpha_coil0"]}, indent=1))

if __name__ == "__main__":
    main()
