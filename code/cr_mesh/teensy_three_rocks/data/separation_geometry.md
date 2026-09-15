# Separation test — geometry + leg-by-leg reading (2026-09-14)

**Mapping (Brian):** his coil 1 = pin 1 (runner A0) · coil 2 = pin 2 (DRIVEN) · coil 0 = pin 3 (runner A1).
Earlier rod series ran with all three coils ~2" apart.

| station | coil0–coil1 | coil1–coil2 | coil2–coil0 | driven→A0 leg (2→1) | driven→A1 leg (2→0) |
|---|---|---|---|---|---|
| S0 | 8" | 8" | 8" | 0.205 / 0.308 | 0.084 / 0.125 |
| S1 | 12" | 12" | 18" | 0.091 / 0.137 = **×0.44** | 0.083 / 0.126 = **×1.00** |

**Leg 2→1 (A0):** distance ×1.5, coupling ×0.44. 1/d² predicts (8/12)² = 0.444 — exact.
Near-zone inductive fall-off; doubles as a calibration of the method.

**Leg 2→0 (A1):** distance ×2.25, coupling ×1.00 (to 3 decimals). 1/d² predicts ×0.20, 1/d³ ×0.09.
Distance-independent so far — the sealed P-SEP1 signature on this leg.

## Pre-registered control (before it is run)
Pull coil 2's drive lead off its 220 Ω; pin 2 keeps toggling with NO coil attached. Read A0/A1 (on/off ×5).
- A1 → floor (~0.004): the flat leg is coil-mediated → real, proceed to S2/S3 on that leg with the seal's rules.
- A1 stays ~0.08: board/ground crosstalk pedestal → the flat leg is mundane; only the 1/d² leg stands.
Reference: pin 4 driving air (no coil, no load) earlier read A1 ≈ 0.015–0.020 — a lower bound on board crosstalk.

## CONTROL RESULT (12:44) — mundane branch, decisively
Coil 2's lead pulled, pin 2 toggling with no coil: **A0 0.434 / 0.655, A1 1.211 / 1.834** (7878 / 12000 Hz),
vs coil attached at S0: A0 0.205 / 0.308, A1 0.084 / 0.125. Removing the coil made both runners read MORE —
A1 by ~15x. The runners pick up pin 2's drive wiring directly (unloaded 3.3 V square wave on that lead),
not only the coil's field. The flat A1 leg was that pickup — a coil-position-independent pedestal.

**Status: S0 and S1 are VOID; the separation series is MOOT until the wiring passes the null.**
Pre-registered pass criterion for the rewire (before it is done): with coil 2 disconnected and pin 2 toggling,
A0 and A1 must read <= ~3x floor (~0.012). Only then reconnect, reset coils to 8", and re-take S0.
Likely fix: route pin 2's drive lead away from the A1/A0 runner wiring (localize live by moving the loose lead);
verify runner north ends are solidly on GND.

## LIVE LOCALIZATION (13:0x) — lead proximity is only part of it
Pin 2 toggling, coil 2 disconnected, Brian moved the loose lead: A1 swung 0.58 <-> 1.32 with lead position
(proximity real, routing fixes that part). But with the lead AWAY, A1 still 0.58 and A0 0.32, unaffected
by lead position -> a pedestal ~50x the pass target that is NOT the lead. Cause: an OPEN, unloaded pin swings
full rail with ~ns edges and radiates far more than a loaded pin; attaching the coil slows the edge, which is
why the coil made readings DROP. The no-coil control was therefore a HARSHER condition than the real run —
the wrong null.

## CORRECTED CONTROL — pre-registered before it runs
Dummy load: replace coil 2 with a resistor (match coil 2's winding R if metered; else 220 R noted as mismatch)
from the 220 R's far end to GND; route pin-2 leads away from runner wiring. Same current, same edges, no field.
- PASS: A0 and A1 <= ~3x floor (~0.012) -> real coil runs are clean; pickup existed only on an open pin.
- FAIL: A0/A1 still ~0.2 / 0.08 -> pedestal present during real runs; separation data contaminated until the
  sense side is hardened (low-value shunt from each A-pin to GND so the node is low-Z; twist drive pairs;
  keep drive and runner leads apart; verify runner north ends solidly on GND).
S0/S1 remain VOID pending PASS.

## ALIGNMENT CORRECTION (Brian's call, 13:0x) — the C(r) branch was mis-stated
I pre-registered "distance-independent C(r) -> x1.0 at every station." That is NOT the canon formula.
Canon (egt_canonical_anchor): C(r) = lambda(1+2r)e^(-r/3)e^(i phi), r = d/D dimensionless, r_opt = 2.5.
|C(r)| PEAKS at r = 2.5 (d = 6.25" for D = 2.5") and decays as e^(-r/3) beyond.

| d | r | |C(r)| | ratio vs 8" | near-field 1/d^2 vs 8" |
|---|---|---|---|---|
| 2" | 0.8 | 1.99 | x0.78 | x16 |
| 4" | 1.6 | 2.46 | x0.97 | x4 |
| 6.25" | 2.5 | 2.61 | x1.02 (peak) | x1.6 |
| 8" | 3.2 | 2.55 | x1.00 | x1.00 |
| 12" | 4.8 | 2.14 | x0.84 | x0.44 |
| 18" | 7.2 | 1.40 | x0.55 | x0.20 |

Corrected discriminator: a PEAK near 6.25" (non-monotonic) vs monotonic decay. Sharpest single test:
8" -> 2": C(r) predicts x0.78, near-field predicts x16.
The 08-30 sealed "flat across buildings" is the B_res FLOOR coupling in the deep tail — a different regime.
Three rocks: C_total = |C(2.5)| Sum_k e^(i phi_k); symmetric -> 0 (null), 120deg stagger -> 3 (full) — at the CENTROID,
not at in-bore runners. All of this pre-registered before any clean (post-control2) data exists.

## CONTROL2 RUN — DUMMY LOAD (2026-09-15 06:11 -0400, aria memory-07 + Brian) — FAIL
Sealed before data: redis `cadence:tworocks:sealed-control2-dummy-load` @ 10:09:47Z. Coil 2 out, far end of pin-2's 220 R
jumpered to GND (winding ~1 ohm 22 AWG => jumper is the matched load), pin-2 leads routed away, runners as placed.
`separation.py CTRL2`: interleaved on/off x5.

| f | floor | limit (3x) | A0 diff | A1 diff | verdict |
|---|---|---|---|---|---|
| 7878 | 0.003 | 0.009 | 0.094 +/- 0.001 | 0.115 +/- 0.001 | FAIL (x10 / x13) |
| 12000 | 0.005 | 0.015 | 0.142 +/- 0.001 | 0.172 +/- 0.001 | FAIL (x9 / x11) |

Loaded pin is 4-10x quieter than the open pin (CTRL: 0.43 / 1.21) — edge-slowing real — but a pedestal ~0.1 remains
with NO coil and NO field. Pedestal scales with frequency (0.094 -> 0.142 = x1.51; f ratio 1.52): dV/dt-proportional
pickup from the drive wiring into the high-Z runner nodes. Per the pre-registered FAIL branch: harden the sense side
before any coil data — low-value shunt (~100 R) from each A-pin to GND (runner source ~1 ohm, so negligible loading),
twist each drive pair (pin -> 220 R -> load, return), keep drive and runner leads apart, verify runner norths on GND.
Then re-run CTRL2 against the same sealed criterion. S0/S1 remain VOID; eigenmode data NOT to be taken until PASS.

## CONTROL2 RE-RUN — dummy load + 100 R shunts A0/A1/A2 -> GND (2026-09-15 06:25 -0400) — FAIL, but diagnostic
Same seal, same protocol. Prior run kept as `sep_CTRL2_noshunt_0611.json`; this one `sep_CTRL2_shunt_0625.json`.

| f | limit (3x floor) | A0 before -> after | A1 before -> after |
|---|---|---|---|
| 7878 | 0.0095 | 0.094 -> 0.035 (x2.7 better, still x3.7 over) | 0.115 -> 0.093 (x1.2, still x9.8 over) |
| 12000 | 0.0147 | 0.142 -> 0.053 (x2.7 better, still x3.6 over) | 0.172 -> 0.139 (x1.2, still x9.5 over) |

Discrimination: a shunt to GND kills pickup that arrives AT THE NODE (capacitive, high-Z) but does nothing to an EMF
induced IN SERIES around the runner loop (magnetic, from the drive current's loop). A0's residual is mostly
node-type and the shunt took most of it; A1's residual is loop-type — the dummy-load drive loop (pin 2 -> 220 R ->
jumper -> GND) carries the full drive current and its loop area links A1's runner loop. Both still f-proportional.
Next (pre-registered): shrink loop areas — twist the drive path tightly as a pair (out and return together),
twist each runner pair (south -> A-pin with north -> GND), move the dummy-load loop away from the A1 runner.
Re-run vs the same seal. Still NO coil data until PASS.
