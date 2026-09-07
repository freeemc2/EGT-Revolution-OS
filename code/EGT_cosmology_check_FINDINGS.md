# EGT cosmology check — G and Ω_m from C(r), honest scorecard (2026-09-07)

Reproduced and stress-tested Brian's cosmological math (from `universe_circuit_clean.py`)
under his own razor: "no assumption built on an assumption." Razor turned on EGT too.
Scripts: `omega_and_G_check.py`, `derive_geometry_spines.py` (+ `derive_gravity_from_Cr.py`).

## Results reproduced (real, from his code)
- **G = [H₀²·r*³·√(ħc)/(π·mₑ·GM_sun)]² = 6.681e-11 → 99.9% of measured**, using only
  G-free inputs (H₀, r*, ħ, c, mₑ, GM_sun). The `m_Planck=√(ħc/G)` "circularity"
  is COSMETIC and removable — written with the directly-measured GM_sun there is
  zero G on the RHS. So it is a genuine prediction, not a self-consistency loop.
- **Ω_m = 1/π = 0.318310 vs Planck 0.3153 ± 0.0073 → 0.41σ.** The reduction from the
  spin formula is CIRCULARITY-FREE: G, H, R all cancel; result is exactly 1/π for
  ANY inputs (verified numerically). Cross-checks 4 CMB surveys within ~1.3σ.
  Falsifiable: CMB-S4 (~2028) measures Ω_m to ±0.002.

## The two OPEN spines (what stands between this and a submittable paper)
Both numbers are real; neither geometric derivation is closed yet. These are the
hinges — honest research gaps, not fits gone wrong.

### c1 — the spin formula's extra 1/π (vs standard critical mass factor 2)
- Ω_m = 1/π ⇔ the spin formula `M = H²R³/(2πG)` carries a factor π vs standard
  `M_crit = H²R³/(2G)`. So 1/π lives entirely in that 2π.
- **Candidate mechanism (NOT proof):** a HALF-WAVE-RECTIFIED (one-way) coupling over
  the C(r) phase cycle gives exactly `(1/2π)∫₀^π sinθ dθ = 1/π`. Physically plausible
  (the coil is an INVERSE amplifier / one-way floor-puller) and internally consistent
  with the coil's κ = 2/π = ⟨|cos|⟩ (full-wave) — Ω_m is half that, same family.
- **To close:** show C(r) NECESSITATES one-way/half-wave coupling from its structure,
  not because it yields 1/π. Until then Ω_m=1/π is a striking match on an unproven step.

### c2 — the G form's exponent / source count
- `m_Planck/mₑ ≈ 2.4e22` is labeled the "source count" (EM sources to bridge the
  gravity/EM gap). The form is dimensionally correct and lands numerically.
- **Open:** the exponent (the m_Planck bridge / the ^2) comes from solving the
  self-consistency, NOT from a first-principles argument that forces it. Same wall
  `derive_gravity_from_Cr.py` hit: the ~36-OOM α_EM/α_G gap is matched, not yet bridged.
- **To close:** a mechanism showing gravity = collective EM coupling of exactly that
  many C(r) sources at the impedance-matched volume, forcing the exponent.

## Bottom line
Turning the razor on EGT's own work: the parsimony case is strong (fewer entities than
ΛCDM's inflation+dark matter+dark energy stack), and two numbers land hard (G 99.9%,
Ω_m 0.41σ). But "cleaner + matches" is not "derived." Close c1 (half-wave from the
operator) or c2 (source-count mechanism) and that half is paper-ready. Matches alone
are not the paper — the geometry spine is. Note also: the CMB *temperature* (2.725 K)
is NOT derived here; it is used as input. What this touches is Ω_m, which the CMB measures.
