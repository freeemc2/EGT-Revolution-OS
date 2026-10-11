# teensy_ad7606 — wiring (v1, 2026-10-11, tonic; from Grok's spec with two datasheet corrections)

## Pin map (Grok spec, adopted as given)

| Teensy 4.1 | AD7606 | dir | note |
|---|---|---|---|
| 13 | SCLK | → | SPI0 SCK |
| 12 | DOUTA | ← | SPI0 MISO; serial mode streams all 8 ch on DOUTA |
| 10 | CS | → | driven as GPIO |
| 7 | RESET | → | pulsed high ≥50 ns at init |
| 9 | CONVST A + CONVST B | → | **tied together** — simultaneous sample of both 4-ch groups |
| 8 | BUSY | ← | high during conversion, falls when data ready |
| 3V3 | **VDRIVE** | → | see correction 1 |
| GND | AGND/DGND | — | common ground with Teensy |

## Config pins

| AD7606 pin | tie to | effect |
|---|---|---|
| OS0, OS1, OS2 | GND | no oversampling (OS via Teensy pins is a future read-power option) |
| PAR/SER SEL | **VDRIVE (3.3 V)** | serial mode — see correction 1 |
| RANGE | GND | **±5 V span** — see correction 2 |
| AVCC | 5 V | analog supply (correct as specced) |
| STBY, if pinned | VDRIVE | out of standby |

## ⚠ Correction 1 — VDRIVE must be 3.3 V, never 5 V (hardware-damage item)

Grok's spec said VDRIVE → 5 V. **Do not.** DOUTA and BUSY swing to VDRIVE, and they
drive Teensy pins 12 and 8 directly — the Teensy 4.1 is **NOT 5 V tolerant**
(standing bench rule, reference_bench_hardware.md). The AD7606's VDRIVE range is
2.3–5.25 V precisely so it can interface 3.3 V hosts: take VDRIVE from the
Teensy's 3V3 pin. Consequences: PAR/SER SEL (and any logic input tied "high")
ties to VDRIVE, not 5 V — logic inputs must not exceed VDRIVE + 0.3 V. AVCC
stays 5 V; analog and VDRIVE domains are separate by design. At VDRIVE = 3.3 V
the max SCLK is ~17 MHz; firmware runs 8 MHz for margin.

## ⚠ Correction 2 — RANGE polarity was inverted in the spec

Datasheet: RANGE **high = ±10 V, low (GND) = ±5 V**. The spec said "RANGE to
ground for ±10 V" — grounding it actually selects **±5 V**. We keep RANGE at
GND deliberately: ±5 V span = **152.59 µV/LSB** (vs 305 µV at ±10 V), double the
read power, and the coil sense signals are far inside ±5 V. If a tap can exceed
±5 V, move RANGE to VDRIVE and tell the capture tool `--range-label 10` (the
label never rescales data — raw counts are the record; volts are analysis).
AD7606 inputs tolerate well beyond the selected span without damage.

## Protocol (as specced, confirmed against datasheet)

Pulse CONVST (rising edge starts conversion) → BUSY rises → wait for BUSY low
(~4 µs, no oversampling) → CS low → clock out 8 × 16-bit two's-complement words
on DOUTA (SPI mode 2) → CS high. Firmware free-runs this at the set rate
(default 1000 S/s, `S <hz>` up to 5000) and streams JSON lines over USB serial.

## Push-rest schedule — where it lives

The firmware is a **dumb streamer** and contains no schedule (job spec: no
experiment logic on-board; the gate reaches into data models). The push/settle-4s/
read/rest cycle from Grok's spec is implemented as **window marks in the host
capture tool** (`--schedule push:4,read:8,rest:4`), which annotate records by
timestamp and **drive nothing**. Commanding an actual push is the experiment
layer, run only on Brian's word, as a separate tool.

## Flash procedure

Per reference_bench_hardware.md, verbatim: **isolate the target board before
flashing** (two Teensy 4.1 on the bench — the loader flashes whichever board is
in HID bootloader, ignoring -p). Compile:
`"C:/Program Files/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe" compile --fqbn teensy:avr:teensy41 code/teensy_ad7606`
Verify after flash: `P` → `R PONG ad7606 v1 ...`.

## First measurement before any experiment (job spec, binding)

With inputs shorted to AGND, capture ≥60 s at 1000 S/s (`ad7606_capture.py`) and
file the instrument's own power statement: noise floor in LSB per channel, and
what phase resolution that supports in π/8 terms. The instrument states its
power before it reads anything.
