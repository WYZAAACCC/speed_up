#!/bin/bash
# R52: Δx=62.5 的完整判决（跨窗口的累积对账）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for w in "" "0 500" "500 1000" "1000 1500"; do
  echo "##### 窗口 [${w:-全程}]"
  $PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 $w 2>&1 \
    | grep -E '^  (tip|side|wide) ' | tail -3
  echo
done
echo "##### 斜率概览（判"拉长还是肥化"）"
$PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 2>&1 | grep -E '面族|^  tip|^  side|^  wide' | head -4
