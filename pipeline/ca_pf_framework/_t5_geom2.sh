#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== ★ 引擎打印的「播种厚 = 物理厚 + 咬入补偿」 ==="
for T in t5ETAo t5BKMo t5FIX; do
  echo "--- $T ---"
  grep -a '播种厚' _w2_t5_short_$T.log 2>/dev/null | head -3 | cut -c1-230
done
echo
echo "=== ★ 涉及的全部几何参数（引擎 argparse 默认值）==="
grep -n "plate-L\|plate-W\|plate-T\|plate-t-physical\|eng-r-nm\|eng-t-nm\|eng-elong\|nuc-compensate" _bk_exp.py \
  | grep add_argument | cut -c1-170
echo
echo "=== _t5_short.py 传了哪些、没传哪些 ==="
grep -n "plate-t-physical\|plate-T\|eng-r-nm\|eng-t-nm" _t5_short.py | cut -c1-170
echo
echo "=== 实测：每根板条的实际体积（Vt / nslab，取几档）==="
for T in t5ETAo t5BKMo; do
  echo "--- $T ---"
  grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$T.log 2>/dev/null | tail -4 \
    | sed -E 's/.*\[ *([0-9]+)\] Vt=([0-9.]+) µm³.*nslab=([0-9]+).*/    step \1: Vt=\2  nslab=\3  ⇒ 每片=\2\/\3/' | cut -c1-110
done
