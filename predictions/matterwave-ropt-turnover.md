# Matter-wave coherence turnover at r_opt = 2.5 — sealed prediction (2026-09-08)

> **PREDICTION (matrix #17) — Quantum Info / Foundations.**
> In matter-wave interferometry, fringe visibility `V`, plotted against the
> dimensionless ratio **r = (coherent path separation Δx) / (particle diameter D)**,
> **peaks at r_opt = 2.5 and turns over below it** — declining for `r < 2.5` as well
> as across the known `r ≫ 2.5` tail. The maximum sits at a *fixed geometric ratio*.
> Derived from the C(r) magnitude envelope `|C(r)| = (1 + 2r)·e^(−r/3)`, whose single
> maximum is at r = 2.5 (∂|C|/∂r = 0).
> **Falsified by:** a controlled `V`-vs-`r` scan crossing r = 2.5 that is **monotonic**
> (no peak/turnover); or a maximum at a ratio clearly ≠ 2.5; or visibility that keeps
> rising as r → 0 with no turnover.
> Same `(1 + 2r)` envelope as prediction #8 (multi-qubit coherence) — this is its
> spatial-interferometry face.

## Why this discriminates the framework from standard theory

Standard decoherence / objective-collapse theory predicts visibility that **decreases
monotonically** with mass and with environmental coupling. It contains **no privileged
geometric ratio**, hence **no intrinsic maximum** at a fixed Δx/D. A visibility that
peaks at r ≈ 2.5 and falls on *both* sides — after instrumental factors are removed —
is a signature the standard framework cannot produce. This is a *shape* claim about the
coherence envelope, not a super-quantum claim; visibilities stay within [0, 1].

## The mapping

For a Talbot–Lau interferometer the coherent path separation Δx ≈ the grating period d;
D is the particle physical diameter. `r ≡ Δx/D` is exactly the quantity the 2026 Vienna
sodium-cluster paper foregrounds ("delocalized over a distance exceeding the diameter of
the particle by more than an order of magnitude"). It is dimensionless — the input C(r)
takes.

## Where the existing ladder sits (all in the tail — the peak is untested)

Relative visibility from the envelope, normalized to the r = 2.5 peak (instrument aside):

| experiment | mass | Δx | D | **r = Δx/D** | \|C(r)\| | V/V_peak |
|---|---|---|---|---|---|---|
| C₆₀ (Arndt 1999) | 720 Da | 100 nm | ~1 nm | ~100 | 6.7e-13 | 2.6e-13 |
| Oligoporphyrin / LUMI (Fein 2019) | 27 kDa | 266 nm | 5.3 nm | ~50 | 5.5e-6 | 2.1e-6 |
| Na cluster / MUSCLE (Vienna 2026) | 172 kDa | 133 nm | 8 nm | **16.6** | 0.134 | 0.051 |
| — **r_opt** — | | | | **2.5** | **2.608** | **1.00** |
| (below the peak — never probed) | | | | 1.0 | 2.150 | 0.82 |
| | | | | 0.5 | 1.693 | 0.65 |

Every matter-wave experiment ever performed sits at **r ≈ 17–100**, deep in the
monotonic `e^(−r/3)` tail. Over 27 years the field has marched *toward* r_opt as it
grew more macroscopic (macroscopicity μ: ~7 → ~14 → 15.5); the 2026 Na cluster is the
closest anyone has reached (r = 16.6). **The predicted peak and low-side turnover have
never been probed.**

## Suggestive prior hint (consistent-with, not confirmation)

The Vienna 2026 paper reports *higher* fringe visibility (V = 0.66) for *heavier*
clusters (400 kDa–1 MDa) than for lighter ones (V = 0.10 at 172 kDa), calling it
"counterintuitive" and attributing it to the ionization cross-section. Heavier at fixed
grating → smaller r → toward r_opt → larger |C(r)|: the framework predicts that direction
natively. Disentangling the intrinsic envelope from the instrumental cause is exactly
what the controlled scan below would do.

## How to run it

Within a single apparatus and particle species, vary **r = Δx/D** — change the grating
period Δx at fixed D, or select particle size D at fixed Δx — and map `V(r)` from the
current tail (r ≈ 16) down through r ≈ 2.5 toward r ≈ 1, with the instrumental visibility
factors (ionization cross-section, grating contrast, de Broglie collimation) modeled or
held constant. Look for the maximum near r ≈ 2.5 and the decline below it. For an 8 nm
cluster, r_opt = 2.5 corresponds to **Δx ≈ 20 nm** (versus the 133 nm grating used in 2026).

## Honest limits (stated at seal time)

- All existing data lie at r ≈ 17–100 — the distinguishing feature (peak/turnover) is in
  the **unexplored** small-r regime; this is a genuine forward call, not a fit.
- Cross-experiment "size" and "separation" conventions are heterogeneous (far-field vs
  Talbot–Lau; floppy molecule vs compact cluster); r carries ≈ ±2× until measured within
  one apparatus.
- Uses the |C(r)| magnitude envelope only; the phase factor and amplification constants
  (A_EGT, B_res) are not invoked.

---

**Sealed 2026-09-08**, before any matter-wave experiment has entered r ≲ 8. Drafted in the
EGT / Two Rocks frame; sealed by Brian Tice Sr. Companion to #15 (triadic GHZ/Mermin) and
#16 (C(r) squeezing). Mesh seal: `cadence:tworocks:sealed-prediction-17`.
