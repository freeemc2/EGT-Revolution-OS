# teensy_ad7606 — instrument power statement (binding, filed before any experiment read)

**Capture:** `data/ad7606_noisefloor_shorted_20261012_061011.jsonl` (+sidecar), 2026-10-12,
60.1 s @ 1000 S/s, 60,101 records, 0 parse errors. Inputs shorted per Brian at the bench.
Board: Teensy 4.1 #18809830 (COM10) + AD7606, VDRIVE 3.3 V, RANGE = GND (±5 V span,
152.588 µV/LSB), no oversampling.

## Timing
Sample interval: median / min / max = **1000 / 1000 / 1000 µs** over the full run —
no observable jitter at µs resolution, no dropped records. The free-run scheduler holds rate.

## Noise floor (the number that gates every future read)
Per channel over 60 s: **sd 2.29 LSB rms (350 µV)**, peak-to-peak 7 LSB. All 8 channels
within 0.4 % of one another (sd 2.286–2.294 LSB). Stationary across the minute.

## Phase resolution this supports (π/8 terms — the canon question)
Single-sample realized-phase error ≈ atan(σ/A) for a signal of amplitude A:

| signal amplitude | single-sample phase error |
|---|---|
| 11.5 LSB (1.76 mV) | 11.25° = **half a rung** — the single-shot threshold |
| 50 LSB (7.6 mV) | 2.6° |
| 100 LSB (15.3 mV) | 1.3° |
| 1000 LSB (153 mV) | 0.13° |

Coherent averaging improves this as √N: a 1 s lock-in window at 1000 S/s (N=1000, ~×31)
puts even a **0.4 LSB (60 µV)** signal at the half-rung threshold. Compare the retired
read path: the Teensy internal lock-in's least count was 0.001 in its own units with legs
at 1–17 counts — signals that sat unreadable there land hundreds of LSB here, sub-degree.
What this instrument CANNOT do: resolve single-shot phase on signals under ~12 LSB
(1.8 mV) without averaging; see anything finer than 152.59 µV in amplitude per count.

## ⚠ Open instrument characteristic — the standing offset (flagged, not explained)
All 8 channels sit at a common **+1063…+1078 LSB (~+163 mV)** — and the shorted means are
statistically identical to the floating-input conversions taken before the short
(1060–1080). Shorting changed nothing measurable. Most likely: the breakout's input
network biases the inputs so floating ≈ shorted (common on these boards), making the
+163 mV a real, stable common offset of the signal chain (ground drop or input-conditioning
offset — it exceeds the bare chip's offset spec, so it is board-level). It is common-mode,
stable to ±2 LSB, and **subtracts out of every AC/lock-in/phase read** — it gates nothing
we plan to measure. It DOES ride on absolute DC readings until explained. Bench check that
would settle it: meter the voltage between the shorting point and the AD7606's AGND pin.

**Verdict: instrument QUALIFIED for phase work at the resolutions tabled above, with the
DC offset carried as a known characteristic.** This statement is the reference against
which every future "could the measure have seen it" question on this instrument is answered.
