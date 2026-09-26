#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_axis_vel.py --- 直接测**沿三个物理方向的界面位置 vs 时间**（不是 extent）。

为什么要它（记账）：extent 的增长混入两件事：
  (i) 界面**推进**（我们想测的）；
  (ii) 形状**圆化/平移**（Gibbs-Thomson、重初始化）—— 会让 extent 增长而界面并未沿该方向推进。
=> 用**从中心沿固定方向射射线找零等值面**，直接量界面位置 r(t)。
"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants(); nv = 12
rng = np.random.default_rng(0); npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best: best, bn = val, n
    npref[v + 1] = bn

N, dx = 64, 5e-8
L = N * dx
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [2e8] * nv, workers=6, reinit_every=25)
k = 1
n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
w1 = np.asarray(g.wtab[k], float)
a1 = np.cross(n1, w1); a1 /= np.linalg.norm(a1)
g.seed_plate(k, [L/2]*3, n1, 3.0e-7, 1.0e-7)
g.init_parent(); g.c[:] = 0.036
_M = 1e-9
_ed = g.elastic_driving()
dt = 0.15 * dx / (_M * (2e8 + 2.0 * float(np.max(np.abs(_ed)))))
BH, BW = 3.5, 2.3


def ray_r(g, k, d, dx):
    """从中心沿 +d / -d 找 phi_k 的零等值面，返回平均半径（物理单位）。"""
    c0 = np.array([L/2]*3)
    rs = []
    for sgn in (+1.0, -1.0):
        ts = np.arange(0.0, L/2, dx*0.2)
        pts = c0[None, :] + sgn * ts[:, None] * d[None, :]
        idx = np.floor(pts/dx).astype(int)
        ok = ((idx >= 0).all(1)) & ((idx < N).all(1))
        idx = idx[ok]; tt = ts[ok]
        val = g.phi[k][idx[:, 0], idx[:, 1], idx[:, 2]]
        neg = np.where(val < 0)[0]
        if len(neg) == 0:
            continue
        i = neg[-1]
        if i >= len(tt) - 1:
            continue
        r = tt[i] - val[i] * (tt[i+1] - tt[i]) / (val[i+1] - val[i])
        rs.append(r)
    return float(np.mean(rs)) if rs else np.nan


print('%-6s %-9s %10s %10s %10s   %8s %8s' %
      ('step', 'V(um^3)', 'r_n(um)', 'r_w(um)', 'r_a(um)', 'r_a/r_n', 'Mfac比'))
hist = []
for it in range(1, 1001):
    g.advance(dt, aniso=0.0, npref=npref, band_cells=6, mob_beta=BH, mob_beta_w=BW)
    if it % 100 == 0:
        rn, rw, ra = ray_r(g, k, n1, dx), ray_r(g, k, w1, dx), ray_r(g, k, a1, dx)
        V = g.volume(k)
        hist.append((it, V, rn, rw, ra))
        print('%-6d %-9.4f %10.4f %10.4f %10.4f   %8.2f' %
              (it, V*1e18, rn*1e6, rw*1e6, ra*1e6, ra/max(rn, 1e-30)), flush=True)
    nd = g.suggest_dt(cfl=0.15, dt_prev=dt)
    if nd:
        dt = nd
r0 = hist[0]; r1 = hist[-1]
print('\n沿各方向的**界面位移**（%d -> %d 步）：' % (r0[0], r1[0]))
print('  n_hab: %.4f -> %.4f um  (x%.2f)' % (r0[2]*1e6, r1[2]*1e6, r1[2]/r0[2]))
print('  w    : %.4f -> %.4f um  (x%.2f)' % (r0[3]*1e6, r1[3]*1e6, r1[3]/r0[3]))
print('  a    : %.4f -> %.4f um  (x%.2f)' % (r0[4]*1e6, r1[4]*1e6, r1[4]/r0[4]))
print('预期（Mfac 比 exp(-3.5):exp(-2.3):1 = 0.030:0.100:1）')
