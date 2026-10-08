"""Ascon-AEAD128 dan Ascon-Hash256 (NIST SP 800-232). Byte ke word: little-endian."""
from ascon_ref import permute

M64 = (1 << 64) - 1
AEAD_IV = 1 | 12 << 16 | 8 << 20 | 128 << 24 | 16 << 40   # variant, pa, pb, tag bits, rate
HASH_IV = 2 | 12 << 16 | 12 << 20 | 256 << 24 | 8 << 40


def _le(b: bytes) -> int:
    return int.from_bytes(b, "little")


def _mask(n: int) -> int:
    return (1 << (8 * n)) - 1


def _x(s):          # rate part (s0,s1) sebagai satu integer 128-bit
    return s[0] | s[1] << 64


def _set_x(s, x):
    s[0], s[1] = x & M64, x >> 64


def _init(key: bytes, nonce: bytes):
    k0, k1 = _le(key[:8]), _le(key[8:])
    s = permute([AEAD_IV, k0, k1, _le(nonce[:8]), _le(nonce[8:])], 12)
    s[3] ^= k0
    s[4] ^= k1
    return s, k0, k1


def _absorb_ad(s, ad: bytes):
    if not ad:
        return
    n = len(ad) // 16 * 16
    for i in range(0, n, 16):
        _set_x(s, _x(s) ^ _le(ad[i:i + 16]))
        s[:] = permute(s, 8)
    last = ad[n:]
    _set_x(s, _x(s) ^ _le(last) ^ 1 << (8 * len(last)))
    s[:] = permute(s, 8)


def _finish(s, k0, k1):
    s[2] ^= k0
    s[3] ^= k1
    s[:] = permute(s, 12)
    return ((s[3] ^ k0) | (s[4] ^ k1) << 64).to_bytes(16, "little")


def aead_encrypt(key: bytes, nonce: bytes, ad: bytes, pt: bytes):
    """Return (ciphertext, tag)."""
    s, k0, k1 = _init(key, nonce)
    _absorb_ad(s, ad)
    s[4] ^= 1 << 63                                  # domain separation
    ct = b""
    n = len(pt) // 16 * 16
    for i in range(0, n, 16):
        x = _x(s) ^ _le(pt[i:i + 16])
        _set_x(s, x)
        ct += x.to_bytes(16, "little")
        s[:] = permute(s, 8)
    last = pt[n:]
    x = _x(s) ^ _le(last)
    ct += (x & _mask(len(last))).to_bytes(len(last), "little")
    _set_x(s, x ^ 1 << (8 * len(last)))
    return ct, _finish(s, k0, k1)


def aead_decrypt(key: bytes, nonce: bytes, ad: bytes, ct: bytes, tag: bytes):
    """Return plaintext, atau None bila tag salah (plaintext dibuang)."""
    s, k0, k1 = _init(key, nonce)
    _absorb_ad(s, ad)
    s[4] ^= 1 << 63
    pt = b""
    n = len(ct) // 16 * 16
    for i in range(0, n, 16):
        c = _le(ct[i:i + 16])
        pt += (_x(s) ^ c).to_bytes(16, "little")
        _set_x(s, c)
        s[:] = permute(s, 8)
    last = ct[n:]
    m, c = _mask(len(last)), _le(last)
    pt += ((_x(s) ^ c) & m).to_bytes(len(last), "little")
    _set_x(s, ((_x(s) & ~m) | c) ^ 1 << (8 * len(last)))
    return pt if _finish(s, k0, k1) == tag else None


def hash256(msg: bytes) -> bytes:
    s = permute([HASH_IV, 0, 0, 0, 0], 12)
    n = len(msg) // 8 * 8
    for i in range(0, n, 8):
        s[0] ^= _le(msg[i:i + 8])
        s = permute(s, 12)
    last = msg[n:]
    s[0] ^= _le(last) | 1 << (8 * len(last))
    s = permute(s, 12)
    out = s[0].to_bytes(8, "little")
    for _ in range(3):
        s = permute(s, 12)
        out += s[0].to_bytes(8, "little")
    return out
