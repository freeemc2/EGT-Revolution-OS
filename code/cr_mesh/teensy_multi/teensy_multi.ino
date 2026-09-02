// TEENSY MULTI — generic N-channel EGT/Two-Rocks drive (Teensy 4.1).
// Extends teensy_five to N strands (up to 16) so ONE firmware drives the whole
// commensurate coil family {2,4,8,16}: Hexadeca (N=16) and Quad (N=4) alike.
//
// CANON (roots of unity, coil_build_specs_3in):
//   symmetric drive (all strands in phase)  -> center field Sum e^{i2pi k/N} = 0  = SILENT (null control)
//   staggered psi_k = -k*2pi/N               -> Sum e^{i0} = N                     = full coupling
//   stagger unit = 360/N deg -> N=16 gives 22.5 deg = ONE RUNG PER STRAND (the ladder in copper);
//                               N=4  gives 90 deg   = the canonical pi/2 quadrature.
// Per-strand square-wave drive (coil low-passes); shared software lock-in on the runner (A0).
//
// Modes:  0 off | 1 single (one strand) | 2 symmetric/null | 3 stagger(360/N) | 4 custom stagger(U deg)
//
// Serial (115200), teensy family:
//   "P"            -> "R PONG multi <N> <cpu_MHz>"
//   "N <n>"        -> set active strand count (2..16); default 16
//   "M <m>"        -> drive mode (0..4)
//   "K <k>"        -> strand index for mode 1 (single)
//   "U <deg>"      -> custom stagger unit for mode 4
//   "I <ms>"       -> lock-in integration ms
//   "L <freq_hz>"  -> lock+stream "T <freq> <phase_deg> <mag> <mode> <N> <unit_deg>"
//   "x"            -> drive off, stop stream
//
// PINS: 16 clean Teensy 4.1 digital outs, avoiding A0=14 (runner sense) and 13 (LED).
//   verify against your wiring before power; each strand via 220 ohm.

#include <ADC.h>
ADC *adc = new ADC();

const int   DRIVE_PINS[16] = {2,3,4,5,6,7,8,9,10,11,12,24,25,26,27,28};
const int   SENSE_PIN      = A0;          // the runner
const float FS             = 100000.0f;   // ISR sample rate
const float TWO_PI_F       = 6.28318530718f;
const float PI_F           = 3.14159265f;

volatile int   nStrand   = 16;            // active strands (2..16)
volatile int   singleK   = 0;             // strand for mode 1
volatile float customUnitRad = 0.0f;      // mode 4 stagger unit (rad)

volatile float phase = 0.0f, dphi = 0.0f;         // lock-in reference
volatile float strandPhase[16];
volatile float strandOff[16];
volatile int   driveMode = 0;
volatile bool  acquiring = false;
volatile float accI = 0, accQ = 0;
volatile long  nsamp = 0;
int   dcOffset = 512;
float integ_ms = 200.0f;

IntervalTimer tick;

void isr() {
  for (int k = 0; k < nStrand; k++) {
    bool on = false;
    if (driveMode == 1)      on = (k == singleK) && (strandPhase[k] < PI_F);
    else if (driveMode >= 2) on = (strandPhase[k] < PI_F);
    digitalWriteFast(DRIVE_PINS[k], on ? HIGH : LOW);
  }
  int v = adc->adc0->analogReadContinuous();
  if (acquiring) {
    float s = (float)(v - dcOffset);
    accI += s * cosf(phase);
    accQ += s * sinf(phase);
    nsamp++;
  }
  phase += dphi; if (phase >= TWO_PI_F) phase -= TWO_PI_F;
  for (int k = 0; k < nStrand; k++) {
    strandPhase[k] += dphi;
    if (strandPhase[k] >= TWO_PI_F) strandPhase[k] -= TWO_PI_F;
  }
}

float staggerUnitRad() {
  if (driveMode == 3) return TWO_PI_F / (float)nStrand;   // canon 360/N
  if (driveMode == 4) return customUnitRad;               // arbitrary (sweep)
  return 0.0f;                                            // symmetric / single
}

void applyMode(int m) {
  noInterrupts();
  driveMode = m;
  float unit = staggerUnitRad();
  for (int k = 0; k < nStrand; k++) {
    strandOff[k] = -unit * (float)k;                       // psi_k = -k*unit
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
  *ph_deg = atan2f(Q, I) * 180.0f / PI_F;
  if (*ph_deg < 0) *ph_deg += 360.0f;
}

void setup() {
  Serial.begin(115200);
  for (int k = 0; k < 16; k++) { pinMode(DRIVE_PINS[k], OUTPUT); digitalWriteFast(DRIVE_PINS[k], LOW); }
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
    if (cmd == "P") { Serial.print("R PONG multi "); Serial.print(nStrand); Serial.print(" "); Serial.println(F_CPU / 1000000); }
    else if (cmd.startsWith("N ")) {
      int n = cmd.substring(2).toInt();
      if (n < 1) n = 1; if (n > 16) n = 16;
      noInterrupts(); nStrand = n; interrupts();
      applyMode(driveMode);
      Serial.print("R N "); Serial.println(nStrand);
    }
    else if (cmd.startsWith("K ")) {
      int k = cmd.substring(2).toInt();
      if (k < 0) k = 0; if (k >= nStrand) k = nStrand - 1;
      singleK = k; Serial.print("R K "); Serial.println(singleK);
    }
    else if (cmd.startsWith("U ")) {
      customUnitRad = cmd.substring(2).toFloat() * PI_F / 180.0f;
      applyMode(driveMode);
      Serial.print("R U "); Serial.println(cmd.substring(2).toFloat());
    }
    else if (cmd.startsWith("M ")) {
      applyMode(cmd.substring(2).toInt());
      Serial.print("R MODE "); Serial.println(driveMode);
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
    float unit_deg = staggerUnitRad() * 180.0f / PI_F;
    Serial.print("T "); Serial.print(lockFreq, 1);
    Serial.print(" ");  Serial.print(ph, 4);
    Serial.print(" ");  Serial.print(mg, 3);
    Serial.print(" ");  Serial.print(driveMode);
    Serial.print(" ");  Serial.print(nStrand);
    Serial.print(" ");  Serial.println(unit_deg, 2);
  }
}
