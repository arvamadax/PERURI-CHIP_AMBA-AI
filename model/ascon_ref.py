M64 = (1 << 64) - 1
RC = [0xf0, 0xe1, 0xd2, 0xc3, 0xb4, 0xa5, 0x96, 0x87, 0x78, 0x69, 0x5a, 0x4b]
ROT = [(19, 28), (61, 39), (1, 6), (10, 17), (7, 41)]


def ror(x, n):
    return ((x >> n) | (x << (64 - n))) & M64


def ascon_round(s, c):
    s = list(s)
    s[2] ^= c
    s[0] ^= s[4]
    s[4] ^= s[3]
    s[2] ^= s[1]
    t = [(~s[i]) & s[(i + 1) % 5] & M64 for i in range(5)]
    for i in range(5):
        s[i] ^= t[(i + 1) % 5]
    s[1] ^= s[0]
    s[0] ^= s[4]
    s[3] ^= s[2]
    s[2] = (~s[2]) & M64
    return [s[i] ^ ror(s[i], ROT[i][0]) ^ ror(s[i], ROT[i][1]) for i in range(5)]


def permute(s, rounds):
    for c in RC[12 - rounds:]:
        s = ascon_round(s, c)
    return s


def pack(s):
    return sum(w << (64 * (4 - i)) for i, w in enumerate(s))


def unpack(v):
    return [(v >> (64 * (4 - i))) & M64 for i in range(5)]


def ascon_hash_v12(msg: bytes) -> bytes:
    s = [0x00400c0000000100, 0, 0, 0, 0]
    s = permute(s, 12)
    padded = msg + b"\x80" + b"\x00" * (7 - len(msg) % 8)
    blocks = [int.from_bytes(padded[i:i + 8], "big") for i in range(0, len(padded), 8)]
    for b in blocks[:-1]:
        s[0] ^= b
        s = permute(s, 12)
    s[0] ^= blocks[-1]
    out = b""
    for i in range(4):
        s = permute(s, 12)
        out += s[0].to_bytes(8, "big")
    return out
