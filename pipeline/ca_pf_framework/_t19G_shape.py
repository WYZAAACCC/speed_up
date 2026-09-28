#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t19G_shape.py --- D17 的**第三条判据**：`proj2` 会不会像 Godunov 迎风那样
   **压低形状各向异性**（W1 的记账说迎风把 a2 压低 ~8%、且不随 dx 收敛）？

设计（T9-D 的已验证口径，单变量：只换 `adv_grad`）
------------------------------------------------
  单核薄板 + 12 变体 + 弹性 + `mob_beta=3.5, mob_beta_w=2.3` + `npref`，
  N=48 / Δx=25 nm / L=1.2 µm / 120 步 / `reinit_every=25`（与 T9-D 逐字相同）。
  量：三向尺度比（PCA 特征值开方）+ 最薄方向 vs `npref[1]` 的夹角。
  ★ 正对照：`central` 是 D17 之前的默认，归档值 = **8.93 : 2.76 : 1**、角 **2.88°**。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

N, dxn = 48, 25.0
dx = dxn * 1e-9
L = N * dx
DF, MOB = 2.0e8, 1e-9


def go(adv, nstep=120):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=25)
    g.seed_plate(1, [L / 2] * 3, NPF[1], 0.10 * L, 4 * dx)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    for _ in range(nstep):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5,
                  mob_beta_w=2.3, adv_grad=adv)
    reg = g.region()
    idx = np.argwhere(reg == 1)
    f = float((reg == 1).sum()) / g.N ** 3
    if idx.size < 30:
        return None
    p = idx.astype(float) * dx
    p = p - p.mean(0)
    ev, evec = np.linalg.eigh(np.cov(p.T))
    thin = evec[:, int(np.argmin(ev))]
    ang = float(np.degrees(np.arccos(np.clip(abs(thin @ NPF[1]), 0, 1))))
    s = np.sqrt(ev / ev[0])
    return dict(f=f, r_long=float(s[2]), r_mid=float(s[1]), ang=ang,
                # 界面键数（P1 口径）：粗化会让它爆
                nb=int(sum((reg != np.roll(reg, -1, ax)).sum() for ax in range(3))))


print('=' * 100)
print('_t19G —— 形状各向异性 vs 平流格式（T9-D 口径，N=%d Δx=%.0f nm L=%.2f µm 120 步）'
      % (N, dxn, L * 1e6))
print('  归档正对照（central，D17 之前）：尺度比 **8.93 : 2.76 : 1**、角 **2.88°**')
print('-' * 100)
print('  %-9s %-9s %-9s %-9s %-9s %s' % ('adv', 'f', '长:中:薄', '最薄角(°)', '界面键', '判定'))
rows = {}
for adv in ('central', 'upwind', 'upwind2', 'proj', 'proj2'):
    r = go(adv)
    rows[adv] = r
    if r is None:
        print('  %-9s 变体太小' % adv)
        continue
    print('  %-9s %-9.4f %-9s %-9.2f %-9d %s'
          % (adv, r['f'], '%.2f:%.2f:1' % (r['r_long'], r['r_mid']), r['ang'], r['nb'],
             '★' if (r['ang'] < 20 and r['r_long'] > 1.6 * r['r_mid']) else '形状不足'), flush=True)
c = rows.get('central')
p2 = rows.get('proj2')
if c and p2:
    print('-' * 100)
    print('  proj2 / central ：长径比 %.3f → %.3f（比 %.3f）；中径比 %.3f → %.3f（比 %.3f）'
          % (c['r_long'], p2['r_long'], p2['r_long'] / c['r_long'],
             c['r_mid'], p2['r_mid'], p2['r_mid'] / c['r_mid']))
    print('  判据：proj2 的长径比 **不低于 central 的 90%%**（否则说明迎风的数值扩散'
          '把形状各向异性也压掉了）')
    print('  ⇒ %s' % ('PASS' if p2['r_long'] >= 0.90 * c['r_long'] else 'FAIL'))
print('=' * 100)
