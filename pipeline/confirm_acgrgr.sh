#!/bin/bash
# 最终确认：ACGrGrPoly 的离对角雅可比丢了 dL/deta_j。
#
# 证据链（小网格 -snes_test_jacobian，||J-Jfd||/||J||，初始态）：
#   JC C 基线                       1.05e-06   <- L 只依赖 T，缺项为零
#   J0 完整 D                       0.0594
#   J1 kappa 常数                   0.0594     <- 关 kappa 无用
#   J2 gamma 常数                   0.0596     <- 关 gamma 无用
#   J3 kappa+gamma 都常数           0.0596     <- 都关也无用 => 病根在 L
#
# 本实验跑两个（其余一切保持与 J0 相同）：
#   J4 L 只依赖 T（去掉 2a 的迁移率取向因子 + 2b 的 align 因子）
#        -> 若 ||J-Jfd|| 掉到 ~1e-6，则**坐实**病根是 dL/deta_j 缺项
#   J5 L 保留 eta 依赖、但整体乘 0（L恒等于常数）
#        -> 交叉验证：若也掉到 1e-6，进一步排除 L 的**数值**而确认是**导数**
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_conf

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_loc/base.i ./base.i
cp /root/work/s1d_loc/columnar_seeds.csv .

python3 - <<'PY'
import re

def shrink(s, tag):
    s = re.sub(r"^    nx = .*$", "    nx = 20", s, flags=re.M)
    s = re.sub(r"^    ny = .*$", "    ny = 8", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 6", s, flags=re.M)
    s = re.sub(r"^  petsc_options_iname = .*$",
               "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'",
               s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps 1'", s, flags=re.M)
    s = re.sub(r"^file_base = .*$", f"file_base = {tag}", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = {tag}")
    return s

def set_body(s, name, new_block_body):
    """把 Materials/name 的内容整体替换。"""
    m = re.search(rf"\n  \[{name}\]\n(.*?)\n  \[\]\n", s, re.S)
    assert m, f"找不到 Materials/{name}"
    return s[:m.start(1)] + "\n" + new_block_body.rstrip("\n") + s[m.end(1):]

base = open("base.i", encoding="utf-8").read()
assert base.count("type = TimeDerivative") == 8, "核没修好"

# J4: L 只依赖 T。把 L_aniso 换成各向同性 Arrhenius，去掉对 L2a/L2b 的引用。
j4 = set_body(base, "L_aniso", """    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T'
    expression = '(4.0/3.0)*232*exp(-3.234/(8.617e-05*T))/4e-6'
    derivative_order = 2""")
open("J4.i", "w", encoding="utf-8").write(shrink(j4, "J4"))
print("  J4.i  (L 只依赖 T —— 去掉 2a迁移率取向因子 + 2b align 因子)")

# J5: L 与 eta 无关但保留 T 依赖（把 L2b 的系数 A_ani 设成 0，
#     并把 L2a 的逐对权重全部换成 1 => 等价于常数取向因子）
j5 = base
j5 = re.sub(r"(property_name = L2b\n(?:.*\n)*?    expression = ')1\+0\.7",
            r"\g<1>1+0.0", j5)
j5 = re.sub(r"(property_name = L2a\n(?:.*\n)*?    expression = ')[^']*'",
            r"\g<1>(4.0/3.0)*232*exp(-3.234/(8.617e-05*T))/4e-6'", j5, flags=re.S)
open("J5.i", "w", encoding="utf-8").write(shrink(j5, "J5"))
print("  J5.i  (L2a 换各向同性 Arrhenius, L2b 系数=0 -> L 与 eta 无关)")
PY

for t in J4 J5; do mkdir -p "$t"; cp "$t.i" columnar_seeds.csv "$t"/; done

echo "=== 跑 J4 / J5 ==="
for t in J4 J5; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "$t.i" > run.log 2>&1; echo "  $t rc=$?" ) &
done
wait

echo
echo "============ 确认表 ============"
python3 - <<'PY'
import re
ROWS = [("JC", "C 基线（L 只依赖 T）", "1.05e-06"),
        ("J0", "完整 D", None), ("J1", "kappa 常数", None),
        ("J2", "gamma 常数", None), ("J3", "kappa+gamma 常数", None),
        ("J4", "L 只依赖 T（本次）", None), ("J5", "L 与 eta 无关（本次）", None)]
for tag, label, known in ROWS:
    d = "/root/work/s1d_loc" if tag in ("JC", "J0", "J1", "J2", "J3") else "/root/work/s1d_conf"
    try:
        s = open(f"{d}/{tag}/run.log", encoding="utf-8", errors="replace").read()
    except OSError:
        print(f"  {tag:>2}  {label:26} 无日志"); continue
    vals = [float(v) for v in re.findall(r"J - Jfd\|\|_F/\|\|J\|\|_F = ([0-9.eE+-]+)", s)]
    if vals:
        print(f"  {tag:>2}  {label:26} {vals[0]:.3e}")
    else:
        print(f"  {tag:>2}  {label:26} 拿不到比值")
print()
print("  判定：若 J4 掉到 ~1e-6 而 J0/J3 保持 ~0.06，则坐实病根 =")
print("        ACGrGrPoly::computeQpOffDiagJacobian 丢了 dL/deta_j 项。")
PY
