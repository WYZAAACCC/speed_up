#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r148_dbg2.py —— 用**驱动里那份手工 dict**调 `snapshot_coverage`，与真快照并排。"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

p = os.path.join(HERE, '_exp', '_bk_cvchk', 'dry_cvchk', 'snap_00000.npz')
z = np.load(p)
reg = z['region']
L = float(z['L'])
n_hab = np.asarray(z['n_hab'], float)

# ① 真快照
c1 = BM.snapshot_coverage(z)
# ② 手工 dict（与驱动里同一构造）
zc = dict(region=reg, L=L, n_hab=n_hab,
          vmap_keys=np.array(sorted({1: 1, 2: 1, 3: 1})),
          vmap_vals=np.array([1, 1, 1]))
c2 = BM.snapshot_coverage(zc)
# ③ 手工 dict，但 region 是 `np.array` 的副本（看是不是"视图/只读"的问题）
zc3 = dict(region=np.array(reg), L=L, n_hab=n_hab,
           vmap_keys=np.array([1, 2, 3]), vmap_vals=np.array([1, 1, 1]))
c3 = BM.snapshot_coverage(zc3)

print('=' * 92)
print('_r148 —— 手工 dict vs 真快照')
print('=' * 92)
for lab, c in (('① 真快照', c1), ('② 手工 dict', c2), ('③ 手工+array 副本', c3)):
    print('  %-18s cov=%-10s f3=%.6e  exp=%.6e  n_occ=%d  maxβ=%s'
          % (lab, c['cov'], c['f3_area'], c['exp_int'], c['n_occ'],
             (max(c['beta_frac'].values()) if c['beta_frac'] else None)))
print()
print('  ⚠ `cov = tot_f3/exp_int if exp_int>0 else nan` ⇒ `nan` 只可能来自 `exp_int<=0`')
print('     ⇒ 若 ② 正常而驱动里给 nan，那驱动传进去的 `region` 就是**空的**')
print('     ⇒ 最可能：自检跑在 `init_parent()` **之前**（`phi` 还没落定 ⇒ region 全 0）。')
print()
# 直接验：全 0 的 region 会给什么
z0 = dict(region=np.zeros_like(reg), L=L, n_hab=n_hab,
          vmap_keys=np.array([1, 2, 3]), vmap_vals=np.array([1, 1, 1]))
c0 = BM.snapshot_coverage(z0)
print('  **负对照**（`region` 全 0）：cov=%s f3=%.3e exp=%.3e n_occ=%d'
      % (c0['cov'], c0['f3_area'], c0['exp_int'], c0['n_occ']))
print('     ⇒ 与驱动里 `cov=nan` 的读数**一致**吗？ %s'
      % ('**一致 ⇒ 确认是"region 全 0"**' if c0['cov'] != c0['cov'] else '不一致'))
