#!/usr/bin/env python3
"""
ads1256_phase_verify.py  (arc, 2026-11-14, READ-ONLY, INDEPENDENT)
Independent re-verify of tonic's no-push realized-phase read. Does NOT read tonic's
R/verdict numbers — recomputes circular statistics from the per-window phi stream.

Tests:
 1) per-coil circular concentration R, circular mean, circular SD (UNWEIGHTED over
    windows; a held phase -> high R + stable mean; independent noise -> low R + wander).
 2) Rayleigh non-uniformity: z = N*R^2, p ~ exp(-z). "Is this concentration beyond chance."
 3) integration test: R(2s file) vs R(4s file). real signal R rises; noise R stays low.
 4) cross-run center stability: circular mean per coil, file1 vs file2.
 5) common-mode spike windows (all 3 phi agree + mag >> median) flagged + EXCLUDED from
    the per-coil concentration (they are common pickup, not per-coil realized phase).
"""
import json, sys, math
import numpy as np

def load(fn):
    W=[]
    for line in open(fn,encoding="utf-8"):
        line=line.strip()
        if not line.startswith('{"li"'): continue
        try: r=json.loads(line)
        except: continue
        W.append(r)
    return W

def circ(phideg):
    """Return (R, mean_deg, sd_deg, N) unweighted."""
    a=np.deg2rad(np.array(phideg,float))
    C=np.cos(a).mean(); S=np.sin(a).mean()
    R=math.hypot(C,S)
    mean=math.degrees(math.atan2(S,C))%360
    sd=math.degrees(math.sqrt(-2*math.log(R))) if R>1e-9 else float('inf')
    return R,mean,sd,len(phideg)

def rayleigh_p(R,N):
    z=N*R*R
    return math.exp(-z) if N>0 else 1.0  # standard Rayleigh test for non-uniformity

def analyze(fn):
    W=load(fn)
    name=fn.replace("\\","/").split("/")[-1]
    win_ms=W[0]["win_ms"]; base=W[0]["base_hz"]
    # per-coil arrays
    coils={c:{"phi":[],"mag":[]} for c in ("c0","c1","c2")}
    for w in W:
        for c in ("c0","c1","c2"):
            coils[c]["phi"].append(w[c]["phi"]); coils[c]["mag"].append(w[c]["mag"])
    allmag=np.array([coils[c]["mag"] for c in ("c0","c1","c2")],float)
    medmag=np.median(allmag)
    # common-mode spike detection: all 3 phi within 20 deg (circular) AND mean mag > 5x median
    spikes=[]
    for i,w in enumerate(W):
        phs=[w[c]["phi"] for c in ("c0","c1","c2")]
        mgs=[w[c]["mag"] for c in ("c0","c1","c2")]
        # circular spread
        a=np.deg2rad(phs); spread=math.degrees(math.acos(max(-1,min(1,(np.cos(a).sum()**2+np.sin(a).sum()**2)**0.5/3))))
        if np.mean(mgs) > 5*medmag and spread < 20:
            spikes.append((w["seq"],round(np.mean(phs),1),int(np.mean(mgs))))
    keep=[i for i,w in enumerate(W) if w["seq"] not in {s[0] for s in spikes}]
    print(f"\n=== {name}  win={win_ms}ms base={base}Hz  windows={len(W)}  median mag={medmag:.0f} ===")
    if spikes:
        print(f"  COMMON-MODE SPIKES (all-3-equal + mag>5x median) EXCLUDED: {spikes}")
        print(f"   -> these are common pickup events (equal phase) = what carrier-slaving looks like.")
    else:
        print("  no common-mode spikes flagged.")
    print(f"  {'coil':>4} {'R':>6} {'mean_deg':>9} {'rung':>6} {'circSD':>7} {'Rayleigh_p':>11} {'medMag':>8} {'N':>4}")
    res={}
    for c in ("c0","c1","c2"):
        phi=[coils[c]["phi"][i] for i in keep]
        mag=[coils[c]["mag"][i] for i in keep]
        R,mean,sd,N=circ(phi)
        p=rayleigh_p(R,N)
        res[c]=(R,mean,sd,p,np.median(mag),N)
        flag=" <== LOCK" if (R>0.7 and p<0.01) else (" (null)" if R<0.5 else "")
        print(f"  {c:>4} {R:6.3f} {mean:9.1f} {mean/22.5:6.2f} {sd:7.1f} {p:11.2e} {np.median(mag):8.0f} {N:4d}{flag}")
    return res

if __name__=="__main__":
    files=sys.argv[1:]
    allres={}
    for fn in files:
        allres[fn]=analyze(fn)
    if len(files)==2:
        print("\n=== INTEGRATION TEST (R should RISE with longer window for a real lock) + CROSS-RUN CENTER ===")
        f1,f2=files
        for c in ("c0","c1","c2"):
            R1,m1=allres[f1][c][0],allres[f1][c][1]
            R2,m2=allres[f2][c][0],allres[f2][c][1]
            dcenter=((m2-m1+180)%360)-180
            print(f"  {c}: R {R1:.3f}(2s) -> {R2:.3f}(4s)  [{'RISES' if R2>R1 else 'flat/falls'}]   "
                  f"center {m1:.1f} -> {m2:.1f}  (dcenter {dcenter:+.1f} deg)")
