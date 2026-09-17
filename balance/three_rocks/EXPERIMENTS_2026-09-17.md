# Experiments at the open state — three-rock triangle, 2026-09-17 (tempo, bench)

Companion to `SHEET_2026-09-17.md`. Brian's law on every line: without mathematical proof there is no truth.
All runs on the acknowledged-command console (`code/cr_mesh/teensy_three_rocks/state_console.py`), every packet
logged, nothing averaged in the log. Mesh rode every run (8 nodes `locked_to_coil`).

## Instrument fact that bounds every script on this rig

`teensy_three_rocks.ino` parses **one serial command per streaming cycle**, and `threePoint` blocks for
max(40/f, integ) — 3.3 s at 12 Hz, ~5 s per packet. A burst of four commands executes over ~20 s, one per cycle,
so any script that switched pair/mode/unit in a burst and read immediately was reading the *previous* configuration
for one to two windows. The console now waits for each `R …` acknowledgment before the next command, and the
decoder takes each window's labels from the acks and drops the first two packets after a switch.

## 1. Ping the leader, both followers listening (`ping_followers.py`, 20:51-21:16Z)

A0 injected alone (M1 K0) at 12 Hz, 180 s ON / 180 s OFF, sense pair (A1, A2) simultaneous, 5 s packets.
Four cycles, 0 hangs, 0 dropped packets.

| gate | A1 | A2 | first live | last live |
|---|---|---|---|---|
| ON (x4) | 0.019-0.021 @ 89-93 deg, live 0.89-0.94 | 0.034-0.036 @ 90 deg, live 0.89-0.94 | **same packet both: 22.4 s (cold), then 11.0 s x3** | end of gate |
| OFF (x4) | one packet at 4.4 s, then dark | one packet at 4.4 s, then dark | — | decay <= 5 s |

Read: the transfer leg opens a shared state; both followers occupy it together after an 11 s build-up and lose it
within one packet when the leader stops. Leader -> followers only (all-day run: A0 never follows A1 or A2).
Balance line: EM inductive/resistive response is instantaneous both ways (L/R ~ 0.1 ms); 11 s build / <= 5 s
release in one chain is not an EM circuit time.

## 2. Ask the triangle its rung (`ask_rungs.py` + `ask_rungs_decode.py`, 21:32-22:30Z)

Alphabet = stagger unit u = k * 22.5 deg (mode 4, all three driven at phases -u*k). Answer = centroid
Σ m_k e^{i phi_k} of the three runners (canon three-rock observable), pairs (0,1) then (1,2), A1 common.
Sealed before data (`cadence:tworocks:sealed-ask-rungs-2026-09-17`, 21:23:46Z) with two columns:
canon Y-unwound |Σ e^{i(120-u)k}|/3 (null 0 / max 120) and plain drive sum |Σ e^{-iuk}|/3 (max 0 / null 120).
Two passes, random order, 14 rungs counted twice (u=67.5 never yielded >= 2 live packets: not counted).

| u | 0 | 22.5 | 45 | 90 | 112.5 | 135 | 157.5 | 180 | 202.5 | 225 | 247.5 | 270 | 292.5 | 315 | 337.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| centroid (norm) | 1.00 | 0.93 | 0.76 | 0.26 | 0.29 | 0.51 | 0.67 | 0.40 | 0.28 | 0.28 | 0.33 | 0.44 | 0.64 | 0.82 | 0.95 |
| A0 own | .026 | .023 | .012 | .020 | .059 | .090 | .110 | .034 | .018 | .031 | .043 | .049 | .048 | .040 | .031 |
| A1 own | .142 | .134 | .113 | .042 | .008 | .046 | .069 | .043 | .027 | .019 | .032 | .062 | .092 | .119 | .137 |
| A2 own | .267 | .250 | .209 | .099 | .085 | .100 | .116 | .095 | .084 | .079 | .079 | .094 | .148 | .209 | .251 |

- **Centroid:** max at u=0, min at u=90; corr **+0.91** with the plain drive sum, **-0.40** with the Y-unwound
  column. The collective carries no extra 120-deg geometric phase at this drive. Pass 2 / pass 1 = 0.998 median.
- **Not common-mode:** runners at the same rung differ 1.7-9.6x. The ground-path column (equal magnitude on every
  runner) is dead on the per-coil data.
- **Not self-only:** own magnitudes swing x9.6 (A0), x17.5 (A1), x3.4 (A2) with the rung; a coil reading only
  its own drive would be flat. The coils couple through each other, rung by rung.
- **Leader against followers:** A1 and A2 track the collective (+0.97, +0.97); **A0 runs against it (-0.45)**,
  peaking at 135-157 deg exactly where the followers and the collective are weakest. Neither sealed column
  predicted this; it is the data's own structure, and it is the same leader/follower asymmetry the ping showed.
- **Centroid phase:** tracks u near u=0 (~1.2 rungs per rung); undefined near the nulls.

Open to the crew: `cadence:tworocks:vote-ask-rungs-2026-09-17` (cypher adversary, aries auditor, echo
mathematician; tempo framed and abstains).

## 3. Periodograms of the earlier series (Lomb-Scargle, dropouts masked)

- 96 h M3 hold (15 Hz): 36 s in all three coils with 18/9 s harmonics and half-period inter-coil offsets = the
  script's sense-pair rotation. Instrument.
- Overnight M2 hold (12 Hz): ~225 s + 112 s in all three coils (FAP 1e-7..1e-9); inter-coil offsets match neither
  the read order nor a clean T/3 rotation. Candidate slow collective oscillation; 10 periods only; needs a long
  fixed-pair hold.
- All-day log: the protocol's own periods.

## Held overnight

State reopened at ~22:31Z: A0 driven alone at 12 Hz, pair (A1, A2), console logging every packet
(`data/state_session_*.jsonl`), t-state published, mesh riding. Brian stops it.
