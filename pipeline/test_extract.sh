#!/bin/bash
# 用已有的 2D 数据验证提取管线

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

WORK=/root/work/extract_test
mkdir -p "$WORK"
sed 's/\r$//' /mnt/f/speed_up/pipeline/extract.py > "$WORK/extract.py"

echo "=============================================="
echo " 在 2D 数据上测试提取管线"
echo "=============================================="
cd "$WORK" || exit 1

python3 extract.py /root/work/phase0a/phase0a_out.e --out "$WORK/out2d" 2>&1 | tail -40

echo
echo "=============================================="
echo " 输出文件"
echo "=============================================="
ls -la "$WORK/out2d" 2>/dev/null

echo
echo "=== faces.csv 表头与样例 ==="
head -4 "$WORK/out2d/faces.csv" 2>/dev/null

echo
echo "=== events.csv 样例 ==="
head -8 "$WORK/out2d/events.csv" 2>/dev/null
