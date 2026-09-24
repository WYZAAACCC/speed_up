#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_fix3.py --- T7 化学：池尺度 Scheil + 基底 c0 + 质量守恒 + 空间/晶界富集趋势"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V, F_MIN

DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0

ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
ca.nucleate_substrate_grid(2, 3)
ca.seed_solid_from_substrate(ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), T_SOL)
pool0 = (ca.gid == 0).copy(); sub0 = ca.gid > 0
V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
dt = DX/(4*V_max); nst = int(1.2e-3/dt)
s = 0
for s in range(nst):
    ca.t = s*dt
    ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
    if (ca.gid == 0).sum() == 0:
        break
ca.finalize_chemistry()
pool = pool0 & (ca.gid > 0)
cl = ca.cl[pool]; cs = ca.c[pool]; cc = ca.c_cell[pool]; ts = ca.ts[pool]
print("步数 %d;  池内胞 %d" % (s, pool.sum()))
print("c_l  (该胞凝固时刻的枝晶间液相, Window C 输入): %.4f .. %.4f  均值 %.4f" % (
    cl.min(), cl.max(), cl.mean()))
print("c_s  (该胞沉积固相成分, Window B 输入):        %.4f .. %.4f  均值 %.4f" % (
    cs.min(), cs.max(), cs.mean()))
print("c_cell(体平均, 守恒恒等式 => 应恒等于 c0):      %.4f .. %.4f" % (cc.min(), cc.max()))
print("基底胞 c = %.4f (物理 c0=%.4f; 修前 k*c0=%.4f)" % (
    ca.c[sub0].mean(), C0_V, K_V*C0_V))
print("质量守恒 <体平均>/c0 = %.6f  (修前 0.7324)" % ca.mass_balance())
print("空间趋势 corr(t_capture, c_l) = %+.3f  (>0 = 越晚凝固越富集)" % float(np.corrcoef(ts, cl)[0,1]))
print("c_l 相对动态范围 (max-min)/c0 = %.3f  (修前 ~0.05 几乎常数)" % ((cl.max()-cl.min())/C0_V))
# 晶界相邻胞是否更富集（GB = 两晶粒前沿相遇处 => 应更晚、更富集）
g = ca.gid; gbc = np.zeros(g.shape, bool)
for ax in range(3):
    n = g.shape[ax]; lo = list(range(n-1)); hi = list(range(1, n))
    a = np.take(g, lo, axis=ax); b = np.take(g, hi, axis=ax)
    for ii in np.argwhere((a > 0) & (b > 0) & (a != b)):
        for off in (0, 1):
            c = list(ii); c[ax] += off; gbc[tuple(c)] = True
gb = gbc & pool
print("晶界相邻胞: c_l 均值 %.4f vs 池内 %.4f (比值 %.3f);  t_capture 均值比 %.4f" % (
    ca.cl[gb].mean(), cl.mean(), ca.cl[gb].mean()/cl.mean(),
    ca.ts[gb].mean()/ts.mean()))
# 与旧路径对比
ca.scheil_chemistry()
cl_old = ca.cl[pool]
print("对照(旧全域-f 路径): c 范围 %.4f..%.4f, 顶在 F_MIN 天花板的胞占比 %.0f%%" % (
    cl_old.min(), cl_old.max(), 100.0*(cl_old > ca.cl_max*0.999).sum()/len(cl_old)))