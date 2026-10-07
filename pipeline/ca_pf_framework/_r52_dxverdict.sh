#!/bin/bash
# R52: `dry_mb1s62`（Δx=62.5 nm）跑满 1500 步后，**用累积口径**判 R-1/R-2/R-3。
#   这是 §33 的关键复核：Δx=125 给"肥化"（side>tip），Δx=62.5 前 600 步给"拉长"（tip>side）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "########## 全程 0–1500（累积对账）"
$PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 2>&1 | grep -E '窗口|面族|d\(sep|tip |side |wide |Δsep|累积'
echo
echo "########## 分段稳定性（每 500 步）"
for w in "0 500" "500 1000" "1000 1500"; do
  echo "--- 窗口 $w"
  $PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 $w 2>&1 | grep -E '^  (tip|side|wide) '
done
