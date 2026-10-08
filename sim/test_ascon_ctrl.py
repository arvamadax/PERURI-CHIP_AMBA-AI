import json
import os
import random
from pathlib import Path

import cocotb

from ascon_sp232 import aead_decrypt, aead_encrypt, hash256
from ctrl_driver import DEC, ENC, HASH, Core
from helpers import start_clock
from kat import aead_kats, hash_kats

U = int(os.environ.get("UNROLL", "1"))
FULL = os.environ.get("FULL") == "1"        # FULL=1: semua KAT; default: sampel
AEAD = list(aead_kats())
HASHV = list(hash_kats())
if not FULL:                                  # UNROLL besar lambat di Icarus -> sampel lebih jarang
    AEAD = AEAD[::3] if U == 1 else AEAD[::9]
    HASHV = HASHV[:40] + HASHV[40::25] if U == 1 else HASHV[:20] + HASHV[20::100]
OUT = Path(__file__).parent / "out"


async def setup(dut):
    await start_clock(dut)
    core = Core(dut)
    await core.reset()
    return core


async def check_aead(core, key, nonce, ad, pt, ct=None, tag=None):
    if ct is None:
        ct, tag = aead_encrypt(key, nonce, ad, pt)
    r = await core.run(ENC, key, nonce, ad, pt)
    assert (r["out"], r["tag"]) == (ct, tag), f"enc ad={len(ad)} pt={len(pt)}"
    r = await core.run(DEC, key, nonce, ad, ct, tag)
    assert r["tag_ok"] == 1 and r["out"] == pt, f"dec ad={len(ad)} pt={len(pt)}"


@cocotb.test()
async def aead_kat(dut):
    core = await setup(dut)
    for _, key, nonce, pt, ad, ct, tag in AEAD:
        await check_aead(core, key, nonce, ad, pt, ct, tag)


@cocotb.test()
async def hash_kat(dut):
    core = await setup(dut)
    for _, msg, md in HASHV:
        r = await core.run(HASH, bytes(16), bytes(16), data=msg)
        assert r["digest"] == md, f"hash len={len(msg)}"


@cocotb.test()
async def tag_or_ciphertext_changed_is_rejected(dut):
    core = await setup(dut)
    rng = random.Random(7)
    for _, key, nonce, pt, ad, ct, tag in AEAD[::9]:
        bit = rng.randrange(128)
        bad = (int.from_bytes(tag, "little") ^ (1 << bit)).to_bytes(16, "little")
        r = await core.run(DEC, key, nonce, ad, ct, bad)
        assert r["tag_ok"] == 0 and aead_decrypt(key, nonce, ad, ct, bad) is None
        if ct:
            bad_ct = bytes([ct[0] ^ 0x80]) + ct[1:]
            r = await core.run(DEC, key, nonce, ad, bad_ct, tag)
            assert r["tag_ok"] == 0


@cocotb.test()
async def length_corners(dut):
    core = await setup(dut)
    rng = random.Random(11)
    key, nonce = rng.randbytes(16), rng.randbytes(16)
    lens = (0, 1, 7, 8, 9, 15, 16, 17, 31, 32, 33, 47, 48)
    for la in lens:
        for lp in lens:
            await check_aead(core, key, nonce, rng.randbytes(la), rng.randbytes(lp))
    for ln in lens:
        r = await core.run(HASH, bytes(16), bytes(16), data=(m := rng.randbytes(ln)))
        assert r["digest"] == hash256(m), f"hash len={ln}"


@cocotb.test()
async def reset_mid_operation(dut):
    core = await setup(dut)
    rng = random.Random(13)
    key, nonce, ad, pt = rng.randbytes(16), rng.randbytes(16), rng.randbytes(40), rng.randbytes(70)
    for mode, cut in [(ENC, 3), (ENC, 15), (ENC, 40), (DEC, 90), (HASH, 20), (HASH, 100)]:
        task = cocotb.start_soon(core.run(mode, key, nonce, ad, pt if mode != HASH else pt))
        for _ in range(cut):
            await core.tick()
        task.cancel()
        dut.start.value = 0
        dut.blk_valid.value = 0
        await core.reset()
        assert int(dut.busy.value) == 0 and int(dut.done.value) == 0
        await check_aead(core, key, nonce, ad, pt)
        r = await core.run(HASH, bytes(16), bytes(16), data=pt)
        assert r["digest"] == hash256(pt)


@cocotb.test()
async def back_to_back_and_seeded_random(dut):
    core = await setup(dut)
    rng = random.Random(2026)
    for _ in range(60):
        key, nonce = rng.randbytes(16), rng.randbytes(16)
        ad, pt = rng.randbytes(rng.randrange(81)), rng.randbytes(rng.randrange(81))
        if rng.random() < 0.3:
            r = await core.run(HASH, key, nonce, data=pt)
            assert r["digest"] == hash256(pt)
        else:
            await check_aead(core, key, nonce, ad, pt)


@cocotb.test()
async def cycles_per_phase(dut):
    """Siklus inti (tanpa stall host): blok dikirim tanpa jeda. Hasil ke sim/out/cycles_u<U>.json."""
    core = await setup(dut)
    key, nonce = bytes(range(16)), bytes(range(16, 32))
    res = {"unroll": U}

    def steady(accepts, is_ad):
        t = [c for a, c in accepts if a == is_ad]
        return t[-1] - t[-2]

    r = await core.run(ENC, key, nonce, data=bytes(4096))
    res["aead_4096B"] = {"cycles": r["cycles"], "cycles_per_byte": r["cycles"] / 4096}
    res["init_cycles"] = r["init"]
    res["data_block_cycles"] = steady(r["accepts"], 0)
    res["final_cycles"] = r["t_end"] - r["accepts"][-1][1]
    for n in (16, 64, 1024):
        r = await core.run(ENC, key, nonce, data=bytes(n))
        res[f"aead_{n}B"] = {"cycles": r["cycles"], "cycles_per_byte": r["cycles"] / n}
    r = await core.run(ENC, key, nonce, ad=bytes(1024), data=bytes(16))
    res["ad_block_cycles"] = steady(r["accepts"], 1)
    r = await core.run(HASH, key, nonce, data=bytes(1024))
    res["hash_1024B"] = {"cycles": r["cycles"], "cycles_per_byte": r["cycles"] / 1024}
    res["hash_block_cycles"] = r["accepts"][-1][1] - r["accepts"][-2][1]
    OUT.mkdir(exist_ok=True)
    (OUT / f"cycles_u{U}.json").write_text(json.dumps(res, indent=1))
    assert res["aead_4096B"]["cycles_per_byte"] <= 1.0
