# Sumber KAT

Vektor uji disalin tanpa perubahan dari repo referensi resmi Ascon (lisensi CC0 1.0).

- Repo: https://github.com/ascon/ascon-c
- Commit: `446347f21b209f3921c65ece70027c366cbe1693` (branch `main`, 2026-01-28)

| File di repo ini | Path di ascon-c | Isi |
|---|---|---|
| `model/kat/LWC_AEAD_KAT_128_128.txt` | `crypto_aead/asconaead128/` | 1089 vektor Ascon-AEAD128 (PT 0..32 byte x AD 0..32 byte) |
| `model/kat/LWC_HASH_KAT_128_256.txt` | `crypto_hash/asconhash256/` | 1025 vektor Ascon-Hash256 (pesan 0..1024 byte) |

Urutan byte: word 64-bit dimuat little-endian (`LOADBYTES` di `word.h`), berbeda dari Ascon v1.2 (big-endian).
Konstanta IV dan padding diturunkan dari `constants.h` dan `word.h` pada commit di atas, dan dicek terhadap KAT.
