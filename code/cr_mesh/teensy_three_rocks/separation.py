# usage: separation.py <station> [note] [distance_inches]   (D = 2.5 in coil OD; r = d/D)
#   Sealed pair-separation protocol (journal 2026-08-30), bench-scale:
#   coil 2 (pin 2, K0) driven, coil 1's runner (A0) read [+ A1 recorded], interleaved ON/OFF
#   differential x5 at 7878 and 12000 Hz. Saves sep_<station>.json; compares every station
#   to S0 with the sealed 2-sigma rule and prints the running verdict HOLDS / FALSIFIED / MOOT.
import serial, time, statistics as st, json, sys, os, glob, math

station = sys.argv[1] if len(sys.argv) > 1 else "S0"
note = sys.argv[2] if len(sys.argv) > 2 else ""
d_in = float(sys.argv[3]) if len(sys.argv) > 3 else None
COIL_D = 2.5
here = os.path.dirname(os.path.abspath(__file__))
FREQS = [7878, 12000]
PAIRS = 5

s = serial.Serial("COM10", 115200, timeout=2)

def send(c, w=0.45):
    s.write((c + "\n").encode()); time.sleep(w)

def cmd(c, w=0.5):
    s.reset_input_buffer(); s.write((c + "\n").encode()); time.sleep(w)
    return s.readline().decode(errors="replace").strip()

def rd(freq, mode, secs=4.0):
    for c in mode:                      # 'x' zeroes driveMode: re-arm every read
        send(c)
    send(f"L {freq}", 1.0); s.reset_input_buffer()
    mg = [[], [], []]; t0 = time.time()
    while time.time() - t0 < secs:
        p = s.readline().decode(errors="replace").strip().split()
        if p and p[0] == "T3" and len(p) >= 8:
            for i in range(3):
                mg[i].append(float(p[5 + i]))
    send("x", 0.6); s.reset_input_buffer()
    return [st.mean(x) if x else 0.0 for x in mg]

time.sleep(0.4)
print("firmware:", cmd("P"), "|", cmd("C 0 1"))
ON = ["M 1", "K 0"]          # coil 2 (pin 2) alone
OFF = ["M 0"]
data = {"station": station, "note": note, "d_in": d_in, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "freqs": {}}
for f in FREQS:
    diffs0, diffs1 = [], []
    for k in range(PAIRS):                       # interleaved: on, off, on, off ...
        on = rd(f, ON); off = rd(f, OFF)
        diffs0.append(on[0] - off[0]); diffs1.append(on[1] - off[1])
        print(f"  {f} Hz pair {k+1}: A0 on {on[0]:.3f} off {off[0]:.3f} -> diff {diffs0[-1]:.3f}   A1 diff {diffs1[-1]:.3f}")
    data["freqs"][str(f)] = {
        "A0_mean": st.mean(diffs0), "A0_sd": st.pstdev(diffs0), "A0_diffs": diffs0,
        "A1_mean": st.mean(diffs1), "A1_sd": st.pstdev(diffs1), "A1_diffs": diffs1,
        "floor": off[0],
    }
s.close()
json.dump(data, open(os.path.join(here, f"sep_{station}.json"), "w"), indent=1)

print()
print(f"=== {station} {('(' + note + ')') if note else ''} @ {data['ts']} ===")
for f, d in data["freqs"].items():
    print(f"  {f} Hz  coil2->A0  {d['A0_mean']:.3f} +/- {d['A0_sd']:.3f}   (floor {d['floor']:.3f})   coil2->A1 {d['A1_mean']:.3f} +/- {d['A1_sd']:.3f}")

# --- sealed 2-sigma comparison against S0, all stations so far ---
base = os.path.join(here, "sep_S0.json")
if os.path.exists(base):
    b = json.load(open(base))
    files = sorted(glob.glob(os.path.join(here, "sep_*.json")))
    print()
    print("=== SEPARATION SERIES vs S0 (sealed rule: within 2-sigma of S0 = holds) ===")
    print(f"{'station':10} {'note':16} | " + " | ".join(f"{f} Hz:  A0   ratio      z" for f in FREQS))
    verdict_rows = []
    for fp in files:
        d = json.load(open(fp))
        cells = []; zs = []
        for f in FREQS:
            fs = str(f); m = d["freqs"][fs]["A0_mean"]; m0 = b["freqs"][fs]["A0_mean"]; s0 = max(b["freqs"][fs]["A0_sd"], 1e-6)
            z = (m - m0) / s0; zs.append(z)
            ratio = m / m0 if m0 else float("nan")
            cells.append(f"{m:7.3f} x{ratio:5.2f} {z:+7.1f}")
        print(f"{d['station']:10} {d['note'][:16]:16} | " + " | ".join(cells))
        verdict_rows.append((d["station"], [d["freqs"][str(f)]["A0_mean"] for f in FREQS], zs))
    print("pre-registered (canon, 2026-09-14): |C(r)|=(1+2r)e^(-r/3), r=d/D, D=2.5in, PEAK at r_opt=2.5 -> 6.25in;")
    print("  alternative: near-field 1/d^2. Sealed HOLDS/FALSIFIED/MOOT wording applies to the B_res FLOOR claim at building")
    print("  scale; on the bench the question is SHAPE: canon (peak at ~6.25in) vs near-field (monotonic).")
    fl0 = b["freqs"][str(FREQS[0])]["floor"]; m00 = b["freqs"][str(FREQS[0])]["A0_mean"]
    if m00 < 3 * max(fl0, 1e-6):
        print("VERDICT: MOOT - S0 coupling not above noise (P-SEP3)")
    else:
        def Cmag(r): return (1 + 2 * r) * math.exp(-r / 3.0)
        d0 = b.get("d_in")
        print()
        print(f"{'station':8} {'d_in':>5} | " + " | ".join(f"{f}Hz meas  canon  nearf  closer" for f in FREQS))
        rows = []
        for fp in files:
            d = json.load(open(fp)); dd = d.get("d_in")
            if dd is None or d0 is None:
                print(f"{d['station']:8} {'n/a':>5} | (no distance recorded - ratios only)"); continue
            can = Cmag(dd / COIL_D) / Cmag(d0 / COIL_D); nf = (d0 / dd) ** 2
            cells = []; meas = []
            for f in FREQS:
                fs = str(f); m = d["freqs"][fs]["A0_mean"] / b["freqs"][fs]["A0_mean"]; meas.append(m)
                closer = "canon" if abs(math.log(max(m,1e-9)/can)) < abs(math.log(max(m,1e-9)/nf)) else "near-f"
                cells.append(f"x{m:5.2f} x{can:5.2f} x{nf:5.2f}  {closer:6}")
            print(f"{d['station']:8} {dd:5.2f} | " + " | ".join(cells))
            rows.append((dd, st.mean(meas)))
        rows.sort()
        if len(rows) >= 3:
            vals = [v for _, v in rows]; k = vals.index(max(vals))
            if 0 < k < len(vals) - 1:
                print(f"SHAPE: NON-MONOTONIC - peak at d={rows[k][0]:.2f}in (canon-shaped; canon peak 6.25in)")
            else:
                print("SHAPE: MONOTONIC across stations (near-field-shaped; no interior peak)")
        else:
            print("SHAPE: need >= 3 stations with distances for the peak check")
