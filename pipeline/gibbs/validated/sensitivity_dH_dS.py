#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【A1/A3 敏感性】把"数据缺口"变成**量化的不确定度带**。

A1  ΔS_seg：文献不存在。做法：**锚点照样钉在 Tan 2016 的 923 K**（那是最硬的实测），
     ΔH_seg 由 ΔG_seg(923) = ΔH − 923·ΔS 反解 ⇒ 改 ΔS 不改低温、只改**高温外推**。
     这里扫 ΔS = 0 / ±1R / ±2R，报 Γ(1950 K) 与 s(1950 K) 的带宽。

A3  δ·D_GB(T)：生产给的是一个**指派常数** 4e-10 m²/s（没说在哪个温度）。
     做法：把它当作 T_ref = 1950 K 的值，加 Arrhenius 因子
         D_GB(T) = D_ref·exp(−Q_GB/R·(1/T − 1/T_ref))
     扫 Q_GB（0.4/0.6/0.8 × Q_lattice），报 900–1200 K 的放大倍数。

用法（WSL 里 conda activate ml 或任意有 numpy 的环境；纯标准库也行）：
    python3 sensitivity_dH_dS.py
"""
import math

R = 8.314462618
AVOG = 6.02214076e23
GAM0 = 2.1421e-5           # mol/m^2
RHOMOL = 101292.8831       # mol/m^3
C0 = 0.036
T_ANCHOR = 923.0
# Tan 2016 锚点：Γ_V(923 K) = 2.2 at/nm^2（下界）
G_ANCHOR_ATNM2 = 2.2
G_ANCHOR = G_ANCHOR_ATNM2 / AVOG * 1e18   # mol/m^2


def dG_at(T, dH, dS):
    return dH - T * dS


def dH_from_anchor(dS):
    """由锚点反解 ΔH：Γ_anchor = A_s(923)·c0 = Γ0·exp(−ΔG/(RT))·c0"""
    # exp(−ΔG/(R·T_anchor)) = Γ_anchor/(Γ0·c0)
    K = G_ANCHOR / (GAM0 * C0)
    dG = -R * T_ANCHOR * math.log(K)
    return dG + T_ANCHOR * dS, dG


def report_A1():
    print("=" * 78)
    print("【A1】ΔS_seg 的敏感度：锚点钉在 Tan 2016 的 923 K，看高温外推的变化")
    print("=" * 78)
    print("  ΔS_seg        ΔH_seg[kJ/mol]   K(1950K)   s(1950K)   Γ(1950K)[at/nm²]")
    for dS_over_R in (0.0, 1.0, -1.0, 2.0, -2.0):
        dS = dS_over_R * R
        dH, _ = dH_from_anchor(dS)
        K = math.exp(-dG_at(1950.0, dH, dS) / (R * 1950.0))
        s = K / (1 + C0 * (K - 1))         # Langmuir；Henry 极限下 s≈K
        Gam = GAM0 * K * C0 / (1 + C0 * (K - 1))
    print("   %+4.1f R      %9.2f        %7.3f    %7.3f      %6.3f"
              % (dS_over_R, dH / 1000, K, s, Gam * AVOG / 1e18))
    print("  ⇒ 读数：ΔS = ±2R 时 Γ(1950 K) 的相对带宽就是**这个数据缺口的真实代价**。")
    print()
    print("  ★ 结论：ΔS_seg 在 **1950 K 是一阶量**（±2R ⇒ Γ 差 2.5~7 倍），不是小修正。")
    print("  ★ 可行的'不用文献猜'路线 —— **补偿效应**（GB 偏析的经典经验关系）：")
    dH0, _ = dH_from_anchor(0.0)
    for beta in (3.0, 4.0, 6.0):
        dS_est = dH0 / (beta * 1943.0)          # δ 相熔点 ~1943 K
        dH_e, _ = dH_from_anchor(dS_est)
        K = math.exp(-dG_at(1950.0, dH_e, dS_est) / (R * 1950.0))
        Gam = GAM0 * K * C0 / (1 + C0 * (K - 1))
        print("     ΔS ≈ ΔH/(β·T_m)，β=%.1f ⇒ ΔS = %+.3f J/mol/K (= %+.2f R)"
              "  ⇒ Γ(1950K) = %.3f at/nm²"
              % (beta, dS_est, dS_est / R, Gam * AVOG / 1e18))
    print("     ⇒ 给出的是 -0.1 ~ -0.3 R 量级、Γ(1950K) 只降 ~5~15%% ⇒ **可以带误差棒使用**。")


def report_A3():
    print()
    print("=" * 78)
    print("【A3】δ·D_GB(T)：把生产那个指派常数当 1950 K 的值，看 900–1200 K 的外推")
    print("=" * 78)
    Q_lat = 3.234          # eV：生产 [L_mobility] 里 GB *迁移率* 的 Q（同源 Ti64 β）
    print("  取 Q_GB = f × Q_lattice（Q_lattice = %.3f eV）；D_GB(1950K) = 4e-10 m²/s" % Q_lat)
    D_S_ref = 4.0e-13      # 生产 D_S
    D_GB_ref = 4.0e-10     # 生产（指派）D_GB
    ratio_ref = D_GB_ref / D_S_ref
    print("  真正有物理意义的是**晶界相对体相的倍数** D_GB/D_S（低温下晶界优势才显现）")
    print("     f      Q_GB[eV]   D_GB/D_S(1950K)   (1500K)    (1200K)    (900K)")
    for f in (0.4, 0.5, 0.6, 0.8):
        Q = f * Q_lat
        # D ∝ exp(−Q/kT)：用 eV/kB = 11604.5 K
        def r(T):
            return ratio_ref * math.exp(-(Q - Q_lat) * 11604.5 * (1.0 / T - 1.0 / 1950.0))
        print("     %.1f     %6.3f      %7.2f          %8.1f   %9.1f  %9.1f"
              % (f, Q, r(1950.0), r(1500.0), r(1200.0), r(900.0)))
    print("  ⇒ 读数：这决定「阶段 2（900–1200 K）晶界扩散通道到底比体相快多少量级」。")
    print("     ⚠ 生产那个 4e-10 是**指派值**；上表的 f 也只是占位 ⇒ 这条必须由用户定。")


if __name__ == "__main__":
    report_A1()
    report_A3()
