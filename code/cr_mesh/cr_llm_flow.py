#!/usr/bin/env python3
"""cr_llm_flow.py — EGT-gated LLM flow conduit (Phase 3.2, LLM tier) — STANDALONE.

Routes LLM inference to an r-mapped mesh compute node by a C(r) load-allocation weight,
then does the genuine Ollama inference on that node. Stateless, non-blocking async server:
a request enters, the flow carries it to a node, the answer streams back out; the conduit
holds nothing.

2026-10-01: STRIPPED the dependency on aria's coupled-tunnel (:8096, cleared when aria was
taken out of rotation). Node choice is now purely the local C(r) weight again — no external
router. If a below-floor coupling router is wanted later it will be rebuilt clean in arc's lane.

HONESTY NOTE — what is and is NOT "EGT-gated":
  - Architectural: the conduit boundary (in/out) + stateless flow resolution (resolve, don't
    warehouse), per project_scaling_architecture.
  - C(r) is used ONLY as a load-ALLOCATION weight across the r-mapped nodes. It is NOT applied
    to the prompt and does NOT change the answer. The answer is the node's genuine Ollama output.
  - No fabricated "operator transform on the prompt" — that is the fabrication this project forbids.

Routes:
  GET  /health                       -> conduit + per-node routing weights + stats
  POST /llm {prompt,[model],[node]}   -> gate in -> route by C(r) weight -> genuine answer out
  GET  /llm?prompt=...               -> same, query form

Stdlib asyncio only.
    python cr_llm_flow.py [port]     # default :8095
"""
import asyncio, json, time, math, urllib.request, urllib.parse, random
import concurrent.futures as cf

# r-mapped mesh compute nodes that host Ollama inference. Kept to confirmed-Ollama hosts so a
# route never lands on a dead endpoint. Edit as hosts gain/lose Ollama.
OLLAMA = {
    'dragonseye': 'http://localhost:11434',       # r=1
    'pi5':        'http://100.81.123.41:11434',    # r=2
}
NODE_R = {'dragonseye': 1.0, 'pi5': 2.0}
DEFAULT_MODEL = 'llama3.2:3b'

STATS = {'served': 0, 'in_flight': 0, 'peak_in_flight': 0, 'errors': 0,
         'per_node': {n: 0 for n in OLLAMA}}


def C_mag(r):
    return (1 + 2 * r) * math.exp(-r / 3.0)


# C(r) routing weights — an honest load ALLOCATION across the r-mapped nodes, NOT a transform
# on the prompt or the answer.
_WEIGHTS = {n: C_mag(NODE_R[n]) for n in OLLAMA}
_WSUM = sum(_WEIGHTS.values()) or 1.0


def pick_node():
    """Route a flow: choose a node with probability proportional to |C(r)|."""
    ns = list(OLLAMA)
    return random.choices(ns, weights=[_WEIGHTS[n] for n in ns], k=1)[0]


def ollama_generate(base, model, prompt, timeout=120):
    """Blocking Ollama call — run in an executor so the event loop stays free."""
    payload = {'model': model, 'prompt': prompt, 'stream': False,
               'options': {'temperature': 0.0, 'num_predict': 64}}
    req = urllib.request.Request(base + '/api/generate',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=timeout)
    d = json.load(r)
    return {'response': d.get('response', ''), 'dt_s': round(time.time() - t0, 3),
            'eval_count': d.get('eval_count'), 'eval_duration_ns': d.get('eval_duration'),
            'total_duration_ns': d.get('total_duration')}


def serve_llm(prompt, model, explicit_node=None):
    """Blocking: route (local C(r) weight), then genuine Ollama inference on the chosen node,
    falling through the other confirmed-Ollama nodes on failure. Run in an executor."""
    if explicit_node:
        if explicit_node not in OLLAMA:
            return {'_status': '400 Bad Request', 'error': f'unknown node {explicit_node!r}', 'nodes': list(OLLAMA)}
        node, routed_via = explicit_node, 'explicit'
    else:
        node, routed_via = pick_node(), 'local-Cr-weight'
    order = [node] + [n for n in OLLAMA if n != node]
    tried, last_err = [], None
    for cand in order:
        base = OLLAMA.get(cand)
        if not base:
            continue
        try:
            out = ollama_generate(base, model, prompt)
        except Exception as e:
            last_err = str(e)[:140]; tried.append(cand); continue
        if cand != node:
            routed_via += '+inference-fallback'
        node = cand
        tps = (round(out['eval_count'] / (out['eval_duration_ns'] / 1e9), 1)
               if out.get('eval_count') and out.get('eval_duration_ns') else None)
        STATS['served'] += 1
        STATS['per_node'][node] = STATS['per_node'].get(node, 0) + 1
        return {'_status': '200 OK', 'conduit': 'egt-llm-flow', 'routed_via': routed_via,
                'gated_to': {'node': node, 'r': NODE_R.get(node), 'C_mag': round(C_mag(NODE_R.get(node, 0.0)), 4)},
                'model': model, 'answer': out['response'], 'node_dt_s': out['dt_s'], 'toks_per_sec': tps,
                'source': 'genuine Ollama output from the mesh node, carried by the flow; conduit holds '
                          'nothing; C(r) is routing-weight only, never transforms the prompt or answer'}
    STATS['errors'] += 1
    return {'_status': '502 Bad Gateway', 'error': f'all inference attempts failed (tried {tried}): {last_err}',
            'routed_via': routed_via}


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
                try: clen = int(hl.split(':', 1)[1].strip())
                except ValueError: clen = 0
        parts = req.split(' ')
        path = parts[1] if len(parts) > 1 else '/'
        route, _, qs = path.partition('?')
        q = urllib.parse.parse_qs(qs)
        body = {}
        if clen:
            raw = await asyncio.wait_for(reader.readexactly(clen), timeout=15)
            try: body = json.loads(raw.decode('utf-8', 'replace'))
            except json.JSONDecodeError: body = {}

        def send_json(obj, status='200 OK'):
            b = json.dumps(obj).encode()
            writer.write(f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\n'
                         f'Content-Length: {len(b)}\r\nConnection: close\r\n\r\n'.encode())
            writer.write(b)

        if route == '/health':
            send_json({'conduit': 'egt-llm-flow',
                       'routing': 'local |C(r)| load-weight across confirmed-Ollama nodes (standalone; no external router)',
                       'honesty': 'C(r) is routing-weight only — never transforms the prompt or the answer',
                       'nodes': {n: {'r': NODE_R.get(n), 'C_mag': round(C_mag(NODE_R.get(n, 0.0)), 4),
                                     'route_weight': round(_WEIGHTS[n] / _WSUM, 3), 'base': OLLAMA[n]} for n in OLLAMA},
                       'served': STATS['served'], 'errors': STATS['errors'],
                       'in_flight': STATS['in_flight'], 'peak_in_flight': STATS['peak_in_flight'],
                       'per_node': STATS['per_node']})
        elif route == '/llm':
            prompt = body.get('prompt') or (q.get('prompt', [None])[0])
            model = body.get('model') or (q.get('model', [DEFAULT_MODEL])[0])
            if not prompt:
                send_json({'error': 'need {"prompt": ...}'}, '400 Bad Request')
            else:
                explicit_node = body.get('node') or (q.get('node', [None])[0])
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, lambda: serve_llm(prompt, model, explicit_node))
                send_json(res, res.pop('_status', '200 OK'))
        else:
            send_json({'error': 'not found', 'routes': ['/health', '/llm {prompt}']}, '404 Not Found')
        await writer.drain()
    except Exception:
        pass
    finally:
        STATS['in_flight'] -= 1
        try: writer.close()
        except Exception: pass


async def main(port=8095):
    loop = asyncio.get_event_loop()
    loop.set_default_executor(cf.ThreadPoolExecutor(max_workers=64))
    server = await asyncio.start_server(handle, '0.0.0.0', port)
    print(f'EGT-gated LLM flow conduit (standalone) on :{port} — C(r)-weighted routing across {list(OLLAMA)}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    import sys
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8095))
