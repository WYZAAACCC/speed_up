#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_ca.py --- CA 代码审计用的数值探针（分批运行: irf / geom / thermal / scheil / interlock）"""
import os, sys, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, OFFSETS, T_LIQ, T_SOL, C0_V, K_V, M_L, F_MIN
from scipy.special import exp1

GAMMA = 3.08e-7      # K m   （MATH_FRAMEWORK 4.3）
DL    = 9.5e-9       # m2/s
MU_K  = 1.0          # m/(s K)
GROUP = sys.argv[1] if len(sys.argv) > 1 else "irf"


# ---------------------------------------------------------------- 1) IRF 自洽性
def chk_irf():
    irf = IRF()
    tab = np.loadtxt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "irf_ti64.csv"),
                     delimiter=",", skiprows=1)
    dT, V, R = tab[:, 0], tab[:, 1], tab[:, 2]
    P = R * V / (2 * DL)
    Iv = P * np.exp(P) * exp1(P)
    cl = C0_V / (1.0 - (1.0 - K_V) * Iv)
    Gc = V / DL * cl * (1.0 - K_V)
    xi = 1.0 - 2 * K_V / (np.sqrt(1.0 + (2 * np.pi / P) ** 2) - 1.0 + 2 * K_V)
    G_impl = abs(M_L) * Gc * xi - (2 * np.pi / R) ** 2 * GAMMA      # 由边际稳定性反解出的 G
    dT_pred = abs(M_L) * (cl - C0_V) + 2 * GAMMA / R + V / MU_K     # 过冷度预算
    print("  dT(表)   V(m/s)   R(um)     P      cl*    Gc(K/m)   xi    G_反解(K/m)  dT_预算   Δ%")
    for i in range(0, len(dT), 12):
        print("  %6.3f  %8.4f  %6.3f  %5.2f  %6.4f  %8.1f  %.3f  %10.3e  %6.3f  %+6.1f%%" % (
            dT[i], V[i], R[i]*1e6, P[i], cl[i], Gc[i], xi[i], G_impl[i], dT_pred[i],
            100*(dT_pred[i]-dT[i])/dT[i]))
    print("  G_反解 / (1e5/V):", " ".join("%.2f" % (G_impl[i]*V[i]/1e5) for i in range(0, len(dT), 24)))
    print("  全表 dT_预算 vs dT 相对偏差: 均值 %.2f%%, 最大 %.2f%%" % (
        100*np.mean((dT_pred-dT)/dT), 100*np.max(np.abs((dT_pred-dT)/dT))))
    print("  V·R^2 是否常数: 首 %.3e 末 %.3e  比 %.2f" % (
        (V*R**2)[0], (V*R**2)[-1], (V*R**2)[-1]/(V*R**2)[0]))
    print("  表头: dT_lo=%.3f dT_hi=%.3f V_lo=%.3e V_hi=%.3e" % (
        irf.dT_lo, irf.dT_hi, irf.V_at_lo, irf.V_at_hi))
    print("  dt 规则: dt=dx/(4*V_max) -> 每步最大推进 %.3f 胞 (V_max=%.4f m/s)" % (
        irf.V_at_hi*1/4/irf.V_at_hi, irf.V_at_hi))


# ---------------------------------------------------------------- 2) 包络几何
def _quat_axis_angle(axis, deg):
    a = np.array(axis, float); a /= np.linalg.norm(a)
    th = math.radians(deg)
    return (math.cos(th/2), *(a*math.sin(th/2)))

def chk_geom(dx=1.0e-6, N=60, dT=12.0, mode="analytic", nxyz=(91, 91, 91)):
    from ca3d import quat_to_axes
    ca = CA3D(*nxyz, dx, irf=IRF(), seed=1, capture=mode)
    c = tuple(s//2 for s in nxyz)
    q = _quat_axis_angle((0.3, 0.7, 0.2), 37.0)
    g = ca.add_grain(c[0], c[1], c[2], quat=q)
    P = ca.axes[g]
    T = ca.T_iso(dT)
    V = float(ca.irf.capped(np.array([dT]))[0][0])
    irf = ca.irf
    print("  取向 q=(%.3f,%.3f,%.3f,%.3f);  dT=%.1f K -> V=%.4f m/s;  dx=%.2f um; 模式=%s" % (
        *q, dT, V, dx*1e6, mode))
    print("  晶体主轴(实验室系) p1=%s p2=%s p3=%s" % tuple(
        "(%+.3f,%+.3f,%+.3f)" % tuple(P[:, a]) for a in range(3)))
    dt = dx / (4 * V)
    t = 0.0
    for s in range(N):
        ca.t = t
        ca.step(dt, T, window="full")
        t += dt
    ell = V * (N * dt)                    # 八面体半轴 = ∫V dt
    seed = np.array(c, float)
    X, Y, Z = ca.coords()
    solid = ca.gid > 0
    # 沿指定【晶体方向】测最远充填距离
    print("  晶体方向          n̂_world                    Σ|c|   max|c|   r/ℓ实测   ℓ/Σ     ℓ·max")
    for cdir in [(1,0,0), (0,1,0), (1,1,0), (1,1,1), (1,0.5,0), (1,0.3,0.2), (2,1,0)]:
        cv = np.array(cdir, float); cv /= np.linalg.norm(cv)
        nw = P @ cv
        dm, sm, mm = np.abs(cv).sum(), np.abs(cv).max(), 0.0
        for rr in np.arange(0.0, 3*ell, 0.2*dx):
            pos = (seed + 0.5) * dx + rr * nw
            idx = np.floor(pos / dx).astype(int)
            if np.any(idx < 0) or np.any(idx >= np.array(nxyz)):
                break
            if solid[idx[0], idx[1], idx[2]]:
                sm = rr
        r_over_ell = sm / ell
        # 理论: 八面体径向函数 ℓ/Σ（=analytic 应该给的值）；支撑函数 ℓ·max
        print("  (%4.1f,%4.1f,%4.1f)  (%+.3f,%+.3f,%+.3f)  %5.3f  %5.3f   %7.3f   %6.3f   %6.3f" % (
            cdir[0], cdir[1], cdir[2], nw[0], nw[1], nw[2], dm, mm,
            r_over_ell, 1.0/dm, mm))


if GROUP == "irf":
    print("=== IRF（LKT 界面响应函数）自洽性核对 ===")
    chk_irf()
elif GROUP == "geom":
    print("=== 包络几何：单晶生长实测径向距离 vs ℓ/Σ 与 ℓ·max ===")
    for mode in ("analytic", "decentered"):
        chk_geom(mode=mode)
        print()