#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_w8c.py --- W-8c：盒子 B 的 **Delta x 收敛（真判决版）**。

修掉 W-8b 的两处混淆：
  (1) **物理单位种子**：位置/半径/厚度全部用**米**给定，三档 Delta x 看到**同一初始组织**
      （W-8b 用驱动自带的  ⇒ 种子厚随 Delta x 变 ✗）。
  (2) **显式时间控制**：按**累计物理时间**循环（），每步 dt 由 CFL 定
      ⇒ 三档的物理时间**严格相同**（W-8b 用固定步数 ⇒ 总时间不等 ✗）。

盒子取 **L = 8 µm**（不是 20 µm）：因为 N=160（L=20 µm @ 0.125 µm）实测 **101 s/步**，
三档不可行；L=8 µm 下三档 N=16/32/64，最细档 ~2 s/步 ⇒ 三档都在几分钟内。
物理设置（三档相同）：6 个晶核、位置固定、**R = 1.6 µm**、**厚 t = 1.0 µm**（0.5 µm 网格上仍有 2 胞）。

判据：W8c-1 |f - f_fine| < 0.05；W8c-2 |t - t_fine|/t_fine < 0.30；
      W8c-3 **收敛趋势**：粗档与中间档的差 > 中间档与细档的差（一阶收敛的指纹）。
"""
import sys
import time

import numpy as np

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

L = 8.0e-6
R_M, T_M = 1.6e-6, 1.0e-6
NSEED = 6
T_END = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0e-6
DF = 1e8
CFL = 0.15


def nuclei():
    rng = np.random.default_rng(11)
    out = []
    for _ in range(NSEED):
        c = rng.random(3) * (L - 2 * R_M) + R_M
        out.append((c, int(rng.integers(1, 13))))
    return out


NUC = nuclei()


def npref_of(C, rng, eps0, nv=12):
    d = {}
    for v in range(nv):
        best, bn = None, None
        for n in rng.normal(size=(150, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
            if best is None or val < best:
                best, bn = val, n
        d[v + 1] = bn
    return d


def run(dx):
    N = int(round(L / dx))
    assert abs(N * dx - L) < 1e-15 * L, (N, dx)
    C = C_cubic(134.0e9, 110.0e9, 36.0e9)
    eps0, _F, _m = variants()
    nv = len(eps0)
    rng = np.random.default_rng(5)
    npf = npref_of(C, rng, eps0, nv)
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] * (nv + 1), workers=6, reinit_every=25)
    for c, k in NUC:
        g.seed_plate(k, c, npf[k], R_M, T_M)      # ★ 物理单位（米）
    g.init_parent()
    g.c[:] = 0.036
    g.df[1:] = DF
    t = 0.0
    dt = CFL * dx / (1e-9 * DF)
    n = 0
    t0 = time.time()
    while t < T_END:
        g.advance(dt, aniso=0.4, npref=npf, band_cells=20)
        g.update_Gamma(dt)
        t += dt
        n += 1
        nd = g.suggest_dt(cfl=CFL, dt_prev=dt)
        if nd:
            dt = nd
    reg = g.region()
    f = 1.0 - float((reg == 0).mean())
    Sv = g.area_total_geom() / L ** 3
    v = np.array([g.volume(j) for j in range(g.nreg)])[1:]
    return dict(N=N, dx=dx, n=n, t=t, f=f, Sv=Sv, t_plat=2 * f / max(Sv, 1e-30),
                unif=float(v.max() / max(v.min(), 1e-30)),
                band=g.band_health()[0], secs=time.time() - t0)


print('==== W-8c 盒子 B 的 Delta x 收敛（L=%.0f µm，物理种子 R=%.1f µm/t=%.1f µm，t_end=%.1e s）===='
      % (L * 1e6, R_M * 1e6, T_M * 1e6, T_END))
res = []
for dx in (0.5e-6, 0.25e-6, 0.125e-6):
    r = run(dx)
    res.append(r)
    print('   dx=%.3f µm  N=%3d  nstep=%4d (t=%.3e s) : f=%.4f  板片厚=%.3f µm  均分度=%.2f  带=%6d  %.0f s'
          % (r['dx'] * 1e6, r['N'], r['n'], r['t'], r['f'], r['t_plat'] * 1e6,
             r['unif'], r['band'], r['secs']))
c, m, fine = res
d_cm = abs(m['t_plat'] - c['t_plat']) / max(fine['t_plat'], 1e-30)
d_mf = abs(fine['t_plat'] - m['t_plat']) / max(fine['t_plat'], 1e-30)
f_cm = abs(m['f'] - c['f'])
f_mf = abs(fine['f'] - m['f'])
print('   板片厚相对差: 粗-中 %.1f%% ; 中-细 %.1f%%' % (100 * d_cm, 100 * d_mf))
print('   f 的差      : 粗-中 %.4f ; 中-细 %.4f' % (f_cm, f_mf))
print('   W8c-1 f 收敛到最细档（<0.05）: %s' % ('PASS' if f_mf < 0.05 else 'FAIL'))
print('   W8c-2 板片厚收敛到最细档（<30%%）: %s' % ('PASS' if d_mf < 0.30 else 'FAIL'))
print('   W8c-3 收敛趋势（粗-中的差 > 中-细的差）: %s'
      % ('PASS' if (d_cm > d_mf and f_cm > f_mf) else 'FAIL'))
