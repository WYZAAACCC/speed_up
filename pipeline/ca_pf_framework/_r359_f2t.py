#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r359_f2t.py —— F2（异变体）面数随时间的曲线 ⇒ 为"变体置换"实验选**最短可用步数**。

只读归档 `region`/`vmap`，不用解弹性。判据：
* 找出 F2 首次 > 0 的步、以及达到末态 F2 的某个比例（如 50%/80%）的步
  ⇒ 用它当置换实验的步数下限（省机时）。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def main():
    arm = sys.argv[1] if len(sys.argv) > 1 else 'saSet2'
    d = os.path.join(MB, 'dry_' + arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    if not fs:
        print('  ⚠ 无快照'); return 2
    print('=' * 84)
    print('_r359 —— %s 的 F1/F2/F3 随步数（只读 region）' % arm)
    print('=' * 84)
    print('  %-6s %9s %9s %9s %10s' % ('step', 'F1', 'F2', 'F3', 'f 转变率'))
    rows = []
    for f in fs:
        z = np.load(f, allow_pickle=True)
        reg = np.asarray(z['region'], np.int64)
        vk = np.asarray(z['vmap_keys'], np.int64)
        vv = np.asarray(z['vmap_vals'], np.int64)
        var = np.full(int(vk.max()) + 1, -1, np.int64)
        var[vk] = vv
        n1 = n2 = n3 = 0
        for ax in range(3):
            b = np.roll(reg, -1, axis=ax)
            sel = reg != b
            if not sel.any():
                continue
            I = np.where(sel)
            va = var[np.clip(reg[I], 0, var.size - 1)]
            vb = var[np.clip(b[I], 0, var.size - 1)]
            both = (va > 0) & (vb > 0)
            n1 += int((~both).sum())
            n2 += int((both & (va != vb)).sum())
            n3 += int((both & (va == vb)).sum())
        ftr = 1.0 - float((reg == 0).sum()) / reg.size
        print('  %-6s %9d %9d %9d %9.4f' % (z['step'], n1, n2, n3, ftr))
        rows.append((int(z['step']), n1, n2, n3))
    a = np.array([[r[0], r[2]] for r in rows], float)
    nz = a[a[:, 1] > 0]
    print()
    if nz.size:
        print('  **F2 首次 > 0 的步 = %d**' % int(nz[0, 0]))
        fin = float(nz[-1, 1])
        for frac in (0.25, 0.5, 0.8):
            tgt = frac * fin
            hit = nz[nz[:, 1] >= tgt]
            if hit.size:
                print('  F2 达到末态 %.0f%%（%.0f 面）的步 = **%d**'
                      % (100 * frac, tgt, int(hit[0, 0])))
    else:
        print('  ⚠ 全程 F2 = 0')
    return 0


if __name__ == '__main__':
    sys.exit(main())
