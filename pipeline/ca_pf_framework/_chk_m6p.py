#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_m6p.py --- M6' 口径：**变体-母相界面**法向 vs npref[k]（惯习面钉扎的直接判据）。

为什么需要它（记账）：M6（_chk_morph.py 口径）只统计**变体-变体**界面。
  但 mob_aniso 让生长变慢（GX 的 f=0.064 vs G0 的 0.185）=> 界面绝大多数是
  **变体-母相** => 用变体-变体口径去判"惯习面钉扎"是**口径错**（样本既少又不相关）。
本脚本直接测每个变体与母相的界面法向 vs npref[k]（npref = 弹性最省能法向 = 惯习面法向）。
"""
import sys
import numpy as np
from scipy import ndimage as ndi

from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)


def npref_table(seed=0):
    rng = np.random.default_rng(seed)
    tab = {}
    for v in range(nv):
        best, bn = None, None
        for n in rng.normal(size=(400, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
            if best is None or val < best:
                best, bn = val, n
        tab[v + 1] = bn
    return tab


NP = npref_table()
rng = np.random.default_rng(0)
ns = rng.normal(size=(600, 3)); ns /= np.linalg.norm(ns, axis=1)[:, None]

print('=== M6p: 变体-母相界面法向 vs npref[k]（惯习面）===')
for p in sys.argv[1:]:
    d = np.load(p)
    reg = d['reg']; dx = float(d['dx'])
    f = 1.0 - float((reg == 0).mean())
    angs, rnds, cells = [], [], 0
    for k in range(1, nv + 1):
        m = (reg == k)
        ncell = int(m.sum())
        if ncell < 200:
            continue
        # 与母相相邻的界面带：reg==k 的边界
        chi = ndi.gaussian_filter(m.astype(float), 1.5)
        gr = np.array(np.gradient(chi, dx))
        bnd = (chi > 0.2) & (chi < 0.8)
        # 只取"外侧是母相"的带（用膨胀后的母相掩模交）
        par = ndi.binary_dilation(reg == 0, iterations=2)
        bnd &= par
        nn = np.moveaxis(gr, 0, -1)[bnd]
        nrm = np.linalg.norm(nn, axis=1)
        nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
        if nn.shape[0] == 0:
            continue
        nd = NP[k]
        angs.append(np.degrees(np.arccos(np.clip(np.abs(nn @ nd), 0, 1))))
        rnds.append(np.degrees(np.arccos(np.clip(np.abs(ns @ nd), 0, 1))))
        cells += nn.shape[0]
    if not angs:
        print('  %s: 无可用界面（f=%.3f）' % (p, f)); continue
    a = np.concatenate(angs); r = np.concatenate(rnds)
    print('  %-42s f=%.4f  界面点 %6d  M6p 中位 %5.1f deg (随机 %5.1f)  p25 %5.1f'
          % (p.split('/')[-1], f, cells, np.median(a), np.median(r), np.percentile(a, 25)))
