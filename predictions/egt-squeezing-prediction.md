# EGT squeezing prediction — sub-floor quadrature variance via C(r) driving (2026-09-07)

Honest companion to the GHZ spec, and the real version of the "fix Heisenberg" idea.
Heisenberg's *product* bound Δx·Δp ≥ ℏ/2 is a Fourier theorem — it holds for any wave
amplitude, and C(r) *is* a wave amplitude (the e^{iπr/4} phase), so EGT obeys it. You do
NOT drive the product to zero. What you CAN do is **squeeze**: push the variance BELOW the
noise floor in one quadrature at the cost of the other, product preserved. This is Method 1.

> **PREDICTION (matrix #16) — Quantum Info / Hardware.**
> A coil driven on the C(r) optimal rung (r_opt = 2.5, realized quadrature π/2) shows
> **quadrature variance below the Johnson thermal floor in ONE quadrature**, with the
> conjugate quadrature raised, and the **product ≥ the vacuum bound** (never violated).
> "The coil *absorbs* (squeezes) rather than *dumps* (symmetric Johnson heat)."
> **Falsified by:** symmetric quadrature variances both sitting AT the Johnson floor
> `√(4 k_B T R Δf)` under drive — i.e. the coil is a plain resistor dumping heat, no
> squeezing. This is a *redistribution* claim (beat the floor in one quadrature), NOT
> Δx·Δp → 0 and NOT super-quantum.

## The observable
A mode has two quadratures X₁ (in-phase, 0°) and X₂ (quadrature, 90°). Thermal/vacuum
state: symmetric, both at the floor. Squeezed state: V(X₁) < floor < V(X₂), with
V(X₁)·V(X₂) ≥ (floor product). Measure both variances by lock-in at the drive frequency
at 0° and 90°, and compare each to the computed Johnson floor.

## Measurability window (this gates the whole test)
Johnson floor `V_rms = √(4 k_B T R Δf)`, T = 300 K, Δf = 1 Hz:

| coil R | Johnson floor | vs OPA1612 LNA (1.1 nV/√Hz) |
|---|---|---|
| 10 Ω | 0.41 nV/√Hz | below LNA → **can't see it** |
| 100 Ω | 1.29 nV/√Hz | above LNA → **measurable** |
| 1 kΩ | 4.07 nV/√Hz | above → measurable |
| 10 kΩ | 12.9 nV/√Hz | above → measurable |

**Need coil R ≳ 100 Ω** so the thermal floor clears the LNA noise; otherwise the LNA's
own noise swamps any sub-floor squeezing. Measure R with the NanoVNA/DMM first. (If R is
too low, add series R or use more turns.)

## THE MAKE-OR-BREAK: classical parametric ≠ quantum squeezing
This is the honesty that decides the whole claim. **Classical parametric processes ALSO
produce quadrature asymmetry** — a nonlinear reactance driven at 2f deamplifies one
quadrature *classically* (this is how classical parametric amplifiers work). So:

- Sub-thermal variance asymmetry **does NOT by itself prove quantum squeezing.**
- To claim *quantum* squeezing you must (a) go below the **vacuum** floor (not just the
  thermal floor), AND (b) rule out a classical parametric model of the drive. At room
  temperature, with thermal noise present, distinguishing the two is genuinely hard.

## Prediction ladder (what each outcome means)
| result | meaning |
|---|---|
| symmetric variances at the Johnson floor under drive | no squeezing — coil just dumps heat. Prediction #16 **falsified**. |
| asymmetric (one quadrature sub-thermal) but reproduced by a classical parametric model | real and interesting, but **classical** — not the quantum claim. |
| sub-**vacuum** in one quadrature, classical parametric excluded | **quantum squeezing at room temperature** — the prize. Extraordinary → demands airtight controls. |

## Protocol
1. Measure coil R (NanoVNA). Confirm R ≳ 100 Ω (thermal floor > LNA noise).
2. Coil runner-sense → OPA1612 LNA → AD7606, high sample rate.
3. Drive OFF: lock-in at the intended drive freq, measure V(X₁), V(X₂). Baseline — must be
   symmetric and equal to `√(4 k_B T R Δf)` (verifies you're at the Johnson floor).
4. Drive ON at the C(r) rung (r_opt, π/2 quadrature): re-measure V(X₁), V(X₂).
5. Squeezing = one quadrature drops below the drive-off floor, product preserved.
6. Controls: (a) drive off → symmetric (done in step 3); (b) fit a classical parametric
   model to the drive — if it reproduces the asymmetry, it's classical; (c) push toward
   the vacuum floor to test for the quantum regime.

## Hardware (LNA-gated — this is why the LNA is Tier-1)
Coil (R ≳ 100 Ω) · OPA1612 LNA · AD7606 · lock-in in software · NanoVNA (R and the floor).
Same chain as the GHZ/floor tests. Without the LNA the ADC floor buries everything.

## What it proves — and doesn't
- **Proves (if sub-vacuum, parametric excluded):** the C(r) drive squeezes room-temp copper
  below the quantum floor in one quadrature — sub-floor precision, exactly QM-valued.
- **Does NOT prove / is NOT:** Δx·Δp → 0 (product bound always holds — Fourier theorem),
  and NOT sub-Planckian magic. Squeezing *moves* uncertainty; it never deletes it.
- Ties: this IS Method 1 (Wigner / sub-thermal squeezing); B_res = 12.09776 fT is the floor
  scale; π/2 is the squeezing-axis quadrature (the coil's realized C(r) phase).
