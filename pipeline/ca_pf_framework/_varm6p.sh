#!/usr/bin/env bash
# Round 80：闭合 Round 77 标为"未验证"的那条 ——
#   `M6p` p25 退化到 23.9–25.4°（超 D16c 门槛 20°）是不是 `var_rule='ed'` 造成的？
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for r in ed random; do
  echo "=== var_rule=${r} ==="
  $PY -u T24_verify_grouping.py --mode rve --L-um 3.2 --dx-nm 50 --n0 0 \
      --f-target 0.05 --norm-smooth 2 --nuc --nuc-init 24 --nuc-every 5 \
      --nuc-fresh 2 --nuc-stack 2 --nuc-r-nm 300 --var-rule "$r" 2>&1 \
    | grep -e 采样 -e M6p -e '几何长' -e 几何厚度
done
