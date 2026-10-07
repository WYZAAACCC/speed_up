#!/bin/bash
# R50: §25 的"结清"是否依赖窗口？—— 用**累积对账**（良定义）逐窗口跑一遍
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for w in "0 200" "0 480" "200 480"; do
  echo "########## 窗口 $w"
  $PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 $w 2>&1 | sed -n '/累积对账/,$p' | head -9
  echo
done
