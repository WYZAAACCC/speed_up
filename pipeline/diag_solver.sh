#!/bin/bash
# 诊断：为什么时间步卡在 dt=20 不涨？
# 看非线性迭代次数、每步耗时、以及放大 dt 是否可行

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase1
cd "$RUN" || exit 1

echo "=============================================="
echo " A. 默认设置（dt=20）跑 3 步，看迭代次数"
echo "=============================================="
rm -f diag*.e diag*_out.csv
timeout 900 "$BIN" -i phase1_3d.i \
    Executioner/end_time=60 \
    Outputs/file_base=diagA Outputs/csv=false 2>&1 | \
    grep -E "Time Step|Solve Converged|NL step|Linear|iterations|Finished Executing" | tail -25

echo
echo "=============================================="
echo " B. 放大初始 dt 到 60，看能否收敛"
echo "=============================================="
timeout 900 "$BIN" -i phase1_3d.i \
    Executioner/end_time=180 \
    Executioner/TimeStepper/dt=60 \
    Outputs/file_base=diagB Outputs/csv=false 2>&1 | \
    grep -E "Time Step|Solve Converged|NL step|Linear|iterations|Finished Executing|ERROR" | tail -25
