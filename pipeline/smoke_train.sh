#!/bin/bash
# 核验修改后的 train_rollout_batched.py 能跑通（少量 epoch）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
cd /root/work || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/train_rollout_batched.py > tr_new.py

echo "=== 语法检查 ==="
python3 -c "import ast,sys; ast.parse(open('tr_new.py').read()); print('OK')" || exit 1

echo
echo "=== 5 epoch 冒烟测试（ds_full）==="
python3 tr_new.py /root/work/ds_full --epochs 6 --W 16 --K 8 \
    --out /root/work/smoke.pt 2>&1 | tail -20
