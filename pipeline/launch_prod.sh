#!/bin/bash
# 启动 2D 生产算例（含偏析，100 晶粒，end_time=1500，约 5 小时）

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/prod

mkdir -p "$RUN"
sed 's/\r$//' /mnt/f/speed_up/pipeline/phase2_prod.i > "$RUN/prod.i"
cd "$RUN" || exit 1

rm -f prod.e prod_out.csv prod.log

echo "开始 $(date '+%m-%d %H:%M:%S')"
mpirun -np 8 "$BIN" -i prod.i > prod.log 2>&1
RC=$?
echo "结束 $(date '+%m-%d %H:%M:%S')，退出码 $RC"

if [ -f prod_out.csv ]; then
    echo "步数: $(($(wc -l < prod_out.csv) - 1))"
    awk -F, 'NR>1 {if ($5!=p) printf "  t=%-8s 晶粒 %s\n", $1, $5; p=$5}' prod_out.csv | head -30
    tail -2 prod_out.csv
fi
