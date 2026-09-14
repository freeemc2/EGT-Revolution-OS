# Rod-series data — three coils, Teensy three-rocks rig (2026-09-14)

Produced by `../measure_rods.py`: each coil driven alone (pins 2/3/1), every runner read
(A0/A1/A2, fixed ADC per runner), 3 frequencies (3000/7878/12000 Hz) x 3 repeats, no-drive
floor per frequency. Values are lock-in magnitude (arb.); floor ~0.004.

| file | state | note |
|---|---|---|
| `rods_norods_3coils.json` | **no cores** — confirmed by Brian | the baseline |
| `rods_1rod_each.json`     | one ferrite rod in each coil | |
| `rods_2rods_each.json`    | two ferrite rods in each coil | |

Ratios (2rods/norods, consistent at all 3 freqs): coil2->A0 0.12, coil3->A0 0.06, coil1->A0 1.5;
coil3->A1 1.0, coil2->A1 0.28, coil1->A1 0.15; all->A2 ~1.2. Rods confine each coil's flux
to its own bore: cross-coupling to neighbours' runners collapses (up to 17x), each runner ends
up owned by the coil it sits in. Inter-coil coupling is what ferrite suppresses.

## superseded/
Taken on the earlier firmware that drove pin **4** (no coil on it in this build). Their
`pin2`/`pin3` rows are valid; every `pin4` row is pin 4 driving air, not a coil.
- `rods_norods.json` — no cores
- `rods_2rods_coils2-3.json` — two rods total (coils 2 and 3), before coil 1 was ever driven
