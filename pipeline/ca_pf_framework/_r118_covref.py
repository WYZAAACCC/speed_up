#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r118_covref.py —— **界面完整性 `cov` 的参照**：R75 盒子（板条**维持住了**）vs R110 盒子。

## 为什么要这个参照

`_r117` 实测 R110 的 6 块盒子：
* **t=0 就** `cov = 0.53`（判据 ≥0.85）、各对 β 占比 0.26–0.33（判据 ≤0.25）；
* step 20 时 `f3_area` 从 **1.03 → 0.003 µm²**（×1/340）、`cov → 0.001`。

**但"`cov` 低"本身不能直接判缺陷** —— 必须与**同一量具在已知良好构型上**的读数比。
已知良好：`dry_mb2fp10`（R75，N=96/Δx=62.5/L=1600/W=700/T=635）实测
`blk_nprof = 3/3` 在 **31/31 快照**上成立 ⇒ 它的同变体界面**是维持住的**。

⇒ 逐快照跑 `snapshot_coverage`，两盒子并排。判据：**若 R75 的 `cov` 显著更高**，
则 R110 的**播种几何**（`L=600/W=350/T=510`、`gap=0`）确实把 F3 界面播坏了。
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
PAIRS = [('dry_mb2fp10', 'R75 盒子 N=96 L=1600 W=700 T=635（板条**维持住了**）'),
         ('dry_mo1fp10', 'R77 单块 N=96 L=1600 W=700 T=635'),
         ('dry_saOdd', 'R110 六块 N=112 L=600 W=350 T=510（**裂了**）'),
         ('dry_saPairE0', 'R110 六块 el=0（同样裂）')]


def step_of(p):
    return int(re.search(r'snap_(\d+)\.npz$', p).group(1))


def main():
    print('=' * 112)
    print('_r118 —— `cov`（界面完整性）并排：良好构型 vs 出问题的构型')
    print('=' * 112)
    for tag, lab in PAIRS:
        fs = sorted(glob.glob(os.path.join(MB, tag, 'snap_*.npz')), key=step_of)
        if not fs:
            print('\n  ### %-14s （无快照）' % tag)
            continue
        print('\n  ### %-14s %s' % (tag, lab))
        print('     %-7s %-9s %-11s %-11s %-9s %s'
              % ('step', 'cov', 'f3_area', 'exp_int', '最差对', '各对 β 占比'))
        pick = fs if len(fs) <= 5 else [fs[0], fs[1], fs[len(fs) // 2], fs[-1]]
        for p in pick:
            z = np.load(p)
            try:
                c = BM.snapshot_coverage(z)
            except Exception as e:
                print('     %-7d ⚠ %s' % (step_of(p), str(e)[:60]))
                continue
            bf = c.get('beta_frac', {}) or {}
            s = '  '.join('%d|%d:%.2f' % (ij[0], ij[1], bf[ij])
                          for ij in sorted(bf)[:6])
            print('     %-7d %-9.3f %-11.4f %-11.4f %-9s %s'
                  % (step_of(p), c.get('cov', float('nan')),
                     c.get('f3_area', 0.0) * 1e12, c.get('exp_int', 0.0) * 1e12,
                     str(c.get('worst')), s))
    print()
    print('  ---- 判读 ----')
    print('  * 判据（`snapshot_coverage` docstring，由预装臂 `dry_pa` 校准）：')
    print('       `cov ≥ 0.85` 且 **各对 β 占比 ≤ 0.25**；本倾角/分辨率下**天花板 0.85–0.96**、')
    print('       β **底噪 ~0.15**（所以 t=0 的 0.15 左右是正常的，不是缺陷）。')
    print('  * 若 R75 盒子 t=0 的 `cov` 明显 >0.85 而 R110 只有 ~0.53 ⇒')
    print('       **R110 的播种几何把 F3 界面播坏了**（`gap=0` 的阶梯错位，见 `_bk_exp.py:708-721`）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
