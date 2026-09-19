#!/bin/bash
# =============================================================================
# 缺口 #3 修复路线的判决性实验（**重做版**）：抗截留项在正确的 kappa_c 下还有效吗
# =============================================================================
# ## 为什么要重做
#
# 前一轮（`run_antitrap_test.sh` / `run_antitrap_vs_s.sh`）结论是「抗截留项不成立」。
# **但那一轮的 `kappa_c` 是错的**：`tests/front1d.i` 里还留着 `1.125e-11`，
# 而生产 2026-09-18 已改成 `1e-14`。坏 `kappa_c` 会把溶质剖面撑到 `4.5 δ_c`
# （见 `run_kc_vs_keff.sh` 的实测），那个效应**淹没了**抗截留项要修的东西。
#
# ## 本轮已经查清的两件事（都是实测）
#
#   ① `kappa_c` 是**一个**机制：`κ_c: 1.125e-11 → 1e-13` 把 `k_eff` 从 0.877 压到 0.800。
#      但它在 `κ_c ≤ 1e-13` 之后**饱和**（`L_eff/δ_c` 停在 2.4）⇒ 还有第二个机制。
#
#   ② 第二个机制是**界面宽 ξ**。拟合 `L_eff = δ_c + 1.5·ξ`：
#        s=0.5（δ_c=4µm, ξ=2µm）：预测 L_eff/δ_c = 1.75，实测 1.8 ✓
#        s=1  （δ_c=2µm, ξ=2µm）：预测 2.50，实测 2.4~2.9 ✓
#      物理含义很清楚：**溶质是在整个弥散界面 ξ 上被排出的，不是在锐前沿上**
#      ⇒ 富集区至少 ξ 宽。**这正是抗截留项（Karma–Rappel / Plapp）要消掉的那一项。**
#
#   ③ 而且实测 `k_eff` 对 `nx`（40 vs 160）几乎不变 ⇒ **不是网格问题**。
#
# ## 官方系数（本轮从 MOOSE 例子里读出来的，不是猜的）
#
#   `phase_field/test/tests/GrandPotentialPFM/GrandPotentialAnisotropyAntitrap.i`：
#       [int]  property_name = rhodiff
#              expression = 'int_width*(rhob-rhoa)'
#       [rhoa] expression = 'w/Vm^2/ka + caeq/Vm'     ← 就是相 α 的浓度 c_α
#       [rhob] expression = 'w/Vm^2/kb + cbeq/Vm'     ← 相 β 的浓度 c_β
#   ⇒ **F = W·(c_β − c_α) = W·(c_l − c_s) = W·(1−k)·c_l**
#   ⇒ 本脚本参数化 `F_at = ALPHA*W*(1-k_eq)*c` 的**理论值是 ALPHA = 1**。
#
# ## 判据（这才是「薄界面修正」的定义性质）
#
#   真正的修正必须**与界面宽无关** ⇒ **同一个 ALPHA 要在所有 s 上给出同一个 k_eff = k_e**。
#   若必须逐 s 调 ALPHA，那就只是曲线拟合，不能推广（上一轮的结论形式，但要在对的 κ_c 下重判）。
#
# ## 矩阵
#
#   ALPHA ∈ {0, 0.5, 1, 1.5, 2, 3}   （0 = 基线，ALPHA=1 是理论值）
#   s     ∈ {0.5, 1, 2, 4}           （s = ξV/D；s 越大边界层越薄）
#
# ⚠ 用户约束：只做 1D 局部算例，不跑生产。
#
# 用法： bash run_antitrap2.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/at2}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
T_END="${T_END:-1.5e-2}"
TMO="${TMO:-900}"
NX="${NX:-160}"
KC_FIX="${KC_FIX:-1e-14}"
S_LIST="${S_LIST:-1}"
ALPHA_LIST="${ALPHA_LIST:-0 0.5 1 1.5 2 3}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

python3 - "$ROOT" "$SRC" "$KC_FIX" "$S_LIST" "$ALPHA_LIST" <<'PY'
import os, re, sys
root, src, kc, slist, alist = (sys.argv[1], sys.argv[2], sys.argv[3],
                               sys.argv[4].split(), sys.argv[5].split())
XI, L, DG, K_C = 2.0e-6, 5.833e-4, 3.6e5, 0.9
V = 3.0 * XI * L * DG
base = open(src, encoding="utf-8").read()
base = base.rstrip() + """

[VectorPostprocessors]
  [prof]
    type = LineValueSampler
    variable = 'c eta'
    start_point = '0 0 0'
    end_point = '4.0e-5 0 0'
    num_points = 4001
    sort_by = x
  []
[]
"""
for s in slist:
    D = XI * V / float(s)
    M = D / K_C
    t, n = re.subn(
        r"(prop_values\s*=\s*')([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(')",
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}"
                  f"{kc}{m.group(7)}{M:.10g}{m.group(9)}", base)
    assert n == 1, f"s={s}: prop_values 匹配 {n} 处"
    t2, n2 = re.subn(r"exp\(-1\.26e-3\*\(x-5\.0e-6\)/2\.52e-9\)",
                     f"exp(-{V:.6e}*(x-5.0e-6)/{D:.6e})", t)
    assert n2 == 1, f"s={s}: IC 替换 {n2} 处"
    t = t2
    # elementid=155 在大 s 时落在固相里，关掉
    t = t.replace("[c_far]\n    type = ElementalVariableValue",
                  "[c_far]\n    enable = false\n    type = ElementalVariableValue")
    for a in alist:
        if a in ("0", "0.0"):
            tt = t
        else:
            mat = f"""  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = 'c'
    constant_names = 'ALPHA W k_eq'
    constant_expressions = '{a} 2.0e-6 0.6303'
    expression = 'ALPHA*W*(1-k_eq)*c'
    derivative_order = 2
  []
"""
            ker = """  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = eta
    f_name = F_at
    coupled_variables = 'c'
  []
"""
            m = re.search(r"^\[Materials\]\n", t, re.M); assert m
            tt = t[:m.end()] + mat + t[m.end():]
            m = re.search(r"^\[Kernels\]\n", tt, re.M); assert m
            tt = tt[:m.end()] + ker + tt[m.end():]
        d = os.path.join(root, f"s{s}_a{a}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(tt)
print(f"  写出 {len(slist)*len(alist)} 个算例（κ_c={kc} 固定）")
PY

echo
echo "=== 跑 ==="
for S in $S_LIST; do
  for A in $ALPHA_LIST; do
    cd "$ROOT/s${S}_a${A}"
    S0=$(date +%s); RC=0
    timeout "$TMO" "$MOOSE" -i case.i "Mesh/nx=$NX" "Executioner/end_time=$T_END" \
        "Outputs/exo/enable=false" > run.log 2>&1 || RC=$?
    printf "  s=%-5s ALPHA=%-5s rc=%-4s %4ss\n" "$S" "$A" "$RC" "$(( $(date +%s) - S0 ))"
    cd "$ROOT"
  done
done

echo
echo "=== 结果 ==="
python3 "$HERE/report_antitrap2.py" "$ROOT" "$S_LIST" "$ALPHA_LIST"
