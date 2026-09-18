#!/bin/bash
# 最小验证：AD 核 + AD 派生材料这条链能不能用、雅可比是不是精确。
#
# 为什么必须先做这个：重写生产输入前，有三个机制点我没把握 ——
#   1. `ADDerivativeParsedMaterial` 是否会声明 AD 版的命名导数属性
#      （`ADACInterface` 的 variable_L 分支显式请求 `dL/dgr1` 这类属性）
#   2. `ADGrainGrowth` 用 AD 属性 L 乘 ADReal 的 computeDFDOP()，
#      能否自动带上 ACGrGrPoly 丢掉的那一项 dL/deta_j
#   3. 网格规模需不需要重编译（已知 MOOSE_AD_MAX_DOFS_PER_ELEM=64 >
#      11变量x4节点=44，但这台机器上实测一次更保险）
#
# 判据：||J - Jfd||_F/||J||_F 应达到 ~1e-6 量级
#       （非 AD 的 C 基线是 1.05e-06；完整非 AD 的 D 版是 0.059）
#
# 设计：2 个序参量，L 显式依赖 gr0/gr1（复现 ACGrGrPoly 丢项的条件），
#       kappa/gamma 保持常数以隔离变量。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/probe_ad
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

cat > A.i <<'EOF'
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 4
  ny = 4
  xmin = 0
  xmax = 4e-5
  ymin = 0
  ymax = 4e-5
[]
[GlobalParams]
  op_num = 2
  var_name_base = gr
[]
[Variables]
  [PolycrystalVariables]
  []
[]
[ICs]
  [ic0]
    type = PolycrystalColoringIC
    variable = gr0
    polycrystal_ic_uo = voronoi
    op_index = 0
  []
  [ic1]
    type = PolycrystalColoringIC
    variable = gr1
    polycrystal_ic_uo = voronoi
    op_index = 1
  []
[]
[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
    grain_num = 2
    rand_seed = 10
    int_width = 4e-6
  []
[]
[Kernels]
  [gr0_dt]
    type = ADTimeDerivative
    variable = gr0
  []
  [gr0_poly]
    type = ADGrainGrowth
    variable = gr0
    v = 'gr1'
    mob_name = L
  []
  [gr0_int]
    type = ADACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'gr1'
  []
  [gr1_dt]
    type = ADTimeDerivative
    variable = gr1
  []
  [gr1_poly]
    type = ADGrainGrowth
    variable = gr1
    v = 'gr0'
    mob_name = L
  []
  [gr1_int]
    type = ADACInterface
    variable = gr1
    mob_name = L
    kappa_name = kappa_op
    variable_L = true
    coupled_variables = 'gr0'
  []
[]
[Materials]
  # 注意：必须用 AD 版常数材料。MOOSE 禁止同一属性既作 AD 又作非 AD 声明 ——
  # 用 GenericConstantMaterial 会报
  #   "The requested AD material property 'gamma_asymm' is already ... non-AD"
  # 这条约束限定了生产输入的转换范围：kappa_op/gamma_asymm/mu/L 必须全转 AD，
  # 且不能有任何非 AD 消费者（已核对：生产输入里没有）。
  [const]
    type = ADGenericConstantMaterial
    prop_names = 'kappa_op gamma_asymm'
    prop_values = '1.8e-6 1.5'
  []
  [mu]
    type = ADDerivativeParsedMaterial
    property_name = mu
    coupled_variables = 'gr0 gr1'
    expression = '9.0e5*(1 + 0.3*(gr0^2 - gr1^2))'
    derivative_order = 2
  []
  # L 显式依赖序参量 —— 这正是非 AD 的 ACGrGrPoly 会丢 dL/deta_j 的条件
  [L]
    type = ADDerivativeParsedMaterial
    property_name = L
    coupled_variables = 'gr0 gr1'
    expression = '1.0*(1 + 0.5*(gr0^2 - gr1^2))'
    derivative_order = 2
  []
[]
[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]
[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  dt = 1e-6
  num_steps = 1
  dtmax = 2e-6
  nl_max_its = 6
  l_tol = 1e-6
  l_max_its = 30
  nl_rel_tol = 1e-8
  nl_abs_tol = 1e-7
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type -snes_test_jacobian'
  petsc_options_value = 'lu mumps 1'
[]
[Outputs]
  csv = true
[]
EOF

echo "=== 跑 AD 最小验证 ==="
setsid --wait "$MOOSE" -i A.i > A.log 2>&1
echo "退出码 $?"
echo
echo "======== ||J - Jfd||_F/||J||_F ========"
grep -a "J - Jfd" A.log | sed 's/^/  /'
echo
echo "======== 牛顿 ========"
grep -a "Nonlinear |R|" A.log | sed 's/\x1b\[[0-9;]*m//g' | head -6 | sed 's/^/  /'
echo
echo "======== 报错（关键：找 'not declared' / 'derivative' / 'AD' 相关）========"
grep -a -m6 -E '\*\*\* ERROR|not declared|not found|MOOSE_AD_MAX|derivative' A.log | sed 's/^/  /'
echo
echo "======== 判定 ========"
python3 - <<'PY'
import re
s = open("/root/work/probe_ad/A.log", encoding="utf-8", errors="replace").read()
vals = [float(v) for v in re.findall(r"J - Jfd\|\|_F/\|\|J\|\|_F = ([0-9.eE+-]+)", s)]
if vals:
    w = max(vals)
    print(f"  实测最大 = {w:.4e}")
    print("  ==> " + ("AD 链可用且雅可比精确（与 C 基线 1e-6 同级）-> 可以开始重写生产输入"
                      if w < 1e-4 else "**仍不一致，AD 没解决问题**"))
else:
    print("  拿不到比值 —— 说明这条链跑不起来，看上面的报错")
PY
