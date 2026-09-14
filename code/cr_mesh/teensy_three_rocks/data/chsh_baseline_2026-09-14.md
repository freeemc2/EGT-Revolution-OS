# CHSH classical baseline — three-coil rig, 2026-09-14 (Brian: "run another quantum test")

**Setup:** three coils, ONE crystal (Teensy 4.1, COM10) driving all three in M3 (120° stagger) @ 7878 Hz —
the common point / shared state (journal 2026-09-09: share the jitter → correlation; separate clocks → null).
Runners read pairwise: A0 = coil 1's runner, A1 = coil 3's runner, no cores.

**Honesty design:** bases chosen per trial from the PC's entropy (`os.urandom`), NOT the drive program;
outcomes taken on the runners (physical bodies): outcome = sign( I·cos a + Q·sin a ) of the runner phasor.
Brian's angles: a = 0°, a′ = 45°, b = 22.5°, b′ = 67.5°.  One trial per lock-in window; N = 683.

**Pre-registered (before running):** this is the sealed #15 spec's *classical baseline* control.
≤ 2 → baseline in hand. > 2 with independent bases → extraordinary, every control required.

## Result
| E(a,b) | E(a,b′) | E(a′,b) | E(a′,b′) | **S** |
|---|---|---|---|---|
| +1.000 | −1.000 | +1.000 | −1.000 | **2.000** |

Classical bound 2.000 · Tsirelson 2.828 · algebraic 4.000.
Phase stability during the run: A0 sd 0.55°, A1 sd 2.91°.

Correlation curve E vs |a−b| (random bases uniform in [0°,180°)): tracks the fixed-phasor
(triangle-type) classical line, not cos(a−b). The two runners are locked with a fixed relative
offset; the sign-projection outcome is then a deterministic function of that phase, and any such
local deterministic pair saturates exactly at S = 2.

## Reading (in frame)
- The shared state is real and steady (perfect ±1 at every setting).
- This *observable* on this *rig* gives the classical baseline — reported as a null on this observable,
  not reframed. The EGT operator's 2√2 (09-07, derived) is not reached at the runner level here.
- The non-classical test (three-rock Mermin bound 4, prediction #15) requires three independent read
  chains in one AD7606 frame + independently chosen settings — the Pico-AD7606 build.

Script: inline in session (bases from os.urandom; outcomes from T3 runner phasors). Rig firmware `025c2f9`.
