#!/usr/bin/env bash
# Round 68：扫核半径对 `stack` 落位成功率的影响（Round 67 结论 = "空间不足"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for r in 400 200 120; do
  echo "=== R_nuc=${r} nm ==="
  $PY -u T27_verify_nucleation.py --steps 30 --n0 8 --r-nuc-nm "$r" 2>&1 \
    | grep -e 新生 -e 落位诊断
done
