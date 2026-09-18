#!/bin/bash
# 测试迁移率 M 对时间步的影响
#
# 思路：c 的弛豫速率 ~ M·k。dt=1.6 正是被这个速率卡住的。
#       把 M 调小 → 弛豫变慢 → dt 可放大。
#       只要 c 弛豫仍远快于晶粒长大（后者上千时间单位），偏析仍是准静态的。

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/mtest
SRC=/mnt/f/speed_up/pipeline

mkdir -p "$RUN"
cd "$RUN" || exit 1

# 杀掉旧算例（用 [.] 技巧避免 pkill 匹配自身）
pkill -f '[p]hase2_2d_seg' 2>/dev/null
sleep 3

cp "$SRC/gen_seeds.py" gen_seeds.py 2>/dev/null
python3 gen_seeds.py seeds.txt 1000 > /dev/null 2>&1

for M in 1.0 0.3 0.1 0.03; do
    echo "=============================================="
    echo " M = $M"
    echo "=============================================="
    # 用等尺寸的随机结构（快），只测 dt 能达到多少
    sed -e 's/\r$//' "$SRC/phase2_2d_seg.i" \
        | sed -e "s/^    prop_values = '1.0 1.0'/    prop_values = '$M 1.0'/" \
        | sed -e 's/    file_name = seeds_poly.txt/    grain_num = 60\n    rand_seed = 10/' \
        > "m$M.i"

    rm -f "o$M.e" "o$M.csv"
    timeout 900 mpirun -np 8 "$BIN" -i "m$M.i" \
        Executioner/end_time=60 \
        Outputs/file_base="o$M" \
        Outputs/csv=false 2>&1 | grep -E "Time Step|dt =|Finished" | tail -6
    echo
done
