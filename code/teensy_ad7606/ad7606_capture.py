#!/usr/bin/env python3
"""
ad7606_capture.py — host capture tool for the teensy_ad7606 streamer. v1 (2026-10-11, tonic)

Writes the house raw-capture convention so captures are md5-able, epoch-alignable
and archive-ready:
  <out>.jsonl   one line per conversion, verbatim from the firmware plus "wall_us"
  <out>.json    sidecar: node, wall_origin_ns, perf_origin_ns, firmware header,
                port, fields, schedule marks (if any)

The capture tool DRIVES NOTHING. --schedule marks push/rest windows in the log
by timestamp only (the experiment layer annotates; commanding any drive is a
separate tool, run on Brian's word). Analysis (lock-in, realized phase on the
pi/8 ladder, anchor pair) lives in a separate file, never here and never in
firmware.

Usage:
  python ad7606_capture.py --port COM11 --rate 1000 --seconds 60 --node DE --out ad7606_noise_floor
  python ad7606_capture.py --port COM11 --rate 1000 --seconds 300 --node DE \
      --schedule push:4,read:8,rest:4 --out ad7606_pushrest   # marks windows only
"""
import argparse, json, time, socket, sys

try:
    import serial
except ImportError:
    sys.exit("pip install pyserial")


def parse_schedule(spec):
    """'push:4,read:8,rest:4' -> [('push',4.0),('read',8.0),('rest',4.0)] cycled."""
    out = []
    for part in spec.split(','):
        name, _, secs = part.partition(':')
        out.append((name.strip(), float(secs)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', required=True)
    ap.add_argument('--rate', type=int, default=1000)
    ap.add_argument('--seconds', type=float, default=60.0)
    ap.add_argument('--node', default=socket.gethostname())
    ap.add_argument('--out', default=None)
    ap.add_argument('--range-label', choices=['5', '10'], default='5',
                    help='what RANGE is wired to (label only; data stays raw counts)')
    ap.add_argument('--schedule', default=None,
                    help='optional window marks, e.g. push:4,read:8,rest:4 — annotates, never drives')
    a = ap.parse_args()

    stamp = time.strftime('%Y%m%d_%H%M%S')
    out = a.out or f'ad7606_{a.node}_{stamp}'

    s = serial.Serial(a.port, 115200, timeout=2)
    time.sleep(0.5)
    s.reset_input_buffer()

    def cmd(c):
        s.write((c + '\n').encode())
        time.sleep(0.1)

    cmd('P')
    ident = s.readline().decode(errors='replace').strip()
    if 'ad7606' not in ident:
        sys.exit(f'wrong firmware on {a.port}: {ident!r}')
    cmd(f'V {a.range_label}')
    cmd(f'S {a.rate}')
    hdr = None
    t_end = time.time() + 2
    while time.time() < t_end:
        line = s.readline().decode(errors='replace').strip()
        if line.startswith('{"hdr"'):
            hdr = json.loads(line)

    wall_origin_ns = time.time_ns()
    perf_origin_ns = time.perf_counter_ns()
    sched = parse_schedule(a.schedule) if a.schedule else None
    sched_log = []

    jsonl = open(out + '.jsonl', 'w', encoding='utf-8')
    n = 0
    cmd('G')
    t0 = time.perf_counter()
    try:
        # schedule bookkeeping (marks only)
        si, phase_t0 = 0, t0
        while time.perf_counter() - t0 < a.seconds:
            if sched:
                name, dur = sched[si % len(sched)]
                if time.perf_counter() - phase_t0 >= dur:
                    si += 1
                    phase_t0 = time.perf_counter()
                    name, dur = sched[si % len(sched)]
                    sched_log.append({'phase': name, 'wall_us': time.time_ns() // 1000})
                elif not sched_log:
                    sched_log.append({'phase': name, 'wall_us': time.time_ns() // 1000})
            raw = s.readline().decode(errors='replace').strip()
            if not raw or raw.startswith('{"hdr"'):
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            rec['wall_us'] = time.time_ns() // 1000
            if sched:
                rec['phase'] = sched[si % len(sched)][0]
            jsonl.write(json.dumps(rec, separators=(',', ':')) + '\n')
            n += 1
    finally:
        cmd('g')   # stop streaming ONLY - 'x' would kill a running drive (v2)
        jsonl.close()
        side = {
            'node': a.node, 'instrument': 'teensy_ad7606 v1', 'port': a.port,
            'wall_origin_ns': wall_origin_ns, 'perf_origin_ns': perf_origin_ns,
            'wall_origin_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(wall_origin_ns / 1e9)),
            'rate_hz': a.rate, 'range_label': f'+/-{a.range_label}V',
            'lsb_uV': 152.588 if a.range_label == '5' else 305.176,
            'firmware_header': hdr, 'n_records': n,
            'fields': ['t_us (teensy micros)', 'seq', 'ch[8] raw int16 counts', 'wall_us (host)', 'phase (if scheduled)'],
            'schedule': a.schedule, 'schedule_marks': sched_log,
            'note': 'raw counts only; volts and any phase reduction are host-side analysis, separate file',
        }
        with open(out + '.json', 'w', encoding='utf-8') as f:
            json.dump(side, f, indent=1)
        print(f'{n} records -> {out}.jsonl (+ sidecar {out}.json)')


if __name__ == '__main__':
    main()
