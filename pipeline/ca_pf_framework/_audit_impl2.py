#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_impl2.py --- 碰撞前沿的过冷并入顺序依赖 + 界面粗糙度 vs dt（判断"交错"是否结构性）"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d
from ca3d import CA3D, IRF, OFFSETS, T_LIQ, T_SOL
from scipy import ndimage as ndi

BASE = list(ca3d.OFFSETS)


def shuf(seed):
    r = np.random.default_rng(seed); o = BASE[:]; r.shuffle(o); return o


def t_collide(nx=41, sep=10):
    """两个种子相距 sep, 全冷, 一次 thermal_capture => 两片领土必然相遇"""
    def run(offs):
        ca3d.OFFSETS = offs
        ca = CA3D(nx, nx, nx, 1e-6, irf=IRF(), seed=9)
        c = nx//2
        ca.add_grain(c-sep//2, c, c)
        ca.add_grain(c+sep//2, c, c)
        ca.thermal_capture(np.full(ca.shape, 300.0), spontaneous=False)
        return ca.gid.copy()
    g0 = run(BASE)
    print("[过冷并入·碰撞前沿] 盒 %d^3, 两种子相距 %d 胞, 全冷一次并入:" % (nx, sep))
    print("    默认顺序: 晶粒1 %d 胞, 晶粒2 %d 胞" % ((g0 == 1).sum(), (g0 == 2).sum()))
    for s in range(3):
        g = run(shuf(s))
        print("    打乱 #%d: 不同胞 %6d (%.2f%%), 晶粒1 %d / 晶粒2 %d" % (
            s, int((g != g0).sum()), 100.0*(g != g0).sum()/g0.size,
            (g == 1).sum(), (g == 2).sum()))
    ca3d.OFFSETS = BASE


def t_interlock(nx=41, nz=81, dx=1.5e-6, G=1e6, vpull=0.06, fac=(1, 2, 4)):
    """定向凝固 + 两个并排种子 => 测界面粗糙度随 dt 的变化"""
    print("[界面粗糙度 vs dt] 盒 %dx%dx%d, dx=%.1f um, G=%.1e K/m, 抽拉 %.2f m/s" % (
        nx, nx, nz, dx*1e6, G, vpull))
    print("   dt 倍率  末态 f_s   晶界面对数  投影面(理想)  粗糙度比  孤立小块(胞<8)  界面连通片")
    for f in fac:
        ca = CA3D(nx, nx, nz, dx, irf=IRF(), seed=21)
        c = nx//2
        ca.add_grain(c-8, c, 0)
        ca.add_grain(c+8, c, 0)
        V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
        dt = dx/(4*V_max)/f
        nst = int(1.6e-3/dt)
        for s in range(nst):
            ca.t = s*dt
            T = ca.T_directional(G, vpull)
            ca.step(dt, T, window="full")
            if (ca.gid == 0).sum() == 0:
                break
        g = ca.gid
        # 两晶粒交界面（只数一个方向，避免重复）
        fac_list = []
        for ax in range(3):
            n = g.shape[ax]
            lo = list(range(n-1)); hi = list(range(1, n))
            ga = np.take(g, lo, axis=ax); gb = np.take(g, hi, axis=ax)
            m = (np.minimum(ga, gb) == 1) & (np.maximum(ga, gb) == 2)
            for ii in np.argwhere(m):
                fac_list.append((ax, tuple(ii)))
        proj = set()
        for ax, ii in fac_list:
            proj.add((ax, ii[1], ii[2]) if ax == 0 else (ax, ii[0], ii[2]) if ax == 1 else (ax, ii[0], ii[1]))
        nf = len(fac_list); npr = len(proj)
        small = 0
        for gid in (1, 2):
            lab, nn = ndi.label(g == gid)
            sz = np.bincount(lab.ravel())
            for L in range(1, len(sz)):
                if 0 < sz[L] < 8:
                    small += sz[L]
        # 界面连通片（按共享棱，粗粒度：用 26-邻接的面对做并查集）
        par = {}
        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: par[ra] = rb
        ft = []
        for ax, ii in fac_list:
            pl = list(ii); pl[ax] += 1
            o1, o2 = [k for k in range(3) if k != ax]
            corner = []
            for du, dv in ((0,0),(1,0),(1,1),(0,1)):
                p = list(pl); p[o1] += du; p[o2] += dv; corner.append(tuple(p))
            ft.append(corner)
        for i in range(len(ft)):
            par[("F", i)] = ("F", i)
        for i, f in enumerate(ft):
            for e in [(f[0], f[1]), (f[1], f[2]), (f[2], f[3]), (f[3], f[0])]:
                for j, g2 in enumerate(ft):
                    if j <= i: continue
                    if e[0] in g2 and e[1] in g2:
                        uni(("F", i), ("F", j))
        comps = len({find(("F", i)) for i in range(len(ft))})
        print("   /%-5d  %.3f      %6d        %6d       %.2f       %4d          %3d" % (
            f, float((g > 0).mean()), nf, npr, nf/max(npr, 1), small, comps))


t_collide()
print()
t_interlock()