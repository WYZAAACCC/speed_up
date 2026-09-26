#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_mfac.py --- 直接检查 Mfac 在界面上的**实际方向分布**。
   预期（设计意图）：法向沿 n_hab 的界面 Mfac 最小；沿 a 的最大。
   做法：跑 6 步后在 |phi_1| <= 2dx 的带上，按 |n.n_hab| 分桶打印平均 Mfac 与胞数。
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

N, dx, L = 64, 5e-8, 64 * 5e-8
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [2e8] * nv, workers=6, reinit_every=25)
k = 1
n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
w1 = np.asarray(g.wtab[k], float)
a1 = np.cross(n1, w1); a1 /= np.linalg.norm(a1)
print('n_hab =', np.round(n1, 4), ' w =', np.round(w1, 4), ' n x w =', np.round(a1, 4))
print('w.n_hab = %.3f (应 ~0)   (nxw).n_hab = %.3f' % (w1 @ n1, a1 @ n1))

g.seed_plate(k, [L / 2, L / 2, L / 2], n1, 3.0e-7, 1.0e-7)
g.init_parent(); g.c[:] = 0.036
_M = 1e-9
_ed = g.elastic_driving()
dt = 0.15 * dx / (_M * (2e8 + 2.0 * float(np.max(np.abs(_ed)))))
BH, BW = 3.5, 2.3
for it in range(6):
    g.advance(dt, aniso=0.0, npref=npref, band_cells=20, mob_beta=BH, mob_beta_w=BW)

# --- 手动复算 advance 里的 ndir_ / Mfac（同代码路径）---
reg = g.region()
order = np.argsort(g.phi, axis=0)
karr, larr = order[0], order[1]
pha = np.take_along_axis(g.phi, karr[None], 0)[0]
phb = np.take_along_axis(g.phi, larr[None], 0)[0]
gd_ = np.gradient(pha - phb, g.dx)
gdn = np.sqrt(sum(x ** 2 for x in gd_)) + 1e-30
ndir = np.stack([x / gdn for x in gd_], -1)
ndir = ndir / (np.linalg.norm(ndir, axis=-1, keepdims=True) + 1e-300)
band = np.abs(g.phi[k]) <= 2.0 * dx
nn = ndir[band]
print('带上胞数 =', nn.shape[0], ' karr/larr 取值:', np.unique(karr), np.unique(larr))
c2b = np.clip((nn @ n1) ** 2, 0, 1)
c2w = np.clip((nn @ w1) ** 2, 0, 1)
c2a = np.clip((nn @ a1) ** 2, 0, 1)
mf = np.exp(-BH * c2b - BW * c2w)
print('\n按 |n.nd_hab| 分桶：')
for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]:
    sel = (np.abs(nn @ n1) >= lo) & (np.abs(nn @ n1) < hi)
    if sel.sum():
        print('   |n.n_hab| in [%.1f,%.1f): 胞 %6d  平均 Mfac %.4f  平均 |n.w| %.2f  平均 |n.a| %.2f'
              % (lo, hi, sel.sum(), mf[sel].mean(), np.abs(nn[sel] @ w1).mean(), np.abs(nn[sel] @ a1).mean()))
print('\n平均 |n.n_hab| = %.3f  平均 |n.w| = %.3f  平均 |n.a| = %.3f'
      % (np.abs(nn @ n1).mean(), np.abs(nn @ w1).mean(), np.abs(nn @ a1).mean()))
print('=> 若 Mfac 在 |n.n_hab|->1 处最小，则大面被压制（设计意图）')
