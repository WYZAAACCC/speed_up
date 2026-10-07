#!/bin/bash
# R50: **§25 的结论是否依赖窗口？** —— 同一算例、不同窗口各算一次。
#   若 ③/实测 随窗口大幅漂移 ⇒ §25 的"结清"就是**过早**的。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for w in "0 200" "200 480" "0 480" "300 480"; do
  echo "########## 窗口 $w"
  $PY _r49_samearm.py _exp/_bk_mb/dry_mb1s62 $w 2>&1 \
    | grep -E '^  (tip|side|wide) |③/实|ΔG_max' | head -6
  echo
done
