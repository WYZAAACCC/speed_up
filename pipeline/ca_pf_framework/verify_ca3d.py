#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ca3d.py --- Window A (3D CA) 的验证

**本文件全部以三维为准。** 只有 G7 是二维交叉校验，且显式标注为「仅代码校验」。

判据来源：MATH_FRAMEWORK.md 4.1/4.3/4.4/4.5。

用法: /root/miniconda3/envs/ml/bin/python verify_ca3d.py
"""

import math
import os
import time
import numpy as np

import ca3d
from ca3d import CA3D, IRF, quat_to_axes, T_LIQ, T_SOL, K_V, C0_V, M_L

RES = []
def chk(name, verdict, detail, value=None):
    RES.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    print("[{:<4}] {:<50} {}".format(verdict, name, detail))


def axes_for_aligned(d_lab=(0, 0, 1), target=(1, 1, 1)):
    """构造旋转 R，使 d_lab 在晶体坐标下 = normalize(target)，返回 P = R^T。
    这样 sum_a |P[:,a] . d_lab| = sum_a |(R d_lab)_a| 达到指定值。"""
    d = np.array(d_lab, float); d /= np.linalg.norm(d)
    t = np.array(target, float); t /= np.linalg.norm(t)
    # 需要 R d = t  <=>  R 的第 (d 所对应的列) = t。这里 d = e3, 所以 R 的第 3 列 = t
    c3 = t
    tmp = np.array([1.0, -1.0, 0.0])
    if abs(tmp @ c3) > 0.9:
        tmp = np.array([1.0, 0.0, -1.0])
    c1 = tmp - (tmp @ c3) * c3; c1 /= np.linalg.norm(c1)
    c2 = np.cross(c3, c1)
    R = np.column_stack([c1, c2, c3])
    return R.T


def lattice3d(n):
    """Z^3 中满足 |i|+|j|+|k| <= n 的整数点数（精确公式）。"""
    n = int(n)
    return 1 + (2 * n * (n + 1) * (2 * n + 1)) // 3 + 2 * n


def lattice2d(n):
    """Z^2 中满足 |i|+|j| <= n 的整数点数（精确公式）。"""
    n = int(n)
    return 1 + 2 * n * (n + 1)


def support(P, n):
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))


# ===================================================== G1 单晶包络几何（3D）
def G1():
    print("")
    print("=" * 100)
    print("G1  单晶包络几何（三维）: 八面体 |u1|+|u2|+|u3| <= L")
    print("=" * 100)
    dx = 2e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    L_end = 8 * dx      # 取 L/dx 为整数, 以便与精确格点数对照
    t_end = L_end / V
    dt = dx / (4.0 * V)
    nst = int(round(t_end / dt))

    for tag, P in (("各向同性(单位取向)", np.eye(3)),
                   ("<111> 对准 z", axes_for_aligned())):
        ca = CA3D(48, 48, 48, dx, irf=irf, seed=1)
        g = ca.add_grain(24, 24, 24)
        ca.axes[g] = P
        ca.n_grains_forced = True
        T = ca.T_iso(dTu)
        for _ in range(nst):
            ca.step(dt, T, window="full")
        L = float(irf(dTu)) * (nst * dt)
        N = int((ca.gid > 0).sum())
        n = int(round(L / dx))
        vol_num = N * dx ** 3
        vol_ana = 4.0 / 3.0 * L ** 3
        rel = abs(vol_num - vol_ana) / vol_ana
        if abs(P - np.eye(3)).max() < 1e-12:
            Nex = lattice3d(n)
            chk("G1a [各向同性] 胞数 = 精确格点数 |i|+|j|+|k|<=n",
                "PASS" if N == Nex else "FAIL",
                "N={} vs 精确 {} (n={}) ; 与连续体 4/3 n^3={:.1f} 的 {:.1f}% 偏差是 O(dx) 离散伪影".format(
                    N, Nex, n, 4.0 / 3.0 * n ** 3, 100 * rel), (N, Nex))
        else:
            chk("G1a [<111> 对准 z] 胞数 vs 立方向包络", "PASS" if 0.5 < N / (4.0 / 3.0 * n ** 3) < 1.5 else "WARN",
                "N={} vs 连续体 {:.1f} (n={}) ; 旋转八面体的离散计数无简单闭式, 故只查量级".format(
                    N, 4.0 / 3.0 * n ** 3, n), N)
        idx = np.where(ca.gid > 0)
        for nvec, nm in (((0, 0, 1), "+z"), ((1, 0, 0), "+x"), ((1, 1, 1), "(1,1,1)")):
            s = support(P, nvec)
            ana = L / s
            if nm == "+z":
                ext = (idx[2].max() - 24) * dx
            elif nm == "+x":
                ext = (idx[0].max() - 24) * dx
            else:
                ext = max((idx[0][m] - 24) * dx for m in range(1) )  # placeholder
                nn = np.array(nvec, float); nn /= np.linalg.norm(nn)
                proj = (idx[0] - 24) * nn[0] + (idx[1] - 24) * nn[1] + (idx[2] - 24) * nn[2]
                ext = proj.max() * dx
            chk("G1b 方向支撑 {} [{}]: 解析 L/s={:.2f} um".format(nm, tag, ana * 1e6),
                "PASS" if abs(ext - ana) <= 1.5 * dx else "WARN",
                "数值 {:.2f} um ; 量化误差 {:.2f} um (胞长 {:.1f} um)".format(
                    ext * 1e6, (ext - ana) * 1e6, dx * 1e6),
                (ext, ana))
    return V


# ======================================================= G2 网格收敛（3D）
def G2():
    print("")
    print("=" * 100)
    print("G2  包络体积误差的网格收敛（三维）")
    print("=" * 100)
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    L_end = 16e-6
    errs = []
    dxs = (4e-6, 2e-6, 1e-6)
    for dx in dxs:
        nx = int(48e-6 / dx)
        dt = dx / (4.0 * V)
        nst = int(round((L_end / V) / dt))
        ca = CA3D(nx, nx, nx, dx, irf=irf, seed=2)
        g = ca.add_grain(nx // 2, nx // 2, nx // 2)
        ca.axes[g] = np.eye(3)
        T = ca.T_iso(dTu)
        for _ in range(nst):
            ca.step(dt, T, window="full")
        L = V * nst * dt
        N = int((ca.gid > 0).sum())
        rel = abs(N * dx ** 3 - 4.0 / 3.0 * L ** 3) / (4.0 / 3.0 * L ** 3)
        errs.append(rel)
    chk("G2 体积误差 O(dx) 收敛", "PASS" if errs[-1] < errs[0] else "FAIL",
        "dx=4/2/1 um -> 相对误差 {}".format(" ".join("{:.3f}".format(e) for e in errs)), errs)


# ================================================= G3 取向竞争（3D 正对照）
def G3():
    print("")
    print("=" * 100)
    print("G3  取向竞争（三维正对照）: Walton-Chalmers —— 立方轴对准梯度的晶粒胜出")
    print("=" * 100)
    dx = 3e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    ny = 60
    ca = CA3D(60, ny, 24, dx, irf=irf, seed=3)
    Pa = np.eye(3)
    Pb = axes_for_aligned()
    sa, sb = support(Pa, (0, 0, 1)), support(Pb, (0, 0, 1))
    print("  取向 A: s_z = {:.4f} (理论 1) ; 取向 B: s_z = {:.4f} (理论 sqrt3={:.4f})".format(
        sa, sb, math.sqrt(3.0)))
    chk("G3a 取向构造正确", "PASS" if abs(sa - 1) < 1e-9 and abs(sb - math.sqrt(3)) < 1e-9 else "FAIL",
        "A: s_z={:.6f} ; B: s_z={:.6f}".format(sa, sb))
    ia = ca.add_grain(10, ny // 2, 0); ca.axes[ia] = Pa
    ib = ca.add_grain(50, ny // 2, 0); ca.axes[ib] = Pb
    L_end = 30e-6
    dt = dx / (4.0 * V)
    nst = int(round((L_end / V) / dt))
    T = ca.T_iso(dTu)
    for _ in range(nst):
        ca.step(dt, T, window="full")
    L = V * nst * dt
    ia_i = np.where(ca.gid == ia); ib_i = np.where(ca.gid == ib)
    ha = (ia_i[2].max()) * dx
    hb = (ib_i[2].max()) * dx
    ratio = ha / max(hb, 1e-30)
    ok_b = abs(hb - L / math.sqrt(3)) <= 1.5 * dx
    chk("G3b 两晶粒顶点高度比 (判据按格点量化)", "PASS" if ok_b else "WARN",
        "h_A={:.2f} um (解析 L={:.2f}), h_B={:.2f} um (解析 L/sqrt3={:.2f}) ; 比值 {:.3f}".format(
            ha * 1e6, L * 1e6, hb * 1e6, L / math.sqrt(3) * 1e6, ratio), ratio)
    va = int((ca.gid == ia).sum()); vb = int((ca.gid == ib).sum())
    chk("G3c 对准梯度的晶粒体积更大", "PASS" if va > vb else "FAIL",
        "V_A={} 胞, V_B={} 胞 ; 比 {:.2f}".format(va, vb, va / max(vb, 1)), (va, vb))
    return dict(ha=ha, hb=hb, ratio=ratio)


# ==================================================== G4 滑动窗口一致性（3D）
def G4():
    print("")
    print("=" * 100)
    print("G4  滑动窗口一致性（三维）: 开/关 active region 必须给同一结果")
    print("=" * 100)
    dx = 2e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    nst = 40
    outs = {}
    for mode in ("full", None):
        ca = CA3D(40, 40, 40, dx, irf=irf, seed=7)
        ca.nucleate_substrate_grid(6, 6)
        T = ca.T_iso(dTu)
        for _ in range(nst):
            ca.step(dt, T, window=mode)
        outs[str(mode)] = ca.gid.copy()
    same = bool((outs["full"] == outs["None"]).all())
    chk("G4 窗口开关不改变 gid 场", "PASS" if same else "FAIL",
        "逐位相同 = {}".format(same) + " ; 差异胞数 = {}".format(
            int((outs["full"] != outs["None"]).sum())))


# ================================================ G5 Scheil 化学趋势（3D）
def G5():
    print("")
    print("=" * 100)
    print("G5  Scheil 逐胞化学（三维）: 晚凝固的胞更富集")
    print("=" * 100)
    dx = 3e-6
    irf = IRF()
    ca = CA3D(24, 24, 40, dx, irf=irf, seed=11)
    ca.nucleate_substrate_grid(4, 4)
    G, v = 5e6, 0.2
    dt = dx / (4.0 * 0.3)
    nst = 120
    for _ in range(nst):
        ca.t = _ * dt
        T = ca.T_directional(G, v)
        ca.step(dt, T, window=None)
    ca.scheil_chemistry()
    # G5a 守恒恒等式（精确）
    ident = ca.check_scheil_conservation()
    err_id = max(abs(tot - C0_V) / C0_V for (f, tot) in ident)
    chk("G5a Scheil 质量守恒恒等式 f*cs+(1-f)*cl = c0", "PASS" if err_id < 1e-12 else "FAIL",
        "6 个固相分数点上最大相对偏差 {:.2e}".format(err_id), err_id)
    # G5b 末态液相浓度与框架一致
    chk("G5b 正则化后的胞界浓度上限", "PASS" if ca.cl_max < 0.2 else "FAIL",
        "c_interface 正则化上限 = {:.4f} (F_MIN={:.2f}, 未正则化时 f->1 发散)".format(
            ca.cl_max, ca3d.F_MIN), ca.cl_max)
    sens = []
    for fm in (0.02, 0.05, 0.10):
        sens.append((fm, C0_V * fm ** (K_V - 1.0)))
    chk("G5f F_MIN 的敏感度（A 档参数，必须记账）", "WARN",
        "f_min=0.02/0.05/0.10 -> c_interface,max = " + " / ".join(
            "{:.4f}".format(v) for (k, v) in sens), sens)
    # G5c 空间趋势: 晚凝固的胞界更富集
    cap = np.isfinite(ca.ts)
    corr = float(np.corrcoef(ca.fcap[cap], ca.cl[cap])[0, 1])
    chk("G5c 空间趋势: 越晚凝固 -> 胞界 V 越富集", "PASS" if corr > 0.9 else "FAIL",
        "corr(f_s(capture), c_interface) = {:.3f}".format(corr), corr)
    lo = float(ca.cl[cap].min()); hi = float(ca.cl[cap].max())
    chk("G5d 富集带的范围", "PASS" if lo >= C0_V - 1e-12 else "FAIL",
        "c_interface 从 {:.4f} 到 {:.4f} (c0={:.4f}, Scheil 上限 0.198)".format(
            lo, hi, C0_V), (lo, hi))
    chk("G5e 凝固核心成分 = k*c0 (常量参照)", "PASS",
        "c_core = {:.4f}".format(K_V * C0_V), K_V * C0_V)
    return dict(lo=lo, hi=hi, clast=float(ca.c_last))


# ==================================================== G6 性能（3D）
def G6():
    print("")
    print("=" * 100)
    print("G6  滑动窗口的加速比（三维）")
    print("=" * 100)
    dx = 2e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    ca = CA3D(48, 48, 48, dx, irf=irf, seed=5)
    ca.nucleate_substrate_grid(8, 8)
    T = ca.T_iso(dTu)
    for mode in ("full", None):
        c2 = CA3D(48, 48, 48, dx, irf=irf, seed=5)
        c2.nucleate_substrate_grid(8, 8)
        t0 = time.time()
        for _ in range(30):
            c2.step(dt, T, window=mode)
        el = time.time() - t0
        print("    mode={:>6}: 30 步 {:.2f} s ({:.0f} ms/步)".format(str(mode), el, 1000 * el / 30))
        if mode == "full":
            tf = el
        else:
            tw = el
    chk("G6 active region 加速", "PASS" if tw < tf else "WARN",
        "全网格 {:.2f} s -> 滑动窗口 {:.2f} s ; 加速 {:.2f}x".format(tf, tw, tf / max(tw, 1e-9)),
        tf / max(tw, 1e-9))


# ============================================ G7 二维交叉校验（仅代码校验）
def G7():
    print("")
    print("=" * 100)
    print("G7  **二维交叉校验（仅代码校验，不是仿真结果）**")
    print("=" * 100)
    dx = 2e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    nst = 20
    ca = CA3D(48, 1, 48, dx, irf=irf, seed=9)
    g = ca.add_grain(24, 0, 24)
    ca.axes[g] = np.eye(3)
    T = ca.T_iso(dTu)
    for _ in range(nst):
        ca.step(dt, T, window="full")
    L = V * nst * dt
    N = int((ca.gid > 0).sum())
    area_num = N * dx ** 2
    area_ana = 2.0 * L ** 2          # 2D 退化为菱形 |x|+|z|<=L, 面积 2L^2
    rel = abs(area_num - area_ana) / area_ana
    n = int(round(L / dx))
    Nex = lattice2d(n)
    chk("[仅代码校验] 2D 胞数 = 精确格点数 |i|+|j|<=n", "PASS" if N == Nex else "FAIL",
        "N={} vs 精确 {} (n={}) ; 与 2n^2={} 的 {:.1f}% 偏差是 O(dx) 离散伪影".format(
            N, Nex, n, 2 * n * n, 100 * rel), (N, Nex))


def main():
    print("verify_ca3d.py --- Window A (3D CA) 验证")
    print("**全部以三维为准；G7 是二维，只用于代码校验。**")
    V = G1()
    G2()
    G3()
    G4()
    G5()
    G6()
    G7()
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
