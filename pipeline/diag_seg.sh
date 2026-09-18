#!/bin/bash
# 诊断含偏析的 CH 系统为何不收敛
# 用 [p] 技巧避免 pkill 匹配到自己的命令行

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase2seg
cd "$RUN" || exit 1

echo "=== 杀掉卡住的进程 ==="
pkill -f '[p]hase2_2d_seg' 2>/dev/null
sleep 3
n=$(pgrep -fc '[p]hase_field-opt' 2>/dev/null || true)
echo "  剩余: ${n:-0}"

echo
echo "=== 单步诊断：看非线性迭代与残差 ==="
rm -f diag*.e diag*_out.csv
timeout 600 "$BIN" -i phase2_2d_seg.i \
    Executioner/end_time=20 \
    Outputs/file_base=diag Outputs/csv=false 2>&1 | \
    grep -E "Time Step|NL step|Solve Converged|Converged|residual|iterations|dt =|ERROR|dtmin" | head -40

echo
echo "退出码: $?"
