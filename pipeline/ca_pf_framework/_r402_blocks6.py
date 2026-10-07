#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r402_blocks6.py —— 6 个块**逐个**特写：块内两根板条怎么堆叠。

## 做法
对每个变体 `v`（含两根板条 `k1,k2`）：
1. 取 `(reg==k1)|(reg==k2)` 的联合掩模；
2. 在**盒坐标**下取最小跨度的那个轴做**最大投影**（"脚印"视图）
   ⇒ 两根板条会**并排**显示出来（堆叠面正对镜头）；
3. 两根板条用**同色相、不同明度**画出。

输出：`_viz/<arm>_blocks6.png`（2×3 面板）。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
sys.path.insert(0, HERE)
from _r400_viz import load, palette, draw_slice   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', default='saSet2P0')
    ap.add_argument('--step', type=int, default=-1)
    ap.add_argument('--outdir', default=os.path.join(HERE, '_viz'))
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    d = os.path.join(MB, 'dry_' + a.arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    if a.step >= 0:
        fs = [f for f in fs
              if int(re.search(r'_(\d+)\.npz$', f).group(1)) == a.step] or fs
    f = fs[-1]
    reg, var, N, st = load(f)
    pal = palette(var, int(reg.max()))
    vs = sorted(set(var.values()))
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.6))
    for ax, v in zip(axes.ravel(), vs):
        ks = sorted(k for k in var if var[k] == v)
        m = np.isin(reg, ks)
        if not m.any():
            ax.set_axis_off(); continue
        ii = np.argwhere(m)
        lo, hi = ii.min(0), ii.max(0)
        ext = hi - lo + 1
        proj_ax = int(np.argmin(ext))            # 沿**最薄**的盒轴投影
        sub = reg[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1]
        # ⚠ `np.rollaxis` 只**移动**轴、不改变剩余轴的顺序 ⇒ 与 `sub.shape[1:]` 对不上
        #   （第一版就栽在这：形状 (37,42) vs (42,25)）。用 `moveaxis` + 由它取形状。
        sm = np.moveaxis(sub, proj_ax, 0)
        foot = np.zeros(sm.shape[1:], np.int64)
        for slab in sm:
            upd = (slab > 0) & (foot == 0)       # 先到先得 ⇒ 两场都保得住
            foot[upd] = slab[upd]
        ks_other = [i for i in range(3) if i != proj_ax]
        n1, n2 = int(ext[ks_other[0]]), int(ext[ks_other[1]])
        ax.imshow(foot + 1, origin='lower', interpolation='nearest',
                  cmap=_cmap(pal), vmin=0, vmax=int(reg.max()) + 1)
        ax.set_title('V%d : laths %s   footprint %d x %d cells (%.2f x %.2f um)'
                     % (v, ks, n1, n2, n1 * 0.0625, n2 * 0.0625), fontsize=9)
        ax.set_xlabel('cell', fontsize=8); ax.set_ylabel('cell', fontsize=8)
        ax.tick_params(labelsize=7)
    hs = [plt.Line2D([], [], marker='s', ls='', ms=10, color=pal[k],
                     label='field %d' % k) for k in sorted(pal)]
    fig.legend(handles=hs, loc='lower center', ncol=6, fontsize=9, frameon=False)
    fig.suptitle('%s  step %d   each block seen face-on: the two laths of one '
                 'variant (same hue, 2nd darker)' % (a.arm, st), fontsize=12)
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])
    p = os.path.join(a.outdir, '%s_blocks6.png' % a.arm)
    fig.savefig(p, dpi=130); plt.close(fig)
    print('写出 %s' % p)


def _cmap(pal):
    from matplotlib.colors import ListedColormap
    n = max(pal) + 2
    c = np.zeros((n, 4))
    c[0] = [0.93, 0.93, 0.96, 1]
    for k, col in pal.items():
        c[k + 1] = col
    return ListedColormap(c)


if __name__ == '__main__':
    sys.exit(main())
