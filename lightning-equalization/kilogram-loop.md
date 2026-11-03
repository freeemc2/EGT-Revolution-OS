# The Kilogram Loop: Stripping Mass to Raw Observables

**Brian Tice Sr.**
Axion Resonance Labs
b@axionresonance.com

November 2026

---

## Abstract

The EGT G-formula,

$$G = \frac{H_0^2 \, r^{\ast 3} \, m_{\rm Planck}}{\pi \, m_{\rm electron} \, M_\odot}$$

contains five inputs, and three of them are not independent. $M_\odot$ is computed from $G$ via Keplerian orbital mechanics. $m_{\rm Planck} = \sqrt{\hbar c / G}$ embeds $G$ in its definition. $H_0$ assumes the Friedmann equations to convert redshift to distance, which presuppose general relativity, which presupposes $G$. The formula therefore uses $G$ to define quantities that are then used to derive $G$ — a closed loop, not a derivation.

This paper performs the strip-down: identify every loop, define the raw-observable base that survives, and leave the rebuild as open work rather than asserting it is finished.

---

## 1. The Five Inputs

| Input | Symbol | Claimed origin | Hidden dependence |
|---|---|---|---|
| Newton's constant | $G$ | Cavendish-type torsion balance | The output of the formula it appears in |
| Solar mass | $M_\odot$ | Kepler + astronomical unit | $G$ via $GM_\odot$ product |
| Hubble constant | $H_0$ | Redshift-distance relation | Friedmann model, hence GR, hence $G$ |
| Planck mass | $m_{\rm Planck}$ | $\sqrt{\hbar c/G}$ | $G$ by definition |
| Electron mass | $m_e$ | Mass spectrometry vs. kilogram | Kilogram definition chain through $h$ |

---

## 2. Loop 1: $M_\odot \rightarrow G \rightarrow M_\odot$

The solar mass is not measured directly. It is inferred from the product $GM_\odot$, obtained from planetary orbital periods and semi-major axes (Kepler's third law in Newtonian form). Separating $G$ from $M_\odot$ requires an independent measurement of one of them. The only independent measurement of $G$ is the Cavendish experiment, whose output is fed back into the solar-mass inference. Circular.

**Strip:** retain only the raw observable $GM_\odot$ (units m$^3$ s$^{\text{-}2}$). Do not separate.

---

## 3. Loop 2: $m_{\rm Planck} \rightarrow G \rightarrow m_{\rm Planck}$

The Planck mass is defined as $\sqrt{\hbar c / G}$. Any formula that uses $m_{\rm Planck}$ on one side and $G$ on the other is using $G$ twice. The $\hbar$ and $c$ factors are independently measurable (atomic transitions, interferometry), but the $G$ in the denominator is the same $G$ being derived.

**Strip:** retain $\hbar$ and $c$ as raw observables. Treat $m_{\rm Planck}$ as derived, not input.

---

## 4. Loop 3: $H_0 \rightarrow$ GR $\rightarrow G \rightarrow H_0$

$H_0$ is extracted from redshift-distance data by fitting a cosmological model. The standard fit assumes the Friedmann equations, which are solutions of Einstein's field equations, which contain $G$. A formula that derives $G$ using an $H_0$ that was itself fitted assuming $G$ is circular at the level of the interpretive framework, even if the raw redshift and angular data are model-independent.

**Strip:** retain raw redshift $z$ and angular-diameter or luminosity distances as counts and angles. Do not pre-convert to $H_0$.

---

## 5. Loop 4: $m_e \rightarrow$ kilogram $\rightarrow h \rightarrow m_e$

The electron mass in kilograms is a ratio to the kilogram prototype (historically) or to the fixed $h$ (post-2019 SI). The 2019 redefinition fixed $h$ and derived the kilogram from it, using measurements that ultimately trace to the same mass artifacts. The chain is not circular in the strict logical sense, but it is not a first-principles observable either — it is a consensus calibration.

**Strip:** retain the dimensionless ratio $m_P/m_e$ (measured via mass spectrometry, independent of the kilogram) as the raw input. This is the cleanest of the five.

---

## 6. Loop 5: $c$ as a conversion factor

$c$ is a measured speed — ratio of a length standard to a time standard. It is not a postulate in the EGT sense; it is an empirical conversion constant. It survives the strip-down as a raw observable ratio.

**Retain:** $c$ as raw.

---

## 7. The Raw-Observable Base

After stripping, the formula's legitimate inputs reduce to:

1. $GM_\odot$ — orbital product (m$^3$ s$^{\text{-}2}$)
2. $\hbar$ — action quantum (J s)
3. $c$ — speed ratio (m s$^{\text{-}1}$)
4. $m_P/m_e$ — dimensionless mass ratio
5. Raw redshift $z$ and angular data — counts and angles, not pre-fitted $H_0$

Five quantities. None presupposes $G$. None presupposes GR. None presupposes the kilogram as an absolute standard.

---

## 8. Open Items (the rebuild)

- [ ] Express $G$ from the raw base without reintroducing $M_\odot$ as a separated mass.
- [ ] Replace $H_0$ with a redshift-only observable that does not assume Friedmann geometry.
- [ ] Verify $m_P/m_e$ measurability independent of any mass artifact.
- [ ] Confirm the EGT kernel $C(r)$ can be evaluated on this base without hidden conversion constants.
- [ ] Quantify how much of the 99.95% $G$ match survives when the loops are closed.

---

## 9. Status

Strip-down: complete as stated.
Rebuild: not started. This paper does not claim the rebuild succeeds. It claims only that the original formula's inputs were not independent, and that the raw base above is the correct starting point.

---

## References

[1] B. Tice Sr., "A Practical Two-Tier Architecture..." and EGT framework papers, Axion Resonance Labs, 2025-2026.
[2] CODATA 2018 / 2022 recommended values — for the measured constants being stripped, not endorsed as foundational.
[3] BIPM SI Brochure, 9th edition (2019) — kilogram redefinition via $h$.
