from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge


async def start_clock(dut):
    import cocotb
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


async def reset(dut, cycles=3):
    """Reset sinkron aktif-tinggi; semua input didrive pada falling edge."""
    dut.rst.value = 1
    for _ in range(cycles):
        await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)
