#!/bin/bash
# =============================================================================
# T1b 的**受控 FD 判决实验**：`L` 的 η 依赖到底进没进雅可比
# =============================================================================
# ## 背景（本轮用 MOOSE 自己的 dump 查出来的，不是推的）
#
# `[Debug] show_material_props = true` 逐材料打印**它实际产出的属性**。
# 在生产链的输出上实测：
#
#     L2a            → "L2a" "dL2a/dT" "dL2a/dgr0..7" "d^2L2a/..."     ✅ 全产出
#     free_energy    → "d^2f_loc/dcdgr0..7" ...                        ✅ 全产出
#     L2b            → **只有 "L2b"**                                  ❌ 导数一个没有
#     L_aniso  (L)   → **只有 "L"**                                    ❌
#     solute_mobility(M) → **只有 "M"**                                ❌
#
# 规律：**凡是用 `material_property_names` 引别的材料的，导数只按"本材料
# `coupled_variables` 里**直接出现在表达式文本中**的变量"发射**。`L2b` 的
# 表达式是 `1+0.7*(2*align4-1)` —— `gr*` 根本没出现 ⇒ 导数判为零 ⇒ **不发射**。
#
# 而生产核**确实在要这些导数**：
#     [gr0_int]  type = ACInterface  variable_L = true  → 构造函数里无条件取 `dL/dgr0`
#     [coupled_res] SplitCHWRes  coupled_variables='gr0..gr7' → 取 `dM/dgr0`
#
# ## 本实验问的是
#
#   **雅可比与残差一致吗？** 只在「`L` 依赖 η」时才会不一致。
#   两个算例**只差 `L2b` 里的 `align4` 那一项**：
#
#     eta_dep :  L2b = 1 + 0.7*(2*align4 - 1)      ← 与生产逐字相同
#     const   :  L2b = 1                            ← 关掉 η 依赖（正对照的"关"档）
#
#   判据：
#     * `const` 档必须给出很小的比值（否则测试本身有问题 —— 探针要先做正对照）
#     * 若 `eta_dep` 的比值**远大于** `const` ⇒ **`∂L/∂η` 真的没进雅可比** ⇒ T1b 成立
#
# ⚠ 网格要小（MOOSE 自己的 PetscJacobianTester 也只用小算例）。
# ⚠ 必须加 `-snes_max_it 1`：`-snes_convergence_test skip` 会让 SNES 永不收敛，
#   于是每次非线性迭代都重做一遍 FD（本仓库踩过，见 T1_CRITERION.md §3.2）。
#
# 用法： bash run_t1b_L_test.sh
# =============================================================================
set -eo pipefail

ROOT="${ROOT:-/root/work/t1b_L}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
NX="${NX:-60}"
TMO="${TMO:-600}"

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

mk_case () {   # $1=目录 $2=L2b 表达式 $3=mp $4=mob_name $5=L_aniso 的 expression（空=默认 L2a*L2b）
python3 - "$1" "$2" "$3" "$4" "$5" <<'PY'
import os, sys
d, l2b, mp = sys.argv[1], sys.argv[2], sys.argv[3]
mob = sys.argv[4]
lover = sys.argv[5] if len(sys.argv) > 5 else ""
if lover.strip():
    l_mp = "    material_property_names = 'gdir_p gdir_q'\n"
    l_ex = lover
else:
    l_mp = "    material_property_names = 'L2a L2b'\n"
    l_ex = "L2a*L2b"
os.makedirs(d, exist_ok=True)
mp_line = f"    material_property_names = '{mp}'\n" if mp.strip() else ""
t = f"""[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 60
  xmin = 0.0
  xmax = 6.0e-6
[]

[Variables]
  [gr0]
  []
  [gr1]
  []
[]

[ICs]
  [g0]
    type = FunctionIC
    variable = gr0
    function = '0.5*(1-tanh((x-3.0e-6)/4.0e-7))'
  []
  [g1]
    type = FunctionIC
    variable = gr1
    function = '0.5*(1+tanh((x-3.0e-6)/4.0e-7))'
  []
[]

[Kernels]
  [d0]
    type = TimeDerivative
    variable = gr0
  []
  [d1]
    type = TimeDerivative
    variable = gr1
  []
  # 生产核：variable_L = true ⇒ 构造函数里无条件索取 dL/dgr0、d^2L/dgr0^2、dkappa_op/dgr0
  [i0]
    type = ACInterface
    variable = gr0
    mob_name = {mob}
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'gr1'
  []
  [i1]
    type = ACInterface
    variable = gr1
    mob_name = {mob}
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'gr0'
  []
[]

[Materials]
  # --- 2b 第 0 层：热梯度方向（纯数据，ParsedMaterial 不产生雅可比项）---
  #     这里取固定方向，与生产同构（生产里它由 grad_Tx/grad_Ty 驱动）
  [gdir_p]
    type = ParsedMaterial
    property_name = gdir_p
    coupled_variables = ''
    constant_names = 'gp'
    constant_expressions = '1.0'
    expression = 'gp'
  []
  [gdir_q]
    type = ParsedMaterial
    property_name = gdir_q
    coupled_variables = ''
    constant_names = 'gq'
    constant_expressions = '0.0'
    expression = 'gq'
  []

  # --- 2b 第一层：四重对齐度（与生产逐字同构的简化版，两个取向）---
  [align4]
    type = DerivativeParsedMaterial
    property_name = align4
    coupled_variables = 'gr0 gr1'
    material_property_names = 'gdir_p gdir_q'
    expression = '((gr0^2*(1*gdir_p+0*gdir_q)^2 + gr1^2*(0.5*gdir_p+0.8660254*gdir_q)^2)/((gr0^2+gr1^2)+0.001))'
    derivative_order = 2
  []

  # --- 2b 第二层：本实验的自变量 ---
  [L2b]
    type = DerivativeParsedMaterial
    property_name = L2b
    coupled_variables = 'gr0 gr1'
{mp_line}    expression = '{l2b}'
    derivative_order = 2
  []

  # --- 2a：与 η 无关的常数迁移率（把变量隔离到 L2b 一处）---
  [L2a]
    type = DerivativeParsedMaterial
    property_name = L2a
    coupled_variables = 'gr0 gr1'
    constant_names = 'c0'
    constant_expressions = '1.0'
    expression = 'c0'
    derivative_order = 2
  []

  # --- 合成：L = L2a * L2b ---
  [L_aniso]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'gr0 gr1'
{l_mp}    expression = '{l_ex}'
    derivative_order = 2
  []

  [kap]
    type = GenericConstantMaterial
    prop_names = 'kappa_op'
    prop_values = '3.6e-6'
  []
[]

[Executioner]
  type = Transient
  solve_type = NEWTON
  scheme = bdf2
  petsc_options_iname = '-pc_type'
  petsc_options_value = 'lu'
  end_time = 1e-9
  dtmax = 1e-9
  nl_rel_tol = 1e-9
  nl_abs_tol = 1e-12
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1e-10
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
"""
open(os.path.join(d, "case.i"), "w", encoding="utf-8", newline="").write(t)
PY
}

AL4='((gr0^2*(1*gdir_p+0*gdir_q)^2 + gr1^2*(0.5*gdir_p+0.8660254*gdir_q)^2)/((gr0^2+gr1^2)+0.001))'
mk_case const   "1"                  ""              L    # 正对照：L 与 η 无关
mk_case eta_dep "1+0.7*(2*align4-1)" "align4"        L    # ← 生产结构
mk_case inline  "1+0.7*(2*$AL4-1)"   "gdir_p gdir_q" L    # 把 η 依赖写进 L2b 表达式
mk_case direct  "1+0.7*(2*$AL4-1)"   "gdir_p gdir_q" L2b  # 再绕过 L_aniso 那一层
mk_case merged  "1"                  ""              L    "1*(1+0.7*(2*$AL4-1))"  # ← 候选修法：L 自己字面含变量
echo "  写出 5 个算例（只差 L2b / L_aniso 两处）"

# 关掉输出里的 csv 噪声，避免覆盖
for d in const eta_dep inline direct merged; do rm -f "$d"/*.csv 2>/dev/null || true; done

echo
echo "=== 跑 FD 判决（nx=$NX，只在初始态做一次）==="
for d in const eta_dep inline direct merged; do
  cd "$ROOT/$d"
  set +e
  timeout "$TMO" "$MOOSE" -i case.i Mesh/nx=$NX \
      -snes_force_iteration -snes_type ksponly -ksp_type preonly -pc_type none \
      -snes_convergence_test skip -snes_max_it 1 \
      -snes_test_jacobian -snes_test_jacobian_view > jac.log 2>&1
  RC=$?
  set -e
  printf "  %-8s rc=%s\n" "$d" "$RC"
  cd "$ROOT"
done

echo
echo "=== 结果 ==="
python3 - <<'PY'
import os, re
pat = re.compile(r"\|\|J - Jfd\|\|_F/\|\|J\|\|_F\s?=?\s?(\S+?),\s*"
                 r"\|\|J - Jfd\|\|_F\s?=?\s?(\S+)")
print("  %-10s %-26s %s" % ("算例", "比值 ||J-Jfd||/||J||", "绝对 ||J-Jfd||"))
print("  " + "-" * 62)
res = {}
for d in ("const", "eta_dep", "inline", "direct", "merged"):
    f = os.path.join(d, "jac.log")
    if not os.path.exists(f):
        print("  %-10s 没有日志" % d); continue
    x = open(f, encoding="utf-8", errors="replace").read()
    x = re.sub(r"\x1b\[[0-9;]*m", "", x)
    ms = pat.findall(x)
    if not ms:
        tail = [l for l in x.splitlines() if "Jfd" in l or "ERROR" in l][:3]
        print("  %-10s 没解析到比值；线索：%s" % (d, tail)); continue
    r, a = ms[0]
    res[d] = (float(r), float(a))
    print("  %-10s %-26s %s" % (d, r, a))
print()
print("  读法：")
print("    `const`   = 正对照，L 与 η 无关 ⇒ 比值必须很小（否则测试本身有问题）")
print("    `eta_dep` = **生产结构**：L2b 经 material_property_names 引 align4")
print("    `inline`  = 候选修法：把 align4 的 η 依赖直接写进 L2b 的表达式")
print()
if "const" in res:
    rc = res["const"][0]
    if rc > 1e-6:
        print(f"  ⚠ **正对照不干净（{rc:.2e}）⇒ 测试本身有问题**，先查算例（教训 19）")
    else:
        print(f"  ✅ 正对照干净（{rc:.2e}，MOOSE 阈值 1e-7）⇒ 测试有分辨力")
    for d, tag in (("eta_dep", "生产结构"),
                   ("inline", "把 η 写进 L2b"),
                   ("direct", "再绕过 L_aniso"),
                   ("merged", "候选修法：L 字面含 η")):
        if d not in res:
            continue
        r = res[d][0]
        if r > 100 * rc:
            print(f"  ❌ `{d}`（{tag}）比值 {r:.2e}，比正对照大 {r/rc:.0f} 倍"
                  f" ⇒ **∂L/∂η 没进雅可比**")
        elif r < 10 * rc:
            print(f"  ✅ `{d}`（{tag}）比值 {r:.2e}，与正对照同量级"
                  f" ⇒ **雅可比与残差一致**")
        else:
            print(f"  ⚠ `{d}`（{tag}）比值 {r:.2e}，差 {r/rc:.0f} 倍 —— 介于两者之间")
PY
