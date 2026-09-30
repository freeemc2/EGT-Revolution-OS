#!/usr/bin/env python3
"""cr_llm_flow.py — EGT-gated LLM flow conduit (Phase 3.2, LLM tier).

Brian 2026-09-29: the correct LLM experiment routes inference THROUGH the EGT
gate / flow-conduit, not a bare Ollama call.

Same architecture as cr_resolver.py (the below-floor flow conduit): an async,
stateless, non-blocking server. A request enters EGT-gated, the FLOW carries it
to a mesh compute node (Ollama on an r-mapped rock-node), the answer streams
back out gated. The conduit RESOLVES and holds nothing — no warehouse, no queue
of materialized objects — so a modest box carries many concurrent LLM streams
(the "flow handles the work, no massive infra" thesis, project_scaling_architecture).

HONESTY NOTE — what is and is NOT "EGT-gated" here:
  - The gate is ARCHITECTURAL: the conduit boundary (in/out) + stateless flow
    resolution (resolve, don't warehouse), exactly as the scaling doc defines it.
  - C(r) is used ONLY as a load-routing WEIGHT across the r-mapped nodes (a real
    use of the operator to allocate flow). It is NOT applied to the prompt text
    and does NOT change the answer. The answer is the node's genuine LLM output.
  - No fabricated "operator transform on the prompt." Anything else would be the
    exact fabrication this project forbids ("not fabricated by us").

Routes:
  GET  /health                          -> conduit + per-node routing weights + stats
  POST /llm   {prompt,[model],[node]}   -> gate in -> route by C(r) -> genuine answer out
  GET  /llm?prompt=...                  -> same, query form

Stdlib asyncio only.
    python cr_llm_flow.py [port]     # default :8095
"""
import asyncio, json, time, math, urllib.request, urllib.parse, random
import concurrent.futures as cf

# r-mapped mesh compute nodes that host Ollama inference (the rocks that compute).
# Tiers measured by aria: dragonseye (r=1) + pi5 (r=2). oracle can be added when
# it runs Ollama; the conduit routes over whatever is listed here.
NODES = {
    'dragonseye': {'r': 1.0, 'ollama': 'http://localhost:11434'},
    'pi5':        {'r': 2.0, 'ollama': 'http://100.81.123.41:11434'},
}
DEFAULT_MODEL = 'llama3.2:3b'

STATS = {'served': 0, 'in_flight': 0, 'peak_in_flight': 0, 'errors': 0,
         'per_node': {n: 0 for n in NODES}}


def C_mag(r):
    return (1 + 2 * r) * math.exp(-r / 3.0)


# C(r) routing weights — an honest load-ALLOCATION weight across the r-mapped
# nodes, NOT a transform on the prompt or the answer.
_WEIGHTS = {n: C_mag(v['r']) for n, v in NODES.items()}
_WSUM = sum(_WEIGHTS.values())


def pick_node():
    """EGT-gated routing: choose a node with probability proportional to |C(r)|."""
    ns = list(NODES)
    return random.choices(ns, weights=[_WEIGHTS[n] for n in ns], k=1)[0]


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
                       'gating': 'architectural flow-conduit (stateless resolve) + C(r) load-routing weight; '
                                 'C(r) does NOT transform the prompt or answer',
                       'nodes': {n: {'r': v['r'], 'C_mag': round(C_mag(v['r']), 4),
                                     'route_weight': round(_WEIGHTS[n] / _WSUM, 3)}
                                 for n, v in NODES.items()},
                       'served': STATS['served'], 'errors': STATS['errors'],
                       'in_flight': STATS['in_flight'], 'peak_in_flight': STATS['peak_in_flight'],
                       'per_node': STATS['per_node']})
        elif route == '/llm':
            prompt = body.get('prompt') or (q.get('prompt', [None])[0])
            model = body.get('model') or (q.get('model', [DEFAULT_MODEL])[0])
            if not prompt:
                send_json({'error': 'need {"prompt": ...}'}, '400 Bad Request')
            else:
                node = body.get('node') or (q.get('node', [None])[0]) or pick_node()
                if node not in NODES:
                    send_json({'error': f'unknown node {node!r}', 'nodes': list(NODES)}, '400 Bad Request')
                else:
                    base = NODES[node]['ollama']
                    loop = asyncio.get_event_loop()
                    try:
                        out = await loop.run_in_executor(
                            None, lambda: ollama_generate(base, model, prompt))
                        STATS['served'] += 1
                        STATS['per_node'][node] += 1
                        tps = (round(out['eval_count'] / (out['eval_duration_ns'] / 1e9), 1)
                               if out.get('eval_count') and out.get('eval_duration_ns') else None)
                        send_json({'conduit': 'egt-llm-flow',
                                   'gated_to': {'node': node, 'r': NODES[node]['r'],
                                                'C_mag': round(C_mag(NODES[node]['r']), 4)},
                                   'model': model, 'answer': out['response'],
                                   'node_dt_s': out['dt_s'], 'toks_per_sec': tps,
                                   'source': 'genuine LLM output from the mesh node, carried by the flow; '
                                             'conduit holds nothing'})
                    except Exception as e:
                        STATS['errors'] += 1
                        send_json({'error': f'node {node} inference failed: {str(e)[:140]}',
                                   'node': node}, '502 Bad Gateway')
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
    print(f'EGT-gated LLM flow conduit on :{port} — C(r)-weighted routing across {list(NODES)}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    import sys
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8095))
