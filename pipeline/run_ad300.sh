#!/bin/bash
# AD 精确雅可比 + 提线性迭代上限 —— 两条修复合起来。
#
# 已知：
#   AD 版（l_max_its=30）牛顿单调下降 3.91->3.90->3.78->3.49e-05，
#     但 2 次 DIVERGED_ITS 30（线性求解容量不够）
#   非 AD 版（l_max_its=300）线性求解零失败，但牛顿卡在 7.3e-07 地板
#     （地板来自 ACGrGrPoly 丢 dL/deta_j 造成的雅可比不一致）
# 两者互补，所以合起来应该既无线性失败、也无残差地板。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_ad300
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./A.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("A.i", encoding="utf-8").read()
s = re.sub(r"^  l_max_its = .*$", "  l_max_its = 300", s, flags=re.M)
s = re.sub(r"^  l_tol = .*$", "  l_tol = 1e-6", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 4e-6", s, flags=re.M)
s = s.replace("file_base = stage1d", "file_base = A")
if "[Debug]" not in s:
    s = s.replace("\n[Executioner]\n",
                  "\n[Debug]\n  show_var_residual_norms = true\n[]\n\n[Executioner]\n", 1)
assert s.count("type = ADGrainGrowth") == 8 and s.count("type = ADACInterface") == 8
assert s.count("type = ADDerivativeParsedMaterial") == 4
open("A.i", "w", encoding="utf-8").write(s)
print("A.i 写好: AD 核 + l_max_its=300 + l_tol=1e-6 + end_time=4e-6")
PY

echo "=== 跑 ==="
setsid --wait "$MOOSE" -i A.i > run.log 2>&1
echo "退出码 $?"
echo
echo "======== 收敛步数 ========"
grep -ac "Solve Converged" run.log
echo
echo "======== 牛顿轨迹 ========"
grep -a "Nonlinear |R|" run.log | sed 's/\x1b\[[0-9;]*m//g' | head -30 | sed 's/^/  /'
echo
echo "======== 线性求解 ========"
grep -a "Linear solve" run.log | sed 's/^ *//' | sed 's/\x1b\[[0-9;]*m//g' | sort | uniq -c | sort -rn | head -4 | sed 's/^/  /'
echo
echo "======== 时间步推进 ========"
grep -a "^Time Step" run.log | tail -6 | sed 's/^/  /'
echo
echo "======== 报错 ========"
grep -a -m4 -E '\*\*\* ERROR|Aborting|SUBPC|NANORINF' run.log | sed 's/^/  /'
