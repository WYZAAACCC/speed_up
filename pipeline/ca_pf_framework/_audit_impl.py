#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_impl.py --- 实现层审计：thermal_capture / seed_solid_from_substrate 的顺序依赖与自形核风险 + Scheil 化学"""
import os, sys, math, copy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d
from ca3d import CA3D, IRF, OFFSETS, T_LIQ, T_SOL, C0_V, K_V, F_MIN

BASE = list(ca3d.OFFSETS)


def shuffled(seed=0):
    rng = np.random.default_rng(seed)
    o = BASE[:]
    rng.shuffle(o)
    return o


# ---------------------------------------------------- 1) 过冷液相并入：顺序依赖
def t_thermal_order(nx=61, nseed=3):
    def run(offs):
        ca3d.OFFSETS = offs
        ca = CA3D(nx, nx, nx, 1e-6, irf=IRF(), seed=11)
        for (i, j, k) in [(0, 0, 0), (nx-1, 0, 0), (0, nx-1, nx-1)][:nseed]:
            ca.add_grain(i, j, k)
        T = np.full(ca.shape, 300.0)             # 全冷
        ca.thermal_capture(T, spontaneous=False)
        return ca.gid.copy()
    g0 = run(BASE)
    outs = [run(shuffled(s)) for s in range(3)]
    ca3d.OFFSETS = BASE
    n = g0.size
    print("[thermal_capture 顺序依赖] 盒 %d^3=%d 胞, %d 个种子, 全冷一次并入:" % (nx, n, nseed))
    for s, g in enumerate(outs):
        print("    打乱顺序 #%d: 与默认顺序不同的胞 = %d (%.2f%%)" % (
            s, int((g != g0).sum()), 100.0*(g != g0).sum()/n))
    u, c = np.unique(g0, return_counts=True)
    print("    默认顺序下各晶粒胞数:", " ".join("%d:%d" % (a, b) for a, b in zip(u, c)))


# ---------------------------------------------------- 2) 自发形核风险
def t_spont(nx=41):
    ca3d.OFFSETS = BASE
    ca = CA3D(nx, nx, nx, 1e-6, irf=IRF(), seed=5)
    ca.add_grain(0, 0, 0)
    T = np.full(ca.shape, 300.0)
    n_th, n_sp = ca.thermal_capture(T, spontaneous=True)
    print("[自发形核风险] 盒 %d^3, 只有 1 个种子在角落, 全冷:" % nx)
    print("    过冷并入 %d 胞;  自发形核【新晶粒】= %d 个 (占剩余 %.1f%%)" % (
        n_th, n_sp, 100.0*n_sp/(nx**3)))
    print("    ⇒ 剩下来的每个孤立冷胞各自变成一个【1 胞新晶粒(随机取向)】")


# ---------------------------------------------------- 3) 基底洪泛的顺序依赖
def t_substrate():
    def run(offs):
        ca3d.OFFSETS = offs
        ca = CA3D(61, 61, 61, 1e-6, irf=IRF(), seed=3)
        ca.nucleate_substrate_grid(2, 2)
        T = np.full(ca.shape, 300.0)
        ca.seed_solid_from_substrate(T, T_SOL)
        return ca.gid.copy()
    g0 = run(BASE)
    g1 = run(shuffled(1))
    g2 = run(shuffled(2))
    ca3d.OFFSETS = BASE
    n = g0.size
    print("[seed_solid_from_substrate 顺序依赖] 61^3 盒, 4 个底面种子, 全域冷:")
    for nm, g in (("打乱#1", g1), ("打乱#2", g2)):
        d = (g != g0)
        print("    %s: 与默认顺序不同的胞 = %d (%.2f%%)  ⇒ 基底晶粒图是【扫描顺序】的函数" % (
            nm, d.sum(), 100.0*d.sum()/n))


# ---------------------------------------------------- 4) Scheil 化学
def t_scheil():
    ca3d.OFFSETS = BASE
    DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
    T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
    ca.nucleate_substrate_grid(2, 3)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    n_sub = ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max); nst = int(1.2e-3/dt)
    for s in range(nst):
        ca.t = s*dt
        T = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
        ca.step(dt, T, window=None)
        if (ca.gid == 0).sum() == 0:
            break
    ca.scheil_chemistry()
    pool = pool0 & (ca.gid > 0)
    c_sub = ca.c[ca.ts < 0]
    cc = ca.c[pool]; cl = ca.cl[pool]
    print("[Scheil 化学] 池内 %d 胞:" % pool.sum())
    print("    c   : min %.4f  max %.4f  均值 %.4f  (k*c0=%.4f, k*c_l_max=%.4f)" % (
        cc.min(), cc.max(), cc.mean(), K_V*C0_V, K_V*ca.cl_max))
    print("    处于【F_MIN 正则化上限】的池内胞比例 = %.1f%%" % (
        100.0*(cl > ca.cl_max*0.999).sum()/max(len(cl), 1)))
    print("    全局质量守恒: ∫c dV / (c0*V_solid) = %.4f  (1.0 = 守恒)" % (
        ca.c[ca.gid > 0].mean()/C0_V))
    if len(c_sub):
        print("    基底(ts<0) 的 c = %.4f  (物理应为 c0=%.4f; 代码给 k*c0=%.4f)" % (
            c_sub.mean(), C0_V, K_V*C0_V))
    print("    池内 cl(液相成分) 均值 %.4f  <-- Window C 的输入" % cl.mean())


for fn in (t_thermal_order, t_spont, t_substrate, t_scheil):
    fn(); print()