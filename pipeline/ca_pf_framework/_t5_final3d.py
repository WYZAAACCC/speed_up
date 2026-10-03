#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_final3d.py --- ★★★★★ `t5N276` **终态**三维图：区分**块（变体）**与**板条（场）**

## 用户要求
> "将 t5N276 最后的三维图像画出来，使用不同颜色区分**块**与**马氏体板条**"

## 画什么（2×2）
* **左列 = 按【板条（场号）】着色** —— 每个场一个颜色 ⇒ 看**一根根板条**;
* **右列 = 按【块（变体）】着色** —— 同变体一个色系 ⇒ 看**块**;
* **上排 = 等轴视角** · **下排 = 俯视**（沿 z）。
**★ 标记用小尺寸（s=1.0）** —— 上一版用 s=4.0 会把碎片**视觉上糊成一片**（用户已指出）。

## 事实（终态 step 2160，来自快照与块表）
* 活跃场 **20 个**：变体 1 占 **18 个**（[1..18]）、变体 5 占 **2 个**（[93, 94]）
* 块表 `blk_laths = "16/1/1/1/1"` ⇒ **5 个块**（16+1+1+1+1 根）
* `nslab_n = 19` · `nf3_col = 16`（低角晶界）
"""
import glob
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
OUT = '_w2_t5_final3d_%s.png' % TAG
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
ST = int(P.split('snap_')[1].replace('.npz', ''))
DX = 62.5
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    vmap = {}
    for k, v in zip(np.asarray(z['vmap_keys']).ravel(),
                    np.asarray(z['vmap_vals']).ravel()):
        vmap[int(k)] = int(v)

live = sorted(int(x) for x in np.unique(reg) if x != 0)
byv = {}
for k in live:
    byv.setdefault(vmap.get(k, -1), []).append(k)
print('  终态 step %d：活跃场 %d 个；变体分布 %s'
      % (ST, len(live), {v: len(ks) for v, ks in byv.items()}))

# ── 配色 ──
# 按【场】: 用 tab20（20 色）
cmap_f = plt.get_cmap('tab20')
field_color = {k: cmap_f(i % 20) for i, k in enumerate(live)}
# 按【变体/块】: 变体1 = 蓝色系, 变体5 = 红色系, 其余 = 绿色系
vcolors = {1: (0.10, 0.35, 0.85), 5: (0.85, 0.15, 0.15)}
def vcolor(v):
    return vcolors.get(v, (0.15, 0.65, 0.25))

fig = plt.figure(figsize=(17, 15))
VIEWS = (('isometric', 22, 35), ('top view (along z)', 62, -90))
for row, (by_field, title_left) in enumerate(((True, 'colored by LATH (field id)'),
                                              (False, 'colored by BLOCK (variant)'))):
    for col, (vname, elev, azim) in enumerate(VIEWS):
        ax = fig.add_subplot(2, 2, row * 2 + col + 1, projection='3d')
        for k in live:
            idx = np.argwhere(reg == k)
            if idx.size == 0:
                continue
            c = field_color[k] if by_field else vcolor(vmap.get(k, -1))
            ax.scatter(idx[:, 0] * DX / 1000, idx[:, 1] * DX / 1000, idx[:, 2] * DX / 1000,
                       s=1.0, c=[c], depthshade=False, linewidths=0)
        ax.set_xlim(0, 5); ax.set_ylim(0, 5); ax.set_zlim(0, 5)
        ax.set_xlabel('x (um)', fontsize=9)
        ax.set_ylabel('y (um)', fontsize=9)
        ax.set_zlabel('z (um)', fontsize=9)
        ax.set_title('step %d | %s | %s' % (ST, title_left, vname), fontsize=11)
        ax.view_init(elev=elev, azim=azim)
        ax.tick_params(labelsize=7)
        if row == 0 and col == 0:
            h = [mpatches.Patch(color=field_color[k], label='field %d (v%d)' % (k, vmap.get(k, -1)))
                 for k in live[:20]]
            ax.legend(handles=h, loc='upper left', fontsize=6, ncol=2, framealpha=0.85)
        if row == 1 and col == 0:
            h = [mpatches.Patch(color=vcolor(v), label='variant %d  (%d fields)' % (v, len(byv[v])))
                 for v in sorted(byv)]
            ax.legend(handles=h, loc='upper left', fontsize=8, framealpha=0.85)

plt.suptitle('%s FINAL state (step %d):  LEFT = per-LATH colors (field id) | '
             'RIGHT = per-BLOCK colors (variant)    |  box 5x5x5 um, marker s=1.0'
             % (TAG, ST), fontsize=13)
plt.tight_layout()
plt.savefig(OUT, dpi=115, bbox_inches='tight')
print('  已写 %s' % OUT)
