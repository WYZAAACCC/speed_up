#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_vnk.py --- 反推实际作用在界面上的速度 vnk，与 v_cell 逐胞对比。
   关掉重初始化（reinit_every=0）以排除 reinit 干扰。"""
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

N, dx = 48, 5e-8
L = N * dx
x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')

for axname in ['n', 'w', 'a']:
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [2e8] * nv, workers=4, reinit_every=0)  # 关重初始化
    k = 1
    n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
    w1 = np.asarray(g.wtab[k], float)
    a1 = np.cross(n1, w1); a1 /= np.linalg.norm(a1)
    DIR = {'n': n1, 'w': w1, 'a': a1}[axname]
    proj = X * DIR[0] + Y * DIR[1] + Z * DIR[2]
    g.phi[k] = proj - 0.5 * (proj.min() + proj.max())
    g.init_parent(); g.c[:] = 0.036
    g.pf = None                       # 关弹性（隔离）
    M = 1e-9
    dt = 0.15 * dx / (M * 2e8)
    ph0 = g.phi[k].copy()
    g.advance(dt, aniso=0.0, npref=npref, band_cells=8, mob_beta=3.5, mob_beta_w=2.3)
    dphi = g.phi[k] - ph0
    # 反推 vnk = -dphi/(dt*gmag)，取界面附近
    gn = np.sqrt(sum(t**2 for t in np.gradient(ph0, dx))) + 1e-30
    band = np.abs(ph0) <= 0.5 * dx
    vnk_eff = -dphi[band] / (dt * gn[band])
    # 理论 v_cell
    order = np.argsort(ph0, axis=0)  # 用初始 phi
    # 重算理论 v_cell（同 _dbg_plane_step 的路径）
    g2 = g
    karr, larr = np.argsort(ph0, axis=0), None
    Mf = np.exp(-3.5 * np.clip((np.stack(np.gradient(ph0, dx), -1) @ n1 / gn) ** 2, 0, 1)
                - 2.3 * np.clip((np.stack(np.gradient(ph0, dx), -1) @ w1 / gn) ** 2, 0, 1))
    v_theory = M * 2e8 * Mf
    print('axis=%s  band=%d' % (axname, band.sum()))
    print('   vnk_eff  : mean %+.4e  med %+.4e' % (vnk_eff.mean(), np.median(vnk_eff)))
    print('   v_theory : mean %+.4e  med %+.4e   (M*df*Mfac)' % (v_theory[band].mean(), np.median(v_theory[band])))
    print('   ratio eff/theory = %.3f  (mean)  %.3f (med)'
          % (vnk_eff.mean() / max(v_theory[band].mean(), 1e-30),
             np.median(vnk_eff) / max(np.median(v_theory[band]), 1e-30)))
