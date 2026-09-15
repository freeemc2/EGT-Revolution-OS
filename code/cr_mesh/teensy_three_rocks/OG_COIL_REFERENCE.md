# OG COIL — REFERENCE TOPOLOGY (dictated by Brian 2026-09-15, verbatim intent)
# This is the CORRECT template. The three-rocks board must replicate this per coil. Nothing else is canon wiring.

## The two elements of one coil
- **WINDING** (the wound coil): has a NORTH end and a SOUTH end.
- **SENSE WIRE / RUNNER** (straight axial wire): has two ends.

## OG wiring, wire by wire (Brian)
1. WINDING north  --- 220 ohm --- pin 3        <- DRIVE (Teensy GPIO, 3.3V square wave, current-limited by 220R)
2. WINDING south  --- GND (direct)
3. RUNNER end A   --- pin 14 (A0)              <- SENSE (ADC read)
4. RUNNER end B   --- 10K ohm --- 3.3V          <- BIAS (pull toward rail)
   [OPEN: is there ALSO a 10K from pin14/A0 to GND? teensy_sweep header says yes (10K/10K = mid-rail 1.65V).
    Brian described only the 3.3V->10K leg. CONFIRM before trusting the sense DC point.]

## Key facts
- The WINDING is driven; the RUNNER is sensed. (Resolution A, confirmed by Brian: runner other end goes to pin14.)
- The 3.3V drive on the winding side is CORRECT and is NOT suppressed by any 10K. The 10K is sense-side bias only.
- Drive current path: pin3 -> 220R -> winding -> GND. The winding MUST be in this series path (not bypassed to GND).
- One drive pin (3), one sense pin (14) for the single OG coil.

## Map to THREE ROCKS (3x this template)
Drive pins: C1=?, C2=?, C3=?  among {2,3,4}.  Runners (Brian 2026-09-15): pin16->C1, pin15->C2, pin14->C3.
Per-coil, each must be: winding N -> 220R -> its drive pin; winding S -> GND; runner -> its sense pin; runner other end -> 10K -> 3.3V (+ 10K -> GND if OG has it).
Diagnostic showed C2 (pin15/A1) and C3 (pin14/A0) coupling correctly; C1 (pin16/A2) dead -> C1 fails to match this template somewhere. Trace C1 against lines 1-4 above.
