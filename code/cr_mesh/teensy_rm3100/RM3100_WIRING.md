# RM3100 ARRAY — wiring sheet (v1, Teensy 4.1, 6-sensor triadic)

The RM3100 array is the **DC / low-frequency VECTOR field-geometry mapper**. It
reads the 3-axis field around the triadic and an **inside↔outside differential**.
Keep it in its own box (see "What this does NOT measure" at the bottom).

## ⚠️ SAFETY / GOTCHAS (read before wiring)
- **RM3100 is 3.3 V. Teensy 4.1 is 3.3 V → NO level shifting needed** (the AD7606
  headache does not apply here). But **feed the sensor 3V3, NOT 5 V** unless your
  breakout has its own on-board regulator *and* logic-level shifting. When unsure,
  use 3V3. A 5 V line into an RM3100/Teensy pin can damage it.
- **All grounds common** with the Teensy and the coil-bench ground (single-point).
- **Keep every sensor away from the 4-ton AC transformer** — that duty-cycle drift
  is the documented phase-wander source; it will swamp a nT-scale magnetometer.
- Twist each sensor's cable (or use shielded) on long runs; ground the shield at the
  Teensy end only.

## BUS — shared SPI0 + one CS per sensor
```
                 Teensy 4.1 (3.3 V)
                 +------------------+
   3V3  ---------| 3V3          SCK |13 --------+-----+-----+-----+-----+-----+
   GND  ---------| GND         MOSI |11 ------+ |   +-|-----|-----|-----|-----|--+
                 |             MISO |12 ----+ | | | | |   | |   | |   | |   | |  |
                 |                  |       | | | | | |   | |   ...  (shared bus)
                 |  CS pins:        |       v v v v v v
                 |   s0 = 2 --------|--------> to each RM3100's SSN (own line)
                 |   s1 = 3         |
                 |   s2 = 4         |   Every RM3100 gets: 3V3, GND, SCK, MOSI, MISO (shared)
                 |   s3 = 5         |                  +  its OWN SSN(CS) from the list at left
                 |   s4 = 6         |
                 |   s5 = 7         |   DRDY is POLLED over SPI (STATUS reg) — no DRDY wires.
                 +------------------+
```

### Per-sensor pin table
| RM3100 pin | Teensy 4.1 | shared? | note |
|---|---|---|---|
| VCC / 3V3  | 3V3 (or a clean 3.3 V rail) | shared | **3.3 V only** |
| GND        | GND | shared | single-point ground w/ coil bench |
| SCK / SCL  | 13 (SCK0) | **shared** | SPI clock |
| MOSI / SDA | 11 (MOSI0) | **shared** | |
| MISO       | 12 (MISO0) | **shared** | |
| SSN / CS   | see map ↓ | **one each** | this is how 6 sensors are addressed |
| DRDY       | *(leave unconnected)* | — | polled via STATUS 0x34 bit7 |

### CS map (edit `NSENS` + `CS_PINS[]` in the .ino to change)
| sensor | role | CS → Teensy pin |
|---|---|---|
| s0 | vertex (coil A) | 2 |
| s1 | vertex (coil B) | 3 |
| s2 | vertex (coil C) | 4 |
| s3 | observer (outside) | 5 |
| s4 | observer (outside) | 6 |
| s5 | observer (outside) | 7 |

*I²C alternative:* only ~4 addresses without a mux — for 6+ sensors use SPI (above)
or a TCA9548A I²C mux. SPI is simpler here; stick with it.

## PHYSICAL ARRAY — Gemini's topology (3 vertices + 3 observers)
Three like coils = the "body" (triadic). A sensor sits **at each coil** (vertex,
inside the field) and **outside observers** ring the array to catch what leaves it.
The signal you're hunting is the **inside vs outside** vector differential as you
switch drive modes (symmetric/null ↔ staggered).

```
                        (top-down view, bench)

              o s3                                   o s4
            observer                              observer
                 \                                   /
                  \                                 /
                   \          [ s0 ]  coil A       /
                    \          (vertex)           /
                     \        /        \         /
                      \      /          \       /
                       \    /   CENTER   \     /
                        \  /   (the well) \   /
                  coil C [ s2 ]---------[ s1 ] coil B
                       (vertex)          (vertex)
                          |
                          |
                        o s5
                       observer

   • s0,s1,s2  : one RM3100 co-located at each coil (measures the field AT the source)
   • s3,s4,s5  : observers stood off outside the triangle (measures the escaping field)
   • CENTER    : the point the triadic drive is meant to act on (the "well")
   • Each sensor reports Bx,By,Bz -> you get the full vector, not just magnitude.
```

**Reading it:** in **symmetric/null** drive the center vector sum → 0 (silent
control); in **staggered** drive it → full coupling. The observable that matters
here is *how the vertex field vs the observer field changes between those two modes*
— an inside-heavy / outside-quiet signature (or vice-versa). That spatial pattern
is the RM3100 array's whole contribution.

## BRING-UP (do in order)
1. Flash `teensy_rm3100.ino`. Nothing near the coils powered yet.
2. `P` → `R PONG rm3100 6 600`.
3. `W` → every sensor prints `R ID s<i> 0x22 OK`. **Any `??` = bad wiring/power on
   that CS line — fix before trusting data.**
4. In Earth's field, hold still, `S` → each sensor streams a steady ~±50 µT vector
   (Earth ≈ 25–65 µT). Rotate one sensor by hand → its Bx/By/Bz swing. Confirms axes live.
5. `Z` with everything still → captures & subtracts baseline (now stream ≈ 0).
6. Power the coils. `C 400` for finer resolution if you need it (slower). Log with a
   capture script; switch drive modes on the Teensy_multi and watch vertex vs observer.

## STREAM FORMAT
`T <ms> s<i> <Bx> <By> <Bz> <|B|>`  — µT, baseline-subtracted if `Z` was run.
Commands: `P` ping · `W` whoami · `C <cc>` cycle count (25–800) · `R <hex>` TMRC rate
· `Z` baseline · `S` stream on · `x` off.

## WHAT THIS DOES *NOT* MEASURE (frame guard — do not blur)
- **Not the 22 kHz drive / arg C phase.** RM3100 band is DC..few hundred Hz. The
  phase observable stays on the coil runner-sense → LNA → AD7606 lock-in chain.
- **Not the B_res ~fT floor.** RM3100 floor is ~nT (~10⁶ coarser). The floor /
  C(r) coupling test stays on the LNA chain.
- **Not proof of a gravity anomaly.** The sealed triadic observable is *force on a
  test mass*, not field pattern. This array maps the field configuration = necessary
  context and control — it does **not**, by itself, demonstrate an anomaly.
```
```
