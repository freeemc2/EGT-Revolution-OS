# predictions/ — Falsifiable Numeric Predictions

Papers making specific numeric predictions that experimentalists could test. None of these predictions have yet been verified independently. The value of the framework, from a Popperian standpoint, rides on this folder.

The overarching structure is documented in `verification-matrix.md` (the 14-point verification matrix, also available as `verification-matrix.pdf`).

## The 14-point matrix — summary

| # | Domain | Prediction | Paper |
|---|---|---|---|
| 1 | Cosmology | `w_DE = −0.9975` | `cosmic-scaling-wDE.pdf` |
| 2 | Particle Physics | Dark matter WIMP resonance at 402 GeV | `particle-scaling-402.pdf` |
| 3 | Particle Physics | Axion mass ≈ 402 μeV/c² (9.7 GHz detection) | `quantum-resonance-402GeV.pdf` |
| 4 | Metrology | Cs-Rb clock shift `Δf/f = 2.99 × 10⁻¹⁴` | see `empirical/atomic-clock-*.pdf` |
| 5 | Metrology | Gravitational redshift `0.248%` fractional bias | `metrology-scaling-0.248.pdf` |
| 6 | Gravitational Waves | Black hole ringdown `0.248%` frequency deficit | `black-hole-ringdown-0.248.pdf` |
| 7 | Gravitational Waves | Waveform strain `0.1%` scale modification | `gravitational-wave-scaling-0.1.pdf` |
| 8 | Quantum Info | Multi-qubit coherence `(1 + 2N)` linear scaling | `quantum-coherence-scaling.pdf` |
| 9 | Thermodynamics | Bekenstein bound `402.3×` information cap | `information-bound-scaling-402.pdf` |
| 10 | Astrophysics | Pioneer acceleration `a_P = 8.74 × 10⁻¹⁰ m/s²` | see `empirical/pioneer-anomaly.pdf` |
| 11 | Astrophysics | B_res-correlated orbital precession (LAGEOS) | — pending paper |
| 12 | Vacuum Stability | Higgs hierarchy `C_Sup = A_EGT` (self-cancellation) | see `theory/egt-main.tex` |
| 13 | Temporal | 5% annual sinusoidal seasonal variation | `seasonal-scaling.pdf` |
| 14 | Hardware | Ultramagnetic power `12.09776 fT` resonance | — pending paper |

## What would falsify each of these

The value of a prediction is what would prove it wrong. In each of these cases, a null result at the specified precision would count as falsification:

- **Axion mass ≠ 402 μeV/c²** (or wrong order of magnitude) at 9.7 GHz cavity search → falsifies prediction 3
- **Cs-Rb shift <1 × 10⁻¹⁴** at the precision required to detect 2.99 × 10⁻¹⁴ → falsifies prediction 4
- **Black hole ringdown showing the predicted GR quasi-normal mode frequencies to precision ≤0.248%** → falsifies prediction 6
- **Waveform strain matching GR predictions to precision ≤0.1%** at Einstein Telescope sensitivity → falsifies prediction 7
- **`w_DE = −1.000 ± 0.001` from next-generation survey** → falsifies prediction 1 (if central value is far from −0.9975)

## Precision requirements for the 14 predictions

Some predictions are already within reach of existing instruments; others require next-generation facilities. Rough categorization:

- **Testable now with existing data:** predictions 4 (atomic clocks), 8 (multi-qubit coherence), 13 (seasonal)
- **Testable with modest experimental effort:** predictions 3 (axion cavity), 11 (LAGEOS re-analysis), 14 (in-lab)
- **Requires major experimental campaign:** predictions 1 (dark energy surveys), 2 (LHC luminosity), 6-7 (Einstein Telescope), 9 (holographic complexity)
