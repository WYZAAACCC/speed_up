#!/bin/bash
# 主元平移已消除 SUBPC_ERROR，剩下 DIVERGED_ITS（GMRES 30 次不够）。
# 这一轮：保留主元平移 + 把线性迭代上限提到 300，看是否只是迭代数不够。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
cd /root/work/s1d_w || exit 1

cp stage1_meltpool_d.i try2.i
python3 - <<'PY'
import re
s = open("try2.i", encoding="utf-8").read()
s = s.replace(
  "-pc_asm_overlap'",
  "-pc_asm_overlap -sub_pc_factor_shift_type -sub_pc_factor_shift_amount'")
s = s.replace(
  "asm      31                  preonly       ilu          1'",
  "asm      31                  preonly       ilu          1                 nonzero                      1e-8'")
s = re.sub(r"^  l_max_its = .*$", "  l_max_its = 300", s, flags=re.M)
s = re.sub(r"^  l_tol = .*$", "  l_tol = 1e-5", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 4e-6", s, flags=re.M)
open("try2.i", "w", encoding="utf-8").write(s)
PY
grep -n "l_max_its\|l_tol\|petsc_options_value\|end_time" try2.i

echo "=== 跑 ==="
setsid --wait "$MOOSE" -i try2.i > try2.log 2>&1
echo "退出码 $?"
printf "收敛步数: "; grep -ac "Solve Converged" try2.log
echo "残差序列:"; grep -a "Nonlinear |R|" try2.log | head -14 | sed 's/^/  /'
echo "线性求解:"; grep -a "Linear solve" try2.log | head -6 | sed 's/^/  /'
echo "步长推进:"; grep -a "^Time Step" try2.log | tail -4 | sed 's/^/  /'
