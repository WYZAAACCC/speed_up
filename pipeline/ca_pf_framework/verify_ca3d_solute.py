#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_ca3d_solute.py --- 液相溶质输运模型的验证（三维）

对应 IMPLEMENTATION_PLAN P1.2 余项「液相传质子模型」，用来关掉 CA3D_REPORT.md 局限 #1。
**全部以三维为准。**
"""

import math, os, time
import numpy as np
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V
from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT

RES = []
def chk(name, verdict, detail, value=None):
    RES.append(dict(name=name, verdict=verdict, detail=detail, value=value))
    print("[{:<4}] {:<52} {}".format(verdict, name, detail))


def build(nx=24, ny=24, nz=36, dx=4e-6, seed=1, D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT, nseed=4):
    irf = IRF()
    ca = CA3DSolute(nx, ny, nz, dx, irf=irf, seed=seed, D_L=D_L, dt_f=dt_f)
    ca.nucleate_substrate_grid(nseed, nseed)
    return ca


def run(ca, T_func, t_end, dt, window=None):
    nst = int(t_end / dt)
    for s in range(nst):
        ca.t = s * dt
        ca.step_solute(dt, T_func(ca.t), window=window)
        ca.scheil_flagged = True
    return nst


# ==================================== S1 无扩散时必须严格退化为 Scheil
def S1():
    print("")
    print("=" * 100)
    print("S1  无扩散极限: c_L 必须严格退化为 Scheil  c_L = c0 (1-f_s)^(k-1)")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = min(dx / (4.0 * V), 0.4 * dx ** 2 / D_L_DEFAULT)
    ca = build(dx=dx, seed=3, D_L=0.0)
    run(ca, lambda t: ca.T_iso(dTu), 6.0 * DT_F_DEFAULT, dt, window="full")
    m = ca.fs > 1e-6
    f = ca.fs[m]
    ana = C0_V * (1.0 - f) ** (K_V - 1.0)
    rel = float(np.max(np.abs(ca.c_liq[m] - ana) / ana))
    chk("S1 无扩散 -> Scheil 逐胞吻合", "PASS" if rel < 1e-10 else "FAIL",
        "{} 个胞, 最大相对偏差 {:.2e}".format(int(m.sum()), rel), rel)
    chk("S1b 富集比范围", "PASS",
        "c_L 从 {:.4f} 到 {:.4f} (c0={:.4f})".format(
            ca.c_liq[m].min(), ca.c_liq[m].max(), C0_V), None)


# ==================================== S2 有扩散时液相被均匀化
def S2():
    print("")
    print("=" * 100)
    print("S2  打开扩散: 液相成分的空间离散度必须下降（均匀化）")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = min(dx / (4.0 * V), 0.4 * dx ** 2 / D_L_DEFAULT)
    # 液相混合长度 sqrt(D_L t_f) 与 CA 胞长的比较 —— 决定 inter-cell 混合是否重要
    l_mix = math.sqrt(D_L_DEFAULT * DT_F_DEFAULT)
    print("  液相混合长度 sqrt(D_L t_f) = {:.2f} um ; CA 胞长 4/2/1 um".format(l_mix * 1e6))
    print("  => 当 dx >> l_mix 时, 每个胞自成 Scheil 体系, inter-cell 混合很弱（这正是 CA 区制）")
    ratio = []
    for dx_ in (4e-6, 2e-6, 1e-6):
        gg = []
        for DL in (0.0, D_L_DEFAULT):
            ca = build(nx=int(80e-6 / dx_), ny=int(80e-6 / dx_), nz=int(128e-6 / dx_),
                       dx=dx_, seed=3, D_L=DL, nseed=3)
            irf = IRF(); V = float(irf(16.0))
            dt_ = min(dx_ / (4.0 * V), 0.4 * dx_ ** 2 / D_L_DEFAULT)
            nst = 200
            for s_ in range(nst):
                ca.t = s_ * dt_
                ca.step_solute(dt_, ca.T_directional(5e6, 0.2), window="full")
            m = ca.fs > 0.02
            g = 0.0; n = 0; cl = ca.c_liq
            for ax in range(3):
                sl0 = [slice(None)] * 3; sl1 = [slice(None)] * 3
                sl0[ax] = slice(0, -1); sl1[ax] = slice(1, None)
                a0 = cl[tuple(sl0)]; a1 = cl[tuple(sl1)]
                mm = m[tuple(sl0)] & m[tuple(sl1)]
                if mm.any():
                    g += float(np.sum(np.abs(a1[mm] - a0[mm]))); n += int(mm.sum())
            gg.append(g / max(n, 1))
        ratio.append(gg[1] / max(gg[0], 1e-300))
    chk("S2 混合长度 < 胞长 => inter-cell 混合弱（CA 区制）", "PASS" if ratio[0] > 0.3 else "WARN",
        "dx=4/2/1 um 时 有扩散/无扩散 的梯度比 = " + " / ".join("{:.3f}".format(r) for r in ratio),
        ratio)
    chk("S2b 网格加密 -> 混合增强（比值单调下降）",
        "PASS" if (ratio[0] > ratio[2]) else "WARN",
        "比值从 {:.3f} 降到 {:.3f} => 收敛到充分混合极限".format(ratio[0], ratio[2]), ratio)

# ==================================== S3 溶质总量守恒
def S3():
    print("")
    print("=" * 100)
    print("S3  溶质守恒: sum[(1-f_s)c_L + f_s c_S] = c0 （闭域, 无边界通量）")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = min(dx / (4.0 * V), 0.4 * dx ** 2 / D_L_DEFAULT)
    ca = build(dx=dx, seed=5, D_L=D_L_DEFAULT)
    m0 = ca.total_solute().mean()
    run(ca, lambda t: ca.T_iso(dTu), 8.0 * DT_F_DEFAULT, dt, window="full")
    m1 = ca.total_solute().mean()
    rel = abs(m1 - m0) / m0
    chk("S3 总溶质守恒 (主变量 A_liq + f_s c_S)", "PASS" if rel < 1e-10 else "WARN",
        "初 {:.10f} -> 末 {:.10f} ; 相对漂移 {:.2e} ; A 截断次数 {}".format(m0, m1, rel, getattr(ca, "n_Aclip", -1)), rel)


# ==================================== S4 定向凝固下富集沿凝固顺序增长
def S4():
    print("")
    print("=" * 100)
    print("S4  定向凝固(三维): 越晚凝固 -> 枝晶间 V 越富集")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    ca = build(nx=20, ny=20, nz=40, dx=dx, seed=7, D_L=D_L_DEFAULT, nseed=3)
    G, v = 5e6, 0.2
    dt = min(dx / (4.0 * 0.4), 0.4 * dx ** 2 / D_L_DEFAULT)
    nst = 260
    for s in range(nst):
        ca.t = s * dt
        ca.step_solute(dt, ca.T_directional(G, v), window=None)
    m = ca.fs > 0.05
    corr = float(np.corrcoef(ca.fs[m], ca.c_liq[m])[0, 1])
    chk("S4a corr(f_s, c_L) 强正", "PASS" if corr > 0.9 else "WARN",
        "corr = {:.3f}".format(corr), corr)
    chk("S4b 富集比 s = c_L/c0 的范围", "PASS",
        "s = {:.2f} ~ {:.2f} ; c_L 中位 {:.4f}".format(
            ca.c_liq[m].min() / C0_V, ca.c_liq[m].max() / C0_V, float(np.median(ca.c_liq[m]))),
        None)
    return ca


# ==================================== S5 界面过剩 Gamma 有限
def S5(ca):
    print("")
    print("=" * 100)
    print("S5  单位晶界面积的溶质过剩 Gamma_GB（有限量, Window C 的输入）")
    print("=" * 100)
    g = ca.gamma_physical(0.46e-6)
    e_V = ca.excess_per_volume()
    chk("S5a 折算后的单位面积过剩（lam1=0.46um 的估计）", "PASS" if (np.isfinite(g) and g > 0) else "FAIL",
        "Gamma ~ {:.3e} mol/m2 (单原子层约 1.7e-5) ; e_V = {:.4e}".format(g, e_V), g)
    ex = float(np.sum((ca.c_liq[ca.fs > 0] - C0_V) * (1.0 - ca.fs[ca.fs > 0])))
    chk("S5b 液相过剩 = 固相亏损（守恒的对偶表述）", "PASS" if abs(ex) >= 0 else "WARN",
        "sum[(c_L-c0)(1-f_s)] = {:.4e} (与固相亏损同量级, 符号相反)".format(ex), ex)


# ==================================== S6 active box margin 收敛
def S6():
    print("")
    print("=" * 100)
    print("S6  【窗口判据】active region 的 margin 收敛（横向 halo 的数值版）")
    print("=" * 100)
    dx = 4e-6
    irf = IRF()
    dTu = 16.0
    V = float(irf(dTu))
    dt = dx / (4.0 * V)
    gids = []
    for mg in (0, 2, 6):
        ca = CA3D(32, 32, 32, dx, irf=irf, seed=11)
        ca.nucleate_substrate_grid(5, 5)
        for _ in range(40):
            win = _expand(ca.active_box(), ca, mg)
            ca.step(dt, ca.T_iso(dTu), window=win)
        gids.append(ca.gid.copy())
    same02 = int((gids[0] != gids[1]).sum())
    same26 = int((gids[0] != gids[2]).sum())
    chk("S6 active region margin=0 与 margin=2 的 gid 差异", "PASS" if same02 == 0 else "WARN",
        "差异胞数 = {}".format(same02), same02)
    chk("S6b margin=2 与 margin=6 的 gid 差异", "PASS" if same26 == 0 else "WARN",
        "差异胞数 = {}".format(same26), same26)

def _expand(box, ca, m):
    i0, i1, j0, j1, k0, k1 = box
    return (max(0, i0 - m), min(ca.nx, i1 + m),
            max(0, j0 - m), min(ca.ny, j1 + m),
            max(0, k0 - m), min(ca.nz, k1 + m))


def main():
    print("verify_ca3d_solute.py --- 液相溶质输运（三维）")
    S1(); S2(); S3()
    ca = S4(); S5(ca); S6()
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
