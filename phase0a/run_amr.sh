#!/bin/bash
# AMR 变体：验证自适应网格（真的增删单元）是否破坏溶质守恒
#
# 为什么关键：
#   相场本身用固定网格，GrainTracker 只交换序参量，所以守恒是平凡的。
#   但 AMR 会真的细化/粗化单元 —— 粗化时要把解从细网格搬到粗网格，
#   这是 MOOSE 里唯一"离散化本身在变"的环节，也是最可能泄漏守恒的地方。

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase0a

cd "$RUN" || exit 1
rm -f amr_out.csv amr_out.e

echo "=============================================="
echo " AMR 变体：t = 0 .. 1500"
echo "=============================================="
mpirun -np 4 "$BIN" -i phase0a_amr.i \
    Executioner/end_time=1500 \
    Outputs/file_base=amr_out 2>&1 | tail -6

echo
echo "=============================================="
echo " 分析"
echo "=============================================="
if [ -f amr_out.csv ]; then
    python3 precision_check.py amr_out.csv
else
    echo "amr_out.csv 未生成，仿真失败"
fi
