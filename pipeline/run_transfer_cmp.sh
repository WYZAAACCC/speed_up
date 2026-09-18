#!/bin/bash
# 四种转移规则的闭环对比（完整输出）

source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
cd /root/work || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/replay_transfer.py > replay_transfer.py

for rule in none volume area flux; do
    echo "########## 规则: $rule ##########"
    python3 replay_transfer.py /root/work/ds_full /root/work/tb.pt \
        --rule "$rule" --t0 0 --t1 1400 2>&1 | tail -18
    echo
done
