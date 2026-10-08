"""Cetak tabel cycles/byte dari sim/out/cycles_u*.json (hasil `make sim`)."""
import json
from pathlib import Path

rows = [json.loads(p.read_text()) for p in sorted((Path(__file__).parent / "out").glob("cycles_u*.json"))]
print("| UNROLL | init | blok AD | blok data | final | blok hash | AEAD 4096 B (cyc/B) | AEAD 16 B (cyc/B) | Hash 1024 B (cyc/B) |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r['unroll']} | {r['init_cycles']} | {r['ad_block_cycles']} | {r['data_block_cycles']} | "
          f"{r['final_cycles']} | {r['hash_block_cycles']} | {r['aead_4096B']['cycles_per_byte']:.3f} | "
          f"{r['aead_16B']['cycles_per_byte']:.3f} | {r['hash_1024B']['cycles_per_byte']:.3f} |")
