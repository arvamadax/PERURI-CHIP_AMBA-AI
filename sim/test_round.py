import random

import cocotb
from cocotb.triggers import Timer

from ascon_ref import RC, ascon_round, pack, unpack


async def check(dut, state, rc):
    dut.s_in.value = pack(state)
    dut.rc.value = rc
    await Timer(1, "ns")
    assert int(dut.s_out.value) == pack(ascon_round(state, rc))


@cocotb.test()
async def all_round_constants(dut):
    rng = random.Random(1)
    for rc in RC:
        await check(dut, unpack(rng.getrandbits(320)), rc)


@cocotb.test()
async def random_states(dut):
    rng = random.Random(2)
    for _ in range(2000):
        await check(dut, unpack(rng.getrandbits(320)), rng.choice(RC))


@cocotb.test()
async def corner_states(dut):
    for v in (0, (1 << 320) - 1, 1, 1 << 319):
        for rc in (RC[0], RC[-1]):
            await check(dut, unpack(v), rc)


@cocotb.test()
async def twelve_rounds_hash_iv(dut):
    state = [0x00400c0000000100, 0, 0, 0, 0]
    expected = list(state)
    for rc in RC:
        await check(dut, state, rc)
        state = ascon_round(state, rc)
    from ascon_ref import permute
    assert state == permute(expected, 12)


@cocotb.test()
async def chained_8_and_12_rounds_random(dut):
    from ascon_ref import permute
    rng = random.Random(3)
    for rounds in (8, 12):
        for _ in range(200):
            s0 = unpack(rng.getrandbits(320))
            s = s0
            for c in RC[12 - rounds:]:
                dut.s_in.value = pack(s)
                dut.rc.value = c
                await Timer(1, "ns")
                s = unpack(int(dut.s_out.value))
            assert s == permute(s0, rounds), f"p{rounds} mismatch"
