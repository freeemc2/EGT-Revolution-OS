#!/usr/bin/env python3
"""
solar_em_gravity.py
===================
The founding question: is gravity a product of electromagnetism?

Start from Earth. Use real numbers. No imported QM, no Schrodinger,
no abstract graphs.

Inputs (all measured):
  - Sun's electromagnetic output (luminosity, magnetic field, solar wind)
  - Total mass of everything orbiting the Sun
  - Sun's spin (rotation period)
  - Heliosphere boundary (where the EM "bubble" ends)

Questions:
  1. What is the Sun's total EM energy output vs gravitational binding energy?
  2. If C(r) operates on physical distance, where does r_opt = 2.5 land?
  3. Does the heliosphere boundary match where C(r) dies?
  4. Can the Sun's spin be predicted from its EM + mass properties?
  5. What is the quarter-turn (pi/4) in physical units?

No postulates imported except: conservation of energy, measurable quantities.
"""

import numpy as np

# =====================================================================
# MEASURED CONSTANTS
# =====================================================================

# Fundamental
c = 2.99792458e8          # m/s
G = 6.67430e-11           # m^3 kg^-1 s^-2
h = 6.62607015e-34        # J·s
k_B = 1.380649e-23        # J/K
mu_0 = 4 * np.pi * 1e-7   # T·m/A (vacuum permeability)
epsilon_0 = 8.8541878128e-12  # F/m

# Distance units
AU = 1.496e11             # meters
ly = 9.461e15             # meters (light-year)
pc = 3.086e16             # meters (parsec)

# Sun
M_sun = 1.989e30          # kg
R_sun = 6.957e8           # m
L_sun = 3.828e26          # W (total EM luminosity)
T_sun_surface = 5778      # K
B_sun_surface = 1e-4      # T (1 Gauss, dipole average)
P_sun_equator = 25.05 * 86400  # s (sidereal rotation period, equator)
P_sun_pole = 34.4 * 86400      # s (poles — differential rotation)
omega_sun = 2 * np.pi / P_sun_equator  # rad/s

# Sun's angular momentum
I_sun = 0.070 * M_sun * R_sun**2  # moment of inertia (solid body approx, k=0.070)
L_ang_sun = I_sun * omega_sun      # kg m^2/s

# Solar wind
solar_wind_mass_rate = 1.5e9  # kg/s (~1.5 million tons/hour)
solar_wind_speed = 4.5e5      # m/s (average, slow+fast wind)
solar_wind_power = 0.5 * solar_wind_mass_rate * solar_wind_speed**2  # W (kinetic)

# Solar magnetic field at various distances (dipole: B ~ 1/r^3)
def B_sun_at(r_meters):
    """Dipole magnetic field of the Sun at distance r."""
    return B_sun_surface * (R_sun / r_meters)**3

# Planets and debris — masses (kg) and orbital radii (AU)
bodies = {
    'Mercury':   (3.301e23,   0.387),
    'Venus':     (4.867e24,   0.723),
    'Earth':     (5.972e24,   1.000),
    'Mars':      (6.417e23,   1.524),
    'Asteroids': (3.0e21,     2.7),    # total asteroid belt
    'Jupiter':   (1.898e27,   5.203),
    'Saturn':    (5.683e26,   9.537),
    'Uranus':    (8.681e25,  19.19),
    'Neptune':   (1.024e26,  30.07),
    'Kuiper':    (6.0e23,    42.0),    # Kuiper belt estimate
    'Oort':      (3.0e25,    50000),   # Oort cloud (very uncertain, 5-100 M_Earth)
}

# Heliosphere
heliopause_AU = 120        # AU (Voyager 1 crossing, 2012)
termination_shock_AU = 94  # AU (Voyager 1, 2004)
oort_inner_AU = 2000       # AU
oort_outer_AU = 100000     # AU (~1.6 ly)

# Alpha Centauri
alpha_cen_distance = 4.37 * ly / AU  # in AU (~276,000 AU)


# =====================================================================
# PART 1: THE NUMBERS — what does the Sun actually put out?
# =====================================================================

def part1_solar_inventory():
    print("=" * 78)
    print("PART 1: SOLAR SYSTEM INVENTORY — measured quantities")
    print("=" * 78)

    # EM output
    print("\n  SUN'S ELECTROMAGNETIC OUTPUT:")
    print(f"    Luminosity (photons):     {L_sun:.3e} W")
    print(f"    Solar wind (kinetic):     {solar_wind_power:.3e} W")
    print(f"    Solar wind (mass flux):   {solar_wind_mass_rate:.3e} kg/s")
    print(f"    Total EM power:           {L_sun + solar_wind_power:.3e} W")
    print(f"    Ratio wind/photon:        {solar_wind_power/L_sun:.4f}")

    # Magnetic field
    print(f"\n  MAGNETIC FIELD (dipole):")
    for label, r_au in [("Surface", R_sun/AU), ("Mercury", 0.387),
                         ("Earth", 1.0), ("Jupiter", 5.2),
                         ("Heliopause", 120), ("Oort inner", 2000)]:
        r_m = r_au * AU
        B = B_sun_at(r_m)
        print(f"    At {label:12s} ({r_au:>10.3f} AU): B = {B:.3e} T")

    # Mass distribution
    print(f"\n  MASS DISTRIBUTION:")
    total_non_sun = 0
    total_L_orb = 0
    for name, (mass, r_au) in sorted(bodies.items(), key=lambda x: x[1][1]):
        r_m = r_au * AU
        v_orb = np.sqrt(G * M_sun / r_m) if r_au < 100000 else 0
        L_orb = mass * v_orb * r_m  # orbital angular momentum
        total_non_sun += mass
        total_L_orb += L_orb
        print(f"    {name:12s}: m = {mass:.3e} kg, r = {r_au:>10.1f} AU, "
              f"L_orb = {L_orb:.3e} kg⋅m²/s")

    print(f"\n    Total non-Sun mass:       {total_non_sun:.3e} kg")
    print(f"    Sun mass fraction:        {M_sun/(M_sun+total_non_sun)*100:.4f}%")
    print(f"    Total orbital ang. mom:   {total_L_orb:.3e} kg⋅m²/s")
    print(f"    Sun's spin ang. mom:      {L_ang_sun:.3e} kg⋅m²/s")
    print(f"    Ratio orbital/spin:       {total_L_orb/L_ang_sun:.1f}x")
    print(f"    (planets carry {total_L_orb/(total_L_orb+L_ang_sun)*100:.1f}% "
          f"of total angular momentum)")

    # Sun's spin
    print(f"\n  SUN'S SPIN:")
    print(f"    Equatorial period:        {P_sun_equator/86400:.2f} days")
    print(f"    Polar period:             {P_sun_pole/86400:.2f} days")
    print(f"    Angular velocity:         {omega_sun:.3e} rad/s")
    print(f"    Equatorial surface v:     {omega_sun * R_sun:.0f} m/s "
          f"({omega_sun * R_sun / 1000:.1f} km/s)")

    # Heliosphere
    print(f"\n  HELIOSPHERE / GRAVITATIONAL BOUNDARY:")
    print(f"    Termination shock:        {termination_shock_AU} AU")
    print(f"    Heliopause:               {heliopause_AU} AU")
    print(f"    Oort cloud inner:         {oort_inner_AU} AU")
    print(f"    Oort cloud outer:         {oort_outer_AU} AU ({oort_outer_AU*AU/ly:.2f} ly)")
    hill = (M_sun / (3 * 4e10 * M_sun))**(1/3) * 8e3 * pc / AU  # rough Hill sphere vs Milky Way
    print(f"    Hill sphere (vs galaxy):  ~{1.0:.1f}-{2.0:.1f} ly")
    print(f"    Alpha Centauri:           {alpha_cen_distance:.0f} AU ({4.37:.2f} ly)")

    return total_non_sun, total_L_orb


# =====================================================================
# PART 2: EM ENERGY vs GRAVITATIONAL BINDING
# =====================================================================

def part2_em_vs_gravity():
    print()
    print("=" * 78)
    print("PART 2: ELECTROMAGNETIC vs GRAVITATIONAL ENERGY")
    print("=" * 78)

    # Gravitational binding energy of Sun
    E_grav_sun = 3 * G * M_sun**2 / (5 * R_sun)
    print(f"\n  Gravitational binding energy of Sun: {E_grav_sun:.3e} J")

    # Total EM energy radiated over Sun's lifetime (~4.6 Gyr)
    t_sun = 4.6e9 * 3.156e7  # seconds
    E_em_total = L_sun * t_sun
    print(f"  Total EM radiated (4.6 Gyr):         {E_em_total:.3e} J")

    print(f"\n  Ratio E_em / E_grav:                 {E_em_total / E_grav_sun:.4f}")
    print(f"  (EM output over Sun's life ≈ {E_em_total/E_grav_sun*100:.1f}% "
          f"of gravitational binding)")

    # Gravitational force vs EM radiation pressure on each planet
    print(f"\n  GRAVITY vs RADIATION PRESSURE on each body:")
    print(f"  {'Body':12s}  {'F_grav (N)':>14s}  {'F_rad (N)':>14s}  {'ratio':>14s}")
    print(f"  {'-'*12}  {'-'*14}  {'-'*14}  {'-'*14}")

    for name, (mass, r_au) in sorted(bodies.items(), key=lambda x: x[1][1]):
        if name in ('Oort', 'Kuiper', 'Asteroids'):
            continue
        r_m = r_au * AU
        F_grav = G * M_sun * mass / r_m**2
        # radiation pressure: L/(4*pi*r^2*c) * cross-section
        # Use geometric cross-section estimate
        R_body = (3 * mass / (4 * np.pi * 5000))**(1/3)  # rough radius from mass
        F_rad = L_sun / (4 * np.pi * r_m**2 * c) * np.pi * R_body**2
        ratio = F_grav / F_rad if F_rad > 0 else float('inf')
        print(f"  {name:12s}  {F_grav:14.3e}  {F_rad:14.3e}  {ratio:14.1e}")

    # Magnetic pressure vs gravitational pressure at various distances
    print(f"\n  MAGNETIC PRESSURE vs GRAVITATIONAL 'PRESSURE':")
    print(f"  {'Distance':>12s}  {'P_mag (Pa)':>14s}  {'a_grav (m/s²)':>14s}  "
          f"{'B field (T)':>14s}")
    print(f"  {'-'*12}  {'-'*14}  {'-'*14}  {'-'*14}")

    for r_au in [0.1, 0.387, 1.0, 5.2, 30, 120, 1000]:
        r_m = r_au * AU
        B = B_sun_at(r_m)
        P_mag = B**2 / (2 * mu_0)
        a_grav = G * M_sun / r_m**2
        print(f"  {r_au:10.1f} AU  {P_mag:14.3e}  {a_grav:14.3e}  {B:14.3e}")


# =====================================================================
# PART 3: C(r) ON PHYSICAL DISTANCES — where does it map?
# =====================================================================

def part3_Cr_physical():
    print()
    print("=" * 78)
    print("PART 3: C(r) ON PHYSICAL DISTANCES")
    print("=" * 78)

    print(f"\n  C(r) = (1+2r) exp(-r/3) exp(i*pi*r/4)")
    print(f"  Peak |C(r)| at r_opt = 2.5")
    print(f"  Phase = pi/4 per unit r (quarter turn per unit)")
    print(f"  Full phase rotation at r = 8")
    print(f"  Effectively dead (< 0.1%) by r ~ 25")
    print()

    # If r is measured in different units, where does r_opt land?
    print(f"  IF r IS IN AU:")
    print(f"    r_opt = 2.5 AU  → asteroid belt (Mars-Jupiter gap)")
    print(f"    r = 8 AU        → between Jupiter and Saturn (full phase rotation)")
    print(f"    r = 25 AU       → near Neptune (C(r) effectively zero)")
    print(f"    Heliosphere at 120 AU: C(120) = {abs((1+240)*np.exp(-40)*np.exp(1j*30*np.pi)):.3e}")
    print()

    # What if the unit is set by something physical?
    # Candidate: r = distance / (some characteristic EM length)

    # Solar system characteristic lengths
    print(f"  CANDIDATE NATURAL UNITS FOR r:")
    print()

    # 1. If r = distance / 1 AU
    print(f"  1) r = distance / AU:")
    print(f"     r_opt = 2.5 AU = {2.5 * AU:.3e} m")
    print(f"     Peak coherence between Mars (1.52 AU) and Jupiter (5.2 AU)")
    print(f"     The asteroid belt IS the peak coherence zone")
    print()

    # 2. If r = distance / (R_sun)
    print(f"  2) r = distance / R_sun:")
    r_earth_Rsun = AU / R_sun
    print(f"     Earth is at r = {r_earth_Rsun:.1f} R_sun")
    print(f"     r_opt = 2.5 R_sun = {2.5 * R_sun / AU:.4f} AU "
          f"(inside Mercury orbit)")
    print(f"     This scale is too small — peak coherence inside Mercury")
    print()

    # 3. If unit set so r_opt = Earth orbit
    unit_earth = AU / 2.5
    print(f"  3) r = distance / {unit_earth:.3e} m  (so r_opt = Earth):")
    print(f"     r_opt = Earth (1 AU)")
    print(f"     Unit = {unit_earth/AU:.2f} AU = {unit_earth/R_sun:.1f} R_sun")
    print(f"     Full rotation (r=8) = {8 * unit_earth / AU:.1f} AU (Jupiter)")
    print(f"     Dead zone (r=25) = {25 * unit_earth / AU:.1f} AU (Uranus)")
    print()

    # 4. If unit set so full rotation = heliopause
    unit_helio = heliopause_AU * AU / 8
    print(f"  4) r = distance / {unit_helio:.3e} m  (so r=8 = heliopause):")
    print(f"     Unit = {unit_helio/AU:.1f} AU")
    print(f"     r_opt = 2.5 × {unit_helio/AU:.1f} = {2.5*unit_helio/AU:.0f} AU")
    print(f"     (Peak coherence at {2.5*unit_helio/AU:.0f} AU — between Saturn and Uranus)")
    print(f"     Dead zone (r=25) = {25*unit_helio/AU:.0f} AU")
    print()

    # 5. If unit set so dead zone = Oort cloud
    unit_oort = oort_outer_AU * AU / 25
    print(f"  5) r = distance / {unit_oort:.3e} m  (so r=25 = Oort outer edge):")
    print(f"     Unit = {unit_oort/AU:.0f} AU")
    print(f"     r_opt = {2.5*unit_oort/AU:.0f} AU ({2.5*unit_oort/ly:.2f} ly)")
    print(f"     Full rotation (r=8) = {8*unit_oort/AU:.0f} AU ({8*unit_oort/ly:.2f} ly)")
    print(f"     Dead zone = {oort_outer_AU} AU ({oort_outer_AU*AU/ly:.2f} ly)")
    print(f"     Alpha Centauri at r = {alpha_cen_distance*AU/unit_oort:.1f}")
    print()


# =====================================================================
# PART 4: THE QUARTER TURN — what is pi/4 physically?
# =====================================================================

def part4_quarter_turn():
    print()
    print("=" * 78)
    print("PART 4: THE QUARTER TURN — pi/4 in physical terms")
    print("=" * 78)

    # Sun's rotation
    print(f"\n  SUN'S ROTATION:")
    print(f"    Period = {P_sun_equator/86400:.2f} days")
    print(f"    Quarter turn = {P_sun_equator/86400/4:.2f} days = {P_sun_equator/4:.0f} s")
    print(f"    One-eighth turn (pi/4) = {P_sun_equator/86400/8:.2f} days "
          f"= {P_sun_equator/8:.0f} s")
    print()

    # How far does light travel in one Sun quarter-turn?
    d_quarter = c * P_sun_equator / 4
    d_eighth = c * P_sun_equator / 8
    print(f"  LIGHT TRAVEL in one Sun rotation phase:")
    print(f"    Quarter turn (pi/2): {d_quarter:.3e} m = {d_quarter/AU:.2f} AU")
    print(f"    Eighth turn (pi/4):  {d_eighth:.3e} m = {d_eighth/AU:.2f} AU")
    print(f"    Full rotation (2pi): {c*P_sun_equator:.3e} m = {c*P_sun_equator/AU:.1f} AU")
    print()

    # How far does solar wind travel in one quarter-turn?
    d_wind_quarter = solar_wind_speed * P_sun_equator / 4
    d_wind_eighth = solar_wind_speed * P_sun_equator / 8
    print(f"  SOLAR WIND TRAVEL in one Sun rotation phase:")
    print(f"    Quarter turn (pi/2): {d_wind_quarter:.3e} m = {d_wind_quarter/AU:.4f} AU")
    print(f"    Eighth turn (pi/4):  {d_wind_eighth:.3e} m = {d_wind_eighth/AU:.4f} AU")
    print(f"    Full rotation (2pi): {solar_wind_speed*P_sun_equator:.3e} m "
          f"= {solar_wind_speed*P_sun_equator/AU:.3f} AU")
    print()

    # Parker spiral angle
    # At distance r, the spiral angle theta satisfies tan(theta) = omega*r / v_wind
    print(f"  PARKER SPIRAL (EM field geometry from spin + wind):")
    print(f"  {'Distance':>10s}  {'spiral angle':>14s}  {'B_radial':>12s}  {'B_tangential':>14s}")
    print(f"  {'-'*10}  {'-'*14}  {'-'*12}  {'-'*14}")

    for r_au in [0.3, 1.0, 2.5, 5.2, 10, 30, 120]:
        r_m = r_au * AU
        tan_theta = omega_sun * r_m / solar_wind_speed
        theta = np.arctan(tan_theta)
        B_r = B_sun_at(r_m)  # radial (dipole, overestimate but shape is right)
        # At large r, tangential B dominates: B_phi ~ B_r * tan(theta)
        # More accurately for Parker spiral: B_phi = -B_0*(R_sun/r)*sin(theta)*omega*r/v_sw
        B_r_parker = B_sun_surface * (R_sun / r_m)**2  # radial component (1/r^2)
        B_phi = B_r_parker * omega_sun * r_m / solar_wind_speed  # tangential
        print(f"  {r_au:8.1f} AU  {np.degrees(theta):12.1f}°  "
              f"{B_r_parker:12.3e} T  {B_phi:14.3e} T")

    print()
    print(f"  KEY OBSERVATION:")
    print(f"  The Parker spiral angle reaches 45° (pi/4) at:")
    # tan(pi/4) = 1 = omega*r/v_wind → r = v_wind/omega
    r_45 = solar_wind_speed / omega_sun
    print(f"    r = v_wind / omega_sun = {r_45:.3e} m = {r_45/AU:.2f} AU")
    print(f"    This is {r_45/AU:.2f} AU — right at Earth's orbit!")
    print()
    print(f"  At this distance, radial and tangential B components are EQUAL.")
    print(f"  The EM field geometry has its 'quarter turn' at ~1 AU.")


# =====================================================================
# PART 5: SPIN FROM EM — can we predict the Sun's rotation?
# =====================================================================

def part5_spin_from_em():
    print()
    print("=" * 78)
    print("PART 5: CAN WE PREDICT THE SUN'S SPIN FROM ITS EM + MASS?")
    print("=" * 78)

    # Total orbital angular momentum
    total_L_orb = 0
    for name, (mass, r_au) in bodies.items():
        r_m = r_au * AU
        if r_au < 100000:
            v_orb = np.sqrt(G * M_sun / r_m)
            total_L_orb += mass * v_orb * r_m

    print(f"\n  Total angular momentum budget:")
    print(f"    Sun's spin:      {L_ang_sun:.3e} kg⋅m²/s")
    print(f"    Orbital (all):   {total_L_orb:.3e} kg⋅m²/s")
    print(f"    Total:           {total_L_orb + L_ang_sun:.3e} kg⋅m²/s")
    print(f"    Sun fraction:    {L_ang_sun/(total_L_orb+L_ang_sun)*100:.2f}%")
    print()

    # Angular momentum carried by EM radiation
    # Photon angular momentum: L_photon = energy / (omega)
    # Total EM angular momentum flux from Sun:
    # L_dot_em = L_sun / omega_sun (if all photons carry spin aligned with rotation)
    # This is an upper bound
    L_dot_em_max = L_sun / omega_sun
    print(f"  EM angular momentum flux (upper bound):")
    print(f"    L_dot = L_sun / omega = {L_dot_em_max:.3e} kg⋅m²/s²")
    print(f"    Over 4.6 Gyr: {L_dot_em_max * 4.6e9 * 3.156e7:.3e} kg⋅m²/s")
    print(f"    Compare to Sun's current spin L: {L_ang_sun:.3e}")
    print(f"    Ratio (lost/current): "
          f"{L_dot_em_max * 4.6e9 * 3.156e7 / L_ang_sun:.1f}x")
    print()

    # Solar wind angular momentum (magnetic braking)
    # Each parcel carries L = m * v_phi * r, where v_phi ~ omega * r_Alfven
    r_alfven = 15 * AU  # Alfven radius (~10-20 AU)
    v_phi_alfven = omega_sun * r_alfven
    L_dot_wind = solar_wind_mass_rate * v_phi_alfven * r_alfven
    print(f"  Solar wind angular momentum (magnetic braking):")
    print(f"    Alfven radius: ~{r_alfven/AU:.0f} AU")
    print(f"    v_phi at Alfven: {v_phi_alfven:.0f} m/s")
    print(f"    L_dot_wind = {L_dot_wind:.3e} kg⋅m²/s²")
    print(f"    Over 4.6 Gyr: {L_dot_wind * 4.6e9 * 3.156e7:.3e} kg⋅m²/s")
    print(f"    This IS why the Sun spins slowly — magnetic braking over Gyr")
    print()

    # The question: does the spin rate relate to EM output via a quarter-turn?
    print(f"  QUARTER-TURN TEST:")
    print(f"    If spin omega = (EM coupling) / (mass moment):")

    # Energy ratio
    E_rot = 0.5 * I_sun * omega_sun**2
    print(f"    Sun's rotational KE:     {E_rot:.3e} J")
    print(f"    1 second of EM output:   {L_sun:.3e} J")
    print(f"    Time to radiate E_rot:   {E_rot/L_sun:.0f} s = {E_rot/L_sun/86400:.1f} days")
    print(f"    Compare to rotation:     {P_sun_equator/86400:.1f} days")
    print(f"    Ratio:                   {E_rot/L_sun / P_sun_equator:.4f}")
    print()

    # Dimensionless ratios
    print(f"  DIMENSIONLESS RATIOS (looking for structure):")
    print(f"    L_sun * P_sun / (G * M_sun^2 / c):")
    ratio1 = L_sun * P_sun_equator / (G * M_sun**2 / c)
    print(f"      = {ratio1:.6f}")
    print()

    print(f"    omega_sun * R_sun / c (surface velocity / c):")
    beta = omega_sun * R_sun / c
    print(f"      = {beta:.6e}")
    print(f"      1/beta = {1/beta:.0f}")
    print()

    print(f"    (v_surface / c) * (M_sun * c^2 / L_sun):")
    ratio2 = beta * M_sun * c**2 / L_sun
    print(f"      = {ratio2:.3e}")
    print()

    # Magnetic to gravitational energy ratio
    E_mag = (B_sun_surface**2 / (2 * mu_0)) * (4/3 * np.pi * R_sun**3)
    E_grav = 3 * G * M_sun**2 / (5 * R_sun)
    print(f"    E_magnetic / E_gravitational:")
    print(f"      E_mag  = {E_mag:.3e} J")
    print(f"      E_grav = {E_grav:.3e} J")
    print(f"      ratio  = {E_mag/E_grav:.3e}")
    print()


# =====================================================================
# PART 6: THE BUBBLE — what sets the heliosphere boundary?
# =====================================================================

def part6_bubble():
    print()
    print("=" * 78)
    print("PART 6: THE BUBBLE — heliosphere, Oort cloud, Hill sphere")
    print("=" * 78)

    # Ram pressure balance: solar wind vs ISM
    # P_sw = 0.5 * rho_sw * v_sw^2 = P_ISM
    # rho_sw at distance r: rho = m_dot / (4*pi*r^2*v_sw)
    # So P_sw(r) = m_dot * v_sw / (8*pi*r^2)
    # Balance: r_heliopause = sqrt(m_dot * v_sw / (8*pi*P_ISM))

    P_ISM = 3e-13  # Pa (interstellar medium pressure, rough)
    r_balance = np.sqrt(solar_wind_mass_rate * solar_wind_speed / (8 * np.pi * P_ISM))
    print(f"\n  HELIOPAUSE from pressure balance:")
    print(f"    Solar wind ram pressure = ISM pressure")
    print(f"    P_ISM ≈ {P_ISM:.1e} Pa")
    print(f"    Predicted heliopause: {r_balance:.3e} m = {r_balance/AU:.0f} AU")
    print(f"    Measured (Voyager 1): {heliopause_AU} AU")
    print(f"    Agreement: {r_balance/AU/heliopause_AU*100:.0f}%")
    print()

    # Hill sphere (gravitational boundary)
    # r_Hill = a * (M_sun / 3*M_galaxy)^(1/3)
    # Sun orbits at ~8 kpc from galactic center
    # M_galaxy(< 8 kpc) ~ 1e11 M_sun
    r_galactic = 8e3 * pc  # 8 kpc
    M_galaxy_enclosed = 1e11 * M_sun
    r_hill = r_galactic * (M_sun / (3 * M_galaxy_enclosed))**(1/3)
    print(f"  HILL SPHERE (gravitational dominance):")
    print(f"    Galactic orbit: {r_galactic/pc:.0f} pc")
    print(f"    M_galaxy(< 8kpc): {M_galaxy_enclosed:.1e} kg")
    print(f"    Hill sphere: {r_hill:.3e} m = {r_hill/ly:.2f} ly")
    print(f"    Oort cloud outer: {oort_outer_AU * AU / ly:.2f} ly")
    print(f"    Alpha Centauri: 4.37 ly")
    print()

    # Do the bubbles overlap?
    print(f"  DO THE BUBBLES OVERLAP?")
    print(f"    Sun's Hill sphere:          {r_hill/ly:.2f} ly radius")
    print(f"    Alpha Centauri's (similar):  ~{r_hill/ly:.2f} ly radius")
    print(f"    Separation:                 4.37 ly")
    print(f"    Gap (if any):               {4.37 - 2*r_hill/ly:.2f} ly")
    if 2 * r_hill / ly > 4.37:
        print(f"    >>> OVERLAP: the gravitational bubbles TOUCH <<<")
    else:
        print(f"    >>> GAP: bubbles don't quite reach each other <<<")


# =====================================================================
# PART 7: THE FOUNDING QUESTION
# =====================================================================

def part7_founding_question():
    print()
    print("=" * 78)
    print("PART 7: IS GRAVITY A PRODUCT OF ELECTROMAGNETISM?")
    print("=" * 78)

    # What this data tells us
    print(f"""
  WHAT THE NUMBERS SAY:

  1. The Sun's EM output (3.8e26 W) is enormous, but gravity is
     ~10^13 times stronger than radiation pressure on every planet.
     Direct EM force cannot BE gravity.

  2. BUT: the Parker spiral reaches its pi/4 (quarter turn) at
     {solar_wind_speed/omega_sun/AU:.2f} AU — right at Earth's orbit.
     The EM GEOMETRY has a natural quarter-turn scale.

  3. The heliosphere (EM bubble) extends to ~120 AU.
     The Hill sphere (gravitational bubble) extends to ~1-2 ly.
     The gravitational influence extends ~500x farther than the EM wind.

  4. Angular momentum: the Sun's EM (via magnetic braking) has
     TRANSFERRED angular momentum from the Sun to the planets
     over 4.6 Gyr. The Sun spins slowly BECAUSE of EM coupling.
     EM and gravity are entangled in the angular momentum budget.

  5. The Sun's magnetic field energy ({(B_sun_surface**2/(2*mu_0))*(4/3*np.pi*R_sun**3):.3e} J)
     is ~10^-6 of its gravitational binding energy ({3*G*M_sun**2/(5*R_sun):.3e} J).
     But energy isn't the only measure — STRUCTURE matters.

  OPEN QUESTION:
  If C(r) connects EM to gravity, what sets the unit of r?
  The Parker spiral quarter-turn at ~1 AU is suggestive.
  The phase rate pi/4 in C(r) matching the spiral geometry is
  either coincidence or the key.
""")


# =====================================================================
# MAIN
# =====================================================================

def main():
    part1_solar_inventory()
    part2_em_vs_gravity()
    part3_Cr_physical()
    part4_quarter_turn()
    part5_spin_from_em()
    part6_bubble()
    part7_founding_question()


if __name__ == "__main__":
    main()
