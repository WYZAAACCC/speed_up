#!/bin/bash
# _t5_blkthk.sh --- 块结构与板条厚度（验"每块能堆几根 = L_box / t_lath"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== NOW $(date '+%H:%M:%S') ==="
$PY _t5_blkcsv2.py t5FIX t5BKMo t5ETAo 2>&1 | head -40
echo
echo "=== 末个日志步的 nslab / 厚度 / 核数 ==="
for T in t5FIX t5BKMo t5ETAo; do
  echo "--- $T ---"
  grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$T.log 2>/dev/null | tail -1 | cut -c1-300
done
echo
echo "=== burst 记账与节拍 ==="
for T in t5FIX t5BKMo t5ETAo; do
  L=_w2_t5_short_$T.log
  echo "  $T 成功=$(grep -ac '块内第' $L) 被拒=$(grep -ac '被引擎拒' $L) 补投轮=$(grep -ac '◆ s292' $L) 末节拍=$(grep -aoE '[0-9.]+s/步' $L | tail -1)"
  grep -a '◆ s292' $L | tail -2 | sed 's/^/     /'
done
