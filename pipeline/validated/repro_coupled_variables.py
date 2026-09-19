#!/usr/bin/env python3
"""
最小判定：`SplitCHParsed` 的 `coupled_variables` 到底改不改变雅可比？

背景：审计 P0-1（= 本报告 P15）说 `[coupled_parsed]` 缺 `coupled_variables='gr0..gr7'`
⇒ `∂²f/∂c∂ηᵢ` 整块不进雅可比 ⇒ 牛顿退化。

**实测反驳了后果那半句**：在生产算例（24×12）上修复前后
`||J−Jfd||_F/||J||_F` 与整个牛顿残差序列**逐位相同**。
生产算例每次跑要 ~2 分钟（巨型 parsed 表达式的 JIT），不适合反复试，
所以这里造一个**同结构的最小算例**（2 个序参量 + c + w，小 f_loc），
把「声明 / 不声明」的差别量出来。

用法：
    python3 repro_coupled_variables.py      # 生成 A.i（不声明）与 B.i（声明）
    # 然后各自 phase_field-opt -i X.i -snes_test_jacobian 1e-5
"""

import pathlib

TMPL = """# 最小判定算例（自动生成，见 repro_coupled_variables.py）
#   A = 不声明 coupled_variables   B = 声明
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 8
  xmin = 0
  xmax = 1e-6
[]
[Variables]
  [gr0]
    initial_condition = 0.5
  []
  [gr1]
    initial_condition = 0.5
  []
  [c]
    initial_condition = 0.036
  []
  [w]
    initial_condition = 0
  []
[]
[Kernels]
  # --- 序参量：给一个非零驱动力，让 eta 真的动 ---
  [gr0_dot]
    type = TimeDerivative
    variable = gr0
  []
  [gr1_dot]
    type = TimeDerivative
    variable = gr1
  []

  # --- 溶质：与生产同一套分裂式 CH ---
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
@COUPLED@  []
[]
[Materials]
  [params]
    type = GenericConstantMaterial
    prop_names  = 'M       kappa_c'
    prop_values = '2.8e-9  1e-14'
  []
  [free_energy]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0 gr1'
    constant_names = 'k_c c0 A_part'
    constant_expressions = '0.9 0.036 0.264'
    expression = 'k_c/2*(c-c0)^2 + A_part*c^2*(gr0^2+gr1^2)'
    derivative_order = 2
  []
[]
[Postprocessors]
  [total_c]
    type = ElementIntegralVariablePostprocessor
    variable = c
  []
[]
[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  l_max_its = 50
  l_tol = 1e-8
  nl_max_its = 20
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
  dt = 1e-3
  end_time = 2e-3
[]
[Outputs]
  csv = true
  print_linear_residuals = false
[]
"""

if __name__ == "__main__":
    d = pathlib.Path("/root/work/valid/cvtest")
    d.mkdir(parents=True, exist_ok=True)
    a = TMPL.replace("@COUPLED@", "")
    b = TMPL.replace("@COUPLED@",
                     "    coupled_variables = 'gr0 gr1'\n")
    (d / "A.i").write_text(a, encoding="utf-8")
    (d / "B.i").write_text(b, encoding="utf-8")
    print("生成 A.i（不声明）与 B.i（声明）")
