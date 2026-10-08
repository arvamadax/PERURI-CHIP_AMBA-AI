"""Driver tingkat blok untuk tb_ctrl: satu transaksi AEAD/hash + hitung siklus."""
from cocotb.triggers import FallingEdge

ENC, DEC, HASH = 0, 1, 2


def blocks_of(ad: bytes, data: bytes, rate: int):
    """Daftar (is_ad, chunk, last). Blok terakhir tiap jenis diberi last=1."""
    out = []
    for kind, buf in ((1, ad), (0, data)):
        chunks = [buf[i:i + rate] for i in range(0, len(buf), rate)] or ([b""] if kind == 0 else [])
        out += [(kind, c, i == len(chunks) - 1) for i, c in enumerate(chunks)]
    return out


class Core:
    def __init__(self, dut):
        self.dut = dut
        self.cycle = 0
        for n in ("rst", "start", "blk_valid", "blk_ad", "blk_last"):
            getattr(dut, n).value = 0
        for n in ("mode", "key", "nonce", "tag_in", "blk_data", "blk_len"):
            getattr(dut, n).value = 0

    async def tick(self):
        await FallingEdge(self.dut.clk)
        self.cycle += 1

    async def reset(self, n=3):
        self.dut.rst.value = 1
        for _ in range(n):
            await self.tick()
        self.dut.rst.value = 0
        await self.tick()

    async def run(self, mode, key, nonce, ad=b"", data=b"", tag=bytes(16), max_cycles=200000):
        d = self.dut
        d.key.value = int.from_bytes(key, "little")
        d.nonce.value = int.from_bytes(nonce, "little")
        d.tag_in.value = int.from_bytes(tag, "little")
        d.mode.value = mode
        d.start.value = 1
        t_start = self.cycle
        await self.tick()
        d.start.value = 0
        out, accepts, t_ready = b"", [], None
        for is_ad, chunk, last in blocks_of(ad, data, 8 if mode == HASH else 16):
            while not int(d.blk_ready.value):
                await self.tick()
                assert self.cycle - t_start < max_cycles, "timeout menunggu blk_ready"
            if t_ready is None:
                t_ready = self.cycle
            d.blk_ad.value, d.blk_last.value, d.blk_len.value = is_ad, last, len(chunk)
            d.blk_data.value = int.from_bytes(chunk, "little")
            d.blk_valid.value = 1
            await self.tick()
            d.blk_valid.value = 0
            accepts.append((is_ad, self.cycle))
            if not is_ad and mode != HASH:
                out += int(d.out_data.value).to_bytes(16, "little")[:len(chunk)]
        while not int(d.done.value):
            await self.tick()
            assert self.cycle - t_start < max_cycles, "timeout menunggu done"
        return {
            "out": out,
            "tag": int(d.tag_out.value).to_bytes(16, "little"),
            "tag_ok": int(d.tag_ok.value),
            "digest": int(d.digest.value).to_bytes(32, "little"),
            "cycles": self.cycle - t_start,
            "init": (t_ready or 0) - t_start,
            "accepts": accepts,
            "t_end": self.cycle,
        }
