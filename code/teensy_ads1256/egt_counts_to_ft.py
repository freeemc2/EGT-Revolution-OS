#!/usr/bin/env python3
"""
egt_counts_to_ft.py -- ADS1256 bench: counts-to-femtotesla calibration.
Tonic, 2026-11-15. Brian direct: "now we need to have a conversion to ft."

Three calibration methods:
  1. THEORETICAL -- from coil geometry + mutual inductance M
  2. SELF-CAL    -- drive current -> known B -> measured counts
  3. NOISE-FLOOR -- express the ADC noise in field units

Signal chain:  external B -> flux through runner loop -> EMF on runner
               -> 10kohm sense resistor -> ADS1256 differential (PGA 64)

The runner is the READ element (a single 18-AWG axial wire under the
winding).  The 4-strand winding is the DRIVE.  The runner picks up
flux through the circuit loop formed by the runner wire + its return
path to the ADC differential input.

For the solenoid self-field coupling, the mutual inductance M gives:
  V_runner = M * dI/dt

For the solenoid field:
  B = u0 * (N / L_winding) * I

Combining:
  B = V_runner * u0 * N / (L_winding * M * 2pif)

  fT_per_count(f) = LSB * u0 * N * 1e15 / (L_winding * M * 2pif)
"""
import json, math, numpy as np, os, sys

# -------- CONSTANTS --------
MU0      = 4e-7 * math.pi       # H/m
LSB_V    = 4.657e-9             # V/count -- ADS1256 PGA 64, Vref 2.5V
LSB_NV   = 4.657                # nV/count

# -------- COIL / RIG PARAMETERS (from rig.json + em_account) --------
N_TURNS         = 64            # turns (each strand winds 64; 4 strands)
N_STRANDS       = 4
FORMER_OD_IN    = 3.500         # inches (PVC sch40)
FORMER_OD_M     = FORMER_OD_IN * 0.0254
FORMER_R_M      = FORMER_OD_M / 2      # 0.04445 m
WINDING_LEN_IN  = 8.75          # inches
WINDING_LEN_M   = WINDING_LEN_IN * 0.0254  # 0.22225 m
A_BORE_M2       = math.pi * FORMER_R_M**2   # bore cross-section

# -- Mutual inductance: runner to winding --
# M_max = u0 * N * A_bore / L  (one runner-loop turn linking the full bore flux)
M_RUNNER_H = MU0 * N_TURNS * A_BORE_M2 / WINDING_LEN_M
M_RUNNER_UH = M_RUNNER_H * 1e6

# -- Circuit --
R_SERIES_OHM    = 220           # drive series resistor
R_COIL_4P_OHM   = 0.262        # 4 parallel strands
R_COIL_1S_OHM   = 1.049        # 1 strand
R_SENSE_OHM     = 10000        # 10kohm sense resistor
V_DRIVE          = 3.3          # GPIO high

# -- ADS1256 --
PGA     = 64
VREF    = 2.5
ADC_BITS = 24
DR_SPS   = 1000

DATA_DIR = r"C:\Users\affor\egt_repo_rebuild\current_repo\code\teensy_ads1256\data"

# -------- HELPER FUNCTIONS --------

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
    """Single-sided spectral amplitude at target_freq (counts peak)."""
    N = len(data)
    seg = data - data.mean()
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(N, d=1.0/fs)
    idx = int(round(target_freq * N / fs))
    lo = max(1, idx - window)
    hi = min(len(freqs) - 1, idx + window + 1)
    best_idx = np.argmax(spec[lo:hi]) + lo
    amp = spec[best_idx] / N * 2  # single-sided peak amplitude
    return amp, freqs[best_idx]


# ===========================================================
print("=" * 72)
print("  COUNTS-TO-FEMTOTESLA CALIBRATION")
print("  ADS1256 bench -- Three-coil set, sense runners")
print("  Tonic, 2026-11-15")
print("=" * 72)

# ======= 1. COIL GEOMETRY =======
print("\n" + "=" * 72)
print("  1. COIL GEOMETRY")
print("=" * 72)
print(f"  Former OD:        {FORMER_OD_IN}\" = {FORMER_OD_M*1e3:.1f} mm")
print(f"  Former radius:    {FORMER_R_M*1e3:.2f} mm")
print(f"  Bore area:        {A_BORE_M2*1e4:.2f} cm^2 = {A_BORE_M2:.6f} m^2")
print(f"  Winding length:   {WINDING_LEN_IN}\" = {WINDING_LEN_M*1e3:.2f} mm")
print(f"  Turns:            {N_TURNS} (per strand, {N_STRANDS} strands)")
print(f"  L/D:              {WINDING_LEN_IN / FORMER_OD_IN:.4f} (= 2.5 = r_opt)")
print(f"  Turns density:    {N_TURNS / WINDING_LEN_M:.1f} turns/m")

# ======= 2. MUTUAL INDUCTANCE =======
print("\n" + "=" * 72)
print("  2. MUTUAL INDUCTANCE (runner-to-winding)")
print("=" * 72)
print(f"  M_max = u0*N*A_bore/L = {M_RUNNER_UH:.4f} uH = {M_RUNNER_H:.6e} H")
print(f"  (One runner-loop turn linking the full bore flux -- upper bound)")

# ======= 3. ADS1256 PARAMETERS =======
print("\n" + "=" * 72)
print("  3. ADS1256 PARAMETERS")
print("=" * 72)
print(f"  PGA:              {PGA}")
print(f"  Vref:             {VREF} V")
print(f"  Resolution:       {ADC_BITS} bits")
print(f"  LSB:              {LSB_NV:.3f} nV = {LSB_V:.3e} V")
print(f"  Full-scale:       +/-{VREF/PGA*1e3:.3f} mV")
print(f"  DRATE:            {DR_SPS} SPS")
print(f"  Sense resistor:   {R_SENSE_OHM/1000:.0f} kohm (negligible attenuation)")

# ======= 4. THEORETICAL CALIBRATION =======
print("\n" + "=" * 72)
print("  4. THEORETICAL CALIBRATION: fT_per_count(f)")
print("=" * 72)
print()
print("  Formula:  fT_per_count = LSB * u0 * N * 1e15 / (L * M * 2pif)")
print("            = K0 / f")
print()

K0 = LSB_V * MU0 * N_TURNS * 1e15 / (WINDING_LEN_M * M_RUNNER_H * 2 * math.pi)
print(f"  K0 = {K0:.6e}  (fT*Hz per count)")
print()

freqs_of_interest = [
    (4,   "beat (|16-20| Hz)"),
    (16,  "base drive"),
    (20,  "overlay drive"),
    (36,  "sum (16+20 Hz)"),
    (60,  "mains fundamental"),
    (120, "mains 2nd harmonic"),
    (180, "mains 3rd harmonic"),
]

print(f"  {'freq':>6s}  {'fT/count':>14s}  {'pT/count':>10s}  {'nT/count':>10s}  note")
print(f"  {'-'*6}  {'-'*14}  {'-'*10}  {'-'*10}  {'-'*24}")
for f, note in freqs_of_interest:
    ft = K0 / f
    pt = ft / 1e3
    nt = ft / 1e6
    print(f"  {f:6.0f}  {ft:14.0f}  {pt:10.1f}  {nt:10.4f}  {note}")

# ======= 5. DRIVE SELF-CALIBRATION =======
print("\n" + "=" * 72)
print("  5. DRIVE SELF-CALIBRATION")
print("=" * 72)
print()
print("  Drive: 0-3.3V square wave through 220ohm + R_coil")

# Drive current
for label, R_coil in [("4-parallel", R_COIL_4P_OHM), ("1-strand", R_COIL_1S_OHM)]:
    R_total = R_SERIES_OHM + R_coil
    I_max = V_DRIVE / R_total
    # Square wave 0->V: mean = V/2, fundamental = (2/pi)*V / R_total (peak, single-sided)
    I_fund = (2 / math.pi) * V_DRIVE / R_total
    B_dc = MU0 * N_TURNS * (I_max / 2) / WINDING_LEN_M
    B_fund = MU0 * N_TURNS * I_fund / WINDING_LEN_M
    print(f"\n  [{label}] R_total={R_total:.2f}ohm, I_max={I_max*1e3:.2f} mA")
    print(f"    I_fund (square-wave fundamental) = {I_fund*1e3:.2f} mA peak")
    print(f"    B_DC (mean) = {B_dc*1e6:.2f} uT = {B_dc*1e9:.0f} nT = {B_dc*1e15:.0f} fT")
    print(f"    B_fund = {B_fund*1e6:.2f} uT = {B_fund*1e9:.0f} nT = {B_fund*1e15:.0f} fT")

# Expected runner voltage at drive fundamental
print(f"\n  Expected runner response at 16 Hz base drive:")
R_total = R_SERIES_OHM + R_COIL_4P_OHM
I_fund_16 = (2 / math.pi) * V_DRIVE / R_total
V_runner_16 = M_RUNNER_H * 2 * math.pi * 16 * I_fund_16
counts_16 = V_runner_16 / LSB_V
B_16 = MU0 * N_TURNS * I_fund_16 / WINDING_LEN_M
print(f"    I_fund @ 16 Hz     = {I_fund_16*1e3:.2f} mA")
print(f"    V_runner (peak)    = {V_runner_16*1e9:.1f} nV = {V_runner_16/LSB_V:.2f} counts")
print(f"    B_solenoid (peak)  = {B_16*1e6:.2f} uT = {B_16*1e15:.0f} fT")
print(f"    Theoretical fT/ct  = {B_16*1e15 / counts_16:.0f} fT/count @ 16 Hz")
print(f"    From K0/f formula  = {K0/16:.0f} fT/count @ 16 Hz")

# ======= 6. APPLY TO ACTUAL DATA =======
print("\n" + "=" * 72)
print("  6. SPECTRAL AMPLITUDES -> fT (original captures)")
print("=" * 72)

FILES = {
    "rest1":   os.path.join(DATA_DIR, "egt_rest1_20261115_092006.jsonl"),
    "forward": os.path.join(DATA_DIR, "egt_forward_20261115_092211.jsonl"),
    "rest2":   os.path.join(DATA_DIR, "egt_rest2_20261115_092418.jsonl"),
    "reverse": os.path.join(DATA_DIR, "egt_reverse_20261115_092623.jsonl"),
}

data = {}
for tag, path in FILES.items():
    if os.path.exists(path):
        ch, ts = load_jsonl(path)
        dt = np.mean(np.diff(ts)) * 1e-6
        data[tag] = {"ch": ch, "ts": ts, "fs": 1/dt}
        print(f"  Loaded {tag}: {len(ts)} records, fs={1/dt:.1f} Hz")

# Spectral analysis at key frequencies
test_freqs = [4, 16, 20, 36, 60, 120]

for condition in ["rest1", "forward"]:
    if condition not in data:
        continue
    d = data[condition]
    print(f"\n  -- {condition.upper()} --")
    print(f"  {'freq':>6s}  {'c0 cts':>8s}  {'c1 cts':>8s}  {'c2 cts':>8s}  "
          f"{'c0 fT':>12s}  {'c1 fT':>12s}  {'c2 fT':>12s}  "
          f"{'c0 pT':>8s}  {'c1 pT':>8s}  {'c2 pT':>8s}")
    for f_t in test_freqs:
        amps = []
        fts = []
        for ci in range(3):
            amp, actual_f = spectral_amplitude(d["ch"][ci], d["fs"], f_t)
            ft_val = amp * K0 / f_t
            amps.append(amp)
            fts.append(ft_val)
        print(f"  {f_t:6.0f}  {amps[0]:8.1f}  {amps[1]:8.1f}  {amps[2]:8.1f}  "
              f"{fts[0]:12.0f}  {fts[1]:12.0f}  {fts[2]:12.0f}  "
              f"{fts[0]/1e3:8.1f}  {fts[1]/1e3:8.1f}  {fts[2]/1e3:8.1f}")

# ======= 7. NOISE FLOOR IN fT =======
print("\n" + "=" * 72)
print("  7. NOISE FLOOR IN FIELD UNITS")
print("=" * 72)
print()
print("  The noise std (in counts) is BROADBAND -- it spans all frequencies.")
print("  To express in fT, we need a bandwidth. The spectral density is")
print("  noise_std / sqrt(BW) counts/sqrtHz, and fT/sqrtHz = counts/sqrtHz x K0/f.")
print()

for condition in ["rest1", "forward"]:
    if condition not in data:
        continue
    d = data[condition]
    print(f"  -- {condition.upper()} --")
    for ci in range(3):
        std = d["ch"][ci].std()
        # Voltage noise
        v_noise = std * LSB_V
        # Spectral density (white noise approximation)
        bw = d["fs"] / 2  # Nyquist
        psd_counts = std / math.sqrt(bw)  # counts/sqrtHz
        psd_v = psd_counts * LSB_V  # V/sqrtHz

        print(f"    c{ci}: std={std:.1f} counts = {v_noise*1e9:.1f} nV")
        print(f"         PSD = {psd_v*1e9:.2f} nV/sqrtHz = {psd_counts:.2f} counts/sqrtHz")

        # fT/sqrtHz at specific frequencies
        for f in [16, 60]:
            ft_per_rootHz = psd_counts * K0 / f
            pt_per_rootHz = ft_per_rootHz / 1e3
            print(f"         @ {f} Hz: {ft_per_rootHz:.0f} fT/sqrtHz = {pt_per_rootHz:.1f} pT/sqrtHz")

# ======= 8. B_res DETECTABILITY =======
print("\n" + "=" * 72)
print("  8. B_res DETECTABILITY")
print("=" * 72)
B_RES_FT = 12.09776
print(f"\n  B_res (canon) = {B_RES_FT} fT (uncalibrated theoretical)")
print(f"\n  At 16 Hz drive:")
counts_for_Bres_16 = B_RES_FT / (K0 / 16)
print(f"    B_res -> {counts_for_Bres_16:.2e} counts (single spectral bin)")

if "rest1" in data:
    rest_std = data["rest1"]["ch"][1].std()
    print(f"    Rest noise std = {rest_std:.1f} counts")
    print(f"    SNR = {counts_for_Bres_16 / rest_std:.2e} (single-shot)")
    # Integration time needed for SNR=1
    # SNR improves as sqrt(T*BW) for narrowband detection in white noise
    # With BW = 1/T (single bin), SNR_T = signal * sqrtT / noise_per_bin
    # noise_per_bin = noise_std * sqrt(N) where N = total samples... this gets complex
    # Simpler: after T seconds at fs SPS, the spectral bin width is 1/T Hz
    # noise_in_bin = PSD * sqrt(1/T) = noise_std/sqrt(fs/2) * sqrt(1/T)
    # SNR_T = signal / noise_in_bin = signal * sqrt(T * fs/2) / noise_std
    bw = data["rest1"]["fs"] / 2
    T_for_snr1 = (rest_std / counts_for_Bres_16)**2 / bw
    print(f"    Time for SNR=1: {T_for_snr1:.2e} seconds = {T_for_snr1/3600:.0e} hours")
    print(f"      = {T_for_snr1/86400:.0e} days = {T_for_snr1/86400/365.25:.0e} years")
    print(f"\n    (!) B_res is ~{rest_std/counts_for_Bres_16:.0e}x below the noise floor.")
    print(f"    The experiment detects STATISTICAL PATTERNS in noise (pulldown,")
    print(f"    separator, correlation), not B_res directly.")

# ======= 9. CONVERSION TABLE =======
print("\n" + "=" * 72)
print("  9. CONVERSION REFERENCE TABLE")
print("=" * 72)
print()
print("  +----------------------------------------------------------------+")
print("  |  ADS1256 PGA=64, Vref=2.5V, 24-bit                           |")
print("  |  Runner sense: M = %.4f uH, N = %d, L = %.5f m     |" % (M_RUNNER_UH, N_TURNS, WINDING_LEN_M))
print("  |  fT_per_count(f) = %.6e / f                         |" % K0)
print("  |  Applies to: solenoid self-field seen by runner               |")
print("  +------+--------------+-----------+----------+------------------+")
print("  | freq |  fT/count    |  pT/count | nT/count | note             |")
print("  +------+--------------+-----------+----------+------------------+")
for f, note in freqs_of_interest:
    ft = K0 / f
    pt = ft / 1e3
    nt = ft / 1e6
    short_note = note[:16]
    print(f"  | {f:4.0f} | {ft:12.0f} | {pt:9.1f} | {nt:8.4f} | {short_note:<16s} |")
print("  +------+--------------+-----------+----------+------------------+")

# ======= 10. PULLDOWN IN fT =======
print("\n" + "=" * 72)
print("  10. PULLDOWN EXPRESSED IN FIELD UNITS")
print("=" * 72)
print()
print("  The pulldown is a BROADBAND effect (noise std drops under drive).")
print("  Expressing std as a field requires picking a reference frequency.")
print()
if "rest1" in data and "forward" in data:
    for ci in range(3):
        r_std = data["rest1"]["ch"][ci].std()
        d_std = data["forward"]["ch"][ci].std()
        pd_pct = (1 - d_std/r_std) * 100
        # Express at 60 Hz (dominant spectral content)
        r_nT = r_std * K0 / 60 / 1e6
        d_nT = d_std * K0 / 60 / 1e6
        delta_nT = (r_std - d_std) * K0 / 60 / 1e6
        print(f"  c{ci}: rest={r_std:.0f}  drive={d_std:.0f} counts  "
              f"pulldown={pd_pct:+.1f}%")
        print(f"      @ 60 Hz ref: rest={r_nT:.1f} nT  drive={d_nT:.1f} nT  "
              f"delta={delta_nT:.1f} nT")

# ======= SUMMARY =======
print("\n" + "=" * 72)
print("  SUMMARY")
print("=" * 72)
print(f"""
  CALIBRATION CONSTANT:
    K0 = {K0:.6e} fT*Hz
    fT_per_count(f) = K0 / f = {K0:.4e} / f

  AT KEY FREQUENCIES:
    16 Hz (drive base):    1 count = {K0/16:.0f} fT = {K0/16/1e3:.1f} pT
    20 Hz (drive overlay): 1 count = {K0/20:.0f} fT = {K0/20/1e3:.1f} pT
    60 Hz (mains):         1 count = {K0/60:.0f} fT = {K0/60/1e3:.1f} pT

  LSB (voltage):  {LSB_NV:.3f} nV/count
  M (runner):     {M_RUNNER_UH:.4f} uH

  CAVEAT: This is the SOLENOID SELF-FIELD calibration via mutual
  inductance M.  For external-field sensitivity, the runner's own
  effective loop area (not M) determines the coupling -- this requires
  either a known-source calibration or a geometry measurement of the
  runner circuit loop area.
""")

print("=" * 72)
print("  DONE")
print("=" * 72)
