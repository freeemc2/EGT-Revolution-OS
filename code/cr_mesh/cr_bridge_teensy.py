#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Teensy Bridge — makes a bare-metal Teensy 4.1 a first-class mesh worker.

The Teensy can't run redis, so Dragonseye bridges it: this process registers a
heartbeat as a worker, pulls jobs from the Teensy's redis queue, ships the data
to the Teensy over USB serial, the Teensy computes the tree-hash kernel in
deterministic bare-metal C, and the result is voted back into the mesh.

Each Teensy's USB serial number is its hwid (teensy41-<serial>) so the mesh
counts each board distinctly. Reports the Teensy's own microsecond timing.

Usage:  python cr_bridge_teensy.py --port COM8 [--node teensy-a]
"""
import json, os, sys, time, threading
import serial, serial.tools.list_ports as lp
import redis

REDIS_HOST = os.environ.get("CR_REDIS_HOST", "100.86.79.99")
REDIS_PORT = int(os.environ.get("CR_REDIS_PORT", "6379"))
REDIS_PW   = os.environ.get("CR_REDIS_PW", "Xa5KML-5Ze4GB-79ahx5")
HB_TTL = 30

def rconn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                       decode_responses=True, socket_connect_timeout=8, socket_timeout=40,
                       health_check_interval=15)

def teensy_serial(port):
    for p in lp.comports():
        if p.device == port and p.vid == 0x16C0:
            return str(p.serial_number)
    return None

def heartbeat_loop(hwid, node, host):
    r = rconn()
    info = json.dumps({"node": node, "host": host, "machine": "cortex-m7",
                       "system": "teensy4.1-baremetal", "hwid": hwid})
    while True:
        try: r.set(f"cadence:tworocks:hb:{hwid}", info, ex=HB_TTL)
        except Exception:
            try: r = rconn()
            except Exception: pass
        time.sleep(HB_TTL // 3)

def ask_teensy(ser, data, rounds):
    """Send job to Teensy, return (value, micros)."""
    line = "C %d %d %s\n" % (rounds, len(data), " ".join(str(int(v) & 0xFFFFFFFF) for v in data))
    ser.reset_input_buffer()
    ser.write(line.encode("ascii")); ser.flush()
    resp = ser.readline().decode(errors="replace").strip()
    # expect: "R <value> <micros>"
    parts = resp.split()
    if len(parts) >= 3 and parts[0] == "R":
        return int(parts[1]) & 0xFFFFFFFF, int(parts[2])
    raise RuntimeError(f"bad teensy response: {resp!r}")

def main():
    port = sys.argv[sys.argv.index("--port")+1]
    sn = teensy_serial(port) or port.replace("COM", "com")
    hwid = f"teensy41-{sn}"
    node = sys.argv[sys.argv.index("--node")+1] if "--node" in sys.argv else f"teensy-{sn}"
    host = os.environ.get("COMPUTERNAME", "DragonsEye") + f"/{port}"

    ser = serial.Serial(port, 115200, timeout=6, write_timeout=6)
    time.sleep(0.3); ser.reset_input_buffer()
    ser.write(b"P\n"); ser.flush(); time.sleep(0.2)
    print(f"bridge: {node} hwid={hwid} on {port} -> {ser.readline().decode(errors='replace').strip()}",
          flush=True)

    r = rconn(); r.ping()
    threading.Thread(target=heartbeat_loop, args=(hwid, node, host), daemon=True).start()
    myq = f"cadence:tworocks:q:{hwid}"
    done = 0
    while True:
        try:
            item = r.brpop(myq, timeout=20)
            if not item:
                continue
            task = json.loads(item[1])
            value, us = ask_teensy(ser, task.get("data", []),
                                   int(task.get("problem", {}).get("rounds", 16)))
            res = json.dumps({"node": node, "hwid": hwid, "host": host,
                              "value": value, "ms": round(us / 1000.0, 3)})
            rk = f"cadence:tworocks:results:{task['task_id']}"
            r.lpush(rk, res); r.expire(rk, 120)
            done += 1
            print(f"  [{node}] task {task['task_id']} -> {value} ({us}us on-chip, {done} done)", flush=True)
        except redis.exceptions.RedisError as e:
            print(f"  [{node}] redis error: {e}; reconnect 3s", flush=True); time.sleep(3)
            try: r = rconn(); r.ping()
            except Exception: pass
        except Exception as e:
            print(f"  [{node}] error: {type(e).__name__}: {e}", flush=True); time.sleep(1)

if __name__ == "__main__":
    main()
