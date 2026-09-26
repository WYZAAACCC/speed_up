#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1-2D：晶界**面电导 δ·D_GB** 的二维参考解（Fisher 型：解析出的 GB 板）。

要测的物理
----------
文献里的「晶界扩散三重积」s·δ·D_GB。本算例测最基础的一支：**δ·D_GB**。

几何：2D，竖直晶界（宽 δ，**按物理宽度解析**），两侧晶粒（D_S）。
驱动：沿 y 加浓度差（沿晶界方向），x 两侧零通量。
稳态总通量（单位厚度）：
    j = (Δc/Ly)·[ D_S·(W−δ) + D_GB·δ ]
⇒ **增强比**  R = j / (D_S·Δc/Ly·W) = 1 + (D_GB−D_S)·δ/(D_S·W)

⇒ R 的实测值直接给出 δ·D_GB。这就是判据。

⚠ 本算例是"**子模型/真值源**"：域是 nm 尺度的，晶界是解析的。
   它同时是 P2（"贵"）的实测对象 —— 后续会测它的成本。
用法： python3 make_2d_gb_slab.py --out gb2d.i
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gibbs_physics as GP   # noqa: E402

TEMPLATE = r"""# =============================================================================
# G1-2D：晶界面电导 δ·D_GB 的二维参考解 —— 自动生成，勿手改
# =============================================================================
#  域 @LX@ × @LY@ m   dx=dy=@DX@ m   nx=@NX@ ny=@NY@
#  晶界：x = @XGB@ m 处、宽 δ = @DELTA@ m（@NELGB@ 个单元，δ/dx = @RES@）
#  D_S = @DS@   D_GB = @DGB@
#  解析增强比 R = 1 + (D_GB−D_S)·δ/(D_S·W) = @RTHEORY@
#  ⇒ 实测 R 应 = @RTHEORY@；反解 δ·D_GB 看是否 = @TRIPLE@ m^3/s
# =============================================================================
[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 2
    nx = @NX@
    ny = @NY@
    xmin = 0
    xmax = @LX@
    ymin = 0
    ymax = @LY@
    elem_type = QUAD4
  []
[]

[Variables]
  [c]
  []
[]

[Functions]
  # 晶界指示：|x − x_gb| < δ/2 时为 1（Δc 箱）
  [gb_fn]
    type = ParsedFunction
    expression = 'if(abs(x-@XGB@) < @HALFD@, 1, 0)'
  []
  # 初值给沿 y 的线性剖面 ⇒ 更快到稳态
  [c_init_fn]
    type = ParsedFunction
    expression = '@C0@ + (@CHI@-@CLO@)*(1 - y/@LY@) - (@CHI@-@C0@)'
  []
[]

[AuxVariables]
  [gb_aux]
    order = CONSTANT
    family = MONOMIAL
  []
  [D_aux]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [gb_out]
    type = FunctionAux
    variable = gb_aux
    function = gb_fn
    execute_on = 'initial timestep_end'
  []
  [D_out]
    type = MaterialRealAux
    variable = D_aux
    property = D_eff
    execute_on = 'initial timestep_end'
  []
[]

[ICs]
  [c_ic]
    type = FunctionIC
    variable = c
    function = c_init_fn
  []
[]

[Kernels]
  [c_dt]
    type = TimeDerivative
    variable = c
  []
  [c_diff]
    type = MatDiffusion
    variable = c
    diffusivity = D_eff
  []
[]

[Materials]
  # D_eff = D_S + (D_GB − D_S)·h_gb(x)
  [D_eff]
    type = DerivativeParsedMaterial
    property_name = D_eff
    coupled_variables = 'c gb_aux'
    constant_names = 'DS DGB'
    constant_expressions = '@DS@ @DGB@'
    expression = 'DS + (DGB-DS)*gb_aux + 0*c'
    derivative_order = 1
  []
[]

[BCs]
  [top]
    type = DirichletBC
    variable = c
    boundary = top
    value = @CLO@
  []
  [bottom]
    type = DirichletBC
    variable = c
    boundary = bottom
    value = @CHI@
  []
[]

[Postprocessors]
  # 进入域的总通量（沿 y）—— 稳态时等于全场的沿 y 通量
  [flux_in]
    type = SideFluxIntegral
    variable = c
    boundary = bottom
    diffusivity = D_eff
  []
  [flux_out]
    type = SideFluxIntegral
    variable = c
    boundary = top
    diffusivity = D_eff
  []
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    execute_on = 'timestep_end'
  []
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    execute_on = 'timestep_end'
  []
  [D_min]
    type = ElementExtremeValue
    variable = D_aux
    value_type = min
    execute_on = 'initial timestep_end'
  []
  [D_max]
    type = ElementExtremeValue
    variable = D_aux
    value_type = max
    execute_on = 'initial timestep_end'
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-18
  dt = @DT@
  end_time = @TEND@
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = @DT@
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 8
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
    ap.add_argument("--lx", type=float, default=10.0e-9)
    ap.add_argument("--ly", type=float, default=25.0e-9)
    ap.add_argument("--delta", type=float, default=0.5e-9, help="晶界物理宽度 m")
    ap.add_argument("--res", type=float, default=4.0, help="δ/dx")
    ap.add_argument("--ds", type=float, default=GP.D_S)
    ap.add_argument("--dgb", type=float, default=GP.D_GB)
    ap.add_argument("--c0", type=float, default=GP.C0)
    ap.add_argument("--c-hi", type=float, default=GP.C0 + 2.0e-3)
    ap.add_argument("--c-lo", type=float, default=GP.C0 - 2.0e-3)
    ap.add_argument("--t-end", type=float, default=1.0e-4)
    ap.add_argument("--n-steps", type=int, default=4000)
    args = ap.parse_args()

    dx = args.delta / args.res
    nx = int(round(args.lx / dx))
    ny = int(round(args.ly / dx))
    nel_gb = int(round(args.delta / dx))
    # 晶界放在单元边界上
    k = nx // 2
    x_gb = k * dx
    W = args.lx
    # 解析增强比
    R = 1.0 + (args.dgb - args.ds) * args.delta / (args.ds * W)
    triple = args.delta * args.dgb     # δ·D_GB [m^3/s]
    # 稳态特征时间（沿 y 的体扩散）：Ly^2/D_S
    t_ss = args.ly**2 / args.ds

    txt = (TEMPLATE
           .replace("@NX@", str(nx)).replace("@NY@", str(ny))
           .replace("@LX@", "%.10g" % args.lx).replace("@LY@", "%.10g" % args.ly)
           .replace("@DX@", "%.10g" % dx)
           .replace("@XGB@", "%.10g" % x_gb)
           .replace("@DELTA@", "%.10g" % args.delta)
           .replace("@HALFD@", "%.10g" % (args.delta / 2.0))
           .replace("@NELGB@", str(nel_gb)).replace("@RES@", "%.1f" % args.res)
           .replace("@DS@", "%.10g" % args.ds).replace("@DGB@", "%.10g" % args.dgb)
           .replace("@C0@", "%.10g" % args.c0)
           .replace("@CHI@", "%.10g" % args.c_hi).replace("@CLO@", "%.10g" % args.c_lo)
           .replace("@RTHEORY@", "%.6f" % R).replace("@TRIPLE@", "%.6e" % triple)
           .replace("@DT@", "%.10g" % (args.t_end / args.n_steps))
           .replace("@TEND@", "%.10g" % args.t_end))
    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit("未替换 %s" % sorted(set(left)))
    open(args.out, "w", encoding="utf-8", newline="").write(txt)

    meta = dict(lx=args.lx, ly=args.ly, dx=dx, nx=nx, ny=ny, nel_gb=nel_gb, x_gb=x_gb,
                delta=args.delta, res=args.res, D_S=args.ds, D_GB=args.dgb,
                c0=args.c0, c_hi=args.c_hi, c_lo=args.c_lo, W=W,
                R_theory=R, triple_theory=triple, t_ss=t_ss, t_end=args.t_end,
                ncell=nx * ny)
    json.dump(meta, open(os.path.join(os.path.dirname(os.path.abspath(args.out)),
                                      "params.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print("写出 %s" % args.out)
    print("  域 %.3g × %.3g m   nx=ny=%d/%d  单元 %d" % (args.lx, args.ly, nx, ny, nx*ny))
    print("  δ=%.3g m（%d 单元，δ/dx=%.1f）  x_gb=%.6g" % (args.delta, nel_gb, args.res, x_gb))
    print("  D_S=%.3g  D_GB=%.3g  ⇒ 解析增强比 R = %.4f" % (args.ds, args.dgb, R))
    print("  ⇒ 反解 δ·D_GB(解析) = %.4e m^3/s" % triple)
    print("  ⚠ 稳态特征时间 Ly²/D_S = %.3g s（t_end=%.3g）" % (t_ss, args.t_end))


if __name__ == "__main__":
    main()