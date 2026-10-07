#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r404_cmp.py —— `--facet-proj 0` vs `10` 的**早期块结构对比**（同一时刻、同一窗口）。

## 为什么这张图重要
`§185` 实测：`--facet-proj 10` 下块结构在**头 20 步被打散**
（`blk_nprof` 6 块 → 10 块，`nf3` 1169 → 2），而 `--facet-proj 0` 下全程稳定。
**本图把这个差异直接画出来。**
"""
from __future__ import annotations

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
from _r400_viz import load, palette, draw_slice, oblique, window, U1, U2   # noqa: E402

STEPS = [0, 20, 60, 200, 400]


def snap_at(tag, step):
    d = os.path.join(MB, 'dry_' + tag)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    for f in fs:
        if int(re.search(r'_(\d+)\.npz$', f).group(1)) == step:
            return f
    return None


def main():
    arms = ['saSet2P0', 'saSet2']
    half = 110
    grid = np.arange(-half, half)
    regL, var, N, _ = load(snap_at(arms[0], 400))
    pal = palette(var, int(regL.max()))
    wfix = window(regL, U1, U2, margin=14)
    org = np.array([N / 2.0] * 3)
    fig, axes = plt.subplots(2, len(STEPS), figsize=(3.1 * len(STEPS), 7.2))
    for r, arm in enumerate(arms):
        for c, stp in enumerate(STEPS):
            f = snap_at(arm, stp)
            ax = axes[r, c]
            if f is None:
                ax.set_axis_off(); continue
            reg, _, _, st = load(f)
            sl = oblique(reg, org, U1, U2, half)
            i0 = max(np.searchsorted(grid, wfix[0]), 0)
            i1 = np.searchsorted(grid, wfix[1])
            j0 = max(np.searchsorted(grid, wfix[2]), 0)
            j1 = np.searchsorted(grid, wfix[3])
            draw_slice(ax, sl[i0:i1, j0:j1], pal,
                       ('--facet-proj 0' if r == 0 else '--facet-proj 10')
                       + '   step %d' % st)
    fig.suptitle('Block structure:  --facet-proj 0 (top, blocks intact)  vs  '
                 '--facet-proj 10 (bottom, blocks fragmented in the first '
                 '20 steps then re-formed)', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(HERE, '_viz', 'compare_proj0_vs_proj10.png')
    fig.savefig(p, dpi=130); plt.close(fig)
    print('写出 %s' % p)


if __name__ == '__main__':
    sys.exit(main())
