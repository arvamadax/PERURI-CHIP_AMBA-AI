#include "ascon_hps.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mman.h>
#include <unistd.h>

#include "ascon_soft.h"

enum { R_CTRL = 0, R_BLK = 1, R_STATUS = 2, R_KEY = 4, R_NONCE = 8, R_DIN = 12, R_TAGIN = 16,
       R_DOUT = 20, R_TAGOUT = 24, R_DIGEST = 28 };
enum { S_BUSY = 1, S_READY = 2, S_DONE = 4, S_TAG_OK = 8 };
#define POLL_LIMIT 10000000

int ascon_open(ascon_dev *d, uint32_t offset) {
    d->fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (d->fd < 0) return -1;
    d->map = mmap(NULL, ASCON_LWBRIDGE_SPAN, PROT_READ | PROT_WRITE, MAP_SHARED, d->fd, ASCON_LWBRIDGE_BASE);
    if (d->map == MAP_FAILED) { close(d->fd); return -1; }
    d->r = (volatile uint32_t *)((uint8_t *)d->map + offset);
    return 0;
}

void ascon_close(ascon_dev *d) {
    if (d->fd >= 0) { munmap(d->map, ASCON_LWBRIDGE_SPAN); close(d->fd); }
}

void ascon_attach(ascon_dev *d, volatile uint32_t *regs) {
    d->r = regs; d->fd = -1; d->map = NULL;
}

static uint32_t le32(const uint8_t *p) { return p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24; }

static void put_le32(uint8_t *p, uint32_t v) { for (int i = 0; i < 4; i++) p[i] = (uint8_t)(v >> (8 * i)); }

static void wr_big(ascon_dev *d, int base, const uint8_t *p, size_t n) {   /* n kelipatan 4 */
    for (size_t i = 0; i < n; i += 4) d->r[base + i / 4] = le32(p + i);
}

static void rd_big(ascon_dev *d, int base, uint8_t *p, size_t n) {
    for (size_t i = 0; i < n; i += 4) put_le32(p + i, d->r[base + i / 4]);
}

static int wait_status(ascon_dev *d, uint32_t mask, uint32_t *status) {
    for (long i = 0; i < POLL_LIMIT; i++) {
        uint32_t s = d->r[R_STATUS];
        if (s & mask) { if (status) *status = s; return 0; }
    }
    return -2;                                           /* timeout */
}

/* Satu transaksi: start, kirim blok AD lalu blok data (blok terakhir diberi LAST), kumpulkan keluaran. */
static int run(ascon_dev *d, int mode, const uint8_t *key, const uint8_t *nonce, const uint8_t *tag_in,
               const uint8_t *ad, size_t adlen, const uint8_t *in, size_t inlen, uint8_t *out) {
    size_t rate = mode == ASCON_HASH ? 8 : 16;
    uint32_t st;
    if (mode != ASCON_HASH) { wr_big(d, R_KEY, key, 16); wr_big(d, R_NONCE, nonce, 16); }
    if (mode == ASCON_DEC) wr_big(d, R_TAGIN, tag_in, 16);
    d->r[R_CTRL] = 1u | (uint32_t)mode << 1;
    for (int pass = 0; pass < 2; pass++) {              /* pass 0: AD, pass 1: data */
        const uint8_t *buf = pass ? in : ad;
        size_t len = pass ? inlen : adlen, off = 0;
        if (!pass && !len) continue;
        do {
            size_t n = len - off < rate ? len - off : rate;
            uint8_t blk[16] = {0};
            memcpy(blk, buf + off, n);
            if (wait_status(d, S_READY, NULL)) return -2;
            wr_big(d, R_DIN, blk, 16);
            d->r[R_BLK] = (uint32_t)n | (uint32_t)(off + n >= len) << 8 | (uint32_t)(pass == 0) << 9;
            if (pass && mode != ASCON_HASH) {
                if (wait_status(d, S_READY | S_DONE, NULL)) return -2;
                rd_big(d, R_DOUT, blk, 16);
                memcpy(out + off, blk, n);
            }
            off += n;
        } while (off < len);
    }
    if (wait_status(d, S_DONE, &st)) return -2;
    return (mode == ASCON_DEC && !(st & S_TAG_OK)) ? -1 : 0;
}

int ascon_hash256(ascon_dev *d, const uint8_t *msg, size_t len, uint8_t digest[32]) {
    int rc = run(d, ASCON_HASH, NULL, NULL, NULL, NULL, 0, msg, len, NULL);
    if (rc == 0) rd_big(d, R_DIGEST, digest, 32);
    return rc;
}

int ascon_encrypt_explicit_nonce(ascon_dev *d, const uint8_t key[16], const uint8_t nonce[16],
                                 const uint8_t *ad, size_t adlen, const uint8_t *pt, size_t ptlen,
                                 uint8_t *ct, uint8_t tag[16]) {
    int rc = run(d, ASCON_ENC, key, nonce, NULL, ad, adlen, pt, ptlen, ct);
    if (rc == 0) rd_big(d, R_TAGOUT, tag, 16);
    return rc;
}

int ascon_decrypt(ascon_dev *d, const uint8_t key[16], const uint8_t nonce[16],
                  const uint8_t *ad, size_t adlen, const uint8_t *ct, size_t ctlen,
                  const uint8_t tag[16], uint8_t *pt) {
    int rc = run(d, ASCON_DEC, key, nonce, tag, ad, adlen, ct, ctlen, pt);
    if (rc == -1) memset(pt, 0, ctlen);                  /* buang plaintext bila tag salah */
    return rc;
}

int ascon_session_init(ascon_session *s, ascon_dev *d, const uint8_t key[16], const char *state_dir) {
    uint8_t h[32];
    char id[17];
    s->dev = d;
    memcpy(s->key, key, 16);
    ascon_soft_hash256(h, key, 16);                      /* id key (bukan rahasia): 8 byte pertama hash */
    for (int i = 0; i < 8; i++) sprintf(id + 2 * i, "%02x", h[i]);
    if (snprintf(s->path, sizeof s->path, "%s/%s.ctr", state_dir, id) >= (int)sizeof s->path) return -1;
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0 || read(fd, s->salt, 8) != 8) { if (fd >= 0) close(fd); return -1; }
    close(fd);
    return 0;
}

int ascon_next_nonce(ascon_session *s, uint8_t nonce[16]) {
    uint8_t buf[8] = {0};
    int fd = open(s->path, O_RDWR | O_CREAT | O_SYNC, 0600);
    if (fd < 0) return -1;
    if (flock(fd, LOCK_EX) < 0) { close(fd); return -1; }
    ssize_t n = pread(fd, buf, 8, 0);
    if (n != 0 && n != 8) { close(fd); return -1; }
    uint64_t ctr = 0;
    for (int i = 0; i < 8; i++) ctr |= (uint64_t)buf[i] << (8 * i);
    if (ctr == UINT64_MAX) { close(fd); return -1; }     /* penghitung habis: ganti key */
    uint64_t next = ctr + 1;
    for (int i = 0; i < 8; i++) buf[i] = (uint8_t)(next >> (8 * i));
    int ok = pwrite(fd, buf, 8, 0) == 8 && fsync(fd) == 0;
    close(fd);                                           /* lepas lock */
    if (!ok) return -1;
    for (int i = 0; i < 8; i++) nonce[i] = (uint8_t)(ctr >> (8 * i));
    memcpy(nonce + 8, s->salt, 8);
    return 0;
}

int ascon_seal(ascon_session *s, const uint8_t *ad, size_t adlen, const uint8_t *pt, size_t ptlen,
               uint8_t nonce_out[16], uint8_t *ct, uint8_t tag[16]) {
    if (ascon_next_nonce(s, nonce_out)) return -1;
    return ascon_encrypt_explicit_nonce(s->dev, s->key, nonce_out, ad, adlen, pt, ptlen, ct, tag);
}
