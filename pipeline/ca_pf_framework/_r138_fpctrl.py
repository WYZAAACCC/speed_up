#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r138_fpctrl.py —— **R115 保面对照判读**：6 块盒子里 `--facet-proj 0` vs `10`。

## 本脚本要回答（`§99` 的**第二例**，独立于 R75 的 2 块盒子）

`§99` 在 **R75 的 2 块盒子**上用**严格单变量**（同一次 `_r75_mb.sh` 的两条臂）证明：
**`--facet-proj 10` 在第一次投影（step 20）把 `f3_area` 从 4.108 抹到恰好 0.000000**，
而 `--facet-proj 0` 的对照臂**逐位不变**（4.108111），~100 步后恢复。

`R115` 是**同一个问题的第二个盒子**（**6 块** / N=112 / L=600 / W=350 / T=510）：
`saOdd`（proj=10，已在 `_r110` 跑过前 40 步）vs `saOddFp0`（proj=0，本臂）。

⇒ 报两者的 `cov` / `f3_area` 逐快照，看**是不是同样的现象**。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = [('dry_saOddFp0', '**6 块** / proj=**0**（本臂）'),
        ('dry_saOdd', '**6 块** / proj=**10**（`_r110` 的前 40 步）')]


def step_of(p):
    return int(re.search(r'snap_(\d+)\.npz$', p).group(1))


def main():
    print('=' * 108)
    print('_r138 —— 6 块盒子的保面对照（`§99` 的第二例）')
    print('=' * 108)
    got = {}
    for tag, lab in ARMS:
        fs = sorted(glob.glob(os.path.join(MB, tag, 'snap_*.npz')), key=step_of)
        if not fs:
            print('\n  ### %-14s （无快照）' % tag)
            continue
        print('\n  ### %-14s %s（%d 个快照，step %d→%d）'
              % (tag, lab, len(fs), step_of(fs[0]), step_of(fs[-1])))
        print('     %-7s %-9s %-12s %-9s %s'
              % ('step', 'cov', 'f3_area(µm²)', '最差对', '各对 β 占比'))
        rows = []
        for p in fs[:8]:
            z = np.load(p)
            try:
                c = BM.snapshot_coverage(z)
            except Exception as e:
                print('     %-7d ⚠ %s' % (step_of(p), str(e)[:50]))
                continue
            bf = c.get('beta_frac', {}) or {}
            rows.append((step_of(p), c.get('cov', float('nan')),
                         c.get('f3_area', 0.0) * 1e12))
            print('     %-7d %-9.4f %-12.6f %-9s %s'
                  % (step_of(p), c.get('cov', float('nan')),
                     c.get('f3_area', 0.0) * 1e12, str(c.get('worst')),
                     '  '.join('%d|%d:%.2f' % (ij[0], ij[1], bf[ij])
                               for ij in sorted(bf)[:6])))
        got[tag] = rows
    print()
    print('  ---- 判读 ----')
    a, b = got.get('dry_saOddFp0'), got.get('dry_saOdd')
    if a and b:
        ca = dict((s, c) for s, c, _ in a)
        cb = dict((s, c) for s, c, _ in b)
        for s in sorted(set(ca) & set(cb)):
            print('     step %-4d  proj=0 cov=%.4f   proj=10 cov=%.4f  ⇒ %s'
                  % (s, ca[s], cb[s],
                     '**只有投影臂被抹平** ⇒ `§99` 现象**复现**'
                     if (cb[s] < 0.05 <= ca[s]) else
                     ('两臂都被抹平' if cb[s] < 0.05 and ca[s] < 0.05
                      else '两臂都正常 / 其他')))
    print()
    print('  参照（R75 的 2 块盒子，`§99`）：proj=10 的 `f3_area` **4.108 → 0.000000**')
    print('     （step 20），proj=0 的**逐位不变**（4.108111）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
