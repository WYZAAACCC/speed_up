#!/bin/bash
# 决定性诊断：不再调求解器参数，而是问 MOOSE 两个问题
#   Q1 哪个变量的残差卡住？      -> [Debug] show_var_residual_norms
#   Q2 kappa_op / L / gamma 本身是不是病态值？ -> ElementExtremeMaterialProperty
#
# 若 Q2 显示 kappa_op 出现 <=0 或 L 出现 1e30 这种值 -> 材料表达式错了（我的 bug）
# 若 Q2 正常而 Q1 只卡在某几个序参量 -> 雅可比/耦合问题
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
cd /root/work/s1d_w || exit 1

cp stage1_meltpool_d.i try3.i

python3 - <<'PY'
import re
s = open("try3.i", encoding="utf-8").read()

# 1) 主元平移（已实测能消除 SUBPC_ERROR），保留原 l_max_its=30 以复现原症状
s = s.replace(
  "-pc_asm_overlap'",
  "-pc_asm_overlap -sub_pc_factor_shift_type -sub_pc_factor_shift_amount'")
s = s.replace(
  "asm      31                  preonly       ilu          1'",
  "asm      31                  preonly       ilu          1                 nonzero                      1e-8'")

# 2) 快速失败
s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)

# 3) 逐变量残差
dbg = """[Debug]
  show_var_residual_norms = true
[]
"""
assert "\n[Executioner]\n" in s
s = s.replace("\n[Executioner]\n", "\n" + dbg + "[Executioner]\n", 1)

# 4) 材料属性极值
diag = []
for prop in ("kappa_op", "gamma_asymm", "L"):
    for vt in ("min", "max"):
        diag.append(f"""  [{prop}_{vt}]
    type = ElementExtremeMaterialProperty
    mat_prop = {prop}
    value_type = {vt}
    execute_on = 'initial timestep_end'
  []
""")
diag = "".join(diag)
i = s.index("\n[Postprocessors]\n") + len("\n[Postprocessors]\n")
s = s[:i] + diag + s[i:]

open("try3.i", "w", encoding="utf-8").write(s)
print("try3.i 写好")
PY

grep -n "mat_prop\|show_var_residual\|end_time\|petsc_options_value" try3.i

echo "=== 跑 ==="
setsid --wait "$MOOSE" -i try3.i > try3.log 2>&1
echo "退出码 $?"

echo
echo "############ Q2: 材料属性极值（关键）############"
grep -a -E "kappa_op_(min|max)|gamma_asymm_(min|max)|L_(min|max)" try3.log | head -20

echo
echo "############ Q1: 卡住的是哪个变量 ############"
grep -a "Nonlinear |R|" try3.log | head -6
echo "--- 逐变量（最后一次牛顿迭代）---"
awk '/Nonlinear \|R\|/{n++} n>=1' try3.log | grep -a -E "^\s+[a-z_]+ +\|R\|" | tail -40

echo
echo "############ 线性求解状态 ############"
grep -a "Linear solve" try3.log | head -5
echo "############ 报错 ############"
grep -a -m3 -E '\*\*\* ERROR|SUBPC|DIVERGED' try3.log
