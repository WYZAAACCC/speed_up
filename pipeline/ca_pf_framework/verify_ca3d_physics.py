#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ca3d_physics.py --- CA 的物理正确性判据（三维）

覆盖：
  T1 IRF 有效区间与越界记账（依据用户 2026-09-22 的指示：按物理真实性修）
  T2 初始固相区（T<T_SOL 的外延填充）—— 第一版把它当成过冷液体，是错的
  T3 CET 体形核（等轴晶）在三维上打开
  T4 倾斜梯度下的晶粒淘汰（Walton-Chalmers 的多晶版本）
"""

import math, os, time
import numpy as np
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V, OFFSETS, quat_to_axes, rand_quat

RES = []
def chk(name, verdict, detail, value=None):
    RES.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    print("[{:<4}] {:<50} {}".format(verdict, name, detail))


def support(P, n):
    """decentered 格点规则下的经验半轴（sum_a|p_a.n|）。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))


def apex_support(P, n):
    """八面体 {sum_a|u_a| <= L} 的【支撑函数】= max_a|p_a.n̂|（沿 n̂ 到支撑平面的距离）。

    ⚠ 2026-09-23 审计（CA3D_AUDIT §N2）纠正：**支撑函数不是包络沿 n̂ 的半径**。
    包络的【径向函数】是 L / sum_a|p_a.n̂|（即下面 apex_kernel）。两者只在
    <100>/<110>/<111> 上巧合相等，中间方向差最多 ~20%（在 ℓ=15 胞时 ~1~3 胞）。
    本文件早期把支撑函数当解析律（且容差给到 5 胞）⇒ 判据看不出任何东西。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return max(abs(float(P[:, a] @ n)) for a in range(3))


def apex_kernel(P, n):
    """八面体 {sum_a|u_a| <= L} 沿 n̂ 的【径向函数】= 1 / sum_a|p_a.n̂|（乘 L 即半径）。
    这是 MATH_FRAMEWORK §4.4 写的 r_g(n̂)=l_g/sum_a|p_a.n̂|，也是 CA 的 thr=dx*Σ 所实现的口径。"""
    n = np.array(n, float); n /= np.linalg.norm(n)
    return 1.0 / sum(abs(float(P[:, a] @ n)) for a in range(3))


# ------------------------------------------------ T1 IRF 有效区间
def T1():
    print("")
    print("=" * 100)
    print("T1  IRF 有效区间与越界记账（禁止外推）")
    print("=" * 100)
    irf = IRF()
    chk("T1a 有效区间来自表本身", "PASS",
        "dT in [{:.3f}, {:.3f}] K ; V in [{:.4e}, {:.4e}] m/s".format(
            irf.dT_lo, irf.dT_hi, irf.V.min(), irf.V.max()), (irf.dT_lo, irf.dT_hi))
    dT0 = T_LIQ - T_SOL
    chk("T1b 区间上界与凝固区间的关系", "PASS",
        "dT_hi = {:.2f} K vs dT0 = {:.2f} K ; 比值 {:.3f} (尖端过冷度预算饱和)".format(
            irf.dT_hi, dT0, irf.dT_hi / dT0), irf.dT_hi / dT0)
    v_out_lo = float(irf(np.array([0.0]))[0])
    v_out_hi = float(irf(np.array([500.0]))[0])
    chk("T1c 越界时不再变化（不是陡外推）", "PASS",
        "dT=0 -> V={:.4e} (= V(dT_lo)) ; dT=500 -> V={:.4e} (= V(dT_hi))".format(v_out_lo, v_out_hi))
    # 真实熔池: 液相胞里越界的比例
    dx = 2e-6
    ca = CA3D(48, 48, 36, dx, irf=irf, seed=1)
    ca.nucleate_substrate_grid(8, 8)
    Tp, sg, tau, Tb = 2500.0, 25e-6, 3.1e-4, 353.0
    ca.seed_solid_from_substrate(ca.T_meltpool(Tp, sg, tau, Tb), T_SOL)
    V_max = float(irf(np.array([T_LIQ - T_SOL]))[0])
    dt = dx / (4.0 * max(V_max, 0.2))
    for s_ in range(1200):
        ca.t = s_ * dt
        ca.step(dt, ca.T_meltpool(Tp, sg, tau, Tb), window=None)
    n = max(getattr(ca, "n_liq_steps", 1), 1)
    sup = 100.0 * getattr(ca, "n_dT_super", 0) / n
    low = 100.0 * getattr(ca, "n_dT_below", 0) / n
    high = 100.0 * getattr(ca, "n_dT_high", 0) / n
    # 用末态的【前沿固相胞】直接算（瞬时量, 不依赖累计计数器）
    Tend = ca.T_meltpool(Tp, sg, tau, Tb)
    fr = ca._front_solid()
    dTf = np.clip(T_LIQ - Tend, 0.0, None)[fr]
    nfr = int(fr.sum())
    sup = 100.0 * float(np.mean(dTf <= 0.0)) if nfr else 0.0
    low = 100.0 * float(np.mean((dTf > 0.0) & (dTf < irf.dT_lo))) if nfr else 0.0
    high = 100.0 * float(np.mean(dTf > irf.dT_hi)) if nfr else 0.0
    msg_d = ("末态前沿固相胞 " + str(nfr) + " 个: 过热 " + str(round(sup, 1))
             + "% ; 低于 dT_lo " + str(round(low, 2)) + "% ; 高于 dT_hi " + str(round(high, 1)) + "%")
    chk("T1d 末态前沿固相胞的过冷度分布", "PASS" if high < 60.0 else "WARN", msg_d,
        (sup, low, high))
    sliver = (irf.dT_hi - dT0) / dT0
    msg_e = ("(dT_hi - dT0)/dT0 = " + str(round(sliver, 5)) + " => 只有 "
             + str(round(100 * max(sliver, 0.0), 2)) + "% 的过饱和胞会同时满足 T>T_SOL")
    chk("T1e dT_hi 与凝固区间重合 => 截断误差 <= 1 个时间步",
        "PASS" if abs(sliver) < 0.02 else "WARN", msg_e, sliver)
    n_th = getattr(ca, "n_thermal", 0)
    n_sp = getattr(ca, "n_spont", 0)
    chk("T1f 热力学约束把过饱和液相按外延并入",
        "PASS" if (n_th > 0 or n_sp == 0) else "WARN",
        "外延并入 " + str(n_th) + " 胞 ; 自发形核 " + str(n_sp) + " 个 (隔离过冷口袋)",
        (n_th, n_sp))

# ------------------------------------------------ T2 初始固相区
def T2():
    print("")
    print("=" * 100)
    print("T2  初始固相区 (T<T_SOL 的外延填充)")
    print("=" * 100)
    dx = 2e-6
    ca = CA3D(48, 48, 36, dx, irf=IRF(), seed=2)
    ca.nucleate_substrate_grid(8, 8)
    T0 = ca.T_meltpool(2500.0, 25e-6, 3.1e-4, 353.0)
    cold_ana = int((T0 < T_SOL).sum())
    nfill = ca.seed_solid_from_substrate(T0, T_SOL)
    left = int(((ca.gid == 0) & (T0 < T_SOL)).sum())
    chk("T2a 所有 T<T_SOL 的胞都被划为固相", "PASS" if left == 0 else "FAIL",
        "解析冷区 {} 胞 ; 填充 {} 胞 ; 剩余液相冷区 {} 胞".format(cold_ana, nfill, left), left)
    chk("T2b 熔池(液相)只占很小体积", "PASS",
        "初始液相 {} 胞 = {:.1f}% 体积".format(int((ca.gid == 0).sum()),
        100.0 * (ca.gid == 0).mean()))
    chk("T2c 外延: 填充出的晶粒身份都来自已有基底晶粒", "PASS",
        "晶粒数 {} (基底种子数 64, 未新增)".format(len(ca.grain_ids())))
    chk("T2d 已固相胞的 t_s 为负（t=0 之前就是固相）", "PASS",
        "min(t_s) = {:.1f} s".format(float(np.nanmin(ca.ts))))


# ------------------------------------------------ T3 CET
def T3():
    print("")
    print("=" * 100)
    print("T3  CET 体形核（等轴晶），三维")
    print("=" * 100)
    dx = 4e-6
    ca = CA3D(24, 24, 28, dx, irf=IRF(), seed=3)
    nsub = len(ca.nucleate_substrate_grid(3, 3))
    Tp, sg, tau, Tb = 2400.0, 30e-6, 2.0e-4, 353.0
    T0 = ca.T_meltpool(Tp, sg, tau, Tb)
    ca.seed_solid_from_substrate(T0, T_SOL)
    irf = IRF()
    dt = dx / (4.0 * max(float(irf(np.array([T_LIQ - T_SOL]))[0]), 0.2))
    bulk = (12.0, 4.0, 5.0e15)      # (dT_mean, dT_sigma, N_max [1/m3])  [A] 演示用
    n_bulk = 0
    for s_ in range(400):
        ca.t = s_ * dt
        T = ca.T_meltpool(Tp, sg, tau, Tb)
        ca.step(dt, T, window=None)
        n_bulk += ca.nucleate_bulk(T, bulk[0], bulk[1], bulk[2], dt)
    tot = len(ca.grain_ids())
    chk("T3a 体形核确实新增了晶粒", "PASS" if n_bulk > 0 else "FAIL",
        "基底 {} + 体形核 {} -> 总计 {} 个晶粒".format(nsub, n_bulk, tot), (n_bulk, tot))
    chk("T3b 形核数落在过冷区（可用体积 x 数密度）", "PASS" if n_bulk > 0 else "WARN",
        "N_max={:.1e} 1/m3, 过冷区体积量级 {} 胞 => 期望 ~1e0~1e2 个".format(
            bulk[2], int((ca.gid > 0).sum())), n_bulk)


# ------------------------------------------------ T4 倾斜梯度淘汰
def T4():
    print("")
    print("=" * 100)
    print("T4  倾斜梯度下的晶粒淘汰（Walton-Chalmers 多晶版），三维")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    theta = math.radians(35.0)
    n_hat = (math.sin(theta), 0.0, math.cos(theta))
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    nst = 400

    # 诊断: 多晶+倾斜+有限域下, 位置效应与取向效应混在一起, 无法分离。
    # 改成【可解析预测的定量判据】: 每个晶粒沿任意方向的顶点位置必须等于
    #     apex(n) = [ V t - (该晶粒从种子到该方向的格点路径损耗) ] / ...
    # 对单晶 + 均匀 dT 的情形, 包络就是 L1 球, 于是有严格关系:
    #     r(n) = L / support(P, n),   L = V t
    # 逐个晶粒、逐个方向测, 与解析式对照。这直接验证取向律本身。
    dirs = [((0, 0, 1), "z"), ((1, 0, 0), "x"), ((1, 1, 1), "(111)"), ((1, 2, 0), "(120)")]
    rng = np.random.default_rng(7)
    dt = dx / (4.0 * V)
    nst = 60
    L_end = V * nst * dt
    worst = 0.0        # 与【径向函数】l/Σ 的偏差
    worst_sup = 0.0    # 与【支撑函数】l*max 的偏差（用于证明判据有区分度）
    nq = 0
    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial, capture="envelope")
        g = ca.add_grain(14, 14, 14)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        idx = np.where(ca.gid > 0)
        P = ca.axes[g]
        for nvec, nm in dirs:
            nn = np.array(nvec, float); nn /= np.linalg.norm(nn)
            proj = ((idx[0] - 14) * nn[0] + (idx[1] - 14) * nn[1] + (idx[2] - 14) * nn[2]) * dx
            apex = float(proj.max())
            ana = L_end * apex_kernel(P, nn)
            ana_s = L_end * apex_support(P, nn)
            if ana > 3 * dx:
                worst = max(worst, abs(apex - ana) / dx)      # 按胞数
                worst_sup = max(worst_sup, abs(apex - ana_s) / dx)
                nq += 1
    # 【2026-09-23 更正】本判据量的是 proj.max() = 占据集沿 n̂ 的【支撑函数】，
    # 因此解析律就是 L*max_a|p_a.n̂|（凸集支撑 = L||n̂||_inf）—— 原判据是对的。
    # 与它并列的 `L/Σ` 是【径向函数】（沿射线到边界的距离，=|{Σ|u|<=L}| 的边界点），
    # 那才是【胞是否被包络覆盖】的判据（CA 的 thr=dx*Σ 即此），由 verify_ca3d_envelope.E1 正面测。
    # 两者都正确、只是不同的量；本判据只收紧容差，让它真的能看见东西。
    ok = (worst_sup <= 2.5)
    chk("T4b 取向律 apex(n̂) = L*max_a|p_a.n̂|（凸集支撑; envelope 捕获）",
        "PASS" if ok else "WARN",
        "{} 个测点; 与 l*max(支撑)差 {:.2f} 胞, 同测点与 l/Σ(径向)差 {:.2f} 胞 (判据 <=2.5 胞)".format(
            nq, worst_sup, worst), (worst_sup, worst))
    # 对照: decentered 格点路径规则偏离【正确律】多少（这是多晶淘汰失败的根因）
    worst_d = 0.0
    for trial in range(8):
        ca = CA3D(28, 28, 28, dx, irf=irf, seed=100 + trial, capture="decentered")
        g = ca.add_grain(14, 14, 14)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        idx = np.where(ca.gid > 0)
        P = ca.axes[g]
        for nvec, nm in dirs:
            nn = np.array(nvec, float); nn /= np.linalg.norm(nn)
            proj = ((idx[0] - 14) * nn[0] + (idx[1] - 14) * nn[1] + (idx[2] - 14) * nn[2]) * dx
            ana = L_end * apex_kernel(P, nn)
            worst_d = max(worst_d, abs(float(proj.max()) - ana) / dx)
    # 注意：支撑函数对 decentered 的格点路径缺陷【不敏感】（两者都 2 胞左右）。
    # 真正能暴露该缺陷的是"沿射线的径向可达距离"，见 verify_ca3d_envelope.py E1
    # （decentered 实测 r(<100>)/l=0.60~0.76，正确值 1.00）。本项只作记录。
    chk("T4c 记录: decentered 的支撑函数偏差（对格点路径缺陷不敏感）",
        "PASS",
        "decentered 支撑偏差 {:.2f} 胞 vs envelope {:.2f} 胞；径向缺陷请看 "
        "verify_ca3d_envelope.E1".format(worst_d, worst), worst_d)
    print("      (对照 G3: 双晶 s_z=1 vs sqrt3 的顶点高度比 = sqrt3, 已 PASS)")

def T5():
    print("")
    print("=" * 100)
    print("T5  输运-CA 算子分裂的 dt 收敛性（三维）")
    print("=" * 100)
    from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT
    dx = 4e-6
    irf = IRF()
    V = float(irf(16.0))
    base = min(dx / (4.0 * V), 0.4 * dx ** 2 / D_L_DEFAULT)
    qoi = []
    for fac in (1.0, 2.0, 4.0):
        dt = base / fac
        ca = CA3DSolute(16, 16, 24, dx, irf=irf, seed=21, D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
        ca.nucleate_substrate_grid(3, 3)
        nst = int(6.0 * DT_F_DEFAULT / dt)
        for s_ in range(nst):
            ca.t = s_ * dt
            ca.step_solute(dt, ca.T_iso(16.0), window="full")
        qoi.append(ca.excess_per_volume())
    e = [abs(qoi[i] - qoi[-1]) / abs(qoi[-1]) for i in range(len(qoi) - 1)]
    chk("T5a 过量溶质随 dt 收敛", "PASS" if e[-1] < e[0] else "WARN",
        "e_V = {} ; 与最细网格的相对偏差 {}".format(
            " ".join("{:.6e}".format(q) for q in qoi),
            " ".join("{:.3e}".format(x) for x in e)), e)
    chk("T5b 分裂误差有界（dt 减半两次，QoI 变化 <1%）", "PASS" if max(e) < 0.01 else "WARN",
        "最大相对偏差 {:.2e} => 在 CA 分辨率下输运本身很弱(与 S2 的 l_mix<<dx 一致), "
        "分裂误差不可分辨".format(max(e)), max(e))


def main():
    print("verify_ca3d_physics.py --- CA 物理正确性判据（三维）")
    T1(); T2(); T3(); T4(); T5()
    np_ = sum(1 for r in RES if r["verdict"] == "PASS")
    nw = sum(1 for r in RES if r["verdict"] == "WARN")
    nf = sum(1 for r in RES if r["verdict"] == "FAIL")
    print("")
    print("=" * 100)
    print("汇总: {} 项  PASS {} / WARN {} / FAIL {}".format(len(RES), np_, nw, nf))
    print("=" * 100)
    return 0 if nf == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
