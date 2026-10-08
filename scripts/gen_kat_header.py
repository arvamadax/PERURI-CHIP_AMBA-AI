"""Buat sw/kat_vectors.h dari KAT resmi (model/kat). Jalankan: python scripts/gen_kat_header.py"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "model"))
from kat import aead_kats, hash_kats  # noqa: E402

AEAD_LENS, AD_LENS, HASH_LENS = (0, 1, 15, 16, 17, 32), (0, 1, 16, 32), (0, 1, 7, 8, 9, 16, 17, 64, 100)
h = lambda b: b.hex()
out = ["/* Dibuat oleh scripts/gen_kat_header.py dari model/kat (lihat docs/KAT_SOURCES.md). */",
       "typedef struct { const char *key, *nonce, *pt, *ad, *ct, *tag; } aead_kat;",
       "typedef struct { const char *msg, *md; } hash_kat;",
       "static const aead_kat AEAD_KATS[] = {"]
for _, k, n, pt, ad, ct, tag in aead_kats():
    if len(pt) in AEAD_LENS and len(ad) in AD_LENS:
        out.append(f'    {{"{h(k)}", "{h(n)}", "{h(pt)}", "{h(ad)}", "{h(ct)}", "{h(tag)}"}},')
out += ["};", "static const hash_kat HASH_KATS[] = {"]
for _, msg, md in hash_kats():
    if len(msg) in HASH_LENS:
        out.append(f'    {{"{h(msg)}", "{h(md)}"}},')
out.append("};")
(root / "sw" / "kat_vectors.h").write_text("\n".join(out) + "\n")
