#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_fix1.py --- 审计修复 Step1-3 的验收：T3 顺序无关 / T4 无假晶粒 / T5 dt 收敛 / T6 界面质量"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d
from ca3d import CA3D, IRF, T_LIQ, T_SOL, OFFSETS
from scipy import ndimage as ndi

BASE = list(ca3d.OFFSETS)


def shuf(seed):
    r = np.random.default_rng(seed); o = BASE[:]; r.shuffle(o); return o


def metrics(g, keep):
    gg = np.where(keep, g, 0)
    ft = []
    for ax in range(3):
        n = gg.shape[ax]
        lo = list(range(n - 1)); hi = list(range(1, n))
        a = np.take(gg, lo, axis=ax); b = np.take(gg, hi, axis=ax)
        m = (a > 0) & (b > 0) & (a != b)
        for ii in np.argwhere(m):
            ft.append((ax, tuple(ii)))
    proj = set()
    for ax, ii in ft:
        proj.add((ax,) + tuple(v for k, v in enumerate(ii) if k != ax))
    small = 0
    for gid in np.unique(g[keep & (g > 0)]):
        lab, nn = ndi.label(gg == gid)
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
    return dict(nf=len(ft), npr=len(proj), rough=len(ft)/max(len(proj),1), small=small, comps=comps)


# ---------------------------------------------------------------- T3/T4
def cold_fill(offs, nseed=2, nx=41, iters=80, sep=10):
    ca3d.OFFSETS = offs
    c = CA3D(nx, nx, nx, 1e-6, irf=IRF(), seed=9)
    if nseed == 2:
        k = nx//2
        c.add_grain(k - sep//2, k, k)
        c.add_grain(k + sep//2, k, k)
    else:
        c.add_grain(0, 0, 0)
    T = np.full(c.shape, 300.0)
    for _ in range(iters):
        before = int((c.gid == 0).sum())
        c.thermal_capture(T, mode="count")
        if int((c.gid == 0).sum()) == before:
            break
    out = (c.gid.copy(), getattr(c, "n_spont", 0), len(c.grain_ids()),
           int((c.gid == 0).sum()))
    ca3d.OFFSETS = BASE
    return out

print("=== T3 顺序无关性（碰撞前沿，迭代填充到不再变化）===")
g0, sp0, ng0, left0 = cold_fill(BASE)
print("  默认顺序: 晶粒1 %d / 晶粒2 %d, 剩余液相 %d, 晶粒总数 %d" % (
    (g0 == 1).sum(), (g0 == 2).sum(), left0, ng0))
for s in range(3):
    g, sp, ng, left = cold_fill(shuf(s))
    print("  打乱 #%d: 与默认不同 %6d 胞 (%.3f%%), 晶粒1 %d / 晶粒2 %d, 剩余 %d" % (
        s, int((g != g0).sum()), 100.0*(g != g0).sum()/g0.size, (g == 1).sum(), (g == 2).sum(), left))

print()
print("=== T4 自发形核（1 个角落种子 + 全冷，迭代填满）===")
g1, nsp, ng1, left1 = cold_fill(BASE, nseed=1)
print("  自发形核晶粒数 = %d（旧版在 41^3 盒里是 68578 个）; 末态晶粒数 %d; 剩余液相 %d" % (nsp, ng1, left1))

print()
print("=== T3b 基底初始图（各向异性 Voronoi）顺序无关性 ===")
def sub(offs):
    ca3d.OFFSETS = offs
    c = CA3D(61, 61, 61, 1e-6, irf=IRF(), seed=3)
    c.nucleate_substrate_grid(2, 2)
    c.seed_solid_from_substrate(np.full(c.shape, 300.0), T_SOL)
    g = c.gid.copy(); ca3d.OFFSETS = BASE; return g
s0 = sub(BASE)
for k in (1, 2):
    s = sub(shuf(k))
    print("  打乱 #%d: 不同胞 %d (%.2f%%)  ← 旧版是 30.16%% / 32.84%%" % (
        k, int((s != s0).sum()), 100.0*(s != s0).sum()/s0.size))


# ---------------------------------------------------------------- T5/T6 熔池
DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0

def meltpool(capture, fac=1.0, win=None):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026, capture=capture)
    ca.nucleate_substrate_grid(2, 3)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max)/fac
    nst = int(1.2e-3/dt)
    s = 0
    for s in range(nst):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=win)
        if (ca.gid == 0).sum() == 0:
            break
    m = metrics(ca.gid, pool0 & (ca.gid > 0))
    return dict(step=s, n_th=getattr(ca, "n_thermal", 0), pool=int(pool0.sum()),
                unres=getattr(ca, "n_unresolved", 0), **m)

print()
print("=== T5/T6 熔池（新默认 envelope）===")
print("  配置                          步数  热归属胞(占池)  未归属  晶界面  粗糙度  孤岛  连通片")
base = None
for tag, cap, fac, win in (("envelope / dt",        "envelope", 1.0, None),
                           ("envelope / dt*2",      "envelope", 0.5, None),
                           ("envelope / dt/2",      "envelope", 2.0, None),
                           ("envelope / dt/4",      "envelope", 4.0, None),
                           ("decentered / dt (旧默认)", "decentered", 1.0, None)):
    r = meltpool(cap, fac, win)
    print("  %-28s %5d  %6d (%4.0f%%)  %6d  %6d  %.2f  %4d  %3d" % (
        tag, r["step"], r["n_th"], 100.0*r["n_th"]/r["pool"], r["unres"],
        r["nf"], r["rough"], r["small"], r["comps"]))