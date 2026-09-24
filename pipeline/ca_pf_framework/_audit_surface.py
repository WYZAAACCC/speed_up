#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计 windowB_surface.py 的三个关键离散化：
  A1 cell_area（异键数×dx²）对球的面积偏差      —— 面积测度是否可信
  A2 LevelSetSurface.area（带内 |∇φ| 积分）偏差  —— 同上
  A3 面扩散是否沿【法向】泄漏（本应只沿切向）    —— 表示层是否真的"面化"
"""
import numpy as np
from windowB_surface import LevelSetSurface, LevelSetMulti


def A1(N=64, dx=2e-9, R0=3e-8):
    g = LevelSetMulti(N, N * dx, nv=1)
    g.seed_sphere(1, [0.5 * N * dx] * 3, R0)
    g.init_parent()
    A_meas = float(g.cell_area().sum())
    A_th = 4 * np.pi * R0 ** 2
    print('  A1 cell_area 测度: Σ A_c = %.4e m² vs 4πR² = %.4e  ⇒ 偏差 %+.1f%%'
          % (A_meas, A_th, 100 * (A_meas / A_th - 1)))
    A_new = g.area_total_geom()
    print('  A1b P1 修正后的几何测度: %.4e m² ⇒ 偏差 %+.1f%%'
          % (A_new, 100 * (A_new / A_th - 1)))
    return A_meas / A_th


def A2(N=64, dx=2e-9, R0=3e-8):
    g = LevelSetSurface(N, N * dx, R0=R0)
    A_meas = g.area()
    A_th = 4 * np.pi * R0 ** 2
    print('  A2 LevelSetSurface.area: %.4e vs 4πR² = %.4e  ⇒ 偏差 %+.1f%%'
          % (A_meas, A_th, 100 * (A_meas / A_th - 1)))
    return A_meas / A_th


def A3(N=48, dx=2e-9, nstep=60):
    """平面界面 + 面扩散：Γ 若只沿切向扩散，则**法向剖面不应变宽**；
       若"面邻接"把法向也算进去，Γ 会沿法向糊开 ⇒ 用"法向二阶矩"是否增长来判定。"""
    g = LevelSetMulti(N, N * dx, nv=1)
    z = np.arange(N)[None, None, :] * dx
    g.phi[1] = np.where(z < 0.5 * N * dx, -1e-9, 1e-9) * np.ones((N, N, N))
    g.init_parent()
    m = g.surface_band()
    # 给面上一小块一个 Γ 峰（其余为 0），看扩散后法向剖面宽度
    g.Gam = np.zeros_like(g.phi[0])
    g.Gam[m] = 1e-6
    def norm_width():
        w = g.Gam.copy()
        tot = w.sum()
        if tot <= 0:
            return np.nan
        zc = (w * (np.arange(N)[None, None, :] * dx)).sum() / tot
        return float(np.sqrt((w * (np.arange(N)[None, None, :] * dx - zc) ** 2).sum() / tot))
    w0 = norm_width()
    for _ in range(nstep):
        g.update_Gamma(2e-11, tau_ex=1e30, D_s=1e-20)   # 关掉交换，只留面扩散
    w1 = norm_width()
    print('  A3 面扩散的法向宽度: 初始 %.3e m ⇒ %.3e m（比值 %.3f）'
          % (w0, w1, w1 / w0 if w0 else np.nan))
    print('     墙内界面带共 %d 层厚（应只有 1~2 层才说明"面"没被糊厚）' % _band_layers(g))
    return w1 / w0 if w0 else np.nan


def _band_layers(g):
    m = g.surface_band()
    # 沿 z 数平均层数（每列 True 的个数）
    return float(m.sum(axis=(0, 1)).mean())


if __name__ == '__main__':
    print('=' * 80)
    print('windowB_surface.py 离散化审计')
    print('=' * 80)
    A1(); A2(); A3()
