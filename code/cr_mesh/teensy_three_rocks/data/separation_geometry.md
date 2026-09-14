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
