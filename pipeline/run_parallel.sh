#!/bin/bash
# =============================================================================
# 并行跑多个 2D 生产算例 —— 把机器的并发度用起来
#
# 【为什么】
#   单个算例 6.3 小时只用 8 个进程，20 核的机器大部分闲着。
#   改成多算例并行，同样的墙上时间产出多倍数据。
#   而数据是整个项目的真正瓶颈（算子训练、转移算子标定都靠它）。
#
# 【资源核算】
#   本机：20 逻辑核，WSL 24 GB 内存
#   每个 MOOSE 算例：约 1.5–2 GB 内存
#   方案：4 个算例 × 4 进程 = 16 进程，留 4 个给系统/训练
#        内存约 8 GB，安全
#
# 【每个算例的差异】
#   用不同的 rand_seed → 不同的初始晶粒结构
#   这样数据是独立同分布的，不是同一个算例的重复
#
# 用法：
#   bash run_parallel.sh [算例数] [每算例进程数] [end_time]
#   默认 4 / 4 / 1500
# =============================================================================

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

NRUNS="${1:-4}"
NP="${2:-4}"
END_TIME="${3:-1500}"

BIN=/root/moose/modules/phase_field/phase_field-opt
BASE=/root/work/multi
SRC=/mnt/f/speed_up/pipeline

mkdir -p "$BASE"
sed 's/\r$//' "$SRC/phase2_prod.i" > "$BASE/template.i"

echo "=============================================="
echo " 并行生产：$NRUNS 个算例，每算例 $NP 进程"
echo " end_time = $END_TIME"
echo " 合计 $((NRUNS * NP)) 个 MPI 进程（共 20 核）"
echo "=============================================="
date '+  开始 %H:%M:%S'

pids=()
for rid in $(seq 1 "$NRUNS"); do
    dir="$BASE/run$rid"
    mkdir -p "$dir"
    # 每个算例换个随机种子 → 独立初始结构
    sed "s/rand_seed = 10/rand_seed = $((100 + rid * 7))/" "$BASE/template.i" > "$dir/in.i"
    (
        cd "$dir" || exit 1
        rm -f out.e out_out.csv
        mpirun -np "$NP" "$BIN" -i in.i \
            Executioner/end_time="$END_TIME" \
            Outputs/file_base=out > run.log 2>&1
        echo "  [run$rid] 完成于 $(date '+%H:%M:%S')"
    ) &
    pids+=($!)
done

wait
date '+  全部结束 %H:%M:%S'

echo
echo "=============================================="
echo " 汇总"
echo "=============================================="
tot=0
for rid in $(seq 1 "$NRUNS"); do
    f="$BASE/run$rid/out_out.csv"
    if [ -f "$f" ]; then
        g0=$(awk -F, 'NR==2{print $5}' "$f")
        g1=$(awk -F, 'END{print $5}' "$f")
        n=$((g0 - g1))
        tot=$((tot + n))
        printf "  run%d: 晶粒 %s → %s   消失 %d 个\n" "$rid" "$g0" "$g1" "$n"
    else
        printf "  run%d: 失败\n" "$rid"
    fi
done
echo "  ────────────────────────────"
echo "  合计拓扑事件: $tot 次"
