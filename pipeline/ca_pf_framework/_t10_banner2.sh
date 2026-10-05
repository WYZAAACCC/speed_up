#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10PRT2_b3_1005_1213.log
[ -f "$L" ] || L=_w2_t5_short_t10B9.log
echo "=== $L ==="
echo "总行数 = $(wc -l < "$L")"
echo
echo "── ① 剔掉逐对表行后的 banner（前 120 行）──"
grep -avE '板条[0-9]+\(V[0-9]+\) *- *板条' "$L" 2>/dev/null \
  | head -120 | tr -d '\r' | cut -c1-165 | sed 's/^/  /'
