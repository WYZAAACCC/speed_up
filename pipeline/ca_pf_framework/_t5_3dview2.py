#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_3dview2.py --- 三维形貌图（**英文标签** —— 上一版中文因字体缺失显示成方块）

## 画什么
**2×2 图**：上排 = step 200（**新场出现前**）；下排 = step 800（**新场出现后**）
* 左列 = 等轴视角；右列 = 沿 z 看（俯视）
* **老场（field 2–9）= 蓝绿系** · **新场（field ≥10）= 红橙黄** · 种子 = 灰
**⇒ 文件名带 _en 后缀，避免与上一版混淆。**
"""
import glob
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DX = 62.5
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
OUT = '_w2_t5_3dview_%s_en.png' % TAG
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
avail = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]


def load(step):
    for P in snaps:
        if int(P.split('snap_')[1].replace('.npz', '')) == step:
            with np.load(P, allow_pickle=False) as z:
                return np.asarray(z['region']).astype(np.int32)
    return None


t_early = min([s for s in avail if s >= 200], default=avail[0])
t_late = avail[-1]
fig = plt.figure(figsize=(16, 14))
for row, t in enumerate((t_early, t_late)):
    reg = load(t)
    if reg is None:
        continue
    ks = sorted(int(x) for x in np.unique(reg) if x != 0)
    old = [k for k in ks if 2 <= k <= 9]
    new = [k for k in ks if k >= 10]
    for col, view in enumerate(('iso', 'top')):
        ax = fig.add_subplot(2, 2, row * 2 + col + 1, projection='3d')
        for i, k in enumerate(old):
            idx = np.argwhere(reg == k)
            if idx.size == 0:
                continue
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=1.2, c=[plt.cm.winter(i / max(len(old) - 1, 1))],
                       label=('old f%d' % k) if (row == 0 and col == 0) else None, depthshade=False)
        for i, k in enumerate(new):
            idx = np.argwhere(reg == k)
            if idx.size == 0:
                continue
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=4.0, c=[plt.cm.autumn(i / max(len(new) - 1, 1))],
                       label=('NEW f%d' % k) if (row == 1 and col == 0) else None, depthshade=False)
        idx = np.argwhere(reg == 1)
        if idx.size:
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=3.0, c='0.6', marker='s', depthshade=False,
                       label=('seed f1' if (row == 0 and col == 0) else None))
        ax.set_xlim(0, 5); ax.set_ylim(0, 5); ax.set_zlim(0, 5)
        ax.set_xlabel('x (um)'); ax.set_ylabel('y (um)'); ax.set_zlabel('z (um)')
        ax.set_title('step %d | %s | old fields: %d | NEW fields: %d'
                     % (t, 'isometric' if view == 'iso' else 'top view', len(old), len(new)),
                     fontsize=11)
        ax.view_init(elev=22 if view == 'iso' else 60, azim=35 if view == 'iso' else -90)
        if col == 0:
            ax.legend(loc='upper left', fontsize=7, markerscale=3)
plt.suptitle('%s : 3D morphology (NEW fields >=10 in red/orange/yellow; old fields 2-9 in blue/green; '
             'seed f1 in gray)  |  box 5x5x5 um' % TAG, fontsize=12)
plt.tight_layout()
plt.savefig(OUT, dpi=110, bbox_inches='tight')
print('  已写 %s' % OUT)
