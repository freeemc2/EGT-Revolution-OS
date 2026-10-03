# EGT Compute API — Tester Guide (Phase 1 Preview)

A small, keyed HTTP API exposing three things you can test today:

- **`/predict`** — the EGT connectivity operator **|C(r)| = (1 + 2r)·e^(−r/3)**, exact and instant. A calculation/design tool; no hardware, no run.
- **`/experiment`** — sets a geometry and runs a **real below-floor lock on a physical coil rig**, then returns the reading.
- **`/flow`** — a **deterministic, zero-retention transform** of your input: same input → same output, and the service stores nothing.

> **Base URL:** `https://<host>/v1` — replace `<host>` with the address you were given.
> Everything below assumes `BASE="https://<host>/v1"` and, after signup, `KEY="<your key>"`.

---

## 1. Get an API key

```bash
curl -s -X POST "$BASE/keys" -H "Content-Type: application/json" \
  -d '{"name":"your-name","email":"you@example.com"}'
```
```json
{ "api_key": "egt_xxxxxxxx", "per_min": 30, "per_day": 500,
  "note": "Save this key now — shown once, stored only as a hash." }
```

Send it on every other call as a header:

```bash
-H "X-API-Key: $KEY"          # (or:  -H "Authorization: Bearer $KEY")
```

The key is shown **once** and stored only as a hash — if you lose it, request a new one. Per-key rate limits apply (defaults: 30/min, 500/day).

---

## 2. `GET /v1/predict` — the operator (exact, instant)

Query the connectivity operator and the coupling between two positions.

```bash
curl -s "$BASE/predict?r_a=0&r_b=2&dphi_deg=55" -H "X-API-Key: $KEY"
```
```json
{ "r_a": 0.0, "r_b": 2.0, "dphi_deg": 55.0,
  "C_a": 1.0, "C_b": 2.5671, "coupling": 1.4724, "r_opt": 2.5,
  "operator": "|C(r)| = (1+2r)*e^(-r/3); coupling = |C_a||C_b|*cos(dphi)" }
```

- `C_a`, `C_b` = **|C(r)| = (1 + 2r)·e^(−r/3)** at `r_a`, `r_b`.
- `coupling` = `|C_a|·|C_b|·cos(Δφ)`.
- `r_opt = 2.5` is where |C(r)| peaks.

Reference values: `|C(0)|=1.000`, `|C(1)|=2.150`, `|C(2)|=2.567`, `|C(2.5)|=2.608`, `|C(3)|=2.575`.

---

## 3. `POST /v1/experiment` — run the real rig

Set a geometry and read a real below-floor lock on the physical coil.

```bash
curl -s -X POST "$BASE/experiment" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"r":2.5, "phi_deg":90, "seconds":2}'
```
```json
{ "r": 2.5, "C_mag": 2.6076,
  "sigma_psi_rung": 4, "sigma_psi_label": "commanded",
  "below_floor": true, "below_floor_label": "measured (copper real lock state)",
  "state": { "offsets_commanded_deg": [30,150,270], "mag": [...], "phase_deg": [...] } }
```

Honest labels, so you always know what a number is:
- **`sigma_psi_rung`** is **commanded** — the geometry *you* set, mapped to the π/8 rung ladder (16 rungs). It is labeled `"commanded"`, never presented as a measured output.
- **`below_floor`** is **measured** — the rig's real lock state at read time.
- `/experiment` drives a **shared physical instrument**, so it is rate-limited, and a response may be `503` if the rig's read path is momentarily busy — retry.

---

## 4. `POST /v1/flow` — deterministic, zero-retention transform

Send raw bytes/text in the body; get back a 64-value tuple (each 0–15).

```bash
curl -s -X POST "$BASE/flow" -H "X-API-Key: $KEY" --data-binary 'your data here'
```
```json
{ "rungs": [0,0,1,1,2, ...],
  "note": "deterministic zero-retention transform; same input -> same output" }
```

- **Deterministic:** identical input always yields identical `rungs`.
- **Zero-retention:** the service keeps nothing — your input is not stored, logged, or recoverable after the response.

---

## 5. Utility

```bash
curl -s "$BASE/health"      # liveness + endpoint list  (no key needed)
curl -s "$BASE/meter"       # test instrument; off in production (records nothing)
```

---

## Errors

| status | meaning |
|---|---|
| `401` | missing or invalid API key |
| `429` | rate limit exceeded (per-minute or per-day) — see `retry_after_s` |
| `400` | bad parameters |
| `503` | (`/experiment` only) the physical rig was momentarily unreachable — retry |

---

## Scope of this preview (so expectations are clear)

This preview gives you the **operator** (`/predict`), a **real-rig experiment** (`/experiment`), and a **deterministic transform** (`/flow`). That is the whole of Phase 1.

It intentionally makes **no** claims and provides **no** features beyond that — in particular:
- no performance/throughput or "requests-per-second" figures,
- no cryptographic or security guarantees,
- no "we compute/process your data": `/flow` is a deterministic fingerprint of your input, not a computation over your payload.

Those are separate research tracks and are **not** part of this preview.

---

## Quick full session

```bash
BASE="https://<host>/v1"
KEY=$(curl -s -X POST "$BASE/keys" -H "Content-Type: application/json" -d '{"name":"demo"}' \
      | python -c "import sys,json;print(json.load(sys.stdin)['api_key'])")

curl -s "$BASE/predict?r_a=0&r_b=2&dphi_deg=55" -H "X-API-Key: $KEY"
curl -s -X POST "$BASE/experiment" -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"r":2.5,"phi_deg":90}'
curl -s -X POST "$BASE/flow" -H "X-API-Key: $KEY" --data-binary 'hello egt'
```
