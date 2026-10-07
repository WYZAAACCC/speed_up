#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r116_frag.py —— **块裂开没有？**（6 块盒子里条件 ② 的存活判据）

## 背景（本轮新观测）

`saPair` 在 **step 20** 时 `nblk_sig` 从 **6 → 11**、`blk_nprof` 从 `2/2/2/2/2/2`
变成 `2/1/1/1/…/1` ⇒ **播好的"2 根一块"在 20 步内裂成单根**。

## 报什么

对每个臂逐步报：`nblk_sig` / `blk_laths` / `blk_nprof` / `blk_nruns`，
以及**"块内 2 根的块数"**（= `blk_nprof` 里等于 2 的个数）—— 这是判据量的直接形式。

⚠ 口径：`blk_nprof` 是**逐块、沿该块自己的 n\\* 的柱剖面里出现过的场数**（`§87` 的新量具）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = ['saPair', 'saPairE0', 'saOdd', 'saOddFp0']


def ints(s):
    return [int(float(t)) for t in str(s or '').split('/') if t.strip()]


def main():
    print('=' * 108)
    print('_r116 —— 块有没有裂？（6 块盒子里的条件 ② 存活判据）')
    print('=' * 108)
    for t in ARMS:
        p = os.path.join(MB, 'dry_' + t, 'series.csv')
        if not os.path.exists(p):
            print('  %-10s （无数据）' % t)
            continue
        rows = list(csv.DictReader(open(p)))
        print()
        print('  ### %-10s （%d 行）' % (t, len(rows)))
        print('     %-7s %-9s %-30s %-30s %s'
              % ('step', 'nblk_sig', 'blk_laths', 'blk_nprof', '块内=2 的块数'))
        for r in rows:
            if 'blk_nprof' not in r:
                print('     ⚠ 无 `blk_nprof` 列')
                break
            npf = ints(r.get('blk_nprof'))
            n2 = sum(1 for x in npf if x == 2)
            print('     %-7s %-9s %-30s %-30s %d'
                  % (r.get('step'), r.get('nblk_sig'), r.get('blk_laths'),
                     r.get('blk_nprof'), n2))
        # 趋势判读
        if len(rows) >= 3:
            nb = [int(float(r.get('nblk_sig', 'nan') or 'nan')) for r in rows]
            n2 = [sum(1 for x in ints(r.get('blk_nprof')) if x == 2) for r in rows]
            print('     ⇒ `nblk_sig` %d → %d（初→末）；"块内 2 根"的块数 %d → %d'
                  % (nb[0], nb[-1], n2[0], n2[-1]))
    print()
    print('  ---- 保面对照（`saOdd` proj=10  vs  `saOddFp0` proj=0）----')
    a = os.path.join(MB, 'dry_saOdd', 'series.csv')
    b = os.path.join(MB, 'dry_saOddFp0', 'series.csv')
    if os.path.exists(a) and os.path.exists(b):
        ra = list(csv.DictReader(open(a)))
        rb = list(csv.DictReader(open(b)))
        print('     %-7s %-12s %-12s %-12s %s'
              % ('step', 'saOdd(10)', 'saOddFp0(0)', '判读', ''))
        sa = {int(float(r['step'])): r for r in ra}
        sb = {int(float(r['step'])): r for r in rb}
        for k in sorted(set(sa) & set(sb)):
            na = sa[k].get('nblk_sig')
            nb = sb[k].get('nblk_sig')
            print('     %-7d %-12s %-12s %s' % (k, na, nb,
                  '两臂都裂' if (na and nb and float(na) > 6 and float(nb) > 6)
                  else ('**只有投影臂裂**' if (na and float(na) > 6
                                              and nb and float(nb) <= 6)
                        else ('只有对照臂裂' if (nb and float(nb) > 6
                                                and na and float(na) <= 6)
                              else '两臂都稳'))))
    else:
        print('     （`saOddFp0` 还没写出数据）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
