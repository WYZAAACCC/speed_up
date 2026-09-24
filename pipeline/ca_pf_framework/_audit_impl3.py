#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_impl3.py --- 界面粗糙度 vs dt：定向凝固 + 两个并排种子，同一物理时刻比较"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL
from scipy import ndimage as ndi

NX, NZ, DX = 31, 61, 1.5e-6
G, VPULL, TEND = 1.0e6, 0.06, 6.0e-4


def run(fac):
    ca = CA3D(NX, NX, NZ, DX, irf=IRF(), seed=21)
    c = NX//2
    ca.add_grain(c-3, c, 0)
    ca.add_grain(c+3, c, 0)
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max)/fac
    nst = int(TEND/dt)
    for s in range(nst):
        ca.t = s*dt
        ca.step(dt, ca.T_directional(G, VPULL), window="full")
    g = ca.gid
    ft = []
    for ax in range(3):
        n = g.shape[ax]
        lo = list(range(n-1)); hi = list(range(1, n))
        ga = np.take(g, lo, axis=ax); gb = np.take(g, hi, axis=ax)
        m = (np.minimum(ga, gb) == 1) & (np.maximum(ga, gb) == 2)
        for ii in np.argwhere(m):
            ft.append((ax, tuple(ii)))
    proj = set()
    for ax, ii in ft:
        proj.add((ax,) + tuple(v for k, v in enumerate(ii) if k != ax))
    small = 0
    for gid in (1, 2):
        lab, nn = ndi.label(g == gid)
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
            e = corners[i]
            if len(set(e) & set(corners[j])) >= 2:
                uni(("F", i), ("F", j))
    comps = len({find(("F", i)) for i in range(len(corners))})
    return dict(nf=len(ft), npr=len(proj), small=small, comps=comps,
                fs=float((g > 0).mean()), nst=nst, dt=dt)


print("定向凝固: 盒 %dx%dx%d, dx=%.1f um, G=%.0e K/m, v=%.2f m/s, 同一物理时刻 t=%.1e s" % (
    NX, NX, NZ, DX*1e6, G, VPULL, TEND))
print("  dt倍率  步数     dt(s)     f_s    晶界面数  投影面数  粗糙度比  孤立胞  界面连通片")
for fac in (1, 2, 3):
    r = run(fac)
    print("  /%-5d %5d  %.3e  %.3f  %7d  %7d   %.3f    %4d      %3d" % (
        fac, r["nst"], r["dt"], r["fs"], r["nf"], r["npr"], r["nf"]/max(r["npr"],1),
        r["small"], r["comps"]))