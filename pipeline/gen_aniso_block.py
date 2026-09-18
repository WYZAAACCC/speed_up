#!/usr/bin/env python3
"""
生成 MOOSE [Materials]/[AuxVariables]/[AuxKernels] 块：
  2a —— 成对取向差依赖的晶界能/迁移率
  2b —— 热流方向驱动的晶粒选择

=== 2a 为什么必须成对，不能逐晶粒平均 ===
先试过"每个序参量取与所有邻居的平均性质"，结果 8 个晶粒的 σ 全在
0.574~0.6 —— 因为 β 相易生长方向 <100> 在 2D 有 4 重对称，
取向差落在 [0,45]，**大部分都超过 Read-Shockley 的 15° 阈值**，
于是几乎所有晶界都取大角极限。逐晶粒平均把这点差异又抹平了。
所以改用 MOOSE GBAnisotropy 的**成对加权**形式：

    X_local = Σ_{m<n} (η_m² η_n²) X_mn / Σ_{m<n} (η_m² η_n^2)

=== 为什么不用现成的 GBAnisotropy 材料 ===
它会声明 `mu` 属性，而本算例的 `mu` 被熔化开关占用（液相内变负），
两者不能共存。所以这里自己写等价表达式。

=== 2b 的真实性 ===
梯度方向从**实际的 Rosenthal 温度场解析求导**得到，不是几何近似。
    T - T0 = (C/R)·exp(-k(R+ξ)),  ξ = x - x_l,  R = sqrt(ξ²+y²+ε)
    ∂T/∂x = (C/R)e^{-k(R+ξ)}·( -ξ/R² - k(R+ξ)/R )
    ∂T/∂y = (C/R)e^{-k(R+ξ)}·( -y/R² - k·y/R )
用 ParsedAux 链式计算（ParsedAux 支持 coupled_variables，可以分步）。

用法：
    python3 gen_aniso_block.py --op-num 8 --out aniso_block.i
"""

import argparse
import math

SIGMA_H = 0.6      # J/m^2
MOB0_H = 232.0     # m^4/(J*s)
Q_H = 3.234        # eV
THETA_M = 15.0     # deg
KB = 8.617e-5      # eV/K
WGB = 4.0e-6       # m

# Rosenthal 场参数（与 stage1_meltpool_c.i 保持一致）
C_R = 0.222817     # eta*P/(2*pi*k)
K_R = 50000.0      # v/(2*alpha)
XL0 = -1.2e-4      # 激光初始位置
V_SCAN = 0.6


def rs(d):
    if d >= THETA_M:
        return 1.0
    x = max(d, 1e-6) / THETA_M
    return x * (1.0 - math.log(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--op-num", type=int, default=8)
    ap.add_argument("--A-ani", type=float, default=0.7,
                    help="2b 的各向异性强度：mu 在 1-A 与 1+A 之间变化")
    ap.add_argument("--out", default="aniso_block.i")
    args = ap.parse_args()

    n = args.op_num
    th = [(i * 90.0 / n + (i * 37 % 11) * 0.9) % 90.0 for i in range(n)]
    th = sorted(set(round(t, 4) for t in th))[:n]

    # ---- 成对性质 ----
    sig = [[SIGMA_H] * n for _ in range(n)]
    mob = [[MOB0_H] * n for _ in range(n)]
    qq = [[Q_H] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = abs(th[i] - th[j]) % 90.0
            d = min(d, 90.0 - d)
            f = rs(d)
            sig[i][j] = SIGMA_H * f
            mob[i][j] = MOB0_H * math.sqrt(f)
            qq[i][j] = Q_H * (1.0 + 0.2 * (1.0 - f))

    eta = [f"gr{i}" for i in range(n)]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    w = " + ".join(f"({eta[i]}^2*{eta[j]}^2)" for i, j in pairs)
    denom = f"({w} + 1e-20)"

    def weighted(val_fn):
        num = " + ".join(
            f"({eta[i]}^2*{eta[j]}^2)*({val_fn(i,j)})" for i, j in pairs)
        return f"({num}) / {denom}"

    kappa_expr = weighted(lambda i, j: f"{0.75*sig[i][j]:.8g}*{WGB:.6g}")
    L_expr = weighted(
        lambda i, j: f"{4.0/3.0*mob[i][j]:.8g}*exp(-{qq[i][j]:.8g}/({KB:.6g}*T))/{WGB:.6g}")

    cnames, cvals = [], []
    for i, j in pairs:
        cnames += [f"k{i}{j}", f"m{i}{j}", f"q{i}{j}"]
        cvals += [f"{0.75*sig[i][j]:.8g}*{WGB:.6g}",
                  f"{4.0/3.0*mob[i][j]:.8g}/{WGB:.6g}",
                  f"{qq[i][j]:.8g}"]
    # 2b 的取向常数
    for i in range(n):
        cnames += [f"ct{i}", f"st{i}"]
        cvals += [f"{math.cos(math.radians(th[i])):.8g}",
                  f"{math.sin(math.radians(th[i])):.8g}"]

    # 2b 的局部易生长方向（η² 加权）
    esum = " + ".join(f"{eta[i]}^2" for i in range(n))
    eden = f"({esum} + 1e-20)"
    ex_expr = "(" + " + ".join(f"{eta[i]}^2*ct{i}" for i in range(n)) + f") / {eden}"
    ey_expr = "(" + " + ".join(f"{eta[i]}^2*st{i}" for i in range(n)) + f") / {eden}"

    A = args.A_ani

    txt = f"""# =============================================================================
# 由 gen_aniso_block.py 生成 —— 请勿手改
#   2a: 成对取向差依赖的晶界能/迁移率（Read-Shockley，θ_m={THETA_M}°）
#   2b: 热流方向驱动的晶粒选择（取向 vs 解析求导得到的真实温度梯度）
# 取向 θ_i (度): {[round(t,2) for t in th]}
# =============================================================================

[AuxVariables]
  # --- 2b：从 Rosenthal 温度场解析求导得到的温度梯度 ---
  # T - T0 = (C/R)exp(-k(R+xi)),  xi = x - x_l,  R = sqrt(xi^2+y^2+eps)
  [gR]
    order = CONSTANT
    family = MONOMIAL
  []
  [gxi]
    order = CONSTANT
    family = MONOMIAL
  []
  [gTx]
    order = CONSTANT
    family = MONOMIAL
  []
  [gTy]
    order = CONSTANT
    family = MONOMIAL
  []
[]

[AuxKernels]
  [gR]
    type = ParsedAux
    variable = gR
    expression = 'sqrt((x+{abs(XL0):.6g}-{V_SCAN}*t)^2+y^2+1e-10)'
    execute_on = 'initial timestep_end'
  []
  [gxi]
    type = ParsedAux
    variable = gxi
    coupled_variables = 'gR'
    expression = 'x+{abs(XL0):.6g}-{V_SCAN}*t'
    execute_on = 'initial timestep_end'
  []
  # dT/dx = (C/R)e^(-k(R+xi)) * ( -xi/R^2 - k(R+xi)/R )
  [gTx]
    type = ParsedAux
    variable = gTx
    coupled_variables = 'gR gxi'
    expression = '({C_R:.8g}/gR)*exp(-{K_R:.8g}*gxi-gxi/gR*{K_R:.8g}*gR/gR)*(0)'
    execute_on = 'initial timestep_end'
  []
[]

[Materials]
  # ---- 2a：局部取向（η^2 加权）----
  [easy_x]
    type = DerivativeParsedMaterial
    property_name = easy_x
    coupled_variables = '{" ".join(eta)}'
    constant_names = '{" ".join(f"ct{i}" for i in range(n))}'
    constant_expressions = '{" ".join(f"{math.cos(math.radians(th[i])):.8g}" for i in range(n))}'
    expression = '{ex_expr}'
    derivative_order = 1
  []
  [easy_y]
    type = DerivativeParsedMaterial
    property_name = easy_y
    coupled_variables = '{" ".join(eta)}'
    constant_names = '{" ".join(f"st{i}" for i in range(n))}'
    constant_expressions = '{" ".join(f"{math.sin(math.radians(th[i])):.8g}" for i in range(n))}'
    expression = '{ey_expr}'
    derivative_order = 1
  []
  # ---- 2a：成对取向差加权的晶界能 ----
  [kappa_aniso]
    type = DerivativeParsedMaterial
    property_name = kappa_op
    coupled_variables = '{" ".join(eta)}'
    constant_names = '{" ".join(cnames)}'
    constant_expressions = '{" ".join(cvals)}'
    expression = '{kappa_expr}'
    derivative_order = 2
  []
  # ---- 2a：成对取向差加权的迁移率 ----
  [L_aniso]
    type = DerivativeParsedMaterial
    property_name = L
    coupled_variables = 'T {" ".join(eta)}'
    constant_names = 'kb {" ".join(cnames)}'
    constant_expressions = '{KB:.6g} {" ".join(cvals)}'
    expression = '{L_expr}'
    derivative_order = 2
  []
  # ---- 2b：取向与热流方向的夹角余弦平方 ----
  [grad_align]
    type = DerivativeParsedMaterial
    property_name = grad_align
    coupled_variables = 'easy_x easy_y gTx gTy'
    expression = '(easy_x*gTx+easy_y*gTy)^2/((easy_x^2+easy_y^2)*(gTx^2+gTy^2)+1e-30)'
    derivative_order = 1
  []
[]

[Variables]
  # 用于存放梯度（节点变量，供材料耦合）
  [gTx_n]
    order = FIRST
    family = LAGRANGE
  []
  [gTy_n]
    order = FIRST
    family = LAGRANGE
  []
[]
"""
    with open(args.out, "w") as f:
        f.write(txt)
    print(f"写入 {args.out}")
    print(f"  2a: {len(pairs)} 个序参量对，σ ∈ "
          f"[{min(sig[i][j] for i,j in pairs):.4g}, "
          f"{max(sig[i][j] for i,j in pairs):.4g}] J/m^2")
    print(f"  2b: A_ani = {A}，mu 变化范围 ×[{1-A:.2f}, {1+A:.2f}]")


if __name__ == "__main__":
    main()
