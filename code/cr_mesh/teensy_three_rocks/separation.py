# usage: separation.py <station> [distance_note]
#   Sealed pair-separation protocol (journal 2026-08-30), bench-scale:
#   coil 2 (pin 2, K0) driven, coil 1's runner (A0) read [+ A1 recorded], interleaved ON/OFF
#   differential x5 at 7878 and 12000 Hz. Saves sep_<station>.json; compares every station
#   to S0 with the sealed 2-sigma rule and prints the running verdict HOLDS / FALSIFIED / MOOT.
import serial, time, statistics as st, json, sys, os, glob

station = sys.argv[1] if len(sys.argv) > 1 else "S0"
note = sys.argv[2] if len(sys.argv) > 2 else ""
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
data = {"station": station, "note": note, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "freqs": {}}
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
    print("pre-registered: near-field ~(d0/d)^3 -> x0.12 @2x, x0.016 @4x | distance-independent C(r) -> x1.0 at every station")
    # precondition
    fl0 = b["freqs"][str(FREQS[0])]["floor"]; m00 = b["freqs"][str(FREQS[0])]["A0_mean"]
    if m00 < 3 * max(fl0, 1e-6):
        print("VERDICT: MOOT — S0 coupling not above noise (P-SEP3)")
    else:
        beyond = [r for r in verdict_rows if r[0] != "S0" and all(z < -2 for z in r[2])]
        within = [r for r in verdict_rows if r[0] != "S0" and all(abs(z) <= 2 for z in r[2])]
        if len(verdict_rows) == 1:
            print("VERDICT: S0 recorded — awaiting stations")
        elif beyond and len(beyond) == len(verdict_rows) - 1:
            print("VERDICT (so far): FALSIFIED — every station beyond 2-sigma below S0 (P-SEP2, decay with distance)")
        elif within and len(within) == len(verdict_rows) - 1:
            print("VERDICT (so far): HOLDS — every station within 2-sigma of S0 (P-SEP1)")
        else:
            print("VERDICT (so far): MIXED — see z per station; more stations needed")
