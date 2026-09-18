#!/bin/bash
# 定位残差地板（2.65e-06，对 l_tol / l_max_its 都不敏感）。
#
# 证据链：
#   收紧 l_tol 1e-5 -> 1e-6/1e-8，地板不降反升（7.3e-07 -> 2.65e-06）
#   提到 l_max_its=1000，地板不动
#   => 不是线性精度问题，是**雅可比不一致**（近似雅可比的牛顿法线性收敛到地板）
#
# 源码怀疑对象：ACInterface 的离对角雅可比第 146 行用了 _dkappadop（= dkappa/d自身变量），
# 而对 η_j 求导本该用 _dkappadarg[cvar]。第 121 行（对角）与第 146 行**逐字相同**，
# 像复制粘贴。C 版 κ 是常数 -> 两个导数都为 0 -> 这个 bug 不可见（C 的 ||J-Jfd||=1e-6）。
# D 版 kappa_aniso 依赖全部 8 个 η -> 离对角项错 -> 雅可比不一致。
#
# 定位方法：小网格 + MUMPS + -snes_test_jacobian，逐个把 η 依赖关掉，看 ||J-Jfd||/||J||
#   J0 完整 D                    （预期 ~1e-2：不一致）
#   J1 kappa 常数                （若掉到 ~1e-6 -> 坐实是 kappa 那一项）
#   J2 gamma 常数                （检查 ACGrGrPoly 侧是否也有同类问题）
#   J3 kappa+gamma 都常数
#   JC C 基线                     （参照，已知 1.05e-06）
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_loc

# 停掉卡在地板上的 T1/T2/T3（用 PID，不用 pkill -f）
pgrep -f "phase_field-opt -i" > /tmp/mp.txt 2>/dev/null
xargs -r kill -9 < /tmp/mp.txt 2>/dev/null
sleep 3
echo "已停旧进程，剩余 $(pgrep -cf 'phase_field-opt -i')"

rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./base.i
cp /root/work/s1d_w/stage1_meltpool_c.i ./baseC.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re

def shrink(s):
    s = re.sub(r"^    nx = .*$", "    nx = 20", s, flags=re.M)
    s = re.sub(r"^    ny = .*$", "    ny = 8", s, flags=re.M)
    s = re.sub(r"^  end_time = .*$", "  end_time = 1e-6", s, flags=re.M)
    s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 6", s, flags=re.M)
    s = re.sub(r"^  petsc_options_iname = .*$",
               "  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'",
               s, flags=re.M)
    s = re.sub(r"^  petsc_options_value = .*$", "  petsc_options_value = 'lu mumps 1'", s, flags=re.M)
    return s

def set_expr(s, name, expr):
    m = re.search(rf"\n  \[{name}\]\n(.*?)\n  \[\]\n", s, re.S)
    assert m, f"找不到 Materials/{name}"
    body = re.sub(r"\n? *expression = '[^']*'", f"\n    expression = '{expr}'", m.group(1), count=1)
    assert body != m.group(1), f"{name} 里没找到 expression"
    return s[:m.start(1)] + body + s[m.end(1):]

base = open("base.i", encoding="utf-8").read()
assert base.count("type = TimeDerivative") == 8, "核没修好，前提不成立"

baseC = open("baseC.i", encoding="utf-8").read()
open("JC.i", "w", encoding="utf-8").write(shrink(baseC).replace("file_base = stage1c", "file_base = JC"))
print("  JC.i  (C 基线, 参照)")

open("J0.i", "w", encoding="utf-8").write(shrink(base).replace("file_base = stage1d", "file_base = J0"))
print("  J0.i  (完整 D)")

s = set_expr(base, "kappa_aniso", "1.8e-6")
open("J1.i", "w", encoding="utf-8").write(shrink(s).replace("file_base = stage1d", "file_base = J1"))
print("  J1.i  (kappa 常数)")

s = set_expr(base, "gamma_aniso", "1.5")
open("J2.i", "w", encoding="utf-8").write(shrink(s).replace("file_base = stage1d", "file_base = J2"))
print("  J2.i  (gamma 常数)")

s = set_expr(set_expr(base, "kappa_aniso", "1.8e-6"), "gamma_aniso", "1.5")
open("J3.i", "w", encoding="utf-8").write(shrink(s).replace("file_base = stage1d", "file_base = J3"))
print("  J3.i  (kappa+gamma 都常数)")
PY

for t in JC J0 J1 J2 J3; do mkdir -p "$t"; cp "$t.i" columnar_seeds.csv "$t"/; done

echo "=== 并行跑 JC/J0/J1/J2/J3 ==="
for t in JC J0 J1 J2 J3; do
  ( cd "$D/$t" && setsid --wait "$MOOSE" -i "$t.i" > run.log 2>&1; echo "  $t rc=$?" ) &
done
wait

echo
echo "============ ||J - Jfd||_F / ||J||_F ============"
python3 - <<'PY'
import re
LABEL = {
    "JC": "C 基线（参照，已知 ~1e-6）",
    "J0": "完整 D（预期 ~1e-2 = 不一致）",
    "J1": "kappa 常数（若 -> 1e-6 则坐实 kappa 项）",
    "J2": "gamma 常数",
    "J3": "kappa+gamma 都常数",
}
for t in ("JC", "J0", "J1", "J2", "J3"):
    try:
        s = open(f"/root/work/s1d_loc/{t}/run.log", encoding="utf-8", errors="replace").read()
    except OSError:
        print(f"  {t}: 无日志"); continue
    vals = [float(v) for v in re.findall(r"J - Jfd\|\|_F/\|\|J\|\|_F = ([0-9.eE+-]+)", s)]
    if vals:
        print(f"  {t:>2}  最大 {max(vals):.5e}   {LABEL[t]}")
    else:
        err = re.findall(r"\*\*\* ERROR \*\*\*\n(.*)", s)
        print(f"  {t:>2}  拿不到比值  {'/'.join(err[:1])[:70]}")
PY
