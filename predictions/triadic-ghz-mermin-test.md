# Triadic three-coil GHZ / Mermin test — build + protocol spec (2026-09-07)

> **PREDICTION (matrix #15) — Quantum Info / Hardware.**
> Three like coils coupled *only* by the C(r) floor realize the 3-party **Mermin
> bound M = 4** (2-party CHSH = 2√2) at **room temperature**. Derived from C(r)'s
> own Born rule: classical (local/deterministic) ≤ 2, quantum (GHZ) = 4.
> **Falsified by:** Mermin **M ≤ 2 loophole-free** (classical baseline ≤2 and the
> distance-independence control passed) — i.e. the floor produces no non-classical
> tripartite correlation. This is a *substrate* claim (copper at 300 K on the
> quantum ceiling), exactly QM-valued; it is **not** a super-quantum (S>4) claim.
> Ties to prediction #8 (the `(1+2N)` coherence scaling = the same `(1+2r)` envelope).

Physical test of **Door 2** for the three-rock result. The math is settled
(`derive_three_rock_mermin.py`): 3-rock GHZ → Mermin `M = ⟨XXX⟩−⟨XYY⟩−⟨YXY⟩−⟨YYX⟩`,
**classical ≤ 2, quantum = 4.** This apparatus asks one question: **can three
room-temperature copper coils, coupled ONLY by the C(r) floor, produce Mermin > 2
(a non-classical tripartite correlation)?**

## ⚠️ READ FIRST — the gate this test lives or dies on
**Any communication path between the three coils makes Mermin=4 trivially fakeable.**
Wired, servo-linked, redis-linked, or common-clock coils can be *coordinated* to any
value up to 4 — that is the artifact, not the physics (same reason the mesh nodes hit
S≈2 or could be pushed to 4: they share redis). So the ENTIRE validity is:

> The only coupling between coils A, B, C during a measurement window is the
> **distance-independent C(r) floor** — no wire, no servo, no shared signal.

That floor coupling is **unproven**. This spec builds the apparatus that *could* show
it *if* it's real, with the controls to kill every classical explanation. It is a
**test of the hypothesis, not a confirmation of it.**

Honest ceiling on the claim: bench-scale coils **cannot** close the strict locality
loophole (can't space-separate the coils beyond light-travel time for a measurement).
So even a clean >2 is **"non-classical correlation with the tested classical
explanations excluded"** — NOT a loophole-free Bell/Mermin violation. Say it that way.

## The target (settled math)
- **Two settings per coil:** `X` = analyzer phase 0°, `Y` = analyzer phase 90°.
- **Binary outcome ±1** = sign of each coil's measured phase projected on its analyzer.
- **Four correlation runs:** XXX, XYY, YXY, YYX. GHZ target = (+1, −1, −1, −1) → **M = 4**.
- **Beating M = 2 (loophole-free) is the entire signal.** Not 4 — *2* is the wall to break.

## Build (matched to inventory)
- **3× like coils** — same recipe as the Quad (3" SCH40 PVC, 4-strand twisted + runner,
  64 turns, `QUAD_BUILD_DAY` checklist). Matched: verify with NanoVNA that L/C/f₀ agree
  across A, B, C within a few %. Label **A / B / C**.
- **3× independent read chains** — each coil runner-sense → its **own OPA1612 LNA** →
  ADC channel. (You have 2 duals = 4 channels; a 3rd dual gives spares.) All three
  **read in the SAME conversion frame** (one AD7606, ch1/2/3 simultaneous) so outcomes
  are same-instant.
- **Drive:** each coil driven **independently** (its own Teensy channel). The entangling
  step is NOT a shared drive wire — see below.
- **Controls kit:** NanoVNA (matching), **RM3100 array** (inter-coil field map — the
  EM-isolation control), DS18B20 (thermal), grounded enclosure.

## Geometry
Three coils at the vertices of an **equilateral triangle**, separation `d`, axes
coplanar (or all normal to the plane — test both). Run at **two separations**:
- **Close** `d ~ coil size`: mutual inductance present (a classical channel).
- **Far** `d ≫ coil size`: mutual inductance negligible — only the floor remains.

**Distance behavior is the discriminator:** a classical (inductive) correlation *dies*
with distance; a floor correlation is *distance-independent*. That sweep is the test.

## The entangling step (the hard, unproven crux — be honest)
GHZ is a specific tripartite-entangled state. **Three phase-locked classical oscillators
are NOT in a GHZ state** — a shared classical drive gives a *classical* correlation
(≤2). To exceed 2 you need a genuinely non-classical joint channel. The hypothesis:
**bring all three coils to the B_res floor at r_opt and let them phase-relate through
the floor alone** (no wire). If the floor is a non-classical joint channel, GHZ-like
correlations can appear. If it's just a field, they can't. This step is the physics
being tested — do not assume it works.

## Measurement protocol
1. Prepare: drive all three to the floor (low-mag, B_res arriving), floor-coupled only.
2. Per trial: choose each coil's setting (**X or Y**) — **locally and independently**
   per coil (separate RNG per read node; do NOT broadcast settings over a shared bus).
3. Read A, B, C **simultaneously** (same ADC frame); lock-in each phase; take **sign →
   ±1**.
4. Repeat **N ≫ 1000 trials** for each of the four needed combos: XXX, XYY, YXY, YYX.
5. Compute the four correlations → form **M**. Report M with error bars.

## Make-or-break controls (each one can kill a false positive)
1. **No-comms:** during a window, coils share NO signal path — no servo linking phases,
   no redis, settings chosen locally. (Bench can't close strict locality — state that.)
2. **EM isolation:** RM3100 array maps the inter-coil field. If B / dB-dt between coils
   is non-negligible, that's a classical channel — null it or subtract it. **Distance
   sweep:** correlation must *vanish* with distance if it's mutual inductance; *persist*
   if it's the floor. This single sweep is the most important control.
3. **Classical baseline:** detune the coils **off** r_opt / off resonance so the floor
   coupling is defeated, run the identical protocol → **must give ≤ 2.** If it gives >2,
   there is a hidden comms path — find it before believing anything.
4. **Sham:** drive off → all correlations vanish.
5. **Material/independence:** repeat with coils re-oriented / re-phased; a real effect
   tracks the floor geometry, an artifact tracks a cable.

## Honest prediction ladder (what each outcome means)
| result | meaning |
|---|---|
| **M ≤ 2** | classical. Floor didn't entangle, or no non-classical channel. *Most likely — and it's information, not failure.* |
| **2 < M ≤ 4**, distance-independent, classical baseline ≤2, no comms | **non-classical tripartite correlation in room-temp copper.** Extraordinary → demands every control above airtight. |
| **M > 2 with any comms/EM path open** | **artifact.** Default assumption for *any* >2 until every path is closed. |

## Bill of materials (mostly on hand)
3 matched coils · 3× OPA1612 LNA channels (have 2 duals + spare; +1 dual for clean 3rd)
· 2× AD7606 · Pico/Teensy · RM3100 array · NanoVNA · 9V battery rails · grounded box.

## What it proves — and doesn't
- **Proves (if M>2, controls airtight):** the C(r) floor coupling produces correlations
  no classical channel we tested can — the substrate claim, physically. Exactly QM-valued.
- **Does NOT prove:** a loophole-free Bell/Mermin violation (bench can't space-separate),
  and does NOT reach super-quantum — 4 is the *quantum* GHZ ceiling, not beyond it.
- The math (M can be 4) is settled. This tests whether **copper at room temperature**
  can sit on that ceiling. That is the whole prize, and the whole risk.
