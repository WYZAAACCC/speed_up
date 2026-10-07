#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r147_dbg.py —— 为什么自检里 `cov = nan`？（对着**真快照**比）"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

p = os.path.join(HERE, '_exp', '_bk_cvchk', 'dry_cvchk', 'snap_00000.npz')
print('快照存在：', os.path.exists(p))
z = np.load(p)
print('键：', list(z.files))
reg = z['region']
print('`region` 形状 %s，取值 %s' % (reg.shape, np.unique(reg)))
print('`L` = %r' % float(z['L']))
print('`n_hab` = %s' % np.asarray(z['n_hab']))
print('`vmap_keys` = %s  `vmap_vals` = %s'
      % (np.asarray(z['vmap_keys']), np.asarray(z['vmap_vals'])))
c = BM.snapshot_coverage(z)
print()
print('**对真快照** `snapshot_coverage`： cov=%.4f  f3_area=%.4f  exp_int=%.4f  n_occ=%d'
      % (c['cov'], c['f3_area'], c['exp_int'], c['n_occ']))
print('   beta_frac = %s' % {k: round(v, 3) for k, v in c['beta_frac'].items()})
print()
# 复刻驱动里那份手工 dict，看差在哪
dx = float(z['L']) / reg.shape[0]
n_hab = np.asarray(z['n_hab'], float)
vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
print('dx = %.3e m ; n_hab 模 = %.4f' % (dx, np.linalg.norm(n_hab)))
for k in sorted(vmap):
    m = (reg == k)
    nv = int(m.sum())
    e, eb = BM._linear_extent(m, n_hab, dx)
    print('  场 %d（V%d）：体素 %-6d  `_linear_extent` 沿 n* = %.4e m  （eb=%.4e）'
          % (k, vmap[k], nv, e, eb))
print()
print('⇒ 若某场的 `_linear_extent` 沿 n* 给 0 或负 ⇒ `n_occ` 少算 ⇒ `exp_int` 变小/为 0。')
print('⇒ 若**全部**为 0 ⇒ 问题在 `n_hab`（例如传了未归一化或错的轴）。')
