# THREE ROCKS — COMPLETE BOARD PINOUT (Teensy 4.1) — 2026-09-15

## ★★ DRIVE-PATH BUG FOUND (Brian observation 2026-09-15): 220R jumps straight to a GROUND wire.
## Brian sees: drive pin -> breadboard -> 220R -> ground wire -> GND, i.e. pin -> 220R -> GND with the COIL
## WINDING NOT in the current path. That shorts the winding / bypasses the coil -> no field -> no coupling.
## ANSWER to Brian's question: the 3.3V drive is CORRECT (GPIO HIGH = 3.3V) and is NOT suppressed by any 10K.
## The 10K's are SENSE-side bias ONLY. Drive current is limited by the 220R, and the winding MUST be in series:
##     drive pin --- 220R --- winding NORTH ;  winding SOUTH --- GND      (winding is the ONLY path to GND here)
## FIX: at the far end of each 220R, the ONLY connection is the coil winding NORTH. Remove any ground jumper at
## that node. The winding SOUTH is the sole ground. C2/C3 coupled (their windings ARE in-path); C1 is dead
## (the runner-pin16/drive-pin4 coil) -> check C1 first for the stray ground jumper at its 220R far end.

## ★ RUNNER MAP CORRECTED (Brian 2026-09-15): sense pins are wired in REVERSE coil order.
##   pin16 (A2) -> C1 runner   |   pin15 (A1) -> C2 runner   |   pin14 (A0) -> C3 runner
## Diagnostic re-read under this map: driving pin2 lights C3's runner (A0) strongest, pin3 lights C2's (A1).
## So the DRIVE side is also reverse-ordered: pin2->C3, pin3->C2, pin4->C1 (pin4->C1 inferred; C1 chain is broken).
## CONSEQUENCE: the firmware index pairs (drive pin2<->A0, pin3<->A1, pin4<->A2) each land on the SAME coil,
## so the firmware is ALREADY self-consistent — NO firmware change needed. Only my earlier labels were backwards.
##   firmware K0 = pin2 + A0 = C3   |   K1 = pin3 + A1 = C2   |   K2 = pin4 + A2 = C1
## THE ONE REAL FAULT: C1's chain (drive pin4, runner pin16=A2) — A2 is the weakest channel in EVERY drive
## condition (0.018-0.035 vs 0.15+ healthy). Isolated to: pin4 drive not reaching C1 winding, or pin16/A2
## runner (wire / its 100R north return / the A2 bias leg) open. Meter C1's chain; C2 and C3 are proven good.
# aria (memory-07) for Brian. Reconciled to the OG-coil (teensy_sweep) bias topology Brian says he built.
# Supersedes the resistor section of WIRING_v2_2026-09-15.md. VERIFY every line with a meter before power.

Board: Teensy 4.1 on COM10, F_CPU 600 MHz (`P` -> `R PONG 3rocks 600`). NOT 5V tolerant — every sense pin
must be biased and clamped to stay in 0..3.3V or the pin is damaged.

## POWER RAILS (single star points — this is where a stray 3.3V path hides)
- **3V3**  = Teensy 3.3V pin. Feeds ONLY the three 10K bias-top resistors (one per sense pin). Nothing else.
- **GND**  = one Teensy GND pin = the star node. EVERY ground returns here directly, never coil-to-coil.
  Grounds landing on GND: each winding south, each runner north, each 10K bias-bottom, board GND of the shunts if used.

## THE OG-COIL SENSE BIAS (this is the part my v2 sheet omitted — Brian's "like the OG coil")
Each analog sense pin is centered at mid-rail (~1.65 V) by a divider so the coil's induced swing rides on top
without going negative or above 3.3 V:
    3V3 --- 10K --- [A-pin] --- 10K --- GND        (per sense pin; OG teensy_sweep line 16)
The RUNNER connects to the A-pin node too (runner south -> A-pin, runner north -> GND). So the DC picture at
each sense pin is: 3V3 -> 10K -> node -> (10K to GND) || (runner ~1 ohm to GND). Bias current ~0.16 mA per pin.

## PER-COIL WIRING (all three identical) — DRIVE and SENSE are separate wires
Drive (winding is driven):   DRIVE_PIN --- 220R --- winding NORTH ;  winding SOUTH --- GND
Sense  (runner is read):     runner SOUTH --- A-pin (+ 10K/10K bias) ;  runner NORTH --- 100R --- GND bus
   (Brian 2026-09-15: the 100R is a SERIES element in the runner's north ground return, NOT a shunt on the A-pin.
    The 10K/10K bias is at the A-pin on the SOUTH end; opposite ends of the runner, so the 100R does not load the bias.)

| Coil | DRIVE pin | 220R | winding N / S | SENSE pin (ADC) | runner S / N | bias top 10K | bias bot 10K |
|------|-----------|------|---------------|-----------------|--------------|--------------|--------------|
| C1   | pin 2     | 220R | N->220R->pin2, S->GND | A0 = pin14 (adc0) | S->A0, N->100R->GND | 3V3->A0 | A0->GND |
| C2   | pin 3     | 220R | N->220R->pin3, S->GND | A1 = pin15 (adc1) | S->A1, N->100R->GND | 3V3->A1 | A1->GND |
| C3   | pin 4     | 220R | N->220R->pin4, S->GND | A2 = pin16 (adc0/adc1) | S->A2, N->100R->GND | 3V3->A2 | A2->GND |

Firmware indices: K0=C1(pin2/A0), K1=C2(pin3/A1), K2=C3(pin4/A2). `DRIVE_PINS={2,3,4}`, `SENSE_PINS={A0,A1,A2}` (flashed).

## RESERVED / FORBIDDEN PINS (do not put a coil or runner on these)
- pin 0, pin 1  = Serial1 RX/TX. **pin 1 was the OLD C3 drive — that is the bug we just removed. Nothing on 0/1.**
- pin 18, 19    = I2C SDA/SCL — reserve for the RM3100 magnetometer (centroid field read) later.
- pin 11,12,13  = SPI + onboard LED (13).
- USB / 3V3 / VIN / GND per the Teensy silk.

## FULL RESISTOR BILL
- 3 x 220R  — drive series, one per drive pin (pin2, pin3, pin4).
- 3 x 10K   — bias top, 3V3 -> A0 / A1 / A2.
- 3 x 10K   — bias bottom, A0 / A1 / A2 -> GND.
- 3 x 100R  — series in each runner's NORTH ground return (runner north -> 100R -> GND bus). Per Brian's build.

## RESOLVED / OPEN
1. **RESOLVED (Brian 2026-09-15):** the 100R is in the runner's north ground return, 10K/10K bias is on the
   A-pin (south) — opposite ends, no conflict. Bias intact. My earlier "shunt on the A-pin" reading was wrong.
2. **STILL OPEN — Drive topology.** OG teensy_sweep (after the 2026-08-23 swap) drives the RUNNER (pin3->220R->runner->GND)
   and senses the PAIR wires. three_rocks firmware drives the WINDING and senses the RUNNER — the OPPOSITE
   roles. "Set up like the OG coil" could mean you wired runner-driven. If so, C1/C2 happening to look right is
   luck of symmetry and C3 is the tell. Confirm: on the bench, is the 220R feeding the WINDING or the RUNNER?

## TARGETED CHECK for your hypothesis "3.3V / drive is passing through the drive wires"
Power OFF, Teensy USB unplugged, meter in ohms:
- a. 3V3 pin to each DRIVE pin (2,3,4): must be **OPEN** (infinite). If any reads ~10K or lower, the 3V3 bias
     rail is touching a drive line — that is the leak. Most likely on C3 (pin4) given the diagnostic.
- b. Each DRIVE pin to GND: ~221 ohm (220R + ~1 ohm winding). C3/pin4 reading OPEN = its drive never reaches
     the winding (matches pin4 radiating, A2 dead).
- c. Each A-pin to GND: 10K bias-bottom in parallel with (runner ~1 ohm + 100R = ~101 ohm) => ~100 ohm.
     All three A-pins should read the SAME (~100 ohm). If A2 differs, that is the C3 sense fault (runner open,
     100R missing/wrong, or bias leg off).
- d. Each A-pin to its own DRIVE pin (A0-pin2, A1-pin3, A2-pin4): must be **OPEN**. A short here means a runner
     shares a node with a drive line — the exact "3.3V through drive wires" path, since the A-pin carries the
     3V3 bias. Check A2-to-pin4 first.
- e. 3V3 to GND: with everything correct, ~5K (3 bias dividers of 20K each in parallel = ~6.7K). A much lower
     reading = a shunt or short loading the rail.

Expected outcome that explains the diagnostic: (b) pin4 OPEN to GND and/or (d) A2 shorted to pin4.
