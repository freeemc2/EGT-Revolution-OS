/*
  teensy_ad7606.ino — AD7606 read-side instrument, Teensy 4.1. v1 (2026-10-11, tonic)

  DUMB STREAMER BY DESIGN (job_teensy_ad7606_firmware.md): raw samples only.
  No thresholds, no gates, no booleans, no on-board phase math — all reduction
  happens host-side, inspectable. The gate reaches into data models.

  Wiring (per Grok spec 2026-10-11, corrected against the AD7606 datasheet):
    Teensy 13  -> AD7606 SCLK          (SPI0 SCK)
    Teensy 12  <- AD7606 DOUTA         (SPI0 MISO; serial mode, all 8 ch on DOUTA)
    Teensy 10  -> AD7606 CS            (SPI0 CS, driven as GPIO)
    Teensy  7  -> AD7606 RESET
    Teensy  9  -> AD7606 CONVST A+B    (tied together: simultaneous A/B groups)
    Teensy  8  <- AD7606 BUSY
    AD7606 config: OS0..OS2 -> GND (no oversampling), PAR/SER SEL -> VDRIVE
    (serial mode), RANGE -> GND (= +/-5 V span; HIGH would be +/-10 V),
    AVCC -> 5 V, **VDRIVE -> 3V3 from the Teensy rail — NEVER 5 V** (DOUT/BUSY
    swing to VDRIVE and Teensy 4.1 pins are not 5 V tolerant).

  Serial commands (115200 is ignored — Teensy native USB runs full speed):
    P          -> "R PONG ad7606 v1 <rate_hz> <range_label>"
    G          -> start free-run streaming at the set rate
    x          -> stop streaming
    C          -> one conversion, one JSON line
    S <hz>     -> set sample rate (1..5000)
    V <5|10>   -> set the RANGE LABEL reported in headers (label only — it
                  never rescales data; raw counts are always emitted)
    R          -> pulse RESET on the ADC

  Output: one JSON line per conversion:
    {"t_us":<micros since boot>,"seq":<n>,"ch":[c0,...,c7]}
  ch values are RAW two's-complement int16 counts. LSB volts = span/65536
  (+/-5 V: 152.59 uV; +/-10 V: 305.18 uV) — applied host-side, never here.
  A header line is emitted on boot, on G, and on config change:
    {"hdr":1,"fw":"ad7606 v1","rate_hz":...,"range_label":"+/-5V",
     "lsb_uV_at_5V":152.588,"lsb_uV_at_10V":305.176,"os_bits":0}
*/

#include <SPI.h>

const int PIN_SCLK = 13, PIN_DOUT = 12, PIN_CS = 10;
const int PIN_RESET = 7, PIN_CONVST = 9, PIN_BUSY = 8;

// 8 MHz: margin under the AD7606's 17 MHz max SCLK at VDRIVE = 3.3 V.
SPISettings SPI_CFG(8000000, MSBFIRST, SPI_MODE2);

uint32_t rate_hz = 1000;
uint32_t period_us = 1000;
uint8_t range_label = 5;        // label only; wiring decides the real span
bool streaming = false;
uint32_t seq = 0;
elapsedMicros since_last;

void adc_reset() {
  digitalWriteFast(PIN_RESET, HIGH);
  delayMicroseconds(2);           // t_RESET min 50 ns
  digitalWriteFast(PIN_RESET, LOW);
  delayMicroseconds(2);
}

void emit_header() {
  Serial.print("{\"hdr\":1,\"fw\":\"ad7606 v1\",\"rate_hz\":");
  Serial.print(rate_hz);
  Serial.print(",\"range_label\":\"+/-");
  Serial.print(range_label);
  Serial.print("V\",\"lsb_uV_at_5V\":152.588,\"lsb_uV_at_10V\":305.176,\"os_bits\":0}");
  Serial.println();
}

// One conversion: CONVST rising edge starts it; BUSY high during conversion,
// falls when all 8 results are ready; then clock 8 x 16 bits out of DOUTA.
bool convert_and_read(int16_t ch[8]) {
  digitalWriteFast(PIN_CONVST, LOW);
  delayMicroseconds(1);           // t_CONVST low min 25 ns
  digitalWriteFast(PIN_CONVST, HIGH);

  // wait BUSY rise (fast, may be missed at low poll granularity) then fall.
  elapsedMicros t0;
  while (digitalReadFast(PIN_BUSY) == LOW)  { if (t0 > 100)  break; }       // rise
  while (digitalReadFast(PIN_BUSY) == HIGH) { if (t0 > 2000) return false; } // fall; conv ~4 us, OS up to ~1 ms

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
  if (!convert_and_read(ch)) {
    Serial.println("{\"err\":\"busy_timeout\"}");
    return;
  }
  Serial.print("{\"t_us\":"); Serial.print(t);
  Serial.print(",\"seq\":");  Serial.print(seq++);
  Serial.print(",\"ch\":[");
  for (int i = 0; i < 8; i++) { if (i) Serial.print(','); Serial.print(ch[i]); }
  Serial.println("]}");
}

void handle_line(char *line) {
  switch (line[0]) {
    case 'P':
      Serial.print("R PONG ad7606 v1 "); Serial.print(rate_hz);
      Serial.print(" +/-"); Serial.print(range_label); Serial.println("V");
      break;
    case 'G': streaming = true; seq = 0; since_last = 0; emit_header(); break;
    case 'x': streaming = false; Serial.println("R STOPPED"); break;
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
    default: break; // unknown bytes ignored — never let console noise change state
  }
}

void setup() {
  pinMode(PIN_CS, OUTPUT);     digitalWriteFast(PIN_CS, HIGH);
  pinMode(PIN_RESET, OUTPUT);  digitalWriteFast(PIN_RESET, LOW);
  pinMode(PIN_CONVST, OUTPUT); digitalWriteFast(PIN_CONVST, HIGH);
  pinMode(PIN_BUSY, INPUT);
  SPI.begin();
  Serial.begin(115200);
  adc_reset();
  period_us = 1000000UL / rate_hz;
  emit_header();
}

char buf[32]; int blen = 0;

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (blen) { buf[blen] = 0; handle_line(buf); blen = 0; } }
    else if (blen < 31) buf[blen++] = c;
  }
  if (streaming && since_last >= period_us) {
    since_last -= period_us;
    emit_sample();
  }
}
