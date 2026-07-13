# empirical/ — Reproduction of Measured Anomalies

Papers claiming that EGT reproduces existing physical measurements. These are the load-bearing empirical anchors — the framework's claim to be more than mathematical elegance rests on these.

## Files

- **`pioneer-anomaly.pdf`** — reproduces the observed constant sunward deceleration of Pioneer 10/11: `a_P ≈ 8.74 × 10⁻¹⁰ m/s²`. EGT formula: `a_EGT = H₀·c × G_M` with `G_M = 1.324`. Starting from `H₀·c ≈ 6.6 × 10⁻¹⁰ m/s²` puts the argument in the same order-of-magnitude neighborhood as Milgrom's MOND acceleration scale, which is not an accident and is worth exploring further.
  - **Known gap:** `G_M = 1.324` is called "self-derived from geometric constants" but the derivation is not shown in the current paper. Its value is exactly `a_P,obs / (H₀·c)`, meaning it is currently a one-parameter fit. Fixing this is a priority.
- **`atomic-clock-proof.pdf`** — predicts a Cs-Rb differential frequency shift of `Δf/f = 2.99 × 10⁻¹⁴` correlated with the Earth's rotational alignment relative to the B_res field. Reported to match empirical calibration behavior of the IEN-CsF1 clock (Levi et al. 2004) — an independent measurement not associated with EGT.
- **`atomic-clock-differential-sensitivity.pdf`** — expanded / revised version of the atomic clock argument.

## Additional empirical anchors mentioned in the memory but not yet compiled here

- **B_res = 12.09776 fT match to Levi et al. 2004.** Presented in `theory/egt-main.tex`; if kept as an empirical anchor it should have its own paper in this folder.
- **Earth LOD 383.50-day signal at 9.0% SNR.** Referenced in project memory as predicted before measurement and confirmed in IERS EOP data 1962-2025. Corresponding paper is being imported from Overleaf (`lod_psd_analysis`). Should land here once verified.

## What is *not* claimed here

- The Dragon's Eye / S24 Ultra silicon coherence measurements from the June 2026 CSV data are NOT included in this folder. The data actually collected (CV metric on two VPS nodes) does not match the memory-file claim of "0.8024 wall on i9 + Snapdragon." That set of claims is being re-scoped based on what the data actually supports (see `code/` for the raw measurement infrastructure and drafts folder for pending revisions).
