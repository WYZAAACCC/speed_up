#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1：1D **真·Gibbs 面**参考解算例生成器（面 = 点）。

物理
----
1D 里"面"是一个点。Gibbs 面的意思是：晶界有一份**面过剩量** Γ [mol/m^2]，
它不挂在任何"板宽"上。取**局域平衡**（我在 RESEARCH_INTENT_FULL §三 论证过的正确极限），
Γ = A_s(T)·c_GB，其中 A_s = Γ_0·exp(−ΔG_seg/(RT)) 是 McLean 等温线的亨利系数。

守恒 ⇒ 在宽度 w 的指示带里：
    ∂/∂t[ρ_mol·c + Γ/w] = ∇·(ρ_mol D ∇c)
⇔   (1 + A_s/(ρ_mol·w)·h_gb(x))·∂c/∂t = ∇·(D∇c)

**w → 0 时严格收敛到点面（点电容）。**
⇒ **判据：算出的 Γ 与 w 无关。** 这一条就是"它真是面、不是带"的证明。

用到的构件：`ScaledTimeDerivative`（本 app 自建，残差 = scale·du/dt·test）
用法：
  python3 make_1d_gibbs_surface.py --out gb.i --wgb 0.5e-9 --temp 1950
"""
import argparse
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gibbs_physics as GP   # noqa: E402

TEMPLATE = r"""# =============================================================================
# G1：1D Gibbs 面（面 = 点）—— 由 make_1d_gibbs_surface.py 生成，勿手改
# =============================================================================
#  T = @TEMP@ K        ΔH_seg = @DHSEG@ J/mol     A_s = Γ_0·K(T) = @AS@ mol/m2
#  晶界面指示带: 宽 w = @WGB@ m，位于 x = @XGB@ m（对准单元边界，恰好 @NELGB@ 个单元）
#  带内系数: β = 1 + A_s/(ρ_mol·w) = @BETA@
#  ρ_mol = @RHO@ mol/m3
#
#  解析预期（由总量守恒解出 c_far）：c_far = c0·L/(L + A_s/ρ_mol)
#      ⇒ Γ = A_s·c_far = @GT@ mol/m2
#  **判据：Γ 与 w 无关。**
# =============================================================================
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
  [c]
  []
[]

[ICs]
  # ⚠ 必须给瞬态驱动：均匀 c + 零通量边界时 β·∂c/∂t = ∇·(D∇c) = 0
  #   ⇒ 均匀 c 本身就是精确解，测试是空的（第一版就栽在这里）。
  #   用零均值余弦，让带内 c 随时间变 ⇒ Γ(t) 真的变化。
  [c_ic]
    type = FunctionIC
    variable = c
    function = c_init_fn
  []
[]

[Functions]
  [c_init_fn]
    type = ParsedFunction
    expression = '@C0@ + @AMP@*cos(pi*x/@LDOM@)'
  []
  # 指示带：|x - x_gb| < w/2 时为 1，否则 0（箱函数，∫h dx = w 精确）
  [gb_fn]
    type = ParsedFunction
    expression = 'if(abs(x-@XGB@) < @HALFW@, 1, 0)'
  []
[]

[AuxVariables]
  [gb_aux]
    order = CONSTANT
    family = MONOMIAL
  []
  [beta_aux]
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
  [beta_out]
    type = MaterialRealAux
    variable = beta_aux
    property = beta
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  # (1 + ASR*gb)·∂c/∂t  —— 用本 app 自建的 ScaledTimeDerivative
  [c_dt]
    type = ScaledTimeDerivative
    variable = c
    scale = beta
  []
  [c_diff]
    type = MatDiffusion
    variable = c
    diffusivity = D_eff
  []
[]

[Materials]
  [D_eff]
    type = GenericConstantMaterial
    prop_names = 'D_eff'
    prop_values = '@DS@'
  []
  # β = 1 + ASR·gb ；**必须声明 c**，否则 ScaledTimeDerivative 请求 dβ/dc 会报 "not defined"
  # （这正是 AGENTS.md §3.1 坑 1 / 教训 28 那一类：0 导数也要显式存在）
  [beta]
    type = DerivativeParsedMaterial
    property_name = beta
    coupled_variables = 'c gb_aux'
    constant_names = 'ASR'
    constant_expressions = '@ASR@'
    expression = '1 + ASR*gb_aux + 0*c'
    derivative_order = 1
  []
[]

[Postprocessors]
  [total_c]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
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
  [c_far]
    type = ElementalVariableValue
    variable = c
    elementid = 0
    execute_on = 'timestep_end'
  []
  [beta_max]
    type = ElementExtremeValue
    variable = beta_aux
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
  l_max_its = 50
  nl_max_its = 30
  nl_rel_tol = 1e-12
  nl_abs_tol = 1e-16
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
    ap.add_argument("--ldom", type=float, default=200.0e-9, help="域长 m")
    ap.add_argument("--wgb", type=float, default=0.5e-9, help="指示带宽 w m（扫 w 是核心判据）")
    ap.add_argument("--dx-over-w", type=float, default=0.25, help="dx = w * 该值（默认 4 个单元跨带）")
    ap.add_argument("--temp", type=float, default=GP.T_LPBF)
    ap.add_argument("--dh-seg", type=float, default=-11931.1, help="ΔH_seg J/mol（由锚点+δ 解出）")
    ap.add_argument("--ds-seg", type=float, default=0.0)
    ap.add_argument("--ds", type=float, default=GP.D_S)
    ap.add_argument("--t-end", type=float, default=1.0e-3)
    ap.add_argument("--n-steps", type=int, default=2000)
    ap.add_argument("--c0", type=float, default=GP.C0)
    ap.add_argument("--amp", type=float, default=1.0e-3, help="初值余弦振幅")
    args = ap.parse_args()

    dx = args.wgb * args.dx_over_w
    n = int(round(args.ldom / dx))
    nel_gb = int(round(args.wgb / dx))
    # 把带放在单元边界上：中心取在 k·dx 处
    k = n // 2
    x_gb = k * dx
    # 带 = [x_gb - w/2, x_gb + w/2]，落在单元边界上 ⇒ 整数个单元
    halfw = args.wgb / 2.0

    K = GP.K_mclean(args.temp, args.dh_seg, args.ds_seg)
    As = GP.GAMMA_MONO * K                      # Γ_0·K(T)  [mol/m2]
    rho = GP.RHO_MOL
    ASR = As / (rho * args.wgb)                 # 无量纲：A_s/(ρ_mol·w)
    beta = 1.0 + ASR
    c_far = args.c0 * args.ldom / (args.ldom + As / rho)
    G_theory = As * c_far

    txt = (TEMPLATE
           .replace("@NX@", str(n))
           .replace("@LDOM@", "%.10g" % args.ldom)
           .replace("@XGB@", "%.10g" % x_gb)
           .replace("@HALFW@", "%.10g" % halfw)
           .replace("@WGB@", "%.10g" % args.wgb)
           .replace("@NELGB@", str(nel_gb))
           .replace("@TEMP@", "%.10g" % args.temp)
           .replace("@DHSEG@", "%.10g" % args.dh_seg)
           .replace("@AS@", "%.10g" % As)
           .replace("@ASR@", "%.10g" % ASR)
           .replace("@BETA@", "%.6f" % beta)
           .replace("@RHO@", "%.6e" % rho)
           .replace("@GT@", "%.6e" % G_theory)
           .replace("@DS@", "%.10g" % args.ds)
           .replace("@C0@", "%.10g" % args.c0)
           .replace("@AMP@", "%.10g" % args.amp)
           .replace("@DT@", "%.10g" % (args.t_end / args.n_steps))
           .replace("@TEND@", "%.10g" % args.t_end))
    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit("未替换占位符 %s" % sorted(set(left)))
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        f.write(txt)

    meta = dict(T=args.temp, dH_seg=args.dh_seg, dS_seg=args.ds_seg, K=K, A_s=As,
                rho_mol=rho, wgb=args.wgb, ASR=ASR, beta=beta, dx=dx, ldom=args.ldom,
                nx=n, nel_gb=nel_gb, x_gb=x_gb, c0=args.c0, D_S=args.ds,
                t_end=args.t_end, c_far_theory=c_far, Gamma_theory=G_theory, amp=args.amp,
                Gamma_mono=GP.GAMMA_MONO)
    with open(os.path.join(os.path.dirname(os.path.abspath(args.out)), "params.json"),
              "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("写出 %s" % args.out)
    print("  T=%.1f K  ΔH_seg=%.1f  K=%.6f  A_s=%.6e mol/m2" % (args.temp, args.dh_seg, K, As))
    print("  w=%.4g m（%d 个单元）  dx=%.4g  nx=%d  域长=%.4g" % (args.wgb, nel_gb, dx, n, args.ldom))
    print("  β = 1 + A_s/(ρ_mol·w) = %.6f" % beta)
    print("  解析预期: c_far=%.10f  Γ=%.6e mol/m2  （Γ 应与 w 无关）" % (c_far, G_theory))


if __name__ == "__main__":
    main()