// TEENSY RM3100 — N-sensor vector magnetometer array reader (Teensy 4.1).
//
// ROLE (frame-honest): this is the DC / low-frequency VECTOR field-geometry
// mapper for the triadic. It maps the 3-axis field around the coil array and an
// inside<->outside differential (3 sensors AT the vertices + observers OUTSIDE).
//   * It does NOT see the 22 kHz drive tone or arg C phase  (RM3100 band = DC..few hundred Hz)
//   * It does NOT reach the B_res ~fT floor                 (RM3100 floor ~nT; ~1e6 coarser)
//   Those stay the coil runner-sense -> LNA -> AD7606 lock-in chain's job.
//   This array measures the gross vector field configuration = necessary context/control,
//   NOT proof of a gravity anomaly (that observable is force-on-mass, not field pattern).
//
// BUS: shared SPI0 (SCK=13, MOSI=11, MISO=12), one CS GPIO per sensor.
//   RM3100 is 3.3V native and Teensy 4.1 is 3.3V -> NO level shifting. Feed 3V3, not 5V.
//   SPI mode 0 (CPOL=0,CPHA=0), MSB first, 1 MHz (datasheet allows more; 1 MHz is safe).
//   Read  = (reg | 0x80).  Write = reg (bit7=0).
//
// DRDY is POLLED via STATUS reg (0x34 bit7) -> fewer wires (no per-sensor DRDY line).
//
// RM3100 registers used:
//   0x0B TMRC   continuous-measurement update rate  (0x92..0x9F; 0x96 ~= 37 Hz default-ish)
//   0x04 CCX..  cycle-count X/Y/Z (2 bytes each, 0x04..0x09). CC=200 -> ~75 LSB/uT (13.3 nT/LSB)
//   0x01 CMM    continuous mode: 0x79 = CMX|CMY|CMZ|DRDM|START (all axes)
//   0x24 MX..   results, 9 bytes total, 24-bit signed big-endian per axis (MX,MY,MZ)
//   0x34 STATUS bit7 = DRDY
//   0x36 REVID  should read 0x22  (the "who am I" sanity check)
//
// Serial (115200), teensy family style:
//   "P"          -> "R PONG rm3100 <NSENS> <cpu_MHz>"
//   "W"          -> whoami: "R ID s<i> 0x<revid>"  for every sensor (0x22 = good)
//   "C <n>"      -> set cycle count on all sensors (50..400 typical; higher=finer/slower)
//   "R <hex>"    -> set TMRC rate byte on all sensors (e.g. 96)
//   "Z"          -> capture baseline (bias) = mean of 64 frames/sensor; subtracted from stream
//   "S"          -> stream on
//   "x"          -> stream off
// Stream line, ONE per ready sensor per cycle (uT, baseline-subtracted if Z was run):
//   "T <ms> s<i> <bx> <by> <bz> <bmag>"
//
// CS PIN MAP — edit NSENS + CS_PINS for your array. Default = Gemini's 6:
//   s0,s1,s2 = triadic VERTICES (co-located at the 3 coils)
//   s3,s4,s5 = external OBSERVERS
// Keep all sensors AWAY from the 4-ton AC transformer (known phase-drift source).

#include <SPI.h>

// ---- ARRAY CONFIG (edit these two lines to scale) --------------------------
const int NSENS = 6;
const int CS_PINS[NSENS] = {2, 3, 4, 5, 6, 7};   // one clean GPIO per sensor
// Labels are just for the wiring sheet: s0..s2 vertices, s3..s5 observers.
// ---------------------------------------------------------------------------

const uint32_t SPI_HZ = 1000000;
SPISettings RM_SPI(SPI_HZ, MSBFIRST, SPI_MODE0);

// register addresses
const uint8_t REG_CMM    = 0x01;
const uint8_t REG_CCX    = 0x04;
const uint8_t REG_TMRC   = 0x0B;
const uint8_t REG_MEAS   = 0x24;
const uint8_t REG_STATUS = 0x34;
const uint8_t REG_REVID  = 0x36;

uint16_t cycleCount = 200;      // -> ~75 LSB/uT
uint8_t  tmrcRate   = 0x96;
bool     streaming  = false;

float baseX[NSENS], baseY[NSENS], baseZ[NSENS];  // bias per sensor (uT)

static inline float lsbPerUT() { return 0.3671f * (float)cycleCount + 1.5f; } // PNI gain fit
// (CC=200 -> ~75 LSB/uT; CC=400 -> ~148 LSB/uT). counts / lsbPerUT() = uT.

void csLow (int i){ digitalWriteFast(CS_PINS[i], LOW); }
void csHigh(int i){ digitalWriteFast(CS_PINS[i], HIGH); }

void wReg(int i, uint8_t reg, const uint8_t *buf, int n) {
  SPI.beginTransaction(RM_SPI); csLow(i);
  SPI.transfer(reg & 0x7F);
  for (int k = 0; k < n; k++) SPI.transfer(buf[k]);
  csHigh(i); SPI.endTransaction();
}
void rReg(int i, uint8_t reg, uint8_t *buf, int n) {
  SPI.beginTransaction(RM_SPI); csLow(i);
  SPI.transfer(reg | 0x80);
  for (int k = 0; k < n; k++) buf[k] = SPI.transfer(0x00);
  csHigh(i); SPI.endTransaction();
}
uint8_t rByte(int i, uint8_t reg){ uint8_t b; rReg(i, reg, &b, 1); return b; }

void setCycleCount(int i, uint16_t cc) {
  uint8_t b[6] = { (uint8_t)(cc>>8),(uint8_t)(cc&0xFF),
                   (uint8_t)(cc>>8),(uint8_t)(cc&0xFF),
                   (uint8_t)(cc>>8),(uint8_t)(cc&0xFF) };
  wReg(i, REG_CCX, b, 6);
}

void startSensor(int i) {
  uint8_t t = tmrcRate;      wReg(i, REG_TMRC, &t, 1);
  setCycleCount(i, cycleCount);
  uint8_t cmm = 0x79;        wReg(i, REG_CMM, &cmm, 1);   // all axes, DRDM, start
}

bool readField(int i, float *x, float *y, float *z) {
  if (!(rByte(i, REG_STATUS) & 0x80)) return false;       // DRDY low -> no new frame
  uint8_t m[9]; rReg(i, REG_MEAS, m, 9);
  int32_t raw[3];
  for (int a = 0; a < 3; a++) {
    int32_t v = ((int32_t)m[a*3] << 16) | ((int32_t)m[a*3+1] << 8) | m[a*3+2];
    if (v & 0x800000) v |= 0xFF000000;                    // sign-extend 24->32
    raw[a] = v;
  }
  float g = lsbPerUT();
  *x = raw[0]/g; *y = raw[1]/g; *z = raw[2]/g;
  return true;
}

void captureBaseline() {
  for (int i = 0; i < NSENS; i++) { baseX[i]=baseY[i]=baseZ[i]=0; }
  const int N = 64;
  for (int i = 0; i < NSENS; i++) {
    float sx=0,sy=0,sz=0; int got=0; uint32_t t0=millis();
    while (got < N && millis()-t0 < 3000) {
      float x,y,z; if (readField(i,&x,&y,&z)) { sx+=x; sy+=y; sz+=z; got++; }
    }
    if (got) { baseX[i]=sx/got; baseY[i]=sy/got; baseZ[i]=sz/got; }
    Serial.print("R BASE s"); Serial.print(i);
    Serial.print(" "); Serial.print(baseX[i],4);
    Serial.print(" "); Serial.print(baseY[i],4);
    Serial.print(" "); Serial.print(baseZ[i],4);
    Serial.print(" n="); Serial.println(got);
  }
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < NSENS; i++) { pinMode(CS_PINS[i], OUTPUT); csHigh(i); }
  SPI.begin();
  delay(20);
  for (int i = 0; i < NSENS; i++) startSensor(i);
  for (int i = 0; i < NSENS; i++) { baseX[i]=baseY[i]=baseZ[i]=0; }
  delay(50);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); cmd.trim();
    if (cmd == "P") {
      Serial.print("R PONG rm3100 "); Serial.print(NSENS);
      Serial.print(" "); Serial.println(F_CPU/1000000);
    }
    else if (cmd == "W") {
      for (int i = 0; i < NSENS; i++) {
        uint8_t id = rByte(i, REG_REVID);
        Serial.print("R ID s"); Serial.print(i);
        Serial.print(" 0x"); Serial.print(id, HEX);
        Serial.println(id == 0x22 ? " OK" : " ??");   // 0x22 expected
      }
    }
    else if (cmd.startsWith("C ")) {
      int cc = cmd.substring(2).toInt(); if (cc<25) cc=25; if (cc>800) cc=800;
      cycleCount = cc;
      for (int i = 0; i < NSENS; i++) { setCycleCount(i, cycleCount); uint8_t c=0x79; wReg(i,REG_CMM,&c,1); }
      Serial.print("R CC "); Serial.print(cycleCount);
      Serial.print(" (~"); Serial.print(lsbPerUT(),1); Serial.println(" LSB/uT)");
    }
    else if (cmd.startsWith("R ")) {
      tmrcRate = (uint8_t)strtol(cmd.substring(2).c_str(), NULL, 16);
      for (int i = 0; i < NSENS; i++) { uint8_t t=tmrcRate; wReg(i,REG_TMRC,&t,1); uint8_t c=0x79; wReg(i,REG_CMM,&c,1); }
      Serial.print("R TMRC 0x"); Serial.println(tmrcRate, HEX);
    }
    else if (cmd == "Z") { captureBaseline(); }
    else if (cmd == "S") { streaming = true;  Serial.println("R STREAM ON"); }
    else if (cmd == "x") { streaming = false; Serial.println("R STREAM OFF"); }
  }

  if (streaming) {
    uint32_t ms = millis();
    for (int i = 0; i < NSENS; i++) {
      float x,y,z;
      if (readField(i,&x,&y,&z)) {
        x -= baseX[i]; y -= baseY[i]; z -= baseZ[i];
        float mag = sqrtf(x*x + y*y + z*z);
        Serial.print("T "); Serial.print(ms);
        Serial.print(" s"); Serial.print(i);
        Serial.print(" "); Serial.print(x,4);
        Serial.print(" "); Serial.print(y,4);
        Serial.print(" "); Serial.print(z,4);
        Serial.print(" "); Serial.println(mag,4);
      }
    }
  }
}
