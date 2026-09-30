#!/usr/bin/env python3
"""cr_api_full_acceptance.py — full acceptance test of the whole EGT lattice API.

Exercises every category from the audit and reports PASS/FAIL per check:
  [1] discovery / structure     [2] F access (signup/auth/rate-limit)
  [3] C answer integrity        [4] A/B canonical registry + node_status
  [5] D isolation               [6] phi-in=phi-out contract (multi-body + duplicate-r)
  [7] input validation          [8] G supervision / health

Read-only against the API except it creates inert test signup accounts + one
low-limit key (for the rate-limit check). Run from cr_mesh/.
    python cr_api_full_acceptance.py
"""
import requests, concurrent.futures as cf, sys
import cr_api_auth as auth

LOOP = 'http://127.0.0.1:8092'
NET  = 'http://100.121.177.94:8092'   # dragonseye tailnet IP = non-loopback (the gate applies)

results = []
def check(name, ok, detail=''):
    results.append((name, bool(ok)))
    sys.stdout.buffer.write((f'  [{"PASS" if ok else "FAIL"}] {name}' + (f'  -- {detail}' if detail else '') + '\n').encode('utf-8', 'replace'))
    sys.stdout.flush()

def gp(url, body=None, timeout=90, **kw):
    return requests.post(url, json=body, timeout=timeout, **kw)
def gg(url, timeout=8, **kw):
    return requests.get(url, timeout=timeout, **kw)
def near(a, b, tol=0.5):
    try: return abs(((float(a) - float(b) + 180) % 360) - 180) < tol
    except Exception: return False

tiny = {'experiment': {'bodies': {'q0': {'r': 2, 'phi_deg': 90}}, 'seconds': 2}}
print('=== FULL API ACCEPTANCE — egt-lattice ===')

print('\n[1] DISCOVERY / STRUCTURE')
b = gg(f'{LOOP}/api/v1/backend').json()
check('backend name=egt-lattice', b.get('name') == 'egt-lattice')
check('operator present', 'operator' in b)
check('>=3 rocks', isinstance(b.get('rocks'), list) and len(b['rocks']) >= 3, f"{len(b.get('rocks', []))}")
check('registry.r_to_node canonical', b.get('registry', {}).get('r_to_node') == {'1.0': 'dragonseye', '2.0': 'pi5', '3.0': 'oracle'}, str(b.get('registry', {}).get('r_to_node')))
check('registry r_source = canonical r-map', 'r-map' in b.get('registry', {}).get('r_source', ''))
check('answer_policy names provenance', 'provenance' in b.get('answer_policy', ''))
check('access hint present', 'signup' in b.get('access', ''))
check('nodes endpoint', isinstance(gg(f'{LOOP}/api/v1/lattice/nodes').json(), dict))
check('backends alias 200', gg(f'{LOOP}/api/v1/backends').status_code == 200)

print('\n[2] ACCESS LAYER (F)')
su = gp(f'{LOOP}/api/v1/signup', {'name': 'full-acceptance'}, timeout=10)
key = su.json().get('api_key', '')
check('signup -> 201 + egt_ key', su.status_code == 201 and key.startswith('egt_'), f'status {su.status_code}')
check('signup no name -> 400', gp(f'{LOOP}/api/v1/signup', {}, timeout=10).status_code == 400)
check('protected no key (tailnet) -> 401', gp(f'{NET}/api/v1/experiment', tiny).status_code == 401)
check('protected bad key (tailnet) -> 401', gp(f'{NET}/api/v1/experiment', tiny, headers={'X-API-Key': 'egt_bogus'}).status_code == 401)
check('protected good key (tailnet) -> 200', gp(f'{NET}/api/v1/experiment', tiny, headers={'X-API-Key': key}).status_code == 200)
check('loopback bypass no key -> 200', gp(f'{LOOP}/api/v1/experiment', tiny).status_code == 200)
u = gg(f'{NET}/api/v1/account/usage', headers={'X-API-Key': key})
check('usage endpoint', u.status_code == 200 and 'per_min' in u.json())
lk = auth.create_account('ratelimit-test', per_min=2, per_day=100)['api_key']
onec = {'experiment': {'bodies': {'q0': {'r': 2, 'phi_deg': 10}}, 'seconds': 1}}
codes = [gp(f'{NET}/api/v1/experiment', onec, headers={'X-API-Key': lk}).status_code for _ in range(3)]
check('rate limit (per_min=2): a 429 appears', codes.count(429) >= 1, f'codes {codes}')

print('\n[3] ANSWER INTEGRITY (C)')
r = gp(f'{LOOP}/api/v1/experiment', {'experiment': {'bodies': {'q0': {'r': 2, 'phi_deg': 137}}, 'seconds': 2}}).json()
q = r['result']['rocks']['q0']
check('conserved_sigma_psi_deg == phi (compat)', near(q.get('conserved_sigma_psi_deg'), 137))
check('conserved_sigma_psi_measured == False', q.get('conserved_sigma_psi_measured') is False)
check('provenance.computed_from_input lists sigma', 'conserved_sigma_psi_deg' in q.get('provenance', {}).get('computed_from_input', []))
check('provenance.measured_from_run non-empty', len(q.get('provenance', {}).get('measured_from_run', [])) >= 10)
check('result.the_answer present', bool(r['result'].get('the_answer')))

print('\n[4] REGISTRY + FANOUT (A/B)')
check('rock has node_status', q.get('node_status') in ('ok', 'unavailable'))
check('node_status ok (nodes up)', q.get('node_status') == 'ok')

print('\n[5] ISOLATION (D) — 4 concurrent same-node, distinct phi')
def fire(phi):
    rr = gp(f'{LOOP}/api/v1/experiment', {'experiment': {'bodies': {'q0': {'r': 2, 'phi_deg': phi}}, 'seconds': 2}}).json()
    return (phi, rr['result']['rocks']['q0'].get('conserved_sigma_psi_deg'))
with cf.ThreadPoolExecutor(max_workers=4) as ex:
    iso = list(ex.map(fire, [33, 111, 222, 333]))
check('4 concurrent same-node each own phi', all(near(g, p) for p, g in iso), str(iso))

print('\n[6] CONTRACT — multi-body + duplicate-r (fanout fix)')
mb = gp(f'{LOOP}/api/v1/experiment', {'experiment': {'bodies': {'q0': {'r': 3, 'phi_deg': 50}, 'q1': {'r': 3, 'phi_deg': 250}, 'q2': {'r': 1, 'phi_deg': 100}}, 'seconds': 2}}).json()
rk = mb['result']['rocks']
check('duplicate-r: all 3 bodies served', all(x in rk for x in ('q0', 'q1', 'q2')), f'got {list(rk.keys())}')
check('duplicate-r q0=50 & q1=250 each own', near(rk.get('q0', {}).get('conserved_sigma_psi_deg'), 50) and near(rk.get('q1', {}).get('conserved_sigma_psi_deg'), 250))

print('\n[7] INPUT VALIDATION')
check('empty bodies -> 400', gp(f'{LOOP}/api/v1/experiment', {'experiment': {'bodies': {}}}, timeout=10).status_code == 400)
inv = gp(f'{LOOP}/api/v1/experiment', {'experiment': {'bodies': {'q0': {'r': 9, 'phi_deg': 0}}, 'seconds': 2}}, timeout=10)
check('invalid r=9 -> 400', inv.status_code == 400)
check('/lattice/solve alias -> 200', gp(f'{LOOP}/api/v1/lattice/solve', tiny).status_code == 200)

print('\n[8] SUPERVISION / HEALTH (G)')
for nm, url in [('memory_serve', 'http://127.0.0.1:8090/health'),
                ('compute-dragonseye', 'http://127.0.0.1:8091/api/v1/health'),
                ('lattice', 'http://127.0.0.1:8092/api/v1/backend')]:
    try: check(f'{nm} up', gg(url, timeout=5).status_code == 200)
    except Exception as e: check(f'{nm} up', False, str(e)[:40])
for nm, ip in [('dragonseye', '100.121.177.94'), ('pi5', '100.81.123.41'), ('oracle', '100.114.92.17')]:
    try: check(f'rock {nm} up', gg(f'http://{ip}:8091/api/v1/health', timeout=5).status_code == 200)
    except Exception as e: check(f'rock {nm} up', False, str(e)[:40])

passed = sum(1 for _, ok in results if ok)
tot = len(results)
print(f'\n=== SUMMARY: {passed}/{tot} checks passed ===')
if passed < tot:
    print('FAILURES:')
    for nm, ok in results:
        if not ok: print(f'  - {nm}')
