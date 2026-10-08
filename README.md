# Merah Putih Crypto Core (Amba Chip)

IP core Verilog untuk Ascon-AEAD128 dan Ascon-Hash256 (NIST SP 800-232), target DE10-Nano (Cyclone V SoC).
PERURI Chip Hackathon 2026, tantangan 02 Hardware Cryptography Accelerator.
Antarmuka akhir: Avalon-MM slave 32-bit lewat lightweight bridge HPS.

## Menjalankan tes

```bash
python3 -m venv ~/venv && source ~/venv/bin/activate
pip install -r requirements.txt
make          # cocotb + Icarus Verilog
make clean
```

Struktur: `rtl/` (Verilog), `sim/` (cocotb + Makefile), `model/` (model Python), `docs/`.

## Status modul

| Modul | Status |
|---|---|
| `ascon_round` | Selesai, lulus tes |
| `model/ascon_ref.py` (permutasi p8/p12, Hash v1.2) | Selesai; Hash v1.2 bukan referensi Hash256 |
| Model SP 800-232 (AEAD128, Hash256) | Belum |
| `ascon_perm`, `tag_compare`, `ascon_ctrl` | Belum |
| `ascon_csr_avalon`, `ascon_top` | Belum |
| Driver C HPS | Belum |
| Sintesis Quartus | Belum |

## Hasil tes terbaru

`make`: 5 dari 5 tes lulus (cocotb 2.1.0, Icarus Verilog 12.0, Python 3.14.4, 2026-10-08).
Tes membandingkan `ascon_round` dengan `model/ascon_ref.py`: semua round constant, 2000 state acak, state sudut, p12 dari IV hash, rantai p8/p12 acak.

## Batasan yang diketahui

- `ascon_ref.py` diverifikasi hanya lewat kecocokan dengan RTL dan satu vektor hash pesan kosong v1.2; belum ada KAT resmi SP 800-232.
- IV, rate, dan padding SP 800-232 berbeda dari Ascon v1.2. `ascon_hash_v12` tidak boleh dipakai sebagai referensi Hash256.
- Belum ada angka area atau Fmax yang terverifikasi. Yosys belum terpasang di server (`yosys: command not found`, 2026-10-08), jadi estimasi area sebelumnya belum direproduksi. Quartus belum terpasang.
