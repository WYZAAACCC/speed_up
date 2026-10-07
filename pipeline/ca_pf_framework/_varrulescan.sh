#!/usr/bin/env bash
# Round 77：核变体选择规则 `ed` vs `random` 的对照（默认 `ed`，归档行为不变）
# 目的：`M6p` p25 在形核档退化到 23.9–25.4°（超 D16c 门槛 20°）——
#       检验"是不是 `argmax ed` 这条规则把取向选坏了"。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for r in ed random; do
  echo "=== var_rule=${r} ==="
  $PY -u T27_verify_nucleation.py --steps 30 --n0 8 --r-nuc-nm 300 --var-rule "$r" 2>&1 \
    | grep -e 新生 -e 落位诊断 -e 汇总
done
