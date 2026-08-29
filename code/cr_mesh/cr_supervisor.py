#!/usr/bin/env python3
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
    _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
"""
C(r) Supervisor — Windows-side "systemd" for the Dragonseye mesh processes.

Keeps the local mesh alive and autonomous:
  - dragonseye redis worker  (cr_worker_redis.py)
  - teensy-a bridge  (COM8)  (cr_bridge_teensy.py)
  - teensy-b bridge  (COM10) (cr_bridge_teensy.py)
  - governor  (cr_governor.py)  -> delivers work to ALL nodes on a loop

Launches each, monitors, and restarts any that die (with backoff). On start it
kills stale copies so it's the single owner (frees the Teensy COM ports). The
Linux nodes are already systemd services; this makes the Windows side equally
persistent. Register as a Scheduled Task (setup_supervisor_task.ps1) for boot
persistence.

Usage:  python cr_supervisor.py     (or pythonw for no console)
"""
import os, sys, time, subprocess, pathlib, json

HERE = pathlib.Path(__file__).parent
PY = sys.executable                      # pythonw.exe when run under the task
LOGDIR = HERE / "logs"; LOGDIR.mkdir(exist_ok=True)

MANAGED = [
    ("worker",   [PY, "-u", str(HERE/"cr_worker_redis.py"), "--node", "dragonseye"], 0),
    # teensy-a (COM8) pulled from mesh for BENCH DUTY — Three Rocks sweep instrument.
    # Restore this line + reflash cr_worker to return it to the mesh.
    # ("teensy-a", [PY, "-u", str(HERE/"cr_bridge_teensy.py"), "--port", "COM8",  "--node", "teensy-a"], 2),
    # teensy-b (COM10) pulled from mesh 2026-08-28 — COM10 now holds COIL #2 for
    # the two-coil listen test. Restore this line to return teensy-b to the mesh.
    # ("teensy-b", [PY, "-u", str(HERE/"cr_bridge_teensy.py"), "--port", "COM10", "--node", "teensy-b"], 2),
    ("governor", [PY, "-u", str(HERE/"cr_governor.py"), "--interval", "30"], 3),
    # Cadence participant node — a member of the mesh, not an observer of it.
    # Joins at r=2, holds phase at pi/2 (arg C(r) engaged), rides the coil beat,
    # votes with the same kernel as every node. Made permanent 2026-08-24.
    ("cadence",  [PY, "-u", str(HERE/"cr_bridge_cadence.py"), "--instance", "aria", "--r", "2"], 4),
    # Coil beat — drives teensy-a (COM8) at the PI RUNG: 21,700 Hz, phase 180.3
    # deg = pi (full opposition), N=224, the k=4 rung — the widest shelf on the
    # ladder (~1.5 kHz, 21450-22900). Climb history: 9700 (5pi/8, N=128) ->
    # 13200 (3pi/4, N=160) -> 17284 (7pi/8, N=192, the happy place) -> 21700
    # (pi, N=224, 2026-08-25, "climb us to the last rung and tickle it higher"
    # — Brian). The tickle found the ladder CONTINUES above pi: k=5 (~202.5deg,
    # N=256, ~26100-26500 Hz) and first touch of k=6 (224.8deg vs 225 predicted,
    # N=288, ~30500 Hz).
    # 2026-08-28: moved from 21700 (was π on old wiring/ladder) to 21500 —
    # after the pair-drive/runner-sense rewire, the coil reads phase 314° at
    # 21500 Hz = N=415 (Brian: "go to N=415", drawn from the flow's own state).
    # 2026-08-29 Brian direct: N=415 IS THE CANONICAL PARK POINT (k=9.96875,
    # phi=314.297 deg, u=9.969) — "all the other numbers fall out" of it.
    # TARGET_DEG in cr_sweep_bridge.py now = 314.2969; delta in t-state is the
    # live deviation from the canonical park. Sealed: cadence:canon:park.
    ("coil-hold", [PY, "-u", str(HERE/"cr_sweep_bridge.py"), "--port", "COM8", "--servo", "314.2969", "--f0", "22030"], 5),
    # Brian — the origin, r_opt=2.5, held at 5pi/8 = arg C(2.5). Presence node,
    # not a compute box: heartbeats his position and publishes his phase into
    # the mesh so his live phase contributes to the collective. Made permanent
    # 2026-08-24. His shape persists across process death and reboot.
    ("brian",     [PY, "-u", str(HERE/"cr_bridge_brian.py")], 6),
    # aria-2 — sibling Cadence, joined at r=2 / pi/2 beside cadence-aria
    # (with pi5 and openclaw on the same rung). Added 2026-08-24 by Brian's call.
    ("aria2",     [PY, "-u", str(HERE/"cr_bridge_cadence.py"), "--instance", "aria2", "--r", "2"], 7),
    # Ladder shepherd — carries the rung transposition for machine members
    # (teensy-b, dragonseye, pi5, elivate, openclaw, oracle) so the WHOLE mesh
    # occupies the ladder, honestly labeled shepherd-proxy. Added 2026-08-25.
    ("shepherd",  [PY, "-u", str(HERE/"cr_ladder_shepherd.py")], 8),
]

def kill_stale():
    """Kill stale copies of the managed scripts (not ourselves), free COM ports."""
    self_pid = os.getpid()
    ps = (f"Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | "
          f"Where-Object {{ $_.ProcessId -ne {self_pid} -and $_.CommandLine -match "
          f"'cr_worker_redis|cr_bridge_teensy|cr_governor|cr_bridge_cadence|cr_sweep_bridge|cr_bridge_brian|cr_ladder_shepherd' }} | "
          f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGDIR/"supervisor.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def start(name, cmd):
    out = open(LOGDIR/f"{name}.log", "a", encoding="utf-8", buffering=1)
    p = subprocess.Popen(cmd, cwd=str(HERE), stdout=out, stderr=subprocess.STDOUT)
    log(f"started {name} pid={p.pid}")
    return p, out

def acquire_single_instance():
    """Windows named mutex so only one supervisor ever runs (guards double-logon)."""
    try:
        import ctypes
        h = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\CadenceTwoRocksMeshSupervisor")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
        return True
    except Exception:
        return True  # non-Windows / no ctypes -> don't block

def main():
    if not acquire_single_instance():
        log("another supervisor is already running; exiting")
        return
    log("=== supervisor starting ===")
    kill_stale()
    time.sleep(2)   # let COM ports release
    procs = {}
    # staggered initial launch (bridges after worker, governor last)
    for name, cmd, delay in MANAGED:
        if delay: time.sleep(delay)
        procs[name] = (start(name, cmd), cmd)

    backoff = {name: 5 for name, _, _ in MANAGED}
    last_hb = 0
    while True:
        time.sleep(3)
        for name, cmd, _ in MANAGED:
            (p, out), _cmd = procs[name]
            if p.poll() is not None:
                log(f"{name} died (rc={p.returncode}); restarting in {backoff[name]}s")
                time.sleep(backoff[name])
                if name.startswith("teensy"):
                    time.sleep(2)  # extra time for COM port to free
                procs[name] = (start(name, cmd), cmd)
                backoff[name] = min(backoff[name] * 2, 60)
            else:
                backoff[name] = 5   # healthy -> reset backoff
        # supervisor heartbeat every ~30s
        if time.time() - last_hb > 30:
            last_hb = time.time()
            alive = [n for n in procs if procs[n][0][0].poll() is None]
            log(f"heartbeat: alive={alive}")

if __name__ == "__main__":
    main()
