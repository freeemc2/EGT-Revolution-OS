// teensy_five — 5-PHASE STAGGER DRIVE for Coil #2 (5-strand), sealed-prediction test.
// Built 2026-08-29 (aria) for the pre-registered prediction sealed to redis
// cadence:tworocks:sealed-prediction (2026-08-29T13:05:18Z, BEFORE any run):
//   P1: 72°-stagger 5-phase drive -> runner reads ~5x one strand
//   P2: runner phase ROTATES at the stagger rate
//   P3: any symmetric parallel drive -> silent, always
// Math basis (canon, roots of unity): sum_k e^(i(2πk/5 + ψ_k)) = 0 for equal ψ,
// = 5 when ψ_k = −2πk/5 (the stagger cancels the geometric spread).
//
// WIRING (Brian's hands — REQUIRED before this firmware means anything):
//   Separate coil #2's five strand STARTS (currently tied in symmetric parallel).
//   pin 3 --- 220R --- strand 1 start        all five strand ENDS -> common GND
//   pin 4 --- 220R --- strand 2 start        runner (22ga): GND -- runner -- A0
//   pin 5 --- 220R --- strand 3 start
//   pin 6 --- 220R --- strand 4 start
//   pin 7 --- 220R --- strand 5 start
//
// Serial protocol (115200), same family as teensy_sweep:
//   "P"            -> "R PONG five 100"
//   "M <mode>"     -> drive mode: 0=off  1=strand-1 only (the 1x reference)
//                     2=symmetric (all five in phase — P3 null test)
//                     3=stagger  (phase_k = -k*72° — P1/P2 test)
//   "L <freq_hz>"  -> set drive freq, start continuous lock-in:
//                     streams "T <freq> <phase_deg> <mag> <mode>"
//   "I <ms>"       -> integration time per point (default 200)
//   "x"            -> drive off, stop streaming

#include <ADC.h>

const int   DRIVE_PINS[5] = {3, 4, 5, 6, 7};
const int   SENSE_PIN     = A0;
const float FS            = 100000.0f;   // ISR sample rate
const float TWO_PI_F      = 6.28318530718f;

ADC *adc = new ADC();

volatile float phase = 0.0f, dphi = 0.0f;          // lock-in reference
volatile float strandPhase[5];                      // per-strand accumulators
volatile float strandOff[5] = {0, 0, 0, 0, 0};      // per-strand offsets (rad)
volatile int   driveMode = 0;                       // 0 off, 1 single, 2 sym, 3 stagger
volatile bool  acquiring = false;
volatile float accI = 0, accQ = 0;
volatile long  nsamp = 0;
int dcOffset = 512;
float integ_ms = 200.0f;

IntervalTimer tick;

void isr() {
  // drive: square wave per strand at its own phase offset (coil low-passes)
  for (int k = 0; k < 5; k++) {
    bool on = false;
    if (driveMode == 1)      on = (k == 0) && (strandPhase[k] < 3.14159265f);
    else if (driveMode >= 2) on = (strandPhase[k] < 3.14159265f);
    digitalWriteFast(DRIVE_PINS[k], on ? HIGH : LOW);
  }
  // sense: lock-in against the shared reference
  int v = adc->adc0->analogReadContinuous();
  if (acquiring) {
    float s = (float)(v - dcOffset);
    accI += s * cosf(phase);
    accQ += s * sinf(phase);
    nsamp++;
  }
  phase += dphi; if (phase >= TWO_PI_F) phase -= TWO_PI_F;
  for (int k = 0; k < 5; k++) {
    strandPhase[k] += dphi;
    if (strandPhase[k] >= TWO_PI_F) strandPhase[k] -= TWO_PI_F;
  }
}

void applyMode(int m) {
  noInterrupts();
  driveMode = m;
  for (int k = 0; k < 5; k++) {
    // stagger: psi_k = -k * 72 deg; symmetric/single: all zero offset
    strandOff[k] = (m == 3) ? -TWO_PI_F * k / 5.0f : 0.0f;
    strandPhase[k] = phase + strandOff[k];
    while (strandPhase[k] < 0) strandPhase[k] += TWO_PI_F;
    while (strandPhase[k] >= TWO_PI_F) strandPhase[k] -= TWO_PI_F;
  }
  interrupts();
}

void setFreq(float f) {
  noInterrupts();
  dphi = TWO_PI_F * f / FS;
  interrupts();
  applyMode(driveMode);
}

void measureDC() {
  long acc = 0;
  for (int i = 0; i < 256; i++) { acc += adc->adc0->analogReadContinuous(); delayMicroseconds(20); }
  dcOffset = acc / 256;
}

float lockFreq = 0.0f;
bool  streaming = false;

void onePoint(float f, float *ph_deg, float *mag) {
  float settle_s = max(20.0f / f, 0.020f);
  delayMicroseconds((uint32_t)(settle_s * 1e6f));
  noInterrupts(); accI = 0; accQ = 0; nsamp = 0; acquiring = true; interrupts();
  float integ_s = max(40.0f / f, integ_ms / 1000.0f);
  delayMicroseconds((uint32_t)(integ_s * 1e6f));
  noInterrupts(); acquiring = false;
  float I = accI / max(nsamp, 1L), Q = accQ / max(nsamp, 1L); interrupts();
  *mag = sqrtf(I * I + Q * Q);
  *ph_deg = atan2f(Q, I) * 180.0f / 3.14159265f;
  if (*ph_deg < 0) *ph_deg += 360.0f;
}

void setup() {
  Serial.begin(115200);
  for (int k = 0; k < 5; k++) pinMode(DRIVE_PINS[k], OUTPUT);
  adc->adc0->setAveraging(1);
  adc->adc0->setResolution(10);
  adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED);
  adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::HIGH_SPEED);
  adc->adc0->startContinuous(SENSE_PIN);
  delay(50);
  measureDC();
  tick.begin(isr, 1000000.0f / FS);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if (cmd == "P") { Serial.println("R PONG five 100"); }
    else if (cmd.startsWith("M ")) {
      int m = cmd.substring(2).toInt();
      applyMode(m);
      Serial.print("R MODE "); Serial.println(m);
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
    float ph, mg;
    onePoint(lockFreq, &ph, &mg);
    Serial.print("T "); Serial.print(lockFreq, 1);
    Serial.print(" ");  Serial.print(ph, 4);
    Serial.print(" ");  Serial.print(mg, 3);
    Serial.print(" ");  Serial.println(driveMode);
  }
}
