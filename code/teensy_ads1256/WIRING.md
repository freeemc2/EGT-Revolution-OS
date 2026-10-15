# teensy_ads1256 — wiring (v1, 2026-10-15, tonic)

ADS1256 replaces the AD7606 on the read side. One Teensy still drives the coils
AND reads the ADS1256. The ADS1256's on-chip PGA is the gain stage (no external
op-amp) and its differential inputs read tapA-tapB directly.

## ADS1256 ↔ Teensy 4.1 (SPI MODE 1)

| Teensy pin | ADS1256 | dir |
|---|---|---|
| 13 | SCLK | → |
| 11 | DIN (MOSI) | → |
| 12 | DOUT (MISO) | ← |
| 10 | CS | → |
| 9 | DRDY | ← (data-ready, active low) |
| 8 | RESET | → |
| 7 | PDWN/SYNC | → (held HIGH; SYNC issued over SPI) |
| GND | DGND + AGND | — common with Teensy |

Power: ADS1256 board on its own 5 V (AVDD) + 3.3 V (DVDD) per the board; Vref 2.5 V
(onboard). Ground common with the Teensy and the coil souths.

**⚠ Logic level:** ADS1256 DOUT swings to DVDD. If the board's DVDD is 5 V, protect
Teensy pin 12 (series R or level shifter) — Teensy 4.1 is NOT 5 V tolerant. If DVDD
is 3.3 V, connect direct. (Same rule as the AD7606 DOUT caution.)

## Analog inputs (differential — one pair per coil)

| coil | ADS1256 + | ADS1256 − | read as |
|---|---|---|---|
| 0 | AIN0 | AIN1 | ch0 |
| 1 | AIN2 | AIN3 | ch1 |
| 2 | AIN4 | AIN5 | ch2 |

The sense tap pair of each coil goes to its AIN+/AIN− pair. The differential read
rejects the common-mode (including the ~163 mV DC offset the AD7606 saw single-ended),
so no AC-coupling cap is needed. AIN6/AIN7 spare.

## Drive (unchanged, WIRING v2 2026-09-15, Brian-verified)

pin 2 → 220 Ω → coil0 north, pin 3 → coil1, pin 4 → coil2; winding souths → GND.

## Read power (why this instrument)

PGA ×64, Vref 2.5 V, 24-bit → LSB ≈ 4.66 nV; input noise ~90 nV (100 SPS) to
~430 nV (1000 SPS). The ~32 µV sense signal reads at SNR 70–350 — vs 0.21 LSB
(below floor) on the AD7606. Read power is solved on-chip; no external gain stage.

## Trade-off (honest)

Single ADC behind a MUX → **sequential, not simultaneous**. The 3 coils are read
round-robin with a per-channel settle (SYNC/WAKEUP, wait DRDY). This puts a FIXED
phase skew between coils (0.6–1.7° at 16 Hz for typical round timing), which is a
constant per-channel offset that cancels in the anchor-relative occupancy — fine
for a HELD below-floor read (phases stable). It is NOT true simultaneous sampling;
do not use for a fast transient where the coils' phases move within one round.

## Run

```
# bring up: set PGA + data rate, self-cal, then the canonical drive, then capture
#   (ads1256_capture.py sends PGA/DR/Z/G itself)
python ads1256_capture.py --port COM10 --seconds 60 --pga 64 --dr 1000 --out data/ads1256_run
# read realized phase (same tool, differential mode):
python ../teensy_ad7606/ad7606_realized_phase.py data/ads1256_run.jsonl --differential --coils 0:1:2 --base 16
```

Flash: isolate the target board (multi-Teensy HID gotcha), verify `P` → `R PONG ads1256...`.
Firmware compiles clean for teensy41 (63.6 K flash).
