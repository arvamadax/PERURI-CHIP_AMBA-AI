import random

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def equal_and_every_single_bit_flip(dut):
    rng = random.Random(5)
    for _ in range(20):
        t = rng.getrandbits(128)
        dut.a.value = t
        dut.b.value = t
        await Timer(1, "ns")
        assert int(dut.tag_ok.value) == 1
        for bit in range(128):
            dut.b.value = t ^ (1 << bit)
            await Timer(1, "ns")
            assert int(dut.tag_ok.value) == 0, f"bit {bit}"
