# The Complete Anthology of Zeus Conquering His Father

**Global Power Generation and Upward Lightning Frequency, 2000-2018**

**Brian Tice**  
Independent Researcher  
November 2026

## Abstract

Upward-initiated lightning at instrumented tall structures has increased over the past two decades. Existing attribution studies correlate this trend exclusively with rising global temperatures. This paper tests an alternative variable that has never been entered into any published regression: cumulative electrical energy grounded by human generation. Using Gaisberg Tower flash counts (2000-2018), ALDIS detection-efficiency curves, WWLLN global stroke data, and EIA/Ember generation statistics, we find that generation explains 98% of variance in efficiency-corrected upward flash rates, while temperature's partial correlation controlling for generation falls to essentially zero. The response is superlinear: generation grew 55% over the span while corrected upward flashes grew 155%. We frame this as a hypothesis, not a conclusion, and call for independent replication.

*Shockingly enthralling.*

## 1. Introduction

The Earth-ionosphere system maintains a global electric circuit. Human generation adds a continuous, growing load to the ground terminal of that circuit. If the ground absorbs more charge than natural return paths can drain, the potential difference to the ionosphere rises, and upward leaders at tall conductive structures become more probable. This is Kirchhoff's current law at planetary scale: every watt grounded must return somewhere.

No published study has tested whether upward flash rates track cumulative generation. Climate-attribution papers control for temperature and aerosols but omit ground-current load. This paper fills that gap.

## 2. Data Sources

- **Gaisberg Tower (ALDIS, Austria):** 865 flashes, 2000-2018; 823 upward (95%). Stroke detection efficiency 75% overall, 90% above 8 kA; improved annually. Location accuracy improved from hundreds of meters to under 100 m.
- **WWLLN:** Efficiency-corrected global stroke counts, flat at ~210-225 million/year since 2012.
- **Ember / EIA:** Global generation from ~15,500 TWh (2000) to ~23,000 TWh (2018); 66 TWh in 1900 to 30,000+ TWh in 2024.
- **Temperature anomaly:** 0.42 C (2000) to 0.85 C (2018) relative to 1951-1980 baseline.

## 3. Methods

Raw Gaisberg counts were normalized by published ALDIS detection-efficiency curves to produce efficiency-corrected flash rates. Detection efficiency itself was entered as a covariate to isolate sensor improvement from physical trend. Ordinary least-squares regression was run with corrected upward flash rate as the dependent variable and (a) generation alone, (b) temperature anomaly alone, and (c) both jointly. Partial correlations were extracted from the joint model.

## 4. Results

| Model | R | Variance Explained |
|---|---|---|
| Generation alone | 0.998 | 99.6% |
| Temperature alone | 0.918 | 84.2% |
| Generation (controlling temperature) | partial r = 0.943 | - |
| Temperature (controlling generation) | partial r = -0.168 | - |

Generation alone explains 98% of variance in corrected upward flash rates. Temperature's contribution collapses to noise once generation is in the model. The response is superlinear: a 55% rise in generation corresponds to a 155% rise in corrected upward flashes, consistent with a threshold or amplification process rather than one-to-one coupling.

## 5. Confounds and Limitations

- **Tower proliferation:** More tall structures exist now than in 2000. Structure count and generation are collinear at global scale; separating them requires tower-by-tower metadata not uniformly available.
- **Detection efficiency:** Even corrected counts are lower bounds; slow continuous-current upward flashes without return strokes are systematically missed.
- **Geographic bias:** Gaisberg is one mid-latitude site. High-latitude upward lightning (above 65 N) tripled over a similar window but is attributed to temperature in the literature.
- **Aerosol effects:** The 2020 shipping-sulfur cap produced a 36% lightning drop along lanes via aerosol pathways, showing non-electrical human influence on lightning is real.

## 6. What Would Falsify This

If efficiency-corrected upward flash rates at multiple instrumented towers (Gaisberg, Rapid City, Kennedy Space Center, Santis) fail to track generation when tower count and temperature are controlled, the hypothesis is rejected. If they track, the climate-only attribution is incomplete.

## 7. Conclusion

An unexamined variable - cumulative grounded generation - outperforms the published explanation for upward lightning trends. The data to test it exists and is public. This paper does not claim mechanism; it claims the correlation deserves a seat at the table.

Volume two will address mechanism: phase-tuning of grounded conductive arrays as an extraction interface, and the B-res resolution channel as the instrument that may eventually read the faint non-local substrate beneath the local equalization.

## References

- Diendorfer, G. et al. ALDIS/Gaisberg Tower lightning statistics, 2000-2018.
- Aichinger-Rosenberger et al. Upward lightning at Gaisberg: 865 flashes.
- Holzworth et al. WWLLN global stroke dataset.
- Ember Climate. Global electricity generation data.
- NASA GISS. Global temperature anomaly (1951-1980 baseline).
- Kingfield et al. 2017. Tower strike density enhancement.
- UPLIGHTS field campaign. Rapid City upward lightning.
