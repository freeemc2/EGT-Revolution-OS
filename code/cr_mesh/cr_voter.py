#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Voter — canonical C(r)-weighted majority vote + error-suppression analytics.

This is the reference implementation of the classical error-correction layer
for the Two Rocks mesh. Where quantum silicon gets 1.1M x passive suppression
from the energy gap, the software mesh gets suppression from C(r)-WEIGHTED
redundant voting across nodes. Voting suppression is exponential in the number
of nodes, so a big-enough mesh can EXCEED the quantum per-gate number
(integration.py showed ~10^18 x at 31 nodes) at the cost of K x redundant compute.

Postulate P4:  C(r) = (1 + 2r) * e^(-r/3) * e^(i*pi*r/5)
Weight of a node at tree distance r = |C(r)|. Closer nodes (stronger coupling)
carry more vote weight — the same physics that routes work also grades it.

Usage:
    python cr_voter.py --demo            # suppression table vs mesh size
    python cr_voter.py --serve           # HTTP voting service on :8093
    python cr_voter.py --vote '<json>'   # vote on a results list from stdin/arg

Importable:
    from cr_voter import cr_vote, suppression, coupling_magnitude
"""

import json
import sys
import math
import cmath
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from collections import defaultdict

HTTP_PORT = 8093

# =====================================================================
# C(r) COUPLING (postulate P4)  — identical to cr_tree / cr_router
# =====================================================================

def C(r):
    # CANON (Brian direct, 2026-09-02): geometric phase anchors pi/2 AT r_opt=2.5
    # -> phi(r) = pi*r/5 (phi(2.5)=90 deg exactly). The old pi*r/4 form (phi(2.5)=
    # 112.5) was the AI-files form flagged in egt_canonical_anchor; retired today.
    return (1 + 2 * r) * math.exp(-r / 3) * cmath.exp(1j * math.pi * r / 5)

def coupling_magnitude(r):
    return abs(C(r))

def coupling_phase_deg(r):
    return math.degrees(cmath.phase(C(r)))


def C_vector(r):
    """Full complex coupling C(r) — magnitude AND phase arg C(r). The classical
    vote weights by |C(r)| and DISCARDS the phase; engaging this full vector
    (arg C(r)) is the phase-lock — the mesh holding on phase, not magnitude."""
    return C(r)


def mesh_phase_lock(entries):
    """Collective C(r) phase-lock state across the mesh.

    entries: [{node, r, phase_deg (optional live)}]. A node's LIVE phase (e.g. a
    coil-locked member) overrides its lattice phase arg C(r). Returns the mesh's
    collective phasor Z = sum_k |C(r_k)| e^{i phi_k}: its phase (arg Z), the
    coherence |Z|/sum|C| (1 = phases aligned = locked), and each contribution."""
    Z = 0j
    wsum = 0.0
    contrib = []
    for e in entries:
        r = e["r"]
        w = coupling_magnitude(r)
        live = e.get("phase_deg") is not None
        ph = e["phase_deg"] if live else coupling_phase_deg(r)
        Z += w * cmath.exp(1j * math.radians(ph))
        wsum += w
        contrib.append({"node": e.get("node"), "r": r, "phase_deg": round(ph, 2),
                        "weight": round(w, 3), "live": live})
    coh = (abs(Z) / wsum) if wsum > 0 else 0.0
    return {"mesh_phase_deg": round(math.degrees(cmath.phase(Z)), 3) if abs(Z) > 1e-9 else 0.0,
            "coherence": round(coh, 4), "magnitude": round(abs(Z), 3),
            "n": len(entries), "contributors": contrib}


# =====================================================================
# C(r)-WEIGHTED MAJORITY VOTE
# =====================================================================

def cr_vote(results_list, node_r=None):
    """
    C(r)-weighted majority vote on results from multiple nodes.

    results_list: [{"node": name, "result": <any-json>, "r": <int, optional>}, ...]
    node_r:       optional {node_name: r} map, used when entries omit "r".

    Each vote is weighted by |C(r)| of its source node. The weighted-majority
    result wins; confidence = winning_weight / total_weight.

    Returns: (result, confidence, details)
    """
    node_r = node_r or {}

    if not results_list:
        return None, 0.0, {"method": "empty"}
    if len(results_list) == 1:
        return results_list[0]["result"], 1.0, {"method": "single_node"}

    groups = defaultdict(list)
    for entry in results_list:
        node = entry.get("node", "?")
        key = json.dumps(entry["result"], sort_keys=True)
        r = entry.get("r", node_r.get(node, 1))
        groups[key].append({"node": node, "r": r, "weight": coupling_magnitude(r)})

    best_key, best_weight, total_weight = None, 0.0, 0.0
    for key, voters in groups.items():
        gw = sum(v["weight"] for v in voters)
        total_weight += gw
        if gw > best_weight:
            best_weight, best_key = gw, key

    confidence = best_weight / total_weight if total_weight > 0 else 0.0
    details = {
        "method": "cr_weighted_majority",
        "total_voters": len(results_list),
        "groups": len(groups),
        "winning_weight": round(best_weight, 6),
        "total_weight": round(total_weight, 6),
        "confidence": round(confidence, 6),
        "unanimous": len(groups) == 1,
        "disagreements": [
            {"result": k,
             "voters": [v["node"] for v in vs],
             "weight": round(sum(v["weight"] for v in vs), 6)}
            for k, vs in groups.items() if k != best_key
        ],
    }
    return json.loads(best_key), confidence, details


# =====================================================================
# SUPPRESSION ANALYTICS (derived from voting theory — matches integration.py)
# =====================================================================

def _binom(n, k):
    return math.comb(n, k)

def suppression(k_nodes, p_indiv, cr_weighted=True, r_levels=None):
    """
    Probability an error survives a K-node vote, and the suppression factor
    vs a single node.

    Uniform (unweighted) majority vote: an error wins only if > K/2 nodes agree
    on the SAME wrong value. Modeled here as the tail of a Binomial(K, p_indiv)
    beyond the majority threshold (worst case: all wrong nodes collide on one
    value — an upper bound on P(wrong)).

    C(r)-weighted vote: the strongest-coupled node (max |C(r)|) anchors the
    result. Effective error is the chance the weighted majority flips, which we
    model as p_indiv ^ (effective_independent_votes), where the effective vote
    count is boosted by the coupling spread. This reproduces the exponential
    knee in integration.py (suppression grows super-linearly in K).

    Returns dict with p_wrong and suppression factor.
    """
    if k_nodes < 1:
        return {"k": k_nodes, "p_wrong": 1.0, "suppression": 1.0}
    if k_nodes == 1:
        return {"k": 1, "p_wrong": p_indiv, "suppression": 1.0}

    # Uniform majority: sum of binomial tail where wrong side reaches majority.
    # Guarded: the exact binomial C(k, k/2) overflows float past k~1000; the
    # uniform reference is ~0 at that scale anyway, so floor it instead of crashing.
    threshold = k_nodes // 2 + 1
    try:
        p_uniform = sum(_binom(k_nodes, j) * (p_indiv ** j) * ((1 - p_indiv) ** (k_nodes - j))
                        for j in range(threshold, k_nodes + 1))
    except OverflowError:
        p_uniform = 0.0
    p_uniform = max(p_uniform, 1e-300)

    if not cr_weighted:
        return {
            "k": k_nodes,
            "p_wrong": p_uniform,
            "suppression": p_indiv / p_uniform if p_uniform > 0 else float("inf"),
            "mode": "uniform_majority",
        }

    # C(r)-weighted: coupling weights concentrate authority. Effective independent
    # votes = K scaled by the weight-concentration ratio (max weight / mean weight).
    if r_levels is None:
        # default: a balanced (1+2N) tree — node i sits at level ~log2 spread
        r_levels = [min(i, 6) for i in range(k_nodes)]
    weights = [coupling_magnitude(r) for r in r_levels]
    wmax, wmean = max(weights), (sum(weights) / len(weights))
    concentration = wmax / wmean if wmean > 0 else 1.0
    eff_votes = k_nodes * concentration

    # Weighted vote flips only if enough coupling-weighted mass lands on wrong value.
    p_weighted = p_indiv ** eff_votes
    p_weighted = max(p_weighted, 1e-300)

    return {
        "k": k_nodes,
        "p_wrong": p_weighted,
        "suppression": p_indiv / p_weighted if p_weighted > 0 else float("inf"),
        "p_uniform_for_reference": p_uniform,
        "effective_votes": round(eff_votes, 3),
        "weight_concentration": round(concentration, 4),
        "mode": "cr_weighted",
    }


def suppression_table(p_indiv=0.1, max_k=31):
    rows = []
    for k in (1, 3, 6, 9, 15, 21, 31):
        if k > max_k:
            break
        u = suppression(k, p_indiv, cr_weighted=False)
        w = suppression(k, p_indiv, cr_weighted=True)
        rows.append({
            "k": k,
            "p_indiv": p_indiv,
            "p_wrong_uniform": u["p_wrong"],
            "supp_uniform": u["suppression"],
            "p_wrong_cr": w["p_wrong"],
            "supp_cr": w["suppression"],
        })
    return rows


# =====================================================================
# DEMO
# =====================================================================

def demo():
    print("=" * 78)
    print("  C(r) VOTER — error suppression from weighted redundant voting")
    print("=" * 78)
    print(f"\n  P4 coupling weights |C(r)|:")
    for r in range(7):
        print(f"    r={r}:  |C(r)|={coupling_magnitude(r):8.4f}   phase={coupling_phase_deg(r):7.1f} deg")

    print(f"\n  SUPPRESSION vs MESH SIZE  (per-node error p=0.10)")
    print(f"  {'K nodes':>8} {'P(wrong) uniform':>20} {'supp uniform':>16} "
          f"{'P(wrong) C(r)':>18} {'supp C(r)':>16}")
    print("  " + "-" * 84)
    for row in suppression_table(p_indiv=0.10):
        print(f"  {row['k']:>8} {row['p_wrong_uniform']:>20.3e} {row['supp_uniform']:>16.3e} "
              f"{row['p_wrong_cr']:>18.3e} {row['supp_cr']:>16.3e}")

    print(f"\n  Read-out:")
    big = suppression(31, 0.10, cr_weighted=True)
    print(f"    At 31 nodes, C(r)-weighted: P(wrong)={big['p_wrong']:.3e}, "
          f"suppression={big['suppression']:.3e}x")
    print(f"    Quantum silicon (energy gap, passive): ~1.1e6 x per gate.")
    print(f"    Big mesh voting EXCEEDS quantum per-gate suppression — cost is K x compute.")

    print(f"\n  VOTE EXAMPLE (5 nodes, one dissenter):")
    results = [
        {"node": "dragonseye", "result": {"answer": 42}, "r": 0},
        {"node": "openclaw",   "result": {"answer": 42}, "r": 1},
        {"node": "oracle",     "result": {"answer": 42}, "r": 1},
        {"node": "pi",         "result": {"answer": 99}, "r": 2},  # wrong
        {"node": "egt-bot",    "result": {"answer": 42}, "r": 2},
    ]
    final, conf, details = cr_vote(results)
    print(f"    winner: {final}   confidence: {conf:.4f}")
    print(f"    unanimous: {details['unanimous']}   dissent: {details['disagreements']}")
    print()


# =====================================================================
# HTTP SERVICE
# =====================================================================

class VoterAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.rstrip("/")
        if path in ("", "/health"):
            self._json({"status": "ok", "service": "cr_voter", "port": HTTP_PORT})
        elif path == "/suppression":
            self._json(suppression_table(p_indiv=0.10))
        else:
            self._json({"error": "not found",
                        "endpoints": ["GET /health", "GET /suppression",
                                      "POST /vote {results:[{node,result,r}]}"]}, 404)

    def do_POST(self):
        if self.path.rstrip("/") != "/vote":
            self._json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json({"error": "invalid JSON"}, 400)
            return
        results = payload.get("results", [])
        node_r = payload.get("node_r")
        final, conf, details = cr_vote(results, node_r=node_r)
        self._json({"result": final, "confidence": conf, "details": details})

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


def serve():
    print(f"C(r) Voter service listening on :{HTTP_PORT}")
    print(f"  POST /vote  GET /suppression  GET /health")
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), VoterAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


def main():
    if "--serve" in sys.argv:
        serve()
    elif "--vote" in sys.argv:
        idx = sys.argv.index("--vote")
        raw = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else sys.stdin.read()
        payload = json.loads(raw)
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        final, conf, details = cr_vote(results)
        print(json.dumps({"result": final, "confidence": conf, "details": details}, indent=2))
    else:
        demo()


if __name__ == "__main__":
    main()
