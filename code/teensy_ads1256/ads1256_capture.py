#!/usr/bin/env python3
"""
ads1256_capture.py — host capture for the teensy_ads1256 streamer. v1 (2026-10-15, tonic)

Same jsonl + sidecar convention as ad7606_capture.py, so ad7606_realized_phase.py
reads it unchanged (use its --differential flag: the ADS1256 outputs 3 already-
differential coil reads in ch[0..2], not 8 single-ended taps).

  <out>.jsonl   one line per round, verbatim from firmware + "wall_us"
  <out>.json    sidecar: node, wall/perf origins, sps, pga, vref, lsb_nV,
                channel_map (3 differential coils), fields, drive state

Drives nothing. --schedule marks push/rest windows by timestamp only.

Usage:
  python ads1256_capture.py --port COM10 --seconds 60 --pga 64 --dr 1000 --node DE --out ads1256_run
"""
import argparse, json, time, socket, sys
try:
    import serial
except ImportError:
    sys.exit("pip install pyserial")

CHANNEL_MAP = {"ch0": "coil0 AIN0-AIN1 differential",
               "ch1": "coil1 AIN2-AIN3 differential",
               "ch2": "coil2 AIN4-AIN5 differential"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--pga", type=int, default=64, choices=[1, 2, 4, 8, 16, 32, 64])
    ap.add_argument("--dr", type=int, default=1000, help="ADS1256 data rate (SPS)")
    ap.add_argument("--node", default=socket.gethostname())
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    out = a.out or f"ads1256_{a.node}_{time.strftime('%Y%m%d_%H%M%S')}"
    s = serial.Serial(a.port, 115200, timeout=2)
    time.sleep(0.6); s.reset_input_buffer()

    def cmd(c, w=0.3):
        s.write((c + "\n").encode()); time.sleep(w)
        return s.read(800).decode(errors="replace").strip()

    ident = cmd("P")
    if "ads1256" not in ident:
        sys.exit(f"wrong firmware on {a.port}: {ident!r}")
    cmd(f"PGA {a.pga}", 0.6)
    cmd(f"DR {a.dr}", 0.6)
    cmd("Z", 1.0)                      # self-cal before the run
    hdr = None
    for _ in range(5):
        line = s.readline().decode(errors="replace").strip()
        if line.startswith('{"hdr"'):
            hdr = json.loads(line)

    wall_origin_ns = time.time_ns()
    perf_origin_ns = time.perf_counter_ns()
    jsonl = open(out + ".jsonl", "w", encoding="utf-8")
    n = 0
    s.reset_input_buffer(); s.write(b"G\n")
    t0 = time.perf_counter()
    try:
        while time.perf_counter() - t0 < a.seconds:
            raw = s.readline().decode(errors="replace").strip()
            if not raw or raw.startswith('{"hdr"'):
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "ch" not in rec:
                continue
            rec["wall_us"] = time.time_ns() // 1000
            jsonl.write(json.dumps(rec, separators=(",", ":")) + "\n")
            n += 1
    finally:
        cmd("g")                        # stop streaming only — never kills the drive
        jsonl.close()
        lsb_nV = hdr.get("lsb_nV") if hdr else (2 * 2.5 / a.pga) / 2**24 * 1e9
        side = {
            "node": a.node, "instrument": "teensy_ads1256 v1", "port": a.port,
            "wall_origin_ns": wall_origin_ns, "perf_origin_ns": perf_origin_ns,
            "wall_origin_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(wall_origin_ns / 1e9)),
            "pga": a.pga, "data_rate_sps": a.dr, "vref": 2.5, "lsb_nV": lsb_nV,
            "firmware_header": hdr, "n_records": n,
            "channel_map": CHANNEL_MAP,
            "fields": ["t_us (teensy micros)", "seq", "ch[3] = 3 coils' raw signed 24-bit differential counts", "wall_us"],
            "note": "raw 24-bit differential counts; ch0/1/2 are coil0/1/2 already-differential. "
                    "Read realized phase with ad7606_realized_phase.py --differential --coils 0:1:2. "
                    "MUX is sequential (not simultaneous) — a fixed per-channel phase skew applies, "
                    "cancels in anchor-relative occupancy. volts = count * lsb_nV * 1e-9.",
        }
        with open(out + ".json", "w", encoding="utf-8") as f:
            json.dump(side, f, indent=1)
        print(f"{n} rounds -> {out}.jsonl (+ sidecar {out}.json)")


if __name__ == "__main__":
    main()
