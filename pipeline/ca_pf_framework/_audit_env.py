#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_env.py --- 多取向扫描：decentered vs analytic 的【有效包络径向距离】
理论: KD 八面体 {Σ|u_a|<=ℓ} 的径向函数 r(n̂)=ℓ/Σ_a|p_a·n̂|  => <100>:<111> = 1:0.577
"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ

NXYZ = (91, 91, 91)
DX = 1.0e-6
NSTEP = 60
DT_K = 12.0


def quat_aa(axis, deg):
    a = np.array(axis, float); a /= np.linalg.norm(a)
    th = math.radians(deg)
    return (math.cos(th/2), *(a*np.sin(th/2)))


def reach_at(ca, seed, nw, ell, solid, nxyz):
    sm = 0.0
    for r in np.arange(0.0, 2.5*ell, 0.2*DX):
        p = (np.array(seed, float) + 0.5)*DX + r*nw
        idx = np.floor(p/DX).astype(int)
        if np.any(idx < 0) or np.any(idx >= np.array(nxyz)):
            break
        if solid[idx[0], idx[1], idx[2]]:
            sm = r
    return sm


def one(mode, q):
    ca = CA3D(*NXYZ, DX, irf=IRF(), seed=7, capture=mode)
    c = tuple(s//2 for s in NXYZ)
    g = ca.add_grain(c[0], c[1], c[2], quat=q)
    P = ca.axes[g]
    T = ca.T_iso(DT_K)
    V = float(ca.irf.capped(np.array([DT_K]))[0][0])
    dt = DX/(4*V)
    t = 0.0
    for s in range(NSTEP):
        ca.t = t
        ca.step(dt, T, window="full")
        t += dt
    ell = V*NSTEP*dt
    solid = ca.gid > 0
    out = {}
    for nm, cv in (("<100>", (1, 0, 0)), ("<110>", (1, 1, 0)), ("<111>", (1, 1, 1)),
                   ("mid", (1, 0.45, 0.15))):
        cv = np.array(cv, float); cv /= np.linalg.norm(cv)
        nw = P @ cv
        sm = reach_at(ca, c, nw, ell, solid, NXYZ)
        out[nm] = (sm/ell, 1.0/np.abs(cv).sum())
    return out, int(solid.sum()), ell


qs = [("随机A", quat_aa((0.3, 0.7, 0.2), 37.0)),
      ("随机B", quat_aa((1.0, 0.2, 0.5), 61.0)),
      ("随机C", quat_aa((0.1, 0.9, 0.4), 23.0)),
      ("随机D", quat_aa((0.6, 0.6, 0.5), 80.0)),
      ("随机E", quat_aa((0.9, 0.1, 0.1), 44.0)),
      ("对齐",   quat_aa((0.0, 0.0, 1.0), 90.0))]
print("定向代理: 单晶中心生长, dT=%.0f K (V=%.4f m/s), dx=%.1f um, %d 步 => ℓ = %.1f 胞" % (
    DT_K, 0.0906, DX*1e6, NSTEP, 0))
print("表内每格 = 实测 r/ℓ ; 括号 = 理论 ℓ/Σ ; 各向异性比 = r(<100>)/r(<111>)")
for mode in ("envelope", "analytic", "decentered"):
    print("\n--- 模式 %s ---" % mode)
    print("  取向    r(<100>)/ℓ      r(<110>)/ℓ      r(<111>)/ℓ      r(mid)/ℓ     <100>/<111>  体积(胞)")
    for nm, q in qs:
        o, ncell, ell = one(mode, q)
        a = o["<100>"][0]/o["<111>"][0]
        print("  %-6s %.3f (%.3f)  %.3f (%.3f)  %.3f (%.3f)  %.3f (%.3f)   %.2f        %d" % (
            nm, o["<100>"][0], o["<100>"][1], o["<110>"][0], o["<110>"][1],
            o["<111>"][0], o["<111>"][1], o["mid"][0], o["mid"][1], a, ncell))