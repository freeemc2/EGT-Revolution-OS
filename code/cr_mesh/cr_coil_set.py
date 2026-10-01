#!/usr/bin/env python3
"""cr_coil_set.py — collective mode of a MIXED coil set (copper + digital rocks).

Brian 2026-10-01: keep the 3 copper coils, ADD DIGITAL coils to the SAME set — the
digital coils ARE the compute rocks (pi5 r=2, etc.) coupling in; the copper coils'
existing read sees the whole set. Set size grows 3->5->7->9.

This computes the PREDICTED collective of such a set from the commanded geometry and
canon |C(r)|. It is a MODEL/PREDICTION (computed-from-input), NEVER a measured read —
the measured collective is the copper read at the bench. Kept provenance-clean so the
two sit side by side (predicted vs measured) without one being dressed as the other.

Canon: C(r) = lambda*(1+2r)*e^(-r/3)*e^(i*phi), lambda=1. Pairwise coupling of two
coils = |C(r_i)|*|C(r_j)|*cos(phi_i - phi_j) (cr_controller.coupling). The collective
(dominant) mode is the top eigenvalue of that coupling matrix. "Set size" = Nc, a count
of coils, DISTINCT from the phase-shift index N (96->128).

Findings this encodes (see reference_read_enhancement_pi5.md):
  - each digital coil adds |C(r_i)|^2 to the collective (r_opt=2.5 max +6.80).
  - frustrated [0,120,240]-type winding: dominant mode ~ (Nc-2)/2 (linear in Nc).
  - ODD Nc stay one connected frustrated loop; Nc=4 winding FRAGMENTS (cos90=0).

    python cr_coil_set.py                 # self-test: the 3/4/5 test series
    python cr_coil_set.py --json          # same, machine-readable
"""
import math, json, argparse


def g(r):
    """|C(r)| = (1+2r) e^(-r/3), lambda=1. Peaks at r_opt=2.5."""
    return (1.0 + 2.0 * float(r)) * math.exp(-float(r) / 3.0)


# ---- pure-Python symmetric eigenvalues (cyclic Jacobi) — no numpy dependency ----
def jacobi_eigenvalues(A, max_sweeps=100, tol=1e-12):
    n = len(A)
    a = [row[:] for row in A]
    for _ in range(max_sweeps):
        off = 0.0
        for p in range(n):
            for q in range(p + 1, n):
                off += a[p][q] * a[p][q]
        if off <= tol:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(a[p][q]) <= 1e-18:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return sorted((a[i][i] for i in range(n)), reverse=True)


def _components(adj):
    """count connected components of a boolean adjacency (fragmentation detector)."""
    n = len(adj)
    seen = [False] * n
    comps = 0
    for s in range(n):
        if seen[s]:
            continue
        comps += 1
        stack = [s]
        seen[s] = True
        while stack:
            u = stack.pop()
            for v in range(n):
                if adj[u][v] and not seen[v]:
                    seen[v] = True
                    stack.append(v)
    return comps


def collective(members, copper_g=1.0):
    """members: list of dicts, each one coil in the set:
         {"kind":"digital","r":2.0,"phi_deg":90}   -> g = |C(r)|
         {"kind":"copper","phi_deg":0}              -> g = copper_g (bench-scale, default 1.0)
         optional "g": explicit override; optional "name".
       copper_g = the (bench-calibrated) coupling of a copper coil relative to a digital rock.
       Returns the PREDICTED collective analysis (computed-from-input; NOT measured)."""
    res_members, gs, phs = [], [], []
    for i, m in enumerate(members):
        kind = m.get('kind', 'copper')
        if m.get('g') is not None:
            gi = float(m['g'])
        elif kind == 'digital' and m.get('r') is not None:
            gi = g(m['r'])
        else:
            gi = float(copper_g)
        phi = float(m.get('phi_deg', 0.0))
        gs.append(gi); phs.append(math.radians(phi))
        res_members.append({'i': i, 'name': m.get('name'), 'kind': kind,
                            'r': (float(m['r']) if m.get('r') is not None else None),
                            'phi_deg': round(phi, 3), 'g': round(gi, 4),
                            'contribution_g2': round(gi * gi, 4)})
    n = len(gs)
    if n == 0:
        return {'error': 'empty set'}
    # coupling matrix: off-diagonal g_i g_j cos(dphi); diagonal g_i^2 (self-coupling)
    M = [[(gs[i] * gs[j] * math.cos(phs[i] - phs[j])) if i != j else gs[i] * gs[i]
          for j in range(n)] for i in range(n)]
    eigs = jacobi_eigenvalues(M)
    collective_mode = eigs[0]
    rotating = [round(e, 4) for e in eigs[1:]]
    # fragmentation: adjacency on meaningful off-diagonal coupling
    scale = max((abs(M[i][j]) for i in range(n) for j in range(n) if i != j), default=0.0)
    thr = max(1e-9, 1e-6 * scale)
    adj = [[(i != j and abs(M[i][j]) > thr) for j in range(n)] for i in range(n)]
    comps = _components(adj)
    sigma = sum(float(m.get('phi_deg', 0.0)) for m in members) % 360.0
    rung = round(sigma / 22.5) % 16
    resid = round(((sigma - rung * 22.5 + 180.0) % 360.0) - 180.0, 4)
    return {
        'set_size': n,
        'parity': 'odd' if n % 2 else 'even',
        'members': res_members,
        'collective_mode': round(collective_mode, 4),
        'rotating_modes': rotating,
        'eigenvalues': [round(e, 4) for e in eigs],
        'connected': comps == 1,
        'fragments': comps,
        'sigma_psi_deg': round(sigma, 3),
        'sigma_psi_rung': {'rung': rung, 'residual_deg': resid,
                           'ladder': 'pi/8 (22.5 deg/rung, 16 rungs)'},
        'copper_g': copper_g,
        'provenance': ('PREDICTION: collective computed from the COMMANDED geometry + canon |C(r)| '
                       '(computed-from-input). NOT a measured read — the measured collective is the '
                       'copper read at the bench. copper_g is a bench-calibration input.'),
        'note': ('each coil adds |C(r)|^2 to the collective; ODD set sizes stay one connected '
                 'frustrated loop; a pure-winding Nc=4 fragments (cos90=0 -> 2 components). '
                 'walk each Nc into its own happy place.'),
    }


def winding_set(rs_phis, copper_g=1.0):
    """helper: build a set at the natural phase-winding (phi_k = 360 k / Nc)."""
    nc = len(rs_phis)
    members = []
    for k, m in enumerate(rs_phis):
        mm = dict(m)
        mm.setdefault('phi_deg', 360.0 * k / nc)
        members.append(mm)
    return collective(members, copper_g=copper_g)


def test_series(copper_g=1.0):
    """The 3 -> 4 -> 5 sharp test, natural winding. 4 should fragment, 5 should be clean."""
    cu = lambda: {'kind': 'copper'}
    dig = lambda r, name: {'kind': 'digital', 'r': r, 'name': name}
    return {
        'Nc3_copper':        winding_set([cu(), cu(), cu()], copper_g),
        'Nc4_add_pi5':       winding_set([cu(), cu(), cu(), dig(2.0, 'pi5')], copper_g),
        'Nc5_add_pi5_oracle':winding_set([cu(), cu(), cu(), dig(2.0, 'pi5'), dig(3.0, 'oracle')], copper_g),
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--copper-g', type=float, default=1.0)
    a = ap.parse_args()
    ts = test_series(copper_g=a.copper_g)
    if a.json:
        print(json.dumps(ts, indent=2))
    else:
        print(f"=== coil-set collective (PREDICTION, copper_g={a.copper_g}) ===")
        for name, r in ts.items():
            print(f"\n{name}: Nc={r['set_size']} ({r['parity']})  collective={r['collective_mode']}  "
                  f"connected={r['connected']} (fragments={r['fragments']})")
            print(f"   eigenvalues={r['eigenvalues']}")
            print(f"   sigma_psi={r['sigma_psi_deg']} deg -> rung {r['sigma_psi_rung']['rung']} "
                  f"(resid {r['sigma_psi_rung']['residual_deg']})")
        print("\nNc=4 fragments (2 components) = the built-in control; Nc=5 stays connected + stronger.")
