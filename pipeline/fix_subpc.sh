#!/bin/bash
# 修复后的下一步：SUBPC_ERROR = ILU 遇到近零主元。
# 标准解法是加非零主元平移。同时看 Jacobian 对比结果（那是修复前跑的，作为对照）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_w

echo "################ 1. 修复前的雅可比对比（缩网格，旧输入）################"
for t in no2b D2b; do
  L=/root/work/s1d_jac/$t.log
  if [ -f "$L" ]; then
    echo "--- $t ---"
    grep -a "J - Jfd" "$L" | head -2 | sed 's/^/  /'
  else
    echo "--- $t --- 未跑出"
  fi
done

echo
echo "################ 2. 加非零主元平移重跑 ################"
cd "$D" || exit 1
cp stage1_meltpool_d.i try_shift.i
python3 - <<'PY'
import re
s = open("try_shift.i", encoding="utf-8").read()
s = s.replace(
  "-pc_asm_overlap'",
  "-pc_asm_overlap -sub_pc_factor_shift_type -sub_pc_factor_shift_amount'")
s = s.replace(
  "asm      31                  preonly       ilu          1'",
  "asm      31                  preonly       ilu          1                 nonzero                      1e-8'")
s = re.sub(r"^  end_time = .*$", "  end_time = 4e-6", s, flags=re.M)
open("try_shift.i", "w", encoding="utf-8").write(s)
PY
grep -n "petsc_options\|end_time" try_shift.i
echo
setsid --wait "$MOOSE" -i try_shift.i > shift.log 2>&1
echo "退出码 $?"
printf "收敛步数: "; grep -ac "Solve Converged" shift.log
echo "残差序列:"; grep -a "Nonlinear |R|" shift.log | head -12 | sed 's/^/  /'
echo "线性求解状态:"; grep -a "Linear solve" shift.log | head -5 | sed 's/^/  /'
echo "报错:"; grep -a -m2 -E 'ERROR|SUBPC' shift.log | sed 's/^/  /'
