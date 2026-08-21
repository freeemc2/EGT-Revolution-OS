// Three Rocks — coil sweep + T-state hunt firmware (Teensy 4.1, bare metal)
//
// Drives the twisted PAIR (both wires PARALLEL / same direction) with a
// phase-accumulator square wave, samples the RUNNER (the 22ga signal wire that
// sits along the pair), and runs a software LOCK-IN AMPLIFIER: every sample is
// multiplied against the drive reference (sin/cos from the same phase
// accumulator), so we read the drive-referenced phase of the coil's response
// directly. Sweep the band, read arg(C(r)) at r_opt = 2.5.
//
// *** WIRING CORRECTION 2026-08-21 (Brian) — READ BEFORE ANY PHYSICS ***
// The pair must run PARALLEL (same direction), NOT bucking/opposing. Bucking
// attenuates the runner coupling ~20x (all measurements before this date were on
// the WRONG, attenuated topology). The RUNNER — not "winding B" — is the sense.
//   pin 3  --- 220R --- BOTH pair-wire starts   (BOTH pair-wire ends -> GND)  [parallel drive]
//   runner (22ga): GND ---- runner ---- A0 (pin 14)                            [sense]
//   bias: 10k from 3.3V to A0, 10k from A0 to GND (centers sense at ~1.65V)
//   core: swappable in the PVC bore. 4-way tested 2026-08-21: AIR couples
//         STRONGEST (cores act as flux excluders at kHz, not concentrators);
//         iron/Nd both REDUCE coupling vs air. Nd pole-flip = null (coupling is
//         DC-field-direction-blind). See journal "4-WAY CORE COMPARISON".
//   NOTE: v1 header claimed "drive winding A, sense winding B, runner floating" —
//         that was STALE/wrong; the runner has always been the A0 sense wire.
//
// Serial protocol (115200+, USB):
//   "P"                      -> "R PONG sweep <cpu_mhz>"
//   "S <f0> <f1> <points>"   -> log sweep, streams "F <freq_hz> <phase_deg> <mag>"
//                               then "R SWEEPDONE"
//   "L <freq_hz>"            -> lock mode: continuous "T <freq> <phase_deg> <mag>"
//                               ~5 lines/s until any byte received -> "R LOCKED off"
//
// Phase convention: positive = response lags drive. Integration: 40 ms or
// >= 20 cycles per point, whichever is longer.

#include <Arduino.h>
#include <ADC.h>

const int DRIVE_PIN = 3;
const int SENSE_PIN = A0;
const float FS = 80000.0f;          // sample rate (Hz) — band ceiling ~25 kHz honest
const float TWO_PI_F = 6.28318530718f;

ADC *adc = new ADC();
IntervalTimer sampler;

// shared between ISR and loop
volatile float phase = 0.0f, dphi = 0.0f;
volatile double accI = 0.0, accQ = 0.0;
volatile uint32_t nsamp = 0;
volatile bool acquiring = false;
volatile int dcOffset = 2048;   // 12-bit midpoint; refined by measureDC() at boot

// --- differential drive modes -----------------------------------------------
// 0 = pure carrier. 1 = C(r)-patterned phase offsets. 2 = random offsets at the
// SAME RMS as mode 1. Offsets are applied to the DRIVE only; the lock-in
// reference stays the pure carrier, so we measure surviving fundamental
// coupling under each treatment. Tables are zero-mean, RMS = 0.35 rad.
volatile int driveMode = 0;
const int PAT_N = 8;
float crPat[PAT_N];        // from (1+2r)e^(-r/3), r=0..7, zero-mean, RMS-scaled
float rndPat[PAT_N];       // fixed pseudo-random, zero-mean, same RMS
float shufPat[PAT_N];      // crPat VALUES in shuffled order (sequence control)
const int SHUF[PAT_N] = {5, 0, 3, 6, 1, 7, 2, 4};
volatile int patIdx = 0;
volatile float curOffset = 0.0f;
// glitch-free drive: separate phase accumulator, offset reached by frequency
// nudging spread across each cycle (pure FM — no waveform discontinuities)
volatile float drivePhase = 0.0f, driveDphi = 0.0f;

// --- two-tone drive + dual lock-in (qubit test: hold N=96 and N=128 at once) -
// When twoTone is set, the drive pin outputs the 1-bit comparator of the summed
// sines (both fundamentals injected on one pin; the coil low-passes), and the
// lock-in runs at BOTH frequencies at once. Lets us hold the classical (f_lo,
// ~90 deg) and quantum (f_hi, ~114 deg) states at the same instant and read
// each one's coupling. Existing single-tone paths untouched.
volatile bool twoTone = false;
volatile float phaseLo = 0.0f, phaseHi = 0.0f;
volatile float dphiLo = 0.0f, dphiHi = 0.0f;
volatile double accI_lo = 0.0, accQ_lo = 0.0, accI_hi = 0.0, accQ_hi = 0.0;
// per-tone amplitudes for W2 command (drive-scaling test): 1.0 each = comparator equivalent
volatile float ampLo = 1.0f, ampHi = 1.0f;
volatile float sd_acc_two = 0.0f;
// jammer tone (v4): in-band EM interference to test coupling-channel robustness.
// ampJam=0 by default (off). When non-zero, isr2 sums a third sine into the SD encoder.
volatile float ampJam = 0.0f;
volatile float phaseJam = 0.0f, dphiJam = 0.0f;
// beat-frequency lock-in (v5): measures response at |f_hi - f_lo|. This is the C(r)
// superposition cross-term signature per Brian's Two Rocks framework. Reference phase
// accumulates at the beat rate; no drive at this frequency, purely detection.
volatile float phaseBeat = 0.0f, dphiBeat = 0.0f;
volatile double accI_beat = 0.0, accQ_beat = 0.0;

// --- drive amplitude control (v2: isolate self-amplitude phase from interaction) -
// driveAmp 1.0 = full square wave (default, unchanged). <1.0 = 1-bit sigma-delta of
// driveAmp*sin(drivePhase): the coil low-passes the pulse density into a clean sine
// of controllable amplitude. Lets us drive N=128 ALONE at the reduced two-tone
// amplitude and watch its phase — no dummy, no corruption.
volatile float driveAmp = 1.0f;
volatile float sd_acc = 0.0f;

void buildPatterns() {
  float w[PAT_N], mean = 0;
  for (int r = 0; r < PAT_N; r++) { w[r] = (1.0f + 2.0f * r) * expf(-r / 3.0f); mean += w[r]; }
  mean /= PAT_N;
  float rms = 0;
  for (int r = 0; r < PAT_N; r++) { w[r] -= mean; rms += w[r] * w[r]; }
  rms = sqrtf(rms / PAT_N);
  for (int r = 0; r < PAT_N; r++) crPat[r] = w[r] * (0.35f / rms);
  // fixed random-ish sequence (deterministic so runs are repeatable)
  float rw[PAT_N] = {0.71f, -0.32f, -0.95f, 0.48f, 0.12f, -0.61f, 0.88f, -0.31f};
  float rmean = 0; for (int r = 0; r < PAT_N; r++) rmean += rw[r];
  rmean /= PAT_N;
  float rrms = 0; for (int r = 0; r < PAT_N; r++) { rw[r] -= rmean; rrms += rw[r] * rw[r]; }
  rrms = sqrtf(rrms / PAT_N);
  for (int r = 0; r < PAT_N; r++) rndPat[r] = rw[r] * (0.35f / rrms);
  for (int r = 0; r < PAT_N; r++) shufPat[r] = crPat[SHUF[r]];
}

void isr2() {
  // two-tone (+ optional jammer): sigma-delta of ampLo*sinLo + ampHi*sinHi + ampJam*sinJam.
  // With ampJam=0 (default) behaves identical to v3. Comparator fast-path only when
  // all amps are near 1.0 and jammer is off.
  if (ampLo >= 0.999f && ampHi >= 0.999f && ampJam < 1e-4f) {
    digitalWriteFast(DRIVE_PIN, (sinf(phaseLo) + sinf(phaseHi) >= 0.0f) ? HIGH : LOW);
  } else {
    sd_acc_two += ampLo * sinf(phaseLo) + ampHi * sinf(phaseHi);
    if (ampJam > 1e-4f) sd_acc_two += ampJam * sinf(phaseJam);
    if (sd_acc_two >= 0.0f) { digitalWriteFast(DRIVE_PIN, HIGH); sd_acc_two -= 1.0f; }
    else                    { digitalWriteFast(DRIVE_PIN, LOW);  sd_acc_two += 1.0f; }
  }
  int v2 = adc->adc0->analogReadContinuous();
  if (acquiring) {
    float s = (float)(v2 - dcOffset);
    accI_lo   += s * cosf(phaseLo);   accQ_lo   += s * sinf(phaseLo);
    accI_hi   += s * cosf(phaseHi);   accQ_hi   += s * sinf(phaseHi);
    accI_beat += s * cosf(phaseBeat); accQ_beat += s * sinf(phaseBeat);
    nsamp++;
  }
  phaseLo   += dphiLo;   if (phaseLo   >= TWO_PI_F) phaseLo   -= TWO_PI_F;
  phaseHi   += dphiHi;   if (phaseHi   >= TWO_PI_F) phaseHi   -= TWO_PI_F;
  phaseJam  += dphiJam;  if (phaseJam  >= TWO_PI_F) phaseJam  -= TWO_PI_F;
  phaseBeat += dphiBeat; if (phaseBeat >= TWO_PI_F) phaseBeat -= TWO_PI_F;
}

void isr() {
  if (twoTone) { isr2(); return; }
  if (driveAmp >= 0.999f) {
    digitalWriteFast(DRIVE_PIN, (drivePhase < 3.14159265f) ? HIGH : LOW);
  } else {
    sd_acc += driveAmp * sinf(drivePhase);     // 1-bit sigma-delta -> amplitude control
    if (sd_acc >= 0.0f) { digitalWriteFast(DRIVE_PIN, HIGH); sd_acc -= 1.0f; }
    else                { digitalWriteFast(DRIVE_PIN, LOW);  sd_acc += 1.0f; }
  }
  int v = adc->adc0->analogReadContinuous();
  if (acquiring) {
    float s = (float)(v - dcOffset);
    accI += s * cosf(phase);
    accQ += s * sinf(phase);
    nsamp++;
  }
  phase += dphi;
  if (phase >= TWO_PI_F) phase -= TWO_PI_F;
  drivePhase += driveDphi;
  if (drivePhase >= TWO_PI_F) {
    drivePhase -= TWO_PI_F;
    // new drive cycle: pick next target offset, nudge frequency so the phase
    // error is absorbed smoothly across the coming cycle (glitch-free FM)
    patIdx = (patIdx + 1) % PAT_N;
    float target = 0.0f;
    if (driveMode == 1) target = crPat[patIdx];
    else if (driveMode == 2) target = rndPat[patIdx];
    else if (driveMode == 3) target = shufPat[patIdx];
    float off = drivePhase - phase;                 // current offset
    if (off > 3.14159265f) off -= TWO_PI_F;
    if (off < -3.14159265f) off += TWO_PI_F;
    float err = target - off;
    driveDphi = dphi + err * dphi / TWO_PI_F;       // spread err over one cycle
  }
}

void setFreq(float f) {
  noInterrupts();
  twoTone = false;
  dphi = TWO_PI_F * f / FS;
  driveDphi = dphi;
  drivePhase = phase;
  patIdx = 0;
  interrupts();
}

void measureDC() {
  // rough DC bias of the sense line with drive off
  long acc = 0;
  for (int i = 0; i < 256; i++) { acc += adc->adc0->analogReadContinuous(); delayMicroseconds(20); }
  dcOffset = acc / 256;
}

// integration time (ms) — settable via I command; long = narrow lock-in bandwidth
volatile float integ_ms = 500.0f;

// one lock-in point at frequency f. returns phase (deg, 0..360) and mag
void point(float f, float *ph_deg, float *mag) {
  setFreq(f);
  // settle 20 cycles or 20 ms
  float settle_s = max(20.0f / f, 0.020f);
  delayMicroseconds((uint32_t)(settle_s * 1e6f));
  // integrate: >=40 cycles and >= integ_ms (bandwidth ~ 1/integ_s: 500ms -> ~2Hz)
  float integ_s = max(40.0f / f, integ_ms / 1000.0f);
  noInterrupts(); accI = 0; accQ = 0; nsamp = 0; acquiring = true; interrupts();
  delayMicroseconds((uint32_t)(integ_s * 1e6f));
  noInterrupts(); acquiring = false;
  double I = accI, Q = accQ; uint32_t n = nsamp; interrupts();
  float p = atan2f((float)Q, (float)I) * 180.0f / 3.14159265f;
  if (p < 0) p += 360.0f;
  *ph_deg = p;
  *mag = (n > 0) ? sqrtf((float)(I * I + Q * Q)) / (float)n : 0.0f;
}

// two-tone frequency setter + dual lock-in point
void setFreq2(float flo, float fhi) {
  noInterrupts();
  dphiLo = TWO_PI_F * flo / FS;
  dphiHi = TWO_PI_F * fhi / FS;
  float fbeat = fhi - flo; if (fbeat < 0) fbeat = -fbeat;
  dphiBeat = TWO_PI_F * fbeat / FS;
  sd_acc_two = 0.0f;
  phaseBeat = 0.0f;
  twoTone = true;
  interrupts();
}

void point2(float flo, float fhi, float *phlo, float *mglo, float *phhi, float *mghi) {
  setFreq2(flo, fhi);
  float fmin = (flo < fhi) ? flo : fhi;
  float settle_s = max(20.0f / fmin, 0.020f);
  delayMicroseconds((uint32_t)(settle_s * 1e6f));
  float integ_s = max(40.0f / fmin, integ_ms / 1000.0f);
  noInterrupts(); accI_lo = accQ_lo = accI_hi = accQ_hi = 0; nsamp = 0; acquiring = true; interrupts();
  delayMicroseconds((uint32_t)(integ_s * 1e6f));
  noInterrupts(); acquiring = false;
  double Il = accI_lo, Ql = accQ_lo, Ih = accI_hi, Qh = accQ_hi; uint32_t n = nsamp; interrupts();
  float pl = atan2f((float)Ql, (float)Il) * 180.0f / 3.14159265f; if (pl < 0) pl += 360.0f;
  float pj = atan2f((float)Qh, (float)Ih) * 180.0f / 3.14159265f; if (pj < 0) pj += 360.0f;
  *phlo = pl; *phhi = pj;
  *mglo = (n > 0) ? sqrtf((float)(Il * Il + Ql * Ql)) / (float)n : 0.0f;
  *mghi = (n > 0) ? sqrtf((float)(Ih * Ih + Qh * Qh)) / (float)n : 0.0f;
}

// v5: two-tone point that ALSO returns the beat-frequency lock-in response.
// The beat mag/phase = the C(r) superposition cross-term signature per Two Rocks.
void point3(float flo, float fhi, float *phlo, float *mglo, float *phhi, float *mghi,
            float *phbt, float *mgbt) {
  setFreq2(flo, fhi);
  float fmin = (flo < fhi) ? flo : fhi;
  float settle_s = max(20.0f / fmin, 0.020f);
  delayMicroseconds((uint32_t)(settle_s * 1e6f));
  float integ_s = max(40.0f / fmin, integ_ms / 1000.0f);
  noInterrupts();
  accI_lo = accQ_lo = accI_hi = accQ_hi = accI_beat = accQ_beat = 0;
  nsamp = 0; acquiring = true;
  interrupts();
  delayMicroseconds((uint32_t)(integ_s * 1e6f));
  noInterrupts(); acquiring = false;
  double Il = accI_lo, Ql = accQ_lo, Ih = accI_hi, Qh = accQ_hi;
  double Ib = accI_beat, Qb = accQ_beat;
  uint32_t n = nsamp; interrupts();
  float pl = atan2f((float)Ql, (float)Il) * 180.0f / 3.14159265f; if (pl < 0) pl += 360.0f;
  float pj = atan2f((float)Qh, (float)Ih) * 180.0f / 3.14159265f; if (pj < 0) pj += 360.0f;
  float pb = atan2f((float)Qb, (float)Ib) * 180.0f / 3.14159265f; if (pb < 0) pb += 360.0f;
  *phlo = pl; *phhi = pj; *phbt = pb;
  *mglo = (n > 0) ? sqrtf((float)(Il * Il + Ql * Ql)) / (float)n : 0.0f;
  *mghi = (n > 0) ? sqrtf((float)(Ih * Ih + Qh * Qh)) / (float)n : 0.0f;
  *mgbt = (n > 0) ? sqrtf((float)(Ib * Ib + Qb * Qb)) / (float)n : 0.0f;
}

void setup() {
  pinMode(DRIVE_PIN, OUTPUT);
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}
  adc->adc0->setAveraging(1);
  adc->adc0->setResolution(12);
  adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::VERY_HIGH_SPEED);
  adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::VERY_HIGH_SPEED);
  adc->adc0->startContinuous(SENSE_PIN);
  measureDC();
  buildPatterns();
  setFreq(1000.0f);
  sampler.begin(isr, 1e6f / FS);   // 10 us
}

static char line[96];

void loop() {
  int len = 0;
  while (true) {
    if (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') break;
      if (len < 95) line[len++] = c;
    }
  }
  line[len] = 0;

  if (line[0] == 'P') {
    Serial.print("R PONG sweep "); Serial.println(F_CPU / 1000000);
    return;
  }
  if (line[0] == 'M') {           // mode: 0=pure 1=C(r) 2=random 3=C(r)-shuffled
    int m = 0; sscanf(line + 1, "%d", &m);
    if (m < 0 || m > 3) m = 0;
    driveMode = m;
    Serial.print("R MODE "); Serial.println(m);
    return;
  }
  if (line[0] == 'D') {           // diagnostic: A0 DC level + spread over 200 ms
    int lo = 4095, hi = 0; long acc = 0; const int n = 2000;
    for (int i = 0; i < n; i++) {
      int v = adc->adc0->analogReadContinuous();
      acc += v; if (v < lo) lo = v; if (v > hi) hi = v;
      delayMicroseconds(100);
    }
    Serial.print("R DIAG mean="); Serial.print((float)acc / n, 1);
    Serial.print(" min="); Serial.print(lo);
    Serial.print(" max="); Serial.print(hi);
    Serial.println(" (4095=3.3V, midpoint=2048)");
    return;
  }
  if (line[0] == 'I') {           // set integration ms: "I 500"
    float ms = 500; sscanf(line + 1, "%f", &ms);
    if (ms < 50) ms = 50; if (ms > 5000) ms = 5000;
    integ_ms = ms;
    Serial.print("R INTEG "); Serial.println(ms, 0);
    return;
  }
  if (line[0] == 'A') {           // drive amplitude 0..1 (1=full square, <1=sigma-delta)
    float a = 1.0f; sscanf(line + 1, "%f", &a);
    if (a < 0.0f) a = 0.0f; if (a > 1.0f) a = 1.0f;
    driveAmp = a; sd_acc = 0.0f;
    Serial.print("R AMP "); Serial.println(a, 3);
    return;
  }
  if (line[0] == 'B') {           // v5: two-tone lock with beat readout: "B <flo> <fhi>"
    float flo = 4423, fhi = 8072; sscanf(line + 1, "%f %f", &flo, &fhi);
    ampLo = 1.0f; ampHi = 1.0f;
    while (!Serial.available()) {
      float pl, ml, pj, mj, pb, mb; point3(flo, fhi, &pl, &ml, &pj, &mj, &pb, &mb);
      float fbeat = fhi - flo; if (fbeat < 0) fbeat = -fbeat;
      Serial.print("T3 "); Serial.print(flo, 1); Serial.print(' ');
      Serial.print(pl, 3); Serial.print(' '); Serial.print(ml, 3); Serial.print(' ');
      Serial.print(fhi, 1); Serial.print(' ');
      Serial.print(pj, 3); Serial.print(' '); Serial.print(mj, 3); Serial.print(' ');
      Serial.print(fbeat, 1); Serial.print(' ');
      Serial.print(pb, 3); Serial.print(' '); Serial.println(mb, 3);
    }
    while (Serial.available()) Serial.read();
    ampLo = 1.0f; ampHi = 1.0f; twoTone = false;
    Serial.println("R LOCKED off");
    return;
  }
  if (line[0] == 'J') {           // jammer tone (v4): "J <freq_hz> <amp>"  (amp 0 = off)
    float jf = 6000.0f, ja = 0.0f; sscanf(line + 1, "%f %f", &jf, &ja);
    if (ja < 0.0f) ja = 0.0f; if (ja > 1.0f) ja = 1.0f;
    noInterrupts();
    dphiJam = TWO_PI_F * jf / FS;
    ampJam = ja;
    sd_acc_two = 0.0f;
    interrupts();
    Serial.print("R JAM "); Serial.print(jf, 1); Serial.print(' '); Serial.println(ja, 3);
    return;
  }
  if (line[0] == 'S') {
    float f0 = 500, f1 = 25000; int pts = 60;
    sscanf(line + 1, "%f %f %d", &f0, &f1, &pts);
    if (f0 < 50) f0 = 50;
    if (f1 > 40000) f1 = 40000;       // honest ADC ceiling at FS=100k
    if (pts < 2) pts = 2; if (pts > 400) pts = 400;
    float lr = logf(f1 / f0) / (pts - 1);
    for (int i = 0; i < pts; i++) {
      float f = f0 * expf(lr * i);
      float ph, mg; point(f, &ph, &mg);
      Serial.print("F "); Serial.print(f, 1); Serial.print(' ');
      Serial.print(ph, 3); Serial.print(' '); Serial.println(mg, 2);
    }
    Serial.println("R SWEEPDONE");
    return;
  }
  if (line[0] == 'L') {
    float f = 1000; sscanf(line + 1, "%f", &f);
    while (!Serial.available()) {
      float ph, mg; point(f, &ph, &mg);
      Serial.print("T "); Serial.print(f, 1); Serial.print(' ');
      Serial.print(ph, 4); Serial.print(' '); Serial.println(mg, 2);
    }
    while (Serial.available()) Serial.read();
    Serial.println("R LOCKED off");
    return;
  }
  if (line[0] == 'W' && line[1] == '2') {  // two-tone lock with amps: "W2 <flo> <fhi> <amp_lo> <amp_hi>"
    float flo = 4423, fhi = 8072, al = 1.0f, ah = 1.0f;
    sscanf(line + 2, "%f %f %f %f", &flo, &fhi, &al, &ah);
    if (al < 0) al = 0; if (al > 1) al = 1;
    if (ah < 0) ah = 0; if (ah > 1) ah = 1;
    ampLo = al; ampHi = ah;
    while (!Serial.available()) {
      float pl, ml, pj, mj; point2(flo, fhi, &pl, &ml, &pj, &mj);
      Serial.print("T2 "); Serial.print(flo, 1); Serial.print(' ');
      Serial.print(pl, 3); Serial.print(' '); Serial.print(ml, 2); Serial.print(' ');
      Serial.print(fhi, 1); Serial.print(' ');
      Serial.print(pj, 3); Serial.print(' '); Serial.println(mj, 2);
    }
    while (Serial.available()) Serial.read();
    ampLo = 1.0f; ampHi = 1.0f; twoTone = false;
    Serial.println("R LOCKED off");
    return;
  }
  if (line[0] == 'W') {           // two-tone lock: "W <f_lo> <f_hi>"  (both amps = 1.0)
    float flo = 4423, fhi = 8072; sscanf(line + 1, "%f %f", &flo, &fhi);
    ampLo = 1.0f; ampHi = 1.0f;
    while (!Serial.available()) {
      float pl, ml, pj, mj; point2(flo, fhi, &pl, &ml, &pj, &mj);
      Serial.print("T2 "); Serial.print(flo, 1); Serial.print(' ');
      Serial.print(pl, 3); Serial.print(' '); Serial.print(ml, 2); Serial.print(' ');
      Serial.print(fhi, 1); Serial.print(' ');
      Serial.print(pj, 3); Serial.print(' '); Serial.println(mj, 2);
    }
    while (Serial.available()) Serial.read();
    twoTone = false;
    Serial.println("R LOCKED off");
    return;
  }
  Serial.println("R ERR badcmd");
}
