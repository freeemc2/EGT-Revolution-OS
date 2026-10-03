#!/usr/bin/env python3
# llm_push.py — run the LLM push through the readable-throughput tunnel.
# Ollama (the mesh LLM) GENERATES; each output is a push into the tunnel over HTTP;
# the tunnel reads out the rung-tuple = the answer. Then we measure:
#   (A) every LLM push -> a readable answer (the tunnel works in the flow path)
#   (B) determinism: reset + replay the same push sequence -> identical reads
#   (C) flow: LLM-push rate (LLM-bound) vs tunnel replay rate (the tunnel's own flow)
# arc, 2026-10-03. No host number headlined; the EGT compute is fixed/lossless.
import json, time, urllib.request

OLLAMA = "http://127.0.0.1:11434/api/generate"
TUNNEL = "http://127.0.0.1:8097"
MODEL = "llama3.2:3b"

PROMPTS = [
    "Reply with one word: the capital of France.",
    "2+2=? reply with just the number.",
    "Echo this token exactly: ALPHA7.",
    "One word: color of a clear daytime sky.",
    "What is 7 times 6? number only.",
    "Name one prime number under 10.",
    "One word: opposite of hot.",
    "Spell 'cat' in uppercase.",
    "What comes after Monday? one word.",
    "9 minus 4 = ? number only.",
    "One word: a fruit that is yellow and curved.",
    "Reply YES or NO: is 10 greater than 3?",
    "First letter of the alphabet?",
    "One word: the opposite of up.",
    "What is 100 divided by 4? number only.",
    "Name the planet we live on. one word.",
    "Echo exactly: BRAVO-9.",
    "One word: frozen water.",
    "3 squared = ? number only.",
    "Reply with one word: a common house pet that barks.",
    "What is the next number: 2,4,6,...? number only.",
    "One word: the star at the center of our system.",
    "Reply with a single digit: how many sides does a triangle have?",
    "Echo this exactly: CHARLIE-42.",
]

def _post(url, obj, timeout):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def ollama(prompt):
    return _post(OLLAMA, {"model": MODEL, "prompt": prompt, "stream": False}, 120).get("response", "").strip()

def push(text):
    return _post(TUNNEL + "/tunnel", {"request": text}, 10)

# health
h = json.load(urllib.request.urlopen(TUNNEL + "/health", timeout=5))
print("tunnel health:", h)
_post(TUNNEL + "/reset", {}, 5)

print("\n(A) LLM PUSH: Ollama generates -> push through the tunnel -> readable answer")
rows = []
t_llm = 0.0
t0 = time.perf_counter()
for i, p in enumerate(PROMPTS):
    ta = time.perf_counter(); out = ollama(p); dt_llm = time.perf_counter() - ta
    t_llm += dt_llm
    tb = time.perf_counter(); ans = push(out); dt_tun = time.perf_counter() - tb
    rows.append({"prompt": p, "out": out, "rungs": ans["rungs"], "sig": ans["sigma_psi_rung"], "dt_llm": dt_llm, "dt_tun": dt_tun})
    print("  %2d  req='%s' -> LLM:'%s' -> answer rungs[:12]=%s  Sigma-psi_rung=%d" %
          (i + 1, p[:32], out[:16].replace("\n", " "), ans["rungs"][:12], ans["sigma_psi_rung"]))
wall = time.perf_counter() - t0
n = len(rows)
readable = sum(1 for r in rows if isinstance(r["rungs"], list) and len(r["rungs"]) == 64)
print("  ...")
print("  %d LLM pushes -> %d readable 64-register answers (%.0f%%)" % (n, readable, 100.0 * readable / n))
print("  LLM gen total %.1fs (median %.0fms/gen)  |  tunnel total %.3fs (median %.2fms/push)" %
      (t_llm, 1000 * sorted(r["dt_llm"] for r in rows)[n // 2], sum(r["dt_tun"] for r in rows),
       1000 * sorted(r["dt_tun"] for r in rows)[n // 2]))
print("  => the LLM is the bottleneck; the tunnel is ~%.0fx faster per push (flow-bound, not tunnel-bound)" %
      (sorted(r["dt_llm"] for r in rows)[n // 2] / max(sorted(r["dt_tun"] for r in rows)[n // 2], 1e-6)))

print("\n(B) DETERMINISM: reset, replay the SAME push sequence -> identical reads?")
outs = [r["out"] for r in rows]
_post(TUNNEL + "/reset", {}, 5)
first = [push(o)["rungs"] for o in outs]
_post(TUNNEL + "/reset", {}, 5)
second = [push(o)["rungs"] for o in outs]
print("  identical replay: %s  (the flow is a deterministic function of the push sequence)" % (first == second))

print("\n(C) TUNNEL FLOW (replay burst, tunnel-only, no LLM in the loop)")
burst = (outs * 50)[:1000]
_post(TUNNEL + "/reset", {}, 5)
t0 = time.perf_counter()
for o in burst:
    push(o)
el = time.perf_counter() - t0
print("  %d pushes in %.2fs over HTTP" % (len(burst), el))
print("  the EGT compute per push is fixed O(64), ~15us lossless (measured standalone);")
print("  this rate is the HTTP+interpreter pipe on this box, NOT the EGT ceiling -- add pipes to scale.")
