#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r720_seedchk.py <seeds.npz> —— 查 t=0 的**实际**在场场数与核胞数（只读体检）。

⚠ 为什么需要它：`seeds.npz` 的 `phi` 是**稀疏带存储**（带外填 0）⇒
   `phi[k] < 0` 的计数**只对带内有效**，不能直接当"该场体积"。
   本脚本同时报 `region` 的逐场计数（`region` 是**全网格**的）以便交叉核对。
"""
import sys

import numpy as np

p = sys.argv[1]
z = np.load(p, allow_pickle=False)
phi = np.asarray(z['phi'])
reg = np.asarray(z['region'])
print('=' * 90)
print(p)
print('=' * 90)
print('  phi.shape = %s   region.shape = %s' % (phi.shape, reg.shape))
vals, cnt = np.unique(reg, return_counts=True)
print('  `region` 逐场胞数（**全网格**，可信）：')
for v, c in zip(vals, cnt):
    print('     场 %-3d  %7d 胞  (%.4f%%)' % (int(v), int(c), 100.0 * c / reg.size))
print('  `phi[k] < 0` 计数（**只对带内有效**）：')
for k in range(phi.shape[0]):
    n = int((phi[k] < 0).sum())
    nz = int((phi[k] != 0).sum())
    if nz:
        print('     场 %-3d  零集 %6d 胞   非零(带内) %7d 胞' % (k, n, nz))
print()
print('  ⚠ 判读：`phi<0` 的计数**不能**当体积用（带外是 0，不是正的大数）；')
print('     要体积必须用 `region`，或把带外正确地填成正的大数。')
