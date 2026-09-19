#!/usr/bin/env python3
"""
T13 算例生成器：**移动固固晶界上的溶质拖曳**

## 审计判据

    「T13 | 溶质拖曳 | 移动固固晶界 |
      随浓度/扩散率变化的速度趋势正确；与无溶质对照显著可分」

**注意判据是定性的**（"趋势正确"、"显著可分"），不需要绝对标定 ——
所以它不受 Phase 3 那个"用哪个物理量标定"的阻塞影响，现在就能做。

## 为什么现在才做得了

拖曳需要**溶质反过来影响晶界迁移**这条通道。在生产模型里溶质的自由能
`f_loc` 只通过 `A_part·c²·Ση²` 与 η 耦合；Phase 3 加的独立偏析项
`(Ω₀/wgb)(c−c₀)h_gb` 是**又一条、而且是专门给晶界加上的**通道。
两条都在，才有拖曳可测。

## 构型

1D、两个晶粒（η₀ + η₁ ≈ 1）、晶界**自由演化**（不冻结），
外加一个恒定驱动力 `F_ext`（`BodyForce` 加在 η₀ 上）让晶界匀速迁移。

**关键技巧**：1D 双晶粒里 η₀ + η₁ ≈ 1 处处成立 ⇒

    ∫η₀ dx  ≈  晶界位置 x_GB   （米）

所以**晶界速度 v = d(∫η₀ dx)/dt**，不需要找 η=0.5 的点、也不会被离散噪声干扰。
（这比"找等值线交点"稳得多 —— T9 就在类似的地方栽过。）

## Cahn 拖曳的预期趋势

定驱动力下，溶质气氛在晶界上施加一个**反向**的力 ⇒
**v 随 c₀ 增大而减小**；c₀ → 0 时回到无溶质的自由速度 v₀。
（高驱动力下还有"脱钉"分支，但本算例只测低驱动力一侧。）

## 用法

    python3 make_1d_drag.py --out drag.i --c0 0.036
"""

import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TEMPLATE = """# T13 移动固固晶界上的溶质拖曳 —— 自动生成，勿手改
# 见 make_1d_drag.py 头注释。

[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = @NX@
  xmin = 0
  xmax = @LDOM@
  elem_type = EDGE2
[]

[Variables]
  [gr0]
    order = FIRST
    family = LAGRANGE
    # ⚠ 这里**不冻结**（与 make_1d_gb.py 相反）：T13 要的就是会动的晶界
  []
  [gr1]
    order = FIRST
    family = LAGRANGE
  []
  [c]
    initial_condition = @C0@
  []
  [w]
  []
[]

[ICs]
  # 平直晶界放在 x_gb；tanh 宽度 = wGB
  [ic_gr0]
    type = FunctionIC
    variable = gr0
    function = f_gr0
  []
  [ic_gr1]
    type = FunctionIC
    variable = gr1
    function = f_gr1
  []
[]

[Functions]
  [f_gr0]
    type = ParsedFunction
    expression = '0.5*(1-tanh((x-@XGB@)/@WGB@))'
  []
  [f_gr1]
    type = ParsedFunction
    expression = '0.5*(1+tanh((x-@XGB@)/@WGB@))'
  []
[]

[BCs]
  # =====================================================================
  # 【必须】周期边界 —— 这是本算例最容易搞错的一处
  # =====================================================================
  # 1D 里一个平直晶界 + **自然边界**是**不稳定**的：那是个 kink 解，
  # 在有限域里它会**跑到边界上消失**（两个晶粒合并）。
  # 实测：η₀ 在第一个输出间隔内（t=2.3e-5 s）就从 1.0 被整体抹成 0，
  #       而且**与驱动力无关**（F_ext = 0 时照样发生）。
  # 只有周期边界能把 kink 钉住。
  #
  # ⚠ 为什么在 make_1d_gb.py 上没暴露：那边 **η 是冻结的**（FunctionAux），
  #   晶界会不会跑根本无从体现。这个坑是"晶界可动"之后才出现的。
  #
  # ⚠ γ_asymm = 1.5 > 1 让**均相**自由能更偏向单晶粒（多晶里没问题，
  #   拓扑上合并不掉；双晶粒 1D 里就直接并掉），所以周期性在这里是唯一支撑。
  [Periodic]
    [all]
      auto_direction = 'x'
    []
  []
[]

[Kernels]
  # --- 序参量：可动 ---
  [dt0]
    type = TimeDerivative
    variable = gr0
  []
  [dt1]
    type = TimeDerivative
    variable = gr1
  []
  [ac0]
    type = ACGrGrPoly
    variable = gr0
    v = 'gr1'
    mob_name = L
  []
  [ac1]
    type = ACGrGrPoly
    variable = gr1
    v = 'gr0'
    mob_name = L
  []
  [int0]
    type = ACInterface
    variable = gr0
    mob_name = L
    kappa_name = kappa_op
  []
  [int1]
    type = ACInterface
    variable = gr1
    mob_name = L
    kappa_name = kappa_op
  []
  # --- 外部驱动力：加在 gr0 上 ⇒ 晶界朝 +x 迁移 ---
  #   ⚠ 这是**人为加的压力项**（等效存储能差），不是自由能的一部分。
  #     T13 测的是"溶质对给定驱动力的响应"，所以驱动力必须是我们控制的量。
  [drive]
    type = BodyForce
    variable = gr0
    value = @FEXT@
  []
  # --- 溶质：分裂式 Cahn–Hilliard（与生产同形式）---
  [c_time]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [c_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
    coupled_variables = 'gr0 gr1'
  []
  [c_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
    coupled_variables = 'gr0 gr1'
  []
[]

[Materials]
  [consts]
    type = GenericConstantMaterial
    prop_names  = 'kappa_op gamma_asymm kappa_c'
    prop_values = '1.8e-6    1.5          1e-14'
  []
  [mu_barrier]
    type = GenericConstantMaterial
    prop_names  = 'mu'
    prop_values = '9.0e5'
  []
  # L = 4/3 * M0 / wGB（与生产同公式）
  [mobility]
    type = GenericConstantMaterial
    prop_names  = 'L'
    prop_values = '@L_VAL@'
  []

  # --- 与生产 / make_1d_gb.py 完全相同的指示函数 ---
  [S_eta2]
    type = DerivativeParsedMaterial
    property_name = S_eta2
    coupled_variables = 'gr0 gr1'
    expression = 'gr0^2+gr1^2'
    derivative_order = 2
  []
  [Q_eta4]
    type = DerivativeParsedMaterial
    property_name = Q_eta4
    coupled_variables = 'gr0 gr1'
    expression = 'gr0^4+gr1^4'
    derivative_order = 2
  []
  [h_gb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'gr0 gr1'
    material_property_names = 'S_eta2 Q_eta4'
    expression = '8*(S_eta2^2 - Q_eta4)'
    derivative_order = 2
  []
  [h_solid]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'gr0 gr1'
    material_property_names = 'S_eta2'
    expression = 'min(1, 2*S_eta2)'
    derivative_order = 2
  []
  [D_field]
    type = DerivativeParsedMaterial
    property_name = D_eff
    coupled_variables = 'gr0 gr1'
    material_property_names = 'h_gb h_solid'
    constant_names = 'D_L D_S D_GB'
    constant_expressions = '@DL@ @DS@ @DGB@'
    expression = 'D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb'
    derivative_order = 2
  []
  [solute_mobility]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'gr0 gr1'
    material_property_names = 'D_eff'
    constant_names = 'k_c A_part'
    constant_expressions = '0.9 0.264'
    # 同上：h_solid 显式内联（必须与 f_loc 的 f_cc 一致）
    expression = 'D_eff / (k_c + 2*A_part*min(1, 2*(gr0^2+gr1^2)))'
    derivative_order = 2
  []
  # --- 自由能：与 make_1d_gb.py 的 --f-part h_solid --f-seg 同一形式 ---
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0 gr1'
    constant_names = 'k_c c0 A_part Omega0 wgb'
    constant_expressions = '0.9 @C0@ 0.264 @OMEGA0@ @WGB@'
    # ⚠ 指示函数**显式内联**，不走 material_property_names。
    #   1D 双序参量下它们是简单多项式：
    #       S = gr0^2+gr1^2,  Q = gr0^4+gr1^4
    #       h_gb    = 8(S^2-Q) = 16*gr0^2*gr1^2      （单项式）
    #       h_solid = min(1, 2*S)
    #   内联后 η 依赖全在表达式里 ⇒ 绕开"跨 DerivativeParsedMaterial 求导"
    #   的病理（导数静默为零 / JIT 爆炸）。实测 JIT 从 20+ 分钟回到 1 分钟量级。
    expression = 'k_c/2*(c-c0)^2
                  + A_part*c^2*min(1, 2*(gr0^2+gr1^2))
                  + (Omega0/wgb)*(c-c0)*16*gr0^2*gr1^2'
    derivative_order = 2
  []
[]

[Postprocessors]
  # ∫η₀ dx = 晶界位置（米）—— 见文件头
  [gb_pos]
    type = ElementIntegralVariablePostprocessor
    variable = gr0
    execute_on = 'initial timestep_end'
  []
  [c_total]
    type = ElementIntegralVariablePostprocessor
    variable = c
    execute_on = 'initial timestep_end'
  []
  [n_elem]
    type = NumElements
    execute_on = 'initial'
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
  petsc_options_iname = '-pc_type -pc_factor_mat_solver_type'
  petsc_options_value = 'lu       mumps'
  l_max_its = 60
  l_tol = 1e-6
  nl_max_its = 30
  nl_rel_tol = 1e-8
  nl_abs_tol = 1e-10
  end_time = @TEND@
  dtmax = @DTMAX@
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = @DT@
    growth_factor = 1.5
    cutback_factor = 0.5
    optimal_iterations = 6
  []
[]

[Outputs]
  csv = true
  exodus = false
  [exo]
    type = Exodus
    time_step_interval = 20
  []
[]
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--nx", type=int, default=400)
    ap.add_argument("--ldom", type=float, default=2.0e-6, help="域长 m")
    ap.add_argument("--xgb", type=float, default=1.0e-6, help="初始晶界位置 m")
    ap.add_argument("--wgb", type=float, default=0.4e-6, help="晶界 tanh 宽度 m")
    ap.add_argument("--c0", type=float, default=0.036, help="初始/平均溶质浓度")
    ap.add_argument("--fext", type=float, default=1.0e3, help="外部驱动力（BodyForce 值）")
    ap.add_argument("--dl", type=float, default=2.52e-9)
    ap.add_argument("--ds", type=float, default=4.0e-13)
    ap.add_argument("--dgb", type=float, default=4.0e-10)
    ap.add_argument("--omega0", type=float, default=-4.6e-9,
                    help="Phase 3 的偏析标定参数（**calibration**，不是 Ti64 常数）")
    ap.add_argument("--no-seg", action="store_true",
                    help="关掉偏析项（对照用：只有分配项那条耦合通道）")
    ap.add_argument("--t-end", type=float, default=2.0e-5)
    # ⚠ 时间步受**界面弛豫时间** τ = 1/(L·μ) ≈ 1.16e-6 s 限制（与生产同一个约束）。
    #   第一版把 dtmax 设成 t_end/20 = 1e-3，比 τ 大三个数量级 —— 会发散。
    ap.add_argument("--dtmax", type=float, default=2.5e-7, help="最大步长 s（须 ≲ τ/4）")
    ap.add_argument("--dt0", type=float, default=1.0e-8, help="初始步长 s")
    a = ap.parse_args()

    # L = 4/3 * M0 / wGB，M0 = 2.8702e-07（与 run_t8.sh / 生成器同公式）
    l_val = (4.0 / 3.0) * 2.8702e-07 / a.wgb

    omega = 0.0 if a.no_seg else a.omega0

    txt = (TEMPLATE
           .replace("@NX@", str(a.nx))
           .replace("@LDOM@", f"{a.ldom:.6e}")
           .replace("@XGB@", f"{a.xgb:.6e}")
           .replace("@WGB@", f"{a.wgb:.6e}")
           .replace("@C0@", f"{a.c0:.10g}")
           .replace("@FEXT@", f"{a.fext:.10g}")
           .replace("@L_VAL@", f"{l_val:.10g}")
           .replace("@DL@", f"{a.dl:g}")
           .replace("@DS@", f"{a.ds:g}")
           .replace("@DGB@", f"{a.dgb:g}")
           .replace("@OMEGA0@", f"{omega:.10g}")
           .replace("@TEND@", f"{a.t_end:.6e}")
           .replace("@DTMAX@", f"{a.dtmax:.6e}")
           .replace("@DT@", f"{a.dt0:.6e}"))

    # 自检：不该有未替换的占位符
    import re
    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit(f"错误：还有未替换的占位符 {sorted(set(left))}")

    open(a.out, "w", encoding="utf-8").write(txt)
    print(f"写出 {a.out}")
    print(f"  dx = {a.ldom/a.nx*1e6:.4f} µm   wGB = {a.wgb*1e6:.3f} µm   "
          f"dx/wGB = {a.ldom/a.nx/a.wgb:.3f}")
    print(f"  L = {l_val:.6g}   F_ext = {a.fext:g}   c0 = {a.c0:g}   "
          f"Ω0 = {omega:g}{'（已关掉偏析项）' if a.no_seg else ''}")
    print(f"  t_end = {a.t_end:g} s")
    print()
    print("量法：v = d(∫η₀ dx)/dt（1D 双晶粒里 ∫η₀ 就是晶界位置，单位米）")


if __name__ == "__main__":
    main()
