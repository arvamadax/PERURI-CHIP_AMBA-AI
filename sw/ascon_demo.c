/* Demo di DE10-Nano (jalankan sebagai root): KAT on-board lalu waktu HW vs software Cortex-A9.
 * Pemakaian: ./ascon_demo [offset_komponen_hex]   (default 0, sesuai alamat di Platform Designer) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "ascon_hps.h"
#include "ascon_soft.h"
#include "hexutil.h"
#include "kat_vectors.h"

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
    ascon_dev dev;
    uint32_t off = argc > 1 ? (uint32_t)strtoul(argv[1], NULL, 16) : 0;
    if (ascon_open(&dev, off)) { perror("ascon_open (perlu root dan /dev/mem)"); return 2; }

    int bad = 0;
    for (size_t i = 0; i < sizeof AEAD_KATS / sizeof *AEAD_KATS; i++) {
        const aead_kat *v = &AEAD_KATS[i];
        uint8_t k[16], n[16], pt[64], ad[64], ct[64], tag[16], c2[64], t2[16], m2[64];
        hexbin(v->key, k); hexbin(v->nonce, n);
        size_t pl = hexbin(v->pt, pt), al = hexbin(v->ad, ad); hexbin(v->ct, ct); hexbin(v->tag, tag);
        bad += ascon_encrypt_explicit_nonce(&dev, k, n, ad, al, pt, pl, c2, t2) != 0
            || memcmp(c2, ct, pl) || memcmp(t2, tag, 16);
        bad += ascon_decrypt(&dev, k, n, ad, al, ct, pl, tag, m2) != 0 || memcmp(m2, pt, pl);
        tag[0] ^= 1;
        bad += ascon_decrypt(&dev, k, n, ad, al, ct, pl, tag, m2) != -1;
    }
    for (size_t i = 0; i < sizeof HASH_KATS / sizeof *HASH_KATS; i++) {
        uint8_t msg[128], md[32], out[32];
        size_t l = hexbin(HASH_KATS[i].msg, msg); hexbin(HASH_KATS[i].md, md);
        bad += ascon_hash256(&dev, msg, l, out) != 0 || memcmp(out, md, 32);
    }
    printf("KAT on-board: %s (%d kegagalan)\n", bad ? "GAGAL" : "lulus", bad);

    static const size_t sizes[] = {16, 256, 4096};
    uint8_t key[16] = {0}, nonce[16] = {0}, tag[16];
    static uint8_t in[4096], out[4096];
    for (size_t s = 0; s < 3; s++) {
        int iters = (int)(1 << 20) / (int)sizes[s] / 16 + 1;
        double t0 = now();
        for (int i = 0; i < iters; i++) ascon_encrypt_explicit_nonce(&dev, key, nonce, NULL, 0, in, sizes[s], out, tag);
        double hw = now() - t0;
        t0 = now();
        for (int i = 0; i < iters; i++) ascon_soft_encrypt(out, tag, in, sizes[s], NULL, 0, nonce, key);
        double sw = now() - t0;
        printf("AEAD %5zu B: HW %.2f us/op, SW %.2f us/op, SW/HW = %.2fx\n", sizes[s],
               hw / iters * 1e6, sw / iters * 1e6, sw / hw);
    }
    ascon_close(&dev);
    return bad != 0;
}
