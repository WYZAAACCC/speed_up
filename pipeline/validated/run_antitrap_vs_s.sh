#!/bin/bash
# =============================================================================
# 抗截留项的**决定性验证**：同一个 ALPHA 能不能让所有 s 都回到 0.6303
# =============================================================================
# ## 为什么这是决定性的
#
# 真正的**薄界面修正**（Karma–Rappel 类）的定义性质就是：
# **结果不再依赖界面宽度**。在本算例里，"界面宽度"的角色由
#     s = ξ·V/D   （界面宽 / 边界层厚）
# 扮演 ⇒ 修正若为真，**同一个 ALPHA 应当在所有 s 上给出同一个 k_eff = k_e**。
#
# 若必须逐 s 调 ALPHA 才能凑上 0.6303，那它只是**曲线拟合**，没有推广价值
# ——那我们就该老老实实走「声明局限」。
#
# ## 矩阵
#
#   s ∈ {1, 10, 100}  ×  ALPHA ∈ {0（基线）, 3.0}
#
# 基线档用来复现「模型自己的 k_eff 随 s 变」（本轮已实测：
# 0.877 / 0.950 / 0.808）—— 那个**变化本身就是 bug 的症状**：
# 锐界面下 k 不该随 s 变。
#
# 用法： bash run_antitrap_vs_s.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/at_vs_s}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-8.0e-3}"
TMO="${TMO:-1800}"
ALPHA="${ALPHA:-3.0}"

XI=2.0e-6; L_MOB=5.833e-4; DG=3.6e5; K_C=0.9
S_LIST="${S_LIST:-1 10 100}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

python3 - "$ROOT" "$SRC" "$XI" "$L_MOB" "$DG" "$K_C" "$ALPHA" "$S_LIST" <<'PY'
import os, re, sys
root, src = sys.argv[1], sys.argv[2]
XI, L, DG, KC, ALPHA = (float(x) for x in sys.argv[3:8])
SLIST = [float(x) for x in sys.argv[8].split()]
V = 3.0 * XI * L * DG
base0 = open(src, encoding="utf-8").read()
print(f"  前沿速度 V = {V:.4e} m/s    ALPHA = {ALPHA}")
print()
print("  %-6s %-12s %-12s %s" % ("s", "D = M·k_c", "M", "δ=D/V (m)"))
for s in SLIST:
    D = XI * V / s
    print("  %-6.0f %-12.4e %-12.4e %-12.4e" % (s, D, D / KC, D / V))

mat = """  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = 'c'
    constant_names = 'ALPHA W k_eq'
    constant_expressions = '%s 2.0e-6 0.6303'
    expression = 'ALPHA*W*(1-k_eq)*c'
  []
""" % ALPHA
ker = """  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = eta
    f_name = F_at
    coupled_variables = 'c'
  []
"""

for s in SLIST:
    D = XI * V / s
    M = D / KC
    for tag, use_at in (("base", False), ("at", True)):
        t, n = re.subn(
            r"(prop_names\s*=\s*'L\s+kappa_op\s+kappa_c\s+M'\s*\n\s*prop_values\s*=\s*')"
            r"([0-9.eE+-]+)(\s+[0-9.eE+-]+\s+[0-9.eE+-]+\s+)([0-9.eE+-]+)(')",
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{M:.10g}{m.group(5)}", base0)
        assert n == 1, f"s={s}: M 匹配 {n} 处"
        if use_at:
            m = re.search(r"^\[Materials\]\n", t, re.M); assert m
            t = t[:m.end()] + mat + t[m.end():]
            m = re.search(r"^\[Kernels\]\n", t, re.M); assert m
            t = t[:m.end()] + ker + t[m.end():]
        d = os.path.join(root, f"s{int(s)}_{tag}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(t)
print()
print(f"  写出 {len(SLIST)*2} 个算例")
PY

echo
echo "=== 跑 ==="
for S in $S_LIST; do
  for T in base at; do
    cd "$ROOT/s${S}_${T}"
    RC=0
    timeout "$TMO" "$MOOSE" -i case.i "Executioner/end_time=$T_END" > run.log 2>&1 || RC=$?
    printf "  s=%-5s %-5s rc=%s\n" "$S" "$T" "$RC"
    cd "$ROOT"
  done
done

echo
echo "=== 结果：抗截留能否让 k_eff 与 s 无关 ==="
python3 - "$ROOT" "$S_LIST" <<'PY'
import csv, os, sys
root, slist = sys.argv[1], sys.argv[2].split()
KE = 0.6303
def ke(d):
    p = os.path.join(root, d)
    if not os.path.isdir(p):
        return None
    fs = [x for x in os.listdir(p) if x.endswith(".csv")]
    if not fs:
        return None
    r = list(csv.DictReader(open(os.path.join(p, fs[0]))))
    if not r:
        return None
    l = r[-1]
    def g(n):
        k = [c for c in l if n in c]
        return float(l[k[0]]) if k else float("nan")
    cs, cm = g("c_solid"), g("c_max")
    return cs / cm if cm else float("nan")

print("  %-6s %-14s %-14s %s" % ("s", "k_eff (无修正)", "k_eff (ALPHA)", "修正后 vs 0.6303"))
print("  " + "-" * 66)
res = {}
for s in slist:
    a, b = ke(f"s{s}_base"), ke(f"s{s}_at")
    res[s] = (a, b)
    if b is None or b != b:
        print("  %-6s %-14s %-14s —" % (s, f"{a:.6f}" if a == a else "?", "?")); continue
    print("  %-6s %-14.6f %-14.6f %+.2f%%" % (s, a, b, 100 * (b - KE) / KE))
print()
vals = [b for a, b in res.values() if b == b]
if len(vals) >= 2:
    spread = (max(vals) - min(vals)) / (sum(vals) / len(vals))
    print("  修正后跨 s 的**离散度** = %.2f%%" % (100 * spread))
    if spread < 0.05:
        print("  ✅ **同一个 ALPHA 让所有 s 都回到 0.6303** ⇒ 这是真正的薄界面修正，可推广")
    else:
        print("  ❌ 修正后仍随 s 变 ⇒ 只是拟合，不能推广 ⇒ 应走「声明局限」")
vals0 = [a for a, b in res.values() if a == a]
if len(vals0) >= 2:
    spread0 = (max(vals0) - min(vals0)) / (sum(vals0) / len(vals0))
    print("  （对照：修正前跨 s 的离散度 = %.2f%%）" % (100 * spread0))
PY
