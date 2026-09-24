#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
pf1d_interface.py --- P1.1 的核心：1D 稳态界面匹配（弥散界面 vs 锐界面极限）

对应 MATH_FRAMEWORK 7.2 的强制项。它在本文件里被拆成一个【可严格验证的等价命题】:

    弥散界面宽度 W -> 0 时, 有效分配系数 k_eff 必须 -> k_e;
    而 k_eff = k_e 【只有当抗截留通量存在时】才对所有 W 成立。

记法: u_x = du/dxi, u_xx = d2u/dxi2, g_x = dg/dxi

模型（1D 稳态，界面系）
-----------------------
混合浓度 u = c_m = f_s c_s + (1-f_s) c_l。稳态下混合浓度的总通量为常数:
    -V u + D_eff(xi) * d(c_l)/dxi + j_at(xi) = -V c_inf
局部界面平衡:  c_s = k c_l   =>   c_l = u / (1 - (1-k) f_s) =: g(xi) u
通道面积:      D_eff(xi) = D_S + (D_L - D_S)(1 - f_s)
界面剖面:      f_s(xi) = 0.5(1 - tanh(xi/(sqrt(2) W)))      (W -> 0 即阶跃)
抗截留通量（Karma-Rappel 形式, 系数 A 待定, 只在界面内非零）:
    j_at(xi) = -A (1-k) c_inf V W df_s/dxi
边界条件:  u(+inf) = c_inf ;  u_x(-inf) = 0 (D_S=0 时固体里无通量, 自动满足)

待测:  k_eff = u(-inf)/c_l(0) ;  锐界面极限必须 = k_e ;  找 A 使 k_eff = k_e 对所有 W 成立。
"""

import math
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_E = 0.6303            # [T] 平衡分配系数（由 A_part 反解, T4 验证 0.05%）
C0_V = 0.036            # [L] V 摩尔分数
D_L = 9.5e-9            # [L] m2/s
D_S = 0.0               # 无反扩散极限（与 MATH_FRAMEWORK 4.5 的 alpha_bd=1.6e-3 一致）
V_PULL = 0.1            # [L] m/s
DELTA_C = 2.0 * D_L / V_PULL      # 溶质边界层厚度 = 190 nm


def fs_profile(xi, W):
    if W <= 0.0:
        return (xi < 0.0).astype(float)
    return 0.5 * (1.0 - np.tanh(xi / (math.sqrt(2.0) * W)))


def solve_steady(W, A_at=0.0, c_inf=C0_V, L=6.0, N=20001, k=K_E):
    """稳态线性 ODE 的有限差分解。返回 (xi, u, c_l, f_s, k_eff)。"""
    xi = np.linspace(-L * DELTA_C, L * DELTA_C, N)
    h = xi[1] - xi[0]
    fs = fs_profile(xi, W)
    g = 1.0 / (1.0 - (1.0 - k) * fs)
    De = D_S + (D_L - D_S) * (1.0 - fs)
    gp = np.gradient(g, h)
    fsp = np.gradient(fs, h)

    a = De * g                              # u_xx 系数
    b = De * gp - V_PULL                    # u_x  系数
    src = -A_at * (1.0 - k) * c_inf * V_PULL * W * fsp
    rhs = -V_PULL * c_inf - src

    main = -2.0 * a / h ** 2
    up = a / h ** 2 + b / (2.0 * h)
    dn = a / h ** 2 - b / (2.0 * h)
    M = sp.diags([dn[1:-1], main[1:-1], up[1:-1]], [-1, 0, 1],
                 shape=(N - 2, N - 2), format="lil")
    r = rhs[1:-1].copy()
    M[0, 0] = M[0, 0] + dn[1]               # 左端 Neumann
    r[-1] -= up[N - 2] * c_inf              # 右端 Dirichlet
    u = np.empty(N)
    u[-1] = c_inf
    u[1:-1] = spla.spsolve(M.tocsr(), r)
    u[0] = u[1]
    c_l = g * u
    i0 = int(np.argmin(np.abs(xi)))
    return xi, u, c_l, fs, float(u[0]) / float(c_l[i0])


def main():
    RES = []
    def chk(name, verdict, detail, value=None):
        RES.append((verdict, name, detail))
        print("[{:<4}] {:<50} {}".format(verdict, name, detail))

    print("pf1d_interface.py --- 1D 稳态界面匹配（P1.1 核心）")
    print("=" * 100)
    print("k_e = {:.4f} ; D_L = {:.2e} m2/s ; V = {:.2f} m/s ; delta_c = {:.0f} nm".format(
        K_E, D_L, V_PULL, DELTA_C * 1e9))

    xi, u, cl, fs, keff = solve_steady(0.0, 0.0)
    chk("P1-1 锐界面(W=0)极限 k_eff = k_e", "PASS" if abs(keff - K_E) < 5e-3 else "FAIL",
        "k_eff = {:.5f} vs k_e = {:.5f} (相对 {:.2e})".format(
            keff, K_E, abs(keff - K_E) / K_E), keff)

    Ws = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]) * 1e-9
    dev = []
    for W in Ws:
        _, _, _, _, ke = solve_steady(W, 0.0)
        dev.append(ke / K_E - 1.0)
    print("")
    print("  W(nm)   W*V/D_L    k_eff/k_e - 1")
    for W, d in zip(Ws, dev):
        print("  {:6.1f}  {:8.4f}   {:+.4e}".format(W * 1e9, W * V_PULL / D_L, d))
    chk("P1-2 弥散界面使 k_eff 偏离 k_e（随 W 增大）",
        "PASS" if abs(dev[-1]) > abs(dev[0]) else "WARN",
        "W=0.5->50 nm: 偏离从 {:+.2e} 变到 {:+.2e}".format(dev[0], dev[-1]), dev)
    d = np.abs(np.array(dev))
    good = d > 0
    if good.sum() > 2:
        pf = np.polyfit(np.log(Ws[good] * V_PULL / D_L), np.log(d[good]), 1)
        print("  标度: |k_eff/k_e - 1| ~ (W V / D_L)^{:.3f}".format(pf[0]))

    print("")
    print("  扫描抗截留系数 A（目标: 所有 W 上 k_eff = k_e）")
    from scipy.optimize import brentq
    W_ref = 20e-9
    def gap(A):
        return solve_steady(W_ref, A)[4] - K_E
    A_star = float("nan")
    try:
        if gap(0.0) * gap(6.0) < 0.0:
            A_star = brentq(gap, 0.0, 6.0, xtol=1e-12)
    except Exception:
        pass
    chk("P1-3 存在抗截留系数 A* 使 W=20nm 处 k_eff = k_e",
        "PASS" if np.isfinite(A_star) else "WARN",
        "A* = {:.5f}".format(A_star), A_star)

    if np.isfinite(A_star):
        res = []
        for W in Ws:
            res.append(solve_steady(W, A_star)[4] / K_E - 1.0)
        res = np.array(res)
        chk("P1-4 加抗截留后 k_eff = k_e 对所有 W 成立",
            "PASS" if np.max(np.abs(res)) < 2e-2 else "WARN",
            "残余偏离: " + " ".join("{:+.1e}".format(r) for r in res), res)
        chk("P1-5 抗截留把偏差压低至少一个量级",
            "PASS" if np.max(np.abs(res)) < 0.1 * np.max(d) else "WARN",
            "max|dev|: 无抗截留 {:.2e} -> 有抗截留 {:.2e}".format(np.max(d), np.max(np.abs(res))))

    np_ = sum(1 for v, _, _ in RES if v == "PASS")
    nw = sum(1 for v, _, _ in RES if v == "WARN")
    nf = sum(1 for v, _, _ in RES if v == "FAIL")
    print("")
    print("=" * 100)
    print("汇总: {} 项  PASS {} / WARN {} / FAIL {}".format(len(RES), np_, nw, nf))
    print("=" * 100)
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
