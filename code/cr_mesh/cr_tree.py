#!/usr/bin/env python3
"""
C(r) Tree Topology Manager

Organizes compute nodes in a (1+2N) binary tree.
Computes C(r) coupling weights for all edges.
Serves the tree via HTTP API at :8091.
Pings nodes periodically for health.

Runs on Dragon's Eye (Windows). Reaches nodes via Tailscale.

Usage:
    python cr_tree.py                  # start daemon
    python cr_tree.py --once           # build tree, print, exit
    python cr_tree.py --add NAME IP    # add a node to config
"""

import json
import os
import sys
import time
import subprocess
import threading
import math
import cmath
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone

# =====================================================================
# C(r) COUPLING (postulate P4)
# =====================================================================

def C(r):
    """P4: coupling function. Returns complex."""
    return (1 + 2*r) * math.exp(-r/3) * cmath.exp(1j * math.pi * r / 5)

def coupling_magnitude(r):
    return abs(C(r))

def coupling_phase_deg(r):
    return math.degrees(cmath.phase(C(r)))


# =====================================================================
# CONFIGURATION
# =====================================================================

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "mesh_config.json"
TREE_STATE_FILE = CONFIG_DIR / "tree_state.json"
HTTP_PORT = 8091
PING_INTERVAL_S = 60
PING_TIMEOUT_MS = 2000

DEFAULT_CONFIG = {
    "nodes": {
        "dragonseye": {
            "ip": "100.121.177.94",
            "type": "x86",
            "cores": 16,
            "role": "root",
            "description": "Dragon's Eye - main compute (Windows)"
        },
        "openclaw-prod": {
            "ip": "100.86.79.99",
            "type": "x86",
            "cores": 4,
            "role": "compute",
            "description": "OpenClaw VPS - Flask/Redis"
        },
        "pi": {
            "ip": "100.81.123.41",
            "type": "arm",
            "cores": 4,
            "role": "edge",
            "description": "Pi5 - edge node"
        },
        "oracle": {
            "ip": "100.114.92.17",
            "type": "x86",
            "cores": 2,
            "role": "compute",
            "description": "Oracle VPS"
        },
        "egt-bot": {
            "ip": "100.98.78.103",
            "type": "x86",
            "cores": 2,
            "role": "compute",
            "description": "EGT bot VPS"
        },
        "elevateprogram-scraper": {
            "ip": "100.125.99.45",
            "type": "x86",
            "cores": 2,
            "role": "scraper",
            "description": "Elevate scraper VPS"
        }
    },
    "tree": {
        "root": "dragonseye",
        "ping_interval_s": PING_INTERVAL_S,
        "ping_timeout_ms": PING_TIMEOUT_MS
    }
}


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# =====================================================================
# NODE HEALTH
# =====================================================================

def ping_node(ip, timeout_ms=PING_TIMEOUT_MS):
    """Ping a node, return RTT in ms or None if unreachable."""
    try:
        if sys.platform == "win32":
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout_ms // 1000 or 1), ip]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms/1000 + 2)

        if result.returncode == 0:
            output = result.stdout
            # Parse RTT from ping output
            if "time=" in output:
                for part in output.split("time=")[1:]:
                    try:
                        rtt = float(part.split("ms")[0].strip().rstrip("m"))
                        return rtt
                    except ValueError:
                        continue
            if "time<" in output:
                return 0.5  # sub-millisecond
            return 1.0  # got a response but couldn't parse RTT
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def check_all_nodes(nodes):
    """Ping all nodes, return {name: {online, rtt_ms}}."""
    results = {}
    for name, info in nodes.items():
        if info["ip"] == "100.121.177.94":
            # This is us (Dragon's Eye) — always online
            results[name] = {"online": True, "rtt_ms": 0.0}
        else:
            rtt = ping_node(info["ip"])
            results[name] = {
                "online": rtt is not None,
                "rtt_ms": rtt if rtt is not None else -1
            }
    return results


# =====================================================================
# (1+2N) BINARY TREE BUILDER
# =====================================================================

def build_tree(config, health):
    """
    Build (1+2N) binary tree from available nodes.

    Algorithm:
      1. Root = configured root node (Dragon's Eye)
      2. Sort remaining nodes by RTT (lowest = closest = strongest coupling)
      3. Assign to tree levels breadth-first
      4. Compute C(r) weights for each edge
    """
    nodes = config["nodes"]
    root_name = config["tree"]["root"]

    # Separate root from others
    online_nodes = [name for name, h in health.items()
                    if h["online"] and name != root_name]

    # Sort by RTT (lowest first = closest to root)
    online_nodes.sort(key=lambda n: health[n].get("rtt_ms", 9999))

    # Build tree structure
    tree = {
        "root": root_name,
        "nodes": {},
        "edges": [],
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_online": len(online_nodes) + 1,
        "total_configured": len(nodes)
    }

    # Root node at level 0
    tree["nodes"][root_name] = {
        "level": 0,
        "r": 0,
        "parent": None,
        "children": [],
        "coupling": coupling_magnitude(0),
        "phase_deg": coupling_phase_deg(0),
        "online": True,
        "rtt_ms": 0.0,
        "ip": nodes[root_name]["ip"],
        "type": nodes[root_name].get("type", "unknown"),
        "cores": nodes[root_name].get("cores", 1)
    }

    # Assign nodes breadth-first to binary tree
    # Queue of parents that can accept children (max 2 each)
    parent_queue = [root_name]
    child_slots = {root_name: 2}  # each parent can have 2 children

    for node_name in online_nodes:
        if not parent_queue:
            break

        # Find parent with available slot
        parent = parent_queue[0]
        level = tree["nodes"][parent]["level"] + 1
        r = level  # tree distance = level in the tree

        tree["nodes"][node_name] = {
            "level": level,
            "r": r,
            "parent": parent,
            "children": [],
            "coupling": coupling_magnitude(r),
            "phase_deg": coupling_phase_deg(r),
            "online": True,
            "rtt_ms": health[node_name]["rtt_ms"],
            "ip": nodes[node_name]["ip"],
            "type": nodes[node_name].get("type", "unknown"),
            "cores": nodes[node_name].get("cores", 1)
        }

        # Add edge
        tree["edges"].append({
            "from": parent,
            "to": node_name,
            "r": r,
            "coupling": coupling_magnitude(r),
            "phase_deg": coupling_phase_deg(r),
            "rtt_ms": health[node_name]["rtt_ms"]
        })

        # Update parent
        tree["nodes"][parent]["children"].append(node_name)
        child_slots[parent] -= 1
        if child_slots[parent] == 0:
            parent_queue.pop(0)

        # This node can also be a parent
        parent_queue.append(node_name)
        child_slots[node_name] = 2

    # Add offline nodes as disconnected
    for name in nodes:
        if name not in tree["nodes"]:
            tree["nodes"][name] = {
                "level": -1,
                "r": -1,
                "parent": None,
                "children": [],
                "coupling": 0,
                "phase_deg": 0,
                "online": False,
                "rtt_ms": -1,
                "ip": nodes[name]["ip"],
                "type": nodes[name].get("type", "unknown"),
                "cores": nodes[name].get("cores", 1)
            }

    # Compute aggregate stats
    online_couplings = [n["coupling"] for n in tree["nodes"].values() if n["online"]]
    tree["stats"] = {
        "total_coupling": sum(online_couplings),
        "max_coupling": max(online_couplings) if online_couplings else 0,
        "min_coupling": min(c for c in online_couplings if c > 0) if any(c > 0 for c in online_couplings) else 0,
        "tree_depth": max((n["level"] for n in tree["nodes"].values() if n["online"]), default=0),
        "online_cores": sum(n["cores"] for n in tree["nodes"].values() if n["online"])
    }

    return tree


def save_tree(tree):
    with open(TREE_STATE_FILE, "w") as f:
        json.dump(tree, f, indent=2)


def load_tree():
    if TREE_STATE_FILE.exists():
        with open(TREE_STATE_FILE) as f:
            return json.load(f)
    return None


# =====================================================================
# TREE DISPLAY
# =====================================================================

def print_tree(tree):
    """Pretty-print the tree."""
    print(f"\n  (1+2N) BINARY TREE — built {tree['built_at']}")
    print(f"  {tree['total_online']}/{tree['total_configured']} nodes online\n")

    def print_node(name, indent=0):
        node = tree["nodes"][name]
        status = "ONLINE" if node["online"] else "OFFLINE"
        prefix = "  " + "  |   " * indent + "+-- " if indent > 0 else "  "
        coupling_str = f"|C({node['r']})|={node['coupling']:.3f}" if node['r'] >= 0 else "disconnected"
        rtt_str = f"RTT={node['rtt_ms']:.1f}ms" if node['rtt_ms'] >= 0 else ""
        print(f"{prefix}{name} (r={node['r']}, {coupling_str}, "
              f"{node['cores']}c, {rtt_str}, {status})")
        for child in node.get("children", []):
            print_node(child, indent + 1)

    print_node(tree["root"])

    print(f"\n  Stats:")
    for k, v in tree["stats"].items():
        print(f"    {k}: {v}")
    print()


# =====================================================================
# HTTP API
# =====================================================================

class TreeAPIHandler(BaseHTTPRequestHandler):
    tree = None
    config = None
    last_health = None

    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "" or path == "/tree":
            self._json_response(self.tree or {})
        elif path == "/tree/nodes":
            self._json_response(self.tree.get("nodes", {}) if self.tree else {})
        elif path.startswith("/tree/node/"):
            name = path.split("/tree/node/")[1]
            node = (self.tree or {}).get("nodes", {}).get(name)
            if node:
                self._json_response(node)
            else:
                self._json_response({"error": f"node {name} not found"}, 404)
        elif path == "/tree/edges":
            self._json_response(self.tree.get("edges", []) if self.tree else [])
        elif path == "/tree/stats":
            self._json_response(self.tree.get("stats", {}) if self.tree else {})
        elif path == "/tree/online":
            if self.tree:
                online = {k: v for k, v in self.tree["nodes"].items() if v["online"]}
                self._json_response(online)
            else:
                self._json_response({})
        elif path == "/health":
            self._json_response({
                "status": "ok",
                "tree_built": self.tree.get("built_at") if self.tree else None,
                "nodes_online": self.tree.get("total_online", 0) if self.tree else 0,
                "last_health_check": self.last_health is not None
            })
        elif path == "/coupling":
            # Return coupling table for all pairs
            if self.tree:
                pairs = []
                names = [n for n, v in self.tree["nodes"].items() if v["online"]]
                for i, a in enumerate(names):
                    for b in names[i+1:]:
                        r_a = self.tree["nodes"][a]["level"]
                        r_b = self.tree["nodes"][b]["level"]
                        r_dist = abs(r_a - r_b)
                        pairs.append({
                            "a": a, "b": b,
                            "r": r_dist,
                            "coupling": coupling_magnitude(r_dist),
                            "phase_deg": coupling_phase_deg(r_dist)
                        })
                self._json_response(pairs)
            else:
                self._json_response([])
        elif path == "/refresh":
            # Trigger a tree rebuild
            threading.Thread(target=self._rebuild, daemon=True).start()
            self._json_response({"status": "rebuilding"})
        else:
            self._json_response({"error": "not found", "endpoints": [
                "/tree", "/tree/nodes", "/tree/node/<name>",
                "/tree/edges", "/tree/stats", "/tree/online",
                "/health", "/coupling", "/refresh"
            ]}, 404)

    def _rebuild(self):
        health = check_all_nodes(self.config["nodes"])
        TreeAPIHandler.last_health = health
        TreeAPIHandler.tree = build_tree(self.config, health)
        save_tree(TreeAPIHandler.tree)

    def _json_response(self, data, code=200):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silence request logs


# =====================================================================
# DAEMON
# =====================================================================

def health_loop(config, interval):
    """Periodically rebuild the tree."""
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] pinging nodes...")
            health = check_all_nodes(config["nodes"])
            TreeAPIHandler.last_health = health

            online = sum(1 for h in health.values() if h["online"])
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {online}/{len(health)} online")

            tree = build_tree(config, health)
            TreeAPIHandler.tree = tree
            save_tree(tree)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] tree rebuilt, "
                  f"depth={tree['stats']['tree_depth']}, "
                  f"cores={tree['stats']['online_cores']}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] health check error: {e}")

        time.sleep(interval)


def main():
    config = load_config()

    if "--add" in sys.argv:
        idx = sys.argv.index("--add")
        if idx + 2 < len(sys.argv):
            name = sys.argv[idx + 1]
            ip = sys.argv[idx + 2]
            config["nodes"][name] = {"ip": ip, "type": "x86", "cores": 2, "role": "compute"}
            save_config(config)
            print(f"added {name} at {ip}")
        else:
            print("usage: --add NAME IP")
        return

    # Initial build
    print("C(r) Tree Topology Manager")
    print(f"nodes configured: {len(config['nodes'])}")
    print("pinging all nodes...")

    health = check_all_nodes(config["nodes"])
    tree = build_tree(config, health)
    TreeAPIHandler.tree = tree
    TreeAPIHandler.config = config
    TreeAPIHandler.last_health = health
    save_tree(tree)
    print_tree(tree)

    if "--once" in sys.argv:
        return

    # Start health loop in background
    interval = config["tree"].get("ping_interval_s", PING_INTERVAL_S)
    t = threading.Thread(target=health_loop, args=(config, interval), daemon=True)
    t.start()

    # Start HTTP server
    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), TreeAPIHandler)
    print(f"tree API listening on :{HTTP_PORT}")
    print(f"endpoints: /tree /tree/nodes /tree/online /coupling /health /refresh")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
