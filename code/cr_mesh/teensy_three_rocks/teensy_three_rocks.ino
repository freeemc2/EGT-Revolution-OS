// TEENSY THREE ROCKS — 3-coil EGT drive + simultaneous 3-channel sense (Teensy 4.1).
// Purpose-built for the N=3 equilateral geometry test: three coils, one crystal,
// shared jitter. Drives 3 strands, reads 3 runners simultaneously via dual-ADC
// + fast single-read, streams all 3 phases and 3 pairwise offsets.
//
// WIRING:
//   Drive: pin 2 -> 220ohm -> Coil A, pin 3 -> 220ohm -> Coil B, pin 4 -> 220ohm -> Coil C
//   Sense: Coil A runner -> A0, Coil B runner -> A1, Coil C runner -> A2
//   All coils share one crystal (this Teensy) = shared jitter source.
//
// Serial (115200):
//   "P"            -> "R PONG 3rocks <cpu_MHz>"
//   "M <m>"        -> drive mode: 0=off, 1=single(K), 2=symmetric(all in-phase), 3=stagger(120deg)
//   "K <k>"        -> strand for mode 1 (0/1/2)
//   "U <deg>"      -> custom stagger unit
//   "I <ms>"       -> integration time
//   "L <freq>"     -> lock + stream all 3 channels
//   "x"            -> stop
//
// Stream: "T3 <freq> <phA> <phB> <phC> <magA> <magB> <magC> <dAB> <dAC> <dBC>"
//   where dAB = phB - phA (mod 360), etc. — the three pairwise offsets.

#include <ADC.h>
ADC *adc = new ADC();

const int N_COILS = 3;
const int DRIVE_PINS[N_COILS] = {2, 3, 4};
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
volatile long  nsamp = 0;
volatile bool  acquiring = false;

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

  // read 3 runners: ADC0 (A0) + ADC1 (A1) simultaneous, A2 fast single
  int v0 = adc->adc0->analogReadContinuous();
  int v1 = adc->adc1->analogReadContinuous();
  int v2 = adc->adc0->analogRead(SENSE_PINS[2]);

  if (acquiring) {
    float cosRef = cosf(phase);
    float sinRef = sinf(phase);
    float s0 = (float)(v0 - dcOffset[0]);
    float s1 = (float)(v1 - dcOffset[1]);
    float s2 = (float)(v2 - dcOffset[2]);
    accI[0] += s0 * cosRef; accQ[0] += s0 * sinRef;
    accI[1] += s1 * cosRef; accQ[1] += s1 * sinRef;
    accI[2] += s2 * cosRef; accQ[2] += s2 * sinRef;
    nsamp++;
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
  for (int ch = 0; ch < N_COILS; ch++) {
    long acc = 0;
    for (int i = 0; i < 256; i++) {
      acc += adc->adc0->analogRead(SENSE_PINS[ch]);
      delayMicroseconds(20);
    }
    dcOffset[ch] = acc / 256;
  }
}

void threePoint(float f, float ph[3], float mg[3]) {
  float settle_s = max(20.0f / f, 0.020f);
  delayMicroseconds((uint32_t)(settle_s * 1e6f));
  noInterrupts();
  for (int k = 0; k < N_COILS; k++) { accI[k] = 0; accQ[k] = 0; }
  nsamp = 0; acquiring = true;
  interrupts();
  float integ_s = max(40.0f / f, integ_ms / 1000.0f);
  delayMicroseconds((uint32_t)(integ_s * 1e6f));
  noInterrupts(); acquiring = false;
  long n = max(nsamp, 1L);
  for (int k = 0; k < N_COILS; k++) {
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

  // ADC0 continuous on A0
  adc->adc0->setAveraging(1);
  adc->adc0->setResolution(10);
  adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED);
  adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::HIGH_SPEED);
  adc->adc0->startContinuous(SENSE_PINS[0]);

  // ADC1 continuous on A1
  adc->adc1->setAveraging(1);
  adc->adc1->setResolution(10);
  adc->adc1->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED);
  adc->adc1->setSamplingSpeed(ADC_SAMPLING_SPEED::HIGH_SPEED);
  adc->adc1->startContinuous(SENSE_PINS[1]);

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
