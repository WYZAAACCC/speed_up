#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""④ 的判据：Sussman PDE 式重初始化必须 (a) 把 |∇φ| 拉回 1，
   且 (b) **不移动零等值面**（界面位置保持）。对照旧做法（按掩模重建距离场）会移动界面。"""
import numpy as np
from windowB_surface import LevelSetMulti

N, dx = 48, 2e-9
g = LevelSetMulti(N, N * dx, nv=1)
xx = (np.arange(N) + 0.5) * dx
X = xx[None, None, :] * np.ones((N, N, N))
g.phi[1] = 0.35 * dx * np.sin(2 * np.pi * X / (N * dx) * 3.0) + (X - 0.5 * N * dx)
g.init_parent()
before = g.phi[1].copy()
# 人为破坏 SDF 性质（乘一个非均匀因子），看重初始化能否修回
g.phi[1] = before * 1.8
gi = np.gradient(g.phi[1], dx)
gn_before = np.sqrt(sum(a ** 2 for a in gi))
grey = np.abs(g.phi[1]) < 6 * dx
print('---- ④ 判据：Sussman 重初始化 ----')
print('   重初始化前 |∇φ| 在带内: 均值 %.3f（应为 1）' % gn_before[grey].mean())
g.reinitialize(band_cells=6)
gi = np.gradient(g.phi[1], dx)
gn_after = np.sqrt(sum(a ** 2 for a in gi))
print('   重初始化后 |∇φ| 在带内: 均值 %.3f（应回到 ≈1）' % gn_after[grey].mean())
# 零等值面位置：用线性插值找 φ 变号处的坐标（粗网格统计）
def zero_positions(p):
    s = np.sign(p)
    zi = np.argwhere(s[:, :, :-1] * s[:, :, 1:] < 0)
    if len(zi) == 0:
        return np.array([])
    return np.array([ (i, j) for i, j, k in zi ], float)
z_before, z_after = zero_positions(before * 1.0), zero_positions(g.phi[1])
print('   零等值面胞对数: 前 %d ; 后 %d（应相近，说明界面没被移动）'
      % (len(z_before), len(z_after)))
ok = abs(gn_after[grey].mean() - 1.0) < 0.25 and abs(len(z_after) - len(z_before)) < 0.1 * max(len(z_before), 1)
print('   判定: %s' % ('PASS' if ok else 'FAIL'))
