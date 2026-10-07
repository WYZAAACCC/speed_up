#!/bin/bash
# R51: mb1s62 的累积对账（跨窗口），用于判"拉长还是肥化"
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== 全窗口"
$PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 2>&1 | grep -E '窗口|面族|tip |side |wide '
echo
echo "=== 分段（前半 / 后半），看趋势是否稳定"
for w in "0 300" "300 600"; do
  echo "--- 窗口 $w"
  $PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 $w 2>&1 | grep -E 'tip |side |wide '
done
