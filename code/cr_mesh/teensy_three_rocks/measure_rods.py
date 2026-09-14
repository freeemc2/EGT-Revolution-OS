# usage: measure_rods.py <label>   -> saves rods_<label>.json; if rods_before.json exists and label!=before, prints comparison
import serial, time, statistics as st, json, sys, os
label = sys.argv[1] if len(sys.argv)>1 else "before"
here = os.path.dirname(os.path.abspath(__file__))
FREQS=[3000,7878,12000]; REPS=3
s=serial.Serial("COM10",115200,timeout=2)
def send(c,w=0.45): s.write((c+"\n").encode()); time.sleep(w)
def cmd(c,w=0.5):
    s.reset_input_buffer(); s.write((c+"\n").encode()); time.sleep(w); return s.readline().decode(errors="replace").strip()
def rd(freq,mode,secs=4.0):
    for c in mode: send(c)
    send(f"L {freq}",1.0); s.reset_input_buffer(); mg=[[],[],[]]; t0=time.time()
    while time.time()-t0<secs:
        p=s.readline().decode(errors="replace").strip().split()
        if p and p[0]=="T3" and len(p)>=8:
            for i in range(3): mg[i].append(float(p[5+i]))
    send("x",0.6); s.reset_input_buffer()
    return [st.mean(x) if x else 0.0 for x in mg]
time.sleep(0.4); print("firmware:", cmd("P"))
coils={"pin2":["M 1","K 0"],"pin3":["M 1","K 1"],"pin1":["M 1","K 2"]}
# fixed ADC assignment: A0->ADC0, A1->ADC0, A2->ADC1  (pair (0,2) for A0/A2, pair (1,2) for A1)
data={"label":label,"ts":time.strftime("%Y-%m-%d %H:%M:%S"),"floor":{},"reads":{}}
for f in FREQS:
    cmd("C 0 2"); fl=rd(f,["M 0"]); data["floor"][str(f)]={"A0":fl[0],"A2":fl[2]}
    cmd("C 1 2"); fl=rd(f,["M 0"]); data["floor"][str(f)]["A1"]=fl[1]
    for cn,mode in coils.items():
        vals={"A0":[],"A1":[],"A2":[]}
        for r in range(REPS):
            cmd("C 0 2"); m=rd(f,mode); vals["A0"].append(m[0]); vals["A2"].append(m[2])
            cmd("C 1 2"); m=rd(f,mode); vals["A1"].append(m[1])
        data["reads"][f"{f}:{cn}"]={k:st.mean(v) for k,v in vals.items()} | {k+"_sd":st.pstdev(v) for k,v in vals.items()}
s.close()
json.dump(data,open(os.path.join(here,f"rods_{label}.json"),"w"),indent=1)
print(f"\n=== {label.upper()} @ {data['ts']} ===")
print(f"{'freq:coil':14} {'A0':>7} {'A1':>7} {'A2':>7}   (floor A0/A1/A2)")
for k,v in data["reads"].items():
    f=k.split(":")[0]; fl=data["floor"][f]
    print(f"{k:14} {v['A0']:7.3f} {v['A1']:7.3f} {v['A2']:7.3f}   ({fl['A0']:.3f}/{fl['A1']:.3f}/{fl['A2']:.3f})")
bp=os.path.join(here,"rods_before.json")
if label!="before" and os.path.exists(bp):
    b=json.load(open(bp))
    print(f"\n=== {label.upper()} vs BEFORE (ratio after/before) ===")
    print(f"{'freq:coil':14} {'A0':>6} {'A1':>6} {'A2':>6}")
    for k,v in data["reads"].items():
        bv=b["reads"].get(k)
        if bv: print(f"{k:14} "+" ".join(f"{(v[c]/bv[c] if bv[c]>0.0005 else float('nan')):6.2f}" for c in ("A0","A1","A2")))
