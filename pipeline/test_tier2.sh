#!/bin/bash
# 第二档（2a/2b）验证 —— 不启动任何仿真
#   1. extract.py 语法检查
#   2. 物理单元测试（解析梯度 vs 数值微分；四重对称）
#   3. 在 C 版旧数据上跑 extract.py，验证缺少第二档变量时优雅退化
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

D=/root/work/s1t2
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
for f in extract.py test_tier2_physics.py; do
  sed 's/\r$//' "/mnt/f/speed_up/pipeline/$f" > "$f"
done

echo "=== 1. 语法检查 ==="
python3 -c "import ast,io; ast.parse(io.open('extract.py',encoding='utf-8').read()); print('OK')" || exit 1

echo
echo "=== 2. 物理单元测试 ==="
python3 test_tier2_physics.py || exit 1

echo
echo "=== 3. 在 C 版数据上跑（应优雅退化，不崩）==="
if [ -f /root/work/s1c_col/stage1c.e ]; then
  python3 extract.py /root/work/s1c_col/stage1c.e --out ./ds_c --stride 25 2>&1 | tail -14
  echo
  echo "grains.csv 表头:"; head -1 ./ds_c/grains.csv
  echo "grains.csv 首行:"; sed -n 2p ./ds_c/grains.csv
  echo
  echo "faces.csv 表头:"; head -1 ./ds_c/faces.csv
  echo "faces.csv 首行:"; sed -n 2p ./ds_c/faces.csv
else
  echo "（找不到 C 版数据，跳过）"
fi
