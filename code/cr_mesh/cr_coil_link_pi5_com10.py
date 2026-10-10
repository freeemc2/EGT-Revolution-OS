#!/usr/bin/env python3
"""COIL<->COIL LINK: drive the pi5 coil, read BOTH coils' magnetometers per phase.

Brian 2026-09-28: "create the link with the coils. add com 10 to your read, drop oracle."
Option 2: tonic HOLDS and STREAMS COM10 (his calibration, his lock). I only READ it.

- pi5 coil (teensy 18904640, r=0, the beat) driven through the 7-phase protocol via lattice :8092.
- pi5 coil's OWN magnitudes read each phase via its coil API :8093  (the driven body).
- COM10 coil (teensy 18809830, tonic's OG coil, passive) read each phase via COM10_URL.
- dragonseye + pi5 CPU timing logged in background (oracle DROPPED).
Descriptive only. Every push = Sigma-psi 45; every rest = 0. Edge: discard first 5s of each phase.
"""
import urllib.request, json, time, threading, struct, os, statistics as st, subprocess, sys

LAT   = 'http://localhost:8092/api/v1/lattice'
PI5_COIL_URL = 'http://100.81.123.41:8093/api/v1/coil/read'
COM10_BASE   = os.environ.get('COM10_BASE', 'http://100.121.177.94:8094')
READ_NODES = ['dragonseye', 'pi5']          # oracle DROPPED
NODE_SSH = {'pi5': 'root@100.81.123.41'}
PHASE_SEC = 30
SETTLE = 5
READ_DUR = 20                                # read window inside each 30s phase, after settle
RECORD_FMT = '<qibb'; RSIZE = struct.calcsize(RECORD_FMT)
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
PHASES = [('baseline',[0,120,240]),('push_A0',[45,120,240]),('rest_A0',[0,120,240]),
          ('push_A1',[0,165,240]),('rest_A1',[0,120,240]),('push_A2',[0,120,285]),('rest_A2',[0,120,240])]
TOTAL_S = len(PHASES)*PHASE_SEC + 20

def post(ep,d):
    r=urllib.request.Request(LAT+ep,data=json.dumps(d).encode(),
        headers={'Content-Type':'application/json'},method='POST')
    return json.load(urllib.request.urlopen(r,timeout=TOTAL_S+60))
def coil_geometry(o): post('/geometry',{'only':['coil'],'per_node':{'coil':{'offsets_deg':o}}})
def read_pi5(dur):
    try:
        return json.load(urllib.request.urlopen(PI5_COIL_URL+('?duration=%d'%dur),timeout=dur+15))
    except Exception as e:
        return {'error':str(e)[:80]}
def com10_one():
    try:
        return json.load(urllib.request.urlopen(COM10_BASE+'/read',timeout=12))
    except Exception as e:
        return {'error':str(e)[:80]}
def com10_window(win_s):
    # poll tonic's /read across the window; average his anchor-currency
    amps=[]; phs=[]; mags=[]; t0=time.time()
    while time.time()-t0 < win_s:
        d=com10_one()
        if d.get('ok') and 'amp_ratio' in d:
            amps.append(d['amp_ratio']); phs.append(d['phase_offset_pi8']); mags.append(d['mag'])
        time.sleep(3.4)
    if not amps: return {'error':'no COM10 reads in window'}
    n=len(amps)
    return {'n':n,'amp_ratio':round(sum(amps)/n,5),'phase_offset_pi8':round(sum(phs)/n,5),
            'mag':round(sum(mags)/n,5),
            'amp_sd':round((sum((a-sum(amps)/n)**2 for a in amps)/n)**0.5,5) if n>1 else 0.0}

print('COIL<->COIL LINK  pi5(driven) <-> COM10(tonic, passive)   read-nodes: %s'%READ_NODES,flush=True)
print('  COM10 endpoint: %s/read (tonic, anchor-currency)'%COM10_BASE,flush=True)

# preflight: is COM10 actually streaming?
pf=com10_one()
if not pf.get('ok') or 'amp_ratio' not in pf:
    print('  [PREFLIGHT] COM10 not streaming yet: %s'%pf,flush=True)
    print('  ABORT: need tonic COM10 stream live before this run. Nothing driven.',flush=True); sys.exit(2)
print('  [PREFLIGHT] COM10 LIVE: driven=%s locked=%s mag=%s anchor=%s amp_ratio=%s'%(pf.get('driven'),pf.get('locked'),pf.get('mag'),pf.get('anchor_mag'),pf.get('amp_ratio')),flush=True)

print('\n[1] warm up read-nodes, coil to frustrated...',flush=True)
coil_geometry([0,120,240]); post('/geometry',{'only':READ_NODES,'all':{'offsets_deg':[0,120,240]}})
for _ in range(3): post('/run',{'only':READ_NODES,'seconds':20})

print('[2] background logged CPU run...',flush=True)
holder={}
def long_run(): holder['r']=post('/run',{'only':READ_NODES,'seconds':TOTAL_S,'log':True})
t=threading.Thread(target=long_run); t.start(); time.sleep(2)

print('[3] driving pi5 coil + reading BOTH coils per phase...',flush=True)
plog=[]
for name,off in PHASES:
    abs_us=int(time.time()*1e6); coil_geometry(off)
    time.sleep(SETTLE)
    import threading as _th
    pv={}
    def _p(): pv['m']=read_pi5(READ_DUR)
    th=_th.Thread(target=_p); th.start()          # pi5 driven-coil windowed read in parallel
    com10=com10_window(READ_DUR)                    # COM10 polled across the same window
    th.join()
    pi5m=pv.get('m',{})
    plog.append({'phase':name,'abs_us':abs_us,'pi5_coil':pi5m,'com10':com10})
    print('  %-9s pi5 mag=%s | COM10 amp_ratio=%s phase_pi8=%s (n=%s)'%(name,pi5m.get('mag'),com10.get('amp_ratio'),com10.get('phase_offset_pi8'),com10.get('n')),flush=True)
    slept=SETTLE+READ_DUR
    if slept<PHASE_SEC: time.sleep(PHASE_SEC-slept)
pend=int(time.time()*1e6)
t.join()
print('[4] CPU n_fire: %s'%{n:holder['r'][n].get('n_fire') for n in READ_NODES},flush=True)

# CPU binning (dragonseye,pi5)
def load(p,ons):
    o=ons//1000; recs=[]
    with open(p,'rb') as f:
        while True:
            c=f.read(RSIZE)
            if len(c)<RSIZE: break
            w,dt,ci,fr=struct.unpack(RECORD_FMT,c)
            if fr and dt>0: recs.append((o+w,dt))
    recs.sort(); return recs
print('\n[5] pull CPU logs + bin...',flush=True)
cpu={}
for n in READ_NODES:
    ons=holder['r'][n]['wall_origin_ns']; lp=os.path.join(D,'coil_link_%s.bin'%n)
    if n=='dragonseye':
        import shutil; shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)),'run_capture.bin'),lp)
    else:
        subprocess.run(['scp','-o','ConnectTimeout=10',f'{NODE_SSH[n]}:/root/run_capture.bin',lp],capture_output=True,timeout=45)
    recs=load(lp,ons); out=[]; base=None
    for i,p in enumerate(plog):
        lo=p['abs_us']; hi=plog[i+1]['abs_us'] if i+1<len(plog) else pend
        f=[dt for w,dt in recs if lo<=w<hi]
        if not f: out.append((p['phase'],None,None,0)); continue
        m=st.mean(f)/1e6
        if base is None: base=m
        out.append((p['phase'],round(m,4),round(m-base,4),len(f)))
    cpu[n]=out

print('\n'+'='*66); print('COIL MAGNITUDES PER PHASE (the link)'); print('='*66)
print('%-9s %-26s %-12s %-12s %-6s'%('phase','pi5 coil mag[A0,A1,A2]','COM10 amp_r','phase_pi8','n'))
for p in plog:
    c=p['com10']
    print('%-9s %-26s %-12s %-12s %-6s'%(p['phase'],str(p['pi5_coil'].get('mag')),c.get('amp_ratio'),c.get('phase_offset_pi8'),c.get('n')))
print('\nCPU dt per phase (dragonseye, pi5):')
for n in READ_NODES:
    print(' ',n,[(x[0],x[2]) for x in cpu[n]])

out={'phase_log':plog,'cpu':cpu,'com10_url':COM10_URL,'ts':time.time()}
fn=os.path.join(D,'coil_link_pi5_com10_%s.json'%time.strftime('%Y%m%d_%H%M%S'))
json.dump(out,open(fn,'w'),indent=1); print('\n  data: %s'%os.path.basename(fn),flush=True)
print('  done.',flush=True)
