import os
import random

import cocotb
from cocotb.triggers import FallingEdge

from ascon_ref import pack, permute, unpack
from helpers import reset, start_clock

U = int(os.environ.get("UNROLL", "1"))


async def run_perm(dut, state, rounds):
    dut.d_in.value = pack(state)
    dut.p12.value = int(rounds == 12)
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    cycles = 1
    while int(dut.run.value):
        await FallingEdge(dut.clk)
        cycles += 1
    return unpack(int(dut.st.value)), cycles


@cocotb.test()
async def matches_model_and_cycle_count(dut):
    await start_clock(dut)
    dut.start.value = 0
    dut.p12.value = 0
    dut.d_in.value = 0
    await reset(dut)
    rng = random.Random(10 + U)
    for rounds in (8, 12, 12, 8):
        for _ in range(50):
            s0 = unpack(rng.getrandbits(320))
            s, cycles = await run_perm(dut, s0, rounds)
            assert s == permute(s0, rounds), f"p{rounds} UNROLL={U}"
            assert cycles == rounds // U, f"cycles={cycles}"


@cocotb.test()
async def reset_clears_run(dut):
    await start_clock(dut)
    dut.start.value = 1
    dut.d_in.value = 1
    dut.p12.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    await reset(dut)
    assert int(dut.run.value) == 0
