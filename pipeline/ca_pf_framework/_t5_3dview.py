#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_3dview.py --- ★★★★★ 三维可视化：新场（≥10）与老场（2–9）的**空间关系**

## 目的（用户要求）
> "将当前实验的三维变化图像画出来，标出来哪些是新场，我看一下到底是怎么回事"

## 画什么
**四联图**（同一盒子 5×5×5 µm，从两个视角 × 两个时刻）：
* **上排 = step 200**（新场**尚未**出现；只有老场 2–9）；
* **下排 = step 760**（新场 10–17、93 **已出现**）；
* **左列 = 视角 1（等轴）** · **右列 = 视角 2（沿 n* 方向看，即"厚度方向"）**；
* **配色**：老场（2–9）= 蓝绿系；**新场（≥10）= 红/橙系**；种子（场 1）= 灰。
**⇒ 这样能一眼看出：新场是"贴在老场中间"还是"独立成条"。**

## 同时标注每场的**连通段数**（上一轮发现：新场是散碎片段）
"""
import glob
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import ndimage

DX = 62.5            # nm
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
OUT = '_w2_t5_3dview_%s.png' % TAG

snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not snaps:
    print('  无快照'); sys.exit(1)


def load(step):
    for P in snaps:
        if int(P.split('snap_')[1].replace('.npz', '')) == step:
            with np.load(P, allow_pickle=False) as z:
                return np.asarray(z['region']).astype(np.int32), \
                       (np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None)
    return None, None


def comps(reg, k):
    m = (reg == k)
    if not m.any():
        return 0
    _, n = ndimage.label(m, structure=ndimage.generate_binary_structure(3, 1))
    return n


# 选两个时刻：新场出现前 / 后
avail = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]
t_early = min([s for s in avail if s >= 200], default=avail[0])
t_late = avail[-1]
print('  早 = step %d ｜ 晚 = step %d' % (t_early, t_late))

fig = plt.figure(figsize=(15, 13))
for row, t in enumerate((t_early, t_late)):
    reg, nh = load(t)
    if reg is None:
        continue
    ks = sorted(int(x) for x in np.unique(reg) if x != 0)
    old = [k for k in ks if 2 <= k <= 9]
    new = [k for k in ks if k >= 10]
    print('  step %d: 老场 %s ; **新场 %s**' % (t, old, new))

    for col, view in enumerate(('iso', 'along_n')):
        ax = fig.add_subplot(2, 2, row * 2 + col + 1, projection='3d')
        # 老场：蓝绿渐变
        for i, k in enumerate(old):
            idx = np.argwhere(reg == k)
            if idx.size == 0:
                continue
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=1.2, c=[plt.cm.winter(i / max(len(old) - 1, 1))],
                       label=('老场 %d' % k) if (row == 0 and col == 0) else None,
                       depthshade=False)
        # 新场：红橙渐变（**加粗放大**以便辨认）
        for i, k in enumerate(new):
            idx = np.argwhere(reg == k)
            if idx.size == 0:
                continue
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=4.0, c=[plt.cm.autumn(i / max(len(new) - 1, 1))],
                       label=('★新场 %d' % k) if (row == 1 and col == 0) else None,
                       depthshade=False)
        # 种子
        idx = np.argwhere(reg == 1)
        if idx.size:
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=3.0, c='0.6', marker='s', depthshade=False)
        ax.set_xlim(0, 5); ax.set_ylim(0, 5); ax.set_zlim(0, 5)
        ax.set_xlabel('x (µm)'); ax.set_ylabel('y (µm)'); ax.set_zlabel('z (µm)')
        ax.set_title('step %d ｜ %s ｜ 老场 %d 个 · **新场 %d 个**'
                     % (t, '等轴视角' if view == 'iso' else '沿 n* 看', len(old), len(new)),
                     fontsize=10)
        if view == 'iso':
            ax.view_init(elev=22, azim=35)
        else:
            ax.view_init(elev=8, azim=0)
        if col == 0:
            ax.legend(loc='upper left', fontsize=7, markerscale=3)

plt.suptitle('%s：三维形貌（**新场 ≥10 用红橙色标出**）｜盒 5×5×5 µm ｜ 老场=场2–9，种子=场1（灰）'
             % TAG, fontsize=13)
plt.tight_layout()
plt.savefig(OUT, dpi=115, bbox_inches='tight')
print('  已写 %s' % OUT)

# 文字补充：连通段数
print()
print('  ── 各场连通段数（散碎程度的直接指标）──')
reg, _ = load(t_late)
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    n = comps(reg, k)
    tag = '★新场' if k >= 10 else ('老场' if k >= 2 else '种子')
    print('     %-6s 场 %-4d 连通段数 = %d' % (tag, k, n))
