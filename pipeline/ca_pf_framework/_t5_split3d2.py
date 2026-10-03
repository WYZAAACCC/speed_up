#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_split3d2.py --- 场从"一根"到"多根"的三维对比（**英文标签版**，清晰标注）

## 为什么重画
上一版标题里的**中文因 matplotlib 缺 CJK 字体显示成方块** ⇒ 改**纯英文**（保证可读），
并把版面放大、图例与每块的大小都标清楚。

## 画什么（2 行 × 3 列，共 6 个时刻）
`t5N276F` 的**场 2**（物理相 = `band` 的 φ<0），**按 26-连通分量着色**：
* **蓝 = 最大分量（主板）**; **其余颜色 = 卫星块**;
* 每幅标题给出：step / 块数 / 总胞 / 最大块占比;
* 图例列出**每一块**的胞数（前 8 块）。
"""
import glob
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import ndimage

DX = 62.5
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
K = int(sys.argv[2]) if len(sys.argv) > 2 else 2
STEPS = [int(x) for x in (sys.argv[3].split(',') if len(sys.argv) > 3
                          else '40,120,160,400,1000,1720'.split(','))]
OUT = '_w2_t5_split3d_%s_f%d_en.png' % (TAG, K)
S26 = ndimage.generate_binary_structure(3, 3)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))


def mask(st):
    fs = [f for f in snaps if ('%05d' % st) in f]
    if not fs:
        return None, None
    with np.load(fs[0], allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
    sel = (bf == K) & (bv < 0)
    if not sel.any():
        return N, None
    idx = bi[sel]
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    return N, g


fig = plt.figure(figsize=(20, 13))
for i, st in enumerate(STEPS):
    N, g = mask(st)
    ax = fig.add_subplot(2, 3, i + 1, projection='3d')
    if g is None:
        ax.set_title('step %d : field absent' % st, fontsize=13); continue
    lab, nc = ndimage.label(g, structure=S26)
    sz = np.bincount(lab.ravel())[1:]
    order = list(np.argsort(-sz) + 1)
    for rank, ci in enumerate(order):
        idx = np.argwhere(lab == ci)
        if idx.shape[0] < 20:
            continue
        col = 'tab:blue' if rank == 0 else plt.get_cmap('autumn')(min((rank - 1) / 8.0, 1.0))
        ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                   s=2.2, c=[col], depthshade=False, linewidths=0,
                   label=('%s %d : %d cells' % ('MAIN' if rank == 0 else 'sat', rank + 1,
                                                int(sz[ci - 1]))) if rank < 7 else None)
    L = N * DX / 1000
    ax.set_xlim(0, L); ax.set_ylim(0, L); ax.set_zlim(0, L)
    ax.set_xlabel('x (um)', fontsize=9); ax.set_ylabel('y (um)', fontsize=9)
    ax.set_zlabel('z (um)', fontsize=9)
    ax.set_title('step %d   |   pieces = %d   |   cells = %d   |   main = %.0f%%'
                 % (st, nc, int(g.sum()), 100.0 * sz.max() / max(sz.sum(), 1)),
                 fontsize=13, fontweight='bold')
    ax.view_init(elev=18, azim=38)
    ax.tick_params(labelsize=8)
    ax.legend(loc='upper left', fontsize=8, markerscale=4, framealpha=0.9)
plt.suptitle('%s   FIELD %d   physical phase (band phi<0)   colored by CONNECTED COMPONENT   '
             'box %.1f x %.1f x %.1f um\n'
             'BLUE = main piece     ORANGE/YELLOW = satellite pieces'
             % (TAG, K, N * DX / 1000, N * DX / 1000, N * DX / 1000), fontsize=15)
plt.tight_layout()
plt.savefig(OUT, dpi=125, bbox_inches='tight')
print('  已写 %s' % OUT)
