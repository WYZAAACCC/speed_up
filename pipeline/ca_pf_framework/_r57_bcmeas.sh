#!/bin/bash
# R57: 补齐带宽扫描 (bc20/bc40) 的 v2 口径读数
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for t in bc20 bc40; do
  echo "########## $t"
  timeout 600 $PY _r53_v2run.py "_exp/_bk_mb/dry_$t" 2>&1 | tail -4
  echo
done
