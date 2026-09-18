#!/usr/bin/env python3
"""
验证 2a 的**物理正确性**：解出 1D 平衡晶界，量真实晶界能，与 Read-Shockley 目标对比。

【为什么要做这个检查】
  Moelans Algorithm 1 的 (a*, gamma*) 是**针对某个具体的 mu 解出来的**。
  GBAnisotropy 里 mu = mu_qp = 6*sigma_init/w，自洽。
  但本算例的 mu 被**熔化开关**固定在 6*sigma_H/w = 9e5，不能改。
  于是问题变成：用 mu = 9e5 解出的 (kappa*, gamma*)，其
  **实际界面能**是否等于目标 sigma_mn？

  这是"物理正确"的唯一判据 —— 参数对不对不重要，能量对不对才重要。

【理论依据】
  对 gamma = 1.5，两序参量约化下 eta_m + eta_n = 1 是**精确解**
  （两式相减给出 eta(3-2gamma)(1-eta) = 0），约化为经典 phi^4 kink：
      s = tanh(x/delta),  delta = sqrt(2*kappa/mu),  s = eta_m - eta_n
      sigma = mu*delta/3 = sqrt(2*kappa*mu)/3
  各向同性验算：sqrt(2*1.8e-6*9e5)/3 = 1.8/3 = 0.6 = sigma_H ✓
  但 gamma != 1.5 时该约化不成立，必须**数值解**。

用法： python3 check_gb_energy.py
"""

import math
import numpy as np

from gen_aniso import (SIGMA_H, MOB0_H, WGB, MU_QP_ISO, THETA_M,
                       rs_factor, mob_factor, moelans_pair, compute_mu_qp,
                       pair_dtheta, build_orientations)


def solve_gb(sigma_target, kappa, gamma, mu, n=1201, max_step=80000):
    """
    松弛求解两序参量晶界的平衡剖面，返回 (真实界面能, 剖面)。

    解 MOOSE 实际求解的强形式方程（测的就是算例真正在解的东西）：
        kappa * eta_i'' = mu * (eta_i^3 - eta_i + 2*gamma*eta_i*sum_{j!=i} eta_j^2)
    边界：左 eta=(1,0)，右 eta=(0,1)  (Dirichlet，把界面钉在域中央)

    用显式松弛而不是 solve_bvp：这里的方程刚性比 ~1e5（最快模态 kappa/h^2，
    最慢 kappa/span^2），solve_bvp 会把网格加密到爆。显式松弛稳、且够快 ——
    所需步数 = tau/dt = (delta^2/kappa)/(0.25*h^2/kappa) = 4*(delta/h)^2 ≈ 1.8e4。
    """
    # 界面宽度的正确尺度：令 u=eta_m+eta_n, v=eta_m-eta_n，两式相减得
    #     kappa*v'' = mu*(2*gamma-1)*v*(1-v^2)/4    (在 u=1 的近似下)
    # => delta_v = sqrt(4*kappa/(mu*(2*gamma-1)))
    # gamma=1.5 时退化为 sqrt(2*kappa/mu)=2.0e-6；
    # 但低角晶界 gamma~1.03 时 delta_v ~ 1.0e-5，**宽 5 倍**。
    delta_v = math.sqrt(4.0 * kappa / (mu * max(2.0 * gamma - 1.0, 1e-6)))

    span = 12.0 * delta_v            # 域半宽取 12 个界面宽
    x = np.linspace(-span, span, n)
    h = x[1] - x[0]

    s0 = np.tanh(x / delta_v)        # 初值：u=1、v 为 kink
    em = 0.5 * (1 - s0)
    en = 0.5 * (1 + s0)

    dt = 0.25 * h * h / kappa        # 显式稳定条件 dt < 0.5*h^2/kappa
    for step in range(max_step):
        em_xx = np.empty_like(em)
        en_xx = np.empty_like(en)
        em_xx[1:-1] = (em[2:] - 2.0 * em[1:-1] + em[:-2]) / (h * h)
        en_xx[1:-1] = (en[2:] - 2.0 * en[1:-1] + en[:-2]) / (h * h)
        em_xx[0] = em_xx[-1] = 0.0
        en_xx[0] = en_xx[-1] = 0.0

        dm = mu * (em**3 - em + 2.0 * gamma * em * en**2) - kappa * em_xx
        dn = mu * (en**3 - en + 2.0 * gamma * en * em**2) - kappa * en_xx

        em -= dt * dm
        en -= dt * dn
        em[0], em[-1] = 1.0, 0.0
        en[0], en[-1] = 0.0, 1.0

        # 每 500 步查一次是否已到平衡（残差 max|d eta/dt| 足够小）
        if step % 500 == 0 and step > 0:
            if max(np.max(np.abs(dm)), np.max(np.abs(dn))) * dt < 1e-15:
                break
    else:
        raise RuntimeError(f"松弛未达平衡(sigma目标={sigma_target:.5f}, "
                           f"gamma={gamma:.4f}, delta_v={delta_v:.3e})")

    dm_dx = np.gradient(em, x)
    dn_dx = np.gradient(en, x)
    grad = 0.5 * kappa * (dm_dx**2 + dn_dx**2)
    bulk = mu * (em**4 / 4 + en**4 / 4 - (em**2 + en**2) / 2 + gamma * em**2 * en**2)
    # 均匀相 (1,0) 的能量密度 = -mu/4；界面能 = 超出的那部分
    sigma = np.trapezoid(grad + bulk + mu / 4, x)

    return sigma, (x, em, en)


def main():
    n = 8
    th = build_orientations(n)
    pairs = [(m, k) for m in range(n) for k in range(m + 1, n)]

    sig, mobf, dth = {}, {}, {}
    for m, k in pairs:
        d = pair_dtheta(th[m], th[k])
        sig[(m, k)] = SIGMA_H * rs_factor(d)
        mobf[(m, k)] = mob_factor(d)
        dth[(m, k)] = d

    mu_actual = MU_QP_ISO                                     # 熔化开关实际用的 mu
    mu_gbaniso = compute_mu_qp(sig.values())                  # GBAnisotropy 会用的 mu

    print("=" * 88)
    print("1D 平衡晶界能校验：真实 sigma vs 目标 sigma")
    print("=" * 88)
    print(f"  熔化开关的 mu（本算例实际使用）  = {mu_actual:.6g}"
          f"   (= 6*{SIGMA_H}/{WGB:.1g})")
    print(f"  GBAnisotropy 的 mu_qp            = {mu_gbaniso:.6g}"
          f"   (= 6*(sig_max+sig_min)/2/w)")
    print(f"  两者相差 {(mu_gbaniso - mu_actual) / mu_actual:+.2%}")
    print()

    for label, mu in (("用实际 mu (9e5)", mu_actual),
                      ("用 GBAnisotropy 的 mu_qp", mu_gbaniso)):
        print(f"--- {label} 解不动点 ---")
        print(f"{'σ目标':>8} {'a*':>10} {'kappa*':>12} {'gamma*':>8} "
              f"{'delta_v(um)':>12} {'σ真实':>9} {'相对误差':>10}")
        worst = 0.0
        for m, k in pairs:
            _, g_star, kap_star = moelans_pair(sig[(m, k)], mu)
            a_star = kap_star / (WGB * sig[(m, k)])
            dv = math.sqrt(4.0 * kap_star / (mu * (2.0 * g_star - 1.0))) / 1e-6
            s_real, _ = solve_gb(sig[(m, k)], kap_star, g_star, mu)
            err = (s_real - sig[(m, k)]) / sig[(m, k)]
            worst = max(worst, abs(err))
            if abs(err) > 1e-3 or (m, k) == pairs[0]:
                flag = "  <== 偏差大" if abs(err) > 1e-3 else ""
                print(f"{sig[(m,k)]:8.5f} {a_star:10.7f} {kap_star:12.6e} "
                      f"{g_star:8.5f} {dv:12.4f} {s_real:9.5f} {err:+10.2e}{flag}")
        print(f"  最大相对误差（全部 28 对）= {worst:.3e}"
              f"   {'OK' if worst < 1e-3 else '**不通过**'}")
        print()

    # 各向同性自检：手工验算理论公式
    kap_iso = 0.75 * WGB * SIGMA_H
    s_th = math.sqrt(2 * kap_iso * mu_actual) / 3
    print("=" * 88)
    print("理论公式自检（gamma=1.5 精确约化 sigma = sqrt(2*kappa*mu)/3）")
    print("=" * 88)
    s_num, _ = solve_gb(SIGMA_H, kap_iso, 1.5, mu_actual)
    print(f"  kappa=0.75*w*sigma_H, mu=9e5, gamma=1.5")
    print(f"  解析式 sqrt(2*kappa*mu)/3 = {s_th:.10f}")
    print(f"  数值松弛                  = {s_num:.10f}")
    print(f"  相对偏差 {abs(s_num-s_th)/s_th:.2e}   "
          f"{'OK（数值解与解析式一致，说明松弛程序可信）' if abs(s_num-s_th)/s_th < 1e-3 else '**程序有问题**'}")


if __name__ == "__main__":
    main()
