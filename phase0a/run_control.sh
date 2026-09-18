#!/bin/bash
# 对照实验：把"网格在变"(AMR) 和 "网格更细/非均匀" 两个因素分开
#
# 背景：
#   无 AMR 且 uniform_refine=1  → ΔM 严格为 0
#   有 AMR 且 initial_adaptivity=2 → ΔM 相对漂移 -3.6e-4
#   但两次的网格分辨率不同，是混淆因素。
#
# 对照 A：不开 AMR，但用同样细的网格（uniform_refine=3）
#         → 若 ΔM 仍为 0，则漂移确定来自 AMR 本身
#         → 若 ΔM 也有漂移，则来自网格分辨率/FE 离散
#
# 对照 B：开 AMR 但把时间步减小（dt=5）
#         → 若漂移随步长缩小而减小，说明含时间积分误差成分

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

BIN=/root/moose/modules/phase_field/phase_field-opt
RUN=/root/work/phase0a
cd "$RUN" || exit 1

# ---- 生成对照 A 的输入文件：去掉 AMR，网格加密到 uniform_refine=3 ----
python3 - << 'PYEOF'
src = open('phase0a.i').read()
src = src.replace('uniform_refine = 1', 'uniform_refine = 3')
assert 'uniform_refine = 3' in src
open('ctrlA.i','w').write(src)
print("已生成 ctrlA.i：无 AMR + uniform_refine=3")
PYEOF

echo
echo "=============================================="
echo " 对照 A：无 AMR，细网格 (uniform_refine=3)"
echo "=============================================="
rm -f ctrlA_out.csv ctrlA_out.e
mpirun -np 4 "$BIN" -i ctrlA.i Executioner/end_time=1500 Outputs/file_base=ctrlA_out 2>&1 | tail -4

echo
echo "--- 结果 ---"
if [ -f ctrlA_out.csv ]; then
    python3 precision_check.py ctrlA_out.csv 2>&1 | tail -20
else
    echo "ctrlA_out.csv 未生成"
fi
