#!/usr/bin/env python3
"""cr_resolver.py — Phase 3.2 async data-plane resolver (prototype).

The scalable hot path from project_scaling_architecture.md. An asyncio
(non-blocking) server that STREAMS the GENUINE live below-floor flow, resolved
per request against a live physical anchor — not a fresh physical run per
request, and NOT a fabricated/synthetic signal.

HONEST Model-B design:
  - The ANCHOR is the genuine live below-floor motion of the rock-nodes — each
    node's real per-fire trajectory (fed continuously by the running experiment
    campaign). Refreshed every 2 s.
  - GET /resolve?r=&phi=&bins= streams that rock's GENUINE live flow (resampled)
    as a chunked continuous read (no collapse). The C(r)/phi operator values are
    returned as clearly-labeled THEORY context — never mixed into the measured
    flow. We do not fabricate a phi-shaped signal (that would be us computing the
    answer); the flow is the system's real motion, the operator is context.
  - Stateless: many concurrent streams read the same shared live anchor, so the
    genuine physical read is distributed to many at line rate (the edge model).

Stdlib asyncio only — no external deps.
    python cr_resolver.py [port]     # default :8094
"""
import asyncio, json, time, math, urllib.request, urllib.parse

# rock r -> its compute node (this backend's rocks)
NODES = {1.0: 'http://100.121.177.94:8091',   # dragonseye
         2.0: 'http://100.81.123.41:8091',    # pi5
         3.0: 'http://100.114.92.17:8091'}    # oracle
ANCHOR = {}                     # {r: {'flow': [ms,...], 'ts': t}} — genuine live below-floor motion
STATS = {'served': 0, 'peak_concurrent': 0, 'active': 0}

def C_mag(r):
    return (1 + 2 * r) * math.exp(-r / 3.0)

async def refresh_anchor():
    """Background: pull each rock-node's genuine live per-fire trajectory (the real
    below-floor motion, fed by the running campaign) into the shared anchor."""
    loop = asyncio.get_event_loop()
    while True:
        for r, url in NODES.items():
            try:
                d = await loop.run_in_executor(
                    None, lambda u=url: json.load(urllib.request.urlopen(
                        u + '/api/v1/trajectory?bins=60', timeout=5)))
                flow = [x for x in (d.get('trajectory_dt_ms') or []) if x is not None]
                if flow:
                    ANCHOR[r] = {'flow': flow, 'ts': time.time()}
            except Exception:
                pass
        await asyncio.sleep(2.0)

def resolve_flow(r, bins):
    """Return the rock-at-r's GENUINE live below-floor flow, resampled to `bins`.
    No synthesis — this is the system's real motion from the live anchor."""
    a = ANCHOR.get(float(r))
    if not a or not a.get('flow'):
        return None, None, 'anchor not warm for this rock — run experiments to feed the live flow'
    live = a['flow']
    n = len(live)
    out = [live[min(int(i / bins * n), n - 1)] for i in range(bins)]
    return out, round(time.time() - a['ts'], 1), 'genuine live below-floor flow, resampled'

async def handle(reader, writer):
    STATS['active'] += 1
    STATS['peak_concurrent'] = max(STATS['peak_concurrent'], STATS['active'])
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        req = line.decode('latin1', 'replace').strip()
        while True:
            h = await asyncio.wait_for(reader.readline(), timeout=5)
            if h in (b'\r\n', b'\n', b''):
                break
        parts = req.split(' ')
        path = parts[1] if len(parts) > 1 else '/'
        route, _, qs = path.partition('?')
        q = urllib.parse.parse_qs(qs)

        def send_json(obj, status='200 OK'):
            body = json.dumps(obj).encode()
            writer.write(f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\n'
                         f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode())
            writer.write(body)

        if route == '/health':
            send_json({'resolver': 'egt-async',
                       'anchor_ages_s': {r: round(time.time() - a['ts'], 1) for r, a in ANCHOR.items()},
                       'served': STATS['served'], 'peak_concurrent': STATS['peak_concurrent'],
                       'active': STATS['active']})
        elif route == '/resolve':
            r = float(q.get('r', ['2'])[0])
            phi = float(q.get('phi', ['0'])[0])
            bins = max(2, min(int(q.get('bins', ['60'])[0]), 500))
            flow, age, note = resolve_flow(r, bins)
            if flow is None:
                send_json({'error': note, 'r': r}, '503 Service Unavailable')
            else:
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n'
                             b'Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n')
                head = ('{"resolver":"egt-async",'
                        '"read_type":"GENUINE live below-floor flow, resolved against the live '
                        'physical anchor (no collapse, no synthesis)",'
                        f'"r":{r},"anchor_age_s":{age},"note":"{note}",'
                        '"theory_context":{"note":"C(r) operator prediction — NOT measured, reference only",'
                        f'"C_mag":{round(C_mag(r),4)},"phi_deg":{phi},'
                        f'"phi_character":{round(math.cos(math.radians(phi)),4)}}},'
                        '"flow_dt_ms":[')

                async def chunk(s):
                    b = s.encode()
                    writer.write(f'{len(b):X}\r\n'.encode() + b + b'\r\n')
                    await writer.drain()

                await chunk(head)
                for i, v in enumerate(flow):
                    await chunk((',' if i else '') + str(v))
                    if i % 12 == 0:
                        await asyncio.sleep(0)
                await chunk(']}')
                writer.write(b'0\r\n\r\n')
                STATS['served'] += 1
        else:
            send_json({'error': 'not found', 'routes': ['/health', '/resolve?r=&phi=&bins=']}, '404 Not Found')
        await writer.drain()
    except Exception:
        pass
    finally:
        STATS['active'] -= 1
        try:
            writer.close()
        except Exception:
            pass

async def main(port=8094):
    asyncio.create_task(refresh_anchor())
    server = await asyncio.start_server(handle, '0.0.0.0', port)
    print(f'EGT async resolver on :{port} — genuine live anchor from rock-nodes', flush=True)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    import sys
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8094))
