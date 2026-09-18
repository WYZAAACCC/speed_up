#!/bin/bash
# 3D 算例：语法检查 + 短期计时跑（缩小版，40³ = 64,000 单元）

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase1
SRC=/mnt/f/speed_up/pipeline
NP=8

mkdir -p "$RUN"
sed 's/\r$//' "$SRC/phase1_3d.i" > "$RUN/phase1_3d.i"
cd "$RUN" || exit 1

echo "=============================================="
echo " 1. 语法检查"
echo "=============================================="
"$BIN" -i phase1_3d.i --check-input 2>&1 | tail -12
if [ "${PIPESTATUS[0]}" -ne 0 ]; then echo "语法检查失败"; exit 1; fi
echo "  语法 OK"

echo
echo "=============================================="
echo " 2. 计时跑：end_time=100，$NP 进程"
echo "=============================================="
rm -f phase1_3d_out.csv phase1_3d*.e

START=$(date +%s)
mpirun -np $NP "$BIN" -i phase1_3d.i Executioner/end_time=100 2>&1 | tail -18
RC=${PIPESTATUS[0]}
END=$(date +%s)
WALL=$((END - START))

echo
echo "=============================================="
echo " 结果"
echo "=============================================="
echo "退出码: $RC    墙钟: ${WALL} 秒（end_time=100）"

if [ -f phase1_3d_out.csv ]; then
    NSTEP=$(($(wc -l < phase1_3d_out.csv) - 1))
    echo "完成时间步数: $NSTEP"
    if [ "$NSTEP" -gt 0 ]; then
        PER=$(echo "scale=1; $WALL / $NSTEP" | bc)
        echo "每步约: ${PER} 秒"
        echo
        echo "→ 若跑到 end_time=3000，估计需要 $(echo "scale=1; $PER * 3000 / (100 / $NSTEP)" / 3600 | bc) 小时"
    fi
    echo
    head -1 phase1_3d_out.csv
    tail -3 phase1_3d_out.csv
else
    echo "CSV 未生成"
fi
