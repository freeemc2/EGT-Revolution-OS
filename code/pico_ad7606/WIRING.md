# PICO-AD7606 read-side instrument — wiring sheet (v1, OG coil first)

**Nothing on the Teensy changes. It keeps the drive.** The Pico W + AD7606 is
the eyes only. No bias networks anywhere — the AD7606 is bipolar.

## ⚠️ SAFETY FIRST — the RP2040 is NOT 5V tolerant (this can KILL the Pico)
The AD7606's digital I/O voltage is set by its **VDRIVE** pin. If VDRIVE is 5V,
then DOUTA/BUSY idle at 5V — and a 5V signal into any Pico GPIO **damages the
RP2040** (its pins are 3.3V max, not 5V tolerant).
**Before connecting ANY data/control line to the Pico:**
1. Power the AD7606 analog supply (VCC/AVCC) at 5V, but drive **VDRIVE = 3.3V**
   from the Pico's **3V3(OUT) pin (pin 36)** — NOT 5V. Many Teyleten boards tie
   or jumper VDRIVE; confirm it.
2. With the module powered and the Pico OFF, measure DOUTA and BUSY idle-high
   with a multimeter: must read **~3.3V, not ~5V.** If they read 5V, either set
   VDRIVE to 3.3V or put a level shifter on every AD7606→Pico line.
3. Only after that check reads 3.3V do you connect the data/control lines.
The Pico→AD7606 lines (CONVST, CS, SCLK) are 3.3V out — safe into the AD7606.
It's the AD7606→Pico lines (DOUTA, BUSY) that must be 3.3V.

## Module jumpers (before wiring anything)
| setting | value | why |
|---|---|---|
| PAR/SER | **SERIAL** | SPI serial mode, single DOUTA line |
| RANGE | **±5V** | finer LSB (153 µV); all bench signals fit |
| OS2..OS0 | **GND (000)** | no oversampling = max conversion rate |
| **VDRIVE** | **3.3V (from Pico 3V3 pin 36)** | RP2040 not 5V tolerant — see SAFETY above |

## Pico W ⇄ AD7606 module
| AD7606 pin | Pico W pin | note |
|---|---|---|
| VCC/AVCC | VSYS (pin 39, 5V) | analog supply 5V |
| VDRIVE | 3V3(OUT) (pin 36, 3.3V) | digital I/O level — MUST be 3.3V (see SAFETY) |
| GND | GND | common ground with Teensy bench ground |
| CONVST (A+B tied) | **GP2** | conversion trigger, rising edge |
| BUSY | **GP3** | high during conversion (~4 µs) |
| RST | **GP4** | reset pulse at boot |
| CS | **GP5** | frame select |
| SCLK | **GP6** (SPI0 SCK) | 15 MHz |
| DOUTA | **GP7** (SPI0 RX) | all 8 channels, 128 clocks |

## Channel plan — OG coil session
| ch | connects to | note |
|---|---|---|
| 1 | runner sense (N end) | direct — no divider, no bias |
| 2 | pair-A | direct |
| 3 | pair-B | direct |
| 8 | **drive reference tap: Teensy pin3 side of the 220R** | 3.3V square fits ±5V; through 100k series for safety |
| 4–7 | spare (future strands / thermal analog) | ground unused inputs |

The drive on ch8 is the whole trick: drive + all senses land in the SAME
simultaneous conversion frame, so every lock-in is referenced to measured
hardware truth and Dphase between rocks is a same-instant subtraction.

## Throughput honesty
Serial single-line: 128 SCLKs @15 MHz ≈ 8.5 µs + 4 µs conversion → ~50 kSPS
ceiling on all 8 channels. USB text/binary stream verified in `cr_pico_capture.py`.
50 kSPS covers drive tones to ~24 kHz (Nyquist). If we ever need more:
DOUTB dual-line + PIO doubles it — v2, not now.

## First-light checklist (flash day — Brian's word required)
1. Flash `pico_ad7606.uf2` (BOOTSEL drag-drop). Nothing else powered.
2. `P` → expect `R PONG pico-ad7606 v1 ...`
3. Inputs grounded → `Z` → all 8 channels within ±20 counts of 0.
4. ch8 tap connected, Teensy driving → `T 1000 20` → ch8 toggling ±rail counts.
5. Only then connect coil senses; run `cr_pico_capture.py`.
