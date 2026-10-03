#!/usr/bin/env python3
# cr_tunnel_api.py — wire the readable-throughput tunnel as an HTTP endpoint.
# POST /tunnel  {"request": "<text>"} -> {"rungs":[...], "sigma_psi_rung":n, "j":n}
#   one push winds through the live 64-register coupled set (Sigma-psi conserved),
#   reads the rung-tuple out = the answer. The set FLOWS (cumulative); /reset reseeds.
# POST /flow   raw body -> {"rungs":[...]}  STATELESS (holds nothing; see cr_tunnel.flow)
# GET  /health -> {n, sigma_psi}
# GET  /meter  -> test instrument; INSTRUMENT=0 pulls it (live records nothing)
# POST /reset  -> reseed the flowing set (for determinism replay)
# stdlib only. arc, 2026-10-03.
# NOTE: /flow is a <=27.8-bit input->rung digest with zero-retention, not a payload
# carry; any req/s here is cv (host), not a flow-bound Sigma-psi rate.
import json, sys, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr_tunnel import Tunnel, flow

T = Tunnel()
LOCK = threading.Lock()

# PULLABLE instrument. INSTRUMENT=0 -> live shape: nothing counted, nothing to read.
INSTRUMENT = os.environ.get("INSTRUMENT", "1") != "0"
_METER = {"pkts": 0, "bytes": 0}

def _meter_tick(nbytes):
    if INSTRUMENT:
        _METER["pkts"] += 1
        _METER["bytes"] += nbytes

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        out = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)
    def do_GET(self):
        q = self.path.rstrip('/')
        if q == '/health':
            with LOCK:
                self._send(200, {"tunnel": "egt", "n": T.n, "sigma_psi": T.sigma_psi()})
        elif q == '/meter':
            self._send(200, {"instrument": INSTRUMENT,
                             "pkts": _METER["pkts"] if INSTRUMENT else None,
                             "bytes": _METER["bytes"] if INSTRUMENT else None,
                             "note": ("test instrument (pull with INSTRUMENT=0 for live)"
                                      if INSTRUMENT else "pulled -> nothing recorded, nothing to read")})
        else:
            self._send(404, {"error": "not found"})
    def do_POST(self):
        p = self.path.rstrip('/')
        n = int(self.headers.get('Content-Length', 0) or 0)
        body = self.rfile.read(n) if n else b'{}'
        if p == '/flow':
            # STATELESS conduit: raw body in -> rung answer out. Pure function (no lock),
            # zero-retention. Holds nothing; <=27.8 bits of the body reach the answer.
            rungs = flow(body)
            _meter_tick(len(body))
            self._send(200, {"rungs": rungs})
            return
        if p == '/reset':
            with LOCK:
                T.__init__(T.n)
                self._send(200, {"reset": True, "sigma_psi": T.sigma_psi()})
            return
        if p != '/tunnel':
            self._send(404, {"error": "not found"}); return
        try:
            req = json.loads(body or b'{}').get('request', '')
        except Exception:
            req = ''
        rb = req.encode() if isinstance(req, str) else bytes(req)
        with LOCK:
            ans = T.request(rb)
        self._send(200, ans)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8097
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cr_tunnel_api.pid"), "w") as f:
        f.write(str(os.getpid()))
    print("cr_tunnel_api on 127.0.0.1:%d" % port, flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
