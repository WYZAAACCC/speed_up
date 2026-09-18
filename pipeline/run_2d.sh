#!/bin/bash
# 2D 生产算例：先短跑计时，再决定是否直接放长跑

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase2
SRC=/mnt/f/speed_up/pipeline
NP=8

mkdir -p "$RUN"
sed 's/\r$//' "$SRC/phase2_2d.i" > "$RUN/phase2_2d.i"
cd "$RUN" || exit 1

echo "=============================================="
echo " 语法检查"
echo "=============================================="
"$BIN" -i phase2_2d.i --check-input 2>&1 | tail -6
if [ "${PIPESTATUS[0]}" -ne 0 ]; then echo "语法检查失败"; exit 1; fi

echo
echo "=============================================="
echo " 计时跑：end_time=200"
echo "=============================================="
rm -f phase2_2d*.e phase2_2d_out.csv

START=$(date +%s)
mpirun -np $NP "$BIN" -i phase2_2d.i Executioner/end_time=200 2>&1 | tail -10
RC=${PIPESTATUS[0]}
END=$(date +%s)
WALL=$((END - START))

echo
echo "退出码 $RC，墙钟 ${WALL} 秒"

if [ -f phase2_2d_out.csv ]; then
    NSTEP=$(($(wc -l < phase2_2d_out.csv) - 1))
    echo "完成 $NSTEP 个时间步"
    if [ "$NSTEP" -gt 0 ]; then
        PER=$(echo "scale=2; $WALL / $NSTEP" | bc)
        echo "每步 ${PER} 秒"
        echo "→ 跑完 end_time=4000 估计需要 $(echo "scale=1; $PER * 4000 / 20 / 3600" | bc) 小时"
    fi
    echo
    tail -3 phase2_2d_out.csv
fi
