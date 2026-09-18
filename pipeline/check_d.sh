#!/bin/bash
# 检查 stage1_meltpool_d.i（2a+2b 版）：只做输入检查，不求解。
# --check-input 会真正构造所有对象，包括对超长 parsed 表达式做符号求导，
# 因此能提前暴露解析错误与表达式规模问题。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

D=/root/work/s1d_check
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

sed 's/\r$//' /mnt/f/speed_up/pipeline/stage1_meltpool_d.i > in.i
# 算例依赖的种子文件
for f in columnar_seeds.csv; do
  cp "/mnt/f/speed_up/pipeline/$f" . 2>/dev/null || echo "警告：缺少 $f"
done

echo "=== MOOSE 可执行文件 ==="
MOOSE=$(ls /root/moose/modules/phase_field/phase_field-opt 2>/dev/null)
echo "$MOOSE"
[ -x "$MOOSE" ] || { echo "找不到 phase_field-opt"; exit 1; }

echo
echo "=== 输入检查（含符号求导）==="
time "$MOOSE" -i in.i --check-input 2>&1 | tail -40
