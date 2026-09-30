#!/usr/bin/env python3
"""cr_node_register.py — self-register a compute node into the EGT API backend.

Run this on a node (e.g. Brian's phone under Termux) ALONGSIDE cr_compute_api :8091.
It writes a short-TTL redis key the lattice API's dynamic backend reads:

    cadence:tworocks:node-url:<hwid> = {"node","hwid","url","r","ts"}   (EX ~90s)

and refreshes it on an interval. Effect: the API discovers + routes to this node within
its 30s backend cache; if this helper stops (phone off/asleep), the key TTL-expires and
the API drops the node automatically. Before each write it health-checks the node's own
:8091 so it never advertises a dead endpoint.

    python cr_node_register.py                    # phone defaults: r=3, url auto (tailscale)
    python cr_node_register.py --url http://100.x.y.z:8091 --r 3 --node phone
    python cr_node_register.py --once             # register one time and exit
"""
import argparse, hashlib, json, socket, subprocess, time
import urllib.request
import redis

REDIS_HOST = '100.86.79.99'
REDIS_PORT = 6379
REDIS_PW   = 'Xa5KML-5Ze4GB-79ahx5'
TTL = 90


def default_hwid():
    return 'phone-' + hashlib.sha1(socket.gethostname().encode()).hexdigest()[:12]


def tailnet_ip():
    for cmd in (['tailscale', 'ip', '-4'],
                ['/data/data/com.termux/files/usr/bin/tailscale', 'ip', '-4']):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            lines = [x.strip() for x in (out.stdout or '').splitlines() if x.strip()]
            if lines:
                return lines[0]
        except Exception:
            pass
    try:  # fallback: the local IP used to reach the mesh
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((REDIS_HOST, REDIS_PORT))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def healthy(url):
    try:
        with urllib.request.urlopen(url + '/api/v1/health', timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--r', type=float, default=3.0, help='lattice position r (phone default 3)')
    ap.add_argument('--url', default=None, help='http://host:port of this node (default: tailscale ip + --port)')
    ap.add_argument('--node', default='phone', help='friendly node name')
    ap.add_argument('--port', type=int, default=8091)
    ap.add_argument('--hwid', default=None, help='override hwid (default phone-<sha1(hostname)[:12]>)')
    ap.add_argument('--interval', type=int, default=30)
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--no-verify', action='store_true', help='register even if local :8091 health fails')
    a = ap.parse_args()

    hwid = a.hwid or default_hwid()
    url = a.url
    if not url:
        ip = tailnet_ip()
        if not ip:
            raise SystemExit('could not determine URL — pass --url http://<ip>:%d' % a.port)
        url = f'http://{ip}:{a.port}'
    key = f'cadence:tworocks:node-url:{hwid}'
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PW,
                    decode_responses=True, socket_timeout=10)
    print(f'self-register: node={a.node} hwid={hwid} r={a.r} url={url} -> {key} (TTL {TTL}s, every {a.interval}s)', flush=True)
    while True:
        try:
            if a.no_verify or healthy(url):
                r.set(key, json.dumps({'node': a.node, 'hwid': hwid, 'url': url, 'r': a.r,
                                       'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}), ex=TTL)
                print(f'  registered {time.strftime("%H:%M:%S")}', flush=True)
            else:
                print(f'  {url} not healthy — skipped register (will TTL-expire if this persists)', flush=True)
        except Exception as e:
            print('  register failed:', str(e)[:120], flush=True)
        if a.once:
            break
        time.sleep(a.interval)


if __name__ == '__main__':
    main()
