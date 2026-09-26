#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fig_mob.py --- 组织可视化：三正交中面剖面 + 3D 点云 + 取向分布。

用法：python3 fig_mob.py results_boxB_mob_hi200_final.npz [out.png]
颜色：12 个高区分度暗色（变体）；母相 = 纯白；图例带体积分数。
记账：切片上是**面积**不是体积分数（同一变体可是"大片薄片"）。
"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from scipy import ndimage as ndi

try:
    font_manager.fontManager.addfont('/mnt/c/Windows/Fonts/simhei.ttf')
    plt.rcParams['font.family'] = 'SimHei'
except Exception:
    pass
plt.rcParams['axes.unicode_minus'] = False

P = sys.argv[1] if len(sys.argv) > 1 else 'results_boxB_mob_hi200_final.npz'
OUT = sys.argv[2] if len(sys.argv) > 2 else P.replace('_final.npz', '') + '_FIG.png'
d = np.load(P)
reg = d['reg']; N = int(d['N']); dx = float(d['dx']); f = float(d['f'])
L = N * dx
nv = 12
cnt = np.bincount(reg.ravel(), minlength=nv + 1).astype(float)
frac = cnt / N ** 3

# 12 个高区分度暗色 + 母相纯白
COLS = ['#1f4e79', '#c00000', '#2e7d32', '#7b3f00', '#4a148c', '#00695c',
        '#b8860b', '#8b008b', '#37474f', '#0d47a1', '#bf360c', '#33691e']
cmap = ListedColormap(['#ffffff'] + COLS)
fig = plt.figure(figsize=(18, 11))
fig.suptitle('组织三维切片（%s）  N=%d  dx=%.3f um  L=%.1f um  f=%.4f'
             % (P.split('/')[-1], N, dx * 1e6, L * 1e6, f), fontsize=13)

for i, (ax_i, name) in enumerate([(0, 'yz (x=中)'), (1, 'xz (y=中)'), (2, 'xy (z=中)')]):
    sl = [slice(None)] * 3
    sl[ax_i] = N // 2
    sub = reg[tuple(sl)]
    ax = fig.add_subplot(2, 3, i + 1)
    ax.imshow(sub.T, origin='lower', cmap=cmap, vmin=0, vmax=12,
              extent=[0, L * 1e6, 0, L * 1e6], interpolation='nearest')
    ax.set_title('%s 面' % name, fontsize=11)
    ax.set_xlabel('um'); ax.set_ylabel('um')

# 3D 点云
ax3 = fig.add_subplot(2, 3, 4, projection='3d')
rng = np.random.default_rng(0)
for v in range(1, nv + 1):
    idx = np.argwhere(reg == v)
    if len(idx) == 0:
        continue
    if len(idx) > 4000:
        idx = idx[rng.choice(len(idx), 4000, replace=False)]
    ax3.scatter(idx[:, 0] * dx * 1e6, idx[:, 1] * dx * 1e6, idx[:, 2] * dx * 1e6,
                s=1.2, c=COLS[v - 1], alpha=0.35, linewidths=0)
ax3.set_xlabel('x um'); ax3.set_ylabel('y um'); ax3.set_zlabel('z um')
ax3.set_title('3D 变体分布（半透明点云）', fontsize=11)

# 图例（带体积分数）
axl = fig.add_subplot(2, 3, 5); axl.axis('off')
lines = ['母相 %.4f' % frac[0]]
for v in range(1, nv + 1):
    if frac[v] > 0:
        lines.append('V%-2d  %.4f' % (v, frac[v]))
axl.text(0.02, 0.98, '\n'.join(lines), va='top', fontsize=10, family='monospace')
axl.set_title('体积分数（占全盒）', fontsize=11)

# 取向分布：|n.npref|
npref = d['npref'] if 'npref' in d.files else None
axh = fig.add_subplot(2, 3, 6)
if npref is not None:
    par = ndi.binary_dilation(reg == 0, iterations=2)
    allc = []
    for v in range(1, nv + 1):
        if cnt[v] < 200:
            continue
        chi = ndi.gaussian_filter((reg == v).astype(float), 1.5)
        gr = np.array(np.gradient(chi, dx))
        bnd = (chi > 0.2) & (chi < 0.8) & par
        nn = np.moveaxis(gr, 0, -1)[bnd]
        nrm = np.linalg.norm(nn, axis=1)
        nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
        if nn.shape[0]:
            allc.append(np.abs(nn @ npref[v - 1]))
    if allc:
        C = np.concatenate(allc)
        axh.hist(C, bins=40, range=(0, 1), color='#1f4e79', alpha=0.85)
        axh.axvline(0.8, color='r', ls='--', label='宽面阈值 0.8')
        axh.set_xlabel('|n . n_pref|  （界面法向与惯习面法向的夹角余弦）')
        axh.set_ylabel('界面点数')
        axh.set_title('宽面占比 = %.3f（随机 0.200）' % float((C > 0.8).mean()), fontsize=11)
        axh.legend(fontsize=9)
plt.tight_layout()
plt.savefig(OUT, dpi=110)
print('saved', OUT)
