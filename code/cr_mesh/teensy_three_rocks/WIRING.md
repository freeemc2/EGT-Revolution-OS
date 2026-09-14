# Three Rocks wiring — Teensy 4.1 (proven on the bench 2026-09-14)

Matches `teensy_three_rocks.ino` as committed. Three coils (schedule-40 3" form, 2.5" OD,
winding around the outside, one 18 ga runner straight through the bore), one Teensy 4.1,
one crystal = shared jitter.

## Each coil — 4 wire ends

| Wire                       | Goes to                          |
|----------------------------|----------------------------------|
| Winding **north** end      | 220 Ω → Teensy **drive pin**     |
| Winding **south** end      | **GND**                          |
| Runner **south** end       | Teensy **analog sense pin**      |
| Runner **north** end       | **GND**                          |

Drive = the winding. Sense = the runner. Nothing floats.

## Pin map (this build)

| Coil | Drive pin | Sense pin   | Firmware index (`K`) |
|------|-----------|-------------|----------------------|
| 1    | **pin 2** | **A0** (14) | K 0                  |
| 2    | **pin 3** | **A1** (15) | K 1                  |
| 3    | **pin 1** | **A2** (16) | K 2                  |

All grounds common. USB to PC (serial + power). Board enumerates as **COM10** on Dragonseye
(it was COM8 before a replug — Windows renumbers).

## Reading it

The 4.1 has two ADC engines, so the firmware reads **two runners at a time**, both plain
single-shot every tick. Pick the pair: `C 0 2` = A0 + A2, `C 1 2` = A1 + A2, `C 0 1` = A0 + A1.
Sweep the pairs to cover all three. `measure_rods.py` does this with a fixed ADC assignment
per runner so before/after comparisons are apples to apples.

Bench sequence: `P` → `R PONG 3rocks 600` · `C 0 2` · `M 1` `K 0` (one coil) or `M 2` / `M 3` ·
`L 7878` → stream `T3 <f> ph0 ph1 ph2 mag0 mag1 mag2 dAB dAC dBC` · `x` to stop.
**`x` sets driveMode=0 — re-send `M`/`K` before every `L`.**

## What this rig can and can't tell you

- **Can:** whether a coil couples to a runner and how strongly, on a fixed channel/ADC/mode.
  Floor ≈ 0.004; a coupled coil reads 0.05–0.3 (10–55× floor); runner out of the bore → floor.
- **Can't:** compare drive modes (symmetric vs 120° stagger) across runners. Square-wave
  drive → edge spikes at the runner → the two ADCs sample different instants on the spike.
  That comparison belongs to the Pico-AD7606 (same-instant 8-channel sampling).
- Avoid lock frequencies that divide 100 kHz evenly (10k, 20k, 25k) — crosstalk bumps.
  7878 Hz and 12000 Hz are clean.

## Lessons paid for

- The firmware used to drive pin **4**; this build has no coil on pin 4. Every "coil C"
  reading taken that way was pin 4 driving air. Pins in the firmware must match the bench.
- Any `stopContinuous()`/`startContinuous()` on an ADC made that channel read a dead floor.
  Single-shot only.
