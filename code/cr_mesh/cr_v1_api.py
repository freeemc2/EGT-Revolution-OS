#!/usr/bin/env python3
# cr_v1_api.py — EGT Compute API, Phase 1 ("people can test it"). arc, 2026-10-03.
#
# ONE gated /v1 front unifying already-built, acceptance-verified pieces:
#   POST /v1/keys        issue an API key (gate: cr_api_auth, hashed, per-key rate limit)
#   GET  /v1/predict     the operator, no run, instant+exact  |C(r)|=(1+2r)e^(-r/3)
#   POST /v1/experiment  set geometry -> real below-floor lock on the copper -> read
#   POST /v1/flow        the stateless 64-register transform (zero-retention)
#   GET  /v1/meter       pullable test instrument (INSTRUMENT=0 -> records nothing)
#   GET  /v1/health      open
#
# HONEST FRAMING (baked in, per spec + GUARD):
#   /predict   = exact operator design tool.
#   /experiment= runs a REAL below-floor lock; sigma_psi_rung is COMMANDED
#                (computed-from-input) and labeled so; below_floor is the copper's
#                REAL lock state. Commanded is NOT relabeled realized.
#   /flow      = deterministic, zero-retention transform. Same input -> same output,
#                nothing stored. NOT "computes your data", NO throughput figure.
# NON-GOALS (kept out on purpose): throughput/flow-bound/bits-s, SHA-256/crypto,
#   "computes your payload", below-B_res channel capacity, AD7606. Separate track.
import sys, os, json, math, cmath, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cr_api_auth as auth
from cr_tunnel import flow

R_OPT = 2.5
RUNG = 22.5
LAMBDA = 1.0            # foundational connectivity constant (anchor uses lambda=1)
ANCHOR_MAGSQ = 6.7995   # |C0|^2 at C0 = C(r_opt=2.5, phi=pi/2)
PHI0_DEG = 90.0         # coil target phi = pi/2 (the anchor phase zero-point)
COPPER = os.environ.get("COPPER_URL", "http://100.81.123.41:8093")
INSTRUMENT = os.environ.get("INSTRUMENT", "1") != "0"
_METER = {"pkts": 0, "bytes": 0}

def C_mag(r):
    return LAMBDA * (1 + 2 * r) * math.exp(-r / 3.0)

def C_op(r, phi_deg):
    """The COMPLEX operator C(r,phi) = lambda*(1+2r)*e^(-r/3)*e^(i*phi), with the
    canon reduction (amplitude ratio vs |C0|^2, phase offset from pi/2 in pi/8 rungs)."""
    z = C_mag(r) * cmath.exp(1j * math.radians(phi_deg))
    mag = abs(z)
    return {
        "re": round(z.real, 6), "im": round(z.imag, 6),
        "mag": round(mag, 4), "phase_deg": round(phi_deg % 360.0, 3),
        "rung": int(round((phi_deg % 360.0) / RUNG)) % 16,
        "amplitude_ratio": round(mag * mag / ANCHOR_MAGSQ, 4),
        "phase_offset_pi8": round((phi_deg - PHI0_DEG) / RUNG, 4),
    }

def coupling(r_a, r_b, dphi_rad):
    # geometric-phase projection between two co-equal rocks (symmetric)
    return C_mag(r_a) * C_mag(r_b) * math.cos(dphi_rad)

PROTECTED = ("/v1/predict", "/v1/experiment", "/v1/flow")

def _copper_get(path, timeout=20):
    with urllib.request.urlopen(COPPER + path, timeout=timeout) as r:
        return json.load(r)

def _copper_post(path, obj, timeout=30):
    req = urllib.request.Request(COPPER + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, obj):
        out = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def _key(self):
        return (self.headers.get("X-API-Key")
                or self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                or None)

    def _gate(self, route):
        """Enforce the key on protected routes. Returns True if allowed."""
        if route not in PROTECTED:
            return True
        ok, status, info = auth.check_and_record(self._key())
        if not ok:
            self._send(status, info)
            return False
        return True

    # ---- GET ----
    def do_GET(self):
        route, _, qs = self.path.partition("?")
        route = route.rstrip("/") or "/"
        params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p) if qs else {}
        if route == "/v1/health":
            self._send(200, {"api": "egt-compute-v1", "ok": True,
                             "endpoints": ["POST /v1/keys", "GET /v1/predict",
                                           "POST /v1/experiment", "POST /v1/flow", "GET /v1/meter"],
                             "r_opt": R_OPT})
            return
        if route == "/v1/meter":
            self._send(200, {"instrument": INSTRUMENT,
                             "pkts": _METER["pkts"] if INSTRUMENT else None,
                             "bytes": _METER["bytes"] if INSTRUMENT else None,
                             "note": ("test instrument (INSTRUMENT=0 to pull)" if INSTRUMENT
                                      else "nothing recorded")})
            return
        if route == "/v1/predict":
            if not self._gate(route):
                return
            try:
                r_a = float(params.get("r_a", 0.0))
                r_b = float(params.get("r_b", 2.0))
                # each rock carries a geometric phase; dphi_deg is accepted as
                # phi_a with phi_b=0 (so dphi = phi_a - phi_b) for back-compat
                dphi_in = params.get("dphi_deg")
                phi_a = float(params.get("phi_a_deg", dphi_in if dphi_in is not None else 0.0))
                phi_b = float(params.get("phi_b_deg", 0.0))
            except ValueError:
                self._send(400, {"error": "r_a, r_b, phi_a_deg, phi_b_deg, dphi_deg must be numbers"}); return
            dphi = phi_a - phi_b
            Ca, Cb = C_op(r_a, phi_a), C_op(r_b, phi_b)
            coup = Ca["mag"] * Cb["mag"] * math.cos(math.radians(dphi))
            self._send(200, {
                "r_a": r_a, "r_b": r_b,
                "phi_a_deg": phi_a, "phi_b_deg": phi_b, "dphi_deg": round(dphi, 3),
                "lambda": LAMBDA,
                "C_a": Ca, "C_b": Cb,                 # the COMPLEX operator per rock
                "coupling": round(coup, 4),            # |C_a||C_b|*cos(dphi), geometric-phase projection
                "r_opt": R_OPT,
                "anchor": {"C0_mag_sq": ANCHOR_MAGSQ, "phi0_deg": PHI0_DEG, "rung": 4},
                "operator": "C(r,phi) = lambda*(1+2r)*e^(-r/3)*e^(i*phi) (complex); coupling = |C_a||C_b|*cos(dphi)"})
            return
        self._send(404, {"error": "not found", "see": "GET /v1/health"})

    # ---- POST ----
    def do_POST(self):
        route = self.path.partition("?")[0].rstrip("/") or "/"
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b""
        if route == "/v1/keys":
            try:
                body = json.loads(raw or b"{}")
            except Exception:
                body = {}
            name = (body.get("name") or "").strip()
            if not name:
                self._send(400, {"error": "POST /v1/keys {\"name\": \"...\"}"}); return
            auth.init_db()
            acct = auth.create_account(name, email=body.get("email"))
            self._send(200, {"api_key": acct["api_key"], "account_id": acct["account_id"],
                             "per_min": acct["per_min"], "per_day": acct["per_day"],
                             "note": "Save this key now — shown once, stored only as a hash.",
                             "auth": "send header  X-API-Key: <key>  on /v1/predict, /v1/experiment, /v1/flow"})
            return
        if not self._gate(route):
            return
        if route == "/v1/flow":
            rungs = flow(raw if raw else b"")
            if INSTRUMENT:
                _METER["pkts"] += 1; _METER["bytes"] += len(raw)
            # stateless, zero-retention: nothing about `raw` is kept past this return
            self._send(200, {"rungs": rungs,
                             "note": "deterministic zero-retention transform; same input -> same output"})
            return
        if route == "/v1/experiment":
            try:
                body = json.loads(raw or b"{}")
            except Exception:
                body = {}
            r = float(body.get("r", R_OPT))
            phi_deg = float(body.get("phi_deg", 90.0))
            seconds = max(0.0, min(float(body.get("seconds", 0.0)), 30.0))
            try:
                # set geometry (commanded) -> optional hold -> read
                _copper_post("/api/v1/geometry", {"sigma_psi_deg": phi_deg})
                if seconds:
                    time.sleep(min(seconds, 10.0))
                st = _copper_get("/api/v1/state")
            except Exception as e:
                self._send(503, {"error": "copper rig unreachable", "detail": str(e)[:120],
                                 "copper": COPPER}); return
            # below_floor needs the drive loop streaming T3; degrade honestly if it isn't
            rd, bf, bf_note = {}, None, "measured (copper real lock state)"
            try:
                rd = _copper_get("/api/v1/coil/read")
                bf = bool(rd.get("all_under")) if "all_under" in rd else None
            except Exception as e:
                bf_note = "unavailable: copper drive loop not streaming T3 (%s)" % str(e)[:60]
            commanded_sigma = st.get("sigma_psi_deg")
            self._send(200, {
                "r": r, "C_mag": round(C_mag(r), 4),
                "sigma_psi_rung": (int(round(commanded_sigma / RUNG)) % 16) if commanded_sigma is not None else None,
                "sigma_psi_deg": commanded_sigma,
                "sigma_psi_label": "commanded",   # computed-from-input, NOT realized
                "below_floor": bf,
                "below_floor_label": bf_note,
                "state": {"offsets_commanded_deg": st.get("offsets_commanded_deg"),
                          "mag": rd.get("mag"), "phase_deg": rd.get("phase_deg")},
                "note": "sigma_psi_rung is COMMANDED (computed-from-input); below_floor is the copper's REAL lock."})
            return
        self._send(404, {"error": "not found", "see": "GET /v1/health"})

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    auth.init_db()
    print("EGT Compute API /v1 on 127.0.0.1:%d  (copper=%s)" % (port, COPPER), flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
