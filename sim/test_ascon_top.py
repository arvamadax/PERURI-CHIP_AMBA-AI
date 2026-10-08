"""Tes tingkat bus: urutan akses Avalon sama dengan yang dipakai driver C di HPS."""
import os
import random

import cocotb
from cocotb.triggers import FallingEdge

from ascon_sp232 import aead_encrypt, hash256
from ctrl_driver import DEC, ENC, HASH, blocks_of
from helpers import reset, start_clock
from kat import aead_kats, hash_kats

U = int(os.environ.get("UNROLL", "1"))
STEP = 40 if U == 1 else 120
AEAD = list(aead_kats())[::STEP]
HASHV = list(hash_kats())[:6] + list(hash_kats())[6::300]

CTRL, BLK, STATUS, KEY, NONCE, DIN, TAGIN, DOUT, TAGOUT, DIGEST = 0, 1, 2, 4, 8, 12, 16, 20, 24, 28
BUSY, READY, DONE, TAG_OK, OUT_VALID = 1, 2, 4, 8, 16


class Avalon:
    def __init__(self, dut):
        self.dut = dut
        dut.write.value = 0
        dut.read.value = 0
        dut.address.value = 0
        dut.writedata.value = 0

    async def write(self, addr, val):
        d = self.dut
        d.address.value, d.writedata.value, d.write.value = addr, val, 1
        await FallingEdge(d.clk)
        d.write.value = 0

    async def read(self, addr):
        d = self.dut
        d.address.value, d.read.value = addr, 1
        await FallingEdge(d.clk)
        d.read.value = 0
        return int(d.readdata.value)

    async def write_big(self, base, data: bytes):
        for i in range(0, len(data), 4):
            await self.write(base + i // 4, int.from_bytes(data[i:i + 4], "little"))

    async def read_big(self, base, nbytes):
        return b"".join([(await self.read(base + i)).to_bytes(4, "little") for i in range(nbytes // 4)])

    async def wait_status(self, mask, limit=5000):
        for _ in range(limit):
            s = await self.read(STATUS)
            if s & mask:
                return s
        raise AssertionError("timeout polling STATUS")


async def setup(dut):
    await start_clock(dut)
    dut.rst.value = 0
    av = Avalon(dut)
    await reset(dut)
    return av


async def run(av, mode, key, nonce, ad=b"", data=b"", tag=bytes(16), irq_en=0):
    await av.write_big(KEY, key)
    await av.write_big(NONCE, nonce)
    await av.write_big(TAGIN, tag)
    await av.write(CTRL, 1 | mode << 1 | irq_en << 3)
    out = b""
    for is_ad, chunk, last in blocks_of(ad, data, 8 if mode == HASH else 16):
        await av.wait_status(READY)
        await av.write_big(DIN, chunk.ljust(16, b"\0"))
        await av.write(BLK, len(chunk) | last << 8 | is_ad << 9)
        if not is_ad and mode != HASH:
            await av.wait_status(READY | DONE)
            out += (await av.read_big(DOUT, 16))[:len(chunk)]
    status = await av.wait_status(DONE)
    return {"out": out, "status": status, "tag": await av.read_big(TAGOUT, 16),
            "digest": await av.read_big(DIGEST, 32)}


@cocotb.test()
async def aead_and_hash_over_avalon(dut):
    av = await setup(dut)
    for _, key, nonce, pt, ad, ct, tag in AEAD:
        r = await run(av, ENC, key, nonce, ad, pt)
        assert (r["out"], r["tag"]) == (ct, tag)
        r = await run(av, DEC, key, nonce, ad, ct, tag)
        assert r["out"] == pt and r["status"] & TAG_OK
    for _, msg, md in HASHV:
        r = await run(av, HASH, bytes(16), bytes(16), data=msg)
        assert r["digest"] == md


@cocotb.test()
async def flipped_tag_bit_clears_tag_ok(dut):
    av = await setup(dut)
    _, key, nonce, pt, ad, ct, tag = AEAD[len(AEAD) // 2]
    for bit in (0, 63, 64, 127):
        bad = (int.from_bytes(tag, "little") ^ (1 << bit)).to_bytes(16, "little")
        r = await run(av, DEC, key, nonce, ad, ct, bad)
        assert not r["status"] & TAG_OK, f"bit {bit}"   # driver membuang plaintext bila TAG_OK=0
    r = await run(av, DEC, key, nonce, ad, ct, tag)
    assert r["status"] & TAG_OK


@cocotb.test()
async def status_has_no_race_after_start(dut):
    av = await setup(dut)
    rng = random.Random(3)
    key, nonce = rng.randbytes(16), rng.randbytes(16)
    await run(av, ENC, key, nonce, b"", b"x")           # DONE lama masih 1
    await av.write_big(KEY, key)
    await av.write(CTRL, 1)                              # START
    s = await av.read(STATUS)                            # dibaca persis setelah START
    assert s & BUSY and not s & DONE, f"status={s:#x}"


@cocotb.test()
async def irq_follows_done(dut):
    av = await setup(dut)
    key, nonce = bytes(16), bytes(16)
    await av.write(CTRL, 1 | 1 << 3)                     # enc, IRQ_EN
    await av.wait_status(READY)
    await av.write_big(DIN, bytes(16))
    await av.write(BLK, 0 | 1 << 8)
    assert int(dut.irq.value) == 0
    await av.wait_status(DONE)
    assert int(dut.irq.value) == 1
    await av.write(CTRL, 1)                              # start baru, IRQ_EN=0
    assert int(dut.irq.value) == 0


@cocotb.test()
async def reset_mid_process_and_back_to_back(dut):
    av = await setup(dut)
    rng = random.Random(5)
    key, nonce, ad, pt = rng.randbytes(16), rng.randbytes(16), rng.randbytes(33), rng.randbytes(50)
    await av.write_big(KEY, key)
    await av.write_big(NONCE, nonce)
    await av.write(CTRL, 1)
    await av.wait_status(READY)
    await reset(dut)
    s = await av.read(STATUS)
    assert not s & (BUSY | DONE)
    for _ in range(3):                                   # berurutan tanpa jeda
        r = await run(av, ENC, key, nonce, ad, pt)
        assert (r["out"], r["tag"]) == aead_encrypt(key, nonce, ad, pt)
        r = await run(av, HASH, key, nonce, data=pt)
        assert r["digest"] == hash256(pt)
    assert await av.read(KEY) == 0                       # key write-only
