#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_d1.py --- D1 敏感度：ℓ_g 驱动量取前沿 V 的分位（50/90/100）对熔池结果的影响"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL
from scipy import ndimage as ndi
from scipy.cluster.vq import kmeans2

DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0

def metrics(g, keep):
    gg = np.where(keep, g, 0); ft = []
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
        lab, _ = ndi.label(gg == gid); sz = np.bincount(lab.ravel())
        for L in range(1, len(sz)):
            if 0 < sz[L] < 8:
                small += int(sz[L])
    return len(ft), len(proj), small

print("D1 敏感度（池底 3 种子，其余同 demo_meltpool_envelope）:")
print("  pct  步数  池内晶粒占比                        晶界面  粗糙度  孤岛")
for pct in (50.0, 90.0, 100.0):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026, capture="envelope", lg_percentile=pct)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    poolT = T0 > T_SOL
    wall = ndi.binary_dilation(poolT) & ~poolT
    zbot = np.nonzero(poolT.sum(axis=(0,1)))[0].min()
    foot = wall.copy(); foot[:, :, zbot+3:] = False
    wc = np.argwhere(foot).astype(float)
    cen, lab = kmeans2(wc, 3, minit="++", seed=4)
    for k in range(3):
        idx = wc[lab == k]; i, j, kk = idx[len(idx)//2].astype(int)
        ca.add_grain(int(i), int(j), int(kk))
    ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0]); dt = DX/(4*V_max)
    s = 0
    for s in range(int(1.2e-3/dt)):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
        if (ca.gid == 0).sum() == 0:
            break
    pool = pool0 & (ca.gid > 0)
    u, c = np.unique(ca.gid[pool], return_counts=True)
    frac = " ".join("%d:%.1f%%" % (a, 100.0*b/pool.sum()) for a, b in zip(u, c) if a > 0)
    nf, npr, small = metrics(ca.gid, pool)
    print("  %-5g %4d  %-38s %6d  %.2f  %4d" % (pct, s, frac, nf, nf/max(npr,1), small))