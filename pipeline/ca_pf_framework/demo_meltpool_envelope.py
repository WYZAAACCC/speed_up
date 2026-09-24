#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo_meltpool_envelope.py --- 熔池演示（2026-09-23 审计修复后的新默认口径）

与原 demo_meltpool_growth.py 的差别（原文件保留，用于对照）：
  * 捕获规则 = `envelope`（逐晶粒连续包络 + 外延邻接 + 逐胞 argmax）——正确 KD 各向异性
  * 种子放在【熔池底部footprint】上，数量按文献（池宽 ≈ prior-β 晶粒宽 ⇒ 1~3 个/池宽）
  * 液相归零即停（原版跑满 1083 步，其中 90% 是白算）
  * 化学 = finalize_chemistry()（池尺度 Scheil + 逐胞捕获时刻）
输出：gid/dx/snaps 的 npz（给三维画图）、VTK、以及一份完整诊断。
"""
import os, sys, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V
from scipy import ndimage as ndi
from scipy.cluster.vq import kmeans2

HERE = os.path.dirname(os.path.abspath(__file__))
DX = 3.0e-6
NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
NSEED = 3                       # 池宽 160um / prior-β 晶粒宽 124-168um ⇒ ~1 个/池宽；取 3 个让三叉晶界可见
NSNAP = 6


def metrics(g, keep):
    gg = np.where(keep, g, 0)
    ft = []
    for ax in range(3):
        n = gg.shape[ax]
        a = np.take(gg, list(range(n-1)), axis=ax); b = np.take(gg, list(range(1, n)), axis=ax)
        for ii in np.argwhere((a > 0) & (b > 0) & (a != b)):
            ft.append((ax, tuple(ii)))
    proj = set()
    for ax, ii in ft:
        proj.add((ax,) + tuple(v for k, v in enumerate(ii) if k != ax))
    small = 0
    for gid in np.unique(g[keep & (g > 0)]):
        lab, _ = ndi.label(gg == gid)
        sz = np.bincount(lab.ravel())
        for L in range(1, len(sz)):
            if 0 < sz[L] < 8:
                small += int(sz[L])
    return len(ft), len(proj), small


def gb_cells(g, keep):
    m = np.zeros(g.shape, bool)
    for ax in range(3):
        n = g.shape[ax]
        a = np.take(g, list(range(n-1)), axis=ax); b = np.take(g, list(range(1, n)), axis=ax)
        hit = (a > 0) & (b > 0) & (a != b)
        for ii in np.argwhere(hit):
            for off in (0, 1):
                c = list(ii); c[ax] += off
                if keep[tuple(c)]:
                    m[tuple(c)] = True
    return m


def main():
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026, capture="envelope")
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    poolT = T0 > T_SOL
    wall = ndi.binary_dilation(poolT) & ~poolT
    zbot = np.nonzero(poolT.sum(axis=(0, 1)))[0].min()
    foot = wall.copy()
    foot[:, :, zbot+3:] = False                     # 只取池底那几层的池壁
    wc = np.argwhere(foot).astype(float)
    cen, lab = kmeans2(wc, NSEED, minit="++", seed=4)
    for k in range(NSEED):
        idx = wc[lab == k]
        i, j, kk = idx[len(idx)//2].astype(int)
        ca.add_grain(int(i), int(j), int(kk))
    print("池底 footprint 种子 %d 个; 池底 z=%d" % (NSEED, zbot))
    nfill = ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    print("初始固相(基底) %d 胞; 池 %d 胞" % (nfill, int(pool0.sum())))
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max); nst = int(1.2e-3/dt)
    print("dt=%.2e s; 上限步数 %d" % (dt, nst))
    snaps, times = [], []
    t0 = time.time()
    s = 0
    for s in range(nst):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
        nliq = int((ca.gid == 0).sum())
        if nliq > 0 and len(snaps) < 40 and s % 5 == 0:
            snaps.append(ca.gid.copy()); times.append(ca.t)
        if nliq == 0:
            break
    wall_s = time.time() - t0
    ca.finalize_chemistry()
    snaps.append(ca.gid.copy()); times.append(ca.t)
    pool = pool0 & (ca.gid > 0)
    nf, npr, small = metrics(ca.gid, pool)
    gbc = gb_cells(ca.gid, pool)
    n_th = getattr(ca, "n_thermal", 0); n_un = getattr(ca, "n_unresolved", 0)
    print("用时 %.1f s（跑到第 %d 步；旧版跑满 %d 步≈%.0f s = 白算 %.0f%%）" % (
        wall_s, s, nst, wall_s*nst/max(s,1), 100.0*(1.0 - (s+1)/nst)))
    print("热力学约束(过冷液相归属) %d 胞 = 池的 %.0f%%; 未归属(无固相邻居) %d 胞" % (
        n_th, 100.0*n_th/max(pool0.sum(), 1), n_un))
    print("末态 f_s=%.4f; 晶粒 %d 个; 晶界面积 %.3e m^2" % (
        ca.solid_fraction(), len(ca.grain_ids()), ca.gb_area()))
    print("池内晶界面 %d 面, 投影面 %d (粗糙度 %.2f), 孤岛胞 %d  <-- 旧默认: 4238 / 1.90 / 61" % (
        nf, npr, nf/max(npr, 1), small))
    u, c = np.unique(ca.gid[pool], return_counts=True)
    print("池内各晶粒占比: " + "  ".join("gid%d=%.1f%%" % (a, 100.0*b/pool.sum())
                                   for a, b in zip(u, c) if a > 0))
    capp = np.isfinite(ca.ts) & (ca.ts >= 0.0) & pool
    print("化学: 基底 c=%.4f; c_l 范围 %.4f..%.4f; c_s 范围 %.4f..%.4f; 质量守恒 %.5f" % (
        ca.c[np.isfinite(ca.ts) & (ca.ts < 0)].mean(),
        ca.cl[capp].min(), ca.cl[capp].max(), ca.c[capp].min(), ca.c[capp].max(),
        ca.mass_balance()))
    print("      corr(t_capture, c_l)=%+.3f; 晶界相邻胞 c_l / 池内 = %.3f" % (
        float(np.corrcoef(ca.ts[capp], ca.cl[capp])[0, 1]),
        ca.cl[gbc & capp].mean()/max(ca.cl[capp].mean(), 1e-30)))
    np.savez_compressed(os.path.join(HERE, "meltpool_envelope_gid.npz"),
                        gid=ca.gid, dx=DX, snaps=np.array(snaps), snap_t=np.array(times),
                        cl=ca.cl, c=ca.c, ts=ca.ts)
    ca.write_vtk(os.path.join(HERE, "meltpool_envelope_final.vtk"),
                 fields=("gid", "c", "ts", "cl"))
    print("已存 meltpool_envelope_gid.npz / .vtk")


if __name__ == "__main__":
    main()