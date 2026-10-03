#!/usr/bin/env python3
# cr_v1_acceptance.py — Phase 1 acceptance checks for the EGT Compute API /v1.
# Must pass before shipping. arc, 2026-10-03.
#   usage: python cr_v1_acceptance.py [main_url] [pulled_url]
#   main_url   = server with INSTRUMENT=1 (default http://127.0.0.1:8099)
#   pulled_url = server with INSTRUMENT=0 (default http://127.0.0.1:8100)
import sys, json, math, urllib.request

MAIN = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099"
PULLED = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8100"
FORBIDDEN = ("throughput", "bits/s", "bits-s", "computes your", "flow-bound",
             "quintillion", "sha-256", "sha256", "below-b_res", "ad7606")
PASS = []; FAIL = []

def rec(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  PASS " if ok else "  FAIL ") + name + (("  -- " + detail) if detail else ""))

def req(url, method="GET", body=None, headers=None, timeout=40):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)
    except Exception as e:
        return 0, {"_err": str(e)}

def no_forbidden(obj):
    s = json.dumps(obj).lower()
    return [w for w in FORBIDDEN if w in s]

print("=== EGT Compute API /v1 — Phase 1 acceptance ===  main=%s" % MAIN)

# issue a key
st, k = req(MAIN + "/v1/keys", "POST", {"name": "acceptance"})
KEY = k.get("api_key")
rec("keys: issue returns api_key", st == 200 and bool(KEY))
H = {"X-API-Key": KEY}

# C1 GATE
st_no, _ = req(MAIN + "/v1/predict?r_a=0&r_b=2&dphi_deg=0", "GET")
st_yes, _ = req(MAIN + "/v1/predict?r_a=0&r_b=2&dphi_deg=0", "GET", headers=H)
rec("gate: no key -> 401", st_no == 401, "got %s" % st_no)
rec("gate: valid key -> 200", st_yes == 200, "got %s" % st_yes)

# C2 /predict canon
canon = {0: 1.000, 1: 2.150, 2: 2.567, 2.5: 2.608, 3: 2.575}
allok = True
for r, exp in canon.items():
    st, d = req(MAIN + "/v1/predict?r_a=%s&r_b=2&dphi_deg=0" % r, "GET", headers=H)
    got = d.get("C_a")
    ok = st == 200 and got is not None and abs(got - exp) <= 0.001
    allok = allok and ok
    rec("predict |C(%s)| = %.3f" % (r, exp), ok, "got %s" % got)
# coupling = product * cos(dphi)
st, d = req(MAIN + "/v1/predict?r_a=0&r_b=2&dphi_deg=55", "GET", headers=H)
exp_c = round(1.0 * ((1+4)*math.exp(-2/3)) * math.cos(math.radians(55)), 4)
rec("predict coupling = |C_a||C_b|cos(dphi)", abs(d.get("coupling", 0) - exp_c) <= 0.001,
    "got %s expect %s" % (d.get("coupling"), exp_c))

# C3 /experiment (needs live copper)
st_f, frus = req(MAIN + "/v1/experiment", "POST", {"r": 2.5, "phi_deg": 0, "seconds": 1}, H, timeout=60)
st_d, diff = req(MAIN + "/v1/experiment", "POST", {"r": 2.5, "phi_deg": 90, "seconds": 1}, H, timeout=60)
st_r, rep = req(MAIN + "/v1/experiment", "POST", {"r": 2.5, "phi_deg": 90, "seconds": 1}, H, timeout=60)
if st_f == 200 and st_d == 200 and st_r == 200:
    rec("experiment: different geometry -> different Sigma-psi rung",
        frus.get("sigma_psi_rung") != diff.get("sigma_psi_rung"),
        "frus=%s diff=%s" % (frus.get("sigma_psi_rung"), diff.get("sigma_psi_rung")))
    rec("experiment: same geometry repeated -> same rung",
        diff.get("sigma_psi_rung") == rep.get("sigma_psi_rung"),
        "%s vs %s" % (diff.get("sigma_psi_rung"), rep.get("sigma_psi_rung")))
    rec("experiment: sigma_psi labeled 'commanded'", frus.get("sigma_psi_label") == "commanded")
    # below_floor is rig-state-conditional: only the copper drive loop streaming T3 can show it
    bf = frus.get("below_floor")
    if bf is True:
        rec("experiment: frustrated -> below_floor lock", True)
    else:
        print("  NOTE experiment: below_floor=%s (%s) -- rig-state, not an API defect"
              % (bf, frus.get("below_floor_label")))
    # restore frustrated baseline
    req(MAIN + "/v1/experiment", "POST", {"r": 2.5, "phi_deg": 0, "seconds": 0}, H, timeout=60)
else:
    rec("experiment: copper reachable", False, "status %s/%s/%s (copper down?)" % (st_f, st_d, st_r))

# C4 /flow determinism + zero-retention
_, a1 = req(MAIN + "/v1/flow", "POST", None, {**H}, timeout=20)
# send raw bytes bodies directly
def flow_raw(url, data, headers):
    r = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(r, timeout=20) as resp:
        return json.load(resp)
d1 = flow_raw(MAIN + "/v1/flow", b"hello-egt", H)
d2 = flow_raw(MAIN + "/v1/flow", b"hello-egt", H)
d3 = flow_raw(MAIN + "/v1/flow", b"different-input", H)
rec("flow: same data -> identical rungs", d1["rungs"] == d2["rungs"])
rec("flow: different data -> different rungs", d1["rungs"] != d3["rungs"])
# meter pulled (INSTRUMENT=0 server)
stp, kp = req(PULLED + "/v1/keys", "POST", {"name": "pulledtest"})
if stp == 200:
    Hp = {"X-API-Key": kp["api_key"]}
    flow_raw(PULLED + "/v1/flow", b"zero-retention-check", Hp)
    _, m = req(PULLED + "/v1/meter", "GET")
    rec("meter INSTRUMENT=0 -> records 0 (zero-retention)",
        m.get("instrument") is False and m.get("pkts") is None, "meter=%s" % m)
else:
    rec("meter INSTRUMENT=0 server reachable", False, "pulled server down (status %s)" % stp)

# C5 no forbidden claims in any payload
bad = []
for label, (_, obj) in {
    "health": req(MAIN + "/v1/health", "GET"),
    "predict": req(MAIN + "/v1/predict?r_a=0&r_b=2&dphi_deg=0", "GET", headers=H),
    "flow": (200, d1),
    "meter": req(MAIN + "/v1/meter", "GET"),
}.items():
    hits = no_forbidden(obj)
    if hits: bad.append("%s:%s" % (label, hits))
rec("no endpoint returns throughput/computes/crypto claim", not bad, str(bad))

print("\n== %d PASS, %d FAIL ==" % (len(PASS), len(FAIL)))
sys.exit(0 if not FAIL else 1)
