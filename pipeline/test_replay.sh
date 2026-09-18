#!/bin/bash
# 核验修过的 replay_transfer.py
source /root/miniconda3/etc/profile.d/conda.sh
conda activate ml
cd /root/work || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/replay_transfer.py > replay_transfer.py

echo "=== 语法检查 ==="
python3 -c "import ast; ast.parse(open('replay_transfer.py').read()); print('OK')" || exit 1

echo
echo "=== 跑 volume 规则（用现役 tb.pt）==="
python3 replay_transfer.py /root/work/ds_full /root/work/tb.pt \
    --rule volume --t0 0 --t1 1400 2>&1 | tail -26
