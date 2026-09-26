#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针 B：1D **驱动晶界**能否稳定迁移（拖曳测量的前提）。

物理
----
一个平直晶界，受一个自由能偏置 Δf 驱动 ⇒ 稳态迁移，速度 v 与 Δf 成正比。
  自由能  f(η) = mu*(η^4/4 - η^2/2) - Df*η      （Df = 0 时无驱动）
  演化    ∂η/∂t = -L*( f'(η) - κ∇²η )
⇒ 这是**有解析预期**的经典问题 ⇒ 可以做正对照。

判据
----
  P1  Df = 0 ⇒ 界面**不动**（正对照）
  P2  Df ≠ 0 ⇒ v 恒定（稳态迁移，不是减速/加速）
  P3  v ∝ Df（线性）—— 比例常数与 L 标定
  P4  界面形状不变（传播波）

有了这个，才能"加溶质 ⇒ 量 v 的下降 ⇒ 反解拖曳系数"。
"""
import argparse, json, os, re, sys

TEMPLATE = r"""# 探针 B：驱动晶界稳态迁移
#  Df = @DF@   L = @LMOB@   kappa = @KAP@   mu = @MU@
#  域长 @LDOM@ m，nx = @NX@，dx = @DX@
#  界面初始位 x = @XI0@
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 1
    nx = @NX@
    xmin = 0
    xmax = @LDOM@
  []
[]

[Variables]
  [eta]
  []
[]

[ICs]
  [eta_ic]
    type = FunctionIC
    variable = eta
    function = eta_init
  []
[]

[Functions]
  [eta_init]
    type = ParsedFunction
    expression = 'tanh((x-@XI0@)/@WINT@)'
  []
[]

[AuxVariables]
  [chiB]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [chiB_k]
    type = ParsedAux
    variable = chiB
    coupled_variables = 'eta'
    expression = '(1-eta)/2'
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  [eta_dt]
    type = TimeDerivative
    variable = eta
  []
  # 残差 = L*f'(η)*test
  [eta_bulk]
    type = AllenCahn
    variable = eta
    f_name = f_loc
    mob_name = Lmob
  []
  # 残差 = L*κ*∇η·∇test
  [eta_iface]
    type = ACInterface
    variable = eta
    mob_name = Lmob
    kappa_name = kappa
  []
[]

[Materials]
  # f = mu*(η⁴/4 − η²/2) − Df·η
  # ⚠ 把 eta 字面写进表达式（教训 28）；derivative_order=1 足够（AllenCahn 只要一阶）
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'eta'
    constant_names = 'mu Df'
    constant_expressions = '@MU@ @DF@'
    expression = 'mu*(eta^4/4 - eta^2/2) - Df*eta'
    derivative_order = 1
  []
  # ⚠ ACInterface 无条件索取 L 与 kappa 的二阶材料导数（AGENTS.md §3.1 坑 2）
  #   用 DerivativeParsedMaterial + 0*eta 让那些导数**显式存在**，避免静默取 0
  [Lmob]
    type = DerivativeParsedMaterial
    property_name = Lmob
    coupled_variables = 'eta'
    constant_names = 'L0'
    constant_expressions = '@LMOB@'
    expression = 'L0 + 0*eta'
    derivative_order = 2
  []
  [kappa]
    type = DerivativeParsedMaterial
    property_name = kappa
    coupled_variables = 'eta'
    constant_names = 'K0'
    constant_expressions = '@KAP@'
    expression = 'K0 + 0*eta'
    derivative_order = 2
  []
[]

[Postprocessors]
  # 晶界位置 = L * ∫chiB dx ；速度 = d(x_I)/dt
  [fracB]
    type = ElementIntegralVariablePostprocessor
    variable = chiB
    execute_on = 'initial timestep_end'
  []
  [xI]
    type = ParsedPostprocessor
    expression = '@LDOM@ * fracB'
    pp_names = 'fracB'
    execute_on = 'timestep_end'
  []
  [eta_max]
    type = NodalExtremeValue
    variable = eta
    value_type = max
    execute_on = 'timestep_end'
  []
  [eta_min]
    type = NodalExtremeValue
    variable = eta
    value_type = min
    execute_on = 'timestep_end'
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-14
  dt = @DT@
  end_time = @TEND@
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = @DT@
    growth_factor = 1.2
    cutback_factor = 0.5
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  print_linear_residuals = false
[]
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ldom", type=float, default=40.0e-9)
    ap.add_argument("--nx", type=int, default=320)
    ap.add_argument("--wint", type=float, default=1.0e-9, help="界面宽 w")
    ap.add_argument("--df", type=float, default=0.0, help="驱动偏置 Δf [J/m^3]")
    ap.add_argument("--l-mob", type=float, default=1.0e-9, help="迁移率 L")
    ap.add_argument("--kappa", type=float, default=1.0e-9)
    ap.add_argument("--mu", type=float, default=1.0e6)
    ap.add_argument("--t-end", type=float, default=1.0e-6)
    ap.add_argument("--n-steps", type=int, default=4000)
    args = ap.parse_args()
    dx = args.ldom / args.nx
    xi0 = args.ldom / 2.0
    txt = (TEMPLATE
           .replace("@NX@", str(args.nx)).replace("@LDOM@", "%.10g" % args.ldom)
           .replace("@DX@", "%.10g" % dx).replace("@XI0@", "%.10g" % xi0)
           .replace("@WINT@", "%.10g" % args.wint)
           .replace("@DF@", "%.10g" % args.df)
           .replace("@LMOB@", "%.10g" % args.l_mob)
           .replace("@KAP@", "%.10g" % args.kappa)
           .replace("@MU@", "%.10g" % args.mu)
           .replace("@DT@", "%.10g" % (args.t_end / args.n_steps))
           .replace("@TEND@", "%.10g" % args.t_end))
    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit("未替换 %s" % sorted(set(left)))
    open(args.out, "w", encoding="utf-8", newline="").write(txt)
    json.dump(dict(ldom=args.ldom, nx=args.nx, dx=dx, wint=args.wint, df=args.df,
                   L=args.l_mob, kappa=args.kappa, mu=args.mu,
                   t_end=args.t_end, xi0=xi0, w_dx=args.wint / dx),
              open(os.path.join(os.path.dirname(os.path.abspath(args.out)), "params.json"),
                   "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("写出 %s  (wx/dx=%.2f, Df=%.3g)" % (args.out, args.wint / dx, args.df))


if __name__ == "__main__":
    main()