#!/usr/bin/env python3
"""cr_llm_flow_experiment.py — the EGT-gated LLM acceptance experiment.

Drives cr_llm_flow.py (the EGT-gated flow conduit) with the deterministic
known-answer prompt set and measures the two things that make it the CORRECT
experiment (Brian 2026-09-29: "EGT-gated flow"):

  A. CORRECTNESS THROUGH THE GATE — prompt in -> correct answer out, routed by
     C(r) across the mesh. Scored RIGOROUSLY: exact token match, so a superset
     string like "120" does NOT count as "12" and "reduced" does NOT count as
     "red". The old substring method is scored alongside for contrast (it is the
     same class of over-count as the acceptance-null bug just fixed).

  B. FLOW / CONDUIT PROPERTY — many CONCURRENT requests carried by the conduit:
     throughput, latency, and the peak concurrency the modest conduit box
     sustained while the mesh nodes did the inference ("flow handles the work,
     no massive infra" — project_scaling_architecture, applied to LLM).

Read-only against the conduit. We measure; the conduit routes; the nodes infer.
    python cr_llm_flow_experiment.py [conduit_url] [concurrency] [flow_seconds]
"""
import urllib.request, json, sys, time, re
import concurrent.futures as cf

CONDUIT = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8095'
CONC    = int(sys.argv[2]) if len(sys.argv) > 2 else 12
FLOWSEC = int(sys.argv[3]) if len(sys.argv) > 3 else 20

PROMPTS = [
    ('math_17x23',    'What is 17 times 23? Reply with only the number.', '391'),
    ('math_144div12', 'What is 144 divided by 12? Reply with only the number.', '12'),
    ('math_sum',      'What is 100 plus 250? Reply with only the number.', '350'),
    ('days_week',     'How many days are in a week? Reply with only the number.', '7'),
    ('capital_fr',    'What is the capital of France? Reply with only the city name.', 'paris'),
    ('capital_jp',    'What is the capital of Japan? Reply with only the city name.', 'tokyo'),
    ('color_blood',   'What color is human blood? One word.', 'red'),
    ('echo_alpha',    'Reply with exactly this string, nothing else: ALPHA-42-OMEGA', 'alpha-42-omega'),
    ('echo_ping',     'Reply with exactly this string, nothing else: PING', 'ping'),
    ('year_moon',     'In what year did humans first land on the moon? Reply with only the four-digit year.', '1969'),
]


def call(prompt, timeout=120):
    body = json.dumps({'prompt': prompt}).encode()
    req = urllib.request.Request(CONDUIT + '/llm', data=body,
        headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=timeout))
        return {'ok': True, 'answer': d.get('answer'),
                'node': (d.get('gated_to') or {}).get('node'), 'dt': time.time() - t0}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:100], 'dt': time.time() - t0}


def score_rigorous(expected, resp):
    """Exact token match. '120' != '12'; word 'red' != 'reduced'."""
    if resp is None:
        return 'null'
    r = resp.strip().lower()
    exp = expected.lower()
    if re.fullmatch(r'-?\d+\.?\d*', exp):                    # numeric answer
        return 'correct' if exp in re.findall(r'-?\d+\.?\d*', r) else 'wrong'
    return 'correct' if exp in re.findall(r"[a-z0-9\-]+", r) else 'wrong'    # word answer


def score_substring(expected, resp):
    """aria's old method — kept only to show the over-count contrast."""
    if resp is None:
        return 'null'
    return 'correct' if expected.lower() in re.sub(r'\s+', ' ', resp.strip().lower()) else 'wrong'


def health():
    try:
        return json.load(urllib.request.urlopen(CONDUIT + '/health', timeout=6))
    except Exception:
        return {}


def part_a():
    print('=== PART A — correctness THROUGH the EGT-gated flow (rigorous scoring) ===')
    rig = {'correct': 0, 'wrong': 0, 'null': 0}
    sub = {'correct': 0, 'wrong': 0, 'null': 0}
    per_node = {}
    disagree = 0
    for name, prompt, expected in PROMPTS:
        r = call(prompt)
        ans = r.get('answer') if r['ok'] else None
        vr = score_rigorous(expected, ans)
        vs = score_substring(expected, ans)
        rig[vr] += 1
        sub[vs] += 1
        node = r.get('node') or '-'
        per_node[node] = per_node.get(node, 0) + 1
        if vr != vs:
            disagree += 1
        shown = (ans or '').strip().replace('\n', ' ')[:40]
        flag = '  <-- substring would MIScount' if vr != vs else ''
        print(f'  {name:14s} want={expected:14s} got="{shown}" -> {vr.upper():7s} [{node}]{flag}')
    n = len(PROMPTS)
    print(f'  RIGOROUS : correct {rig["correct"]}/{n}  wrong {rig["wrong"]}  null {rig["null"]}')
    print(f'  substring: correct {sub["correct"]}/{n}  wrong {sub["wrong"]}  null {sub["null"]}   (disagreements: {disagree})')
    print(f'  routing (C(r)-weighted) landed on: {per_node}')
    return rig


def part_b():
    print(f'\n=== PART B — flow property: {CONC} concurrent for {FLOWSEC}s through the conduit ===')
    deadline = time.time() + FLOWSEC
    lat = []
    counts = {'n': 0, 'ok': 0, 'err': 0, 'correct': 0}
    lock = __import__('threading').Lock()

    def worker():
        i = 0
        while time.time() < deadline:
            name, prompt, expected = PROMPTS[i % len(PROMPTS)]
            i += 1
            r = call(prompt)
            ok = r['ok']
            corr = ok and score_rigorous(expected, r.get('answer')) == 'correct'
            with lock:
                counts['n'] += 1
                counts['ok'] += 1 if ok else 0
                counts['err'] += 0 if ok else 1
                counts['correct'] += 1 if corr else 0
                lat.append(r['dt'])

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=CONC) as ex:
        for _ in range(CONC):
            ex.submit(worker)
    wall = time.time() - t0
    lat.sort()
    p = lambda q: lat[min(int(len(lat) * q), len(lat) - 1)] if lat else 0
    h = health()
    print(f'  requests {counts["n"]}  ok {counts["ok"]}  err {counts["err"]}  correct {counts["correct"]}/{counts["ok"]}  wall {wall:.1f}s')
    print(f'  throughput {counts["n"]/wall:.2f} req/s   latency p50 {p(0.5):.2f}s / p95 {p(0.95):.2f}s / max {p(1.0):.2f}s')
    print(f'  conduit peak concurrent streams carried: {h.get("peak_in_flight")}   served(total) {h.get("served")}   errors {h.get("errors")}')
    print(f'  per-node work (C(r)-weighted routing): {h.get("per_node")}')
    print('  (throughput ceiling is the mesh inference capacity — 2 nodes — NOT the conduit;')
    print('   the conduit only routes+streams, so it stays light while carrying the flow.)')


if __name__ == '__main__':
    print(f'EGT-GATED LLM FLOW EXPERIMENT -> {CONDUIT}')
    h0 = health()
    print(f'  conduit nodes + C(r) route weights: '
          + ', '.join(f'{n}(r={v["r"]}, w={v["route_weight"]})' for n, v in (h0.get('nodes') or {}).items()))
    print()
    part_a()
    part_b()
    print('\n  done.')
