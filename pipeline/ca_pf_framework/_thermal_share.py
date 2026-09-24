#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_thermal_share.py --- 统计这个熔池算例里，固相到底是【CA 前沿推进】抓来的，还是
【thermal_capture 的过冷液相并入】填来的；顺便看液相是哪一步消失的。"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL

DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
NGX, NGY = 2, 3
DOM = NX * NY * NZ

ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
ca.nucleate_substrate_grid(NGX, NGY)
T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
n_fill = ca.seed_solid_from_substrate(T0, T_SOL)
V_max = max(float(ca.irf(np.array([T_LIQ - T_SOL]))[0]), 0.2)
dt = DX / (4.0 * V_max); nst = int(1.2e-3 / dt)
print("初始固相(基底) %d 胞, 池 %d 胞, 步数 %d" % (n_fill, DOM - n_fill, nst))

box = [None]; ab = ca.active_box
def rec(margin=None):
    b = ab(margin); box[0] = b; return b
ca.active_box = rec
liq_hist = []; wf = []
t0 = time.perf_counter()
step_solid0 = None
for s in range(nst):
    ca.t = s * dt
    T = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    ca.step(dt, T, window=None)
    nliq = int((ca.gid == 0).sum())
    if s % 20 == 0 or nliq == 0:
        b = box[0]; wf.append(((b[1]-b[0])*(b[3]-b[2])*(b[5]-b[4]))/DOM)
        liq_hist.append((s, nliq))
    if nliq == 0 and step_solid0 is None:
        step_solid0 = s
    if nliq == 0 and s > step_solid0 + 5:
        break
print("用时 %.1f s, 跑到第 %d 步" % (time.perf_counter() - t0, s))
print("液相归零于第 %s 步 (t=%.2e s, 即 τ 的 %.2f 倍)" % (
    step_solid0, step_solid0*dt, step_solid0*dt/TAU))
print("液相胞数轨迹 (step: n_liq):")
print("  " + "  ".join("%d:%d" % (a, b) for a, b in liq_hist if a <= (step_solid0 or 0) + 20))
n_th = getattr(ca, "n_thermal", 0); n_sp = getattr(ca, "n_spont", 0)
print("\n由 thermal_capture 并入的胞 = %d (占池 %.1f%%)" % (n_th, 100.0*n_th/(DOM - n_fill)))
print("自发形核胞 = %d ; 末态晶粒数 = %d" % (n_sp, len(ca.grain_ids())))
print("⇒ 由【CA 前沿捕获】得到的池内胞 = %d (%.1f%%)" % (
    (DOM - n_fill) - n_th, 100.0*((DOM - n_fill) - n_th)/(DOM - n_fill)))
print("窗口体积占比(每 20 步采样) 前 40 个: %s" % " ".join("%.0f%%" % (100*w) for w in wf[:40]))
# 末态：碎屑 + 互穿
from scipy import ndimage as ndi
g = ca.gid
spec = 0
for gid in range(1, g.max()+1):
    m = g == gid
    lab, n = ndi.label(m)
    sz = np.bincount(lab.ravel())
    for L in range(1, len(sz)):
        if 0 < sz[L] < 8:
            spec += sz[L]
print("末态全域碎屑胞(<8胞块) = %d (%.3f%% 域)" % (spec, 100.0*spec/DOM))