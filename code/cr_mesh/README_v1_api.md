# EGT Compute API — Phase 1 (`/v1`)

A gated, documented API over already-built, acceptance-verified pieces: the EGT
operator (`/predict`), a real below-floor-lock experiment runner (`/experiment`),
and a stateless zero-retention transform (`/flow`). One `/v1` front
(`cr_v1_api.py`), stdlib, behind the signup gate (`cr_api_auth.py`).

Operator (canon, complex): **C(r, φ) = λ·(1 + 2r)·e^(−r/3)·e^(iφ)**, r_opt = 2.5, anchor C₀ = C(2.5, π/2), |C₀|² = 6.7995. `/predict` returns the full complex operator per rock, not just the envelope |C(r)|.

## Run

```
python cr_v1_api.py 8099              # INSTRUMENT=1 (test meter on)
INSTRUMENT=0 python cr_v1_api.py 8099 # production (meter pulled)
# /experiment proxies to the copper rig; override with COPPER_URL env
```

## Endpoints (all `/v1`, run endpoints behind the gate)

| method | path | gated | returns |
|---|---|---|---|
| POST | `/v1/keys` | no | `{api_key, per_min, per_day}` — key shown once, stored hashed |
| GET | `/v1/predict?r_a=&r_b=&phi_a_deg=&phi_b_deg=` | yes | complex operator per rock `{C_a,C_b:{re,im,mag,phase_deg,rung,amplitude_ratio,phase_offset_pi8}}` + `lambda,coupling,r_opt,anchor` — no run, exact |
| POST | `/v1/experiment` `{r, phi_deg, seconds}` | yes | `{C_mag, sigma_psi_rung, sigma_psi_label:"commanded", below_floor, state}` |
| POST | `/v1/flow` (raw body) | yes | `{rungs:[64 base-16 ints]}` — deterministic, zero-retention |
| GET | `/v1/meter` | no | `{pkts,bytes}` (INSTRUMENT=1) or `{instrument:false}` (pulled) |
| GET | `/v1/health` | no | liveness + endpoint list |

Auth: send `X-API-Key: <key>` (or `Authorization: Bearer <key>`) on the gated routes.

## Usage

```
POST /v1/keys {"name":"you"}                         -> get a key
GET  /v1/predict?r_a=0&r_b=2&dphi_deg=55             -> operator coupling prediction (design tool)
POST /v1/experiment {"r":2.5,"phi_deg":90}           -> run the lock, read Sigma-psi rung + below-floor state
POST /v1/flow  (body: your bytes/text)               -> deterministic rung-tuple out, zero-retention
```

## Honest-framing guardrail (read before touching the payloads or docs)

- **`/predict`** = the **exact operator**, a design tool. No run, no hardware. Pure math.
- **`/experiment`** = runs a **real below-floor lock** on the copper and reads it.
  `sigma_psi_rung` is **COMMANDED** (computed-from-input) and is **labeled**
  `sigma_psi_label: "commanded"` — it is NOT relabeled as realized. `below_floor`
  is the copper's **real, measured** lock state (null + note if the drive loop
  isn't streaming T3 at read time — honest, never faked).
- **`/flow`** = a **deterministic, zero-retention transform**. Same input → same
  output; nothing is stored. It is **not** described as "computing your data" and
  carries **no throughput figure**.

## Non-goals (explicit, so no one re-drifts)

Phase 1 does **NOT** claim or build any of the following — they are a separate
research track, frontier or retracted, and publishing them here would violate the
GUARD:

- No throughput / "flow-bound" / bits-per-second numbers.
- No SHA-256 / crypto / Bitcoin compute claims.
- No "reads/computes your data / payload."
- No below-B_res channel capacity.
- No AD7606 / Pico read instrument.

## Acceptance

`python cr_v1_acceptance.py http://127.0.0.1:8099 http://127.0.0.1:8100`
(main = INSTRUMENT=1, pulled = INSTRUMENT=0). Current: **17 PASS, 0 FAIL** —
gate 401/200; `/predict` matches canon (|C(0)|=1.000, |C(1)|=2.150, |C(2)|=2.567,
|C(2.5)|=2.608, |C(3)|=2.575) and the coupling formula; `/experiment`
different-geometry→different rung, same→same, labeled commanded, frustrated→below_floor;
`/flow` determinism; `/meter` INSTRUMENT=0 records nothing; no forbidden claim in any payload.

Built on `cr_tunnel_api` (`/flow`+`/meter`, committed `23a21ca`), `cr_compute_api`
(`/predict` operator), `cr_lattice_api`/`cr_api_auth` (gate + experiment). Physics-
measurement track (two-body Σψ, throughput) stays in a separate session per the
drift doctrine.
