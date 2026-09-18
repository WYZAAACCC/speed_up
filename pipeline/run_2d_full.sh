#!/bin/bash
# 2D 生产算例：全量跑（end_time=4000），后台进行
# 产出足够多的晶粒消失事件，供问题量化与算子训练

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase2
cd "$RUN" || exit 1

rm -f phase2_2d*.e phase2_2d_out.csv

echo "开始全量跑 end_time=4000，$(date '+%H:%M:%S')"
START=$(date +%s)
mpirun -np 8 "$BIN" -i phase2_2d.i 2>&1 | tail -30
RC=${PIPESTATUS[0]}
END=$(date +%s)

echo
echo "结束于 $(date '+%H:%M:%S')，退出码 $RC，耗时 $(( (END-START)/60 )) 分钟"
echo
echo "=== 结果摘要 ==="
if [ -f phase2_2d_out.csv ]; then
    echo "时间步数: $(($(wc -l < phase2_2d_out.csv) - 1))"
    head -1 phase2_2d_out.csv
    tail -3 phase2_2d_out.csv
fi
ls -lh phase2_2d*.e 2>/dev/null | head -3
