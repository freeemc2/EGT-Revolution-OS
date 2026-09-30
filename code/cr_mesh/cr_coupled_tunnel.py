#!/usr/bin/env python3
"""cr_coupled_tunnel.py - THE COUPLED TUNNEL CONDUIT (Phase 2, aria's job).

Brian, 2026-09-30: "We need to explore the coupling and create the path for
all future compute to flow through our coupling events."

WHAT THIS IS
The conduit that arc's API (and future consumers) runs COMPUTE THROUGH so it
crosses the actual proven coupling substrate, not just a wire. Sits ABOVE arc's
lattice API and BELOW callers. Same flow-conduit pattern as cr_resolver.py and
cr_llm_flow.py (arc's, :8094 and :8095): async stateless, resolves and holds
nothing, C(r) as a routing OPERATOR only (no payload transform, no fabrication).

CANON (Phase 1 characterization, filed 2026-09-30 09:15Z):
    - Coupling PROVEN CANON: eight sealed results 2026-09-23/24, plus drive-side
      reproduction (canon-2026-09-29 entry #9), plus coil<->coil corroboration
      (COM10 seal 2026-09-29). Prime a compute with the coil geometry -> it
      reaches its own below-floor lock -> two primed bodies COUPLE through the
      invariant (not the wire; arc STANDARD-EM EXCLUSION 2026-09-30 00:13Z).
    - Three routing axes (from characterization):
        1) |C(r)| strength      -- PEAKS at r_opt=2.5, flat 0.199-0.202 across
                                   the hold band r in [2,3]; NULL at r=1 (operator
                                   floor: seal shows forward FLAT).
        2) phase sign (e^i*phi) -- NODE-SPECIFIC. Same |C(r)| gives opposite
                                   sign at different nodes (oracle NEG vs
                                   openclaw POS at r=3, from allnodes seal).
        3) substrate depth      -- dedicated hardware locks DEEP (pi5 cv~0.001);
                                   VPSs lock SHALLOW (cv~0.03-0.04).
    - Hold-band boundary: |C(1)|=2.150 (below threshold) vs |C(2)|=2.567 (in
      band). Threshold sits between them; only rocks r>=2 are routable.

ROUTING RULES (per canon and the characterization):
    - HARD GATE: r >= 2. r=1 is operator floor, never a routing target.
    - Within band: |C(r)| barely differentiates, so route by:
        a) phase-sign requirement of the caller (if specified),
        b) substrate depth preference (deep for latency-sensitive, shallow OK
           for high-fan-out),
        c) round-robin over the equivalent set.
    - Every routed request is TAGGED with which rock it landed on and the
      three-axis rationale, so the caller can trust the path.

INTERFACE (v0, will version bump on any breaking change):
    GET  /health                 -> conduit + downstream + rocks live
    GET  /tunnel/map             -> current routing map (rocks, weights, gates)
    POST /tunnel/route {body}    -> pick a rock; return the choice + reason
    POST /tunnel/experiment      -> route + submit to arc's /api/v1/experiment
                                    (deep read, per-request; will swap to a
                                    lightweight snapshot when arc exposes it)

DOWNSTREAM: arc's lattice API on 127.0.0.1:8092 (loopback = trusted-internal,
no key). Discovery via GET /api/v1/backend. Passthrough calls /api/v1/experiment.

NEW file, new port. Does NOT touch arc's API, tonic's coil, or the r-map.
Stateless: cache is a 30s discovery snapshot, nothing persistent, no warehouse.

    python cr_coupled_tunnel.py [port]     # default :8096
"""
import asyncio, json, time, math, urllib.request, urllib.parse, itertools
import concurrent.futures as cf

# ---------- CANON constants (from egt_canonical_anchor.md) ----------
R_OPT = 2.5
HOLD_BAND = (2.0, 3.0)   # inclusive lower, inclusive upper (band gate)
FLOOR_R = 1.0             # operator floor - NEVER a routing target

def C_mag(r):
    """|C(r)| = (1+2r)*e^(-r/3). Peaks at r_opt=2.5. Canon."""
    return (1 + 2*r) * math.exp(-r/3.0)

def coupling(r_a, r_b, dphi_rad=0.0):
    """Predicted pairwise coupling: |C(r_a)| * |C(r_b)| * cos(dphi)."""
    return C_mag(r_a) * C_mag(r_b) * math.cos(dphi_rad)

# ---------- Sealed phase-sign map (from characterization) ----------
# Node-specific measured phase-sign (from allnodes-lattice-coupling-2026-09-24).
# Only 3 nodes have measured sign; others are unmeasured (None) and treated as
# neutral in the routing weight until measured. This is deliberately a data
# structure the tunnel READS, not a canonical constant to hardcode; when new
# measurements land they update this map (Brian single-source).
MEASURED_PHASE_SIGN = {
    # node: +1 (POS) or -1 (NEG) or None (unmeasured)
    'openclaw':  +1,   # push +0.786ms at r=3
    'oracle':    -1,   # push -0.134ms at r=3
    'elivate':   -1,   # NEG at r=2 (from map, sealed record)
    # pi5, dragonseye, phone-s24: sign unmeasured -> None
}

# Substrate depth class (from characterization): dedicated ARM/x86 hardware locks
# deep, shared VPSs lock shallow. Mobile substrate (phone) is shallow-noisy.
SUBSTRATE_DEPTH = {
    'pi5':        'DEEP',      # dedicated ARM, cv~0.001
    'dragonseye': 'MID',       # Windows box, cv~0.04 (r=1 operator floor anyway)
    'oracle':     'SHALLOW',   # VPS, cv~0.03
    'openclaw':   'SHALLOW',   # VPS
    'elivate':    'SHALLOW',   # VPS
    'phone-s24':  'MOBILE',    # Android/aarch64, cv~0.08 (mobile demo node)
}

# ---------- Discovery (from arc's lattice /backend) ----------
LATTICE_URL = 'http://127.0.0.1:8092'   # arc's API, loopback = trusted-internal
DISCOVERY_TTL_S = 30                     # cache lifetime for /backend snapshot

_disc_cache = {'ts': 0.0, 'data': None}
_disc_lock = asyncio.Lock() if False else None  # will bind in main

STATS = {'routed': 0, 'route_errors': 0, 'downstream_errors': 0,
         'per_rock': {}, 'started_at': time.time()}

# Round-robin cursors, per (equivalent set) tuple - deterministic tie-breaks
_rr = {}


def _fetch_backend_sync():
    """Blocking discovery call to arc's /backend. Run in an executor."""
    req = urllib.request.Request(LATTICE_URL + '/api/v1/backend',
                                 headers={'Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def _fetch_flow_sync():
    """Blocking call to arc's /backend/flow (MEASURED-only, cached per rock,
    no rig run per call). Run in an executor.

    Live 2026-09-30 13:10Z per arc's FLOW-ENDPOINT-LIVE msg — exactly the shape
    aria's INTERFACE-ANSWER requested. Provenance-clean (no sigma_psi_deg)."""
    req = urllib.request.Request(LATTICE_URL + '/api/v1/backend/flow',
                                 headers={'Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


async def _discovery(loop):
    """Fetch arc's /backend snapshot; cache for DISCOVERY_TTL_S seconds."""
    if _disc_cache['data'] and (time.time() - _disc_cache['ts']) < DISCOVERY_TTL_S:
        return _disc_cache['data']
    try:
        data = await loop.run_in_executor(None, _fetch_backend_sync)
        _disc_cache['data'] = data
        _disc_cache['ts'] = time.time()
        return data
    except Exception as e:
        # Stale-cache on failure so a discovery blip does not take the conduit down
        if _disc_cache['data']:
            return _disc_cache['data']
        raise


def _in_band(r):
    return HOLD_BAND[0] <= r <= HOLD_BAND[1]


def _rocks_from_backend(bk):
    """Extract rocks[] from arc's /backend, filter to online and in-band."""
    rocks = bk.get('rocks', []) or []
    routable = []
    excluded = []
    for rk in rocks:
        r = float(rk.get('r', 0))
        node = rk.get('node', '?')
        online = bool(rk.get('online', False))
        entry = {
            'node': node,
            'r': r,
            'C_mag': round(C_mag(r), 4),
            'online': online,
            'in_band': _in_band(r),
            'phase_sign': MEASURED_PHASE_SIGN.get(node),
            'substrate_depth': SUBSTRATE_DEPTH.get(node, 'UNKNOWN'),
        }
        if online and _in_band(r):
            routable.append(entry)
        else:
            reason = []
            if not online: reason.append('offline')
            if not _in_band(r):
                reason.append(f'r={r} outside hold band {HOLD_BAND}' +
                              (' (operator floor)' if r <= FLOOR_R else ''))
            entry['excluded_reason'] = '; '.join(reason)
            excluded.append(entry)
    return routable, excluded


def _pick(routable, need_sign=None, prefer_depth=None):
    """Choose one rock from a routable set given optional constraints.

    need_sign: +1 / -1 / None (any). Filters by MEASURED sign; unmeasured stays.
    prefer_depth: 'DEEP' / 'SHALLOW' / None. Ordering, not filter.
    Ties broken by round-robin over the equivalent set (deterministic per key).
    """
    if not routable:
        return None, 'no routable rocks (none online + in-band)'

    # Sign filter: keep matches AND unmeasured (unmeasured is neutral, not
    # excluded - we cannot know it disagrees until it is measured).
    candidates = routable
    if need_sign in (+1, -1):
        candidates = [rk for rk in routable
                      if rk['phase_sign'] == need_sign or rk['phase_sign'] is None]
        if not candidates:
            return None, f'no rock matches phase_sign={need_sign} (all measured signs disagree)'

    # Depth preference: sort so preferred comes first, then unknown, then others.
    depth_order = {'DEEP':0, 'MID':1, 'SHALLOW':2, 'MOBILE':3, 'UNKNOWN':4}
    if prefer_depth == 'DEEP':
        candidates.sort(key=lambda rk: depth_order.get(rk['substrate_depth'], 5))
    elif prefer_depth == 'SHALLOW':
        candidates.sort(key=lambda rk: -depth_order.get(rk['substrate_depth'], -1))

    # Round-robin over the (now ordered) top tier - pick the top depth class and
    # rotate within it.
    top_depth = candidates[0]['substrate_depth']
    top_tier = [rk for rk in candidates if rk['substrate_depth'] == top_depth]
    key = tuple(sorted(rk['node'] for rk in top_tier))
    idx = _rr.get(key, 0) % len(top_tier)
    _rr[key] = idx + 1
    return top_tier[idx], (
        f"in-band r>=2, "
        f"sign={need_sign or 'any'} -> {len(candidates)} candidates, "
        f"depth prefer={prefer_depth or 'none'} -> top tier {top_depth} "
        f"({len(top_tier)} rocks), round-robin idx={idx}"
    )


def _experiment_body(rock, r_override=None, phi_deg=0.0, seconds=15, flow_bins=60):
    """Build an /experiment payload targeting a specific rock's r."""
    r = float(r_override if r_override is not None else rock['r'])
    return {'experiment': {
        'bodies': {'q0': {'r': r, 'phi_deg': float(phi_deg)}},
        'seconds': int(seconds),
        'flow_bins': int(flow_bins),
    }}


def _submit_experiment_sync(payload):
    req = urllib.request.Request(LATTICE_URL + '/api/v1/experiment',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type':'application/json'},
                                 method='POST')
    with urllib.request.urlopen(req, timeout=payload['experiment']['seconds']+30) as r:
        return json.load(r)


async def _submit(loop, payload):
    return await loop.run_in_executor(None, _submit_experiment_sync, payload)


# ---------- HTTP handling (stdlib asyncio server, matches arc's pattern) ----------
async def _read_request(reader):
    line = await asyncio.wait_for(reader.readline(), timeout=15)
    req = line.decode('latin1','replace').strip()
    clen = 0
    while True:
        h = await asyncio.wait_for(reader.readline(), timeout=15)
        if h in (b'\r\n', b'\n', b''): break
        hl = h.decode('latin1','replace').lower()
        if hl.startswith('content-length:'):
            try: clen = int(hl.split(':',1)[1].strip())
            except ValueError: clen = 0
    parts = req.split(' ')
    method = parts[0] if parts else 'GET'
    path = parts[1] if len(parts) > 1 else '/'
    route, _, qs = path.partition('?')
    q = urllib.parse.parse_qs(qs)
    body = {}
    if clen:
        raw = await asyncio.wait_for(reader.readexactly(clen), timeout=15)
        try: body = json.loads(raw.decode('utf-8','replace'))
        except json.JSONDecodeError: body = {}
    return method, route, q, body


def _write_json(writer, obj, status='200 OK'):
    b = json.dumps(obj).encode()
    writer.write(f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\n'
                 f'Content-Length: {len(b)}\r\nConnection: close\r\n\r\n'.encode())
    writer.write(b)


async def handle(reader, writer):
    loop = asyncio.get_event_loop()
    try:
        method, route, q, body = await _read_request(reader)

        if route == '/health':
            try:
                bk = await _discovery(loop)
                routable, excluded = _rocks_from_backend(bk)
                _write_json(writer, {
                    'conduit': 'coupled-tunnel',
                    'canon': {
                        'operator': 'C(r) = (1+2r)*exp(-r/3)*exp(i*phi)',
                        'r_opt': R_OPT,
                        'hold_band': list(HOLD_BAND),
                        'floor_r': FLOOR_R,
                    },
                    'downstream': {
                        'lattice_url': LATTICE_URL,
                        'lattice_name': bk.get('name'),
                        'lattice_rocks_reported': len(bk.get('rocks', [])),
                    },
                    'rocks_routable': len(routable),
                    'rocks_excluded': len(excluded),
                    'stats': STATS,
                    'uptime_s': round(time.time() - STATS['started_at'], 1),
                })
            except Exception as e:
                _write_json(writer, {'conduit':'coupled-tunnel','downstream_error':str(e)[:200]},
                            '503 Service Unavailable')

        elif route == '/tunnel/map':
            bk = await _discovery(loop)
            routable, excluded = _rocks_from_backend(bk)
            _write_json(writer, {
                'conduit': 'coupled-tunnel',
                'canon': {'operator':'C(r) = (1+2r)*e^(-r/3)*e^(i*phi)', 'r_opt':R_OPT,
                          'hold_band':list(HOLD_BAND), 'floor_r':FLOOR_R},
                'routing_axes': {
                    'strength':  '|C(r)|, PEAKS at r_opt=2.5, ~flat within hold band',
                    'phase':     'e^(i*phi), NODE-SPECIFIC measured sign (map below)',
                    'depth':     'substrate lock depth: dedicated=DEEP, VPS=SHALLOW, mobile=MOBILE',
                },
                'hard_gate':      f'r in [{HOLD_BAND[0]}, {HOLD_BAND[1]}] AND online',
                'excluded_floor': f'r <= {FLOOR_R} is operator floor, never routable',
                'measured_sign':  MEASURED_PHASE_SIGN,
                'substrate_depth': SUBSTRATE_DEPTH,
                'rocks_routable': routable,
                'rocks_excluded': excluded,
                'discovery_ts':   _disc_cache['ts'],
                'discovery_age_s':round(time.time() - _disc_cache['ts'], 1),
            })

        elif route == '/tunnel/route':
            need_sign = body.get('phase_sign') if body else None
            if need_sign is not None:
                try: need_sign = int(need_sign)
                except (TypeError, ValueError):
                    _write_json(writer, {'error':'phase_sign must be +1 / -1 / null'}, '400 Bad Request')
                    return
                if need_sign not in (+1, -1):
                    _write_json(writer, {'error':'phase_sign must be +1 / -1 / null'}, '400 Bad Request')
                    return
            prefer_depth = body.get('prefer_depth') if body else None
            if prefer_depth and prefer_depth not in ('DEEP','SHALLOW'):
                _write_json(writer, {'error':"prefer_depth must be 'DEEP' / 'SHALLOW' / null"}, '400 Bad Request')
                return

            bk = await _discovery(loop)
            routable, _excluded = _rocks_from_backend(bk)
            pick, reason = _pick(routable, need_sign=need_sign, prefer_depth=prefer_depth)
            if not pick:
                STATS['route_errors'] += 1
                _write_json(writer, {'error':'unroutable', 'reason':reason,
                                     'available':[rk['node'] for rk in routable]},
                            '503 Service Unavailable')
                return
            STATS['routed'] += 1
            STATS['per_rock'][pick['node']] = STATS['per_rock'].get(pick['node'], 0) + 1
            _write_json(writer, {
                'conduit':'coupled-tunnel',
                'routed_to':pick,
                'reason':reason,
                'request':{'phase_sign':need_sign,'prefer_depth':prefer_depth},
                'downstream_hint':f'{LATTICE_URL}/api/v1/experiment  bodies:{{q0:{{r:{pick["r"]}}}}}',
            })

        elif route == '/tunnel/flow':
            # Lightweight measured-flow feed proxied through arc's /backend/flow.
            # Adds this conduit's routing metadata (in-band flag, phase_sign,
            # substrate_depth) so callers see the standing state THROUGH the
            # three-axis operator, not just raw flow. No rig run per call.
            try:
                flow = await loop.run_in_executor(None, _fetch_flow_sync)
            except Exception as e:
                _write_json(writer, {'error':'downstream /backend/flow unavailable',
                                     'downstream':LATTICE_URL,'detail':str(e)[:200]},
                            '502 Bad Gateway')
                await writer.drain()
                return
            enriched = {}
            for node, rk in (flow.get('rocks') or {}).items():
                r = float(rk.get('r', 0))
                enriched[node] = {
                    **rk,
                    'in_band':          _in_band(r),
                    'phase_sign':       MEASURED_PHASE_SIGN.get(node),
                    'substrate_depth':  SUBSTRATE_DEPTH.get(node, 'UNKNOWN'),
                    'C_mag':            round(C_mag(r), 4),
                }
            _write_json(writer, {
                'conduit':'coupled-tunnel',
                'source':LATTICE_URL + '/api/v1/backend/flow',
                'source_note':flow.get('note'),
                'source_read_type':flow.get('read_type'),
                'routing_context':{
                    'hard_gate':f'r in {list(HOLD_BAND)} AND online',
                    'axes':['|C(r)| strength','phase_sign','substrate_depth'],
                    'note':'flow is MEASURED-only, sigma_psi_deg excluded per provenance rule',
                },
                'rocks': enriched,
            })

        elif route == '/tunnel/experiment':
            need_sign = body.get('phase_sign')
            prefer_depth = body.get('prefer_depth')
            phi_deg = float(body.get('phi_deg', 0.0))
            seconds = int(body.get('seconds', 15))
            flow_bins = int(body.get('flow_bins', 60))
            bk = await _discovery(loop)
            routable, _excluded = _rocks_from_backend(bk)
            pick, reason = _pick(routable,
                                 need_sign=int(need_sign) if need_sign in (+1,-1,'1','-1',1,-1) else None,
                                 prefer_depth=prefer_depth if prefer_depth in ('DEEP','SHALLOW') else None)
            if not pick:
                STATS['route_errors'] += 1
                _write_json(writer, {'error':'unroutable','reason':reason}, '503 Service Unavailable')
                return
            payload = _experiment_body(pick, phi_deg=phi_deg, seconds=seconds, flow_bins=flow_bins)
            try:
                out = await _submit(loop, payload)
                STATS['routed'] += 1
                STATS['per_rock'][pick['node']] = STATS['per_rock'].get(pick['node'], 0) + 1
                _write_json(writer, {
                    'conduit':'coupled-tunnel',
                    'routed_to':pick,
                    'route_reason':reason,
                    'submitted':payload,
                    'result':out,
                })
            except Exception as e:
                STATS['downstream_errors'] += 1
                _write_json(writer, {'conduit':'coupled-tunnel',
                                     'routed_to':pick,
                                     'downstream_error':str(e)[:300]}, '502 Bad Gateway')

        else:
            _write_json(writer, {'error':'not found',
                                 'routes':['/health','/tunnel/map','/tunnel/flow',
                                           'POST /tunnel/route','POST /tunnel/experiment']},
                        '404 Not Found')
        await writer.drain()
    except Exception:
        pass
    finally:
        try: writer.close()
        except Exception: pass


async def main(port=8096):
    loop = asyncio.get_event_loop()
    loop.set_default_executor(cf.ThreadPoolExecutor(max_workers=32))
    server = await asyncio.start_server(handle, '0.0.0.0', port)
    print(f'coupled-tunnel conduit on :{port} - downstream {LATTICE_URL}', flush=True)
    print(f'  hard gate: r in {HOLD_BAND}   floor: r<={FLOOR_R} never routable', flush=True)
    print(f'  routes: /health  /tunnel/map  /tunnel/flow  POST /tunnel/route  POST /tunnel/experiment', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8096
    asyncio.run(main(port))
