#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== 厚度量具的打印处 ==="
grep -n '厚度(在位的场)' _bk_exp.py | cut -c1-170
echo
echo "=== 该量的计算（前后 40 行内的关键行）==="
L=$(grep -n '厚度(在位的场)' _bk_exp.py | head -1 | cut -d: -f1)
if [ -n "$L" ]; then
  S=$((L-46)); E=$((L+4))
  sed -n "${S},${E}p" _bk_exp.py | grep -nE '_th|thick|厚度|np\.sum|argmax|median|cells|vol' | cut -c1-165
fi
echo
echo "=== 三臂当前状态 ==="
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  echo "  $T max=$(ls $D/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1) 事件=$(grep -ac '块内第' _w2_t5_short_$T.log 2>/dev/null) fresh拒=$(grep -ac 'fresh` 被拒' _w2_t5_short_$T.log 2>/dev/null) 补投=$(grep -ac '◆ s292' _w2_t5_short_$T.log 2>/dev/null)"
done
