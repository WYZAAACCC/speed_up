#!/usr/bin/env python3
# =============================================================================
# T12（1D 版）：把分层迁移率当**动力学系数**量出来，而不只是读材料属性
# =============================================================================
#
# 【为什么不能只读材料属性】
#   T6 / `check_D_layering.py` / `MaterialRealAux` 量到的都是 **D 的取值**——
#   它们证明"写进材料里的表达式在给定 η 下求值正确"。
#   但那不等于**演化方程真的按这个 D 在扩散**：
#   M 进的是 ∂c/∂t = ∇·(M∇μ)，中间还隔着 f_cc、分裂变量 w、以及雅可比。
#   T12 要的是后者。
#
# 【做法：小扰动的指数衰减】
#   在平衡态 c_eq 上加一个余弦扰动 c = c_eq + A·cos(kx)，k = π/L。
#   （自然边界条件下 dc/dx 在两端为 0，与余弦一致，无需额外 BC。）
#
#   把 Cahn–Hilliard 线性化：
#       μ = f'(c) − κ_c∇²c  ⇒  δμ = f''·δc − κ_c∇²δc
#       ∂δc/∂t = ∇·(M∇δμ)   ⇒  对 cos(kx) 本征函数：
#       rate = D·k²·(1 + κ_c·k²/f'')         其中 D = M·f''
#   ⇒ 拟合 ln(振幅) 的斜率得到 rate，反解
#       D_measured = rate / (k²·(1 + κ_c k²/f''))
#
#   **四阶项修正不要省**：κ_c = 1e-14、L = 4 µm 时它占 0.43%，
#   而 T12 的判据是 5–10% —— 省掉它不会翻车，但既然能精确算就该算进去，
#   否则将来有人把 κ_c 调大就会看到一个说不清的偏差。
#
# 【三种状态】
#   liquid : η ≡ 0        ⇒ D 应为 D_L
#   grain  : η0 ≡ 1       ⇒ D 应为 D_S
#   gb     : η0=η1 ≡ 0.5  ⇒ D 应为 D_GB
#   三者都用**同一套分层材料**（不是各自写死一个常数）——
#   这样量的是"分层实现"本身。
#
# 用法：
#   python3 make_1d_decay.py --out d.i --state gb
#   python3 analyze_decay.py <目录>          # 拟合并出表
# =============================================================================

import argparse
import math
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

K_C, A_PART, C0 = 0.9, 0.264, 0.036

# 三种状态下的 eta0 / eta1（常数）
STATES = {
    "liquid": (0.0, 0.0),
    "grain": (1.0, 0.0),
    "gb": (0.5, 0.5),
    # 三叉晶界：三个 η 各 1/3（此处只用两个，另加一个 gr2 占位以体现 S=1/3）
}

TEMPLATE = """# =============================================================================
# T12：小扰动衰减测有效扩散（自动生成 —— 见 validated/make_1d_decay.py）
#   状态 = @STATE@   （eta0 = @E0@, eta1 = @E1@）
# =============================================================================
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = @NX@
  xmin = 0
  xmax = @LDOM@
[]

[Variables]
  # ⚠ 不要在这里写 initial_condition —— 下面 [ICs] 里已有 FunctionIC，
  #   两者同时存在会报 "initial condition ... already has an initial condition defined"。
  [c]
  []
  [w]
    initial_condition = 0
  []
[]

[Functions]
  [c_ic]
    type = ParsedFunction
    expression = '@CEQ@ + @AMP@*cos(pi*x/@LDOM@)'
  []
[]

[ICs]
  [c_ic]
    type = FunctionIC
    variable = c
    function = c_ic
  []
[]

[AuxVariables]
  [eta0]
    initial_condition = @E0@
  []
  [eta1]
    initial_condition = @E1@
  []
  [D_aux]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  # eta 本来就是常数初值，不需要 FunctionAux 去钉（这正好也避免引入额外自由度）
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
    # ⚠ 这里的 eta0/eta1 是**辅助变量**，M 不依赖它们（它们是常数），
    #   所以不需要声明 coupled_variables —— 辅助变量本来也不进雅可比。
    #   保留这行注释是为了说明**为什么这里和 make_1d_gb.py 不同**。
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
  []
[]

[Materials]
  [ch_kappa]
    type = GenericConstantMaterial
    prop_names  = 'kappa_c'
    prop_values = '@KAPPA_C@'
  []
  [S_eta2]
    type = ParsedMaterial
    property_name = S_eta2
    coupled_variables = 'eta0 eta1'
    expression = 'eta0^2+eta1^2'
  []
  [Q_eta4]
    type = ParsedMaterial
    property_name = Q_eta4
    coupled_variables = 'eta0 eta1'
    expression = 'eta0^4+eta1^4'
  []
  [h_gb]
    type = ParsedMaterial
    property_name = h_gb
    coupled_variables = 'eta0 eta1'
    material_property_names = 'S_eta2 Q_eta4'
    expression = '8*(S_eta2^2 - Q_eta4)'
  []
  [h_solid]
    type = ParsedMaterial
    property_name = h_solid
    coupled_variables = 'eta0 eta1'
    material_property_names = 'S_eta2'
    expression = 'min(1, 2*S_eta2)'
  []
  [D_field]
    type = ParsedMaterial
    property_name = D_eff
    coupled_variables = 'eta0 eta1'
    material_property_names = 'h_gb h_solid'
    constant_names = 'D_L D_S D_GB'
    constant_expressions = '@DL@ @DS@ @DGB@'
    expression = 'D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb'
  []
  [solute_mobility]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'c'
    material_property_names = 'D_eff S_eta2'
    constant_names = 'k_c A_part'
    constant_expressions = '0.9 0.264'
    expression = 'D_eff / (k_c + 2*A_part*S_eta2)'
    derivative_order = 2
  []
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c eta0 eta1'
    material_property_names = 'S_eta2'
    constant_names = 'k_c c0 A_part'
    constant_expressions = '0.9 0.036 0.264'
    expression = 'k_c/2*(c-c0)^2 + A_part*c^2*S_eta2'
    derivative_order = 2
  []
[]

[Postprocessors]
  [c_max]
    type = NodalExtremeValue
    variable = c
    value_type = max
    execute_on = 'initial timestep_end'
  []
  [c_min]
    type = NodalExtremeValue
    variable = c
    value_type = min
    execute_on = 'initial timestep_end'
  []
  [D_val]
    type = ElementAverageValue
    variable = D_aux
    execute_on = 'initial'
  []
  [total_c]
    type = ElementIntegralVariablePostprocessor
    variable = c
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
  l_tol = 1e-10
  nl_max_its = 30
  nl_rel_tol = 1e-12
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
    ap.add_argument("--state", choices=sorted(STATES), required=True)
    ap.add_argument("--amp", type=float, default=1e-6, help="扰动振幅（相对 c_eq 要小）")
    ap.add_argument("--ldom", type=float, default=4.0e-6)
    ap.add_argument("--nx", type=int, default=200)
    ap.add_argument("--kc", type=float, default=1.0e-14)
    ap.add_argument("--dl", type=float, default=2.52e-9)
    ap.add_argument("--ds", type=float, default=4.0e-13)
    ap.add_argument("--dgb", type=float, default=4.0e-10)
    ap.add_argument("--t-end", type=float, default=None)
    args = ap.parse_args()

    e0, e1 = STATES[args.state]
    S = e0 ** 2 + e1 ** 2
    # 平衡浓度 c_eq = c0*k_c/(k_c + 2A*S)
    c_eq = C0 * K_C / (K_C + 2.0 * A_PART * S)
    fpp = K_C + 2.0 * A_PART * S          # f''
    D_target = {"liquid": args.dl, "grain": args.ds, "gb": args.dgb}[args.state]

    # 让振幅衰减 ~3 个 e 折所需的时间 ≈ 3/rate，rate = D k²(1+κk²/f'')
    k = math.pi / args.ldom
    rate = D_target * k ** 2 * (1.0 + args.kc * k ** 2 / fpp)
    t_end = args.t_end if args.t_end is not None else 3.0 / rate
    # 步长：一个 e 折至少 40 步
    dt = min(1.0 / rate / 40.0, t_end / 20.0)

    txt = (TEMPLATE
           .replace("@STATE@", args.state)
           .replace("@E0@", f"{e0:g}")
           .replace("@E1@", f"{e1:g}")
           .replace("@LDOM@", f"{args.ldom:.6e}")
           .replace("@NX@", str(args.nx))
           .replace("@CEQ@", f"{c_eq:.12g}")
           .replace("@AMP@", f"{args.amp:g}")
           .replace("@KAPPA_C@", f"{args.kc:.6e}")
           .replace("@DL@", f"{args.dl:g}")
           .replace("@DS@", f"{args.ds:g}")
           .replace("@DGB@", f"{args.dgb:g}")
           .replace("@DT@", f"{dt:.6e}")
           .replace("@TEND@", f"{t_end:.6e}"))

    left = re.findall(r"@[A-Z_0-9]+@", txt)
    if left:
        sys.exit(f"错误：还有未替换的占位符 {sorted(set(left))}")

    open(args.out, "w", encoding="utf-8", newline="").write(txt)

    print(f"写出 {args.out}")
    print(f"  状态={args.state}  S={S:g}  f''={fpp:g}")
    print(f"  c_eq={c_eq:.10g}  振幅={args.amp:g}")
    print(f"  k=pi/L={k:.6g} /m   κ_c k²/f''={args.kc*k*k/fpp:.5f}"
          f"（四阶项修正，已计入预测）")
    print(f"  D 的目标值 = {D_target:g}     预测 rate = {rate:.6g} /s")
    print(f"  t_end = {t_end:.6g} s   dt = {dt:.6g} s   nx = {args.nx}")


if __name__ == "__main__":
    main()
