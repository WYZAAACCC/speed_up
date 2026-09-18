#!/bin/bash
# 重新分配算力：从 4 算例×4 进程 改为 2 算例×8 进程
#
# 实测依据：
#   单个算例 8 进程 → 238 时间单位/小时
#   4 个算例 4 进程 → 每个 71，合计 284
# MPI 扩展非线性，进程减半速度掉到 1/3。
# 换成 2×8 后总吞吐应约 476，是 4×4 的 1.7 倍。

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

echo "=== 1. 先抢救已跑出的部分数据 ==="
for rid in 1 2 3 4; do
    d="/root/work/multi/run$rid"
    if [ -f "$d/out.e" ]; then
        n=$(wc -l < "$d/out.csv" 2>/dev/null || echo 0)
        echo "  run$rid: $((n-1)) 步，提取中..."
        cd /root/work
        python3 extract.py "$d/out.e" --out "/root/work/partial$rid" --stride 2 \
            > /dev/null 2>&1 && echo "    → partial$rid 完成" || echo "    → 提取失败"
    fi
done

echo
echo "=== 2. 停掉现有 4 个算例 ==="
pkill -f '[p]hase_field-opt' 2>/dev/null
sleep 5
echo "  剩余进程: $(pgrep -fc '[p]hase_field-opt' 2>/dev/null || echo 0)"

echo
echo "=== 3. 以 2 算例 × 8 进程重新启动 ==="
BASE=/root/work/multi2
mkdir -p "$BASE"
sed 's/\r$//' /mnt/f/speed_up/pipeline/phase2_prod.i > "$BASE/template.i"

for rid in 1 2; do
    dir="$BASE/run$rid"
    mkdir -p "$dir"
    sed "s/rand_seed = 10/rand_seed = $((200 + rid * 7))/" "$BASE/template.i" > "$dir/in.i"
    (
        cd "$dir" || exit 1
        rm -f out.e out.csv
        mpirun -np 8 /root/moose/modules/phase_field/phase_field-opt -i in.i \
            Executioner/end_time=1500 Outputs/file_base=out > run.log 2>&1
    ) &
    echo "  run$rid 已启动 (PID $!)"
done

echo
echo "已启动，用 status2.sh 查看进度"
