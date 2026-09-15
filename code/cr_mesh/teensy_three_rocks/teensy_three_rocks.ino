// TEENSY THREE ROCKS — 3-coil EGT drive + pair-select runner sense (Teensy 4.1).
// Purpose-built for the N=3 test: three coils, one crystal, shared jitter. Drives 3
// strands; reads TWO runners at a time (the 4.1 has only two ADC engines), both plain
// single-shot every tick — no continuous mode anywhere (stop/restart of a continuous
// run made the channel read a dead floor). Select the pair with "C <a> <b>".
//
// WIRING (Brian's build, 2026-09-14):
//   Drive: pin 2 -> 220ohm -> coil (K0), pin 3 -> 220ohm -> coil (K1), pin 1 -> 220ohm -> coil (K2)
//          winding south ends -> GND
//   Sense: runner south ends -> A0 / A1 / A2, runner north ends -> GND
//   All coils share one crystal (this Teensy) = shared jitter source.
//   NOTE: "x" sets driveMode=0 — re-send "M .."/"K .." before each "L" in scripts.
//
// Serial (115200):
//   "P"            -> "R PONG 3rocks <cpu_MHz>"
//   "M <m>"        -> drive mode: 0=off, 1=single(K), 2=symmetric(all in-phase), 3=stagger(120deg)
//   "K <k>"        -> strand for mode 1 (0/1/2)
//   "U <deg>"      -> custom stagger unit
//   "I <ms>"       -> integration time
//   "C <a> <b>"    -> read SENSE_PINS[a] on ADC0 + SENSE_PINS[b] on ADC1 (the other channel reads 0)
//   "L <freq>"     -> lock + stream (pair channels live, third = 0)
//   "x"            -> stop (also sets driveMode=0)
//
// Stream: "T3 <freq> <phA> <phB> <phC> <magA> <magB> <magC> <dAB> <dAC> <dBC>"
//   where dAB = phB - phA (mod 360), etc. — the three pairwise offsets.

#include <ADC.h>
ADC *adc = new ADC();

const int N_COILS = 3;
const int DRIVE_PINS[N_COILS] = {2, 3, 4};   // WIRING v2 2026-09-15 (verified by Brian): C1=pin2, C2=pin3, C3=pin4. Old pin 1 = Serial1 TX, dropped.
const int SENSE_PINS[N_COILS] = {A0, A1, A2};

const float FS        = 100000.0f;
const float TWO_PI_F  = 6.28318530718f;
const float PI_F      = 3.14159265f;

volatile float phase = 0.0f, dphi = 0.0f;
volatile float strandPhase[N_COILS];
volatile float strandOff[N_COILS];
volatile int   driveMode = 0;
volatile int   singleK   = 0;
volatile float customUnitRad = 0.0f;

// 3-channel lock-in accumulators
volatile float accI[N_COILS] = {}, accQ[N_COILS] = {};
volatile long  nsamp[N_COILS] = {};
volatile bool  acquiring = false;
volatile int   pairA = 0, pairB = 1;   // SENSE_PINS indices read truly simultaneously: ADC0 / ADC1 continuous

int   dcOffset[N_COILS] = {512, 512, 512};
float integ_ms = 200.0f;
float lockFreq = 0.0f;
bool  streaming = false;

IntervalTimer tick;

void isr() {
  // drive all 3 strands
  for (int k = 0; k < N_COILS; k++) {
    bool on = false;
    if (driveMode == 1)      on = (k == singleK) && (strandPhase[k] < PI_F);
    else if (driveMode >= 2) on = (strandPhase[k] < PI_F);
    digitalWriteFast(DRIVE_PINS[k], on ? HIGH : LOW);
  }

  // Teensy 4.1 has only TWO ADC engines, so exactly TWO runners are read per tick:
  // SENSE_PINS[pairA] on ADC0 and SENSE_PINS[pairB] on ADC1, both plain single-shot
  // (~1 us apart, full 100 kHz). NO continuous mode anywhere: every channel that
  // went through a stopContinuous()/startContinuous() cycle read a dead floor.
  // Select the pair with "C <a> <b>"; sweep all three pairs to cover all coils.
  int va = adc->adc0->analogRead(SENSE_PINS[pairA]);
  int vb = adc->adc1->analogRead(SENSE_PINS[pairB]);

  if (acquiring) {
    float cosRef = cosf(phase);
    float sinRef = sinf(phase);
    float sa = (float)(va - dcOffset[pairA]);
    accI[pairA] += sa * cosRef; accQ[pairA] += sa * sinRef; nsamp[pairA]++;
    float sb = (float)(vb - dcOffset[pairB]);
    accI[pairB] += sb * cosRef; accQ[pairB] += sb * sinRef; nsamp[pairB]++;
  }

  // advance reference + strand phases
  phase += dphi; if (phase >= TWO_PI_F) phase -= TWO_PI_F;
  for (int k = 0; k < N_COILS; k++) {
    strandPhase[k] += dphi;
    if (strandPhase[k] >= TWO_PI_F) strandPhase[k] -= TWO_PI_F;
  }
}

float staggerUnitRad() {
  if (driveMode == 3) return TWO_PI_F / (float)N_COILS;  // 120 deg for N=3
  if (driveMode == 4) return customUnitRad;
  return 0.0f;
}

void applyMode(int m) {
  noInterrupts();
  driveMode = m;
  float unit = staggerUnitRad();
  for (int k = 0; k < N_COILS; k++) {
    strandOff[k] = -unit * (float)k;
    strandPhase[k] = phase + strandOff[k];
    while (strandPhase[k] < 0)         strandPhase[k] += TWO_PI_F;
    while (strandPhase[k] >= TWO_PI_F) strandPhase[k] -= TWO_PI_F;
  }
  interrupts();
}

void setFreq(float f) {
  noInterrupts(); dphi = TWO_PI_F * f / FS; interrupts();
  applyMode(driveMode);
}

void measureDC() {
  // Plain single-shot DC reads of all three pins on ADC0. Nothing to pause.
  for (int ch = 0; ch < N_COILS; ch++) {
    long acc = 0;
    for (int i = 0; i < 256; i++) {
      acc += adc->adc0->analogRead(SENSE_PINS[ch]);
      delayMicroseconds(20);
    }
    dcOffset[ch] = acc / 256;
  }
}

void setPair(int a, int b) {
  if (a < 0 || a >= N_COILS || b < 0 || b >= N_COILS || a == b) return;
  noInterrupts();
  pairA = a; pairB = b;     // single-shot reads: nothing to stop or restart
  interrupts();
}

void threePoint(float f, float ph[3], float mg[3]) {
  float settle_s = max(20.0f / f, 0.020f);
  delayMicroseconds((uint32_t)(settle_s * 1e6f));
  noInterrupts();
  for (int k = 0; k < N_COILS; k++) { accI[k] = 0; accQ[k] = 0; nsamp[k] = 0; }
  acquiring = true;
  interrupts();
  float integ_s = max(40.0f / f, integ_ms / 1000.0f);
  delayMicroseconds((uint32_t)(integ_s * 1e6f));
  noInterrupts(); acquiring = false;
  for (int k = 0; k < N_COILS; k++) {
    long n = max(nsamp[k], 1L);
    float I = accI[k] / n, Q = accQ[k] / n;
    mg[k] = sqrtf(I * I + Q * Q);
    ph[k] = atan2f(Q, I) * 180.0f / PI_F;
    if (ph[k] < 0) ph[k] += 360.0f;
  }
  interrupts();
}

float dphase(float a, float b) {
  float d = b - a;
  while (d < -180.0f) d += 360.0f;
  while (d >  180.0f) d -= 360.0f;
  return d;
}

void setup() {
  Serial.begin(115200);
  for (int k = 0; k < N_COILS; k++) { pinMode(DRIVE_PINS[k], OUTPUT); digitalWriteFast(DRIVE_PINS[k], LOW); }

  // Both ADCs: single-shot only (no continuous mode anywhere)
  adc->adc0->setAveraging(1);
  adc->adc0->setResolution(10);
  adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED);
  adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::HIGH_SPEED);

  adc->adc1->setAveraging(1);
  adc->adc1->setResolution(10);
  adc->adc1->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED);
  adc->adc1->setSamplingSpeed(ADC_SAMPLING_SPEED::HIGH_SPEED);

  delay(50);
  measureDC();
  tick.begin(isr, 1000000.0f / FS);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if (cmd == "P") {
      Serial.print("R PONG 3rocks "); Serial.println(F_CPU / 1000000);
    }
    else if (cmd.startsWith("M ")) {
      applyMode(cmd.substring(2).toInt());
      Serial.print("R MODE "); Serial.println(driveMode);
    }
    else if (cmd.startsWith("K ")) {
      int k = cmd.substring(2).toInt();
      if (k < 0) k = 0; if (k >= N_COILS) k = N_COILS - 1;
      singleK = k; Serial.print("R K "); Serial.println(singleK);
    }
    else if (cmd.startsWith("U ")) {
      customUnitRad = cmd.substring(2).toFloat() * PI_F / 180.0f;
      applyMode(driveMode);
      Serial.print("R U "); Serial.println(cmd.substring(2).toFloat());
    }
    else if (cmd.startsWith("I ")) {
      integ_ms = cmd.substring(2).toFloat();
      Serial.print("R INTEG "); Serial.println(integ_ms);
    }
    else if (cmd.startsWith("L ")) {
      lockFreq = cmd.substring(2).toFloat();
      setFreq(lockFreq);
      streaming = true;
    }
    else if (cmd.startsWith("C ")) {
      // "C <a> <b>" -> read SENSE_PINS[a] (ADC0) + SENSE_PINS[b] (ADC1) simultaneously
      int a = -1, b = -1;
      if (sscanf(cmd.c_str() + 2, "%d %d", &a, &b) == 2) setPair(a, b);
      Serial.print("R PAIR "); Serial.print(pairA); Serial.print(" "); Serial.println(pairB);
    }
    else if (cmd == "V") {
      applyMode(0); measureDC();
      Serial.print("R DC "); Serial.print(dcOffset[0]); Serial.print(" ");
      Serial.print(dcOffset[1]); Serial.print(" "); Serial.println(dcOffset[2]);
    }
    else if (cmd == "x") { streaming = false; applyMode(0); Serial.println("R OFF"); }
  }

  if (streaming && lockFreq > 0) {
    float ph[3], mg[3];
    threePoint(lockFreq, ph, mg);
    float dAB = dphase(ph[0], ph[1]);
    float dAC = dphase(ph[0], ph[2]);
    float dBC = dphase(ph[1], ph[2]);
    Serial.print("T3 "); Serial.print(lockFreq, 1);
    Serial.print(" ");   Serial.print(ph[0], 2);
    Serial.print(" ");   Serial.print(ph[1], 2);
    Serial.print(" ");   Serial.print(ph[2], 2);
    Serial.print(" ");   Serial.print(mg[0], 3);
    Serial.print(" ");   Serial.print(mg[1], 3);
    Serial.print(" ");   Serial.print(mg[2], 3);
    Serial.print(" ");   Serial.print(dAB, 2);
    Serial.print(" ");   Serial.print(dAC, 2);
    Serial.print(" ");   Serial.println(dBC, 2);
  }
}
