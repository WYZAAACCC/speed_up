#!/bin/bash
# 对照 B：锁定漂移的机制
#
# 假设：AMR 的漂移来自"粗化" —— 细网格的信息在合并成粗网格时丢失，
#       而细化（插值加密）不丢信息。
#
# 做法：AMR 只细化不粗化（coarsen_fraction = 0）
#   → 若 ΔM 变回 0，证明粗化是元凶
#   → 若仍有漂移，说明细化过程也有问题（挂点约束/投影不守恒）

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase0a
cd "$RUN" || exit 1

python3 - << 'PYEOF'
src = open('phase0a_amr.i').read()
old = 'coarsen_fraction = 0.05'
new = 'coarsen_fraction = 0.0'
assert old in src, '未找到 coarsen_fraction'
open('ctrlB.i','w').write(src.replace(old, new))
print("已生成 ctrlB.i：AMR 只细化不粗化")
PYEOF

echo
echo "=============================================="
echo " 对照 B：AMR 只细化，不粗化"
echo "=============================================="
rm -f ctrlB_out.csv ctrlB_out.e
mpirun -np 4 "$BIN" -i ctrlB.i Executioner/end_time=1500 Outputs/file_base=ctrlB_out 2>&1 | tail -4

echo
echo "--- 结果 ---"
if [ -f ctrlB_out.csv ]; then
    python3 precision_check.py ctrlB_out.csv 2>&1 | tail -20
else
    echo "ctrlB_out.csv 未生成"
fi
