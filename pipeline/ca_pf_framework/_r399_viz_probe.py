#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r399_viz_probe.py —— 先探一下：块在哪、切哪个面最好看。

输出：各场的质心、包围盒；转变体积的整体质心；建议的切面位置。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
DX_NM = 62.5


def main():
    for tag in (sys.argv[1:] or ['saSet2', 'saSet2P0']):
        d = os.path.join(MB, 'dry_' + tag)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
        if not fs:
            print('%-12s ⚠ 无快照' % tag); continue
        z = np.load(fs[-1], allow_pickle=True)
        reg = np.asarray(z['region'], np.int64)
        N = int(z['N'])
        vk = np.asarray(z['vmap_keys'], np.int64)
        vv = np.asarray(z['vmap_vals'], np.int64)
        var = dict(zip(vk.tolist(), vv.tolist()))
        print('=' * 88)
        print('### %s  末快照 step=%s  N=%d  盒 %.2f µm' %
              (tag, z['step'], N, float(z['L']) * 1e6))
        occ = reg > 0
        idx = np.argwhere(occ).astype(float)
        c = idx.mean(0) if idx.size else np.array([N / 2] * 3)
        print('  转变体积质心（胞） = [%.1f %.1f %.1f] ⇒ 盒中心 [%.1f %.1f %.1f]'
              % (c[0], c[1], c[2], N / 2, N / 2, N / 2))
        print('  转变胞占比 = %.3f%%' % (100 * occ.mean()))
        print()
        print('  %-4s %-4s %-22s %-24s %s' %
              ('场', '变体', '质心(µm)', '包围盒跨度(µm)', '胞数'))
        for k in range(1, int(reg.max()) + 1):
            m = reg == k
            if not m.sum():
                continue
            ii = np.argwhere(m).astype(float)
            cc = ii.mean(0) * DX_NM * 1e-3
            sp = (ii.max(0) - ii.min(0) + 1) * DX_NM * 1e-3
            print('  %-4d %-4d %-22s %-24s %d'
                  % (k, var.get(k, -1),
                     '[%.2f %.2f %.2f]' % tuple(cc),
                     '%.2f×%.2f×%.2f' % tuple(sp), int(m.sum())))
        print()
        print('  ⇒ 建议切面（取转变体积质心所在的三个轴对齐面）：')
        print('     x = %d, y = %d, z = %d（胞索引）' % (int(c[0]), int(c[1]), int(c[2])))


if __name__ == '__main__':
    sys.exit(main())
