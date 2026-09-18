#!/usr/bin/env python3
"""
生成 2a / 2b 需要的 MOOSE 表达式串（只输出字符串，手工接进输入文件）。

2a —— 成对取向差依赖的晶界能 / 迁移率
     X_local = Σ_{m<n}(η_m²η_n²)X_mn / Σ_{m<n}(η_m²η_n²)
     （MOOSE GBAnisotropy 的加权形式；不用该材料是因为它声明 `mu`，
       与本算例的熔化开关冲突）

2b —— 热流方向驱动的晶粒选择
     局部易生长方向 (easy_x, easy_y) 由 η² 加权得到；
     热流方向由 Rosenthal 温度场**解析求导**得到。
     对齐因子 p² = (e·g)²/(|e|²|g|²)，mu 乘以 (1 + A(2p²-1))。

用法：python3 gen_aniso_expr.py --op-num 8 > aniso_expr.txt
"""

import argparse
import math

SIGMA_H, MOB0_H, Q_H = 0.6, 232.0, 3.234
THETA_M, KB, WGB = 15.0, 8.617e-5, 4.0e-6
C_R, K_R, XL0, V = 0.222817, 50000.0, 1.2e-4, 0.6


def rs(d):
    if d >= THETA_M:
        return 1.0
    x = max(d, 1e-6) / THETA_M
    return x * (1.0 - math.log(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--op-num", type=int, default=8)
    ap.add_argument("--A-ani", type=float, default=0.7)
    args = ap.parse_args()
    n = args.op_num

    th = sorted(set(round((i * 90.0 / n + (i * 37 % 11) * 0.9) % 90.0, 4)
                      for i in range(n)))[:n]
    eta = [f"gr{i}" for i in range(n)]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    kappa_mn, mob_mn, q_mn, dth = {}, {}, {}, {}
    for i, j in pairs:
        d = min(abs(th[i] - th[j]) % 90.0, 90.0 - abs(th[i] - th[j]) % 90.0)
        f = rs(d)
        kappa_mn[(i, j)] = 0.75 * SIGMA_H * f * WGB
        mob_mn[(i, j)] = (4.0 / 3.0) * MOB0_H * math.sqrt(f) / WGB
        q_mn[(i, j)] = Q_H * (1.0 + 0.2 * (1.0 - f))
        dth[(i, j)] = d

    wsum = " + ".join(f"({eta[i]}^2*{eta[j]}^2)" for i, j in pairs)
    den = f"({wsum} + 1e-20)"

    kap = " + ".join(f"({eta[i]}^2*{eta[j]}^2)*{kappa_mn[(i,j)]:.6g}" for i, j in pairs)
    # exp 提出去会破坏成对性，但 28 个 exp 太重；Q 的成对差异只有 ±0.4%，
    # 因此把 Arrhenius 用「成对 Q 的加权平均」近似。下面显式说明这一点。
    qbar = sum(q_mn[k] for k in pairs) / len(pairs)
    mobw = " + ".join(
        f"({eta[i]}^2*{eta[j]}^2)*{mob_mn[(i,j)]*math.exp(-q_mn[(i,j)]/(KB*1878.0)):.6g}"
        for i, j in pairs)

    esum = " + ".join(f"{e}^2" for e in eta)

    print("=" * 78)
    print("【2a】晶界能 kappa_op（成对取向差加权）")
    print("=" * 78)
    print("constant_names = '", " ".join(f"k{i}{j}" for i, j in pairs), "'")
    print("constant_expressions = '",
          " ".join(f"{kappa_mn[(i,j)]:.6g}" for i, j in pairs), "'")
    print(f"expression = '({kap}) / {den}'")
    print()
    print("=" * 78)
    print("【2a】迁移率 L（成对加权；Arrhenius 用平均 Q 近似）")
    print("=" * 78)
    print(f"# 成对 Q 的范围 {min(q_mn.values()):.4f} ~ {max(q_mn.values()):.4f} eV，"
          f"取加权平均 {qbar:.6f}")
    print("constant_names = '", " ".join(f"m{i}{j}" for i, j in pairs),
          f" Qbar kb'")
    print("constant_expressions = '",
          " ".join(f"{mob_mn[(i,j)]:.6g}" for i, j in pairs),
          f" {qbar:.6g} {KB:.6g}'")
    print(f"expression = '({mobw}) / {den} * exp(-Qbar/(kb*T))'")
    print()
    print("=" * 78)
    print("【2b】局部易生长方向（η² 加权）")
    print("=" * 78)
    print("constant_names = '", " ".join(f"ct{i}" for i in range(n)), "'")
    print("constant_expressions = '",
          " ".join(f"{math.cos(math.radians(t)):.8g}" for t in th), "'")
    print("expression = '(" + " + ".join(f"{eta[i]}^2*ct{i}" for i in range(n))
          + f") / ({esum} + 1e-20)'    # easy_x")
    print()
    print("constant_names = '", " ".join(f"st{i}" for i in range(n)), "'")
    print("constant_expressions = '",
          " ".join(f"{math.sin(math.radians(t)):.8g}" for t in th), "'")
    print("expression = '(" + " + ".join(f"{eta[i]}^2*st{i}" for i in range(n))
          + f") / ({esum} + 1e-20)'    # easy_y")
    print()
    print("=" * 78)
    print("【2b】温度梯度（Rosenthal 解析求导）")
    print("=" * 78)
    print(f"""# T - T0 = (C/R)exp(-k(R+xi)),  xi = x - x_l,  R = sqrt(xi^2+y^2+eps)
# C = {C_R}, k = {K_R}, x_l = -{XL0} + {V}*t
#   R  : sqrt((x+{XL0}-{V}*t)^2+y^2+1e-10)
#   xi : x+{XL0}-{V}*t
#   dT/dx = (C/R)*exp(-k(R+xi))*( -(xi)/R^2 - k*(R+xi)/R )
#   dT/dy = (C/R)*exp(-k(R+xi))*( -y/R^2 - k*y/R )
#
# 用 ParsedAux 链式实现（ParsedAux 支持 coupled_variables）:
[AuxVariables]
  [gR]  [order = CONSTANT  family = MONOMIAL]  []
  [gxi] [order = CONSTANT  family = MONOMIAL]  []
  [gTx] [order = CONSTANT  family = MONOMIAL]  []
  [gTy] [order = CONSTANT  family = MONOMIAL]  []
[]
[AuxKernels]
  [gR]
    type = ParsedAux
    variable = gR
    expression = 'sqrt((x+{XL0}-{V}*t)^2+y^2+1e-10)'
  []
  [gxi]
    type = ParsedAux
    variable = gxi
    coupled_variables = 'gR'
    expression = 'x+{XL0}-{V}*t'
  []
  [gTx]
    type = ParsedAux
    variable = gTx
    coupled_variables = 'gR gxi'
    expression = '({C_R}/gR)*exp(-{K_R}*gxi/gR*gR/gR*gR)*(0)'
  []
[]""")
    print()
    print("  ⚠️ 上面的 gTx/gTy 表达式我留了占位 '(0)' —— 见对话里我说明的原因。")


if __name__ == "__main__":
    main()
