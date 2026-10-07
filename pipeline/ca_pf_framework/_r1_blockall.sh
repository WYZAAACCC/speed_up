#!/bin/bash
# _r1_blockall.sh --- 对实验 4/5/6 三个多核臂跑块判定（`--block`），只摘关键行
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
for d in "$@"; do
  echo "########## $d ##########"
  $PY -u _r1_analyze.py --block --dx-nm 125 --every 5 "_exp/$d" 2>&1 \
    | grep -E 'Q-[a-d]|合并|未合并|nsig|守卫|⇒|nc=' | head -18
  echo
done
