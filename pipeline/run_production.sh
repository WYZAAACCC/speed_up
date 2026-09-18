#!/bin/bash
# =============================================================================
# 2D 数据生产：多组独立算例
#
# 单一初始结构的事件数有限，跑多组独立算例才能拿到足够统计量，
# 供"问题量化"（阶段3）和"逐面算子训练"（阶段4）使用。
#
# 用法：
#   bash run_production.sh [并行组数] [总算例数] [end_time]
#   默认 2 并行 / 6 组 / end_time=400
#
# 资源核算（本机 20 逻辑核、WSL 24 GB）：
#   每组 8 个 MPI 进程 → 2 组并行 = 16 进程，留 4 个给系统
#   每组内存约 1–2 GB → 两组约 4 GB，安全
# =============================================================================

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

NPAR="${1:-2}"
NRUNS="${2:-6}"
END_TIME="${3:-400}"
MPI_PER=8

BIN=/root/moose/modules/phase_field/phase_field-opt
BASE=/root/work/prod
SRC=/mnt/f/speed_up/pipeline

mkdir -p "$BASE"
sed 's/\r$//' "$SRC/phase2_2d_seg.i" > "$BASE/template.i"
sed 's/\r$//' "$SRC/gen_seeds.py"    > "$BASE/gen_seeds.py"

echo "=============================================="
echo " 数据生产"
echo "   算例数   : $NRUNS"
echo "   并行组数 : $NPAR"
echo "   每组 MPI : $MPI_PER"
echo "   end_time : $END_TIME"
echo "=============================================="
date '+  开始 %H:%M:%S'

run_one() {
    local rid="$1"
    local dir="$BASE/run_$(printf '%02d' "$rid")"
    mkdir -p "$dir"
    cd "$dir" || return 1

    # 该组独立的初始结构
    python3 "$BASE/gen_seeds.py" seeds.txt "$((1000 + rid))" > seed_log.txt 2>&1
    cp "$BASE/template.i" input.i
    rm -f out.e out.csv

    local t0=$(date +%s)
    mpirun -np "$MPI_PER" "$BIN" -i input.i \
        Executioner/end_time="$END_TIME" \
        Outputs/file_base=out > run.log 2>&1
    local rc=$?
    local t1=$(date +%s)

    local ng="?"
    [ -f out.csv ] && ng=$(awk -F, 'END{print $5}' out.csv)
    echo "  [run $(printf '%02d' "$rid")] rc=$rc  ${ng} 晶粒  $(( (t1-t0)/60 )) 分钟"
}

rid=0
for rid in $(seq 1 "$NRUNS"); do
    run_one "$rid" &
    # 控制并行度
    while [ "$(jobs -rp | wc -l)" -ge "$NPAR" ]; do
        sleep 10
    done
done

wait
date '+  结束 %H:%M:%S'

echo
echo "=============================================="
echo " 汇总"
echo "=============================================="
for rid in $(seq 1 "$NRUNS"); do
    dir="$BASE/run_$(printf '%02d' "$rid")"
    if [ -f "$dir/out.csv" ]; then
        n=$(($(wc -l < "$dir/out.csv") - 1))
        g0=$(awk -F, 'NR==2{print $5}' "$dir/out.csv")
        g1=$(awk -F, 'END{print $5}' "$dir/out.csv")
        printf "  run %02d: %4d 步   晶粒 %s → %s   消失 %s 个\n" \
               "$rid" "$n" "$g0" "$g1" "$((g0 - g1))"
    else
        printf "  run %02d: 失败\n" "$rid"
    fi
done
