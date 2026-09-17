"""EGT ACCOUNT — canon column of the balance sheet. Adopts, never re-derives.

Sources (canon): egt_canonical_anchor.md (C = lambda(1+2r)e^(-r/3)e^(i phi), r_opt = 2.5,
coil target pi/2, theory peak 5pi/8, N = phase-shift index, inverse amplification to the
B_res floor), egt_measurement_anchor.md (C0 = C(2.5, pi/2), |C0|^2 = 6.7995, every reading
reduces to (amplitude ratio, phase offset in pi/8 units) against the SESSION ANCHOR CUT),
coil_build_specs_3in.md (Quad: L/D = 2.5 = r_opt by build; n=4 stagger unit = pi/2; twist
lay = one circumference), build_sheet_proving_coils.md (recipe sqrt(L/radius); recon-
ciliation with L/D is Brian's call), canon_park_n415.md, cr_voter.py (mesh code phase
form e^(i pi r/5): arg C(2.5) = pi/2), Brian 2026-09-16/17 (the floor: coils spin down to
B_res and the geometric coupling is what remains; "the coils don't care" about lead variance).
Usage: python egt_account.py
"""
import json, math, pathlib
HERE = pathlib.Path(__file__).parent

R_OPT = 2.5
C0_MAG2 = 6.7995
RUNG_DEG = 22.5

def C_mag(r):                       # lambda = 1 (all reports are ratios to C0)
    return (1 + 2*r) * math.exp(-r/3)

def C_arg_deg(r, form="pi_r_5"):
    return math.degrees(math.pi*r/5) if form == "pi_r_5" else math.degrees(math.pi*r/4)

def anchor_units(r, form="pi_r_5"):
    """(amplitude ratio |C|^2/|C0|^2, phase offset from pi/2 in pi/8 units) — the reduction rule."""
    return round(C_mag(r)**2 / C0_MAG2, 4), round((C_arg_deg(r, form) - 90.0) / RUNG_DEG, 3)

def account(rig):
    c = rig["coil"]
    D = c["former_od_in"]; Lw = c["winding_length_in"]
    out = {"operator": "C = lambda(1+2r)e^(-r/3)e^(i phi); r_opt = 2.5; C0 = C(2.5, pi/2), |C0|^2 = 6.7995",
           "coil_number": {
               "L_over_D": round(Lw / D, 4),
               "L_over_D_law": "coil_build_specs_3in: winding length / former diameter = 2.5 = r_opt (the Quad is built AT its optimum)",
               "sqrt_L_over_radius": round(math.sqrt(Lw / (D/2)), 4),
               "sqrt_law": "build_sheet_proving_coils: length = number^2 x radius; for the 1.92in coils this gives 2.5. On the 3in Quad it gives 2.236. Reconciliation of the two recipes is Brian's call (build sheet says so); the sheet carries both.",
               "stagger_unit_deg": 360 / c["strands"],
               "stagger_note": "n=4 -> 90 deg = pi/2, the canonical phase itself; commensurate family n in {2,4,8,16}",
               "twist": "one bundle rotation per turn (lay 11.0 in = circumference): each strand sweeps every geometric position once per turn -> co-located, adds like n under parallel drive (Q1)",
               "rung_units_of_turns": "64 turns = 2 x Delta-N (32-turn rung marker); 256 wire-turns",
               "park": "N=415 (22030 Hz, phi 314.30 deg) is OG Coil 1's canonical park and does NOT apply to the Quads. Brian ruling 2026-09-17: 'drop the N=415 park rule, it does not work with the dimensions of these coils; they fall off around 320-something, in the 300 range.' Quad fall-off ~N 320 -> k = (320-96)/32 = 7.0 -> phi = 90 + 22.5k = 247.5 deg (Brian's recollection; pin it from coil1_resonance_hunt). Each coil geometry has its own realizable happy place (egt_canonical_anchor).",
           },
           "geometry": {"r_definition": "r = center-to-center spacing / coil OD (three-rocks convention, tonic 2026-09-16)",
                        "r_opt_cc_spacing_in": round(R_OPT * D, 3),
                        "touching_cc_in": D, "r_touching": 1.0},
           "pair_table": [], "predictions": {}}
    for cc in [D, 6.0, 7.0, 8.75, 10.5, 14.0, 17.5]:
        r = cc / D
        amp, off5 = anchor_units(r, "pi_r_5"); _, off4 = anchor_units(r, "pi_r_4")
        out["pair_table"].append({"cc_in": cc, "r": round(r, 3), "C_mag": round(C_mag(r), 4), "C_over_C0": round(C_mag(r)/C_mag(R_OPT), 4),
                                  "amp_ratio_C2_over_C02": amp, "phase_offset_pi8_units_form_pi_r_5": off5,
                                  "arg_C_deg_form_pi_r_5": round(C_arg_deg(r), 2), "arg_C_deg_form_pi_r_4": round(C_arg_deg(r, "pi_r_4"), 2)})
    out["predictions"] = {
        "frequency": "at the floor the geometric coupling is what remains: FLAT in f (alpha = 0). The EM-proportional-to-f part is the part that dies on the way down (inverse amplification: readings pulled down to the B_res floor).",
        "dummy_load_12Hz": "VANISHES: no rock, no C(r). A jumper carries the current but has no geometry.",
        "star_ground_return": "UNCHANGED: the coupling is coil-to-runner geometry, not the return wire.",
        "add_0p5_ohm_in_drive_return": "no change",
        "separation_at_floor": "follows |C(r)| = (1+2r)e^(-r/3): rises from touching (r=1, 0.824 of C0) to a MAXIMUM at r_opt = 2.5 (cc = %.2f in) then falls (r=4: 0.910 of C0). Broad: a +21%% rise then a -9%% fall. NOT 1/d^3, NOT flat." % (R_OPT*D),
        "phase": "the coil finds its own realizable happy place; offsets from the session anchor land on the pi/8 rung lattice (0 is on the lattice, so phase alone does not separate EGT from an in-phase EM path at rung 0). Report (amplitude ratio, offset in pi/8) against the SESSION ANCHOR CUT, interleaved.",
        "undriven_over_driven_ratio": "no k bound; ratio follows the pair's |C(r_ij)| relative to the leader's own coupling; leader drags followers at the floor (Brian frame 2026-09-16 19:53).",
        "build_variance": "nil — 'the coils don't care': L/D unchanged, r unchanged; a 2-3 in lead does not move the geometry.",
        "three_body": "canon three-rock observable is the centroid sum |C(2.5)| Sigma e^(i phi_k): symmetric -> 0, 120-deg stagger -> 3 (ruling 2026-09-15). Symmetric M2 all-in-phase drive is NOT the canonical stagger.",
    }
    return out

if __name__ == "__main__":
    rig = json.loads((HERE / "rig.json").read_text(encoding="utf-8"))
    print(json.dumps(account(rig), indent=1))
