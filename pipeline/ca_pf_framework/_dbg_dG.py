#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 M2 的界面驱动 dG 分解成三项（df / 弹性 / 曲率），看哪一项主导、符号对不对。
   dG = (df_karr − df_larr) + (ed_karr − ed_larr) − γ_eff,karr·κ_karr
"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, _lam_full
from windowB_ti64_variants import variants
from windowB_surface import herring_stiffness

aniso, t_dx = 10.0, 6.0
N, dx, df, gamma, Mob, rfrac = 32, 1e-8, -1e8, 0.15, 1e-9, 0.22
C = C_iso3(113e9, 0.34)
eps0, Fs, meta = variants()
nv = len(eps0)
g = W.LevelSetMulti(N, N * dx, C=C, eps0=eps0, gamma=gamma, Mob=Mob,
                    df=[0.0] + [df] * nv, workers=6, reinit_every=25)
npref = {}
rng = np.random.default_rng(0)
for v in range(nv):
    best = None
    bn = None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn
R = rfrac * N * dx
for v in range(nv):
    g.seed_plate(v + 1, (rng.random(3) * (N * dx - 2 * R) + R), npref[v + 1], R,
                 t_dx * dx)
g.init_parent()

order = np.argsort(g.phi, axis=0)
karr, larr = order[0], order[1]
reg = g.region()
m = g.surface_band()
ed = g.elastic_driving()
edk = np.take_along_axis(ed, karr[None], 0)[0]
edl = np.take_along_axis(ed, larr[None], 0)[0]
dF = g.df[karr] - g.df[larr]
# 各向异性有效刚度（与 advance 一致）
stiff = np.ones(g.phi.shape)
for k in range(g.nreg):
    gr = np.gradient(g.phi[k], g.dx)
    gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-30
    if aniso > 0 and npref.get(k) is not None:
        n = np.stack([x / gn for x in gr], -1)
        nd = np.asarray(npref[k], float)
        nd = nd / np.linalg.norm(nd)
        c2 = np.clip((n @ nd) ** 2, 0.0, 1.0)
        stiff[k] = herring_stiffness(c2, gamma, aniso, True)
stk = np.take_along_axis(stiff, karr[None], 0)[0]
kap = np.take_along_axis(np.stack([g.curvature_of(k) for k in range(g.nreg)]),
                         karr[None], 0)[0]
cur = -stk * kap
print('界面带胞数 =', int(m.sum()))
for name, arr in (('df项', dF), ('弹性项', edk - edl), ('曲率项(-stk*kap)', cur)):
    v = arr[m]
    print('   %-16s 中位=%12.3e  p5=%12.3e p95=%12.3e' %
          (name, np.median(v), np.percentile(v, 5), np.percentile(v, 95)))
print('   γ_eff 中位=%8.3f 最小=%8.3f 最大=%8.3f' %
      (np.median(stk[m]), stk[m].min(), stk[m].max()))
print('   界面类型（karr,larr）分布:', end=' ')
from collections import Counter
print(Counter(zip(karr[m].tolist(), larr[m].tolist())).most_common(6))
dG = dF + (edk - edl) + cur
print('   dG 中位=%12.3e  ⇒ 若为负则 winner 收缩' % np.median(dG[m]))
print('   占界面多数类型 {0,k}: dG 中位=%12.3e' %
      np.median(dG[m & (karr == 0)]))