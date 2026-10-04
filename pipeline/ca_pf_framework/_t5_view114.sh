#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== 可用快照 ==="
for T in t5FIX t5BKMo t5ETAo; do
  echo "  $T: $(ls _exp/_bk_t5/dry_$T/snap_*.npz 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ')"
done
echo
ST=$(ls _exp/_bk_t5/dry_t5FIX/snap_*.npz 2>/dev/null | sed 's/.*snap_0*//;s/\.npz//' | sort -n | tail -1)
echo "=== 用 step=$ST 出图（场 2）==="
$PY _t5_split3d2.py t5FIX 2 "${ST:-0}" 2>&1 | tail -3
echo
echo "=== 四指标（步对齐）==="
$PY _t5_aralign.py "${ST:-0}" 2>&1 | tail -25
