#!/bin/bash
# 决定性验证：核修好之后，D 版的**装配雅可比**是否变正确了。
#
# 已知基线（同一把尺子，旧版上测得）：
#   C  基线（正确的核）        ||J-Jfd||/||J|| = 1.05e-06 ~ 3.24e-06   <- 手写雅可比基本精确
#   v0 完整 D（旧，核有 bug）  ||J-Jfd||/||J|| = 0.0546  ~ 0.0552      <- 误差 5.5%
#   v1 关 2b（旧）             ||J-Jfd||/||J|| = 1.20e-03 ~ 1.64e-03
#
# 判据：核修好后 D 版应回落到 ~1e-6 量级（与 C 同级）。
# 若仍在 1e-2 量级 -> 还有别的雅可比错误没找到。
#
# 注意：**不要用 pkill -f phase_field-opt**（会杀掉自己的 shell，exit 9），
# 也不要杀掉其他并行任务。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_jacfix

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./D.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("D.i", encoding="utf-8").read()
s = re.sub(r"^    nx = .*$", "    nx = 20", s, flags=re.M)
s = re.sub(r"^    ny = .*$", "    ny = 8", s, flags=re.M)
s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 6", s, flags=re.M)
s = re.sub(r"^  petsc_options_iname = .*$",
           "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'",
           s, flags=re.M)
s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps 1'", s, flags=re.M)
s = s.replace("file_base = stage1d", "file_base = JF")
# 前提校验：核必须是修好的那一版
assert s.count("type = TimeDerivative") == 8, "TimeDerivative 不是 8 个，核没修好"
assert "variable_L = true" in s, "缺 variable_L"
open("JF.i", "w", encoding="utf-8").write(s)
print("JF.i 写好（小网格 20x8 + MUMPS + 雅可比自检；核前提校验通过）")
PY

mkdir -p run; cp JF.i columnar_seeds.csv run/
cd run || exit 1
setsid --wait "$MOOSE" -i JF.i > run.log 2>&1
echo "退出码 $?"
echo
echo "======== 雅可比自检 ========"
grep -a "J - Jfd" run.log | sed 's/^/  /'
echo
echo "======== 牛顿 ========"
grep -a "Nonlinear |R|" run.log | head -8 | sed 's/^/  /'
echo
echo "======== 零主元/报错 ========"
grep -a -m4 -E "zero pivot|Singular|ERROR" run.log | sed 's/^/  /'
echo
echo "======== 判定（基线 C = 1.05e-06，旧 D = 0.055）========"
python3 - <<'PY'
import re
s = open("run.log", encoding="utf-8", errors="replace").read()
vals = [float(v) for v in re.findall(r"J - Jfd\|\|_F/\|\|J\|\|_F = ([0-9.eE+-]+)", s)]
if not vals:
    print("  拿不到 ||J-Jfd||/||J||，无法判定")
else:
    w = max(vals)
    print(f"  实测最大 = {w:.5e}")
    if w < 1e-4:
        print("  ==> 与 C 同级（~1e-6 量级）-> 雅可比已正确，核修复生效")
    elif w < 1e-2:
        print("  ==> 比旧 D(0.055) 好很多但仍比 C(1e-6) 差 -> 还有残留项")
    else:
        print("  ==> 仍在 1e-2 量级 -> 还有别的雅可比错误没找到")
PY
