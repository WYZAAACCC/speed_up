#!/bin/bash
# =============================================================================
# 直接测「生产现在有多少溶质截留」的 1D 代理算例
# =============================================================================
# ## 为什么要这个
#
# 缺口的定量结论此前一直是**外推**：由 1D 扫出来的 `L_eff = δ_c + c·ξ` 律，
# 代进生产的 `δ_c = D_L/V = 4.2 nm`、`ξ = 2 µm` 得 `k_eff ≈ 0.999`。
# 但 `s = ξV/D = 476` 这一步跨了 100 倍，外推不算数。
#
# 本脚本**直接跑到生产的无量纲工作点**：
#
#   front1d.i 的 ξ = 2 µm、D_L = 2.52e-9、k_c = 0.9、A = 0.264 —— **和生产完全一致**
#   （见 stage1_meltpool_c.i 的 [solute_mobility]：D_L=2.52e-09, k_c=0.9, A_part=0.264）
#   只差两处：
#     * kappa_c 用生产值 1e-14
#     * **V 提到生产的扫描速度 0.6 m/s**（front1d.i 原值是 1.26e-3）
#
#   V = 3·ξ·L·ΔF ⇒ 只改 L（Allen–Cahn 迁移率），保持 dG/ξ 不动 ⇒ 剖面形状不变。
#       L_new = L_old · V_target/V_old = 5.833e-4 · 476.2 = 0.2777
#
#   ⇒ δ_c = D_L/V = 2.52e-9/0.6 = 4.2 nm，而 dx = 0.25 µm
#     ⇒ δ_c/dx = 0.017 —— **与生产的 0.0042 同量级**（生产 dx=1 µm）
#     ⇒ ξ/δ_c = 476 —— 与生产**完全相同**
#
# ## 判据
#
#   * `L_eff = δ_c + c·ξ` 律（1D 实测，c≈1.3~1.5）预测 k_eff ≈ 0.999
#   * 若实测 k_eff ≥ 0.99 ⇒ **生产当前的微偏析被低估约 400 倍**（(1−k_e)/(1−k_eff)）
#     —— 这正是本课题要预测的量，是**结论级**的发现
#   * 守恒漂移 ≤ 1e-8
#
# ⚠ 用户约束：只做 1D 局部算例，不跑生产。
#
# 用法： V_TARGET=0.6 bash run_prod_1d.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${SRC:-$HERE/../tests/front1d.i}"
ROOT="${ROOT:-/root/work/prod1d}"
MOOSE="${MOOSE:-/root/moose/modules/phase_field/phase_field-opt}"
NX="${NX:-160}"
TMO="${TMO:-900}"
T_END="${T_END:-5.0e-5}"
KC_FIX="${KC_FIX:-1e-14}"
V_TARGET="${V_TARGET:-0.6}"
V_LIST="${V_LIST:-$V_TARGET}"

[ -f "$SRC" ] || { echo "错误：找不到 $SRC" >&2; exit 1; }
rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

python3 - "$ROOT" "$SRC" "$KC_FIX" "$V_LIST" "$NX" <<'PY'
import os, re, sys
root, src, kc, vlist, nx = (sys.argv[1], sys.argv[2], sys.argv[3],
                            sys.argv[4].split(), int(sys.argv[5]))
XI, L0, DG = 2.0e-6, 5.833e-4, 3.6e5
V0 = 3.0 * XI * L0 * DG
D = 2.8e-9 * 0.9          # 生产 D_L
K_C, A_P, C0 = 0.9, 0.264, 0.036
DX = 4.0e-5 / nx
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
print(f"  基准 V = {V0:.4e} m/s（= front1d.i 原值），dx = {DX:.3e} m")
for v in vlist:
    vt = float(v)
    Ln = L0 * vt / V0
    DC = D / vt
    # ---- 初值：**把正确的过剩量放进网格能表示的宽度里** ----
    # 守恒要求 ∫(c−c0)dx = 2·M·A·c0/V 必须由初值给定（此后守恒）。
    # 解析剖面 δ_c = D/V 在这里只有 4.2 nm ⇒ 网格上是阶跃 ⇒ 牛顿崩。
    # ⇒ 用同样过剩量、但宽度取 max(δ_c, 2dx) 的指数剖面。
    W_IC = max(DC, 2.0 * DX)
    # ⚠ 过剩量必须是 ∫(c−c0)dx = 2·M·A·c0/V = (2A/k_c)·c0·δ_c
    #   注意是 **(1/k_e − 1) = 2A/k_c = 0.5866**，不是 (1−k_e) = 0.3697。
    #   第一版写错了，初值只带了 63% 的过剩量。
    A_IC = (2.0 * A_P / K_C) * C0 * DC / W_IC
    t, n = re.subn(
        r"(prop_values\s*=\s*')([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(\s+)([0-9.eE+-]+)(')",
        lambda m: f"{m.group(1)}{Ln:.10g}{m.group(3)}{m.group(4)}{m.group(5)}"
                  f"{kc}{m.group(7)}{m.group(8)}{m.group(9)}", base)
    assert n == 1, f"V={v}: prop_values 匹配 {n} 处"
    # ⚠ **只替换单行子串**。跨行正则极易失配（本仓库已踩过两次）。
    # 原式：0.036*(1 + (1-0.6303)/0.6303*exp(-1.26e-3*(x-5.0e-6)/2.52e-9))
    # 新式：0.036*(1 + (A_IC/0.036)*exp(-(x-5.0e-6)/W_IC))   ← 等价于 c0 + A_IC*exp(..)
    t2, n2 = re.subn(
        r"\(1-0\.6303\)/0\.6303\*exp\(-1\.26e-3\*\(x-5\.0e-6\)/2\.52e-9\)",
        f"{A_IC/C0:.10e}*exp(-(x-5.0e-6)/{W_IC:.10e})", t)
    assert n2 == 1, f"V={v}: IC 替换 {n2} 处"
    t = t2
    t = t.replace("[c_far]\n    type = ElementalVariableValue",
                  "[c_far]\n    enable = false\n    type = ElementalVariableValue")
    d = os.path.join(root, f"v{v}")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(t)
    print(f"  V = {vt:.4e} m/s ⇒ L = {Ln:.6g}，δ_c = {DC:.3e} m"
          f"（{DC/DX:.4f} 个网格）")
    print(f"       初值用宽 {W_IC:.3e} m（{W_IC/DX:.1f} 网格）、幅值 {A_IC:.3e}，"
          f"过剩量 ∫ = {A_IC*W_IC:.3e}（目标 {2*2.8e-9*A_P*C0/vt:.3e}）")
PY

echo
echo "=== 跑（nx=$NX，end_time=$T_END s）==="
for V in $V_LIST; do
  cd "$ROOT/v$V"
  S0=$(date +%s); RC=0
  timeout "$TMO" "$MOOSE" -i case.i "Mesh/nx=$NX" "Executioner/end_time=$T_END" \
      "Executioner/TimeStepper/dt=1.0e-8" "Outputs/exo/enable=false" > run.log 2>&1 || RC=$?
  printf "  V=%-8s rc=%-4s %4ss\n" "$V" "$RC" "$(( $(date +%s) - S0 ))"
  cd "$ROOT"
done

echo
echo "=== 结果 ==="
python3 "$HERE/report_prod1d.py" "$ROOT" "$V_LIST" "$NX"
