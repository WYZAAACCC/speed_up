#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_mfac_ratio2.py --- 修正版：用与生产一致的配置（nv=12 + C + eps0 + npref），
   测 实测界面位移 / (M*df*Mfac) 随【界面取向】与【|grad phi| 格式】的变化。
   => 若比值随取向变化，或 central 与 upwind 差异大，就是"压制不足 => 等轴化"的来源。"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = 12
rng = np.random.default_rng(0)
npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn

N, dx = 48, 5e-8
L = N * dx
x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
BH, BW = 3.5, 2.3
M = 1e-9
dt = 0.15 * dx / (M * 2e8)

print('%-8s %-24s %11s %11s %8s' % ('grad', 'DIR 描述', 'v实测(m)', 'v预测(m)', '比值'))
for advg in ('upwind', 'central'):
    for nm, DIR in [('n_hab(惯习面法向)', None), ('w(宽度轴)', None),
                    ('a(长轴)', None), ('tilt(1,1,1)', np.array([1., 1., 1.]) / np.sqrt(3))]:
        g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=M,
                            df=[0.0] + [2e8] * nv, workers=2, reinit_every=0)
        k = 1
        if DIR is None:
            if nm.startswith('n_hab'):
                DIR = np.asarray(npref[k], float)
            elif nm.startswith('w'):
                DIR = np.asarray(g.wtab[k], float)
            else:
                DIR = np.cross(npref[k], g.wtab[k])
        DIR = DIR / np.linalg.norm(DIR)
        proj = X * DIR[0] + Y * DIR[1] + Z * DIR[2]
        g.phi[k] = proj - 0.5 * (proj.min() + proj.max())
        g.init_parent(); g.c[:] = 0.036
        g.pf = None
        def pmed():
            b = np.abs(g.phi[k]) <= 0.5 * dx
            return float(np.median(proj[b]))
        p0 = pmed()
        g.advance(dt, aniso=0.0, npref=npref, band_cells=6, mob_beta=BH,
                  mob_beta_w=BW, adv_grad=advg)
        dproj = pmed() - p0
        c2h = (DIR @ (np.asarray(npref[k], float) / np.linalg.norm(npref[k]))) ** 2
        c2w = (DIR @ (np.asarray(g.wtab[k], float) / np.linalg.norm(g.wtab[k]))) ** 2
        Mfac = float(np.exp(-BH * c2h - BW * c2w))
        v_pred = M * 2e8 * Mfac * dt
        print('%-8s %-24s %11.4e %11.4e %8.3f'
              % (advg, nm, dproj, v_pred, dproj / v_pred))
