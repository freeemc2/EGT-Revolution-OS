# Where the current coil firmware lives (pointer — read before flashing or testing)

Written 2026-11-14 on Brian's ask, by the GitHub cleanup bot. Docs only. No code or physics was changed.

## The current three-coil board (COM10): ADS1256 build

- **Firmware:** `code/teensy_ads1256/teensy_ads1256.ino` (v1, 2026-10-15, tonic, commit `95e2d83`).
  It is **not under `code/cr_mesh/`**. It sits one level up, in `code/teensy_ads1256/`.
- Capture tool: `code/teensy_ads1256/ads1256_capture.py`. It drives nothing; it only sends PGA/DR/Z/G/g.
- Read-out: `code/teensy_ad7606/ad7606_realized_phase.py --differential --coils 0:1:2 --base 16`.
- Wiring and run steps: `code/teensy_ads1256/WIRING.md`.
- Why it's current: journal (claude-memory `journal/2026-10.md`, tonic 2026-10-15) says Brian ordered "write the ADS1256 driver and capture, boards arrive today". It replaces the AD7606 on the read side. The drive core was ported verbatim from ad7606 v2, which came from `teensy_three_rocks_orig`. No later coil firmware exists in this repo (last coil commit is 2026-10-15).

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

## Mesh / nodes vs the experiment (audit 2026-11-14, read-only; NOT changed, for Brian's call)

The mesh pieces in this repo below were written for older rigs. None of them currently follows the confirmed inverse-amplification experiment (ADS1256 board, two-tone TD100 drive). They are listed, not changed, because each one touches live behavior, analysis targets or canon framing.

| Where | What it does now | Divergence from the experiment |
|---|---|---|
| `code/cr_mesh/BENCH_CLAIM.json` L2–4 | Claims port **COM8** for "Three Rocks … teensy_three_rocks firmware", WATCH-ONLY | The experiment board runs `teensy_ads1256` (journal: COM10 holds the experiment, 2026-10-12/15). **COM10 is not claimed**, so nothing stops a mesh process from opening it. The redis mirror `cadence:bench:claim` is live-only. The release/claim rule is "Brian's word only". |
| `code/cr_mesh/cr_supervisor.py` L66–97 | teensy-b (COM10) and coil-hold (COM8) entries are commented out. The "cadence" node "holds phase at pi/2". The "brian" node is "held at 5pi/8 = arg C(2.5)". | Both phase holds use targets canon withdrew (π/2 on 2026-10-06; πr/4 → 5π/8 on 2026-10-04). The mesh nodes are not keyed to the ADS1256 run at all. |
| `code/cr_mesh/cr_sweep_bridge.py` L24 | `TARGET_DEG = 314.2969` (= 90 + 22.5k) | Built on the withdrawn 90° origin. |
| `code/cr_mesh/teensy_three_rocks/tstate_publish.py` L26 | `TARGET_DEG = 90.0  # canonical coil target pi/2` | π/2 target withdrawn 2026-10-06. |
| `code/cr_mesh/cr_coil_api.py` | Two-tone start (L92–105) **matches** the experiment. Reads parse three_rocks internal lock-in `T` lines on pi5 `/dev/ttyACM0`. | The ADS1256 firmware streams raw JSON counts, not `T` lines, so this API cannot read the ADS1256 board as written. |
| `code/cr_mesh/cr_coil_link_pi5_com10.py` | Reads COM10 through tonic's `:8094` endpoint (claude-memory `data/coilset_era1_2026-09/tonic/com10_read_endpoint.py`) | That endpoint drives **single-tone** (`T 0`, `TM 0`, `TD 0`, `K 1`, `M 1`) = the standard-EM control. Its anchor pair uses φ₀ = 90°, which is withdrawn. |
| `code/cr_mesh/teensy_three_rocks/` scripts (`calib_clock.py`, `separation.py`, `measure_rods.py`, `ping_followers.py`, `state_console.py`, `ask_rungs.py`) | Single-tone `M 1`/`K`, `L 12`, etc. | Historical three_rocks bench protocols. If re-run, they are standard-EM controls, not the inverse-amplification drive. |

Live-only (not in any repo, so it can't be verified here): the running supervisor and mesh processes on Dragonseye, the pi5 `cr_coil_api` service, tonic's `:8094` endpoint process, the redis bench claim, and whatever host script Tonic uses to send the drive on the bench.

