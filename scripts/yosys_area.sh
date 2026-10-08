#!/bin/bash
# Estimasi area Cyclone V dengan Yosys (synth_intel_alm). BUKAN hasil Quartus: ALUT dan FF, bukan ALM.
set -e
cd "$(dirname "$0")/.."
Y=${YOSYS:-yowasp-yosys}
echo "Tool: $($Y -V | head -1)"
echo "| Modul | UNROLL | ALUT | FF |"
echo "|---|---|---|---|"
row() {   # nama top, unroll, perintah chparam
    log=$(mktemp)
    $Y -p "read_verilog -sv rtl/*.v; $3 synth_intel_alm -family cyclonev -top $1; stat" >"$log" 2>&1
    alut=$(awk '/Printing statistics/ {s=0} /MISTRAL_ALUT[0-9]/ {s+=$1} END {print s+0}' "$log")
    ff=$(awk '/Printing statistics/ {s=0} /MISTRAL_FF/ {s+=$1} END {print s+0}' "$log")
    echo "| $1 | $2 | $alut | $ff |"
    rm -f "$log"
}
row ascon_round - ""
for u in 1 2 4; do row ascon_top $u "chparam -set UNROLL $u ascon_top;"; done
