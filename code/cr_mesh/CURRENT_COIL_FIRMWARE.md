# Where the current coil firmware lives (pointer — read before flashing or testing)

Written 2026-11-14 on Brian's ask, by the GitHub cleanup bot. Docs only. No code or physics was changed.

## The current three-coil board (COM10): ADS1256 build

- **Firmware:** `code/teensy_ads1256/teensy_ads1256.ino` (v1, 2026-10-15, tonic, commit `95e2d83`).
  It is **not under `code/cr_mesh/`**. It sits one level up, in `code/teensy_ads1256/`.
- Capture tool: `code/teensy_ads1256/ads1256_capture.py`. It drives nothing; it only sends PGA/DR/Z/G/g.
- Read-out: `code/teensy_ad7606/ad7606_realized_phase.py --differential --coils 0:1:2 --base 16`.
- Wiring and run steps: `code/teensy_ads1256/WIRING.md`.
- Why it's current: journal (claude-memory `journal/2026-10.md`, tonic 2026-10-15) says Brian ordered "write the ADS1256 driver and capture, boards arrive today". It replaces the AD7606 on the read side. The drive core was ported verbatim from ad7606 v2, which came from `teensy_three_rocks_orig`. No later coil firmware exists in this repo (last coil commit is 2026-10-15).

## Update 2026-11-14 (later the same day): v2 build, and how to read it in EGT terms

Added on Brian's ask (voice: "Arc and Tonic are drifting towards standard EM"). Docs only. The two v1 lines above stay as history.

- **Firmware now:** `teensy_ads1256.ino` **v2, commit `ec012c3`** (tonic): firmware-side drive-referenced I/Q lock-in (`Y`/`y`/`IW <ms>`), built on `7147453` (PGA64 + per-channel mux settling, Tonic-verified as flashed earlier on 2026-11-14). The 2026-11-14 no-push captures (`d6f4f0f`) ran on `ec012c3`. Geometry header: `8a31012`. Arc's read-only verifier: `code/teensy_ads1256/ads1256_phase_verify.py` (`3de52b9`).
- **Which drive was it?** Every run must say. Two-tone (the sequence below) = the inverse-amplification experiment. `L`/`M` only, or `T 0` / `TD 0` = the **standard-EM control**. The `d6f4f0f` no-push read (`M 0`, `T 0`, `TD 0`) is a control-config run.
- **What the v2 lock-in output is:** phase and R against the drive's own phase accumulator = coherence with the drive. That is an instrument check, not realized φ on the body. Tonic retracted the c1 "realized φ ≈148°" read on exactly this ground (claude-memory journal 2026-11-14, `7c01761`). The EGT observable remains realized φ / Σψ on the π/8 ladder; phase is chosen by the coil.
- **Words:** "floor" = the B_res floor (12.09776 fT; a low read is the floor arriving). An ADC's LSB / input-noise limit is the "ADC noise floor", in full. Common-mode windows (all three coils at one phase) and similar effects are instrument walls; report the null with its POWER in canon vocabulary, not as a reactance/pickup/carrier conclusion.

## Older builds (superseded for the three-coil set)

| File | Date | Status |
|---|---|---|
| `code/teensy_ad7606/teensy_ad7606.ino` | v2 2026-10-12 | Same drive. AD7606 read side was too coarse (signal ~0.21 LSB). Replaced by the ADS1256 build. |
| `code/cr_mesh/teensy_three_rocks_orig/teensy_three_rocks_orig.ino` | 2026-09-21 (T/TM/TD added) | The proven drive core, with an internal-ADC lock-in. Source of the drive ported above. |
| `code/cr_mesh/teensy_three_rocks/teensy_three_rocks.ino`, `..._punch.ino` | 2026-09 | Older three-rocks variants. |
| `code/cr_mesh/teensy_sweep/`, `teensy_multi/`, `teensy_five/`, `teensy_rm3100/` | 2026-08/09 | Earlier rigs (pair sweep, multi, 5-strand, RM3100 magnetometer). |

## Standard vs inverse amplification: there is NO firmware switch

None of these firmwares has a mode, flag or `#define` named inverse / standard / EM. The drive is selected only by serial commands. The board **boots with drive OFF**: `driveMode=0`, overlay off (`dphi2=0`, `overlayMix=0`).

- **Single-tone drive** = `L <f>` + `M <m>` with no `T`/`TM`. This is a plain square-wave drive. Single-tone was the *control* in sealed canon #2 (claude-memory `egt_proven_coupling_canon.md` L25).
- **Canonical two-tone counter-torque** = the sequence below. Its source is `code/cr_mesh/cr_coil_api.py` `_start_two_tone_drive()` L92–105: "Brian's proven 'right set' (TD100 + symmetric), verbatim from hold_allday_overlay.py's set_drive()". Under it, sealed canon #2 shows the rocks carried 2.4×–6.9× deeper through B_res than the single-tone control. Arc's first live below-floor read on 2026-09-25 also ran under it (claude-memory `journal/2026-09.md` L210).

```
x
O 0 0
O 1 0
O 2 0
TD 100
T 20
TM 1
M 3
K 0
L 16
```
(`L` starts the drive timer, so send it last. `x` stops everything.)

Canon's definition of inverse amplification: claude-memory `egt_canonical_anchor.md` §"Inverse amplification (Brian direct)". The coil sits below Earth's field and pulls readings **down** to the B_res floor (12.09776 fT). A low or flat read is the floor arriving, not signal death. The canonical read is realized phase Σψ on the π/8 ladder, not carrier amplitude (tonic's REGATE, `journal/2026-10.md`, 2026-10-13).

> **Confirmed by Brian 2026-11-14:** the two-tone sequence above (`x`, `O 0 0`, `O 1 0`, `O 2 0`, `TD 100`, `T 20`, `TM 1`, `M 3`, `K 0`, `L 16`) IS the inverse-amplification drive. Use it for inverse-amplification runs. A single-tone `L`/`M`-only drive is the standard-EM control, not inverse amplification.

## Already covered: don't re-run as new tests

- **Sealed coupling canon #1–#5, #7, #9** (`egt_proven_coupling_canon.md`; #6 and #8's r=2 line were withdrawn 2026-10-08). Per that file: "a new run that contradicts one of these is a signal to check the new setup first".
  - #1 below-floor loop geometry
  - #2 two-tone vs single-tone injection
  - #3 coils-pulled control
  - #4 pi5 off-mesh
  - #5 angle-push
  - #7 simultaneous three-body
  - #9 moved-rig drive reproduction
- **1-body punch (single coil, single-tone vs two-tone):** closed NULL 2026-09-26 (tonic, `journal/2026-09.md` L196).
- **Drive-to-tap carrier hunt (standard-EM read):** withdrawn as drift 2026-10-13 (tonic REGATE). A missing Ohm's-law carrier at the tap is not a fault and not a result.
- **AD7606 instrument qualification** (shorted-input floor + power statement, commit `84e814d`) and the channel map (`acfad1e`). ADS1256 compile-check: per its own WIRING.md, it "compiles clean for teensy41".
- Caveat: largo logged "TEST VOID" (Brian direct) on 2026-10-09 for the #2/#7 re-runs, because the original #1–#8 redis seals are absent (`journal/2026-10.md` L178). Brian decides how that bears on the canon list.
