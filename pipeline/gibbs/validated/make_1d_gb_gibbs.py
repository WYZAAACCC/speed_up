#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1D 晶界 Gibbs 模型算例生成器。

与生产（以及 pipeline/validated/make_1d_gb.py）的关键区别
------------------------------------------------------------------
生产把晶界当成"一块 4 µm 的弥散板"，偏析强度由一个**无量纲常数 Ω₀** 定：
    f_loc = k_c/2(c−c₀)² + A_part·c²·min(1,2S) + (Ω₀/wgb)(c−c₀)·h_gb
⇒ 后果（已实测）：① 自由能不具物理量纲（k_c=0.9 vs 真实 f_cc≈4.7e10 J/m³，
   差 10 个数量级）；② **没有温度依赖**；③ 偏析强度由**板宽**而非**材料量**定。

本生成器改用**物理量纲**的自由能：

    f_loc/f_ref = τ·[c·ln c + (1−c)·ln(1−c)]           理想溶液（⇒ 精确 McLean）
                + (Δμ°_LS/(R·T_ref))·c·(1−h_solid)       固/液分配 ⇒ k(T)
                + (ΔG_seg(T)/(R·T_ref))·(c−c₀)·h_gb      晶界偏析 ⇒ McLean

其中 f_ref = R·T_ref/v_m，τ = T/T_ref，ΔG_seg(T) = ΔH_seg − T·ΔS_seg。

⇒ 平衡条件 df/dc = μ **逐点**给出 Cahn 1962 / McLean 等温线：
      c(x)/(1−c(x)) = (c_far/(1−c_far))·exp(−ΔG_seg·h_gb(x)/(R·T))
⇒ **峰的富集比 s 与 wgb、与 κ_c 都无关**（只由材料量 ΔG_seg 和 T 定）。
   这正是"物理闭合"的判据。

⚠ 教训 28：DerivativeParsedMaterial 只对**字面出现**的变量发射导数
  ⇒ 本生成器把 S / Q / h_gb / h_solid 全部**内联**进 f_loc 与 M 的表达式，
    不经过 material_property_names。

⚠ MOOSE 里自然对数是 `log()`，**没有 `ln()`**（已用最小探针实测，含正对照）。

用法：
  python3 make_1d_gb_gibbs.py --out gb.i --temp 1950
  python3 make_1d_gb_gibbs.py --out gb.i --wgb 0.5e-9 --dx 0.0625e-9 --ldom 200e-9
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gibbs_physics as GP   # noqa: E402

TEMPLATE = r"""# =============================================================================
# 1D 晶界 Gibbs 模型 —— 由 make_1d_gb_gibbs.py 自动生成，请勿手改
# =============================================================================
#   T        = @TEMP@ K          （T_ref = @TREF@ K 只做无量纲化）
#   ΔH_seg   = @DHSEG@ J/mol     @DHNOTE@
#   ΔS_seg   = @DSSEG@ J/mol/K
#   ΔG_seg(T)= @DGSEG@ J/mol
#   系数     : tau = @TAU@   part = @PART@   seg = @SEG@      (f_ref = @FREF@ J/m3)
#   预期 McLean 峰: c_GB = @CGB_ANA@   s = @S_ANA@
#   Γ 目标（物理）  : @GAMMA_TARGET@ mol/m2
#   晶界宽 wgb = @WGB@ m，域长 @LDOM@ m，dx = @DX@ m，nx = @NX@
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
  [w]
    initial_condition = 0
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
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
    coupled_variables = 'eta0 eta1'
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
    coupled_variables = 'eta0 eta1'
  []
[]

[Materials]
  [ch_kappa]
    type = GenericConstantMaterial
    prop_names = 'kappa_c'
    prop_values = '@KAPPA_C@'
  []

  # --- 晶界指示 h_gb（与生产同一个函数，但**内联**，见教训 28）---
  #     S = eta0^2+eta1^2, Q = eta0^4+eta1^4, h_gb = 8(S^2-Q) = sech^4  (峰值 1)
  [hgb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'eta0 eta1'
    expression = '8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4))'
    derivative_order = 2
  []

  # --- 固相指示 h_solid = min(1, 2S)（二元固固晶界上恒等于 1）---
  [hsolid]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'eta0 eta1'
    expression = 'min(1, 2*(eta0^2+eta1^2))'
    derivative_order = 2
  []

  # --- 溶质自由能（**物理量纲**，无量纲化后数值 O(1)）---
  #     f_loc/f_ref = tau*[c*log(c)+(1-c)*log(1-c)] + part*c*(1-h_solid) + seg*(c-c0)*h_gb
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c eta0 eta1'
    constant_names = 'FREF TAU PART SEG C0'
    constant_expressions = '@FREF@ @TAU@ @PART@ @SEG@ @C0@'
    expression = 'FREF*( TAU*(c*log(c)+(1-c)*log(1-c))
                        + PART*c*(1-min(1, 2*(eta0^2+eta1^2)))
                        + SEG*(c-C0)*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4)) )'
    derivative_order = 2
  []

  # --- 分层扩散系数 D_eff = D_L + (D_S-D_L)h_solid + (D_GB-D_S)h_gb ---
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

  # --- 迁移率 M = D_eff / f_cc，f_cc = f_ref*tau/(c(1-c))  ---
  #     ⇒ 由构造保证 D = M*f_cc **逐点精确成立**（物理量纲）
  [M]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'c eta0 eta1'
    constant_names = 'FREF TAU DL DS DGB'
    constant_expressions = '@FREF@ @TAU@ @DL@ @DS@ @DGB@'
    expression = '(DL + (DS-DL)*min(1, 2*(eta0^2+eta1^2))
                      + (DGB-DS)*8*((eta0^2+eta1^2)^2 - (eta0^4+eta1^4)))
                  / (FREF*TAU/(c*(1-c)))'
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
  [hgb_max]
    type = ElementExtremeValue
    variable = hgb_aux
    value_type = max
    execute_on = 'initial timestep_end'
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
  l_max_its = 50
  l_tol = 1e-8
  nl_max_its = 40
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-14
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
    ap.add_argument("--dx", type=float, default=0.0625e-9, help="网格间距 m")
    ap.add_argument("--ldom", type=float, default=200.0e-9, help="域长 m")
    ap.add_argument("--wgb", type=float, default=None,
                    help="晶界剖面宽 m（默认 0.75*DELTA_GB 使 ∫h_gb dx = δ_GB）")
    ap.add_argument("--temp", type=float, default=GP.T_LPBF, help="温度 K")
    ap.add_argument("--t-ref", type=float, default=GP.T_REF, help="无量纲化参考温度 K")
    ap.add_argument("--dh-seg", type=float, default=None, help="ΔH_seg J/mol（默认由锚点解出）")
    ap.add_argument("--ds-seg", type=float, default=0.0, help="ΔS_seg J/mol/K")
    ap.add_argument("--delta-gb", type=float, default=GP.DELTA_GB, help="晶界结构厚度 δ m")
    ap.add_argument("--kc", type=float, default=1.0e-10)
    ap.add_argument("--dl", type=float, default=GP.D_L)
    ap.add_argument("--ds", type=float, default=GP.D_S)
    ap.add_argument("--dgb", type=float, default=GP.D_GB)
    ap.add_argument("--t-end", type=float, default=1.0e-4)
    ap.add_argument("--n-steps", type=int, default=2000)
    ap.add_argument("--c0", type=float, default=GP.C0)
    args = ap.parse_args()

    wgb = args.wgb if args.wgb is not None else 0.75 * args.delta_gb

    # --- 偏析焓：默认由锚点 + 结构厚度 δ 解出（见 gibbs_physics）---
    if args.dh_seg is None:
        H = GP.dH_seg_from_anchor_delta(delta=args.delta_gb,
                                        dS_seg=args.ds_seg)
        dh_note = "由 Tan 2016 锚点 + δ_GB=%.3g m 解出" % args.delta_gb
    else:
        H = args.dh_seg
        dh_note = "命令行指定"

    dG = GP.dG_seg(args.temp, H, args.ds_seg)
    co = GP.coeffs(args.temp, H, args.ds_seg, args.t_ref)

    n = int(round(args.ldom / args.dx))
    iel_gb = n // 2
    x_gb = (iel_gb + 0.5) * args.dx          # 对准单元质心（h_gb/D 是单元常量）

    c_ana = GP.cGB_from_cfar(args.c0, args.temp, H, args.ds_seg)
    s_ana = c_ana / args.c0
    gamma_target = GP.gamma_eq_langmuir(args.c0, args.temp, H, args.ds_seg)

    txt = (TEMPLATE
           .replace("@NX@", str(n))
           .replace("@LDOM@", "%.10g" % args.ldom)
           .replace("@DX@", "%.10g" % args.dx)
           .replace("@WGB@", "%.10g" % wgb)
           .replace("@XGB@", "%.10g" % x_gb)
           .replace("@TEMP@", "%.10g" % args.temp)
           .replace("@TREF@", "%.10g" % args.t_ref)
           .replace("@DHSEG@", "%.10g" % H)
           .replace("@DHNOTE@", dh_note)
           .replace("@DSSEG@", "%.10g" % args.ds_seg)
           .replace("@DGSEG@", "%.10g" % dG)
           .replace("@FREF@", "%.10g" % GP.f_ref(args.t_ref))
           .replace("@TAU@", "%.10g" % co["tau"])
           .replace("@PART@", "%.10g" % co["part"])
           .replace("@SEG@", "%.10g" % co["seg"])
           .replace("@C0@", "%.10g" % args.c0)
           .replace("@CGB_ANA@", "%.10g" % c_ana)
           .replace("@S_ANA@", "%.10g" % s_ana)
           .replace("@GAMMA_TARGET@", "%.6e" % gamma_target)
           .replace("@KAPPA_C@", "%.10g" % args.kc)
           .replace("@DL@", "%.10g" % args.dl)
           .replace("@DS@", "%.10g" % args.ds)
           .replace("@DGB@", "%.10g" % args.dgb)
           .replace("@C_IC@", "%.10g" % args.c0)
           .replace("@DT@", "%.10g" % (args.t_end / args.n_steps))
           .replace("@TEND@", "%.10g" % args.t_end))

    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit("错误：还有未替换的占位符 %s" % sorted(set(left)))

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        f.write(txt)

    # 同时写一份 params.json —— 让分析脚本**不必**去解析中文日志
    # （教训：解析日志脆弱；教训 24：扫描前先记录它实际读到的值）
    import json
    meta = dict(tag=os.path.basename(os.path.dirname(os.path.abspath(args.out))),
                T=args.temp, T_ref=args.t_ref, dH_seg=H, dS_seg=args.ds_seg,
                dG_seg=dG, wgb=wgb, dx=args.dx, ldom=args.ldom, nx=n,
                kappa_c=args.kc, c0=args.c0, t_end=args.t_end,
                delta_gb=args.delta_gb, D_L=args.dl, D_S=args.ds, D_GB=args.dgb,
                coeffs=co, f_ref=GP.f_ref(args.t_ref),
                c_GB_analytic=c_ana, s_analytic=s_ana,
                Gamma_phys_target=gamma_target,
                Gamma_model_predicted=GP.RHO_MOL * wgb * GP.int_dc_du(args.temp, H, args.ds_seg, args.c0, n=20001),
                rho_mol=GP.RHO_MOL)
    with open(os.path.join(os.path.dirname(os.path.abspath(args.out)), "params.json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("写出 %s" % args.out)
    print("  T=%.1f K  ΔH_seg=%.1f J/mol  ΔG_seg=%.1f J/mol" % (args.temp, H, dG))
    print("  系数 tau=%.6f part=%.6f seg=%.6f  f_ref=%.4e" % (co["tau"], co["part"], co["seg"], GP.f_ref(args.t_ref)))
    print("  网格 nx=%d (dx=%.4g m) 域长 %.4g m  wgb=%.4g m  晶界 x=%.6g m" %
          (n, args.dx, args.ldom, wgb, x_gb))
    print("  解析 McLean 预期: c_GB=%.8f  s=%.4f  Γ_phys=%.4e mol/m2" %
          (c_ana, s_ana, gamma_target))
    print("  模型 Γ 预期 = ρ_mol*wgb*A = %.4e mol/m2   （A=%.6f）" %
          (GP.RHO_MOL * wgb * GP.int_dc_du(args.temp, H, args.ds_seg, args.c0, n=20001),
           GP.int_dc_du(args.temp, H, args.ds_seg, args.c0, n=20001)))


if __name__ == "__main__":
    main()