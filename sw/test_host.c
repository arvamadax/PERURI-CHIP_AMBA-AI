/* Tes di host (tanpa FPGA): software Ascon terhadap KAT resmi + penjaga nonce driver. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ascon_hps.h"
#include "ascon_soft.h"
#include "hexutil.h"
#include "kat_vectors.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("GAGAL %s:%d: %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

static uint64_t ctr_of(const uint8_t n[16]) {
    uint64_t c = 0;
    for (int i = 0; i < 8; i++) c |= (uint64_t)n[i] << (8 * i);
    return c;
}

static void test_kat(void) {
    for (size_t i = 0; i < sizeof AEAD_KATS / sizeof *AEAD_KATS; i++) {
        const aead_kat *v = &AEAD_KATS[i];
        uint8_t k[16], n[16], pt[64], ad[64], ct[64], tag[16], c2[64], t2[16], m2[64];
        hexbin(v->key, k); hexbin(v->nonce, n);
        size_t pl = hexbin(v->pt, pt), al = hexbin(v->ad, ad); hexbin(v->ct, ct); hexbin(v->tag, tag);
        ascon_soft_encrypt(c2, t2, pt, pl, ad, al, n, k);
        CHECK(!memcmp(c2, ct, pl) && !memcmp(t2, tag, 16));
        CHECK(ascon_soft_decrypt(m2, ct, pl, tag, ad, al, n, k) == 0 && !memcmp(m2, pt, pl));
        tag[3] ^= 0x10;
        memset(m2, 0xAA, sizeof m2);
        CHECK(ascon_soft_decrypt(m2, ct, pl, tag, ad, al, n, k) == -1);
        for (size_t j = 0; j < pl; j++) CHECK(m2[j] == 0);   /* plaintext dibuang */
    }
    for (size_t i = 0; i < sizeof HASH_KATS / sizeof *HASH_KATS; i++) {
        uint8_t msg[128], md[32], out[32];
        size_t l = hexbin(HASH_KATS[i].msg, msg); hexbin(HASH_KATS[i].md, md);
        ascon_soft_hash256(out, msg, l);
        CHECK(!memcmp(out, md, 32));
    }
}

static void test_nonce_guard(void) {
    char dir[] = "/tmp/ascon_nonceXXXXXX";
    CHECK(mkdtemp(dir) != NULL);
    uint8_t k1[16] = {1}, k2[16] = {2}, n[16];
    ascon_dev dev;
    ascon_session a, b, c;
    ascon_attach(&dev, NULL);
    CHECK(ascon_session_init(&a, &dev, k1, dir) == 0);
    for (uint64_t i = 0; i < 5; i++) { CHECK(ascon_next_nonce(&a, n) == 0); CHECK(ctr_of(n) == i); }
    CHECK(ascon_session_init(&b, &dev, k1, dir) == 0);        /* sesi baru, key sama: lanjut, bukan ulang */
    for (uint64_t i = 5; i < 10; i++) { CHECK(ascon_next_nonce(&b, n) == 0); CHECK(ctr_of(n) == i); }
    CHECK(ascon_session_init(&c, &dev, k2, dir) == 0);        /* key lain: penghitung sendiri */
    CHECK(ascon_next_nonce(&c, n) == 0 && ctr_of(n) == 0);
    char cmd[64];
    snprintf(cmd, sizeof cmd, "rm -r %s", dir);
    CHECK(system(cmd) == 0);
}

int main(void) {
    test_kat();
    test_nonce_guard();
    printf(fails ? "%d GAGAL\n" : "semua tes host lulus (%d AEAD KAT, %d hash KAT)\n",
           fails ? fails : (int)(sizeof AEAD_KATS / sizeof *AEAD_KATS), (int)(sizeof HASH_KATS / sizeof *HASH_KATS));
    return fails != 0;
}
