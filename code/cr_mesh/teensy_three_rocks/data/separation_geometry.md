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
