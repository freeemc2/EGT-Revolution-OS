#!/usr/bin/env python3
"""cr_llm_flow.py — EGT-gated LLM flow conduit (Phase 3.2, LLM tier).

Brian 2026-09-29: the correct LLM experiment routes inference THROUGH the EGT
gate / coupled tunnel, not a bare Ollama call. aria DECISION-A 2026-09-30: wire
this conduit to call aria's coupled-tunnel POST /tunnel/route to pick the rock,
then hit that rock's Ollama directly — the flow carries the genuine LLM output,
coupling is ROUTING ONLY, no payload transform.

Same architecture as cr_resolver.py (the below-floor flow conduit): an async,
stateless, non-blocking server. A request enters, the coupled tunnel decides
which rock carries the flow (three-axis operator), the genuine LLM answer streams
back out. The conduit RESOLVES and holds nothing — no warehouse, no queue of
materialized objects — so a modest box carries many concurrent LLM streams (the
"flow handles the work, no massive infra" thesis, project_scaling_architecture).

HONESTY NOTE — what is and is NOT "EGT-gated" here:
  - The ROUTER is aria's coupled tunnel (POST /tunnel/route): the rock that carries
    this flow is chosen by the three-axis operator (|C(r)| strength / phase_sign /
    substrate_depth), so LLM inference actually crosses the coupling.
  - Coupling / C(r) is used ONLY to choose the rock. It is NOT applied to the prompt
    text and does NOT change the answer. The answer is the rock's genuine Ollama
    output. No fabricated "operator transform on the prompt" — that would be the
    exact fabrication this project forbids ("not fabricated by us").
  - Fallback (tunnel unreachable, or it routes to a rock with no Ollama) is a local
    |C(r)| weight over the confirmed-Ollama rocks — still routing only, and the
    response says `routed_via` so a caller always sees whether the coupling carried it.

Routes:
  GET  /health                              -> wiring + confirmed-Ollama rocks + stats
  POST /llm {prompt,[model],[node],
             [phase_sign],[prefer_depth]}   -> route via coupled-tunnel -> genuine answer
  GET  /llm?prompt=...                      -> same, query form

Stdlib asyncio only.
    python cr_llm_flow.py [port]     # default :8095
"""
import asyncio, json, time, math, os, urllib.request, urllib.parse, random
import concurrent.futures as cf

# Ollama base per rock (best-known). oracle is included so a tunnel route to r=3 is
# attempted; if it has no Ollama the inference call fails and we fall back (below).
OLLAMA = {
    'dragonseye': 'http://localhost:11434',       # r=1 (floor in aria's band -> only via local fallback)
    'pi5':        'http://100.81.123.41:11434',    # r=2 in-band
    'oracle':     'http://100.114.92.17:11434',    # r=3 in-band (Ollama may be absent -> fallback)
}
# r per node (canonical r-map order) — used for the C(r) fallback weight + labels.
NODE_R = {'dragonseye': 1.0, 'pi5': 2.0, 'oracle': 3.0}

# Fallback set = rocks that actually serve Ollama (used ONLY when the coupled tunnel
# is unreachable or routes to a rock with no Ollama). Kept to confirmed hosts so we
# never fall back onto a dead endpoint. Edit as hosts gain/lose Ollama.
FALLBACK_NODES = ['pi5', 'dragonseye']

# aria's coupled-tunnel conduit — the three-axis coupling gate. The NODE CHOICE goes
# through POST /tunnel/route so LLM inference crosses the coupling (Brian 2026-09-29;
# aria DECISION-A 2026-09-30). Co-located on Dragon's Eye; override with EGT_TUNNEL_URL.
TUNNEL_URL = os.environ.get('EGT_TUNNEL_URL', 'http://127.0.0.1:8096')
TUNNEL_ROUTE_TIMEOUT = float(os.environ.get('EGT_TUNNEL_ROUTE_TIMEOUT', '12'))

DEFAULT_MODEL = 'llama3.2:3b'

STATS = {'served': 0, 'in_flight': 0, 'peak_in_flight': 0, 'errors': 0,
         'routed_via_tunnel': 0, 'routed_via_fallback': 0,
         'per_node': {n: 0 for n in OLLAMA}}


def C_mag(r):
    return (1 + 2 * r) * math.exp(-r / 3.0)


# C(r) fallback weights across the CONFIRMED-Ollama rocks — an honest load
# ALLOCATION, NOT a transform on the prompt or the answer.
_WEIGHTS = {n: C_mag(NODE_R[n]) for n in FALLBACK_NODES}
_WSUM = sum(_WEIGHTS.values()) or 1.0


def pick_node():
    """Fallback routing (tunnel down): choose a confirmed-Ollama rock ~ |C(r)|."""
    return random.choices(FALLBACK_NODES, weights=[_WEIGHTS[n] for n in FALLBACK_NODES], k=1)[0]


def route_via_tunnel(phase_sign=None, prefer_depth=None, timeout=TUNNEL_ROUTE_TIMEOUT):
    """Ask aria's coupled tunnel which rock carries this flow (three-axis operator).

    Returns (node|None, reason). node is the tunnel's routed rock; the caller checks
    whether we can reach that rock's Ollama and otherwise falls back. Coupling is
    routing only — nothing here touches the prompt or the answer.
    """
    payload = {}
    if phase_sign is not None:
        payload['phase_sign'] = phase_sign
    if prefer_depth is not None:
        payload['prefer_depth'] = prefer_depth
    req = urllib.request.Request(TUNNEL_URL + '/tunnel/route',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'},
                                 method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    pick = (d.get('routed_to') or {})
    return pick.get('node'), (d.get('reason') or d.get('error') or 'tunnel route')


def ollama_generate(base, model, prompt, timeout=120):
    """Blocking Ollama call — run in an executor so the event loop stays free."""
    payload = {'model': model, 'prompt': prompt, 'stream': False,
               'options': {'temperature': 0.0, 'num_predict': 64}}
    req = urllib.request.Request(
        base + '/api/generate',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=timeout)
    d = json.load(r)
    return {'response': d.get('response', ''), 'dt_s': round(time.time() - t0, 3),
            'eval_count': d.get('eval_count'), 'eval_duration_ns': d.get('eval_duration'),
            'total_duration_ns': d.get('total_duration')}


def serve_llm(prompt, model, explicit_node=None, phase_sign=None, prefer_depth=None):
    """Blocking: route the flow through aria's coupled tunnel, then do the genuine
    Ollama inference on the routed rock. Returns a result dict (with an internal
    `_status`). Run in an executor. Coupling is routing only."""
    tunnel_pick, tunnel_reason, routed_via = None, None, None

    if explicit_node:
        if explicit_node not in OLLAMA:
            return {'_status': '400 Bad Request',
                    'error': f'unknown node {explicit_node!r}', 'nodes': list(OLLAMA)}
        node, routed_via = explicit_node, 'explicit'
    else:
        try:
            tunnel_pick, tunnel_reason = route_via_tunnel(phase_sign, prefer_depth)
        except Exception as e:
            tunnel_reason = f'tunnel unreachable: {str(e)[:100]}'
        if tunnel_pick and tunnel_pick in OLLAMA:
            node, routed_via = tunnel_pick, 'coupled-tunnel'
        else:
            node, routed_via = pick_node(), 'local-fallback'
            if tunnel_pick and tunnel_pick not in OLLAMA:
                tunnel_reason = f'tunnel routed to {tunnel_pick!r} (no known Ollama) -> local fallback'

    # Inference on the chosen rock, falling through the confirmed-Ollama rocks on failure.
    order = [node] + [n for n in FALLBACK_NODES if n != node]
    tried, last_err = [], None
    for cand in order:
        base = OLLAMA.get(cand)
        if not base:
            continue
        try:
            out = ollama_generate(base, model, prompt)
        except Exception as e:
            last_err = str(e)[:140]
            tried.append(cand)
            continue
        if cand != node:
            routed_via = (routed_via or 'coupled-tunnel') + '+inference-fallback'
        node = cand
        tps = (round(out['eval_count'] / (out['eval_duration_ns'] / 1e9), 1)
               if out.get('eval_count') and out.get('eval_duration_ns') else None)
        STATS['served'] += 1
        STATS['per_node'][node] = STATS['per_node'].get(node, 0) + 1
        STATS['routed_via_tunnel' if str(routed_via).startswith('coupled-tunnel')
              else 'routed_via_fallback'] += 1
        return {'_status': '200 OK', 'conduit': 'egt-llm-flow',
                'routed_via': routed_via,
                'tunnel_pick': tunnel_pick, 'tunnel_reason': tunnel_reason,
                'gated_to': {'node': node, 'r': NODE_R.get(node),
                             'C_mag': round(C_mag(NODE_R.get(node, 0.0)), 4)},
                'model': model, 'answer': out['response'],
                'node_dt_s': out['dt_s'], 'toks_per_sec': tps,
                'source': 'coupling ROUTING only (rock chosen via aria coupled-tunnel '
                          '/tunnel/route); answer is the rock\'s genuine Ollama output '
                          'carried by the flow; conduit holds nothing; C(r) never '
                          'transforms the prompt or the answer'}

    STATS['errors'] += 1
    return {'_status': '502 Bad Gateway',
            'error': f'all inference attempts failed (tried {tried}): {last_err}',
            'routed_via': routed_via, 'tunnel_pick': tunnel_pick, 'tunnel_reason': tunnel_reason}


async def handle(reader, writer):
    STATS['in_flight'] += 1
    STATS['peak_in_flight'] = max(STATS['peak_in_flight'], STATS['in_flight'])
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=15)
        req = line.decode('latin1', 'replace').strip()
        clen = 0
        while True:
            h = await asyncio.wait_for(reader.readline(), timeout=15)
            if h in (b'\r\n', b'\n', b''):
                break
            hl = h.decode('latin1', 'replace').lower()
            if hl.startswith('content-length:'):
                try:
                    clen = int(hl.split(':', 1)[1].strip())
                except ValueError:
                    clen = 0
        parts = req.split(' ')
        path = parts[1] if len(parts) > 1 else '/'
        route, _, qs = path.partition('?')
        q = urllib.parse.parse_qs(qs)
        body = {}
        if clen:
            raw = await asyncio.wait_for(reader.readexactly(clen), timeout=15)
            try:
                body = json.loads(raw.decode('utf-8', 'replace'))
            except json.JSONDecodeError:
                body = {}

        def send_json(obj, status='200 OK'):
            b = json.dumps(obj).encode()
            writer.write(f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\n'
                         f'Content-Length: {len(b)}\r\nConnection: close\r\n\r\n'.encode())
            writer.write(b)

        if route == '/health':
            send_json({'conduit': 'egt-llm-flow',
                       'routing': f'node choice via aria coupled-tunnel POST {TUNNEL_URL}/tunnel/route '
                                  '(three-axis operator: |C(r)| / phase_sign / substrate_depth)',
                       'fallback': 'local |C(r)| weight over confirmed-Ollama rocks when the tunnel is '
                                   'unreachable or routes to a rock with no Ollama',
                       'honesty': 'coupling is ROUTING ONLY — it never transforms the prompt or the answer',
                       'tunnel_url': TUNNEL_URL,
                       'ollama_nodes': {n: {'r': NODE_R.get(n), 'C_mag': round(C_mag(NODE_R.get(n, 0.0)), 4),
                                            'base': OLLAMA[n]} for n in OLLAMA},
                       'fallback_nodes': FALLBACK_NODES,
                       'fallback_weights': {n: round(_WEIGHTS[n] / _WSUM, 3) for n in FALLBACK_NODES},
                       'served': STATS['served'], 'errors': STATS['errors'],
                       'routed_via_tunnel': STATS['routed_via_tunnel'],
                       'routed_via_fallback': STATS['routed_via_fallback'],
                       'in_flight': STATS['in_flight'], 'peak_in_flight': STATS['peak_in_flight'],
                       'per_node': STATS['per_node']})
        elif route == '/llm':
            prompt = body.get('prompt') or (q.get('prompt', [None])[0])
            model = body.get('model') or (q.get('model', [DEFAULT_MODEL])[0])
            if not prompt:
                send_json({'error': 'need {"prompt": ...}'}, '400 Bad Request')
            else:
                explicit_node = body.get('node') or (q.get('node', [None])[0])
                phase_sign = body.get('phase_sign')
                if phase_sign is None and q.get('phase_sign'):
                    phase_sign = q['phase_sign'][0]
                prefer_depth = body.get('prefer_depth') or (q.get('prefer_depth', [None])[0])
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(
                    None, lambda: serve_llm(prompt, model, explicit_node, phase_sign, prefer_depth))
                send_json(res, res.pop('_status', '200 OK'))
        else:
            send_json({'error': 'not found', 'routes': ['/health', '/llm {prompt}']}, '404 Not Found')
        await writer.drain()
    except Exception:
        pass
    finally:
        STATS['in_flight'] -= 1
        try:
            writer.close()
        except Exception:
            pass


async def main(port=8095):
    loop = asyncio.get_event_loop()
    loop.set_default_executor(cf.ThreadPoolExecutor(max_workers=64))
    server = await asyncio.start_server(handle, '0.0.0.0', port)
    print(f'EGT-gated LLM flow conduit on :{port} — node choice via coupled-tunnel '
          f'{TUNNEL_URL}/tunnel/route, fallback {FALLBACK_NODES}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    import sys
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8095))
