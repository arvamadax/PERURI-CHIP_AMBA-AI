/* Driver HPS untuk ascon_top lewat lightweight HPS-to-FPGA bridge (DE10-Nano).
 * Peta register: lihat rtl/ascon_csr_avalon.v. Alamat byte = base komponen + 4 * alamat word. */
#ifndef ASCON_HPS_H
#define ASCON_HPS_H
#include <stddef.h>
#include <stdint.h>

#define ASCON_LWBRIDGE_BASE 0xFF200000u
#define ASCON_LWBRIDGE_SPAN 0x00200000u

enum { ASCON_ENC = 0, ASCON_DEC = 1, ASCON_HASH = 2 };

typedef struct {
    volatile uint32_t *r;       /* register komponen (indeks word) */
    int fd;                     /* fd /dev/mem, -1 bila di-attach manual */
    void *map;
} ascon_dev;

/* Peta lightweight bridge dan arahkan ke komponen di offset byte `offset` (alamat Platform Designer). */
int ascon_open(ascon_dev *d, uint32_t offset);
void ascon_close(ascon_dev *d);
/* Pakai blok register yang sudah dipetakan pemanggil (uji dengan model/mock). */
void ascon_attach(ascon_dev *d, volatile uint32_t *regs);

int ascon_hash256(ascon_dev *d, const uint8_t *msg, size_t len, uint8_t digest[32]);

/* Enkripsi dengan nonce eksplisit. HANYA untuk KAT: memakai ulang (key, nonce) membocorkan plaintext. */
int ascon_encrypt_explicit_nonce(ascon_dev *d, const uint8_t key[16], const uint8_t nonce[16],
                                 const uint8_t *ad, size_t adlen, const uint8_t *pt, size_t ptlen,
                                 uint8_t *ct, uint8_t tag[16]);
/* 0 bila tag benar; -1 bila salah (plaintext dinolkan dan tidak boleh dipakai); <0 lain = error bus. */
int ascon_decrypt(ascon_dev *d, const uint8_t key[16], const uint8_t nonce[16],
                  const uint8_t *ad, size_t adlen, const uint8_t *ct, size_t ctlen,
                  const uint8_t tag[16], uint8_t *pt);

/* Sesi enkripsi: nonce dibuat driver dari penghitung yang disimpan permanen per key, tidak pernah dipakai ulang. */
typedef struct {
    ascon_dev *dev;
    uint8_t key[16];
    uint8_t salt[8];            /* acak per sesi, separuh atas nonce */
    char path[320];             /* berkas penghitung: <dir>/<id key>.ctr */
} ascon_session;

int ascon_session_init(ascon_session *s, ascon_dev *d, const uint8_t key[16], const char *state_dir);
/* Ambil nonce baru: tulis penghitung+1 ke disk (fsync) SEBELUM nonce dipakai. */
int ascon_next_nonce(ascon_session *s, uint8_t nonce[16]);
int ascon_seal(ascon_session *s, const uint8_t *ad, size_t adlen, const uint8_t *pt, size_t ptlen,
               uint8_t nonce_out[16], uint8_t *ct, uint8_t tag[16]);
#endif
