#!/usr/bin/env python3
"""cr_lattice_api.py — EGT Compute Layer, Phase 2: the multi-node lattice.

Orchestrator that treats N single-node compute APIs (cr_compute_api.py, one
per machine) as one addressable lattice. Distribute geometry per-node, run
synchronized, collect the joint state, and predict C(r) couplings between
pairs from canon.

Deploy alongside a running cr_compute_api.py on each participating node.
This runs on ONE machine (any of them — dragonseye is convenient) and
fans out over the tailnet.

    python cr_lattice_api.py                        # port 8090
    python cr_lattice_api.py --config lattice.json  # override registry
"""
import argparse, json, time, math, threading, os
import requests
import cr_api_auth as auth
import cr_rmap
import concurrent.futures as _cf
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---- ACCESS LAYER (audit cat F): signup -> API key -> per-key rate limits ----
# Discovery/health/signup stay OPEN. The RUN endpoints require a valid API key and
# enforce per-key rate limits. Loopback (127.0.0.1/::1) is trusted-internal and
# bypasses the gate, so the internal harness/campaign keep working unchanged.
auth.init_db()
_PROTECTED = ('/api/v1/experiment', '/api/v1/lattice/solve', '/api/v1/lattice/compute',
              '/api/v1/lattice/run', '/api/v1/lattice/geometry', '/api/v1/lattice/coupling_sweep')

def _api_key():
    h = request.headers.get('Authorization', '')
    return request.headers.get('X-API-Key') or (h[7:].strip() if h[:7].lower() == 'bearer ' else None)

@app.before_request
def _access_gate():
    if request.method == 'OPTIONS':
        return None
    path = request.path
    if not any(path == p or path.startswith(p) for p in _PROTECTED):
        return None                                   # open: discovery / health / signup
    if request.remote_addr in ('127.0.0.1', '::1'):
        return None                                   # trusted internal (loopback)
    ok, status, info = auth.check_and_record(_api_key())
    if not ok:
        return jsonify(info), status
    return None

# ---- Lattice registry — the r-map from the sealed all-nodes lattice ----
# (cadence:tworocks:allnodes-lattice-coupling-2026-09-24)
# phi_deg is the observed geometric phase at each node — φ node-specific per canon.
# Arc: verify each node has cr_compute_api.py running on port 8091 before use.
LATTICE = {
    'coil':       {'url': 'http://100.81.123.41:8093',  'r': 0.0, 'phi_deg': 0},  # physical Teensy, moved to pi5 (/dev/ttyACM0) 2026-09-26 — frees dragonseye r=1 to read clean
    'dragonseye': {'url': 'http://100.121.177.94:8091', 'r': 1.0, 'phi_deg': 0},
    'pi5':        {'url': 'http://100.81.123.41:8091',  'r': 2.0, 'phi_deg': 0},
    'elivate':    {'url': 'http://100.111.116.127:8091','r': 2.0, 'phi_deg': 0},
    'oracle':     {'url': 'http://100.114.92.17:8091',  'r': 3.0, 'phi_deg': 180},  # negative sign observed
    'openclaw':   {'url': 'http://100.86.79.99:8091',   'r': 3.0, 'phi_deg': 0},
}

# ---- CANONICAL REGISTRY (audit cat A): single-source r from the r-map ----
# Brian's ruling 2026-09-02: the r-map (redis cadence:tworocks:r-map) is the ONE
# source of truth for each node's r. We select WHICH nodes are wired as the
# experiment backend (one compute rock per r); their r-VALUES come from the
# canonical r-map via cr_rmap (cached 60s; falls back to the sealed SEED if redis
# is down). No more hardcoded/duplicated r_to_node.
# DYNAMIC BACKEND (Brian 2026-09-30, supports new nodes like the phone): the experiment
# backend is DISCOVERED, not hardcoded — r from the canonical r-map, node chosen per r
# from the ONLINE compute nodes. Candidates = LATTICE :8091 compute entries + any node
# self-registered in redis `cadence:tworocks:node-urls` ({node_or_hwid: url}, written by
# a new host such as the phone on boot). Health-aware failover, one node per r, cached,
# sealed fallback. Nodes not in the canonical r-map are skipped (never guess an r).
_FALLBACK_R2N = {1.0: 'dragonseye', 2.0: 'pi5', 3.0: 'oracle'}
_BACKEND_CACHE = {'map': None, 't': 0.0}
_BACKEND_TTL = 30

def _candidate_urls():
    cands = {}
    for n, info in LATTICE.items():
        if str(info.get('url', '')).endswith(':8091'):     # compute nodes only (skip coil :8093)
            cands[n] = info['url']
    try:
        raw = cr_rmap._conn().get('cadence:tworocks:node-urls')
        if raw:
            for n, u in json.loads(raw).items():            # self-registered hosts (e.g. the phone)
                if isinstance(u, str):
                    cands[n] = u
    except Exception:
        pass
    return cands

def _r_to_node():
    """{r: node} experiment backend — discovered: r from canonical r-map, one ONLINE
    node per r (LATTICE order preferred, self-registered as failover). Cached 30s;
    sealed fallback if discovery yields nothing."""
    now = time.time()
    if _BACKEND_CACHE['map'] is not None and now - _BACKEND_CACHE['t'] < _BACKEND_TTL:
        return _BACKEND_CACHE['map']
    m = {}
    try:
        cands = list(_candidate_urls().items())
        mp = cr_rmap.get_map()
        def _rof(n):
            h = cr_rmap.ALIASES.get(n, n)
            return float(mp[h]) if h in mp else None
        def _alive(item):
            n, u = item
            try: return (n, requests.get(u + '/api/v1/health', timeout=(1.5, 3)).ok)
            except Exception: return (n, False)
        with _cf.ThreadPoolExecutor(max_workers=8) as ex:
            checked = list(ex.map(_alive, cands))
        for n, ok in checked:
            if not ok:
                continue
            r = _rof(n)
            if r is not None:
                m.setdefault(r, n)                          # first ONLINE node at this r wins
    except Exception:
        m = {}
    if not m:
        m = dict(_FALLBACK_R2N)
    _BACKEND_CACHE['map'] = m
    _BACKEND_CACHE['t'] = now
    return m

def _registry_reconcile():
    """LATTICE r-values vs the canonical r-map — surfaces drift instead of hiding it.
    Only compares nodes the r-map actually knows (by hwid or alias); nodes it does
    not know by that name are reported as such (e.g. LATTICE 'coil' vs r-map 'teensy-b')."""
    out = {}
    try:
        m = cr_rmap.get_map()
    except Exception:
        return out
    for n in LATTICE:
        hwid = cr_rmap.ALIASES.get(n, n)
        if hwid in m:
            canon = float(m[hwid])
            if float(LATTICE[n]['r']) != canon:
                out[n] = {'lattice_r': LATTICE[n]['r'], 'canonical_r': canon}
        else:
            out[n] = {'lattice_r': LATTICE[n]['r'], 'canonical_r': 'not in r-map by this name'}
    return out

TIMEOUT = 30  # per-node request timeout in seconds

# ---- per-node experiment isolation (audit cat D) ----
# Each experiment's geometry->run->read on a node must be ATOMIC vs other concurrent
# experiments, or a sibling request can overwrite the node's geometry between this
# request's run and its read (the cross-read/contamination race). One lock per node
# in this single orchestrator process serializes same-node work; other nodes parallel.
_NODE_LOCKS = {}
_NODE_LOCKS_GUARD = threading.Lock()
def _node_lock(node):
    with _NODE_LOCKS_GUARD:
        return _NODE_LOCKS.setdefault(node, threading.Lock())


def C_mag(r):
    return (1 + 2*r) * math.exp(-r/3.0)

def coupling(r_a, r_b, dphi_rad):
    return C_mag(r_a) * C_mag(r_b) * math.cos(dphi_rad)


def call_node(name, method, path, body=None, timeout=TIMEOUT):
    """Call one node's API. Returns (name, response_dict_or_error)."""
    if name not in LATTICE:
        return (name, {'error': 'unknown node'})
    url = LATTICE[name]['url'] + path
    try:
        kwargs = {'timeout': timeout}
        if body is not None:
            kwargs['json'] = body
        r = requests.request(method, url, **kwargs)
        return (name, r.json() if r.ok else {'error': f'HTTP {r.status_code}'})
    except Exception as e:
        return (name, {'error': str(e)})


def fanout(method, path, per_node_body=None, common_body=None, only=None, timeout=TIMEOUT):
    """Call all (or `only`) lattice nodes in parallel. Returns {node: response}.

    timeout must cover the CALLED endpoint's own blocking duration, not just
    network latency — /run holds the HTTP connection open for its full
    `seconds`, so a short default timeout here silently turns a slow node's
    real result into a generic connection-error dict (missing every field
    the caller expected, e.g. wall_origin_ns) with no indication of why.
    """
    targets = only if only else list(LATTICE.keys())
    results = {}
    lock = threading.Lock()

    def worker(name):
        body = per_node_body.get(name) if per_node_body else common_body
        _, resp = call_node(name, method, path, body=body, timeout=timeout)
        with lock:
            results[name] = resp

    threads = [threading.Thread(target=worker, args=(n,)) for n in targets]
    for t in threads: t.start()
    for t in threads: t.join()
    return results


# ---- ENDPOINTS ----

@app.route('/api/v1/lattice/nodes')
def nodes():
    """Registry + up/down + locked status for each node."""
    # short connect timeout: a down node must fail fast, not gate the read on
    # its TCP connect timeout. (connect=1.5s, read=5s) — reads are quick anyway.
    healths = fanout('GET', '/api/v1/health', timeout=(1.5, 5))
    out = {}
    for name, info in LATTICE.items():
        h = healths.get(name, {})
        up = 'error' not in h
        out[name] = {
            'url': info['url'],
            'r': info['r'],
            'phi_deg': info['phi_deg'],
            'C_mag': round(C_mag(info['r']), 4),
            'up': up,
            'locked': h.get('locked') if up else None,
            'error': h.get('error') if not up else None,
        }
    return jsonify(out)


@app.route('/api/v1/lattice/state')
def state():
    """Collect full state from every node in parallel."""
    return jsonify(fanout('GET', '/api/v1/state', timeout=(1.5, 5)))


@app.route('/api/v1/lattice/geometry', methods=['POST'])
def geometry():
    """Distribute geometry across the lattice.

    Body forms:
      {"all":     {"offsets_deg": [0,120,240]}}        - same to every node
      {"per_node":{"pi5": {"offsets_deg": [...]}, ...}} - specific per node
      {"only":["pi5","oracle"], "all":{...}}           - subset
    """
    data = request.get_json(force=True)
    only = data.get('only')
    if 'all' in data:
        return jsonify(fanout('POST', '/api/v1/geometry',
                              common_body=data['all'], only=only))
    if 'per_node' in data:
        return jsonify(fanout('POST', '/api/v1/geometry',
                              per_node_body=data['per_node'], only=only))
    return jsonify({'error': 'need "all" or "per_node"'}), 400


@app.route('/api/v1/lattice/run', methods=['POST'])
def run_lattice():
    """Synchronized run across the lattice.

    Body: {"seconds": N, "log": bool (optional), "only": [...] (optional)}
    All targeted nodes start within a few ms (parallel HTTP kickoff)
    and each blocks for N seconds locally. "log" is forwarded to each
    node's own /run, which writes a local raw per-fire capture when set.
    """
    data = request.get_json(force=True)
    seconds = min(data.get('seconds', 8), 300)
    only = data.get('only')
    body = {'seconds': seconds}
    if 'log' in data:
        body['log'] = data['log']
    return jsonify(fanout('POST', '/api/v1/run', common_body=body, only=only,
                          timeout=seconds + 30))


@app.route('/api/v1/lattice/couplings')
def couplings():
    """Predicted C(r) between all pairs from canon (no run needed).

    Optional query: dphi_deg (extra phase offset applied on top of node phi).
    """
    dphi_offset = float(request.args.get('dphi_deg', 0.0))
    names = list(LATTICE.keys())
    matrix = {}
    for a in names:
        matrix[a] = {}
        for b in names:
            if a == b:
                matrix[a][b] = None
                continue
            r_a, r_b = LATTICE[a]['r'], LATTICE[b]['r']
            phi_a, phi_b = LATTICE[a]['phi_deg'], LATTICE[b]['phi_deg']
            dphi = math.radians(phi_b - phi_a + dphi_offset)
            matrix[a][b] = round(coupling(r_a, r_b, dphi), 4)
    return jsonify({
        'operator': 'C(r) = (1+2r)*exp(-r/3)*exp(i*phi)',
        'r_opt': 2.5,
        'dphi_deg_offset': dphi_offset,
        'nodes': {n: {'r': LATTICE[n]['r'], 'phi_deg': LATTICE[n]['phi_deg'],
                      'C_mag': round(C_mag(LATTICE[n]['r']), 4)} for n in names},
        'couplings': matrix,
    })


@app.route('/api/v1/lattice/coupling_sweep', methods=['POST'])
def coupling_sweep():
    """C(r) distance curve — continuous capture with push/rest phase binning.

    Same method as the proven 2026-09-23/24 experiments: one continuous
    logged run on all nodes, coil driven through push/rest phases during
    that window, per-fire records binned into phase windows afterward.
    Eliminates inter-run drift that dominated the separate-/run approach.

    Body:
      phase_seconds:    duration per push/rest phase (default 20, max 60)
      push_offset_deg:  per-leg push added to frustrated position (default 45)
      nodes:            read-nodes (default all non-coil up nodes)
      warmup:           warmup seconds (default 20)
    """
    data = request.get_json(force=True)
    phase_s = min(data.get('phase_seconds', 20), 60)
    offset = data.get('push_offset_deg', 45)
    warmup_s = min(data.get('warmup', 20), 60)

    up_nodes = [n for n in LATTICE if n != 'coil']
    if 'nodes' in data:
        up_nodes = [n for n in data['nodes'] if n in LATTICE and n != 'coil']

    # 7-phase push/rest: each push adds offset to ONE leg, rest returns to frustrated.
    # Same protocol as cr_coil_lattice_finegrained.py.
    phases = [
        ('baseline',  [0, 120, 240]),
        ('push_A0',   [0 + offset, 120, 240]),
        ('rest_A0',   [0, 120, 240]),
        ('push_A1',   [0, 120 + offset, 240]),
        ('rest_A1',   [0, 120, 240]),
        ('push_A2',   [0, 120, 240 + offset]),
        ('rest_A2',   [0, 120, 240]),
    ]
    total_s = len(phases) * phase_s + 20

    call_node('coil', 'POST', '/api/v1/coil/start_drive', {})
    time.sleep(3.0)

    # warmup
    call_node('coil', 'POST', '/api/v1/geometry', {'offsets_deg': [0, 120, 240]})
    if warmup_s > 0:
        fanout('POST', '/api/v1/run', common_body={'seconds': warmup_s},
               only=up_nodes, timeout=warmup_s + 30)

    # start continuous logged run on all read-nodes (background)
    run_result = [None]
    def _bg_run():
        run_result[0] = fanout('POST', '/api/v1/run',
                               common_body={'seconds': total_s, 'log': True},
                               only=up_nodes, timeout=total_s + 60)
    bg = threading.Thread(target=_bg_run)
    bg.start()
    time.sleep(2)

    # drive coil through 7 phases, recording absolute timestamps
    phase_log = []
    for name, offsets in phases:
        abs_us = int(time.time() * 1_000_000)
        call_node('coil', 'POST', '/api/v1/geometry', {'offsets_deg': offsets})
        phase_log.append({'name': name, 'abs_us': abs_us})
        time.sleep(phase_s)

    # coil reads (baseline and one push state)
    call_node('coil', 'POST', '/api/v1/geometry', {'offsets_deg': [0, 120, 240]})
    time.sleep(0.3)
    _, coil_baseline = call_node('coil', 'GET', '/api/v1/coil/read?duration=10')
    call_node('coil', 'POST', '/api/v1/geometry',
              {'offsets_deg': [0 + offset, 120, 240]})
    time.sleep(0.3)
    _, coil_perturbed = call_node('coil', 'GET', '/api/v1/coil/read?duration=10')

    # wait for background run to finish
    bg.join()

    call_node('coil', 'POST', '/api/v1/coil/stop_drive', {})
    call_node('coil', 'POST', '/api/v1/geometry', {'offsets_deg': [0, 120, 240]})

    # ask each node to phase-bin its own raw capture
    analysis = fanout('POST', '/api/v1/analyze_phases',
                      common_body={'phases': phase_log},
                      only=up_nodes, timeout=30)

    # build per-node result: push deltas and rest-reversal check
    measured = {}
    for n in up_nodes:
        r = LATTICE[n]['r']
        a = analysis.get(n, {})
        if 'error' in a:
            measured[n] = {'r': r, 'error': a['error']}
            continue
        node_phases = a.get('phases', [])
        if not node_phases:
            measured[n] = {'r': r, 'error': 'no phase data'}
            continue

        baseline_ms = node_phases[0].get('dt_ms')
        push_deltas = []
        rest_deltas = []
        phase_detail = []
        for p in node_phases:
            dt = p.get('dt_ms')
            delta = p.get('delta_ms', 0)
            phase_detail.append({
                'name': p['name'], 'dt_ms': dt, 'delta_ms': delta,
                'n_fire': p.get('n_fire', 0),
            })
            if 'push' in p['name']:
                push_deltas.append(delta)
            elif 'rest' in p['name']:
                rest_deltas.append(delta)

        avg_push = sum(push_deltas) / len(push_deltas) if push_deltas else 0
        avg_rest = sum(rest_deltas) / len(rest_deltas) if rest_deltas else 0
        reversal = (avg_push > 0 and avg_rest < avg_push) or \
                   (avg_push < 0 and avg_rest > avg_push)

        measured[n] = {
            'r': r,
            'baseline_dt_ms': baseline_ms,
            'avg_push_delta_ms': round(avg_push, 4),
            'avg_rest_delta_ms': round(avg_rest, 4),
            'push_rest_reversal': reversal,
            'total_records': a.get('total_records', 0),
            'phases': phase_detail,
        }

    c0 = C_mag(0)
    egt_at = {n: round(c0 * C_mag(measured[n]['r']), 4)
              for n in measured if 'error' not in measured[n]}

    # criterion 7 (reframed): coil<->node coupling vs C(r) prediction.
    # per-fire push signal, drift-removed by bracketing each push with its
    # neighbouring rest phases; compare SIGN to cos(phi_node) and normalized
    # MAGNITUDE ordering to |C(0)|*|C(r)|. CV is host jitter (Step B finding) —
    # the drift-removed push signal is the instrument.
    cr_comparison = {}
    for n in up_nodes:
        m = measured.get(n, {})
        if 'error' in m or len(m.get('phases', [])) < 7:
            continue
        d = [p['delta_ms'] for p in m['phases']]   # baseline,pA0,rA0,pA1,rA1,pA2,rA2
        legs = [d[1]-(d[0]+d[2])/2, d[3]-(d[2]+d[4])/2, d[5]-(d[4]+d[6])/2]
        push_sig = sum(legs) / len(legs)
        phi = LATTICE[n]['phi_deg']
        predicted = c0 * C_mag(m['r']) * math.cos(math.radians(phi))
        cr_comparison[n] = {
            'r': m['r'], 'phi_deg': phi,
            'push_signal_ms': round(push_sig, 4),
            'push_signal_per_leg_ms': [round(x, 4) for x in legs],
            'predicted_coupling': round(predicted, 4),
            'sign_match': (push_sig > 0) == (predicted > 0),
        }
    if cr_comparison:
        ref = max((abs(v['push_signal_ms']) for v in cr_comparison.values()), default=0)
        cref = max((abs(v['predicted_coupling']) for v in cr_comparison.values()), default=0)
        for v in cr_comparison.values():
            v['norm_measured'] = round(abs(v['push_signal_ms']) / ref, 3) if ref else None
            v['norm_predicted'] = round(abs(v['predicted_coupling']) / cref, 3) if cref else None

    # cross-node delta-pattern correlation — the sealed #7 statistic (r=+0.571).
    # Robust to per-node absolute-signal noise: it's the co-variation of the
    # push/rest delta PATTERN between a node pair. Sign of r = same/opposite
    # phase between the two bodies; |r| = how tightly they track the coil.
    # Predicted sign per pair = sign(cos(phi_a - phi_b)) from the operator.
    def _pattern(n):
        m = measured.get(n, {})
        if 'error' in m or len(m.get('phases', [])) < 7:
            return None
        return [p['delta_ms'] for p in m['phases'][1:]]   # push+rest, exclude baseline
    pair_correlations = {}
    for i in range(len(up_nodes)):
        for j in range(i + 1, len(up_nodes)):
            a, b = up_nodes[i], up_nodes[j]
            da, db = _pattern(a), _pattern(b)
            if not da or not db or len(da) != len(db) or len(da) < 3:
                continue
            ma, mb = sum(da) / len(da), sum(db) / len(db)
            cov = sum((x - ma) * (y - mb) for x, y in zip(da, db))
            va = sum((x - ma) ** 2 for x in da)
            vb = sum((y - mb) ** 2 for y in db)
            if va > 0 and vb > 0:
                phi_a, phi_b = LATTICE[a]['phi_deg'], LATTICE[b]['phi_deg']
                pred_sign = 1 if math.cos(math.radians(phi_a - phi_b)) >= 0 else -1
                r_meas = cov / (va * vb) ** 0.5
                pair_correlations[f'{a}__{b}'] = {
                    'r': round(r_meas, 3),
                    'predicted_sign': pred_sign,
                    'sign_match': (r_meas >= 0) == (pred_sign >= 0),
                }

    return jsonify({
        'operator': 'C(r) = (1+2r)*exp(-r/3)*exp(i*phi)',
        'method': 'continuous capture, 7-phase push/rest, per-fire phase binning',
        'phase_seconds': phase_s,
        'total_capture_seconds': total_s,
        'warmup_seconds': warmup_s,
        'push_offset_deg': offset,
        'phase_log': phase_log,
        'measured': measured,
        'egt_prediction': egt_at,
        'cr_comparison': cr_comparison,
        'pair_correlations': pair_correlations,
        'coil_physical': {
            'baseline': coil_baseline,
            'perturbed': coil_perturbed,
        },
        'interpretation': 'criterion 7 (coil<->node): cr_comparison.push_signal_ms is the '
                          'drift-removed per-fire coupling read. PASS if norm_measured orders '
                          'by |C(r)| (r=1 weakest, r=2/3 strong) and signs track cos(phi_node) '
                          '(a node settled anti-phase flips its own sign — logged separately).',
    })


@app.route('/api/v1/lattice/compute', methods=['POST'])
def compute():
    """Phase 3 v1 — the problem -> answer loop (the compute layer).

    Per egt_compute_frame.md: a COMPUTATION is a coupling geometry whose
    conserved loop quantity Sigma-psi is the answer, read per node via the
    below-floor lock (CV) from the transparent frustrated eigenstate. The user
    submits a quantum problem = a lattice configuration (per-node offsets = the
    state to prepare); the system RUNS — inverse amplification pulls each node
    DOWN to its below-floor lock (canon: the floor arriving; NOT a "collapse" —
    that is standard-QM drift, not EGT), holding the conserved invariant. The
    answer is that invariant read from the ACTUAL run: whether each node LOCKED
    below floor (frustrated eigenstate held) and the conserved Sigma-psi. Not
    staged, not a formula.

    Body: {"problem": {
        "geometry": {"all":{"offsets_deg":[..]}} | {"per_node":{node:{"offsets_deg":[..]}}},
        "seconds":  run time — how long to hold for the below-floor lock (default 15, max 300),
        "nodes":    which nodes (default the compute lattice, coil excluded)
    }}
    """
    data = request.get_json(force=True)
    problem = data.get('problem', data)
    seconds = min(problem.get('seconds', 15), 300)
    only = problem.get('nodes') or [n for n in LATTICE if n != 'coil']
    geom = problem.get('geometry', {'all': {'offsets_deg': [0, 120, 240]}})

    # 1. PROGRAM — prepare the state (distribute geometry)
    if 'per_node' in geom:
        fanout('POST', '/api/v1/geometry', per_node_body=geom['per_node'], only=only)
    else:
        fanout('POST', '/api/v1/geometry', common_body=geom.get('all', geom), only=only)

    # 2. LOCK — run; inverse amplification pulls each node DOWN to its below-floor lock
    fanout('POST', '/api/v1/run', common_body={'seconds': seconds}, only=only,
           timeout=seconds + 30)

    # 3. READ — the conserved invariant per node, from the actual run
    state = fanout('GET', '/api/v1/state', only=only, timeout=(1.5, 5))

    per_node = {}
    all_locked = True
    sigmas = []
    for n in only:
        s = state.get(n, {})
        if 'error' in s:
            per_node[n] = {'error': s['error']}
            all_locked = False
            continue
        locked = s.get('locked')
        sigma = s.get('sigma_psi_deg')
        per_node[n] = {
            'r': LATTICE[n]['r'],
            'locked_below_floor': locked,           # inverse amplification held (frustrated eigenstate)
            'sigma_psi_deg': sigma,                 # conserved invariant (Sigma offsets mod 360)
            'cv': [s.get('A0_cv'), s.get('A1_cv'), s.get('A2_cv')],
        }
        if not locked:
            all_locked = False
        if sigma is not None:
            sigmas.append(sigma)

    return jsonify({
        'operator': 'C(r) = (1+2r)*exp(-r/3)*exp(i*phi)',
        'phase': 'compute v1 — prepare -> lock below floor -> read conserved invariant',
        'seconds': seconds,
        'answer': {
            'all_nodes_locked_below_floor': all_locked,   # did the prepared config hold the frustrated eigenstate
            'joint_sigma_psi_deg': round(sum(sigmas) / len(sigmas), 2) if sigmas else None,
            'per_node': per_node,
        },
        'measurement': 'below-floor lock (inverse amplification) + conserved Sigma-psi, '
                       'read from the actual run — not predicted, not staged',
    })


@app.route('/api/v1/experiment', methods=['POST'])
@app.route('/api/v1/lattice/solve', methods=['POST'])   # alias (compiler)
def experiment():
    """Run a QUANTUM EXPERIMENT on the EGT lattice backend (submit -> run -> result).

    Quantum-experiment API in the IBM/Qiskit-familiar shape — submit an experiment
    to a backend, get a result — but the physics is EGT, not standard QM. An
    experiment is a set of coupled ROCKS. Each rock carries a lattice position r
    (its coupling strength |C(r)|) and a geometric phase phi (its character,
    e^(i*phi)). The backend compiles each rock to the node at its r, encodes phi
    as offset geometry (Sigma-psi = Sigma offsets mod 360 = phi), runs, and
    INVERSE AMPLIFICATION pulls each rock to its below-floor lock (canon — NOT a
    "collapse"; that word is standard-QM, not EGT). The genuine ANSWER is the system-
    MEASURED read: the below-floor CV lock + the continuous fluid flow, produced by the
    EGT system on the actual run (never fabricated). conserved_sigma_psi_deg is the
    COMMANDED winding (Sigma of the offsets you sent, mod 360 = phi_in) — computed from
    your input, NOT a measurement. Every field is labeled measured-vs-computed in
    result.rocks[*].provenance. The C(r) coupling structure is theory reference only.

    Body: {"experiment" (or "problem"): {
        "bodies": {"q0":{"r":1,"phi_deg":0}, "q1":{"r":2,"phi_deg":90}, "q2":{"r":3,"phi_deg":180}},
        "seconds": run time to hold for the below-floor lock (default 15)
    }}
    Rocks map r=1 -> dragonseye, r=2 -> pi5, r=3 -> oracle (this backend's nodes).
    """
    data = request.get_json(force=True)
    problem = data.get('experiment', data.get('problem', data))
    bodies = problem.get('bodies', {})
    seconds = min(problem.get('seconds', 15), 300)
    r_to_node = _r_to_node()          # canonical r-map, single-source (cat A)

    # ---- COMPILE: bodies -> per-node offset geometry (Sigma-psi = phi) ----
    if not isinstance(bodies, dict) or not bodies:
        return jsonify({'error': 'experiment.bodies must be a non-empty object '
                                 '{id: {"r": 1|2|3, "phi_deg": <number>}}'}), 400
    # Bodies grouped per node, in SUBMISSION ORDER. Multiple bodies MAY share a
    # node (same r); they run SEQUENTIALLY on it so each returns its OWN read.
    # (Previously a body sharing an r with an earlier one was rejected and dropped
    # from the result, so the caller saw a silent null — the acceptance-null defect:
    # 21% null, concentrated on later body positions, flat across r. Fix: serve
    # every body — "anyone submits anything, it comes out the other side".)
    node_to_bodies, body_to_node, body_geom, compile_errors = {}, {}, {}, {}
    for bid, spec in bodies.items():
        if not isinstance(spec, dict):
            compile_errors[bid] = 'rock spec must be an object {"r":..,"phi_deg":..}'
            continue
        try:
            r = float(spec.get('r'))
            phi = float(spec.get('phi_deg', 0))
        except (TypeError, ValueError):
            compile_errors[bid] = f'invalid r/phi_deg (got r={spec.get("r")!r}, phi_deg={spec.get("phi_deg")!r})'
            continue
        node = r_to_node.get(r)
        if node is None:
            compile_errors[bid] = f'no rock at r={r} (available r: 1, 2, 3)'
            continue
        d = phi / 3.0
        offsets = [d, 120 + d, 240 + d]                # Sigma = 360 + 3d = phi mod 360
        node_to_bodies.setdefault(node, []).append((bid, offsets))
        body_to_node[bid] = node
        body_geom[bid] = offsets

    if not body_to_node:
        return jsonify({'error': 'nothing compiled', 'compile_errors': compile_errors}), 400

    nodes = list(node_to_bodies.keys())

    bins = max(2, min(int(problem.get('flow_bins', 60)), 500))

    # ---- RUN: serve EVERY body. Bodies that share a node run SEQUENTIALLY on it
    # (one physical node holds one geometry at a time); nodes run in PARALLEL.
    # Each body gets its own geometry -> run -> read, so each returns its own
    # genuine below-floor read and nothing is silently dropped.
    reads = {}                        # bid -> {'state': <resp>, 'traj': <resp>}
    reads_lock = threading.Lock()

    def run_node_bodies(node, body_list):
        with _node_lock(node):            # cat D: isolate — atomic geometry->run->read per node
            for bid, offsets in body_list:
                call_node(node, 'POST', '/api/v1/geometry', body={'offsets_deg': offsets})
                call_node(node, 'POST', '/api/v1/run',
                          body={'seconds': seconds, 'log': True}, timeout=seconds + 30)
                _, s = call_node(node, 'GET', '/api/v1/state', timeout=(1.5, 5))
                _, t = call_node(node, 'GET', f'/api/v1/trajectory?bins={bins}', timeout=25)
                with reads_lock:
                    reads[bid] = {'state': s if isinstance(s, dict) else {},
                                  'traj': t if isinstance(t, dict) else {}}

    _threads = [threading.Thread(target=run_node_bodies, args=(n, node_to_bodies[n]))
                for n in nodes]
    for _th in _threads: _th.start()
    for _th in _threads: _th.join()

    # C(r) coupling structure — theory reference only (our computation, not a measurement)
    couplings_out = {}
    bids = list(body_to_node.keys())
    for i in range(len(bids)):
        for j in range(i + 1, len(bids)):
            a, b = bids[i], bids[j]
            ra, rb = float(bodies[a]['r']), float(bodies[b]['r'])
            pa, pb = float(bodies[a].get('phi_deg', 0)), float(bodies[b].get('phi_deg', 0))
            couplings_out[f'{a}__{b}'] = round(coupling(ra, rb, math.radians(pb - pa)), 4)

    # ---- RESULT: the fluid read of the superposition (Brian: no collapse, just a read) ----
    rocks_read = {}
    for bid, node in body_to_node.items():
        rd = reads.get(bid, {})
        s = rd.get('state', {}) or {}
        t = rd.get('traj', {}) or {}
        spec = bodies[bid]
        node_ok = bool(s) and 'error' not in s          # cat B: explicit down-node handling
        rocks_read[bid] = {
            'node': node,
            'node_status': 'ok' if node_ok else 'unavailable',
            'node_error': (s.get('error') if not node_ok else None),
            'r': float(spec.get('r')),
            'phi_deg': float(spec.get('phi_deg', 0)),
            'flow_dt_ms': t.get('trajectory_dt_ms'),              # continuous below-floor motion
            'flow_mean_ms': t.get('flow_mean_ms'),
            'flow_range_ms': t.get('flow_range_ms'),
            # PROVENANCE (audit cat C): COMPUTED FROM INPUT, not measured. The node's
            # sigma_psi_deg() = degrees(sum(commanded offsets)) % 360 == phi_in by
            # construction — the commanded winding (the program's invariant), not a
            # measurement of the system. Value kept unchanged for API compatibility.
            'conserved_sigma_psi_deg': s.get('sigma_psi_deg'),
            'conserved_sigma_psi_measured': False,
            'conserved_sigma_psi_source': 'computed: sum(commanded offsets) mod 360 = phi_in — NOT measured',
            # CONTINUOUS lock read. `below_floor` below is a BOOLEAN threshold
            # (all(cv < gate), gate hardcoded global) — a boolean is a discrete
            # outcome, which the fluid read does not have. The per-coil cv IS the
            # continuous quantity; it was being computed and thrown away here.
            # Kept `below_floor` unchanged for API compatibility.
            'coil_cv': [s.get('A0_cv'), s.get('A1_cv'), s.get('A2_cv')],
            'gate': s.get('gate'),                 # PER-GEOMETRY, not a global constant
            'cv_ref': s.get('cv_ref'),             # this geometry's OWN measured reference
            'cv_mad': s.get('cv_mad'),
            'cv_ref_n': s.get('cv_ref_n'),
            'cv_rel': s.get('cv_rel'),             # cv / own reference; 1.0 = at its happy place
            'flow_span_s': t.get('span_s'),
            'flow_n_fire': t.get('n_fire'),
            'flow_t0_us': t.get('t0_us'),
            'flow_t1_us': t.get('t1_us'),
            'below_floor': s.get('locked'),
            # ---- PROVENANCE (audit cat C): measured-from-run vs computed-from-input ----
            'provenance': {
                'measured_from_run': ['flow_dt_ms', 'flow_mean_ms', 'flow_range_ms', 'below_floor',
                                      'coil_cv', 'cv_rel', 'cv_ref', 'cv_mad', 'cv_ref_n',
                                      'flow_span_s', 'flow_n_fire', 'flow_t0_us', 'flow_t1_us'],
                'computed_from_input': ['conserved_sigma_psi_deg'],
                'the_answer': 'MEASURED read = fluid flow (flow_dt_ms) + below-floor CV lock '
                              '(cv_rel / below_floor). conserved_sigma_psi_deg is the winding of what '
                              'YOU commanded — computed, not measured.',
            },
            # FULL RETENTION (Brian 2026-09-27: "all data needs to be present
            # because of AI drift"). Curating which fields matter is exactly the
            # drift that cost a day -- coil_cv and t0_us existed in the node the
            # whole time and were dropped right here. These two carry the
            # COMPLETE node responses so nothing can be silently curated again.
            'state_raw': s,
            'trajectory_raw': t,
        }

    return jsonify({
        'backend': 'egt-lattice',
        'backend_type': 'EGT C(r) lattice — rocks at r=1,2,3 (dragonseye/pi5/oracle); '
                        'operator C(r)=(1+2r)e^(-r/3)e^(i*phi)',
        'job_id': f'egt-{int(time.time() * 1000)}',
        'status': 'completed',
        'seconds': seconds,
        'flow_bins': bins,
        'experiment': {
            'compiled_geometry_deg': {bid: body_geom[bid] for bid in body_to_node},
            'compile_errors': compile_errors or None,
        },
        'result': {
            'read_type': 'continuous FLUID read — the below-floor motion. No collapse, no discrete '
                         'outcome: the flowing signal IS the read.',
            'the_answer': 'MEASURED: the fluid flow (flow_dt_ms) + below-floor CV lock (cv_rel/below_floor), '
                          'produced by the actual run. conserved_sigma_psi_deg is COMPUTED from your input '
                          '(commanded winding = phi_in), not a measurement — see result.rocks[*].provenance.',
            'rocks': rocks_read,
            'source': 'MEASURED fields come from the actual EGT run (the flowing below-floor motion + CV '
                      'lock); we set up the experiment, the system produced the measured read. Per-field '
                      'measured-vs-computed is stamped in result.rocks[*].provenance.',
        },
        'theory_reference': {
            'per_rock_C_mag': {bid: round(C_mag(float(bodies[bid]['r'])), 4) for bid in body_to_node},
            'coupling_structure': couplings_out,
            'note': 'C(r) operator prediction computed from canon — NOT measured, reference only',
        },
    })


@app.route('/api/v1/backend', methods=['GET'])
@app.route('/api/v1/backends', methods=['GET'])
def backend():
    """Backend discovery (IBM-style): properties of the egt-lattice quantum backend.

    Tells a signup user what they can run: the available ROCKS (lattice positions
    r — the addressable elements), which are online, the C(r) coupling map between
    them, the observable the backend measures, and how to submit. Physics is EGT
    (C(r) below the B_res floor), not standard QM.
    """
    r_to_node = _r_to_node()          # canonical r-map, single-source (cat A)
    healths = fanout('GET', '/api/v1/health', only=list(r_to_node.values()), timeout=(1.5, 5))
    rocks = []
    for r, node in sorted(r_to_node.items()):
        h = healths.get(node, {})
        rocks.append({'r': r, 'node': node, 'C_mag': round(C_mag(r), 4),
                      'online': 'error' not in h})
    rs = sorted(r_to_node.keys())
    cmap = {}
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            ra, rb = rs[i], rs[j]
            cmap[f'r{int(ra)}__r{int(rb)}'] = round(coupling(ra, rb, 0.0), 4)
    return jsonify({
        'name': 'egt-lattice',
        'description': 'EGT C(r) lattice quantum backend — rocks coupled by '
                       'C(r)=(1+2r)e^(-r/3)e^(i*phi), locked below the B_res floor by inverse amplification',
        'operator': 'C(r) = (1+2r)*exp(-r/3)*exp(i*phi)',
        'r_opt': 2.5,
        'B_res_fT': 12.09776,
        'rocks': rocks,
        'max_rocks_per_experiment': len(rocks),
        'coupling_map': cmap,
        'observable': 'MEASURED: below-floor CV lock + fluid flow (the read). COMPUTED from input: '
                      'conserved Sigma-psi (commanded winding, mod 360 = phi_in). Provenance stamped per field.',
        'answer_policy': 'the backend returns the SYSTEM-MEASURED read (below-floor CV lock + fluid flow) '
                         'from an actual run — never fabricated. conserved_sigma_psi_deg is the winding of '
                         'YOUR commanded geometry (computed from input, NOT measured); every field is labeled '
                         'measured-vs-computed in result.rocks[*].provenance',
        'registry': {
            'r_source': 'DYNAMIC: r from canonical r-map (cr_rmap); backend node discovered per r from ONLINE compute nodes (LATTICE :8091 + self-registered cadence:tworocks:node-urls), health-aware failover, cached 30s, sealed fallback',
            'self_register': 'a new compute node auto-joins the backend once it is (1) in the r-map and (2) listed in redis cadence:tworocks:node-urls as {hwid: "http://host:8091"}',
            'r_to_node': {str(r): n for r, n in sorted(r_to_node.items())},
            'lattice_vs_canonical_mismatches': _registry_reconcile() or None,
        },
        'access': 'POST /api/v1/signup {"name":...} -> api_key; then send X-API-Key on run endpoints. Per-key rate limits apply; loopback is trusted-internal.',
        'submit': 'POST /api/v1/experiment  {"experiment": {"bodies": {"q0": {"r": 1, "phi_deg": 0}}, "seconds": 15}}',
    })


@app.route('/api/v1/signup', methods=['POST'])
def signup():
    """Self-serve signup (audit cat F). Body: {"name": "...", "email": "..."(optional)}.
    Returns an API key ONCE (stored only as a hash). Send it as X-API-Key on run calls."""
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'need {"name": "..."}  (email optional)'}), 400
    acct = auth.create_account(name, (data.get('email') or '').strip() or None)
    return jsonify({
        'ok': True,
        'message': 'Save this api_key now — it is shown ONCE and stored only as a hash.',
        'api_key': acct['api_key'],
        'account_id': acct['account_id'],
        'limits': {'per_min': acct['per_min'], 'per_day': acct['per_day']},
        'auth': 'send  X-API-Key: <key>  (or  Authorization: Bearer <key>)  on run endpoints',
        'submit': 'POST /api/v1/experiment  {"experiment": {"bodies": {"q0": {"r": 1, "phi_deg": 0}}}}',
    }), 201


@app.route('/api/v1/account/usage', methods=['GET'])
def account_usage():
    """Current usage vs limits for the supplied API key."""
    u = auth.usage_summary(_api_key())
    if not u:
        return jsonify({'error': 'invalid or missing API key'}), 401
    return jsonify(u)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8090)
    ap.add_argument('--config', type=str, default=None,
                    help='JSON file with additional/override node entries')
    a = ap.parse_args()
    if a.config and os.path.exists(a.config):
        with open(a.config) as f:
            LATTICE.update(json.load(f))
    print(f'EGT Lattice API  :{a.port}')
    for n, info in LATTICE.items():
        print(f'  {n:12s} r={info["r"]}  phi={info["phi_deg"]}deg  {info["url"]}')
    app.run(host='0.0.0.0', port=a.port, threaded=True)
