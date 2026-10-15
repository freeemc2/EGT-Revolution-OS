/*
  teensy_ads1256.ino — ADS1256 read-side instrument + three-coil drive, Teensy 4.1.
  v1 (2026-10-15, tonic). COM10 holds the experiment: this one board drives the
  three-coil set AND reads the taps through an ADS1256 (24-bit delta-sigma, PGA).
  The ADS1256 replaces the AD7606 on the read side — its on-chip PGA is the gain
  stage (no external op-amp), its differential inputs read tapA-tapB directly and
  reject the common-mode DC offset.

  READ SIDE is a DUMB STREAMER (job spec): raw 24-bit counts only, no thresholds,
  no booleans, no on-board phase math. All reduction host-side.

  DRIVE SIDE is ported verbatim from teensy_three_rocks_orig / ad7606 v2 (same
  teensy-only drive): base square per strand + overlay tone, XOR mix, TD knob,
  per-coil offsets, drive mask.

  --- ADS1256 wiring (SPI MODE 1) ---
    Teensy 13 -> SCLK      Teensy 11 -> DIN (MOSI)    Teensy 12 <- DOUT (MISO)
    Teensy 10 -> CS        Teensy  9 <- DRDY          Teensy  8 -> RESET
    Teensy  7 -> PDWN/SYNC (held HIGH; SYNC issued over SPI)
    ADS1256: AVDD/DVDD 5V & 3.3V per board, Vref 2.5V (onboard), GND common w/ Teensy.
    Differential inputs: coil0 = AIN0(+)/AIN1(-), coil1 = AIN2/AIN3, coil2 = AIN4/AIN5.
    NOTE: ADS1256 DOUT swings to DVDD. If the board's DVDD is 5V, protect Teensy
    pin 12 (series R / level shift) — Teensy 4.1 is NOT 5V-tolerant. 3.3V DVDD = direct.

  --- Drive wiring (WIRING v2 2026-09-15, Brian-verified) ---
    pin 2 -> 220R -> coil0, pin 3 -> coil1, pin 4 -> coil2; winding souths -> GND.

  Serial (115200 framing ignored; native USB):
    P            -> "R PONG ads1256+drive v1 <sps> PGA<g> mode<m>"
    --- read side ---
    G            -> start free-run streaming (round-robin 3 differential coils)
    g            -> stop streaming only (drive survives)
    C            -> one round (one JSON line, all 3 coils)
    PGA <1..64>  -> set PGA (power of two); re-inits ADS1256
    DR <sps>     -> set data rate (e.g. 100 500 1000 2000 7500); re-inits
    Z            -> ADS1256 self-calibrate (SELFCAL)
    I            -> re-init ADS1256 registers
    --- drive side (orig semantics) ---
    L <freq> / M <m> / K <k> / U <deg> / O <k> <deg> / DM <k> <0|1>
    T <freq> / TM <m> / TD <pct>
    x            -> STOP ALL: drive off (pins low) + streaming off

  Output per round (3 coils, each a settled differential read):
    {"t_us":<micros>,"seq":<n>,"ch":[c0,c1,c2]}  raw signed 24-bit counts.
    LSB volts = (2*Vref/PGA)/2^24  (reported in the header; applied host-side).
    Header on boot / G / config change carries sps, pga, vref, lsb_nV, and drive state.
*/

#include <SPI.h>

// ---------- ADS1256 read side ----------
const int PIN_SCLK = 13, PIN_DIN = 11, PIN_DOUT = 12, PIN_CS = 10;
const int PIN_DRDY = 9, PIN_RST = 8, PIN_PDWN = 7;
// ADS1256 SCLK max ~ fCLKIN/4 (~1.92 MHz @ 7.68 MHz). Use 1 MHz, MODE 1.
SPISettings ADS_SPI(1000000, MSBFIRST, SPI_MODE1);

// commands
const uint8_t CMD_WAKEUP=0x00, CMD_RDATA=0x01, CMD_SDATAC=0x0F, CMD_RREG=0x10,
              CMD_WREG=0x50, CMD_SELFCAL=0xF0, CMD_SYNC=0xFC, CMD_RESET=0xFE;
// registers
const uint8_t REG_STATUS=0x00, REG_MUX=0x01, REG_ADCON=0x02, REG_DRATE=0x03;
// the 3 coil differential MUX bytes: (AINp<<4)|AINn
const uint8_t MUX_COIL[3] = {0x01, 0x23, 0x45};   // coil0 AIN0-1, coil1 AIN2-3, coil2 AIN4-5
const float VREF = 2.5f;

uint8_t pga_code(int g){ switch(g){case 1:return 0;case 2:return 1;case 4:return 2;
  case 8:return 3;case 16:return 4;case 32:return 5;case 64:return 6;} return 6; }
uint8_t drate_code(long sps){ // nearest standard code
  if(sps>=30000)return 0xF0; if(sps>=15000)return 0xE0; if(sps>=7500)return 0xD0;
  if(sps>=3750)return 0xC0; if(sps>=2000)return 0xB0; if(sps>=1000)return 0xA1;
  if(sps>=500)return 0x92; if(sps>=100)return 0x82; if(sps>=60)return 0x72;
  if(sps>=50)return 0x63; if(sps>=30)return 0x53; return 0x23; }

int pga = 64;
long sps = 1000;
bool streaming = false;
uint32_t seq = 0;

void ads_wait_drdy(uint32_t to_us=100000){ elapsedMicros t; while(digitalReadFast(PIN_DRDY)){ if(t>to_us) return; } }

void ads_wreg(uint8_t reg, uint8_t val){
  SPI.beginTransaction(ADS_SPI); digitalWriteFast(PIN_CS,LOW);
  SPI.transfer(CMD_WREG|reg); SPI.transfer(0x00); SPI.transfer(val);
  digitalWriteFast(PIN_CS,HIGH); SPI.endTransaction();
  delayMicroseconds(10);
}

void ads_cmd(uint8_t c){
  SPI.beginTransaction(ADS_SPI); digitalWriteFast(PIN_CS,LOW);
  SPI.transfer(c); digitalWriteFast(PIN_CS,HIGH); SPI.endTransaction();
  delayMicroseconds(10);
}

void ads_reset(){
  digitalWriteFast(PIN_RST,LOW); delayMicroseconds(10);
  digitalWriteFast(PIN_RST,HIGH); delay(5);
  ads_wait_drdy();
}

void ads_init(){
  ads_reset();
  ads_cmd(CMD_SDATAC);                 // stop continuous so we can WREG
  ads_wreg(REG_STATUS, 0x01);          // MSB first, auto-cal off, analog buffer ON (bit0)
  ads_wreg(REG_ADCON,  pga_code(pga)); // clkout off, sensor-detect off, PGA
  ads_wreg(REG_DRATE,  drate_code(sps));
  ads_wreg(REG_MUX,    MUX_COIL[0]);
  ads_cmd(CMD_SELFCAL);
  ads_wait_drdy(500000);
}

// read one settled differential sample on coil index ci (changes MUX, SYNC/WAKEUP, waits DRDY)
int32_t ads_read_coil(int ci){
  ads_wait_drdy();
  ads_wreg(REG_MUX, MUX_COIL[ci]);
  ads_cmd(CMD_SYNC);
  ads_cmd(CMD_WAKEUP);
  ads_wait_drdy();                     // settled conversion ready
  SPI.beginTransaction(ADS_SPI); digitalWriteFast(PIN_CS,LOW);
  SPI.transfer(CMD_RDATA);
  delayMicroseconds(7);                // t6 ~ 50 tCLKIN before data
  uint32_t v = ((uint32_t)SPI.transfer(0)<<16)|((uint32_t)SPI.transfer(0)<<8)|SPI.transfer(0);
  digitalWriteFast(PIN_CS,HIGH); SPI.endTransaction();
  if(v & 0x800000) v |= 0xFF000000;    // sign-extend 24->32
  return (int32_t)v;
}

// ---------- drive side (ported from teensy_three_rocks_orig / ad7606 v2) ----------
const int N_COILS = 3;
const int DRIVE_PINS[N_COILS] = {2, 3, 4};
const float FS = 100000.0f, TWO_PI_F = 6.28318530718f, PI_F = 3.14159265f;
volatile float phase=0, dphi=0, strandPhase[N_COILS], strandOff[N_COILS];
volatile int driveMode=0, singleK=0; volatile float customUnitRad=0;
volatile float coilOff[N_COILS]={0,0,0}, dphi2=0, phase2=0; volatile int overlayMix=0;
volatile bool driveEn[N_COILS]={true,true,true}; volatile float overlayDuty=1.0f;
float baseFreq=0, ovlFreq=0; bool driveTimerOn=false; IntervalTimer tick;

void isr(){
  bool ov=(dphi2>0)&&(phase2<PI_F*overlayDuty);
  for(int k=0;k<N_COILS;k++){
    bool driven=((driveMode==1)?(k==singleK):(driveMode>=2))&&driveEn[k];
    bool on=false;
    if(driven){ float ph=strandPhase[k]+coilOff[k];
      if(ph>=TWO_PI_F)ph-=TWO_PI_F; if(ph<0)ph+=TWO_PI_F;
      bool base_on=(ph<PI_F);
      if(overlayMix==1&&dphi2>0) on=base_on^ov;
      else if(overlayMix==2&&dphi2>0) on=base_on&&ov; else on=base_on; }
    digitalWriteFast(DRIVE_PINS[k], on?HIGH:LOW);
  }
  phase+=dphi; if(phase>=TWO_PI_F)phase-=TWO_PI_F;
  if(dphi2>0){ phase2+=dphi2; if(phase2>=TWO_PI_F)phase2-=TWO_PI_F; }
  for(int k=0;k<N_COILS;k++){ strandPhase[k]+=dphi; if(strandPhase[k]>=TWO_PI_F)strandPhase[k]-=TWO_PI_F; }
}
float staggerUnitRad(){ if(driveMode==3)return TWO_PI_F/N_COILS; if(driveMode==4)return customUnitRad; return 0; }
void applyMode(int m){ noInterrupts(); driveMode=m; float u=staggerUnitRad();
  for(int k=0;k<N_COILS;k++){ strandOff[k]=-u*k; strandPhase[k]=phase+strandOff[k];
    while(strandPhase[k]<0)strandPhase[k]+=TWO_PI_F; while(strandPhase[k]>=TWO_PI_F)strandPhase[k]-=TWO_PI_F; }
  interrupts(); }
void setBaseFreq(float f){ baseFreq=f; noInterrupts(); dphi=TWO_PI_F*f/FS; interrupts(); applyMode(driveMode); }
void driveStart(){ if(!driveTimerOn){ tick.begin(isr,1000000.0f/FS); driveTimerOn=true; } }
void driveStopAll(){ if(driveTimerOn){ tick.end(); driveTimerOn=false; } driveMode=0;
  for(int k=0;k<N_COILS;k++) digitalWriteFast(DRIVE_PINS[k],LOW); }

// ---------- output ----------
void emit_header(){
  float lsb_nV = (2.0f*VREF/pga)/16777216.0f*1e9f;
  Serial.print("{\"hdr\":1,\"fw\":\"ads1256+drive v1\",\"sps\":"); Serial.print(sps);
  Serial.print(",\"pga\":"); Serial.print(pga);
  Serial.print(",\"vref\":"); Serial.print(VREF,3);
  Serial.print(",\"lsb_nV\":"); Serial.print(lsb_nV,3);
  Serial.print(",\"coils\":\"AIN0-1,AIN2-3,AIN4-5\"");
  Serial.print(",\"drive\":{\"mode\":"); Serial.print(driveMode);
  Serial.print(",\"base_hz\":"); Serial.print(baseFreq);
  Serial.print(",\"overlay_hz\":"); Serial.print(ovlFreq);
  Serial.print(",\"mix\":"); Serial.print(overlayMix);
  Serial.print(",\"td_pct\":"); Serial.print(overlayDuty*100.0f);
  Serial.print(",\"running\":"); Serial.print(driveTimerOn?"true":"false");
  Serial.println("}}");
}

void emit_round(){
  uint32_t t=micros();
  int32_t c0=ads_read_coil(0), c1=ads_read_coil(1), c2=ads_read_coil(2);
  Serial.print("{\"t_us\":"); Serial.print(t);
  Serial.print(",\"seq\":"); Serial.print(seq++);
  Serial.print(",\"ch\":["); Serial.print(c0); Serial.print(',');
  Serial.print(c1); Serial.print(','); Serial.print(c2); Serial.println("]}");
}

void handle_line(char*line){
  if(line[0]=='T'&&line[1]=='M'){ overlayMix=atoi(line+2); Serial.print("R TMIX "); Serial.println(overlayMix); return; }
  if(line[0]=='T'&&line[1]=='D'){ float d=atof(line+2)/100.0f; overlayDuty=d<0?0:(d>1?1:d);
    Serial.print("R TDUTY "); Serial.println(overlayDuty*100.0f); return; }
  if(line[0]=='D'&&line[1]=='M'){ int k,v; if(sscanf(line+2,"%d %d",&k,&v)==2&&k>=0&&k<N_COILS){
    driveEn[k]=(v!=0); Serial.print("R DMASK "); Serial.print(k); Serial.print(' '); Serial.println(driveEn[k]?1:0);} return; }
  if(line[0]=='D'&&line[1]=='R'){ long v=atol(line+2); if(v>=2&&v<=30000){ sps=v; ads_init(); emit_header(); }
    else Serial.println("{\"err\":\"DR 2..30000\"}"); return; }
  switch(line[0]){
    case 'P': Serial.print("R PONG ads1256+drive v1 "); Serial.print(sps);
      Serial.print(" PGA"); Serial.print(pga); Serial.print(" mode"); Serial.println(driveMode); break;
    case 'G': streaming=true; seq=0; emit_header(); break;
    case 'g': streaming=false; Serial.println("R STREAMOFF"); break;
    case 'x': streaming=false; driveStopAll(); Serial.println("R LOCKED off"); break;
    case 'C': emit_round(); break;
    case 'I': ads_init(); Serial.println("R ADSINIT"); break;
    case 'Z': ads_cmd(CMD_SELFCAL); ads_wait_drdy(500000); Serial.println("R SELFCAL"); break;
    case 'L':{ float f=atof(line+1); if(f>0&&f<=30000){ setBaseFreq(f); driveStart();
      Serial.print("R LOCK "); Serial.println(f); emit_header(); } else Serial.println("{\"err\":\"L freq\"}"); break; }
    case 'M': applyMode(atoi(line+1)); Serial.print("R MODE "); Serial.println(driveMode); break;
    case 'K': singleK=constrain(atoi(line+1),0,N_COILS-1); Serial.print("R K "); Serial.println(singleK); break;
    case 'U': customUnitRad=atof(line+1)*TWO_PI_F/360.0f; Serial.println("R UNIT"); break;
    case 'O':{ int k; float d; if(sscanf(line+1,"%d %f",&k,&d)==2&&k>=0&&k<N_COILS){
      coilOff[k]=d*TWO_PI_F/360.0f; Serial.print("R OFF "); Serial.print(k); Serial.print(' '); Serial.println(d);} break; }
    case 'T':{ ovlFreq=atof(line+1); noInterrupts(); dphi2=(ovlFreq>0)?TWO_PI_F*ovlFreq/FS:0; phase2=0; interrupts();
      Serial.print("R TONE2 "); Serial.println(ovlFreq); break; }
    case 'V':{ long g=atol(line+1); // PGA via 'PGA' handled below; keep 'V' as no-op range note
      Serial.println("R OK"); break; }
    default:
      if(!strncmp(line,"PGA",3)){ long g=atol(line+3);
        if(g==1||g==2||g==4||g==8||g==16||g==32||g==64){ pga=g; ads_init(); emit_header(); }
        else Serial.println("{\"err\":\"PGA 1,2,4,8,16,32,64\"}"); }
      break;
  }
}

void setup(){
  pinMode(PIN_CS,OUTPUT); digitalWriteFast(PIN_CS,HIGH);
  pinMode(PIN_RST,OUTPUT); digitalWriteFast(PIN_RST,HIGH);
  pinMode(PIN_PDWN,OUTPUT); digitalWriteFast(PIN_PDWN,HIGH);  // not powered down
  pinMode(PIN_DRDY,INPUT);
  for(int k=0;k<N_COILS;k++){ pinMode(DRIVE_PINS[k],OUTPUT); digitalWriteFast(DRIVE_PINS[k],LOW); }
  SPI.begin();
  Serial.begin(115200);
  delay(50);
  ads_init();
  emit_header();
}

char buf[48]; int blen=0;
void loop(){
  while(Serial.available()){
    char c=Serial.read();
    if(c=='\n'||c=='\r'){ if(blen){ buf[blen]=0; handle_line(buf); blen=0; } }
    else if(blen<47) buf[blen++]=c;
  }
  if(streaming) emit_round();   // free-run: as fast as settled round-robin allows
}
