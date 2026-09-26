#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1D 晶界 **Gibbs 面模型** 算例生成器（低维 Γ 状态量）。

与 make_1d_gb_gibbs.py 的区别
--------------------------------
前者仍是**弥散**表示：Γ 是自由能里偏析阱的副产品，于是
    Γ = ρ_mol · wGB · A(s)     ⇒ **Γ ∝ wGB**
要 Γ 对上文献就必须让 A 变小，而 A 小时 s→1 —— 弥散表示**无法同时对 s 和 Γ**。

本算例把 Γ 升格为**独立的低维状态量**（单位 mol/m²，不再挂在 wGB 上）：

    体相:   ∂c/∂t = ∇·(D∇c) − shape(x)·∂Γ/∂t
    晶界:   ∂Γ/∂t = h_gb·k_att·( Γ_eq(c,T) − Γ )
    等温线: Γ_eq = Γ_0·K(T)·c        （Henry 极限；Langmuir 位点竞争修正在 c=0.036 处 ~4~12%）
    形状:   shape(x) = h_gb/(∫h_gb dx) = h_gb/((4/3)·wGB),  ∫shape dx = 1

⇒ 关键性质：**Γ 与 wGB 无关**（wGB 只影响 shape 的分布，不影响总量）。
   这正是弥散表示做不到的那件事。

MOOSE 实现（**全部现成非 AD 对象，雅可比精确**）
-----------------------------------------------
把 Γ 的方程代回体相源项，消掉对 dΓ/dt 的显式引用：
    体相源 = −shape·h_gb·k_att·(Γ_eq − Γ)
           = −shape·h_gb·k_att·A_s·c + shape·h_gb·k_att·Γ
⇒ 两项都是 `MatReaction`（残差 = −rate·v）。所有 rate 只依赖 T 与 η（AuxVariable），
   与 c/Γ 无关 ⇒ MatReaction 的 Jacobian 只用到 rate 本身，**不需要 rate 的导数**，
   而且关掉了 AD material 的依赖。

⚠ 若要 Γ_eq 用完整 Langmuir（非线性），rate 会依赖 c，需要新核 —— 见 PHYSICS_CLOSURE.md。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gibbs_physics as GP   # noqa: E402

TEMPLATE = r"""# =============================================================================
# 1D 晶界 **Gibbs 面模型**（Γ 为独立低维状态量）—— 自动生成，勿手改
# =============================================================================
#  T = @TEMP@ K    ΔH_seg = @DHSEG@ J/mol    ΔS_seg = @DSSEG@ J/mol/K
#  Γ_0 = @GAM0@ mol/m2   K(T) = @KT@   A_s = Γ_0*K = @AS@ mol/m2
#  k_att = @KATT@ 1/s     wgb(只影响 shape 分布) = @WGB@ m
#  预期平衡: Γ_eq = A_s*c_far = @G_EQ@ mol/m2   （与 wgb **无关**）
#  ⚠ 弥散表示在同一 wgb 下只能给 Γ = rho_mol*wgb*A(s)，见 PHYSICS_CLOSURE.md
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
    initial_condition = @C_IC@
  []
  [Gam]
    initial_condition = @G_EQ@
  []
[]

[Functions]
  [eta0_fn]
    type = ParsedFunction
    expression = '0.5*(1-tanh((x-@XGB@)/@WGB@))'
  []
  [eta1_fn]
    type = ParsedFunction
    expression = '0.5*(1+tanh((x-@XGB@)/@WGB@))'
  []
[]

[AuxVariables]
  [eta0]
  []
  [eta1]
  []
  [hgb_aux]
    order = CONSTANT
    family = MONOMIAL
  []
  [D_aux]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [eta0_fix]
    type = FunctionAux
    variable = eta0
    function = eta0_fn
    execute_on = 'initial timestep_end'
  []
  [eta1_fix]
    type = FunctionAux
    variable = eta1
    function = eta1_fn
    execute_on = 'initial timestep_end'
  []
  [hgb_out]
    type = MaterialRealAux
    variable = hgb_aux
    property = h_gb
    execute_on = 'initial timestep_end'
  []
  [D_out]
    type = MaterialRealAux
    variable = D_aux
    property = D_eff
    execute_on = 'initial timestep_end'
  []
[]

[Kernels]
  # ---------------- 体相 c ----------------
  [c_dt]
    type = TimeDerivative
    variable = c
  []
  [c_diff]
    type = MatDiffusion
    variable = c
    diffusivity = D_eff
  []
  # ∂c/∂t = ∇·(D∇c) − shape*∂Γ/∂t ，代回 ∂Γ/∂t = h_gb*k_att*(A_s*c − Γ)：
  #   + shape*h_gb*k_att*A_s*c     -> rate = -shape*h_gb*k_att*A_s,  v = c
  #   − shape*h_gb*k_att*Γ         -> rate = +shape*h_gb*k_att,      v = Gam
  [c_src_c]
    type = MatReaction
    variable = c
    reaction_rate = neg_shape_hgb_katt_As
  []
  [c_src_gam]
    type = MatReaction
    variable = c
    v = Gam
    reaction_rate = shape_hgb_katt
  []
  # ---------------- 晶界 Γ ----------------
  [gam_dt]
    type = TimeDerivative
    variable = Gam
  []
  # dΓ/dt − h_gb*k_att*A_s*c + h_gb*k_att*Γ = 0
  [gam_eq]
    type = MatReaction
    variable = Gam
    v = c
    reaction_rate = hgb_katt_As
  []
  [gam_relax]
    type = MatReaction
    variable = Gam
    reaction_rate = neg_hgb_katt
  []
[]

[Materials]
  # --- 晶界指示 h_gb = 8(S^2-Q) = sech^4，峰值 1，∫h_gb dx = (4/3)*wgb ---
  [hgb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'eta0 eta1'
    expression = '8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))'
    derivative_order = 2
  []
  [hsolid]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'eta0 eta1'
    expression = 'min(1, 2*(eta0^2+eta1^2))'
    derivative_order = 2
  []
  # D_eff = D_L + (D_S-D_L)h_solid + (D_GB-D_S)h_gb  （物理分层，逐点精确）
  [D_eff]
    type = DerivativeParsedMaterial
    property_name = D_eff
    coupled_variables = 'eta0 eta1'
    constant_names = 'DL DS DGB'
    constant_expressions = '@DL@ @DS@ @DGB@'
    expression = 'DL + (DS-DL)*min(1, 2*(eta0^2+eta1^2))
                     + (DGB-DS)*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))'
    derivative_order = 2
  []
  # shape = h_gb/((4/3)*wgb)   [1/m]   ∫shape dx = 1
  [shape]
    type = DerivativeParsedMaterial
    property_name = shape
    coupled_variables = 'eta0 eta1'
    constant_names = 'HINT'
    constant_expressions = '@HINT@'
    expression = '8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))/HINT'
    derivative_order = 2
  []
  # --- 四个 rate（只依赖常数与 eta ⇒ 不含 c/Γ，Jacobian 精确）---
  [hgb_katt_As]
    type = DerivativeParsedMaterial
    property_name = hgb_katt_As
    coupled_variables = 'eta0 eta1'
    constant_names = 'KATT AS'
    constant_expressions = '@KATT@ @AS@'
    expression = 'KATT*AS*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))'
    derivative_order = 2
  []
  [hgb_katt]
    type = DerivativeParsedMaterial
    property_name = hgb_katt
    coupled_variables = 'eta0 eta1'
    constant_names = 'KATT'
    constant_expressions = '@KATT@'
    expression = 'KATT*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))'
    derivative_order = 2
  []
  [neg_hgb_katt]
    type = DerivativeParsedMaterial
    property_name = neg_hgb_katt
    coupled_variables = 'eta0 eta1'
    constant_names = 'KATT'
    constant_expressions = '@KATT@'
    expression = '-KATT*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))'
    derivative_order = 2
  []
  [shape_hgb_katt]
    type = DerivativeParsedMaterial
    property_name = shape_hgb_katt
    coupled_variables = 'eta0 eta1'
    constant_names = 'KATT HINT'
    constant_expressions = '@KATT@ @HINT@'
    expression = 'KATT*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))^2/HINT'
    derivative_order = 2
  []
  [neg_shape_hgb_katt_As]
    type = DerivativeParsedMaterial
    property_name = neg_shape_hgb_katt_As
    coupled_variables = 'eta0 eta1'
    constant_names = 'KATT AS HINT'
    constant_expressions = '@KATT@ @AS@ @HINT@'
    expression = '-KATT*AS*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))^2/HINT'
    derivative_order = 2
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
  [c_edge]
    type = ElementalVariableValue
    variable = c
    elementid = 0
    execute_on = 'timestep_end'
  []
  # Γ 的读数：取晶界单元的 Gam
  [gam_gb]
    type = ElementalVariableValue
    variable = Gam
    elementid = @IEL_GB@
    execute_on = 'timestep_end'
  []
  # 总溶质（含 Γ 的贡献）：∫c dx + Γ —— 用于守恒检查
  [gam_int]
    type = ElementIntegralVariablePostprocessor
    variable = Gam
    execute_on = 'timestep_end'
  []
  [hgb_max]
    type = ElementExtremeValue
    variable = hgb_aux
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
  l_tol = 1e-8
  nl_max_its = 40
  nl_rel_tol = 1e-11
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
    ap.add_argument("--dx", type=float, default=0.0625e-9)
    ap.add_argument("--ldom", type=float, default=200.0e-9)
    ap.add_argument("--wgb", type=float, default=None)
    ap.add_argument("--temp", type=float, default=GP.T_LPBF)
    ap.add_argument("--dh-seg", type=float, default=None)
    ap.add_argument("--ds-seg", type=float, default=0.0)
    ap.add_argument("--delta-gb", type=float, default=GP.DELTA_GB)
    ap.add_argument("--katt", type=float, default=1.0e6, help="附着速率 1/s")
    ap.add_argument("--dl", type=float, default=GP.D_L)
    ap.add_argument("--ds", type=float, default=GP.D_S)
    ap.add_argument("--dgb", type=float, default=GP.D_GB)
    ap.add_argument("--t-end", type=float, default=1.0e-4)
    ap.add_argument("--n-steps", type=int, default=2000)
    ap.add_argument("--c0", type=float, default=GP.C0)
    args = ap.parse_args()

    wgb = args.wgb if args.wgb is not None else 0.75 * args.delta_gb
    H = args.dh_seg if args.dh_seg is not None else GP.dH_seg_from_anchor_delta(
        delta=args.delta_gb, dS_seg=args.ds_seg)
    dG = GP.dG_seg(args.temp, H, args.ds_seg)
    K = GP.K_mclean(args.temp, H, args.ds_seg)
    As = GP.GAMMA_MONO * K                 # Henry 系数 [mol/m2 per unit c]
    G_eq = As * args.c0
    G_lang = GP.gamma_eq_langmuir(args.c0, args.temp, H, args.ds_seg)

    n = int(round(args.ldom / args.dx))
    iel_gb = n // 2
    x_gb = (iel_gb + 0.5) * args.dx
    hint = (4.0 / 3.0) * wgb               # ∫h_gb dx

    txt = (TEMPLATE
           .replace("@NX@", str(n))
           .replace("@LDOM@", "%.10g" % args.ldom)
           .replace("@WGB@", "%.10g" % wgb)
           .replace("@XGB@", "%.10g" % x_gb)
           .replace("@TEMP@", "%.10g" % args.temp)
           .replace("@DHSEG@", "%.10g" % H)
           .replace("@DSSEG@", "%.10g" % args.ds_seg)
           .replace("@GAM0@", "%.10g" % GP.GAMMA_MONO)
           .replace("@KT@", "%.10g" % K)
           .replace("@AS@", "%.10g" % As)
           .replace("@KATT@", "%.10g" % args.katt)
           .replace("@G_EQ@", "%.10g" % G_eq)
           .replace("@HINT@", "%.10g" % hint)
           .replace("@DL@", "%.10g" % args.dl)
           .replace("@DS@", "%.10g" % args.ds)
           .replace("@DGB@", "%.10g" % args.dgb)
           .replace("@C_IC@", "%.10g" % args.c0)
           .replace("@IEL_GB@", str(iel_gb))
           .replace("@DT@", "%.10g" % (args.t_end / args.n_steps))
           .replace("@TEND@", "%.10g" % args.t_end))
    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit("错误：未替换占位符 %s" % sorted(set(left)))
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        f.write(txt)

    meta = dict(T=args.temp, T_ref=GP.T_REF, dH_seg=H, dS_seg=args.ds_seg,
                dG_seg=dG, K=K, A_s=As, k_att=args.katt, wgb=wgb,
                dx=args.dx, ldom=args.ldom, nx=n, int_hgb=hint,
                c0=args.c0, t_end=args.t_end, delta_gb=args.delta_gb,
                D_L=args.dl, D_S=args.ds, D_GB=args.dgb,
                Gamma_eq_henry=G_eq, Gamma_eq_langmuir=G_lang,
                Gamma_mono=GP.GAMMA_MONO, rho_mol=GP.RHO_MOL)
    with open(os.path.join(os.path.dirname(os.path.abspath(args.out)), "params.json"),
              "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("写出 %s" % args.out)
    print("  T=%.1f K  ΔH_seg=%.1f  K=%.6f  A_s=%.6e mol/m2  k_att=%.3g 1/s"
          % (args.temp, H, K, As, args.katt))
    print("  网格 nx=%d dx=%.4g 域长 %.4g  wgb=%.4g (∫h_gb=%.4g)" %
          (n, args.dx, args.ldom, wgb, hint))
    print("  ⇒ 预期平衡 Γ = A_s*c0 = %.6e mol/m2  （Henry）" % G_eq)
    print("                      = %.6e mol/m2  （完整 Langmuir，作对照）" % G_lang)
    print("  ⚠ 关键判据：Γ 应与 wgb **无关**（这是弥散表示做不到的）")


if __name__ == "__main__":
    main()