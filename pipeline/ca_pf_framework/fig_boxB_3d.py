#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fig_boxB_3d.py --- 盒子 B 三维可视化（按变体半透明着色，只看盒内）。

用户要求：三维化、不同变体不同颜色**半透明**、只关注盒内组织、看得懂、精度高一点。
做法：(左) 三维散射只画**界面胞**（盒内变体是实心、不必画点阵）；
      (中/右) 两个正交中面切片按变体 ID 着色，看内部归属；
      每个变体固定颜色 + 图例；只画盒内（不画周期镜像）。
"""
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm
# ★ 中文：本机 WSL 没有 CJK 字体，直接挂 Windows 的 SimHei（否则标题全是方块）
for _f in ('/mnt/c/Windows/Fonts/simhei.ttf', '/mnt/c/Windows/Fonts/msyh.ttc'):
    try:
        _fm.fontManager.addfont(_f)
    except Exception:
        pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
from mpl_toolkits.mplot3d import Axes3D  # noqa

import windowB_surface as W

N = int(sys.argv[1]) if len(sys.argv) > 1 else 80
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 25
DX = 0.25e-6
out = W.M2_twelve_variants(N=N, nstep=NS, dx=DX, df=1e8, quiet=True)
g = out['g']
reg = g.region()
L = N * DX
np.savez_compressed('results_boxB_N%03d_reg.npz' % N, reg=reg, N=N, dx=DX,
                    f=out['f_trans'], v_abs=out['v_abs'], Sv=out['S_v_geom'])
print('f=%.4f  band=%d  Sv=%.3e' % (out['f_trans'], out['band'], out['S_v_geom']))

cmap = plt.get_cmap('tab20')
cols = [cmap(i % 20) for i in range(1, 13)]
band = g.surface_band()
rng3 = np.random.default_rng(0)
idx_all = np.argwhere(reg != 0)                     # 变体**实心**区（半透明显示）
if idx_all.shape[0] > 26000:
    idx_all = idx_all[rng3.choice(idx_all.shape[0], 26000, replace=False)]
idx_if = np.argwhere(band & (reg != 0))             # 界面再加亮一层
if idx_if.shape[0] > 14000:
    idx_if = idx_if[rng3.choice(idx_if.shape[0], 14000, replace=False)]
pts = (idx_all + 0.5) * DX * 1e6
k = reg[tuple(idx_all.T)]
pts_i = (idx_if + 0.5) * DX * 1e6
k_i = reg[tuple(idx_if.T)]

fig = plt.figure(figsize=(15.5, 5.4))
ax = fig.add_subplot(131, projection='3d')
for v in range(1, 13):
    m = (k == v)
    if not m.any():
        continue
    ax.scatter(pts[m, 0], pts[m, 1], pts[m, 2], s=1.0, c=[cols[v - 1]],
               alpha=0.14, linewidths=0, label='V%d' % v)
    mi = (k_i == v)
    if mi.any():
        ax.scatter(pts_i[mi, 0], pts_i[mi, 1], pts_i[mi, 2], s=1.6,
                   c=[cols[v - 1]], alpha=0.55, linewidths=0)
ax.set_xlabel('x (um)'); ax.set_ylabel('y (um)'); ax.set_zlabel('z (um)')
ax.set_title('盒子 B 界面胞（按变体半透明着色）\nN=%d  L=%.0f um  dx=0.25 um  f=%.3f'
             % (N, L * 1e6, out['f_trans']), fontsize=9)
ax.legend(fontsize=5, ncol=2, loc='upper left', framealpha=0.6, markerscale=6)
ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=22, azim=35)

for j in (0, 1):
    axn = fig.add_subplot(132 + j)
    sl = reg[:, :, N // 2] if j == 0 else reg[N // 2, :, :]
    img = np.zeros(sl.shape + (3,))
    img[:] = np.array([0.94, 0.94, 0.94])
    for v in range(1, 13):
        img[sl == v] = cols[v - 1][:3]
    axn.imshow(np.transpose(img, (1, 0, 2)), origin='lower',
               extent=[0, L * 1e6, 0, L * 1e6])
    axn.set_title('z 中面切片（按变体着色）' if j == 0 else 'x 中面切片（按变体着色）',
                  fontsize=9)
    axn.set_xlabel('um'); axn.set_ylabel('um')
plt.tight_layout()
plt.savefig('FIG_boxB_3d_N%03d.png' % N, dpi=170)
print('saved FIG_boxB_3d_N%03d.png' % N)
