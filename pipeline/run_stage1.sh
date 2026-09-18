#!/bin/bash
# 阶段一冒烟测试：先语法检查，再短跑
#
# 用法:
#   bash run_stage1.sh              # 语法检查 + 短跑（end_time=2e-5）
#   bash run_stage1.sh full         # 语法检查 + 全长跑
#   bash run_stage1.sh check        # 只做语法检查

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/s1
MODE="${1:-short}"

mkdir -p "$RUN"
sed 's/\r$//' /mnt/f/speed_up/pipeline/stage1_meltpool.i > "$RUN/s1.i"
cd "$RUN" || exit 1

echo "=============================================="
echo " 语法检查"
echo "=============================================="
"$BIN" -i s1.i --check-input 2>&1 | tail -20
RC=${PIPESTATUS[0]}
if [ "$RC" -ne 0 ]; then
    echo "语法检查失败（退出码 $RC）"
    exit 1
fi
echo "语法检查通过"
[ "$MODE" = "check" ] && exit 0

if [ "$MODE" = "full" ]; then
    END="8.0e-4"
    NP=12
else
    END="1.0e-4"
    NP=8
fi

echo
echo "=============================================="
echo " 运行: end_time=$END, $NP 进程"
echo "=============================================="
rm -f stage1.e stage1_out.csv s1.log

date '+  开始 %H:%M:%S'
mpirun -np "$NP" "$BIN" -i s1.i Executioner/end_time="$END" > s1.log 2>&1
RC=$?
date '+  结束 %H:%M:%S'
echo "  退出码: $RC"

if [ -f stage1_out.csv ]; then
    echo
    echo "  --- 进度 ---"
    echo "  输出点数: $(( $(wc -l < stage1_out.csv) - 1 ))"
    head -1 stage1_out.csv
    tail -5 stage1_out.csv
else
    echo "  没有 CSV 输出"
fi

echo
echo "  --- 日志尾 ---"
tail -25 s1.log
