#!/bin/bash
# R56: 对已完成的带宽档跑 v2 口径的 `v_a/v_w`
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for t in bc5 bc10; do
  echo "########## band_cells=${t#bc}"
  timeout 600 $PY _r53_v2run.py "_exp/_bk_mb/dry_$t" 2>&1 | tail -6
  echo
done
