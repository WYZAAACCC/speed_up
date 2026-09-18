#!/bin/bash
# 【A2 的决定性补充实验】区分"求解器差异"与"容差差异"。
#
# 已有事实：
#   A = MUMPS + nl_abs_tol=1e-9
#   B = ASM   + nl_abs_tol=1e-6
#   两者从 t=0 的**逐位相同**初值出发，但 relL2 从 3.4e-09 涨到 1.49e-03（最后一步涨 100 倍）。
#
# 但 A 与 B **同时改了求解器和容差**，是两个变量混杂 -> 无法归因。
# 补一个 C 来解开：
#
#   C = MUMPS + nl_abs_tol=1e-6    （与 B 同容差，与 A 同求解器）
#
# 判据：
#   C ≈ A  且  C ≠ B   -> 差异来自**求解器**（ASM 线性解不准）-> 生产必须 MUMPS
#   C ≈ B  且  C ≠ A   -> 差异来自**容差**（1e-6 不够）-> 收紧容差即可，ASM 仍可用
#   C 与 A、B 都不同    -> 系统对精度**敏感依赖**（混沌式放大）-> 需要独立调查，
#                          这会动摇"真值唯一"的前提，是科学问题不是工程问题
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/slv_cmp

python3 - <<'PY'
import re
s = open("/root/work/slv_cmp/A/A.i", encoding="utf-8").read()
s = re.sub(r"^  nl_abs_tol = .*$", "  nl_abs_tol = 1e-6", s, flags=re.M)
s = s.replace("file_base = A", "file_base = C")
open("/root/work/slv_cmp/C.i", "w", encoding="utf-8").write(s)
print("  C.i = MUMPS + nl_abs_tol=1e-6 （与 B 同容差，与 A 同求解器）")
PY

mkdir -p "$D/C"; cp "$D/C.i" "$D/columnar_seeds.csv" "$D/C"/ 2>/dev/null
cd "$D/C" || exit 1
setsid --wait "$MOOSE" -i C.i > run.log 2>&1
echo "C rc=$?" >> "$D/rc.txt"
echo
echo "================ C(MUMPS + 1e-6) 结果 ================"
echo "  收敛步 = $(grep -ac 'Solve Converged' run.log)"
echo "  末步: $(grep -a '^Time Step' run.log | tail -1)"
echo "  耗时: $(grep -a -oE 'Finished Executing[^]]*\] \[[^]]*\]' run.log | sed 's/\x1b\[[0-9;]*m//g' | tail -1)"
echo "  报错: $(grep -a -cE '\*\*\* ERROR|Aborting' run.log)"
