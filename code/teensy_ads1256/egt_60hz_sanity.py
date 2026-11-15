#!/usr/bin/env python3
"""
egt_60hz_sanity.py -- sanity-check the counts-to-fT calibration
against the 60 Hz mains ambient.

Logic:
  1. At REST (no drive), 60 Hz is purely ambient external pickup.
  2. V_60 = 2*pi*60 * A_eff * B_ambient  (Faraday, for the wire loop)
  3. counts_60 = V_60 / LSB
  4. Assume typical indoor B_60 = 0.1--1.0 uT, solve for A_eff
  5. Check if A_eff is physically reasonable for the runner circuit
  6. Compare coils-in vs bare-wire 60 Hz -- if similar, pickup is
     through the wire loop, not through the coil winding itself.

Also: if A_eff is known, the EXTERNAL-field calibration is:
  fT_per_count_ext(f) = LSB * 1e15 / (2*pi*f * A_eff)
This is DIFFERENT from the solenoid self-field calibration (via M).

Tonic, 2026-11-15.
"""
import json, math, numpy as np, os

MU0   = 4e-7 * math.pi
LSB_V = 4.657e-9
LSB_NV = 4.657
DATA_DIR = r"C:\Users\affor\egt_repo_rebuild\current_repo\code\teensy_ads1256\data"

# Solenoid self-field calibration constant (from egt_counts_to_ft.py)
K0_SELF = 1.194079e+08  # fT*Hz per count

def load_jsonl(path):
    ch = [[], [], []]
    ts = []
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            for i in range(3): ch[i].append(rec["ch"][i])
            ts.append(rec["t_us"])
    for i in range(3): ch[i] = np.array(ch[i], dtype=np.float64)
    return ch, np.array(ts, dtype=np.float64)

def spectral_amplitude(data, fs, target_freq, window=2):
    N = len(data)
    if target_freq > fs / 2:
        return 0.0, target_freq  # above Nyquist
    seg = data - data.mean()
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(N, d=1.0/fs)
    idx = int(round(target_freq * N / fs))
    lo = max(1, idx - window)
    hi = min(len(freqs) - 1, idx + window + 1)
    if hi <= lo:
        return 0.0, target_freq
    best_idx = np.argmax(spec[lo:hi]) + lo
    return spec[best_idx] / N * 2, freqs[best_idx]

def spectral_phase(data, fs, target_freq, window=2):
    N = len(data)
    seg = data - data.mean()
    spec = np.fft.rfft(seg)
    freqs = np.fft.rfftfreq(N, d=1.0/fs)
    idx = int(round(target_freq * N / fs))
    lo = max(1, idx - window)
    hi = min(len(spec) - 1, idx + window + 1)
    best_idx = np.argmax(np.abs(spec[lo:hi])) + lo
    return np.degrees(np.angle(spec[best_idx])) % 360

# ---- Load all datasets ----
FILES = {
    "coil_rest":   ("egt_rest1_20261115_092006.jsonl",   "Original rest (all coils)"),
    "coil_fwd":    ("egt_forward_20261115_092211.jsonl",  "Original forward (all coils)"),
    "bare_rest":   ("egt_bare_rest_20261115_110012.jsonl", "Bare wire rest (no coils)"),
    "bare_drive":  ("egt_bare_drive_20261115_110217.jsonl","Bare wire drive (no coils)"),
    "recon_rest":  ("egt_rest1_20261115_111818.jsonl",    "Reconnected rest"),
    "recon_fwd":   ("egt_forward_20261115_112023.jsonl",  "Reconnected forward"),
}

print("=" * 72)
print("  60 Hz SANITY CHECK -- counts-to-fT calibration")
print("  Tonic, 2026-11-15")
print("=" * 72)

data = {}
for tag, (fname, label) in FILES.items():
    path = os.path.join(DATA_DIR, fname)
    if os.path.exists(path):
        ch, ts = load_jsonl(path)
        dt = np.mean(np.diff(ts)) * 1e-6
        data[tag] = {"ch": ch, "ts": ts, "fs": 1/dt, "label": label}
        print(f"  Loaded {tag}: {len(ts)} rec, fs={1/dt:.1f}")

# ==== 1. 60 Hz SPECTRAL AMPLITUDES (all conditions) ====
print("\n" + "=" * 72)
print("  1. 60 Hz SPECTRAL AMPLITUDES (all conditions)")
print("=" * 72)
print(f"\n  {'condition':>14s}  {'c0 cts':>8s}  {'c1 cts':>8s}  {'c2 cts':>8s}  "
      f"{'c0 nV':>8s}  {'c1 nV':>8s}  {'c2 nV':>8s}")
results_60 = {}
for tag in ["coil_rest", "bare_rest", "recon_rest",
            "coil_fwd", "bare_drive", "recon_fwd"]:
    if tag not in data:
        continue
    d = data[tag]
    amps = []
    for ci in range(3):
        a, _ = spectral_amplitude(d["ch"][ci], d["fs"], 60)
        amps.append(a)
    results_60[tag] = amps
    print(f"  {tag:>14s}  {amps[0]:8.1f}  {amps[1]:8.1f}  {amps[2]:8.1f}  "
          f"{amps[0]*LSB_NV:8.1f}  {amps[1]*LSB_NV:8.1f}  {amps[2]*LSB_NV:8.1f}")

# ==== 2. COILS vs BARE at 60 Hz REST ====
print("\n" + "=" * 72)
print("  2. COILS vs BARE at 60 Hz REST -- is the coil adding pickup?")
print("=" * 72)
if "coil_rest" in results_60 and "bare_rest" in results_60:
    print(f"\n  {'':>3s}  {'coils-in':>9s}  {'bare':>9s}  {'ratio':>6s}  interpretation")
    for ci in range(3):
        c = results_60["coil_rest"][ci]
        b = results_60["bare_rest"][ci]
        r = c / b if b > 0 else float('inf')
        if abs(r - 1) < 0.15:
            interp = "SAME -- pickup is through wire loop, not coil"
        elif r > 1.15:
            interp = f"COIL ADDS {(r-1)*100:.0f}% -- winding picks up ambient too"
        else:
            interp = f"BARE HIGHER by {(1-r)*100:.0f}% -- coil shielding?"
        print(f"  c{ci}  {c:9.1f}  {b:9.1f}  {r:6.3f}  {interp}")

# ==== 3. 60 Hz PHASE GEOMETRY ====
print("\n" + "=" * 72)
print("  3. 60 Hz PHASE (all rest conditions)")
print("=" * 72)
for tag in ["coil_rest", "bare_rest", "recon_rest"]:
    if tag not in data:
        continue
    d = data[tag]
    phases = []
    for ci in range(3):
        ph = spectral_phase(d["ch"][ci], d["fs"], 60)
        phases.append(ph)
    sep01 = (phases[1] - phases[0]) % 360
    if sep01 > 180: sep01 -= 360
    sep12 = (phases[2] - phases[1]) % 360
    if sep12 > 180: sep12 -= 360
    print(f"  {tag:>12s}: c0={phases[0]:5.1f}  c1={phases[1]:5.1f}  c2={phases[2]:5.1f}  "
          f"c1-c0={sep01:+.1f}  c2-c1={sep12:+.1f}")

# ==== 4. SOLVE FOR A_eff ====
print("\n" + "=" * 72)
print("  4. EFFECTIVE LOOP AREA (from 60 Hz ambient)")
print("=" * 72)
print()
print("  At REST, 60 Hz is purely ambient external pickup (no drive).")
print("  V_60 = 2*pi*60 * A_eff * B_ambient")
print("  Solve: A_eff = V_60 / (2*pi*60 * B_ambient)")
print()

# Use bare-wire rest (cleanest -- no coil coupling at all)
tag_for_aeff = "bare_rest" if "bare_rest" in results_60 else "coil_rest"
amps_60 = results_60[tag_for_aeff]
avg_counts = np.mean(amps_60)
V_60 = avg_counts * LSB_V

B_assumptions = [
    (0.05e-6,  "0.05 uT (quiet room, far from wiring)"),
    (0.1e-6,   "0.1 uT  (typical residential)"),
    (0.3e-6,   "0.3 uT  (near desk/electronics)"),
    (0.5e-6,   "0.5 uT  (close to power strip)"),
    (1.0e-6,   "1.0 uT  (near transformer/motor)"),
    (3.0e-6,   "3.0 uT  (very close to source)"),
]

print(f"  Using {tag_for_aeff}: avg 60 Hz = {avg_counts:.1f} counts = {V_60*1e9:.1f} nV")
print(f"\n  {'assumed B_60':>36s}  {'A_eff cm^2':>10s}  {'A_eff dims':>14s}  physical?")
for B, label in B_assumptions:
    A_eff = V_60 / (2 * math.pi * 60 * B)
    A_cm2 = A_eff * 1e4
    side_cm = math.sqrt(A_cm2)
    # Is this physical for wires on a bench?
    if 5 < A_cm2 < 500:
        phys = "PLAUSIBLE"
    elif A_cm2 <= 5:
        phys = "too small"
    else:
        phys = "too large"
    print(f"  {label:>36s}  {A_cm2:10.1f}  {side_cm:.1f}x{side_cm:.1f} cm  {phys}")

# ==== 5. EXTERNAL-FIELD CALIBRATION ====
print("\n" + "=" * 72)
print("  5. EXTERNAL-FIELD CALIBRATION (if A_eff is known)")
print("=" * 72)
print()
print("  For external fields: fT_per_count_ext(f) = LSB*1e15 / (2*pi*f * A_eff)")
print("  This is INDEPENDENT of M -- it's the wire loop sensitivity.")
print()

# Pick the most plausible A_eff (0.3 uT assumption)
B_assumed = 0.3e-6
A_eff_best = V_60 / (2 * math.pi * 60 * B_assumed)
K0_ext = LSB_V * 1e15 / (2 * math.pi * A_eff_best)

print(f"  If B_ambient = 0.3 uT (plausible for bench near electronics):")
print(f"    A_eff = {A_eff_best*1e4:.1f} cm^2 = {A_eff_best:.6e} m^2")
print(f"    K0_ext = {K0_ext:.4e} fT*Hz per count")
print()
print(f"  {'freq':>6s}  {'self-field':>12s}  {'external':>12s}  {'ratio':>8s}")
print(f"  {'':>6s}  {'fT/count':>12s}  {'fT/count':>12s}  {'self/ext':>8s}")
for f in [4, 16, 20, 60, 120]:
    self_ft = K0_SELF / f
    ext_ft = K0_ext / f
    print(f"  {f:6.0f}  {self_ft:12.0f}  {ext_ft:12.0f}  {self_ft/ext_ft:8.2f}")

# ==== 6. HARMONICS CHECK ====
print("\n" + "=" * 72)
print("  6. HARMONIC RATIOS (60/120/180 Hz)")
print("=" * 72)
print("  A pure 60 Hz sine has no harmonics. Harmonics come from:")
print("  - Distorted mains waveform (expected: 120 Hz = 2nd, 180 Hz = 3rd)")
print("  - Nonlinear pickup (unlikely at these levels)")
print("  - The 60 Hz source itself (power lines radiate harmonics)")
print()
for tag in ["coil_rest", "bare_rest"]:
    if tag not in data:
        continue
    d = data[tag]
    print(f"  {tag}:")
    for ci in range(3):
        a60, _ = spectral_amplitude(d["ch"][ci], d["fs"], 60)
        a120, _ = spectral_amplitude(d["ch"][ci], d["fs"], 120)
        a180, _ = spectral_amplitude(d["ch"][ci], d["fs"], 180)
        print(f"    c{ci}: 60Hz={a60:.1f}  120Hz={a120:.1f} ({a120/a60*100:.1f}%)  "
              f"180Hz={a180:.1f} ({a180/a60*100:.1f}%)")

# ==== 7. BROADBAND CHECK ====
print("\n" + "=" * 72)
print("  7. SPECTRUM SHAPE: is the noise dominated by 60 Hz?")
print("=" * 72)
for tag in ["coil_rest", "bare_rest"]:
    if tag not in data:
        continue
    d = data[tag]
    print(f"\n  {tag}:")
    for ci in range(3):
        # Total std
        total_std = d["ch"][ci].std()
        # 60 Hz contribution to std: amp/sqrt(2) for a single sine
        a60, _ = spectral_amplitude(d["ch"][ci], d["fs"], 60)
        rms_60 = a60 / math.sqrt(2)
        frac_60 = rms_60 / total_std * 100
        # Top 5 peaks in spectrum
        N = len(d["ts"])
        dt = np.mean(np.diff(d["ts"])) * 1e-6
        seg = d["ch"][ci] - d["ch"][ci].mean()
        spec = np.abs(np.fft.rfft(seg))
        spec[0] = 0
        freqs = np.fft.rfftfreq(N, d=dt)
        peaks = []
        for j in range(2, len(spec)-2):
            if spec[j] > spec[j-1] and spec[j] > spec[j+1]:
                peaks.append((spec[j]/N*2, freqs[j]))
        peaks.sort(reverse=True)
        print(f"    c{ci}: total_std={total_std:.0f}  60Hz_rms={rms_60:.0f}  "
              f"({frac_60:.1f}% of total)")
        for rank, (amp, fr) in enumerate(peaks[:3]):
            print(f"         #{rank+1}: {fr:.1f} Hz  amp={amp:.1f} counts")

# ==== 8. VERDICT ====
print("\n" + "=" * 72)
print("  8. VERDICT")
print("=" * 72)

# Check coil vs bare ratio
if "coil_rest" in results_60 and "bare_rest" in results_60:
    ratios = [results_60["coil_rest"][i] / results_60["bare_rest"][i]
              for i in range(3)]
    avg_ratio = np.mean(ratios)

    print(f"""
  60 Hz coils-in / bare-wire ratio: {avg_ratio:.2f}
""")
    if avg_ratio > 1.3:
        print(f"  The coil winding ADDS ~{(avg_ratio-1)*100:.0f}% to 60 Hz pickup.")
        print(f"  This makes sense: the 64-turn coil is a ~{64*math.pi*(0.04445)**2*1e4:.0f} cm^2")
        print(f"  effective area (N*A_bore), much larger than the wire loop alone.")
        print(f"  The M-based self-field calibration applies to the coil's own")
        print(f"  60 Hz pickup (the coil acts as a search coil for ambient).")
    elif avg_ratio > 1.1:
        print(f"  Coil adds modest pickup ({(avg_ratio-1)*100:.0f}%). Mixed regime --")
        print(f"  both wire loop and coil winding contribute to 60 Hz.")
    else:
        print(f"  Coil and bare wire give SAME 60 Hz. Pickup is entirely through")
        print(f"  the wire loop geometry, not the coil winding. The M-based")
        print(f"  calibration may overestimate external-field sensitivity.")

    print(f"\n  Self-field cal K0 = {K0_SELF:.4e} fT*Hz/count")

    # If coil is adding pickup, we can estimate A_eff of the coil itself
    if avg_ratio > 1.1:
        # The coil's additional pickup is (ratio - 1) * bare_signal
        coil_extra_counts = np.mean(results_60["coil_rest"]) - np.mean(results_60["bare_rest"])
        V_coil_extra = coil_extra_counts * LSB_V
        # This is from the coil's 64-turn * A_bore effective area
        # V = 2*pi*f * N * A_bore * B (for a search coil)
        # B = V / (2*pi*f * N * A_bore)
        N_TURNS = 64
        A_bore = math.pi * 0.04445**2
        B_from_coil = V_coil_extra / (2 * math.pi * 60 * N_TURNS * A_bore)
        B_from_bare = np.mean(results_60["bare_rest"]) * LSB_V / (2 * math.pi * 60 * A_eff_best)

        print(f"\n  CROSS-CHECK via coil as search coil:")
        print(f"    Coil extra 60 Hz: {coil_extra_counts:.1f} counts = {V_coil_extra*1e9:.1f} nV")
        print(f"    N*A_bore = {N_TURNS} * {A_bore*1e4:.2f} cm^2 = {N_TURNS*A_bore*1e4:.0f} cm^2")
        print(f"    Implied B_60 from coil pickup: {B_from_coil*1e6:.3f} uT")
        print(f"    (For comparison: B_60 from bare wire @ A_eff={A_eff_best*1e4:.0f}cm^2: "
              f"{B_from_bare*1e6:.3f} uT)")
        if abs(B_from_coil - B_from_bare) / max(B_from_coil, B_from_bare) < 0.5:
            print(f"    -> CONSISTENT: both point to B_60 ~ {(B_from_coil+B_from_bare)/2*1e6:.2f} uT")
        else:
            print(f"    -> INCONSISTENT: coil and wire loop imply different B fields")
            print(f"       This suggests the M (mutual inductance) model or A_eff")
            print(f"       estimate needs refinement.")

print(f"""
  BOTTOM LINE:
  - The self-field calibration (K0 = {K0_SELF:.4e} fT*Hz) converts runner
    counts to the B field INSIDE the solenoid that would produce those
    counts via mutual inductance M.
  - For ambient/external fields, the conversion depends on HOW the signal
    enters: through the coil winding (N*A_bore ~ {64*math.pi*(0.04445)**2*1e4:.0f} cm^2) or
    through the wire loop (A_eff ~ tens of cm^2).
  - The 60 Hz data can discriminate: compare coils-in vs bare-wire.
""")

print("=" * 72)
print("  DONE")
print("=" * 72)
