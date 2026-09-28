#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_edsign3.py --- 用**真板条几何**（惯习面法向 n_hab 为薄方向）判决：
   (a) 增厚（沿 n_hab）与 (b) 侧向长大（沿 a/w 面内）各自的**真实能量释放率**，
   与模型 `ed = -eps0:sigma` 在对应界面上的均值比较。
   这是"为什么板条会长厚（等轴化）"的直接定量判据。
"""
import os, sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

N, dx = 64, 2e-8
L = N * dx
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)
k = 1

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


def build(k0, dR=0.0, dt_=0.0):
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.0, Mob=1e-9,
                        df=[0.0] * (nv + 1), workers=4, reinit_every=0, k0_mode=k0)
    n_h = np.asarray(npref[k], float); n_h /= np.linalg.norm(n_h)
    a_t = np.asarray(g.atab[k], float); a_t /= np.linalg.norm(a_t)
    g.seed_plate(k, [L / 2] * 3, n_h, 2.0e-7 + dR, 4.0e-8 + dt_, elong=1.0)
    g.init_parent()
    reg = g.region()
    g.pf.phi[:] = 0.0
    for v in range(g.nv):
        g.pf.phi[v] = (reg == v + 1)
    return g, g.pf.E_el(), reg


def faces(reg, norm):
    """按界面法向分类：|n.u|>0.9 的面上胞（用几何法向）"""
    from scipy import ndimage as ndi
    chi = ndi.gaussian_filter((reg == k).astype(float), 1.2)
    gr = np.array(np.gradient(chi, dx))
    nn = np.moveaxis(gr, 0, -1)
    nrm = np.linalg.norm(nn, axis=-1) + 1e-30
    nn = nn / nrm[..., None]
    bnd = (chi > 0.25) & (chi < 0.75)
    for nm, u in norm.items():
        m = bnd & (np.abs(nn @ u) > 0.9)
        yield nm, m


for k0 in ('clamped', 'free'):
    R0, T0 = 2.0e-7, 4.0e-8
    _g, E0, reg0 = build(k0)
    d = 4e-9
    _, Ep_t, _ = build(k0, dt_=+d)      # 加厚
    _, Em_t, _ = build(k0, dt_=-d)
    _, Ep_R, _ = build(k0, dR=+d)       # 侧向长大
    _, Em_R, _ = build(k0, dR=-d)
    # 面积：面内面（惯习面）= 上下两面 ≈ 2*pi*R^2 ; 侧面积 ≈ 2*pi*R*T
    A_face = 2 * np.pi * R0 ** 2
    A_side = 2 * np.pi * R0 * T0
    D_thick = -(Ep_t - Em_t) / (2 * d) / A_face
    D_lat = -(Ep_R - Em_R) / (2 * d) / A_side
    g = _g
    ed = g.elastic_driving()
    n_h = np.asarray(npref[k], float); n_h /= np.linalg.norm(n_h)
    w_t = np.asarray(g.wtab[k], float); w_t /= np.linalg.norm(w_t)
    print('---- k0=%s  板条 R=%.0f nm 厚=%.0f nm  面内面积 %.3e m^2 侧面 %.3e m^2 ----'
          % (k0, R0 * 1e9, T0 * 1e9, A_face, A_side))
    print('   E_el: 薄 %.5e / 基准 %.5e / 厚 %.5e  J' % (Em_t, E0, Ep_t))
    print('   E_el: 小 %.5e / 基准 %.5e / 大 %.5e  J' % (Em_R, E0, Ep_R))
    print('   **加厚方向的正确驱动力 D = %.4e J/m^3**' % D_thick)
    print('   **侧向长大的正确驱动力 D = %.4e J/m^3**' % D_lat)
    for nm, u in (('大面(n_hab)', n_h), ('侧面(w)', w_t)):
        m = np.zeros(reg0.shape, bool)
        for _nm, _m in faces(reg0, {nm: u}):
            m = _m
        if m.sum() < 10:
            print('   %-12s 面上胞不足(%d)' % (nm, m.sum()))
            continue
        print('   %-12s 面胞 %6d ; 模型 ed 均值 = %+.4e J/m^3' % (nm, m.sum(), ed[1][m].mean()))
    print()
