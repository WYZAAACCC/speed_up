#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r119_projf3.py —— **保面机制是否在第一次投影时抹掉全部 F3 界面？**（用**已有**数据）

## 观测（`_r118`）

| 盒子 | `--facet-proj` | `cov(t=0)` | **`cov(t=20)`** | `cov(末)` |
|---|---|---|---|---|
| `dry_mb2fp10`（R75 保面臂） | **10** | 1.079 | **0.000** | 0.792 |
| `dry_mo1fp10`（R77 保面臂） | **10** | 0.958 | **0.000** | 0.684 |
| `dry_saOdd`（R110） | 10 | 0.527 | 0.004 | 0.010 |

**`f3_area` 在 step 20 **恰好为 0.0000** ⇒ 不是"变少"，是**一张 F3 面都没有了**。
R75 的日志里也写着 `[  20] ... F3面=0 面积=0.0000 µm²`，step 40 起才恢复（0.1219 → … → 4.45）。

## 判据（**用已有臂做对照，不需新仿真**）

R75 有一条**只差 `--facet-proj`** 的对照臂 **`dry_mb2fp0`**（proj=**0**，其余逐项相同）。
⇒ 若 `mb2fp0` 在 step 20 的 `cov` **不为 0** ⇒ **step-20 的抹平是投影造成的**（机制缺陷）。
  若两者都为 0 ⇒ 与投影无关，是别的东西（另查）。

⚠ 记账：`mb2fp0` 与 `mb2fp10` 是**同一次 `_r75_mb.sh`** 里跑的两条臂
（同 N/Δx/盒/板条/步数/`--pair-every`），**只差 `--facet-proj`** ⇒ 严格单变量。
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
SETS = [('dry_mb2fp10', 'proj=**10**'), ('dry_mb2fp0', 'proj=**0**'),
        ('dry_mo1fp10', 'proj=10（单块）')]


def step_of(p):
    return int(re.search(r'snap_(\d+)\.npz$', p).group(1))


def main():
    print('=' * 104)
    print('_r119 —— step-20 的 F3 抹平是不是 `--facet-proj` 造成的？')
    print('=' * 104)
    got = {}
    for tag, lab in SETS:
        fs = sorted(glob.glob(os.path.join(MB, tag, 'snap_*.npz')), key=step_of)
        if not fs:
            print('  %-14s （无快照）' % tag)
            continue
        print('\n  ### %-14s %s' % (tag, lab))
        print('     %-7s %-9s %-11s %-9s %s' % ('step', 'cov', 'f3_area(µm²)',
                                               '最差对', '各对 β 占比'))
        rows = []
        for p in fs[:6]:
            z = np.load(p)
            try:
                c = BM.snapshot_coverage(z)
            except Exception as e:
                print('     %-7d ⚠ %s' % (step_of(p), str(e)[:50]))
                continue
            bf = c.get('beta_frac', {}) or {}
            rows.append((step_of(p), c.get('cov', float('nan')),
                         c.get('f3_area', 0.0) * 1e12))
            print('     %-7d %-9.4f %-11.6f %-9s %s'
                  % (step_of(p), c.get('cov', float('nan')),
                     c.get('f3_area', 0.0) * 1e12, str(c.get('worst')),
                     '  '.join('%d|%d:%.2f' % (ij[0], ij[1], bf[ij])
                               for ij in sorted(bf)[:6])))
        got[tag] = rows
    print()
    print('  ---- 判读 ----')
    a, b = got.get('dry_mb2fp10'), got.get('dry_mb2fp0')
    if not a or not b:
        print('     数据不全')
        return 1
    ca = dict((s, c) for s, c, _ in a)
    cb = dict((s, c) for s, c, _ in b)
    for s in sorted(set(ca) & set(cb))[:4]:
        print('     step %-4d  proj=10 cov=%.4f   proj=0 cov=%.4f  ⇒ %s'
              % (s, ca[s], cb[s],
                 '**只有投影臂被抹平** ⇒ 是保面机制的问题'
                 if (ca[s] < 0.05 <= cb[s]) else
                 ('两臂都被抹平 ⇒ 与投影无关' if ca[s] < 0.05 and cb[s] < 0.05
                  else '两臂都正常 / 其他')))
    print()
    print('  ⚠ 即便确认是投影造成的，也**不要**立刻改引擎：')
    print('     该机制是单块/两块验收通过的（`blk_nprof` 3/3 全程、`f_flat` ×6.4），')
    print('     而 step-20 的抹平**会自行恢复**（step 300 回到 0.748）⇒')
    print('     先记录 + 量化影响，再决定是否修。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
