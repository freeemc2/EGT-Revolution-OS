#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Monitor — entropy / jitter / suppression dashboard for the Two Rocks mesh.

Pulls live state from cr_tree.py (:8091) and cr_router.py (:8092), computes the
health numbers that matter for the architecture (total coupling, effective
suppression from the current node count, entanglement-entropy proxy, cumulative
jitter over a kernel run), and serves them as JSON (/metrics) and a live
auto-refreshing HTML dashboard (/).

The entropy/jitter model mirrors two_rocks_breaking_point.py: jitter accrues per
tick, entropy grows with tree depth, and C(r) suppression is what keeps the
computation on the clean side of the classical->quantum line.

Usage:
    python cr_monitor.py            # serve dashboard on :8095
    python cr_monitor.py --once     # print metrics once and exit
"""

import json
import sys
import math
import cmath
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HTTP_PORT = 8095
TREE_API = "http://127.0.0.1:8091"
ROUTER_API = "http://127.0.0.1:8092"

# Physical constants from the breaking-point / silicon models
JITTER_PER_TICK_NS = 0.1      # 1% of a 10ns gate
KERNEL_TICKS = 127            # reference tree-hash kernel
BASE_ERROR = 0.10             # per-node/per-gate software error proxy


def C(r):
    return (1 + 2 * r) * math.exp(-r / 3) * cmath.exp(1j * math.pi * r / 5)

def coupling_magnitude(r):
    return abs(C(r))


def _get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=4) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def compute_metrics():
    tree = _get(f"{TREE_API}/tree")
    router = _get(f"{ROUTER_API}/status")

    online_nodes, depth, total_coupling, max_coupling = 0, 0, 0.0, 0.0
    node_rows = []
    if tree and "nodes" in tree:
        for name, n in tree["nodes"].items():
            if n.get("online"):
                online_nodes += 1
                r = max(0, n.get("r", 0))
                cm = coupling_magnitude(r)
                total_coupling += cm
                max_coupling = max(max_coupling, cm)
                depth = max(depth, n.get("level", 0))
                node_rows.append({"node": name, "r": r, "coupling": round(cm, 4),
                                  "cores": n.get("cores", 1), "rtt_ms": n.get("rtt_ms", -1)})

    # Suppression from current mesh size (C(r)-weighted voting proxy).
    # p_wrong ~ base_error ^ (effective votes); effective votes boosted by coupling spread.
    if online_nodes >= 1 and node_rows:
        weights = [coupling_magnitude(nr["r"]) for nr in node_rows]
        wmean = sum(weights) / len(weights)
        concentration = (max(weights) / wmean) if wmean > 0 else 1.0
        eff_votes = max(1.0, online_nodes * concentration)
        p_wrong = max(BASE_ERROR ** eff_votes, 1e-300)
        suppression = BASE_ERROR / p_wrong
    else:
        eff_votes, p_wrong, suppression = 1.0, BASE_ERROR, 1.0

    # Entropy proxy (entanglement growth ~ depth-scaled, mirrors breaking_point)
    entropy_proxy = round(depth * 8 + online_nodes, 2)  # ebits-ish
    quantum_line = 48  # S>48 == classically intractable in the breaking-point model
    regime = "QUANTUM (classically intractable)" if entropy_proxy > quantum_line else "classical-simulable"

    # Cumulative jitter over a kernel run
    cumulative_jitter_ns = round(math.sqrt(KERNEL_TICKS) * JITTER_PER_TICK_NS, 4)
    coherence_budget_ns = 1_000_000  # T2 ~ 1ms
    jitter_headroom = round(coherence_budget_ns / (KERNEL_TICKS * 10.0), 1)  # ticks*gate vs T2

    return {
        "mesh": {
            "online_nodes": online_nodes,
            "tree_depth": depth,
            "total_coupling": round(total_coupling, 4),
            "max_coupling": round(max_coupling, 4),
            "nodes": sorted(node_rows, key=lambda x: -x["coupling"]),
            "tree_connected": tree is not None,
            "router_connected": router is not None,
        },
        "suppression": {
            "base_error": BASE_ERROR,
            "effective_votes": round(eff_votes, 3),
            "p_wrong": p_wrong,
            "suppression_factor": suppression,
        },
        "entropy": {
            "entropy_proxy_ebits": entropy_proxy,
            "quantum_line_ebits": quantum_line,
            "regime": regime,
        },
        "jitter": {
            "per_tick_ns": JITTER_PER_TICK_NS,
            "kernel_ticks": KERNEL_TICKS,
            "cumulative_jitter_ns": cumulative_jitter_ns,
            "coherence_headroom_x": jitter_headroom,
        },
        "tasks": (router or {}).get("tasks", {}) if router else {},
    }


DASHBOARD_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>C(r) Mesh Monitor</title>
<meta http-equiv="refresh" content="5">
<style>
 body{background:#0b0e14;color:#c9d1d9;font-family:ui-monospace,Menlo,Consolas,monospace;margin:0;padding:24px}
 h1{color:#58a6ff;font-size:20px;margin:0 0 4px} .sub{color:#6e7681;font-size:12px;margin-bottom:20px}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
 .card{background:#11161f;border:1px solid #21262d;border-radius:10px;padding:16px}
 .card h2{font-size:12px;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;margin:0 0 12px}
 .big{font-size:28px;font-weight:700} .unit{font-size:13px;color:#6e7681}
 .green{color:#3fb950}.red{color:#f85149}.yellow{color:#d29922}.blue{color:#58a6ff}
 table{width:100%;border-collapse:collapse;font-size:12px} td,th{text-align:left;padding:4px 8px;border-bottom:1px solid #21262d}
 th{color:#6e7681;font-weight:500} .pill{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px}
 .ok{background:#12261a;color:#3fb950}.warn{background:#2b2410;color:#d29922}
</style></head><body>
<h1>C(r) Mesh Monitor</h1><div class="sub">Two Rocks software mesh — live at :8095 — auto-refresh 5s</div>
<div class="grid" id="cards"></div>
<script>
async function load(){
 const m = await (await fetch('/metrics')).json();
 const supp = m.suppression.suppression_factor;
 const suppStr = supp>=1e6 ? supp.toExponential(2) : Math.round(supp).toLocaleString();
 const regimeQ = m.entropy.regime.startsWith('QUANTUM');
 const cards = [
  ['MESH NODES', `<div class="big blue">${m.mesh.online_nodes}</div><div class="unit">online, depth ${m.mesh.tree_depth}</div>
     <div class="unit">tree ${m.mesh.tree_connected?'<span class=green>connected</span>':'<span class=red>down</span>'} ·
     router ${m.mesh.router_connected?'<span class=green>connected</span>':'<span class=red>down</span>'}</div>`],
  ['ERROR SUPPRESSION', `<div class="big green">${suppStr}&times;</div>
     <div class="unit">p(wrong)=${m.suppression.p_wrong.toExponential(2)} · eff votes ${m.suppression.effective_votes}</div>
     <div class="unit">base error ${m.suppression.base_error}</div>`],
  ['ENTROPY REGIME', `<div class="big ${regimeQ?'red':'yellow'}">${m.entropy.entropy_proxy_ebits}</div>
     <div class="unit">ebits (quantum line ${m.entropy.quantum_line_ebits})</div>
     <div><span class="pill ${regimeQ?'warn':'ok'}">${m.entropy.regime}</span></div>`],
  ['JITTER / COHERENCE', `<div class="big blue">${m.jitter.cumulative_jitter_ns}</div><div class="unit">ns cumulative over ${m.jitter.kernel_ticks} ticks</div>
     <div class="unit">headroom ${m.jitter.coherence_headroom_x}&times; vs T2</div>`],
  ['TASKS', `<div class="big">${(m.tasks.completed||0)}</div><div class="unit">completed · ${(m.tasks.voted||0)} voted · ${(m.tasks.failed||0)} failed</div>`],
 ];
 let nodeTable = '<table><tr><th>node</th><th>r</th><th>|C(r)|</th><th>cores</th><th>rtt</th></tr>';
 for(const n of m.mesh.nodes){ nodeTable += `<tr><td>${n.node}</td><td>${n.r}</td><td>${n.coupling}</td><td>${n.cores}</td><td>${n.rtt_ms}ms</td></tr>`; }
 nodeTable += '</table>';
 cards.push(['NODE COUPLING TABLE', nodeTable]);
 document.getElementById('cards').innerHTML = cards.map(([t,b])=>`<div class="card"><h2>${t}</h2>${b}</div>`).join('');
}
load();
</script></body></html>"""


class MonitorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.rstrip("/")
        if path == "" or path == "/dashboard":
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/metrics":
            self._json(compute_metrics())
        elif path == "/health":
            self._json({"status": "ok", "service": "cr_monitor", "port": HTTP_PORT})
        else:
            self._json({"error": "not found",
                        "endpoints": ["GET /", "GET /metrics", "GET /health"]}, 404)

    def _json(self, data, code=200):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main():
    if "--once" in sys.argv:
        print(json.dumps(compute_metrics(), indent=2))
        return
    print("C(r) Monitor — entropy/jitter/suppression dashboard")
    print(f"  dashboard: http://localhost:{HTTP_PORT}/")
    print(f"  metrics:   http://localhost:{HTTP_PORT}/metrics")
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), MonitorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
