#!/usr/bin/env python3
"""cr_coil_api.py — the physical coil (Teensy, COM8) as a lattice node.

Unlike cr_compute_api.py, this node runs no kernel and has no CV — it is
r=0, the physical actor. Its "geometry" is the coil's real per-leg phase
offsets, set by writing directly to COM8. Its "run" holds the current
offsets for N seconds (the coil is set-and-forget hardware; it needs no
polling loop to maintain a position) so it fits the same set -> run -> read
cycle every other lattice node uses, and so a synchronized /lattice/run
call can include it without special-casing the orchestrator.

This is what makes the coil addressable inside the lattice instead of only
reachable through a one-off script that opens COM8 directly.
"""
import argparse, time, math, threading, serial
from flask import Flask, request, jsonify

app = Flask(__name__)
_lock = threading.Lock()
_start = time.time()
_ser = None
_com = None
_baud = None
_offsets_deg = [0.0, 120.0, 240.0]  # wrapped [0,360) — what's actually sent to the Teensy
# Wrapping is lossy (-270 and +90 send the identical serial command and are
# indistinguishable afterward). These preserve what wrapping throws away:
_offsets_commanded_deg = [0.0, 120.0, 240.0]     # last value AS SENT, unwrapped, signed
_cumulative_rotation_deg = [0.0, 0.0, 0.0]        # signed running total per leg, never wraps


def _reopen():
    global _ser
    try:
        _ser.close()
    except Exception:
        pass
    time.sleep(1.0)
    _ser = serial.Serial(_com, _baud, timeout=1, write_timeout=2)
    time.sleep(0.3)
    _ser.reset_input_buffer()
    _ser.reset_output_buffer()


def _drain():
    # Bounded on purpose: a `while in_waiting: readline()` drain never exits while
    # the Teensy is streaming, and it runs under _lock (stalled :8093 for minutes).
    try:
        _ser.reset_input_buffer()
    except Exception:
        pass


def _write_leg(leg, deg):
    """Write one leg's offset. The Teensy's USB serial occasionally glitches
    under sustained use (WriteFile PermissionError) — reopen once and retry
    rather than failing the request, the same recovery cr_coil_driver_resilient
    uses for the standalone driver."""
    try:
        _ser.write(f'O {leg} {deg}\n'.encode())
    except serial.SerialException:
        _reopen()
        _ser.write(f'O {leg} {deg}\n'.encode())
    time.sleep(0.08)
    _drain()


def _send_cmd(cmd, settle=0.35, wait_ack=True):
    """Write one command, wait for the Teensy's 'R ...' ack line (same
    contract as hold_allday_overlay.py's send()), then settle. Returns the
    ack lines seen."""
    try:
        _ser.write((cmd + '\n').encode())
    except serial.SerialException:
        _reopen()
        _ser.write((cmd + '\n').encode())
    out = []
    t0 = time.time()
    while wait_ack and time.time() - t0 < 2.5:
        try:
            line = _ser.readline().decode(errors='replace').strip()
        except serial.SerialException:
            _reopen()
            break
        if line:
            out.append(line)
        if line.startswith('R '):
            break
    time.sleep(settle)
    return out


def _start_two_tone_drive(base_freq=16, overlay_freq=20, mix=1, td=100):
    """The canonical two-tone counter-torque start sequence — Brian's proven
    'right set' (TD100 + symmetric), verbatim from hold_allday_overlay.py's
    set_drive(). This is what actually starts the drive loop; O-offsets alone
    (everything sent so far this session) never turned this on."""
    log = {}
    _send_cmd('\nx', 0.4)                                  # stop/reset
    _send_cmd('O 0 0'); _send_cmd('O 1 0'); _send_cmd('O 2 0')  # symmetric
    _send_cmd(f'TD {td}')                                   # full opposition strength
    log['T'] = _send_cmd(f'T {overlay_freq}')
    log['TM'] = _send_cmd(f'TM {mix}')
    _send_cmd('M 3'); _send_cmd('K 0')
    log['L'] = _send_cmd(f'L {base_freq}', 0.8)              # starts the loop
    return log


def _sigma_psi_deg():
    return sum(_offsets_deg) % 360.0


def _read_magnitudes(duration=2.0):
    """Read T3 lines for `duration` seconds and average each leg's magnitude
    and phase. Every T3 line carries all three legs at once (no channel
    cycling needed for the VALUES). The channel command must be re-sent
    every ~2s to keep the stream flowing — a single 'C 0 1' only produces a
    short burst, per the protocol every prior T3-reading script here uses.

    Also reads any non-T3 lines to see what the firmware IS sending (debug)."""
    raw_lines = []
    _drain()
    mags = [[], [], []]
    phases = [[], [], []]
    t0 = time.time()
    ch = 0
    while time.time() - t0 < duration:
        elapsed = time.time() - t0
        new_ch = int(elapsed / 2) % 3
        if new_ch != ch or elapsed < 0.05:
            ch = new_ch
            try:
                _ser.write(f'C {ch} {(ch+1)%3}\n'.encode())
                time.sleep(0.05)
            except serial.SerialException:
                try:
                    _reopen()
                except Exception:
                    return None
        try:
            line = _ser.readline().decode(errors='replace').strip()
        except serial.SerialException:
            try:
                _reopen()
            except Exception:
                return None
            continue
        if not line:
            continue
        if len(raw_lines) < 20:
            raw_lines.append(line)
        p = line.split()
        if p and p[0] == 'T3' and len(p) >= 8:
            try:
                for i in range(3):
                    mags[i].append(float(p[5 + i]))
                    phases[i].append(float(p[2 + i]))
            except (ValueError, IndexError):
                pass
    n = len(mags[0])
    if n == 0:
        return {'raw_sample': raw_lines}
    return {
        'mag': [round(sum(m) / n, 6) for m in mags],
        'phase_deg': [round(sum(p) / n, 2) for p in phases],
        'n': n,
    }


def _read_phase_clean(dwell=4.0, pairs=((0, 1), (1, 2), (2, 0)), synced=False):
    """Clean per-leg REALIZED phase (A-5 compute-layer read). Hold each pair,
    collect raw T3, and CIRCULAR-average each leg's lock-in phase over ONLY the
    samples where it was in the ACTIVE pair with real magnitude -- never the
    unselected channel's stale 0 (which the linear /coil/read averages in, and
    which also breaks across the 0/360 wrap). The phase is the Teensy's OWN
    lock-in reference (its clock, independent of the pi5 host clock BY DESIGN),
    so this read travels with the board.

    synced=True: after writing `C a b`, WAIT for the firmware's own `R PAIR a b`
    ack before collecting, so the dwell window belongs to the requested pair, not
    the previous one. The firmware consumes one command per lock-in pass (~3.75 s
    at 16 Hz); a 0.05 s sleep is far shorter than that, so the unsynced path
    collects stale-pair samples and starves the pair whose switch has not landed
    (leg 0 comes back null). Costs one extra pass per pair; gives all 3 legs."""
    acc = [{'c': 0.0, 's': 0.0, 'n': 0, 'mag': 0.0} for _ in range(3)]
    _drain()
    for (a, b) in pairs:
        try:
            _ser.write(f'C {a} {b}\n'.encode())
            if synced:
                _wait_ack('R PAIR',
                          lambda p: len(p) >= 4 and p[2] == str(a) and p[3] == str(b),
                          dwell + 6.0)
            else:
                time.sleep(0.05)
        except serial.SerialException:
            try:
                _reopen()
                _ser.write(f'C {a} {b}\n'.encode())
            except Exception:
                return None
        # Synced: the ack means the firmware is NOW on this pair, but the next
        # T3 is up to one lock-in pass (~3.75 s at 16 Hz) away -- a fixed dwell
        # window can close before it arrives. So in synced mode collect until
        # BOTH active legs have >= MIN_SAMPLES real-mag samples, capped by a
        # generous timeout. Unsynced keeps the original wall-clock window.
        MIN_SAMPLES = 2
        t0 = time.time()
        cap = (dwell + 10.0) if synced else dwell
        while True:
            if synced:
                if acc[a]['n'] >= MIN_SAMPLES and acc[b]['n'] >= MIN_SAMPLES:
                    break
                if time.time() - t0 >= cap:
                    break
            else:
                if time.time() - t0 >= dwell:
                    break
            try:
                line = _ser.readline().decode(errors='replace').strip()
            except serial.SerialException:
                try:
                    _reopen()
                except Exception:
                    return None
                continue
            if not line:
                continue
            p = line.split()
            if p and p[0] == 'T3' and len(p) >= 8:
                for leg in (a, b):
                    try:
                        mg = float(p[5 + leg])
                        ph = float(p[2 + leg])
                    except (ValueError, IndexError):
                        continue
                    if mg <= 0.0:          # unselected / stale guard
                        continue
                    rad = math.radians(ph)
                    acc[leg]['c'] += math.cos(rad)
                    acc[leg]['s'] += math.sin(rad)
                    acc[leg]['n'] += 1
                    acc[leg]['mag'] += mg
    out = []
    for leg in range(3):
        n = acc[leg]['n']
        if n == 0:
            out.append({'leg': leg, 'phase_deg': None, 'circ_sem_deg': None, 'n': 0, 'mag': None})
            continue
        cbar = acc[leg]['c'] / n
        sbar = acc[leg]['s'] / n
        R = math.hypot(cbar, sbar)                     # resultant length (0..1)
        mean = math.degrees(math.atan2(sbar, cbar)) % 360.0
        circ_std = math.degrees(math.sqrt(-2.0 * math.log(R))) if 1e-9 < R < 1.0 else 0.0
        out.append({'leg': leg, 'phase_deg': round(mean, 3),
                    'circ_sem_deg': round(circ_std / math.sqrt(n), 4),
                    'R': round(R, 5), 'n': n, 'mag': round(acc[leg]['mag'] / n, 6)})
    return out


@app.route('/api/v1/coil/start_drive', methods=['POST'])
def start_drive():
    """Start the physical two-tone counter-torque (base+overlay XOR). Without
    this, T3 magnitude reads nothing — O-offsets alone never turn the drive
    loop on. This is what /api/v1/coil/read needs to return real data."""
    global _offsets_deg, _offsets_commanded_deg, _cumulative_rotation_deg
    data = request.get_json(force=True) if request.data else {}
    base = data.get('base_freq', 16)
    overlay = data.get('overlay_freq', 20)
    mix = data.get('mix', 1)
    td = data.get('td', 100)
    with _lock:
        log = _start_two_tone_drive(base, overlay, mix, td)
        # the sequence explicitly sets all three legs to 0 (symmetric;
        # firmware M3 mode provides the 3-phase stagger internally)
        for i, v in enumerate([0.0, 0.0, 0.0]):
            _cumulative_rotation_deg[i] += (v - _offsets_commanded_deg[i])
        _offsets_commanded_deg = [0.0, 0.0, 0.0]
        _offsets_deg = [0.0, 0.0, 0.0]
    return jsonify({
        'node': 'coil', 'started': True,
        'base_freq': base, 'overlay_freq': overlay, 'mix': mix, 'td': td,
        'acks': log, 'offsets_deg': list(_offsets_deg),
    })


@app.route('/api/v1/coil/stop_drive', methods=['POST'])
def stop_drive():
    """Stop the two-tone loop cleanly with the firmware's own stop command.
    NEVER stop this by killing the process/port instead — force-killing
    mid-loop without sending 'x' corrupts the firmware's serial/acquisition
    state (documented cost from an earlier session)."""
    with _lock:
        ack = _send_cmd('\nx', 0.4)
    return jsonify({'node': 'coil', 'stopped': True, 'ack': ack})


@app.route('/api/v1/health')
def health():
    return jsonify({
        'status': 'ok',
        'node': 'coil',
        'r': 0.0,
        'C_mag': 1.0,  # (1+2*0)*e^0 = 1
        'locked': None,  # not applicable — no kernel, no CV
        'uptime_s': round(time.time() - _start, 1),
    })


@app.route('/api/v1/coil/read')
def coil_read():
    """Physical magnitude snapshot — is the copper coil below B_res (gate 0.05)?"""
    duration = float(request.args.get('duration', 2.0))
    with _lock:
        d = _read_magnitudes(duration=duration)
    if d is None:
        return jsonify({'error': 'serial connection lost on COM8'}), 503
    if 'raw_sample' in d:
        return jsonify({'error': 'no T3 lines received on COM8',
                        'raw_sample': d['raw_sample'],
                        'hint': 'drive loop may not be running — check L command ack'}), 503
    gate = 0.05
    below = [m < gate for m in d['mag']]
    return jsonify({
        'node': 'coil', 'mag': d['mag'], 'phase_deg': d['phase_deg'],
        'n': d['n'], 'gate': gate, 'below_floor': below, 'all_under': all(below),
    })


@app.route('/api/v1/coil/read_phase')
def coil_read_phase():
    """Clean REALIZED per-leg phase -- the A-5 compute-layer read. Circular mean
    of the Teensy lock-in phase over active-pair samples only, mapped to the
    pi/8 rung (22.5 deg/rung) + residual, with the realized loop winding
    Sigma-psi = sum of realized phases mod 360. MEASURED (not the commanded
    echo). Clock is the Teensy's, independent of the pi5 host by design."""
    dwell = float(request.args.get('dwell', 4.0))
    synced = request.args.get('synced', '0') in ('1', 'true', 'yes')
    with _lock:
        legs = _read_phase_clean(dwell=dwell, synced=synced)
    if legs is None:
        return jsonify({'error': 'serial connection lost'}), 503
    RUNG = 22.5
    for L in legs:
        if L['phase_deg'] is not None:
            rung = round(L['phase_deg'] / RUNG) % 16
            L['rung'] = rung
            L['residual_deg'] = round(L['phase_deg'] - rung * RUNG, 3)
            L['phase_pi8'] = round(L['phase_deg'] / RUNG, 4)
    phs = [L['phase_deg'] for L in legs if L['phase_deg'] is not None]
    sigma = round(sum(phs) % 360.0, 3) if phs else None
    return jsonify({
        'node': 'coil',
        'clock': 'teensy (independent of pi5 host clock, by design)',
        'measured': True,
        'read': 'realized lock-in phase, circular-averaged per active-pair leg',
        'legs': legs,
        'realized_sigma_psi_deg': sigma,
        'realized_sigma_psi_rung': (round(sigma / RUNG) % 16) if sigma is not None else None,
        'commanded_offsets_deg': list(_offsets_commanded_deg),
        'commanded_sigma_psi_deg': round(_sigma_psi_deg(), 3),
        'note': 'realized = measured Teensy lock-in; commanded = the echo (what we sent); residual = realized - commanded (below-floor hysteresis).',
    })


@app.route('/api/v1/coil/raw')
def coil_raw():
    """RAW T3 capture, no averaging -- to CHECK what the firmware actually
    streams (are all 3 coils reading? the dAB/dAC/dBC pairwise offsets vs the
    canon 120deg counter-stagger? is per-leg phase rotating?) instead of
    trusting an averaged read. Sweeps the 3 pairs; returns every T3 line
    verbatim + parsed. Phase is the Teensy's own lock-in reference."""
    duration = float(request.args.get('duration', 30.0))
    dwell = float(request.args.get('dwell', 3.0))
    pairs = [(0, 1), (1, 2), (2, 0)]
    lines = []
    with _lock:
        _drain()
        t0 = time.time(); last = 0.0; pi = -1; a, b = 0, 1
        while time.time() - t0 < duration:
            if time.time() - last > dwell:
                pi += 1; a, b = pairs[pi % 3]; last = time.time()
                try:
                    _ser.write(f'C {a} {b}\n'.encode())
                except serial.SerialException:
                    try:
                        _reopen()
                    except Exception:
                        break
            try:
                ln = _ser.readline().decode(errors='replace').strip()
            except serial.SerialException:
                try:
                    _reopen(); continue
                except Exception:
                    break
            if ln.startswith('T3'):
                p = ln.split()
                rec = {'raw': ln, 'pair': [a, b], 't': round(time.time() - t0, 2)}
                if len(p) >= 11:
                    try:
                        rec['ph'] = [float(p[2]), float(p[3]), float(p[4])]
                        rec['mag'] = [float(p[5]), float(p[6]), float(p[7])]
                        rec['d'] = [float(p[8]), float(p[9]), float(p[10])]  # dAB dAC dBC
                    except ValueError:
                        pass
                lines.append(rec)
    return jsonify({'node': 'coil', 'n': len(lines), 'duration': duration,
                    'fields': 'T3 freq phA phB phC magA magB magC dAB dAC dBC',
                    'lines': lines})


@app.route('/api/v1/state')
def state():
    with _lock:
        return jsonify({
            'node': 'coil',
            'r': 0.0,
            'C_mag': 1.0,
            'sigma_psi_deg': round(_sigma_psi_deg(), 2),
            'offsets_deg': list(_offsets_deg),
            'offsets_commanded_deg': list(_offsets_commanded_deg),
            'cumulative_rotation_deg': list(_cumulative_rotation_deg),
            'A0_cv': None, 'A1_cv': None, 'A2_cv': None,  # physical node: no kernel jitter to read
            'locked': None,
            'gate': None,
            'note': 'physical actor (r=0) — sets geometry, does not accumulate CV',
        })


def _apply_commanded(signed_deg):
    """Record the signed value as-sent + cumulative rotation, wrap for the
    Teensy write, and return the wrapped list."""
    global _offsets_deg, _offsets_commanded_deg, _cumulative_rotation_deg
    for i, v in enumerate(signed_deg):
        _cumulative_rotation_deg[i] += (v - _offsets_commanded_deg[i])
    _offsets_commanded_deg = list(signed_deg)
    wrapped = [v % 360.0 for v in signed_deg]
    for leg, deg in enumerate(wrapped):
        _write_leg(leg, deg)
    _offsets_deg = wrapped
    return wrapped


@app.route('/api/v1/geometry', methods=['GET', 'POST'])
def geometry():
    if request.method == 'GET':
        with _lock:
            return jsonify({'offsets_deg': list(_offsets_deg),
                            'offsets_commanded_deg': list(_offsets_commanded_deg),
                            'cumulative_rotation_deg': list(_cumulative_rotation_deg),
                            'sigma_psi_deg': round(_sigma_psi_deg(), 2), 'r': 0.0})
    data = request.get_json(force=True)
    with _lock:
        if 'offsets_deg' in data:
            _apply_commanded([float(x) for x in data['offsets_deg']][:3])
        elif 'sigma_psi_deg' in data:
            per = float(data['sigma_psi_deg']) / 3.0
            base = [0.0, 120.0, 240.0]
            _apply_commanded([b + per for b in base])
        return jsonify({'offsets_deg': list(_offsets_deg),
                        'offsets_commanded_deg': list(_offsets_commanded_deg),
                        'cumulative_rotation_deg': list(_cumulative_rotation_deg),
                        'sigma_psi_deg': round(_sigma_psi_deg(), 2)})


def _wait_ack(prefix, check, timeout):
    """Read until an 'R ...' line starting with prefix passes check(parts).
    Returns (seconds_waited, stale_acks_seen) or (None, stale) on timeout."""
    stale = []
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            line = _ser.readline().decode(errors='replace').strip()
        except serial.SerialException:
            return None, stale
        if not line.startswith('R '):
            continue
        if line.startswith(prefix) and check(line.split()):
            return round(time.time() - t0, 2), stale
        stale.append(line)
    return None, stale


@app.route('/api/v1/coil/push_read', methods=['POST'])
def push_read():
    """Ack-synchronised push -> read. The firmware consumes ONE command per
    lock-in pass (3.75 s at 16 Hz), so a read taken on a host timer can belong
    to an earlier commanded phase. This writes one leg's offset, waits for the
    Teensy's own 'R OFFSET' ack, and only then returns the next T3 lines, raw."""
    global _offsets_deg, _offsets_commanded_deg, _cumulative_rotation_deg
    data = request.get_json(force=True)
    leg = int(data['leg'])
    signed = float(data['deg'])
    wrapped = signed % 360.0
    n = max(1, int(data.get('n', 2)))
    skip = max(0, int(data.get('skip', 0)))
    ack_timeout = float(data.get('ack_timeout', 30.0))
    pair = data.get('pair')
    with _lock:
        out = {'node': 'coil', 'leg': leg, 'deg_sent': wrapped}
        try:
            if pair:
                a, b = int(pair[0]), int(pair[1])
                _drain()
                _ser.write(f'C {a} {b}\n'.encode())
                waited, stale = _wait_ack(
                    'R PAIR', lambda p: len(p) >= 4 and p[2] == str(a) and p[3] == str(b), ack_timeout)
                out['pair'] = [a, b]; out['pair_ack_s'] = waited; out['stale_acks'] = stale
                if waited is None:
                    out['acked'] = False
                    return jsonify(out)
            _drain()
            _ser.write(f'O {leg} {wrapped}\n'.encode())
        except serial.SerialException as e:
            out['acked'] = False; out['error'] = str(e)[:80]
            return jsonify(out)

        def _is_mine(p):
            try:
                return len(p) >= 4 and int(p[2]) == leg and abs(float(p[3]) - wrapped) < 0.01
            except ValueError:
                return False
        waited, stale = _wait_ack('R OFFSET', _is_mine, ack_timeout)
        out['ack_s'] = waited
        out['stale_acks'] = out.get('stale_acks', []) + stale
        if waited is None:
            out['acked'] = False
            return jsonify(out)
        out['acked'] = True
        _cumulative_rotation_deg[leg] += (signed - _offsets_commanded_deg[leg])
        _offsets_commanded_deg[leg] = signed
        _offsets_deg[leg] = wrapped

        lines = []
        t_ack = time.time()
        while len(lines) < skip + n and time.time() - t_ack < (skip + n + 2) * 6.0:
            try:
                line = _ser.readline().decode(errors='replace').strip()
            except serial.SerialException:
                break
            p = line.split()
            if p and p[0] == 'T3' and len(p) >= 8:
                try:
                    lines.append({'t_after_ack_s': round(time.time() - t_ack, 2),
                                  'phase_deg': [float(x) for x in p[2:5]],
                                  'mag': [float(x) for x in p[5:8]]})
                except ValueError:
                    pass
            elif line.startswith('R '):
                out['stale_acks'].append(line)
        out['t3'] = lines[skip:]
        out['skipped'] = lines[:skip]
        out['offsets_deg'] = list(_offsets_deg)
        return jsonify(out)


@app.route('/api/v1/run', methods=['POST'])
def run_transfer():
    """The coil is set-and-forget: 'running' means holding the current
    geometry for the requested duration so other lattice nodes can read
    a stable perturbation during that window. No new writes needed."""
    data = request.get_json(force=True)
    seconds = min(data.get('seconds', 5), 300)
    time.sleep(seconds)
    with _lock:
        return jsonify({
            'node': 'coil', 'r': 0.0,
            'sigma_psi_deg': round(_sigma_psi_deg(), 2),
            'offsets_deg': list(_offsets_deg),
            'held_s': seconds,
        })


@app.route('/api/v1/predict')
def predict():
    # coil is always r=0; trivial C(0)=1, kept for interface parity
    dphi = float(request.args.get('dphi_deg', 0.0))
    r_b = float(request.args.get('r_b', 2.0))
    Cb = (1 + 2*r_b) * math.exp(-r_b/3.0)
    c = 1.0 * Cb * math.cos(math.radians(dphi))
    return jsonify({'r_a': 0.0, 'r_b': r_b, 'dphi_deg': dphi,
                    'C_a': 1.0, 'C_b': round(Cb, 4), 'coupling': round(c, 4)})


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8093)
    ap.add_argument('--com', type=str, default='COM8')
    ap.add_argument('--baud', type=int, default=115200)
    a = ap.parse_args()
    _com, _baud = a.com, a.baud
    _ser = serial.Serial(_com, _baud, timeout=1, write_timeout=2)
    time.sleep(0.5)
    _ser.reset_input_buffer()
    # hold at the frustrated triangle (the eigenstate) on start
    for leg, deg in enumerate(_offsets_deg):
        _write_leg(leg, deg)
    print(f'EGT Coil API  :{a.port}  {a.com}  offsets={_offsets_deg}  r=0')
    app.run(host='0.0.0.0', port=a.port, threaded=True)
