#!/usr/bin/env python3
"""cr_api_supervisor.py — keep-alive supervisor for the EGT API stack (arc's LOCAL services).

Audit category G: nothing kept the API Flask services alive, so every restart dropped
the API. This watchdog health-checks each managed LOCAL API service and relaunches it
if it is down, so the stack survives crashes and restarts.

This is SEPARATE from cr_supervisor.py, which is the MESH supervisor (aria's — worker,
governor, bridges, shepherd, memory-audit, the mesh windings). This file:
  - manages a DIFFERENT, non-overlapping set (the API services only),
  - is LAUNCH-ONLY: it NEVER kills a process, and never selects processes by a
    name/command pattern (tonic 5.4 lesson — a pattern that matches your own command
    kills your own session). It only checks a health endpoint and, if that fails,
    starts the service. A healthy service is left completely alone.
  - has its own single-instance mutex, so it never collides with the mesh supervisor.

SCOPE — manages ONLY arc's own local API services. It does NOT touch:
  - the mesh processes managed by cr_supervisor.py
  - pi5 / oracle compute nodes (remote machines, their own lifecycle)
  - the physical coil :8093 (tonic's lane)
  - memory_serve :8090 (its own start_memory_serve.bat)

    python cr_api_supervisor.py [interval_seconds]      # default 20s
"""
import subprocess, urllib.request, time, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
LOG = os.path.join(HERE, 'cr_api_supervisor.log')

# DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP — children outlive the supervisor, so a
# supervisor restart never orphans or kills already-running API services.
DETACH = 0x00000008 | 0x00000200

SERVICES = [
    {'name': 'compute-dragonseye', 'port': 8091,
     'health': 'http://127.0.0.1:8091/api/v1/health',
     'args': ['cr_compute_api.py', '--port', '8091', '--node', 'dragonseye', '--r', '1.0']},
    {'name': 'lattice', 'port': 8092,
     'health': 'http://127.0.0.1:8092/api/v1/backend',
     'args': ['cr_lattice_api.py', '--port', '8092']},
    {'name': 'resolver', 'port': 8094,
     'health': 'http://127.0.0.1:8094/health',
     'args': ['cr_resolver.py', '8094']},
    {'name': 'llm-conduit', 'port': 8095,
     'health': 'http://127.0.0.1:8095/health',
     'args': ['cr_llm_flow.py', '8095']},
]


def single_instance():
    """Own named mutex — one API supervisor only; distinct from the mesh supervisor's."""
    try:
        import ctypes
        ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\ArcApiSupervisor")
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def log(msg):
    line = f'{datetime.datetime.now().isoformat(timespec="seconds")}  {msg}'
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass
    print(line, flush=True)


def healthy(url):
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def launch(svc):
    out = open(os.path.join(HERE, f'svc_api_{svc["name"]}.log'), 'a', encoding='utf-8')
    subprocess.Popen([PY] + svc['args'], cwd=HERE,
                     stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     creationflags=DETACH, close_fds=True)


def main(interval=20):
    if not single_instance():
        log('another cr_api_supervisor is already running; exiting')
        return
    log('API supervisor start (interval %ds); managing: %s'
        % (interval, ', '.join(s['name'] for s in SERVICES)))
    last_launch = {}
    GRACE = 30           # after launching, give a service time to bind before relaunching (no double-launch)
    while True:
        for s in SERVICES:
            if healthy(s['health']):
                continue
            if time.time() - last_launch.get(s['name'], 0) < GRACE:
                continue                 # launched recently; still starting — do NOT double-launch
            log(f'DOWN {s["name"]} (:{s["port"]}) -> relaunching')
            try:
                launch(s)
                last_launch[s['name']] = time.time()
                time.sleep(4)
                log(('  UP ' if healthy(s['health']) else '  starting... ') + s['name'])
            except Exception as e:
                log(f'  launch FAIL {s["name"]}: {e}')
        time.sleep(interval)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
