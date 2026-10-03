#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_split3d.py --- ★★★★★ 一个场从"一根"到"多根"的三维对比图

## 画什么
取 `t5N276F` 的**场 2**（step 120 = **1 块** → step 1720 = **22 块**），
在 **6 个时刻**画它的**物理相**（`band` 的 φ<0），**按 26-连通分量着色**
⇒ **每一块一个颜色** ⇒ 一眼能看出"什么时候、从哪里裂开的"。

## 量具（**已自洽校验**）
`band_val` = 符号距离 φ（有正有负）；`band_fld` = 场号。
φ<0 的胞 = 该场的**物理相**。合计与 `series.csv` 的 `Vt` 差 **1%** ✓
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
                          else '40,120,160,240,400,1720'.split(','))]
OUT = '_w2_t5_split3d_%s_f%d.png' % (TAG, K)
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


fig = plt.figure(figsize=(17, 12))
cmap = plt.get_cmap('tab20')
for i, st in enumerate(STEPS):
    N, g = mask(st)
    if g is None:
        ax = fig.add_subplot(2, 3, i + 1, projection='3d')
        ax.set_title('step %d: (无该场)' % st, fontsize=10); continue
    lab, nc = ndimage.label(g, structure=S26)
    sz = np.bincount(lab.ravel())[1:]
    order = np.argsort(-sz) + 1
    ax = fig.add_subplot(2, 3, i + 1, projection='3d')
    for rank, ci in enumerate(order):
        idx = np.argwhere(lab == ci)
        if idx.shape[0] < 20:
            continue
        ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                   s=1.2, c=[cmap(rank % 20)], depthshade=False, linewidths=0,
                   label=('块 %d (%d 胞)' % (rank + 1, int(sz[ci - 1]))) if rank < 6 else None)
    ax.set_xlim(0, N * DX / 1000); ax.set_ylim(0, N * DX / 1000); ax.set_zlim(0, N * DX / 1000)
    ax.set_xlabel('x (um)', fontsize=8); ax.set_ylabel('y (um)', fontsize=8)
    ax.set_zlabel('z (um)', fontsize=8)
    ax.set_title('step %d ｜ **%d 块** ｜ 共 %d 胞 ｜ 最大块占 %.0f%%'
                 % (st, nc, int(g.sum()), 100.0 * sz.max() / max(sz.sum(), 1)), fontsize=10)
    ax.view_init(elev=20, azim=35)
    ax.tick_params(labelsize=6)
    if i == 0:
        ax.legend(loc='upper left', fontsize=6, markerscale=3)
plt.suptitle('%s : field %d  (physical phase = band phi<0)  |  colored by CONNECTED COMPONENT '
             '| box %.1f um' % (TAG, K, N * DX / 1000), fontsize=13)
plt.tight_layout()
plt.savefig(OUT, dpi=115, bbox_inches='tight')
print('  已写 %s' % OUT)
