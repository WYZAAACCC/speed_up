#!/bin/bash
# 重新分配算力（修正版）
#
# 上一版的三个 bug：
#   1. Exodus 文件名写错（模板里是 file_base = prod → prod.e，不是 out.e）
#   2. 启动后没有 wait → 脚本一退出后台任务就被 SIGHUP 杀掉
#   3. 抢救数据失败也没报错，静默跳过
#
# 这次：文件名修正 + 显式 wait + 每步都有输出

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

echo "=== 1. 抢救旧算例的部分数据 ==="
cd /root/work || exit 1
for rid in 1 2 3 4; do
    d="/root/work/multi/run$rid"
    # 找该目录下最大的 .e 文件（不管是 prod.e 还是别的名字）
    exo=$(ls -S "$d"/*.e 2>/dev/null | head -1)
    if [ -n "$exo" ]; then
        echo "  run$rid → $(basename "$exo")"
        python3 extract.py "$exo" --out "/root/work/partial$rid" --stride 2 \
            > "/root/work/partial$rid.log" 2>&1 \
            && echo "     提取完成: $(wc -l < /root/work/partial$rid/faces.csv) 行面记录" \
            || { echo "     提取失败:"; tail -3 "/root/work/partial$rid.log" | sed 's/^/       /'; }
    else
        echo "  run$rid: 没有 Exodus 文件"
    fi
done

echo
echo "=== 2. 以 2 算例 × 8 进程启动（这次带 wait）==="
BASE=/root/work/multi2
mkdir -p "$BASE"
sed 's/\r$//' /mnt/f/speed_up/pipeline/phase2_prod.i > "$BASE/template.i"

pids=()
for rid in 1 2; do
    dir="$BASE/run$rid"
    mkdir -p "$dir"
    sed "s/rand_seed = 10/rand_seed = $((200 + rid * 7))/" "$BASE/template.i" > "$dir/in.i"
    (
        cd "$dir" || exit 1
        rm -f prod.e out.csv in_out.csv
        # 用模板自带的 file_base=prod，避免文件名混乱
        mpirun -np 8 /root/moose/modules/phase_field/phase_field-opt \
            -i in.i Executioner/end_time=1500 > run.log 2>&1
        echo "  [run$rid] 结束于 $(date +%H:%M) rc=$?"
    ) &
    pids+=($!)
    echo "  run$rid 已启动"
done

sleep 20
echo
echo "  20 秒后检查："
for rid in 1 2; do
    n=$(pgrep -fc "[p]hase_field-opt" 2>/dev/null || echo 0)
    echo "    run$rid 日志: $(tail -1 "$BASE/run$rid/run.log" 2>/dev/null | head -c 70)"
done
echo "    当前 MOOSE 进程总数: $(pgrep -fc '[p]hase_field-opt' 2>/dev/null || echo 0)"

wait
echo
echo "=== 全部结束 ==="
for rid in 1 2; do
    f="$BASE/run$rid/prod.csv"
    [ -f "$f" ] || f="$BASE/run$rid/out.csv"
    if [ -f "$f" ]; then
        g0=$(awk -F, 'NR==2{print $5}' "$f"); g1=$(awk -F, 'END{print $5}' "$f")
        echo "  run$rid: 晶粒 $g0 → $g1  消失 $((g0-g1)) 个"
    fi
done
