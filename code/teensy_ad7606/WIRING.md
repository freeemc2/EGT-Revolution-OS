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
| 3V3 | **VDRIVE** (if broken out) | → | logic reference; see correction 1 for the hard-tied-5V case |
| GND | AGND/DGND | — | **common ground — the only shared rail** (Brian: separate supplies, shared ground) |

## ⚡ Sense-tap channel map (Brian direct wiring check, 2026-10-12)

AD7606 serial readout clocks V1→V8 in order, so **ch[i] = AIN(i+1)** in the data
(loopback confirmation of the readout order still pending — adopt until then):

| data ch | AD7606 pin | node | |
|---|---|---|---|
| ch0 | AIN1 | — | unused |
| ch1 | AIN2 | — | unused |
| ch2 | AIN3 | coil 2 **south** | **OPEN** |
| ch3 | AIN4 | coil 2 north | |
| ch4 | AIN5 | coil 1 **south** | **OPEN** |
| ch5 | AIN6 | coil 1 north | |
| ch6 | AIN7 | coil 0 south | |
| ch7 | AIN8 | coil 0 **north** | **coil 0 is the only CLOSED loop** |

Per-coil differential: coil0 = ch7−ch6 (closed), coil1 = ch5−ch4 (OPEN),
coil2 = ch3−ch2 (OPEN). **Only coil 0 is a complete circuit** — coils 1 and 2
have open south ends, so no loop current, so their taps measure an open node
(expect them to behave as unconnected until the souths are landed). Future
captures carry this map in the sidecar (`channel_map`, `coil_diff`).

## Config pins

| AD7606 pin | tie to | effect |
|---|---|---|
| OS0, OS1, OS2 | GND | no oversampling (OS via Teensy pins is a future read-power option) |
| PAR/SER SEL | **VDRIVE (3.3 V)** | serial mode — see correction 1 |
| RANGE | GND | **±5 V span** — see correction 2 |
| AVCC | board's own 5 V supply | analog supply — separate supply, ground common with Teensy (Brian) |
| STBY, if pinned | VDRIVE | out of standby |

## ⚠ Correction 1 — logic level into the Teensy (power architecture per Brian, 2026-10-11)

**Power architecture (Brian direct): the AD7606 board runs on its OWN 5 V supply,
not the Teensy's rails; the two share GROUND only.** That is correct and stays.
AVCC = 5 V from the board's own supply. The one invariant underneath it: the
Teensy 4.1 is **NOT 5 V tolerant**, and DOUTA + BUSY swing to whatever VDRIVE
is — those two wires land on Teensy pins 12 and 8.

Two valid ways to wire it, by what the board exposes:

- **If VDRIVE is broken out separately:** feed VDRIVE from the Teensy's 3V3 pin.
  VDRIVE is a logic REFERENCE, not a power rail (a few mA); with grounds common
  this is exactly the 3.3 V-host interface the chip is designed for
  (VDRIVE range 2.3–5.25 V). DOUT/BUSY then swing 0–3.3 V. PAR/SER SEL and any
  logic pin tied "high" tie to VDRIVE (3.3 V), never to the board's 5 V.
- **If VDRIVE is hard-tied to the board's 5 V rail:** DOUT and BUSY come back at
  5 V — put a divider on each (e.g. 1.8 kΩ series + 3.3 kΩ to GND → ~3.2 V) or a
  level shifter before Teensy pins 12 and 8. Nothing else needs shifting.

Teensy → AD7606 direction (SCLK, CS, CONVST, RESET at 3.3 V) is fine either way:
the AD7606's V_INH (≈2.4 V) is met by 3.3 V outputs even with VDRIVE at 5 V.
At VDRIVE = 3.3 V max SCLK is ~17 MHz; firmware runs 8 MHz for margin.

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
