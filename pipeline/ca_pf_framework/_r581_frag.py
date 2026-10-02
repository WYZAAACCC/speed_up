#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_frag.py --- 探针：**场是不是碎的**？

## 为什么要问
`_r581_c6judge.py` 报告「场 1 的包围盒 = 1187 × 7447 × 1432 nm ⇒ 12.66 µm³」，
而 `series.csv` 的总 `Vt` 只有 **2.37 µm³** ⇒ **一个场的包围盒不可能比总体积还大**
⇒ 要么包围盒口径错，要么**这个场不是一根连通的板条**。

同一条线索：b5 的 `series.csv` 里 `runs` 列出现过 **18**（`runs=18/1/2/4`）
—— 「runs」数的是柱剖面里的**连续段个数**，18 段说明**高度碎片化**。

⇒ 本探针直接数每个场的**连通分量**，并逐分量量尺寸。
"""
import os
import sys

import numpy as np
from scipy import ndimage

R = '_exp/_bk_p2'


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
    d = os.path.join(R, 'dry_' + tag)
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')])
    z = np.load(os.path.join(d, snaps[-1]), allow_pickle=True)
    reg = z['region']
    N = int(z['N'])
    dx = float(z['L']) / N
    vox = dx ** 3
    print('=' * 92)
    print('%s : %s（step=%d）  N=%d  dx=%.1f nm' % (tag, snaps[-1], int(z['step']), N, dx * 1e9))
    print('=' * 92)
    pres = np.unique(reg[reg > 0])
    tot = int((reg > 0).sum())
    print('  总体积（数胞）= %d 胞 × %.4e µm³ = **%.5f µm³**' % (tot, vox * 1e18, tot * vox * 1e18))
    print()
    print('  %-5s %-7s %-9s %-11s %-10s %-10s %s'
          % ('场', '总胞数', '体积µm³', '分量数', '最大分量胞', '最大体积', '最大分量的包围盒 nm (厚/长/宽)'))
    for v in pres:
        m = (reg == v)
        lab, n = ndimage.label(m)          # 6-连通（默认结构）
        sizes = ndimage.sum(m, lab, range(1, n + 1)) if n else np.array([])
        big = int(np.argmax(sizes)) + 1 if n else 0
        bsz = int(sizes[big - 1]) if n else 0
        if big:
            idx = np.argwhere(lab == big)
            p = (idx.astype(float) + 0.5) * dx
            n_hab, a_ax, w_ax = z['n_hab'], z['a_ax'], z['w_ax']
            ext = []
            for ax in (n_hab, a_ax, w_ax):
                pr = p @ (np.asarray(ax, float) / (np.linalg.norm(ax) + 1e-300))
                ext.append(float(pr.max() - pr.min()) + dx)
            es = '%8.1f /%8.1f /%8.1f' % tuple(x * 1e9 for x in ext)
        else:
            es = '—'
        print('  %-5d %-7d %-9.5f %-11d %-12d %-10.5f %s'
              % (v, int(m.sum()), m.sum() * vox * 1e18, n, bsz, bsz * vox * 1e18, es))
    print()
    print('  ⇒ 判读：若"分量数"普遍 > 1，则 **`_r581_c6judge.py` 的按场包围盒是错的**')
    print('     （它量的是一个碎片云的包围盒，不是一根板条）⇒ 必须改成**按分量**量。')


if __name__ == '__main__':
    main()
