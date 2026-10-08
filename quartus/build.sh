#!/bin/bash
# Build + laporan Quartus untuk UNROLL tertentu: ./build.sh [1|2|4]. Butuh Quartus Prime (quartus_sh di PATH).
set -e
cd "$(dirname "$0")"
U=${1:-1}
rm -rf "build_u$U" && mkdir "build_u$U"
cp ascon_top.qsf ascon_top.sdc "build_u$U/"
sed -i "s|\.\./rtl|../../rtl|; s|^set_parameter -name UNROLL .*|set_parameter -name UNROLL $U|" "build_u$U/ascon_top.qsf"
cd "build_u$U"
quartus_sh --flow compile ascon_top -c ascon_top
echo "== Quartus $(quartus_sh --version | grep -m1 Version) | UNROLL=$U =="
grep -E "Logic utilization|Total registers|Total block memory|Total DSP" output_files/ascon_top.fit.summary
quartus_sta ascon_top -c ascon_top --do_report_timing >/dev/null 2>&1 || true
grep -A3 -E "Fmax" output_files/ascon_top.sta.rpt | head -12
