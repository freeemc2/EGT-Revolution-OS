# hardware/ — Laboratory Hardware

Physical instrumentation used or planned for EGT verification experiments.

## Files

- **`dragons-eye/config.md`** — Dragons Eye magnetometer array specification. 3×3 RM3100 sensors targeting the 12.09776 fT ultramagnetic resonance. 24-bit SPI, 4-way differential buffer. Objective: capture the C(r) coupling via the claimed 402.3× amplification bridge.

## Additional hardware referenced in project notes but not yet documented here

- **Trifilar coil.** 42 strands, 1.92" steel tube, driven at 130 Hz, for B_res generation.
- **Teensy 4.1 bare-metal controllers.** ARM Cortex-M7, cycle-counter timing for CV measurement without OS jitter. Real controller code in `code/dragons-eye-controller.py` (Python master side) plus `Documents/Arduino/DragonsEye_Clean/DragonsEye_Clean.ino` on the author's workstation (not in this repo yet — should be imported).
- **Instruments in hand.** Spectrum analyzer, VNA (nano-VNA-H), oscilloscope (FNIRSK), signal generator, tinySA Ultra, multimeters.

## Known dependencies

The `code/dragons-eye-controller.py` script depends on:
- Real serial connection to the Dragons Eye hardware or a Teensy 4.1
- `numpy` and `matplotlib` (see repository-level `requirements.txt`)

## What is claimed here vs. what is not

- **Claimed:** the RM3100 array configuration is designed to be sensitive to a 12.09776 fT signal component. This is engineering, not physics — the RM3100 datasheet supports this claim.
- **Not claimed:** that a 12.09776 fT signal has been detected. Successful detection at that level with the described array would be a significant empirical anchor and is one of the pending items in `predictions/verification-matrix.md`.
