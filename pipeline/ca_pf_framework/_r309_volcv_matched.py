#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""_r309_volcv_matched.py —— ★★ **控制步数后**再比：`--facet-proj 0` 是否真的抑制体积分化？

## 为什么必须做（`_r308` 的发现与其**混淆**）
`_r308` 扫了 39 个臂：**31 个（79%）`vol_cv` 上升** ⇒ `§156` 稳健。
**但**：
* **4 个不上升的臂恰好都是 `--facet-proj 0`**（`saSet2P0` 0.94、`p45L0`/`p45P0` 0.74、`saOddFp0` 0.99）；
* **⚠ 混淆**：这些臂**步数更少**（`saSet2P0` 只 6 个快照）⇒ **时间不够**也会"不上升"。

**⇒ 必须**在相同步数**上比"有投影 vs 无投影"。**

## 判据（**先写死**）
* **M-1** 对每一对（有投影臂、无投影臂），取**共同步**，比较该步的 `vol_cv`。
* **M-2 ★** 若在**同一时刻**无投影臂的 `vol_cv` 系统性更低 ⇒ **投影**导致**体积分化**。
* **M-3** 负对照：**同配置跑两次**（`saSet2DT` vs `saSet2`）必须给出**同一条曲线**
  （否则是噪声）。
* **M-4** 退化：无共同步 ⇒ 报"不适用"。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')

# (有投影, 无投影) 成对
PAIRS = [('saSet2', 'saSet2P0'), ('p45L', 'p45L0'), ('p45P', 'p45P0')]


def series(arm):
    """返回 {step: vol_cv}。"""
    out = {}
    for f in sorted(glob.glob(os.path.join(MB, arm, 'snap_*.npz')),
                    key=lambda f: int(re.search(r'_(\d+)\.npz$', f).group(1))):
        try:
            z = np.load(f, allow_pickle=True)
        except (OSError, ValueError):
            continue
        if 'region' not in z:
            continue
        v = [int((z['region'] == k).sum()) for k in np.unique(z['region']) if k > 0]
        if len(v) < 2:
            continue
        a = np.asarray(v, float)
        out[int(z['step']) if 'step' in z else -1] = float(a.std() / a.mean())
    return out


def main():
    print('=' * 108)
    print('_r309 —— **控制步数**后：`--facet-proj 0` 是否抑制体积分化？')
    print('=' * 108)
    allok = True
    for (on, off) in PAIRS:
        A, B = series('dry_' + on), series('dry_' + off)
        if not A or not B:
            print('\n  ## `%s` vs `%s`：⚪ **不适用**（缺数据）' % (on, off))
            continue
        common = sorted(set(A) & set(B))
        print('\n  ## `%s`(投影 10) vs `%s`(投影 0) —— 共同步 %d 个'
              % (on, off, len(common)))
        if not common:
            print('     ⚪ **无共同步 ⇒ 不适用**（两臂采样点不重叠）')
            continue
        print('     %-8s %-14s %-14s %s' % ('step', 'vol_cv(投影10)', 'vol_cv(投影0)', '差(0−10)'))
        for s in common:
            print('     %-8d %-14.4f %-14.4f %+.4f' % (s, A[s], B[s], B[s] - A[s]))
        d = np.array([B[s] - A[s] for s in common])
        nneg = int((d < 0).sum())
        print('     ⇒ 无投影更低的步数 = **%d / %d**；平均差 = **%+.4f**'
              % (nneg, len(common), float(d.mean())))
        if nneg >= 0.7 * len(common) and d.mean() < 0:
            print('     ⇒ ✅ **投影确实推高 `vol_cv`**（同一时刻、无投影系统性更低）')
        elif nneg <= 0.3 * len(common):
            print('     ⇒ ❌ **方向相反**（无投影反而更高）⇒ 记账')
        else:
            print('     ⇒ ⚠ **不明确**（方向混杂）⇒ 如实记录')
            allok = False
    # M-3 负对照
    print('\n  ## **M-3 负对照**：`saSet2DT` vs `saSet2`（**同配置**两次）')
    A, B = series('dry_saSet2DT'), series('dry_saSet2')
    common = sorted(set(A) & set(B))
    same = all(abs(A[s] - B[s]) < 1e-15 for s in common)
    print('     共同步 %d ⇒ **逐位相同 = %s** ⇒ %s'
          % (len(common), same, '✅ 曲线可复现' if same else '❌ 不可复现'))
    print()
    print('  ⚠ 记账：`vol_cv` 是**逐场**体积的 CV；本表**只比同一时刻**的同一量。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
