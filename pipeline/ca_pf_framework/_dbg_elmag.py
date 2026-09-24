#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 M2 的弹性驱动量级是否合理。
   一阶估计：0.5·ε⁰:C:ε⁰ 应与 df=1e8 同量级（甚至更小）；若实测大 ~50 倍，则
   `e0v_eng`（VOIGT/G6 因子）或 `sigma_tensor()` 的量纲/因子有问题。
"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, VOIGT, G6, PF3D
from windowB_ti64_variants import variants
eps0, Fs, meta = variants()
eps0 = np.asarray(eps0)
print('eps0 形状', eps0.shape, ' max|eps0| =', np.abs(eps0).max())
C = C_iso3(113e9, 0.34)
print('C_iso3 尺度: C[0,0,0,0] =', C[0, 0, 0, 0])
G6a = np.array(G6)
print('G6 =', G6a)
e0v = np.array([[eps0[v][i, j] for (i, j) in VOIGT] for v in range(len(eps0))])
print('e0v(未乘G6) max =', np.abs(e0v).max(),
      ' 乘G6后 max =', np.abs(e0v * G6a[None, :]).max())
# 一阶能量尺度：0.5 eps:C:eps（用 Voigt，含工程剪应变因子）
Ct = C[0, 0, 0, 0]
print('一阶估计 0.5*C*(max|eps|)^2 = %.3e' % (0.5 * Ct * np.abs(eps0).max() ** 2))
print('对照 df = 1.000e+08')
N, dx, Mob = 32, 1e-8, 1e-9
g = W.LevelSetMulti(N, N * dx, C=C, eps0=eps0, gamma=0.15, Mob=Mob,
                    df=[0.0] + [-1e8] * len(eps0), workers=6, reinit_every=25)
rng = np.random.default_rng(0)
R = 0.22 * N * dx
npref = {}
from windowB_pf3d import _lam_full
for v in range(len(eps0)):
    best = None; bn = None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best: best, bn = val, n
    npref[v + 1] = bn
for v in range(len(eps0)):
    g.seed_plate(v + 1, (rng.random(3) * (N * dx - 2 * R) + R), npref[v + 1], R, 6 * dx)
g.init_parent()
sig = g.pf.sigma_tensor()
print('sigma_tensor: max|sig| = %.3e  (Voigt 6 分量)' % np.abs(sig).max())
ed = g.elastic_driving()
print('弹性能量项 max %.3e 中位(带内) %.3e' % (np.abs(ed).max(), np.median(np.abs(ed[g.surface_band()]))))