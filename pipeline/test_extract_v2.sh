#!/bin/bash
# 验证补了第一档（温度/方向/速度/时长）之后的 extract.py
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
cd /root/work || exit 1
sed 's/\r$//' /mnt/f/speed_up/pipeline/extract.py > extract.py

echo "=== 语法检查 ==="
python3 -c "import ast,io; ast.parse(io.open('extract.py',encoding='utf-8').read()); print('OK')" || exit 1

echo
echo "=== 在柱状晶 smoke test 的输出上跑（stride=10 控制耗时）==="
rm -rf ds_col_test
python3 extract.py /root/work/s1c_col/stage1c.e --out /root/work/ds_col_test \
    --stride 10 2>&1 | tail -22

echo
echo "=== grains.csv 表头 + 1 行 ==="
head -2 /root/work/ds_col_test/grains.csv
echo
echo "=== faces.csv 表头 + 1 行 ==="
head -2 /root/work/ds_col_test/faces.csv
