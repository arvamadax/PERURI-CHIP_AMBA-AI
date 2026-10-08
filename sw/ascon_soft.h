/* Ascon-AEAD128 dan Ascon-Hash256 (NIST SP 800-232) dalam software, pembanding untuk akselerator. */
#ifndef ASCON_SOFT_H
#define ASCON_SOFT_H
#include <stddef.h>
#include <stdint.h>

void ascon_soft_encrypt(uint8_t *c, uint8_t tag[16], const uint8_t *m, size_t mlen,
                        const uint8_t *ad, size_t adlen, const uint8_t n[16], const uint8_t k[16]);
/* 0 bila tag benar; -1 bila salah (m dinolkan). */
int ascon_soft_decrypt(uint8_t *m, const uint8_t *c, size_t clen, const uint8_t tag[16],
                       const uint8_t *ad, size_t adlen, const uint8_t n[16], const uint8_t k[16]);
void ascon_soft_hash256(uint8_t out[32], const uint8_t *in, size_t len);
#endif
