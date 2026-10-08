#include "ascon_soft.h"

#include <string.h>

typedef uint64_t u64;

#define AEAD_IV 0x00001000808c0001ULL
#define HASH_IV 0x0000080100cc0002ULL

static u64 ror(u64 x, int n) { return (x >> n) | (x << (64 - n)); }

static u64 ld(const uint8_t *p, size_t n) {
    u64 x = 0;
    for (size_t i = 0; i < n; i++) x |= (u64)p[i] << (8 * i);
    return x;
}

static void sto(uint8_t *p, u64 x, size_t n) {
    for (size_t i = 0; i < n; i++) p[i] = (uint8_t)(x >> (8 * i));
}

static void perm(u64 s[5], int rounds) {
    for (int r = 12 - rounds; r < 12; r++) {
        u64 t[5];
        s[2] ^= (u64)(((15 - r) << 4) | r);
        s[0] ^= s[4]; s[4] ^= s[3]; s[2] ^= s[1];
        for (int i = 0; i < 5; i++) t[i] = ~s[i] & s[(i + 1) % 5];
        for (int i = 0; i < 5; i++) s[i] ^= t[(i + 1) % 5];
        s[1] ^= s[0]; s[0] ^= s[4]; s[3] ^= s[2]; s[2] = ~s[2];
        s[0] ^= ror(s[0], 19) ^ ror(s[0], 28);
        s[1] ^= ror(s[1], 61) ^ ror(s[1], 39);
        s[2] ^= ror(s[2], 1) ^ ror(s[2], 6);
        s[3] ^= ror(s[3], 10) ^ ror(s[3], 17);
        s[4] ^= ror(s[4], 7) ^ ror(s[4], 41);
    }
}

static void init(u64 s[5], u64 k[2], const uint8_t n[16], const uint8_t key[16]) {
    k[0] = ld(key, 8); k[1] = ld(key + 8, 8);
    s[0] = AEAD_IV; s[1] = k[0]; s[2] = k[1]; s[3] = ld(n, 8); s[4] = ld(n + 8, 8);
    perm(s, 12);
    s[3] ^= k[0]; s[4] ^= k[1];
}

/* XOR len (<=16) byte ke (s0,s1) dan tambah padding 0x01 setelahnya bila len < 16. */
static void absorb_partial(u64 s[5], const uint8_t *in, size_t len) {
    if (len >= 8) { s[0] ^= ld(in, 8); s[1] ^= ld(in + 8, len - 8) ^ (1ULL << (8 * (len - 8))); }
    else          { s[0] ^= ld(in, len) ^ (1ULL << (8 * len)); }
}

static void finalize(u64 s[5], const u64 k[2], uint8_t tag[16]) {
    s[2] ^= k[0]; s[3] ^= k[1];
    perm(s, 12);
    sto(tag, s[3] ^ k[0], 8); sto(tag + 8, s[4] ^ k[1], 8);
}

static void absorb_ad(u64 s[5], const uint8_t *ad, size_t adlen) {
    if (adlen) {
        for (; adlen >= 16; ad += 16, adlen -= 16) { s[0] ^= ld(ad, 8); s[1] ^= ld(ad + 8, 8); perm(s, 8); }
        absorb_partial(s, ad, adlen);
        perm(s, 8);
    }
    s[4] ^= 1ULL << 63;
}

void ascon_soft_encrypt(uint8_t *c, uint8_t tag[16], const uint8_t *m, size_t mlen,
                        const uint8_t *ad, size_t adlen, const uint8_t n[16], const uint8_t key[16]) {
    u64 s[5], k[2];
    init(s, k, n, key);
    absorb_ad(s, ad, adlen);
    for (; mlen >= 16; m += 16, c += 16, mlen -= 16) {
        s[0] ^= ld(m, 8); s[1] ^= ld(m + 8, 8);
        sto(c, s[0], 8); sto(c + 8, s[1], 8);
        perm(s, 8);
    }
    if (mlen >= 8) {
        s[0] ^= ld(m, 8); s[1] ^= ld(m + 8, mlen - 8);
        sto(c, s[0], 8); sto(c + 8, s[1], mlen - 8);
        s[1] ^= 1ULL << (8 * (mlen - 8));
    } else {
        s[0] ^= ld(m, mlen);
        sto(c, s[0], mlen);
        s[0] ^= 1ULL << (8 * mlen);
    }
    finalize(s, k, tag);
}

int ascon_soft_decrypt(uint8_t *m, const uint8_t *c, size_t clen, const uint8_t tag[16],
                       const uint8_t *ad, size_t adlen, const uint8_t n[16], const uint8_t key[16]) {
    u64 s[5], k[2];
    uint8_t *m0 = m, t[16];
    size_t total = clen;
    init(s, k, n, key);
    absorb_ad(s, ad, adlen);
    for (; clen >= 16; m += 16, c += 16, clen -= 16) {
        u64 c0 = ld(c, 8), c1 = ld(c + 8, 8);
        sto(m, s[0] ^ c0, 8); sto(m + 8, s[1] ^ c1, 8);
        s[0] = c0; s[1] = c1;
        perm(s, 8);
    }
    if (clen >= 8) {
        u64 c0 = ld(c, 8), c1 = ld(c + 8, clen - 8);
        u64 keep = (clen - 8) ? ~0ULL << (8 * (clen - 8)) : ~0ULL;
        sto(m, s[0] ^ c0, 8); sto(m + 8, s[1] ^ c1, clen - 8);
        s[0] = c0; s[1] = (s[1] & keep) | c1;
        s[1] ^= 1ULL << (8 * (clen - 8));
    } else {
        u64 c0 = ld(c, clen);
        u64 keep = clen ? ~0ULL << (8 * clen) : ~0ULL;
        sto(m, s[0] ^ c0, clen);
        s[0] = (s[0] & keep) | c0;
        s[0] ^= 1ULL << (8 * clen);
    }
    finalize(s, k, t);
    uint8_t diff = 0;
    for (int i = 0; i < 16; i++) diff |= t[i] ^ tag[i];
    if (diff) { memset(m0, 0, total); return -1; }
    return 0;
}

void ascon_soft_hash256(uint8_t out[32], const uint8_t *in, size_t len) {
    u64 s[5] = {HASH_IV, 0, 0, 0, 0};
    perm(s, 12);
    for (; len >= 8; in += 8, len -= 8) { s[0] ^= ld(in, 8); perm(s, 12); }
    s[0] ^= ld(in, len) ^ (1ULL << (8 * len));
    perm(s, 12);
    for (int i = 0; i < 4; i++) {
        sto(out + 8 * i, s[0], 8);
        if (i < 3) perm(s, 12);
    }
}
