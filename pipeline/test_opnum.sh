#!/bin/bash
# 测试 3D 下最少需要多少序参量
# 注意：着色错误是在**实际初始化**时报的，--check-input 不触发，
#       所以这里用 end_time=0 做最小初始化跑

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase1
cd "$RUN" || exit 1

for N in 20 16 14 12; do
    printf "op_num = %-3s : " "$N"
    sed "s/  op_num = 20/  op_num = $N/" phase1_3d.i > "test_op$N.i"
    OUT=$(timeout 400 "$BIN" -i "test_op$N.i" Executioner/end_time=0 Outputs/csv=false 2>&1)
    if echo "$OUT" | grep -q "Unable to find a valid grain to op coloring"; then
        echo "❌ 着色失败（序参量不够）"
    elif echo "$OUT" | grep -qiE "^\*\*\* ERROR|MOOSE ABORT"; then
        echo "⚠️  其他错误："
        echo "$OUT" | grep -iE "ERROR" | head -2 | sed 's/^/       /'
    elif echo "$OUT" | grep -q "Finished Executing"; then
        echo "✅ 可用"
    else
        echo "? 状态不明"
    fi
done
