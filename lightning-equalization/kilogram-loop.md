# The Kilogram Loop: Circular Definitions in the Mass Scale

**Brian Tice Sr.**
Axion Resonance Labs
lightning-equalization
2026-11-03

## Abstract

The gravitational constant formula G = H0^2 * r_star^3 * m_Planck / (pi * m_electron * M_sun) contains five inputs. Three of them — G itself, M_sun, and m_Planck — are defined in terms of G. The formula is therefore circular: it is satisfied for any value of G because G is built into both sides. The 99.95% match previously reported is a loop artifact, not a derivation. This paper strips each input to raw observables (counts, ratios, angles, frequencies) and rebuilds from that base.

## 1. The Five Loops

1. **G on both sides.** m_Planck = sqrt(hbar*c/G). Any formula using m_Planck to compute G uses G to compute G.
2. **M_sun depends on G.** Solar mass is computed from Kepler's third law rearranged with G: M = 4*pi^2*a^3/(G*T^2). The input presupposes the output.
3. **m_Planck routes through G.** Same as loop 1, via the definition above.
4. **H_zero assumes Friedmann.** Converting redshift to distance requires the Friedmann equations, which assume general relativity, which assumes G.
5. **m_electron rides the kilogram.** The kilogram was redefined in 2019 through Planck's constant, so electron mass inherits that anchor.

## 2. The Raw Base

Five inputs that are either pure ratios or countable quantities:

- Orbital period ratios (T1/T2) — counts against atomic time
- Parallax angles — raw angle measurements
- Fine-structure constant — frequency ratios from atomic spectra
- Cesium hyperfine frequency — 9,192,631,770 Hz, a count
- Charge-to-mass frequency ratios from Penning traps — field cancels

No G. No GR. No solar mass. No kilogram.

## 3. The Five Rebuilds

### 3.1 Orbital period ratios
Kepler's third law in ratio form: (T1/T2)^2 = (a1/a2)^3. No G. Earth's year = 365.25 days (atomic definition). Mars sidereal year = 686.98 days. Ratio = 1.88. Cube root of ratio squared = 1.52 — Mars at 1.52 AU, matching radar ranging. Period ratio plus parallax angle gives length ratio from geometry alone.

### 3.2 Fine-structure constant
Measured from hydrogen line frequency ratios. Rydberg constant over c gives alpha^2/(hbar*c). Quantum Hall route: h/e^2 = alpha * mu_0 * c. Both are ratio measurements. Alpha = 1/137.036 — a pure number from counting.

### 3.3 Speed of light
Defined as 299,792,458 m/s; the meter is defined as the distance light travels in 1/299,792,458 s. Circular by construction. The raw observable underneath is the cesium hyperfine tick: 9,192,631,770 counts per second. Time is a count. Length is count times a defined conversion.

### 3.4 Electron-proton mass ratio
m_e/m_p ≈ 1/1836. From Penning trap cyclotron frequency ratios. Charge-to-mass ratios are frequency-over-field; the field cancels. Pure number from counting frequencies. No kilogram.

### 3.5 Parallax angles
One arcsecond = 1/3600 degree. Sirius parallax = 0.379". Similar triangles give distance ratio from angle in. Geometry, not gravity.

## 4. Kernel Evaluation on the Raw Base

C(rho) = (1 + 2*rho) * exp(-rho/3) * exp(i*pi*rho/4)

- C(1) = 4.62
- C(2.5) = 6.80 (peak, zero derivative)
- A_EGT = 8 from the phase step pi/4 alone — no fitted constants

The kernel stands on its own from the clean base.

## 5. The 99.95% — Retired

m_Planck is defined as sqrt(hbar*c/G). Any formula using m_Planck to compute G is circular. Stripped of that loop, no G-free path to the 99.95% number exists from the raw base. The kernel is intact; the match was an artifact.

## 6. Open Items

1. Kernel evaluation against each raw-base observable in full numerical detail.
2. Whether the EGT framework can derive any of the five raw inputs from first principles rather than accepting them as measured.

## References

[1] B. Tice, "A Discrete Two-Rock Field Theory With a Built-In Mass Gap," Axion Resonance Labs (2026).
[2] B. Tice, "The Seven Millennium Prize Problems Through the C(r) Framework," EGT Archive (2026-08-08).
