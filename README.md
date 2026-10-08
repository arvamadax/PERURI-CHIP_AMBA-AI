# Merah Putih Crypto Core (Amba Chip)

IP core Verilog untuk Ascon-AEAD128 dan Ascon-Hash256 (NIST SP 800-232), target DE10-Nano (Cyclone V SoC).
PERURI Chip Hackathon 2026, tantangan 02 Hardware Cryptography Accelerator.
Satu datapath 320-bit; parameter `UNROLL` (1, 2, 4) menentukan jumlah ronde permutasi per siklus.
Antarmuka: Avalon-MM slave 32-bit lewat lightweight HPS-to-FPGA bridge.

## Menjalankan

```bash
python3 -m venv ~/venv && source ~/venv/bin/activate
pip install -r requirements.txt
make              # model (pytest) + RTL (cocotb, Icarus Verilog)
make cycles       # tabel siklus per fase dari hasil make
make area         # estimasi area Yosys (butuh requirements-area.txt)
make -C sw host-test   # software Ascon + penjaga nonce driver
```

`FULL=1 make -C sim TOP=tb_ctrl TESTMOD=test_ascon_ctrl UNROLL=1` menjalankan seluruh KAT di RTL (default: sampel).

Struktur: `rtl/` Verilog, `sim/` tes cocotb, `model/` model Python + KAT, `sw/` driver C HPS, `quartus/` proyek Quartus, `docs/`.

## Status modul

| Modul | Fungsi | Status |
|---|---|---|
| `ascon_round` | satu ronde permutasi (kombinasional) | lulus tes |
| `ascon_perm` | state 320-bit, p8/p12, `UNROLL` 1/2/4 | lulus tes |
| `tag_compare` | bandingkan tag 128-bit | lulus tes |
| `ascon_ctrl` | FSM AEAD128 enc/dec + Hash256, padding blok terakhir | lulus tes |
| `ascon_csr_avalon`, `ascon_top` | register Avalon, irq, top | lulus tes |
| `model/ascon_sp232.py` | model referensi SP 800-232 | lulus 1089 KAT AEAD + 1025 KAT hash |
| `sw/` driver C | akses register, penjaga nonce, KAT + timing on-board | software dan penjaga nonce teruji di host; **belum dijalankan di board** |
| `quartus/` | proyek + SDC 100 MHz + skrip build | disiapkan, **belum dijalankan** |

## Hasil tes terbaru (2026-10-08)

Tool: Icarus Verilog 12.0, cocotb 2.1.0, pytest 9.1.1, Python 3.14.4.

- Model: 2117 tes pytest lulus (1089 KAT AEAD, 1025 KAT hash, tamper tag, vektor yang diubah satu byte gagal).
- RTL: `make sim` menjalankan `ascon_round` (5 tes), `tag_compare` (1), `ascon_perm` (2 tes x 3 UNROLL), `ascon_ctrl` lewat `tb_ctrl` (7 x 3), `ascon_top` lewat bus Avalon (5 x 3).
- KAT resmi di RTL (`ascon_ctrl`, UNROLL=1, `FULL=1`): seluruh 1089 vektor AEAD (enkripsi dan dekripsi) dan 1025 vektor hash cocok. Regresi default memakai sampel (AEAD tiap ke-3, UNROLL 2 dan 4 tiap ke-9), karena Icarus lambat untuk UNROLL besar.
- Skenario: AD kosong, plaintext kosong, 1 byte, panjang bukan kelipatan 16, tag diubah 1 bit (`tag_ok=0`), ciphertext diubah, reset di tengah proses (6 titik potong), transaksi berurutan tanpa jeda, acak dengan seed tetap.
- KAT bersumber dari `ascon/ascon-c` commit `446347f` (`docs/KAT_SOURCES.md`).

## Siklus inti (simulasi, `make cycles`)

Dihitung dari `start` sampai `done`, blok dikirim tanpa jeda (tanpa stall dari bus/host).

| UNROLL | init | blok AD | blok data | final | blok hash | AEAD 4096 B (cyc/B) | AEAD 16 B (cyc/B) | Hash 1024 B (cyc/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | 13 | 9 | 9 | 21 | 13 | 0.569 | 2.188 | 1.686 |
| 2 | 7 | 5 | 5 | 11 | 7 | 0.316 | 1.188 | 0.906 |
| 4 | 4 | 3 | 3 | 6 | 4 | 0.189 | 0.688 | 0.517 |

Target proposal `cycles/byte AEAD <= 1.0` (UNROLL=1): tercapai di simulasi untuk pesan panjang (0,569 untuk 4096 B). Pesan pendek lebih mahal karena init dan final (16 B: 2,188).
Throughput inti pada 100 MHz, UNROLL=1: 128 bit per 9 siklus = 1,42 Gbps (asimptotik). Ini **hanya berlaku bila Fmax >= 100 MHz, yang belum terukur**, dan belum memasukkan waktu akses bus.

## Estimasi area (Yosys, bukan Quartus)

`make area`, Yosys 0.60 (`yowasp-yosys 0.60.0.0.post1055`), `synth_intel_alm -family cyclonev`. ALUT dan FF, bukan ALM.

| Modul | UNROLL | ALUT | FF |
|---|---|---|---|
| ascon_round | - | 638 | 0 |
| ascon_top | 1 | 3050 | 1408 |
| ascon_top | 2 | 3851 | 1408 |
| ascon_top | 4 | 5727 | 1408 |

Target proposal `<= 2000 ALM (UNROLL=1)`: **belum bisa dinilai**. ALM final hanya valid dari Quartus; ALUT 3050 untuk UNROLL=1 menunjukkan risiko melewati target (ALM lebih sedikit dari ALUT karena pengepakan, tapi seberapa banyak hanya Quartus yang tahu). Fmax: belum ada angka.

## Batasan dan risiko yang diketahui

- **Fmax dan ALM belum terukur.** Quartus belum dijalankan; `quartus/build.sh` siap dijalankan di PC lain atau saat bootcamp.
- **Bus adalah bottleneck.** Satu blok 16 B butuh 4 tulis DIN + 1 tulis BLK + polling lewat lightweight bridge (PIO). Throughput nyata di HPS jauh di bawah throughput inti; belum diukur di board. Perbaikan yang mungkin: FIFO/DMA.
- **Plaintext dekripsi dikeluarkan per blok sebelum tag diverifikasi** (inheren pada mode streaming). Hardware hanya melaporkan `TAG_OK`; driver (`ascon_decrypt`) membuang plaintext bila `TAG_OK=0`. Pemakai register langsung wajib melakukan hal yang sama.
- Aturan host: blok data/pesan terakhir wajib dikirim (boleh panjang 0) dengan `LAST=1`; blok AD opsional, blok AD terakhir diberi `LAST=1`. Blok hash maksimal 8 byte.
- Driver mencegah pemakaian ulang nonce dengan key yang sama lewat penghitung permanen per key (`ascon_seal`). `ascon_encrypt_explicit_nonce` hanya untuk KAT. Penjaga ini tidak melindungi bila berkas penghitung dihapus atau dikembalikan dari backup.
- Offset komponen di Platform Designer harus diisi pemakai (argumen `ascon_demo`); belum ada `_hw.tcl`.
- `ascon_ref.py::ascon_hash_v12` adalah Ascon-Hash v1.2 dan bukan referensi Hash256; referensi yang benar ada di `model/ascon_sp232.py`.
