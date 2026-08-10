#!/usr/bin/env python3
"""
C(r) Task Router

Routes tasks to compute nodes using C(r) coupling weights.
Supports redundant execution with C(r)-weighted voting.
Serves API at :8092. Reads tree state from cr_tree.py (:8091).

Usage:
    python cr_router.py                    # start daemon
    python cr_router.py --submit "task"    # submit a test task
    python cr_router.py --status           # show router status
"""

import json
import sys
import time
import math
import cmath
import uuid
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from collections import defaultdict

# =====================================================================
# C(r) COUPLING (postulate P4)
# =====================================================================

def C(r):
    return (1 + 2*r) * math.exp(-r/3) * cmath.exp(1j * math.pi * r / 4)

def coupling_magnitude(r):
    return abs(C(r))

# =====================================================================
# CONFIGURATION
# =====================================================================

HTTP_PORT = 8092
TREE_API = "http://localhost:8091"
MAX_TASKS = 10000
TASK_TIMEOUT_S = 30

# =====================================================================
# TASK STORE
# =====================================================================

class TaskStore:
    def __init__(self):
        self.tasks = {}       # task_id -> task
        self.results = {}     # task_id -> result
        self.lock = threading.Lock()
        self.stats = {
            "submitted": 0,
            "routed": 0,
            "completed": 0,
            "failed": 0,
            "voted": 0
        }

    def submit(self, task_data):
        task_id = str(uuid.uuid4())[:12]
        task = {
            "id": task_id,
            "data": task_data,
            "status": "pending",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "routed_to": [],
            "results_received": [],
            "final_result": None,
            "confidence": None,
            "routing_decision": None
        }
        with self.lock:
            self.tasks[task_id] = task
            self.stats["submitted"] += 1
            # Trim old tasks
            if len(self.tasks) > MAX_TASKS:
                oldest = sorted(self.tasks.keys())[:len(self.tasks) - MAX_TASKS]
                for old_id in oldest:
                    del self.tasks[old_id]
        return task_id

    def get(self, task_id):
        return self.tasks.get(task_id)

    def update(self, task_id, **kwargs):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)

    def add_result(self, task_id, node_name, result):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["results_received"].append({
                    "node": node_name,
                    "result": result,
                    "received_at": datetime.now(timezone.utc).isoformat()
                })

    def get_recent(self, limit=20):
        with self.lock:
            items = sorted(self.tasks.values(),
                           key=lambda t: t["submitted_at"], reverse=True)
            return items[:limit]

    def get_stats(self):
        with self.lock:
            pending = sum(1 for t in self.tasks.values() if t["status"] == "pending")
            routed = sum(1 for t in self.tasks.values() if t["status"] == "routed")
            done = sum(1 for t in self.tasks.values() if t["status"] == "completed")
            return {**self.stats, "pending": pending, "in_flight": routed, "done": done}


store = TaskStore()

# =====================================================================
# TREE CLIENT
# =====================================================================

def get_tree():
    """Fetch current tree from cr_tree.py API."""
    try:
        req = urllib.request.Request(f"{TREE_API}/tree")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[router] tree API error: {e}")
        return None


def get_online_nodes():
    """Fetch online nodes from tree API."""
    try:
        req = urllib.request.Request(f"{TREE_API}/tree/online")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return {}


# =====================================================================
# C(r) ROUTING ALGORITHM
# =====================================================================

def route_task(task, tree, redundancy=1):
    """
    Route a task to optimal node(s) using C(r) coupling weights.

    Algorithm:
      1. Get all online nodes from tree
      2. Compute C(r) from root to each node
      3. Score = |C(r)| * cores * (1 / (1 + rtt_ms/100))
      4. Sort by score descending
      5. Select top-K nodes (K = redundancy level)
      6. Compute phase offsets for pipeline staggering

    Returns routing decision with selected nodes and weights.
    """
    if not tree or "nodes" not in tree:
        return None

    candidates = []
    for name, node in tree["nodes"].items():
        if not node.get("online", False):
            continue
        if name == tree.get("root"):
            # Root dispatches, doesn't compute (unless only node)
            if len([n for n in tree["nodes"].values() if n.get("online")]) > 1:
                continue

        r = node.get("r", 0)
        rtt = node.get("rtt_ms", 0)
        cores = node.get("cores", 1)
        coupling = coupling_magnitude(r) if r >= 0 else 0

        # Score: coupling strength * compute power * latency factor
        latency_factor = 1 / (1 + rtt / 100) if rtt >= 0 else 0.1
        score = coupling * cores * latency_factor

        candidates.append({
            "name": name,
            "r": r,
            "coupling": coupling,
            "phase_deg": node.get("phase_deg", 0),
            "cores": cores,
            "rtt_ms": rtt,
            "latency_factor": latency_factor,
            "score": score,
            "ip": node.get("ip", "")
        })

    if not candidates:
        return None

    # Sort by score (highest coupling * compute * 1/latency first)
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # Select top-K
    selected = candidates[:redundancy]

    # Compute aggregate coupling weight (for voting)
    total_weight = sum(c["coupling"] for c in selected)

    decision = {
        "candidates_evaluated": len(candidates),
        "selected": selected,
        "redundancy": len(selected),
        "total_coupling_weight": total_weight,
        "routing_strategy": "cr_weighted" if redundancy > 1 else "cr_optimal"
    }

    return decision


# =====================================================================
# C(r) VOTING (error correction)
# =====================================================================

def cr_vote(results_list, tree):
    """
    C(r)-weighted majority vote on results from multiple nodes.

    Each result is weighted by |C(r)| of its source node.
    Majority by weight wins.

    Returns: (result, confidence, vote_details)
    """
    if not results_list:
        return None, 0, {}

    if len(results_list) == 1:
        return results_list[0]["result"], 1.0, {"method": "single_node"}

    # Group by result value
    result_groups = defaultdict(list)
    for entry in results_list:
        node = entry["node"]
        result_val = json.dumps(entry["result"], sort_keys=True)

        # Get coupling weight from tree
        r = 1  # default
        if tree and "nodes" in tree:
            node_info = tree["nodes"].get(node, {})
            r = node_info.get("r", 1)
        weight = coupling_magnitude(r)

        result_groups[result_val].append({
            "node": node,
            "weight": weight,
            "r": r
        })

    # Find majority by weight
    best_result_key = None
    best_weight = 0
    total_weight = 0

    for result_key, voters in result_groups.items():
        group_weight = sum(v["weight"] for v in voters)
        total_weight += group_weight
        if group_weight > best_weight:
            best_weight = group_weight
            best_result_key = result_key

    confidence = best_weight / total_weight if total_weight > 0 else 0

    vote_details = {
        "method": "cr_weighted_majority",
        "total_voters": len(results_list),
        "groups": len(result_groups),
        "winning_weight": best_weight,
        "total_weight": total_weight,
        "confidence": confidence,
        "unanimous": len(result_groups) == 1,
        "disagreements": [
            {"result": k, "voters": [v["node"] for v in vs],
             "weight": sum(v["weight"] for v in vs)}
            for k, vs in result_groups.items()
            if k != best_result_key
        ]
    }

    return json.loads(best_result_key), confidence, vote_details


# =====================================================================
# TASK EXECUTOR (simulated for now — real dispatch via HTTP later)
# =====================================================================

def execute_on_node(node_info, task_data):
    """
    Execute a task on a remote node.

    Phase 1: simulate execution (node "computes" locally as proxy).
    Phase 2: HTTP dispatch to node worker.
    """
    # For now, simulate computation locally
    # The task_data contains the computation description
    # Result = hash of (task_data + node_name) to simulate node-specific execution
    node_name = node_info["name"]
    result = {
        "computed_by": node_name,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "input_hash": hash(json.dumps(task_data, sort_keys=True)) % (2**32),
        "simulated": True
    }
    return result


def process_task(task_id):
    """Route, execute, vote, complete a task."""
    task = store.get(task_id)
    if not task:
        return

    tree = get_tree()
    if not tree:
        store.update(task_id, status="failed", error="tree unavailable")
        store.stats["failed"] += 1
        return

    # Determine redundancy from task priority
    task_data = task["data"]
    redundancy = task_data.get("redundancy", 1) if isinstance(task_data, dict) else 1

    # Route
    decision = route_task(task, tree, redundancy=redundancy)
    if not decision or not decision["selected"]:
        store.update(task_id, status="failed", error="no nodes available")
        store.stats["failed"] += 1
        return

    store.update(task_id, status="routed", routing_decision=decision,
                 routed_to=[n["name"] for n in decision["selected"]])
    store.stats["routed"] += 1

    # Execute on each selected node
    for node_info in decision["selected"]:
        try:
            result = execute_on_node(node_info, task_data)
            store.add_result(task_id, node_info["name"], result)
        except Exception as e:
            store.add_result(task_id, node_info["name"], {"error": str(e)})

    # Vote if redundant
    task = store.get(task_id)
    results_received = task.get("results_received", [])

    if len(results_received) > 1:
        final, confidence, details = cr_vote(results_received, tree)
        store.update(task_id, status="completed", final_result=final,
                     confidence=confidence, vote_details=details)
        store.stats["voted"] += 1
    elif results_received:
        store.update(task_id, status="completed",
                     final_result=results_received[0]["result"],
                     confidence=1.0)
    else:
        store.update(task_id, status="failed", error="no results received")
        store.stats["failed"] += 1
        return

    store.stats["completed"] += 1


# =====================================================================
# HTTP API
# =====================================================================

class RouterAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "" or path == "/status":
            tree = get_tree()
            online = get_online_nodes()
            self._json_response({
                "status": "ok",
                "tree_connected": tree is not None,
                "nodes_online": len(online),
                "tasks": store.get_stats()
            })

        elif path == "/tasks":
            self._json_response(store.get_recent(50))

        elif path.startswith("/task/"):
            task_id = path.split("/task/")[1]
            task = store.get(task_id)
            if task:
                self._json_response(task)
            else:
                self._json_response({"error": "not found"}, 404)

        elif path == "/routing-table":
            tree = get_tree()
            if tree:
                dummy_task = {"type": "test"}
                for k in [1, 3, 5]:
                    decision = route_task({"data": dummy_task}, tree, redundancy=k)
                    if decision:
                        decision["redundancy_requested"] = k
                self._json_response({
                    "single": route_task({"data": dummy_task}, tree, redundancy=1),
                    "triple": route_task({"data": dummy_task}, tree, redundancy=3),
                    "full": route_task({"data": dummy_task}, tree,
                                       redundancy=len([n for n in tree["nodes"].values()
                                                       if n.get("online")]))
                })
            else:
                self._json_response({"error": "tree unavailable"})

        elif path == "/health":
            self._json_response({"status": "ok", "port": HTTP_PORT})

        else:
            self._json_response({"error": "not found", "endpoints": [
                "GET  /status", "GET  /tasks", "GET  /task/<id>",
                "GET  /routing-table", "GET  /health",
                "POST /submit  {data, redundancy?}",
            ]}, 404)

    def do_POST(self):
        path = self.path.rstrip("/")

        if path == "/submit":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._json_response({"error": "invalid JSON"}, 400)
                return

            task_id = store.submit(payload)

            # Process in background
            threading.Thread(target=process_task, args=(task_id,), daemon=True).start()

            self._json_response({"task_id": task_id, "status": "submitted"}, 201)

        else:
            self._json_response({"error": "not found"}, 404)

    def _json_response(self, data, code=200):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


# =====================================================================
# MAIN
# =====================================================================

def main():
    if "--status" in sys.argv:
        try:
            req = urllib.request.Request(f"http://localhost:{HTTP_PORT}/status")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"router not running: {e}")
        return

    if "--submit" in sys.argv:
        idx = sys.argv.index("--submit")
        task_data = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "test"
        redundancy = 1
        if "--redundancy" in sys.argv:
            r_idx = sys.argv.index("--redundancy")
            redundancy = int(sys.argv[r_idx + 1]) if r_idx + 1 < len(sys.argv) else 1

        payload = {"data": task_data, "redundancy": redundancy}
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"http://localhost:{HTTP_PORT}/submit",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                print(json.dumps(result, indent=2))
                # Wait and fetch result
                task_id = result["task_id"]
                time.sleep(1)
                req2 = urllib.request.Request(f"http://localhost:{HTTP_PORT}/task/{task_id}")
                with urllib.request.urlopen(req2, timeout=5) as resp2:
                    print(json.dumps(json.loads(resp2.read()), indent=2))
        except Exception as e:
            print(f"submit failed: {e}")
        return

    # Check tree API
    print("C(r) Task Router")
    tree = get_tree()
    if tree:
        online = sum(1 for n in tree["nodes"].values() if n.get("online"))
        print(f"tree connected: {online} nodes online")
    else:
        print("WARNING: tree API not reachable at", TREE_API)
        print("start cr_tree.py first, or router will retry on each request")

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", HTTP_PORT), RouterAPIHandler)
    print(f"router API listening on :{HTTP_PORT}")
    print(f"submit tasks: POST http://localhost:{HTTP_PORT}/submit")
    print(f"check status: GET  http://localhost:{HTTP_PORT}/status")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
