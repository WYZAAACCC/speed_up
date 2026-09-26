#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_expert.py --- 独立复核专家审核的 4 条可算项。"""
import numpy as np
import windowB_surface as W

print('=' * 70)
print('[复核 1] 专家称：E6 的 elong=6 种子长轴 1.8um > L/2=0.8um => 被截断')
print('=' * 70)
L, dx, N = 1.6e-6, 2e-8, 80
R = 0.1875 * L          # = 0.3 um  (rfrac=0.1875)
t = 10 * dx             # plate_dx=10 => 厚 0.2um
elong = 6.0
print('  理论: R=%.3f um, elong=%.1f => 长轴半径 = elong*R = %.3f um ; L/2 = %.3f um'
      % (R*1e6, elong, elong*R*1e6, L/2*1e6))
g = W.LevelSetMulti(N, L, nv=1, gamma=0.15, Mob=1e-9)
n1 = np.array([0.0, 0.0, 1.0]); a1 = np.array([1.0, 0.0, 0.0])
g.seed_plate(1, [L/2]*3, n1, R, t, elong=elong, along=a1)
m = g.phi[1] < 0
idx = np.argwhere(m)
p = idx.astype(float) * dx
c = p.mean(0); d = p - c
ext_a = (d @ a1).max() - (d @ a1).min()
ext_n = (d @ n1).max() - (d @ n1).min()
# 面内垂直方向
w1 = np.cross(n1, a1); w1 /= np.linalg.norm(w1)
ext_w = (d @ w1).max() - (d @ w1).min()
print('  实测初始: 沿 a=%.3f um, 沿 w=%.3f um, 沿 n=%.3f um  => 长/宽 = %.2f'
      % (ext_a*1e6, ext_w*1e6, ext_n*1e6, ext_a/max(ext_w,1e-30)))
print('  胞数 = %d ; 是否触到边界: x方向 %s, y方向 %s, z方向 %s'
      % (m.sum(),
         '是' if (m[0].any() or m[-1].any()) else '否',
         '是' if (m[:,0].any() or m[:,-1].any()) else '否',
         '是' if (m[:,:,0].any() or m[:,:,-1].any()) else '否'))
print('  => 专家说法 %s' % ('成立' if (elong*R > L/2) else '不成立'))

print()
print('=' * 70)
print('[复核 6] 专家称：椭圆种子不是严格 SDF => 初始 |grad phi| 偏离 1、曲率尖峰')
print('=' * 70)
gn = np.sqrt(sum(t2**2 for t2 in np.gradient(g.phi[1], dx)))
band = np.abs(g.phi[1]) <= 1.5 * dx
kap = g.curvature_of(1)
print('  界面带内 |grad phi|: median %.3f, p95 %.3f, max %.3f'
      % (np.median(gn[band]), np.percentile(gn[band], 95), gn[band].max()))
print('  界面带内 kappa: median %.3e, p95 %.3e  (1/um: median %.3f)'
      % (np.median(kap[band]), np.percentile(kap[band], 95),
         np.median(kap[band])*1e-6))
print('  => 理想 SDF 应给 median|grad phi|=1.0 ; 实测偏离 %s'
      % ('显著' if abs(np.median(gn[band])-1) > 0.1 else '轻微'))
