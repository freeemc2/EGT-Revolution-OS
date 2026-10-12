/*
  teensy_ad7606.ino — AD7606 read-side instrument + three-coil drive, Teensy 4.1.
  v2 (2026-10-12, tonic): COM10 HOLDS THE EXPERIMENT (Brian direct) — this one board
  drives the three-coil set AND reads the taps through the AD7606. Drive synthesis is
  ported verbatim from teensy_three_rocks_orig.ino (the proven core): base square per
  strand + overlay tone, XOR mix, TD opposition knob, per-coil offsets, drive mask.
  The orig's internal-ADC lock-in is NOT ported — the AD7606 is the sense side now.

  READ SIDE stays a DUMB STREAMER (job spec): raw samples only, no thresholds, no
  booleans, no on-board phase math. All reduction host-side.

  Wiring:
    AD7606 (see WIRING.md): SCLK 13, DOUTA 12, CS 10, RESET 7, CONVST A+B 9, BUSY 8;
      VDRIVE 3.3 V, RANGE=GND (+/-5 V), OS=GND, own 5 V analog supply, shared GND.
    Drive (WIRING v2 2026-09-15, Brian-verified): pin 2 -> 220R -> C1, pin 3 -> C2,
      pin 4 -> C3; winding south ends -> GND. Taps: leg senses -> V1..V3.

  Serial commands (115200 framing ignored; native USB):
    P           -> "R PONG ad7606+drive v2 <rate_hz> <range_label> <driveMode>"
    --- read side (v1, unchanged) ---
    G           -> start free-run ADC streaming     g -> stop streaming ONLY
    C           -> one conversion, one JSON line
    S <hz>      -> ADC sample rate (1..5000)
    V <5|10>    -> RANGE label for headers (label only, never rescales)
    R           -> pulse AD7606 RESET
    --- drive side (orig semantics, same letters as the bench knows) ---
    L <freq>    -> set base freq + START drive timer (needs M first, as ever)
    M <m>       -> drive mode: 0 off, 1 single(K), 2 symmetric, 3 stagger(120deg)
    K <k>       -> strand for mode 1
    U <deg>     -> custom stagger unit (mode 4)
    O <k> <deg> -> per-coil drive-phase offset
    DM <k> <0|1>-> per-coil drive mask (cut one coil's drive, keep it connected)
    T <freq>    -> overlay tone freq (0 = off)
    TM <m>      -> overlay mix: 0 off, 1 XOR (two-tone), 2 AND
    TD <pct>    -> opposition strength: % of overlay half-period engaged
    x           -> STOP EVERYTHING: drive off (mode 0, pins LOW) + streaming off
                   (bench convention; capture tool uses 'g' so it never kills a drive)

  Output: {"t_us":...,"seq":...,"ch":[c0..c7]} raw int16 counts; header lines carry
  config incl. the drive state so every capture self-documents what was driving.
*/

#include <SPI.h>

// ---------- AD7606 read side ----------
const int PIN_SCLK = 13, PIN_DOUT = 12, PIN_CS = 10;
const int PIN_RESET = 7, PIN_CONVST = 9, PIN_BUSY = 8;
SPISettings SPI_CFG(8000000, MSBFIRST, SPI_MODE2);

uint32_t rate_hz = 1000;
uint32_t period_us = 1000;
uint8_t range_label = 5;
bool streaming = false;
uint32_t seq = 0;
elapsedMicros since_last;

// ---------- drive side (ported from teensy_three_rocks_orig) ----------
const int N_COILS = 3;
const int DRIVE_PINS[N_COILS] = {2, 3, 4};   // WIRING v2 2026-09-15 (Brian-verified)
const float FS       = 100000.0f;
const float TWO_PI_F = 6.28318530718f;
const float PI_F     = 3.14159265f;

volatile float phase = 0.0f, dphi = 0.0f;
volatile float strandPhase[N_COILS];
volatile float strandOff[N_COILS];
volatile int   driveMode = 0;
volatile int   singleK   = 0;
volatile float customUnitRad = 0.0f;
volatile float coilOff[N_COILS] = {0.0f, 0.0f, 0.0f};
volatile float dphi2 = 0.0f, phase2 = 0.0f;
volatile int   overlayMix = 0;
volatile bool  driveEn[N_COILS] = {true, true, true};
volatile float overlayDuty = 1.0f;
float baseFreq = 0.0f, ovlFreq = 0.0f;
bool  driveTimerOn = false;
IntervalTimer tick;

void isr() {   // drive only — the AD7606 does all sensing
  bool ov = (dphi2 > 0.0f) && (phase2 < PI_F * overlayDuty);
  for (int k = 0; k < N_COILS; k++) {
    bool driven = ((driveMode == 1) ? (k == singleK) : (driveMode >= 2)) && driveEn[k];
    bool on = false;
    if (driven) {
      float ph = strandPhase[k] + coilOff[k];
      if (ph >= TWO_PI_F) ph -= TWO_PI_F;
      if (ph < 0)         ph += TWO_PI_F;
      bool base_on = (ph < PI_F);
      if (overlayMix == 1 && dphi2 > 0.0f)      on = base_on ^ ov;
      else if (overlayMix == 2 && dphi2 > 0.0f) on = base_on && ov;
      else                                      on = base_on;
    }
    digitalWriteFast(DRIVE_PINS[k], on ? HIGH : LOW);
  }
  phase += dphi; if (phase >= TWO_PI_F) phase -= TWO_PI_F;
  if (dphi2 > 0.0f) { phase2 += dphi2; if (phase2 >= TWO_PI_F) phase2 -= TWO_PI_F; }
  for (int k = 0; k < N_COILS; k++) {
    strandPhase[k] += dphi;
    if (strandPhase[k] >= TWO_PI_F) strandPhase[k] -= TWO_PI_F;
  }
}

float staggerUnitRad() {
  if (driveMode == 3) return TWO_PI_F / (float)N_COILS;
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

void setBaseFreq(float f) {
  baseFreq = f;
  noInterrupts(); dphi = TWO_PI_F * f / FS; interrupts();
  applyMode(driveMode);
}

void driveStart() {
  if (!driveTimerOn) { tick.begin(isr, 1000000.0f / FS); driveTimerOn = true; }
}

void driveStopAll() {
  if (driveTimerOn) { tick.end(); driveTimerOn = false; }
  driveMode = 0;
  for (int k = 0; k < N_COILS; k++) digitalWriteFast(DRIVE_PINS[k], LOW);
}

// ---------- read side ----------
void adc_reset() {
  digitalWriteFast(PIN_RESET, HIGH);
  delayMicroseconds(2);
  digitalWriteFast(PIN_RESET, LOW);
  delayMicroseconds(2);
}

void emit_header() {
  Serial.print("{\"hdr\":1,\"fw\":\"ad7606+drive v2\",\"rate_hz\":");
  Serial.print(rate_hz);
  Serial.print(",\"range_label\":\"+/-");
  Serial.print(range_label);
  Serial.print("V\",\"lsb_uV_at_5V\":152.588,\"lsb_uV_at_10V\":305.176,\"os_bits\":0");
  Serial.print(",\"drive\":{\"mode\":"); Serial.print(driveMode);
  Serial.print(",\"base_hz\":");  Serial.print(baseFreq);
  Serial.print(",\"overlay_hz\":"); Serial.print(ovlFreq);
  Serial.print(",\"mix\":");      Serial.print(overlayMix);
  Serial.print(",\"td_pct\":");   Serial.print(overlayDuty * 100.0f);
  Serial.print(",\"running\":");  Serial.print(driveTimerOn ? "true" : "false");
  Serial.println("}}");
}

bool convert_and_read(int16_t ch[8]) {
  digitalWriteFast(PIN_CONVST, LOW);
  delayMicroseconds(1);
  digitalWriteFast(PIN_CONVST, HIGH);
  elapsedMicros t0;
  while (digitalReadFast(PIN_BUSY) == LOW)  { if (t0 > 100)  break; }
  while (digitalReadFast(PIN_BUSY) == HIGH) { if (t0 > 2000) return false; }
  SPI.beginTransaction(SPI_CFG);
  digitalWriteFast(PIN_CS, LOW);
  for (int i = 0; i < 8; i++) ch[i] = (int16_t)SPI.transfer16(0x0000);
  digitalWriteFast(PIN_CS, HIGH);
  SPI.endTransaction();
  return true;
}

void emit_sample() {
  int16_t ch[8];
  uint32_t t = micros();
  if (!convert_and_read(ch)) { Serial.println("{\"err\":\"busy_timeout\"}"); return; }
  Serial.print("{\"t_us\":"); Serial.print(t);
  Serial.print(",\"seq\":");  Serial.print(seq++);
  Serial.print(",\"ch\":[");
  for (int i = 0; i < 8; i++) { if (i) Serial.print(','); Serial.print(ch[i]); }
  Serial.println("]}");
}

void handle_line(char *line) {
  // two-letter commands first
  if (line[0] == 'T' && line[1] == 'M') {
    overlayMix = atoi(line + 2);
    Serial.print("R TMIX "); Serial.println(overlayMix);
    return;
  }
  if (line[0] == 'T' && line[1] == 'D') {
    float d = atof(line + 2) / 100.0f;
    overlayDuty = (d < 0.0f) ? 0.0f : (d > 1.0f ? 1.0f : d);
    Serial.print("R TDUTY "); Serial.println(overlayDuty * 100.0f);
    return;
  }
  if (line[0] == 'D' && line[1] == 'M') {
    int k, v;
    if (sscanf(line + 2, "%d %d", &k, &v) == 2 && k >= 0 && k < N_COILS) {
      driveEn[k] = (v != 0);
      Serial.print("R DMASK "); Serial.print(k); Serial.print(' '); Serial.println(driveEn[k] ? 1 : 0);
    }
    return;
  }
  switch (line[0]) {
    case 'P':
      Serial.print("R PONG ad7606+drive v2 "); Serial.print(rate_hz);
      Serial.print(" +/-"); Serial.print(range_label); Serial.print("V mode");
      Serial.println(driveMode);
      break;
    case 'G': streaming = true; seq = 0; since_last = 0; emit_header(); break;
    case 'g': streaming = false; Serial.println("R STREAMOFF"); break;
    case 'x': streaming = false; driveStopAll(); Serial.println("R LOCKED off"); break;
    case 'C': emit_sample(); break;
    case 'R': adc_reset(); Serial.println("R RESET"); break;
    case 'S': {
      long v = atol(line + 1);
      if (v >= 1 && v <= 5000) { rate_hz = v; period_us = 1000000UL / rate_hz; emit_header(); }
      else Serial.println("{\"err\":\"rate 1..5000\"}");
      break;
    }
    case 'V': {
      long v = atol(line + 1);
      if (v == 5 || v == 10) { range_label = v; emit_header(); }
      else Serial.println("{\"err\":\"V 5|10\"}");
      break;
    }
    case 'L': {
      float f = atof(line + 1);
      if (f > 0.0f && f <= 30000.0f) {
        setBaseFreq(f); driveStart();
        Serial.print("R LOCK "); Serial.println(f);
        emit_header();
      } else Serial.println("{\"err\":\"L freq\"}");
      break;
    }
    case 'M': applyMode(atoi(line + 1)); Serial.print("R MODE "); Serial.println(driveMode); break;
    case 'K': singleK = constrain(atoi(line + 1), 0, N_COILS - 1); Serial.print("R K "); Serial.println(singleK); break;
    case 'U': customUnitRad = atof(line + 1) * TWO_PI_F / 360.0f; Serial.println("R UNIT"); break;
    case 'O': {
      int k; float deg;
      if (sscanf(line + 1, "%d %f", &k, &deg) == 2 && k >= 0 && k < N_COILS) {
        coilOff[k] = deg * TWO_PI_F / 360.0f;
        Serial.print("R OFF "); Serial.print(k); Serial.print(' '); Serial.println(deg);
      }
      break;
    }
    case 'T': {   // bare T <freq> (TM/TD handled above)
      ovlFreq = atof(line + 1);
      noInterrupts();
      dphi2 = (ovlFreq > 0.0f) ? TWO_PI_F * ovlFreq / FS : 0.0f;
      phase2 = 0.0f;
      interrupts();
      Serial.print("R TONE2 "); Serial.println(ovlFreq);
      break;
    }
    default: break;
  }
}

void setup() {
  pinMode(PIN_CS, OUTPUT);     digitalWriteFast(PIN_CS, HIGH);
  pinMode(PIN_RESET, OUTPUT);  digitalWriteFast(PIN_RESET, LOW);
  pinMode(PIN_CONVST, OUTPUT); digitalWriteFast(PIN_CONVST, HIGH);
  pinMode(PIN_BUSY, INPUT);
  for (int k = 0; k < N_COILS; k++) { pinMode(DRIVE_PINS[k], OUTPUT); digitalWriteFast(DRIVE_PINS[k], LOW); }
  SPI.begin();
  Serial.begin(115200);
  adc_reset();
  period_us = 1000000UL / rate_hz;
  emit_header();
}

char buf[48]; int blen = 0;

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (blen) { buf[blen] = 0; handle_line(buf); blen = 0; } }
    else if (blen < 47) buf[blen++] = c;
  }
  if (streaming && since_last >= period_us) {
    since_last -= period_us;
    emit_sample();
  }
}
