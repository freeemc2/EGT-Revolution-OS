"""EM ACCOUNT — what Maxwell, applied exactly to THIS rig, permits each observable to be.

This is the null side of the balance sheet (Brian 2026-09-17: "a mathematical balancer
against each one of our test systems so we can apply EM law, and then EGT").
Every number below is computed from rig.json, never asserted. A wall is cashed here or
it falls. Units: SI inside, reported in lock-in counts (mag = A/2, 1 count = 3.2258 mV).

Paths accounted:
  1. inductive   winding -> runner loop (M bounded above by one runner-loop turn linking the
                 whole bore flux; ideal axial return -> ~0). EMF proportional to f.
  2. ground path drive return current x shared ground resistance appearing at the sense node.
                 FLAT in f, in phase (reads 90 deg), common-mode, present with a dummy load.
  3. capacitive  drive pin -> sense node stray C into the ~98 ohm node. Proportional to f.
  4. build variance: 2-3 in of lead line between three 65 ft coils.
Usage: python em_account.py  -> prints JSON (also written by sheet.py)
"""
import json, math, pathlib

MU0 = 4e-7 * math.pi
RHO_CU = 1.68e-8                       # ohm*m, copper 20 C
AWG = {18: {"d_mm": 1.02362, "ohm_per_m": 0.02095},
       22: {"d_mm": 0.64384, "ohm_per_m": 0.05296}}
FREQS = [12, 30, 100, 300, 1000, 3000, 7878, 12000, 22030, 40000]
HERE = pathlib.Path(__file__).parent

def load_rig():
    return json.loads((HERE / "rig.json").read_text(encoding="utf-8"))

def wheeler_L_H(N, r_in, l_in):
    """Single-layer solenoid, Wheeler: L(uH) = r^2 N^2 / (9r + 10l), r,l in inches."""
    return (r_in**2 * N**2) / (9*r_in + 10*l_in) * 1e-6

def skin_depth_m(f):
    return math.sqrt(RHO_CU / (math.pi * f * MU0))

def strand_modes(rig):
    c = rig["coil"]
    L_strand_m = c["strand_length_ft"] * 0.3048
    R_strand = L_strand_m * AWG[c["wire_awg"]]["ohm_per_m"]
    r_in = c["former_od_in"] / 2 + 0.03            # bundle sits just outside the pipe
    l_in = c["winding_length_in"]
    N = c["turns"]
    return {
        "1_strand":   {"N": N,   "R_coil": R_strand,     "L_H": wheeler_L_H(N, r_in, l_in)},
        "4_parallel": {"N": N,   "R_coil": R_strand / 4, "L_H": wheeler_L_H(N, r_in, l_in)},
        "4_series":   {"N": 4*N, "R_coil": R_strand * 4, "L_H": wheeler_L_H(4*N, r_in, l_in)},
    }

def drive_current_fund(f, rig, mode, pin_z):
    """Fundamental current amplitude (A) of the 0..3.3 V square through 220R + pin + coil."""
    V1 = (4/math.pi) * rig["drive"]["v_high"] / 2
    Rt = rig["drive"]["series_r_ohm"] + pin_z + mode["R_coil"]
    Z = math.hypot(Rt, 2*math.pi*f*mode["L_H"])
    return V1 / Z, V1

def counts_mag(v_amp, rig):
    """Sense-node sinusoid amplitude (V) -> lock-in mag in counts (mag = A/2)."""
    return v_amp / (rig["sense"]["count_mv"] * 1e-3) / 2

def account(rig):
    c, s = rig["coil"], rig["sense"]
    modes = strand_modes(rig)
    r_bore_m = c["former_od_in"] / 2 * 0.0254
    A_bore = math.pi * r_bore_m**2
    l_m = c["winding_length_in"] * 0.0254
    out = {"wire": {}, "coil": {}, "per_frequency": [], "discriminators": {}, "build_variance": {}}
    for awg in (c["wire_awg"], c["runner_awg"]):
        out["wire"][f"awg{awg}"] = AWG[awg]
    for name, m in modes.items():
        M_max = MU0 * m["N"] * A_bore / l_m       # one runner-loop turn linking the full bore flux
        out["coil"][name] = {"N": m["N"], "R_coil_ohm": round(m["R_coil"], 4), "L_uH": round(m["L_H"]*1e6, 2),
                             "M_runner_max_uH": round(M_max*1e6, 4),
                             "f_res_kHz_for_Cpar_pF": {str(cp): round(1/(2*math.pi*math.sqrt(m["L_H"]*cp*1e-12))/1e3, 1)
                                                       for cp in rig["parasitic_c_pf"]},
                             "f_where_wL_eq_220_kHz": round(220/(2*math.pi*m["L_H"])/1e3, 1)}
    Rsh_lo, Rsh_hi = rig["shared_ground_r_ohm"]["range"]
    C_lo, C_hi = [x*1e-12 for x in rig["stray_c_pf"]]
    pin_lo, pin_hi = rig["drive"]["pin_z_ohm"]
    m1 = modes["1_strand"]
    for f in FREQS:
        I1_hi, V1 = drive_current_fund(f, rig, m1, pin_lo)     # most current: low pin Z
        I1_lo, _  = drive_current_fund(f, rig, m1, pin_hi)
        M_max = MU0 * m1["N"] * A_bore / l_m
        v_ind_max = 2*math.pi*f * M_max * I1_hi
        v_gnd_1   = [I1_lo*Rsh_lo, I1_hi*Rsh_hi]               # one coil driven
        v_gnd_3   = [3*I1_lo*Rsh_lo, 3*I1_hi*Rsh_hi]           # M2 symmetric: three in phase on one bus
        v_cap     = [2*math.pi*f*C_lo*V1*s["node_z_ohm"], 2*math.pi*f*C_hi*V1*s["node_z_ohm"]]
        out["per_frequency"].append({
            "f_hz": f, "skin_depth_mm": round(skin_depth_m(f)*1e3, 2),
            "I1_mA": [round(I1_lo*1e3, 2), round(I1_hi*1e3, 2)],
            "inductive_max_counts": round(counts_mag(v_ind_max, rig), 5),
            "inductive_phase_read_deg": "0 or 180 (quadrature to drive)",
            "ground_1coil_counts": [round(counts_mag(v, rig), 4) for v in v_gnd_1],
            "ground_3coil_counts": [round(counts_mag(v, rig), 4) for v in v_gnd_3],
            "ground_phase_read_deg": 90,
            "capacitive_counts": [round(counts_mag(v, rig), 5) for v in v_cap],
        })
    # what R_sh would have to be to carry a given flat reading
    I1_12, _ = drive_current_fund(12, rig, m1, (pin_lo+pin_hi)/2)
    for mag in (0.7, 0.3, 0.16, 0.03):
        v = mag * 2 * s["count_mv"] * 1e-3
        out["discriminators"][f"Rsh_for_flat_{mag}_counts_ohm"] = {"1_driven": round(v/I1_12, 3), "3_driven_in_phase": round(v/(3*I1_12), 3)}
    out["discriminators"]["frequency_slope_alpha"] = {"inductive": 1.0, "ground_path": 0.0, "capacitive": 1.0,
        "note": "alpha = d log(mag)/d log(f); inductive holds alpha=1 up to f where wL ~ 220 ohm"}
    out["discriminators"]["dummy_load_12Hz"] = {"inductive": 0.0, "ground_path": "UNCHANGED (same current, same bus)", "capacitive": "unchanged (pin still swings)"}
    out["discriminators"]["star_ground_return"] = {"inductive": "unchanged", "ground_path": "collapses toward 0 (no shared segment)", "capacitive": "unchanged"}
    out["discriminators"]["add_0p5_ohm_in_drive_return"] = {"ground_path": "rises by I1 x 0.5 ohm = %.3f counts (1 coil) / %.3f counts (3 coils)" % (counts_mag(I1_12*0.5, rig), counts_mag(3*I1_12*0.5, rig)), "inductive": "no change", "capacitive": "no change"}
    out["discriminators"]["separation_at_floor"] = {"inductive": "already ~0 at 12 Hz; near-field 1/d^3 x cos(theta) for whatever remains", "ground_path": "FLAT vs distance and angle", "capacitive": "flat"}
    out["discriminators"]["undriven_over_driven_ratio"] = {"inductive": "k <= 1 (a coupled coil never exceeds its source)", "ground_path": "NO k bound: ratio = R_sh(i)/R_sh(j), can exceed 1 if the undriven runner's return shares more bus", "note": "the 09-16 'forbidden 13x' line was an inductive-only bound"}
    lo, hi = c["build_variance_lead_in"]
    L_ft = c["strand_length_ft"]
    out["build_variance"] = {
        "delta_R_pct": [round(100*lo/12/L_ft, 3), round(100*hi/12/L_ft, 3)],
        "delta_L_pct": "~0 (straight leads add ~0.07 uH vs ~%d uH winding)" % round(m1["L_H"]*1e6),
        "delta_drive_current_pct_at_12Hz": [round(100*(lo/12/L_ft)*m1["R_coil"]/220, 5), round(100*(hi/12/L_ft)*m1["R_coil"]/220, 5)],
        "delta_f_res_pct": "< 0.05",
        "verdict": "unmeasurable in band: the 220R sets the current, the coil's own R is 0.1-0.5% of it, leads do not change L/D",
    }
    return out

if __name__ == "__main__":
    print(json.dumps(account(load_rig()), indent=1))
