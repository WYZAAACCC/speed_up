#!/bin/bash
# 复验 extract.py 的两处修复：面拓扑事件 + 守恒列
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/extract.py > extract.py

rm -rf ds_lpbf_test2
echo "=== stride=2, persist=2 ==="
python3 extract.py /root/work/s1/stage1.e --out /root/work/ds_lpbf_test2 \
    --solute-var bnds --stride 2 2>&1 | tail -18

echo
echo "=== events.csv ==="
cat /root/work/ds_lpbf_test2/events.csv

echo
echo "=== 事件类型统计 ==="
tail -n +2 /root/work/ds_lpbf_test2/events.csv | cut -d, -f2 | sort | uniq -c

echo
echo "=== conservation.csv（表头 + 前 3 + 后 3）==="
head -4 /root/work/ds_lpbf_test2/conservation.csv
echo "..."
tail -3 /root/work/ds_lpbf_test2/conservation.csv
