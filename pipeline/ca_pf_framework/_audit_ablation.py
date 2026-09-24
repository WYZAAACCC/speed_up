#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_ablation.py --- 熔池算例消融：交错/孤岛到底来自 CA 前沿、过冷并入、还是初始基底图"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL
from scipy import ndimage as ndi

DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
C0 = 0.036


def metrics(g, keep):
    """keep: 关心区域掩膜。返回 (晶界面对数, 投影面数, 粗糙度, 碎屑胞, 连通片数)"""
    gg = np.where(keep, g, 0)
    ft = []
    for ax in range(3):
        n = gg.shape[ax]
        lo = list(range(n-1)); hi = list(range(1, n))
        a = np.take(gg, lo, axis=ax); b = np.take(gg, hi, axis=ax)
        m = (a > 0) & (b > 0) & (a != b)
        for ii in np.argwhere(m):
            ft.append((ax, tuple(ii)))
    proj = set()
    for ax, ii in ft:
        proj.add((ax,) + tuple(v for k, v in enumerate(ii) if k != ax))
    small = 0
    for gid in np.unique(g[keep & (g > 0)]):
        lab, nn = ndi.label((gg == gid))
        sz = np.bincount(lab.ravel())
        for L in range(1, len(sz)):
            if 0 < sz[L] < 8:
                small += int(sz[L])
    par = {}
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    def uni(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    corners = []
    for ax, ii in ft:
        pl = list(ii); pl[ax] += 1
        o1, o2 = [k for k in range(3) if k != ax]
        c4 = []
        for du, dv in ((0,0),(1,0),(1,1),(0,1)):
            q = list(pl); q[o1] += du; q[o2] += dv; c4.append(tuple(q))
        corners.append(c4)
    for i in range(len(corners)):
        par[("F", i)] = ("F", i)
    for i in range(len(corners)):
        for j in range(i+1, len(corners)):
            if len(set(corners[i]) & set(corners[j])) >= 2:
                uni(("F", i), ("F", j))
    comps = len({find(("F", i)) for i in range(len(corners))}) if corners else 0
    return len(ft), len(proj), (len(ft)/max(len(proj), 1)), small, comps


def demo(disable_thermal=False, tag=""):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
    ca.nucleate_substrate_grid(2, 3)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    # 初始基底图在池壁附近的交错程度（池外向膨胀 3 胞的一层）
    from scipy.ndimage import binary_dilation as bd
    near = bd(pool0, iterations=3) & ~pool0
    m0 = metrics(ca.gid, near)
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max); nst = int(1.2e-3/dt)
    if disable_thermal:
        ca.thermal_capture = lambda T, spontaneous=True: (0, 0)
    s = 0
    for s in range(nst):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
        if (ca.gid == 0).sum() == 0:
            break
    pool = pool0 & (ca.gid > 0)
    mm = metrics(ca.gid, pool)
    print("[%s] 跑到第 %d 步, 池内固相 %d 胞 (%.0f%% 池)" % (
        tag, s, pool.sum(), 100.0*pool.sum()/pool0.sum()))
    print("    初始基底图(池壁外 3 胞层): 面 %d, 投影 %d, 粗糙度 %.2f, 碎屑 %d, 连通片 %d" % m0)
    print("    末态池内           : 面 %d, 投影 %d, 粗糙度 %.2f, 碎屑 %d, 连通片 %d" % mm)
    return mm


print("=== 消融 A: 原样（CA + 过冷并入） ===")
demo(False, "A 原样")
print()
print("=== 消融 B: 关掉 thermal_capture 的外延并入（只留 CA 前沿）===")
demo(True, "B 只 CA")