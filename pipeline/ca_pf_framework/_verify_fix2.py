#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_fix2.py --- T2: 包络几何误差随 dx 收敛（envelope 模式，单晶）"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ

DT_K = 12.0
NN = 61                     # 盒边长（胞）


def quat_aa(axis, deg):
    a = np.array(axis, float); a /= np.linalg.norm(a)
    th = math.radians(deg)
    return (math.cos(th/2), *(a*math.sin(th/2)))


def run(mode, dx, nst):
    ca = CA3D(NN, NN, NN, dx, irf=IRF(), seed=7, capture=mode)
    c = (NN//2, NN//2, NN//2)
    g = ca.add_grain(c[0], c[1], c[2], quat=quat_aa((0.3, 0.7, 0.2), 37.0))
    P = ca.axes[g]
    T = ca.T_iso(DT_K)
    V = float(ca.irf.capped(np.array([DT_K]))[0][0])
    dt = dx/(4*V)
    t = 0.0
    for s in range(nst):
        ca.t = t
        ca.step(dt, T, window="full")
        t += dt
    ell = V*nst*dt
    ncell = int((ca.gid > 0).sum())
    vol_ideal = (2*ell)**3/6.0/(dx**3)          # L1 球体积 = 8ℓ³/6（胞数）
    solid = ca.gid > 0
    # 沿晶体 <100> 的实测半径
    cv = np.array([1.0, 0, 0]); nw = P @ cv
    sm = 0.0
    for r in np.arange(0.0, 2.5*ell, 0.2*dx):
        p = (np.array(c) + 0.5)*dx + r*nw
        idx = np.floor(p/dx).astype(int)
        if np.any(idx < 0) or np.any(idx >= NN):
            break
        if solid[idx[0], idx[1], idx[2]]:
            sm = r
    return ncell, vol_ideal, sm/ell, ell/dx


print("T2: 单晶包络（envelope 模式）体积/半径 vs dx  —— 解析: 体积 = 8ℓ³/6, r(<100>) = ℓ")
print("  dx(um)   ℓ(胞)   实测体积   解析体积   体积相对误差   r(<100>)/ℓ")
for dx, frac in ((0.5e-6, 2), (1.0e-6, 1), (2.0e-6, 1), (3.0e-6, 1)):
    # 固定 ℓ = 15 µm：步数随 dx 变
    ell_target = 15e-6
    V = float(IRF().capped(np.array([DT_K]))[0][0])
    nst = int(round(ell_target/(V*dx/(4*V))))
    ncell, voli, ratio, ellc = run("envelope", dx, nst)
    print("  %6.2f  %6.1f  %9d  %9d   %+8.3f%%      %.3f" % (
        dx*1e6, ellc, ncell, voli, 100.0*(ncell-voli)/voli, ratio))