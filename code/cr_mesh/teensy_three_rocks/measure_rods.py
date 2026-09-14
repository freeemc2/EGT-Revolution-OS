# usage: [BASE=label1,label2] measure_rods.py <label>
#   Measures every coil alone (pins 2/3/1) into every runner (A0/A1/A2) with a FIXED ADC
#   assignment per runner, 3 freqs x 3 repeats, saves rods_<label>.json, then prints the
#   ratio vs each BASE run (default: norods_3coils, the confirmed no-cores baseline).
import serial, time, statistics as st, json, sys, os

label = sys.argv[1] if len(sys.argv) > 1 else "run"
here = os.path.dirname(os.path.abspath(__file__))
FREQS = [3000, 7878, 12000]
REPS = 3

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
print("firmware:", cmd("P"))
coils = {"pin2": ["M 1", "K 0"], "pin3": ["M 1", "K 1"], "pin1": ["M 1", "K 2"]}
# fixed ADC assignment: A0 -> ADC0 (pair 0,2), A1 -> ADC0 (pair 1,2), A2 -> ADC1
data = {"label": label, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "floor": {}, "reads": {}}
for f in FREQS:
    cmd("C 0 2"); fl = rd(f, ["M 0"]); data["floor"][str(f)] = {"A0": fl[0], "A2": fl[2]}
    cmd("C 1 2"); fl = rd(f, ["M 0"]); data["floor"][str(f)]["A1"] = fl[1]
    for cn, mode in coils.items():
        vals = {"A0": [], "A1": [], "A2": []}
        for r in range(REPS):
            cmd("C 0 2"); m = rd(f, mode); vals["A0"].append(m[0]); vals["A2"].append(m[2])
            cmd("C 1 2"); m = rd(f, mode); vals["A1"].append(m[1])
        rec = {k: st.mean(v) for k, v in vals.items()}
        rec.update({k + "_sd": st.pstdev(v) for k, v in vals.items()})
        data["reads"][f"{f}:{cn}"] = rec
s.close()

json.dump(data, open(os.path.join(here, f"rods_{label}.json"), "w"), indent=1)
print()
print("=== " + label.upper() + " @ " + data["ts"] + " ===")
print(f"{'freq:coil':14} {'A0':>7} {'A1':>7} {'A2':>7}   (floor A0/A1/A2)")
for k, v in data["reads"].items():
    fl = data["floor"][k.split(":")[0]]
    print(f"{k:14} {v['A0']:7.3f} {v['A1']:7.3f} {v['A2']:7.3f}   ({fl['A0']:.3f}/{fl['A1']:.3f}/{fl['A2']:.3f})")

for base in os.environ.get("BASE", "norods_3coils").split(","):
    bp = os.path.join(here, f"rods_{base}.json")
    if base != label and os.path.exists(bp):
        b = json.load(open(bp))
        print()
        print("=== " + label.upper() + " vs " + base.upper() + "  (ratio " + label + "/" + base + ") ===")
        print(f"{'freq:coil':14} {'A0':>6} {'A1':>6} {'A2':>6}")
        for k, v in data["reads"].items():
            bv = b["reads"].get(k)
            if bv:
                cells = [f"{(v[c] / bv[c]):6.2f}" if bv[c] > 0.0005 else "   nan" for c in ("A0", "A1", "A2")]
                print(f"{k:14} " + " ".join(cells))
