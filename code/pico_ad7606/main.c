/*
 * PICO-AD7606 — the read-side instrument (EGT/Two Rocks bench).
 *
 * Role: a dumb, honest, verifiable sampler. 8 bipolar channels captured at the
 * SAME instant by the AD7606 (true simultaneous sampling), streamed raw to the
 * PC over USB CDC. All physics math (lock-in, Dphase, pi/8 anchor units) stays
 * on the PC where it is inspectable. The instrument adds nothing and hides
 * nothing: it paces conversions, reads bits, frames them, ships them.
 *
 * Board: Raspberry Pi Pico W (RP2040). ADC: AD7606 module, SPI SERIAL mode
 * (single DOUTA line, 8 x 16 bits = 128 SCLKs per conversion). 3.3V logic.
 *
 * Serial protocol (USB CDC, 115200+, line-oriented commands):
 *   "P"                  -> "R PONG pico-ad7606 v1 <f_cpu_MHz>"
 *   "S <rate_hz>"        -> start binary streaming at rate (500..50000 Hz)
 *                           frames: [0xA5 0x5A][u32 seq][8 x i16 ch1..ch8] LE
 *   "T <rate_hz> <n>"    -> text mode: n lines "D <seq> <c1> ... <c8>"
 *   "x" (any byte in stream) -> stop, "R STOPPED <frames>"
 *   "Z"                  -> single conversion, text line (sanity check)
 *
 * Wiring (see WIRING.md): CONVST=GP2, BUSY=GP3, RST=GP4, CS=GP5,
 * SCLK=GP6 (SPI0 SCK), DOUTA=GP4?? -> GP7 (SPI0 RX). OS[2:0]=GND, RANGE=+-5V.
 */

#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"
#include "hardware/clocks.h"

#define PIN_CONVST 2
#define PIN_BUSY   3
#define PIN_RST    4
#define PIN_CS     5
#define PIN_SCK    6
#define PIN_MISO   7
#define SPI_PORT   spi0
#define SPI_HZ     (15 * 1000 * 1000)   /* 15 MHz read clock */

static int16_t sample[8];

static void ad7606_reset(void) {
    gpio_put(PIN_RST, 1); sleep_us(2); gpio_put(PIN_RST, 0); sleep_us(2);
}

/* one full conversion: pulse CONVST, wait BUSY low, clock out 8 x 16 bits */
static bool ad7606_convert(void) {
    gpio_put(PIN_CONVST, 0); sleep_us(1);
    gpio_put(PIN_CONVST, 1);
    /* BUSY rises ~25ns after CONVST, falls when conversion done (~4us no-OS) */
    absolute_time_t t0 = get_absolute_time();
    while (gpio_get(PIN_BUSY)) {
        if (absolute_time_diff_us(t0, get_absolute_time()) > 1000) return false;
    }
    uint8_t raw[16];
    gpio_put(PIN_CS, 0);
    spi_read_blocking(SPI_PORT, 0x00, raw, 16);
    gpio_put(PIN_CS, 1);
    for (int i = 0; i < 8; i++)
        sample[i] = (int16_t)((raw[2*i] << 8) | raw[2*i + 1]);  /* MSB first */
    return true;
}

static int read_line(char *buf, int maxlen, uint32_t timeout_ms) {
    int n = 0;
    absolute_time_t t0 = get_absolute_time();
    while (n < maxlen - 1) {
        int c = getchar_timeout_us(1000);
        if (c == PICO_ERROR_TIMEOUT) {
            if (absolute_time_diff_us(t0, get_absolute_time()) > timeout_ms * 1000ull)
                return -1;
            continue;
        }
        if (c == '\n' || c == '\r') break;
        buf[n++] = (char)c;
    }
    buf[n] = 0;
    return n;
}

static void stream_binary(uint32_t rate_hz) {
    if (rate_hz < 500) rate_hz = 500;
    if (rate_hz > 50000) rate_hz = 50000;
    uint64_t period_us = 1000000ull / rate_hz;
    uint32_t seq = 0;
    absolute_time_t next = get_absolute_time();
    for (;;) {
        /* stop on any inbound byte */
        int c = getchar_timeout_us(0);
        if (c != PICO_ERROR_TIMEOUT) break;
        next = delayed_by_us(next, period_us);
        if (!ad7606_convert()) continue;
        uint8_t frame[2 + 4 + 16];
        frame[0] = 0xA5; frame[1] = 0x5A;
        memcpy(frame + 2, &seq, 4);
        memcpy(frame + 6, sample, 16);
        fwrite(frame, 1, sizeof frame, stdout);
        fflush(stdout);
        seq++;
        sleep_until(next);
    }
    printf("\nR STOPPED %lu\n", (unsigned long)seq);
}

static void stream_text(uint32_t rate_hz, uint32_t nsamp) {
    if (rate_hz < 1) rate_hz = 1;
    if (rate_hz > 5000) rate_hz = 5000;      /* text mode is for humans */
    uint64_t period_us = 1000000ull / rate_hz;
    absolute_time_t next = get_absolute_time();
    for (uint32_t s = 0; s < nsamp; s++) {
        int c = getchar_timeout_us(0);
        if (c != PICO_ERROR_TIMEOUT) { printf("R STOPPED %lu\n", (unsigned long)s); return; }
        next = delayed_by_us(next, period_us);
        if (ad7606_convert())
            printf("D %lu %d %d %d %d %d %d %d %d\n", (unsigned long)s,
                   sample[0], sample[1], sample[2], sample[3],
                   sample[4], sample[5], sample[6], sample[7]);
        sleep_until(next);
    }
    printf("R DONE %lu\n", (unsigned long)nsamp);
}

int main(void) {
    stdio_init_all();

    gpio_init(PIN_CONVST); gpio_set_dir(PIN_CONVST, GPIO_OUT); gpio_put(PIN_CONVST, 1);
    gpio_init(PIN_BUSY);   gpio_set_dir(PIN_BUSY, GPIO_IN);
    gpio_init(PIN_RST);    gpio_set_dir(PIN_RST, GPIO_OUT);   gpio_put(PIN_RST, 0);
    gpio_init(PIN_CS);     gpio_set_dir(PIN_CS, GPIO_OUT);    gpio_put(PIN_CS, 1);

    spi_init(SPI_PORT, SPI_HZ);
    spi_set_format(SPI_PORT, 8, SPI_CPOL_1, SPI_CPHA_0, SPI_MSB_FIRST); /* mode 2: DOUT valid on SCLK falling */
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);

    ad7606_reset();

    char line[64];
    for (;;) {
        if (read_line(line, sizeof line, 60000) <= 0) continue;
        if (line[0] == 'P') {
            printf("R PONG pico-ad7606 v1 %lu\n", (unsigned long)(clock_get_hz(clk_sys) / 1000000));
        } else if (line[0] == 'Z') {
            if (ad7606_convert())
                printf("D 0 %d %d %d %d %d %d %d %d\n",
                       sample[0], sample[1], sample[2], sample[3],
                       sample[4], sample[5], sample[6], sample[7]);
            else printf("R ERR busy-timeout\n");
        } else if (line[0] == 'S') {
            uint32_t rate = 50000;
            sscanf(line + 1, "%lu", (unsigned long *)&rate);
            printf("R STREAM %lu\n", (unsigned long)rate);
            stream_binary(rate);
        } else if (line[0] == 'T') {
            uint32_t rate = 100, n = 100;
            sscanf(line + 1, "%lu %lu", (unsigned long *)&rate, (unsigned long *)&n);
            stream_text(rate, n);
        } else {
            printf("R ERR badcmd\n");
        }
    }
}
