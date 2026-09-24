#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A3 重做（② 的判据）：面扩散必须**只沿切向**。
   做法：平界面 + 带内一个**局部** Γ 斑块（不是均匀！上次写错成均匀 ⇒ 空转 ✗），
   跑面扩散后量 (a) 法向二阶矩（不应增长）(b) 切向二阶矩（应增长）。"""
import numpy as np
from windowB_surface import LevelSetMulti

N, dx = 48, 2e-9
g = LevelSetMulti(N, N * dx, nv=1)
z = np.arange(N)[None, None, :] * dx
X = np.arange(N)[None, :, None] * dx
g.phi[1] = np.where(z < 0.5 * N * dx, -1e-9, 1e-9) * np.ones((N, N, N))
g.init_parent()
m = g.surface_band()
cx = 0.5 * N * dx
g.Gam = np.zeros_like(g.phi[0])
patch = m & (np.abs(X - cx) < 4 * dx)               # 局部斑块（切向窄）
g.Gam[patch] = 1e-6


def moments():
    w = g.Gam.copy()
    tot = w.sum()
    zc = (w * (np.arange(N)[None, None, :] * dx)).sum() / tot
    xc = (w * (np.arange(N)[None, :, None] * dx)).sum() / tot
    sz = np.sqrt((w * (np.arange(N)[None, None, :] * dx - zc) ** 2).sum() / tot)
    sx = np.sqrt((w * (np.arange(N)[None, :, None] * dx - xc) ** 2).sum() / tot)
    return float(sz), float(sx)


sz0, sx0 = moments()
for _ in range(40):
    # ★ 记账：初版取 D_s=1e-20 ⇒ D_s·t = 8e-31 m² 比斑块宽度²(1.6e-17) 小 14 个数量级
    #   ⇒ 40 步内物理上不可能有可见变化（测试参数错 ✗，不是代码错）。取 D_s=1e-8 使其可见。
    g.update_Gamma(2e-11, tau_ex=1e30, D_s=1e-8)   # 关交换，只留面扩散
sz1, sx1 = moments()
print('---- A3 重做：面扩散的切向性 ----')
print('   法向宽度 %.3e → %.3e m（比值 %.3f，应 ≈1）' % (sz0, sz1, sz1 / sz0))
print('   切向宽度 %.3e → %.3e m（比值 %.3f，应 >1）' % (sx0, sx1, sx1 / sx0))
ok = abs(sz1 / sz0 - 1) < 0.15 and sx1 / sx0 > 1.05
print('   判定: %s' % ('PASS' if ok else 'FAIL'))
