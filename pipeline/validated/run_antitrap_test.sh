#!/bin/bash
# =============================================================================
# 溶质截留的**判决性实验**：薄界面抗截留项能不能修掉模型的伪截留
# =============================================================================
# ## 问题（本轮量化）
#
# `tests/front1d.i`（1D 匀速移动前沿）在 `s = ξV/D = 1` 上实测
# `k_eff = c_solid/c_max = 0.877`，而**设计的平衡值是 0.6303**。
#
# 差 **+39%**。而且这不是"移动前沿的正常现象"——锐界面下界面处的
# `k = c_s/c_l` **就是**分配系数，与边界层无关。
# 所以这 +39% 就是模型厚界面造成的**伪溶质截留**。
#
# ## 为什么影响大
#
# 界面**排出的**溶质量 ∝ `(1−k)`：
#     k = 0.6303 ⇒ 1−k = 0.370
#     k = 0.877  ⇒ 1−k = 0.123
# ⇒ **模型少排了 3 倍的溶质** ⇒ 微观偏析被严重低估（那正是本课题要预测的量）。
#
# ## 为什么现在才试
#
# 仓库旧笔记写着「抗截留项的前置因子是在**单 φ** 下推的，本模型是多晶（8 个 η），
# **不能照搬**」。
# ⚠ **但 MOOSE 自己的例子就是多序参量**（`GrandPotentialAnisotropyAntitrap.i`，
# 两个 η）——**做法是每个相场加一个** `AntitrappingCurrent`。所以那条顾虑不成立。
#
# 而且 `front1d.i` **本来就是单 η** —— 正好是干净可判定的载体。
#
# ## 本实验
#
# 在 `front1d.i` 上加 `AntitrappingCurrent(variable = w, v = eta, f_name = F_at)`，
# `F_at = ALPHA · W · (1−k_eq) · c`，扫 `ALPHA`（含负值），看 `k_eff` 能不能回到 0.6303。
#
# **判据**：存在一个 `ALPHA` 使 `k_eff → 0.6303`（偏差 ≤ 2%）。
#   * 若**单一 ALPHA 在多个 s 上都能修** ⇒ 抗截留项有效，可推广
#   * 若怎么调都修不好 ⇒ 证实仓库那条"不在渐近区"的判断，走声明局限
#
# 用法： bash run_antitrap_test.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/antitrap}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-8.0e-3}"
TMO="${TMO:-1800}"
ALPHAS="${ALPHAS:-0 0.25 0.5 1.0 2.0 -0.5}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

# 逐 ALPHA 生成并跑
for A in $ALPHAS; do
  D="$ROOT/a$A"; mkdir -p "$D"
  ROOT_="$ROOT" SRC_="$SRC" A_="$A" D_="$D" python3 - <<'PY'
import os, re
root, src, a, d = (os.environ["ROOT_"], os.environ["SRC_"],
                   os.environ["A_"], os.environ["D_"])
base = open(src, encoding="utf-8").read()
mat = """  # 【抗截留】susceptibility F = ALPHA·W·(1−k_eq)·c
  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = 'c'
    constant_names = 'ALPHA W k_eq'
    constant_expressions = '%s 2.0e-6 0.6303'
    expression = 'ALPHA*W*(1-k_eq)*c'
  []
""" % a
ker = """  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = eta
    f_name = F_at
    coupled_variables = 'c'
  []
"""
if a != "0":
    m = re.search(r"^\[Materials\]\n", base, re.M); assert m
    base = base[:m.end()] + mat + base[m.end():]
    m = re.search(r"^\[Kernels\]\n", base, re.M); assert m
    base = base[:m.end()] + ker + base[m.end():]
open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(base)
PY
  cd "$D"
  RC=0
  timeout "$TMO" "$MOOSE" -i case.i "Executioner/end_time=$T_END" > run.log 2>&1 || RC=$?
  printf "  %-8s rc=%s\n" "$A" "$RC"
  cd "$ROOT"
done

echo
echo "=== k_eff vs ALPHA ==="
python3 - "$ROOT" "$ALPHAS" <<'PY'
import csv, os, sys
root, alphas = sys.argv[1], sys.argv[2].split()
KE = 0.6303
print("  %-8s %-14s %-14s %-12s %s" % ("ALPHA", "c_solid", "c_max", "k_eff", "vs 0.6303"))
print("  " + "-" * 62)
for a in alphas:
    d = os.path.join(root, f"a{a}")
    fs = [x for x in os.listdir(d) if x.endswith(".csv")] if os.path.isdir(d) else []
    if not fs:
        print("  %-8s 没跑成" % a); continue
    r = list(csv.DictReader(open(os.path.join(d, fs[0]))))
    if not r:
        continue
    l = r[-1]
    def g(n):
        k = [c for c in l if n in c]
        return float(l[k[0]]) if k else float("nan")
    cs, cm = g("c_solid"), g("c_max")
    ke = cs / cm if cm else float("nan")
    print("  %-8s %-14.6f %-14.6f %-12.6f %+.2f%%" % (a, cs, cm, ke, 100 * (ke - KE) / KE))
print()
print("  判据：存在一个 ALPHA 使 k_eff 回到 0.6303（偏差 ≤ 2%）")
PY
