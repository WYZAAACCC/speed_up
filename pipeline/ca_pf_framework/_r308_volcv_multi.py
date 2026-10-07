#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r308_volcv_multi.py —— ★ **硬规则 ㉞ 的追溯应用**：`§156` 的"体积 CV 单调上升"是否**多构型成立**？

## 为什么做（`§161` 的直接后果）
`§161` 刚刚证明：本会话已**连续三次**栽在"从单一构型外推"上
（`§33`→`§35`、`§95`→`§98`、`§144`→`§161`）。
⇒ 我立刻用硬规则 ㉞ 回头查**其他**招牌结论，发现：

| 结论 | 当时基于几个构型？ |
|---|---|
| `§146`/`§148`（`ed` 按位置组织）| **1 个**（`saSet2`）|
| **`§156`（体积 CV 单调上升）** | **1 个**（`saSet2EDV`）|

**⇒ 本节对 `§156` 做**全归档多构型**的离线复核**（`vol_cv` 只需 `region`，纯离线）。

## 判据（**先写死**）
* **W-1** 对每个有 ≥4 个快照的臂，算**逐快照的 `vol_cv`**（逐场体积的变异系数）。
* **W-2** 判"是否**上升**"：用**首末比**（末/首）与**单调性**（升的步数占比）两个口径。
* **W-3 ★** 若**多数臂**都上升 ⇒ `§156` 稳健；若**只有少数**（或方向不一）⇒ **须收窄**。
* **W-4** 退化：某快照场数 < 2 ⇒ 跳过（不能算 CV）。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def vol_cv(region):
    v = [int((region == k).sum()) for k in np.unique(region) if k > 0]
    if len(v) < 2:
        return float('nan'), len(v)
    a = np.asarray(v, float)
    return float(a.std() / a.mean()), len(v)


def main():
    print('=' * 108)
    print('_r308 —— `§156` 的多构型复核：逐快照 `vol_cv` 是否上升？')
    print('=' * 108)
    arms = sorted(d for d in os.listdir(MB)
                  if d.startswith('dry_') and os.path.isdir(os.path.join(MB, d)))
    rows = []
    for a in arms:
        fs = sorted(glob.glob(os.path.join(MB, a, 'snap_*.npz')),
                    key=lambda f: int(re.search(r'_(\d+)\.npz$', f).group(1)))
        if len(fs) < 4:
            continue
        steps, cvs = [], []
        for f in fs:
            try:
                z = np.load(f, allow_pickle=True)
            except (OSError, ValueError):
                continue
            if 'region' not in z:
                continue
            c, n = vol_cv(np.asarray(z['region']))
            if c == c and n >= 2:
                steps.append(int(z['step']) if 'step' in z else len(steps))
                cvs.append(c)
        if len(cvs) < 4:
            continue
        d = np.diff(cvs)
        frac_up = float((d > 0).mean())
        ratio = cvs[-1] / cvs[0] if cvs[0] > 0 else float('nan')
        rows.append((a, len(cvs), cvs[0], cvs[-1], ratio, frac_up))
    print('  ## **W-1/W-2** 逐臂（按首末比排序）')
    print('     %-16s %-6s %-11s %-11s %-9s %s'
          % ('臂', '快照', 'vol_cv(首)', 'vol_cv(末)', '末/首', '上升步占比'))
    for (a, n, c0, c1, r, fu) in sorted(rows, key=lambda x: -x[4]):
        print('     %-16s %-6d %-11.4f %-11.4f %-9.2f %.1f%%%s'
              % (a, n, c0, c1, r, 100 * fu,
                 '  ← **`§156` 用的臂**' if a == 'dry_saSet2EDV' else ''))
    print()
    if not rows:
        print('  ⚠ 没有足够的臂')
        return 0
    rs = np.array([r for (_, _, _, _, r, _) in rows], float)
    fus = np.array([f for (_, _, _, _, _, f) in rows], float)
    up = int((rs > 1).sum())
    print('  ## **W-3** 汇总')
    print('     臂数 = **%d**；**末/首 > 1（上升）的臂数 = %d**（%.0f%%）'
          % (len(rows), up, 100 * up / len(rows)))
    print('     末/首 的**中位 = %.3f**；上升步占比的**中位 = %.1f%%**'
          % (float(np.median(rs)), 100 * float(np.median(fus))))
    print('     ⇒ %s' % (
        '✅ **`§156` 稳健**：多数臂的 `vol_cv` 都在上升'
        if up >= 0.7 * len(rows) else
        '⚠ **`§156` 须收窄**：上升的臂不到 70% ⇒ 只能在"某些构型"上说'))
    if 'dry_saSet2EDV' in [a for (a, *_ ) in rows]:
        for (a, n, c0, c1, r, fu) in rows:
            if a == 'dry_saSet2EDV':
                print('     （`§156` 用的 `saSet2EDV`：%.4f → %.4f，末/首 **%.2f**，'
                      '上升步占比 **%.1f%%**）' % (c0, c1, r, 100 * fu))
    print()
    print('  ⚠ 记账：`vol_cv` = **逐场**体积的变异系数（不是逐变体）；')
    print('     每变体若有 2 场，两者同向；但**不同臂的场数/变体数不同**，')
    print('     ⇒ 本表只作**同臂内的时间趋势**比较，**不作跨臂的绝对比较**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
