# Per-pin diagnostic on the v2-flashed rig (2026-09-15 06:xx -0400, aria memory-07 + Brian)

Drive each pin alone (M 1, K k), read all three runners + drive-off floor, x5 interleaved, 2 freqs.
Coils connected (v2 wiring). This is a pin-map + chain-integrity check, NOT the dummy-load null.

| drive | @7878 A0 / A1 / A2 (floor) | @12000 A0 / A1 / A2 (floor) | own runner | reading |
|---|---|---|---|---|
| pin2 (C1) | 0.156 / 0.038 / 0.035 (0.003) | 0.233 / 0.057 / 0.051 (0.003) | A0 | **OK** — own runner dominant (~4x cross) |
| pin3 (C2) | 0.014 / 0.068 / 0.033 (0.003) | 0.020 / 0.100 / 0.047 (0.003) | A1 | **OK** — own runner dominant |
| pin4 (C3) | 0.077 / 0.075 / 0.018 (0.003) | 0.115 / 0.110 / 0.030 (0.003) | A2 | **ANOMALOUS** — own runner A2 is the WEAKEST; A0/A1 nearly equal & large |

## Findings
1. **Flash CONFIRMED at pin level:** pin 4 is live (old firmware had no pin-4 drive), pin 1 dropped. The {2,3,4} table is running.
2. **C1 and C2 chains verified:** driving pin2→A0 dominant, pin3→A1 dominant, each ~2-4x over cross-runners. Correct signature of a coil coupling to the runner in its own bore.
3. **C3 chain is BROKEN or miswired.** Driving pin4, the C3 runner (A2) reads LOWEST (0.018/0.030, ~6-10x floor only), while A0 and A1 read ~0.076/0.11 — nearly equal and 4x larger than A2. A real C3 field would couple strongest to A2. The equal-A0/A1 pattern is the loop-EMF/radiating-stub signature: **pin4's drive is likely not reaching the C3 winding (open at the coil), so pin4 radiates as an open stub into the A0/A1 runner wiring instead.** Secondary suspect: A2 runner itself weak (A2 is the smallest cross-term for every drive: 0.035/0.033/0.018).
4. Drive-off floor is tight (0.003) — the star ground + shunts cleaned that up well.

## DO NOT run physics. Meter the C3 branch first (Brian):
- pin4 → 220 R → C3 winding → GND: unpowered, pin4-to-GND should read ~221 ohm. If open/high, the C3 drive is broken.
- C3 runner south → A2 (pin16), north → GND: A2-to-GND should read ~100 ohm (shunt || runner). If wrong, A2 runner or its shunt is the fault.
- Confirm C3's 220 R and 100 R shunt are actually seated on pin4 / A2.
- Re-run this diagnostic; PASS = driving pin4 makes A2 dominant like C1/C2. Only then the dummy-load null, then physics.
