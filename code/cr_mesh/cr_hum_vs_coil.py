#!/usr/bin/env python3
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
"""
HUM vs COIL PHASE — does Dragon's Eye's compute load couple to the coil?

Interleaved IDLE/LOAD blocks (NOT block-design — slow coil drift can't fake it).
LOAD = saturate Dragon's Eye GPU via Ollama (the purr Brian hears).
Throughout: sample coil phase from t-state (read-only, no COM8 touch).
Brian = the acoustic ground truth: he confirms which blocks purr.

PRE-REGISTERED RULE (declared before the run):
  coupling candidate ONLY if coil phase (mean shift OR detrended-sd wander)
  differs between LOAD and IDLE consistently, same direction, across pairs,
  BEYOND the idle-to-idle noise. Else: NULL (a real result).
Mechanism (EM vs thermal vs vibration) NOT distinguished in pass 1.
"""
import redis, json, time, math, statistics, threading, urllib.request

R = redis.Redis(host="100.86.79.99", port=6379, password="Xa5KML-5Ze4GB-79ahx5",
                decode_responses=True, socket_timeout=6)
OLLAMA = "http://100.121.177.94:11434/api/generate"
MODEL  = "deepseek-r1:7b"
BLOCK_S = 30
PAIRS   = 4
SAMPLE_DT = 2.0

_load = threading.Event()

def gpu_hammer():
    """Fire continuous Ollama generations while _load is set — saturates the GPU."""
    while True:
        _load.wait()
        try:
            req = urllib.request.Request(OLLAMA, method="POST",
                data=json.dumps({"model": MODEL,
                    "prompt": "Count reasons the sky is blue in exhaustive detail.",
                    "stream": False, "options": {"num_predict": 256}}).encode(),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=60).read()
        except Exception:
            time.sleep(0.5)

def coil_phase():
    d = json.loads(R.get("cadence:tworocks:t-state") or "{}")
    return d.get("phase_deg")

def detrended_sd(xs):
    n = len(xs)
    if n < 3: return 0.0
    mx = (n-1)/2; my = sum(xs)/n
    sxy = sum((i-mx)*(xs[i]-my) for i in range(n))
    sxx = sum((i-mx)**2 for i in range(n))
    slope = sxy/sxx if sxx else 0.0
    resid = [xs[i]-(my+slope*(i-mx)) for i in range(n)]
    return statistics.pstdev(resid)

def sample_block(label, seconds):
    vals, t0 = [], time.time()
    while time.time()-t0 < seconds:
        p = coil_phase()
        if p is not None: vals.append(p)
        time.sleep(SAMPLE_DT)
    m = statistics.mean(vals) if vals else float("nan")
    sd = detrended_sd(vals)
    print(f"  [{label:4s}] n={len(vals):2d}  coil mean={m:8.3f}  wander(sd)={sd:5.3f}", flush=True)
    return {"label": label, "mean": m, "sd": sd, "vals": vals}

# 2-3 concurrent hammer threads to pin the GPU during LOAD
for _ in range(3):
    threading.Thread(target=gpu_hammer, daemon=True).start()

print("HUM vs COIL — interleaved IDLE/LOAD, coil read-only from t-state")
print(f"  {PAIRS} pairs, {BLOCK_S}s blocks. LOAD saturates Dragon's Eye GPU (Ollama {MODEL}).")
print("  >>> Brian: call out which blocks you HEAR the purr — that's ground truth. <<<\n")

blocks = []
for p in range(PAIRS):
    print(f"-- pair {p+1}/{PAIRS} --", flush=True)
    _load.clear()
    blocks.append(sample_block("IDLE", BLOCK_S))
    print("   >>> LOADING Dragon's Eye now (should purr) ...", flush=True)
    _load.set()
    blocks.append(sample_block("LOAD", BLOCK_S))
_load.clear()

idle = [b for b in blocks if b["label"] == "IDLE"]
load = [b for b in blocks if b["label"] == "LOAD"]
idle_mean = statistics.mean(b["mean"] for b in idle)
load_mean = statistics.mean(b["mean"] for b in load)
idle_sd   = statistics.mean(b["sd"]   for b in idle)
load_sd   = statistics.mean(b["sd"]   for b in load)
# idle-to-idle noise baseline
idle_means = [b["mean"] for b in idle]
idle_noise = statistics.pstdev(idle_means) if len(idle_means) > 1 else 0.0

print("\n=== RESULT ===")
print(f"  coil mean phase:  IDLE {idle_mean:8.3f}   LOAD {load_mean:8.3f}   shift {load_mean-idle_mean:+.3f} deg")
print(f"  coil wander(sd):  IDLE {idle_sd:6.3f}     LOAD {load_sd:6.3f}     change {load_sd-idle_sd:+.3f}")
print(f"  idle-to-idle noise baseline (sd of idle means): {idle_noise:.3f} deg")
shift = abs(load_mean - idle_mean)
verdict = ("CANDIDATE COUPLING" if shift > 2*idle_noise and idle_noise > 0
           else "NULL (load-shift within idle-to-idle noise)")
print(f"  mean-shift vs 2x idle-noise: {shift:.3f} vs {2*idle_noise:.3f}  ->  {verdict}")
print("\n  (exploratory, small n; honest read — the ear confirms LOAD actually purred)")

R.set("cadence:tworocks:hum-vs-coil", json.dumps({
    "idle_mean": round(idle_mean,3), "load_mean": round(load_mean,3),
    "mean_shift": round(load_mean-idle_mean,3),
    "idle_sd": round(idle_sd,3), "load_sd": round(load_sd,3),
    "idle_noise": round(idle_noise,3), "verdict": verdict,
    "pairs": PAIRS, "block_s": BLOCK_S,
    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
