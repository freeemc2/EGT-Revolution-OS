#!/usr/bin/env python3
# cr_tunnel_api.py — wire the readable-throughput tunnel as an HTTP endpoint.
# POST /tunnel  {"request": "<text>"} -> {"rungs":[...], "sigma_psi_rung":n, "j":n}
#   one push winds through the live 64-register coupled set (Sigma-psi conserved),
#   reads the rung-tuple out = the answer. The set FLOWS (cumulative); /reset reseeds.
# GET  /health -> {n, sigma_psi}
# POST /reset  -> reseed the flowing set (for determinism replay)
# stdlib only. arc, 2026-10-03.
import json, sys, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr_tunnel import Tunnel

T = Tunnel()
LOCK = threading.Lock()

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
        if self.path.rstrip('/') == '/health':
            with LOCK:
                self._send(200, {"tunnel": "egt", "n": T.n, "sigma_psi": T.sigma_psi()})
        else:
            self._send(404, {"error": "not found"})
    def do_POST(self):
        p = self.path.rstrip('/')
        n = int(self.headers.get('Content-Length', 0) or 0)
        body = self.rfile.read(n) if n else b'{}'
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
