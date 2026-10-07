#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r286_z2f3.py —— ★★ **Z-2 的对齐比较**：`f3_area` 的**逐 step 分叉模式**，
投影组 vs 无投影组（同几何、同 γ_F3 对比 1.815×，只差 `--facet-proj`）。

## 为什么比"逐 step 模式"而不是只比末态
`_r243` 揭示：**投影组末态 `f3_area` 差 +0.61%（方向对），
但 21 个采样步里只有 5 步不同、且符号**混杂**（+3.0e-3 / −4.8e-3 / +3.0e-3 / −1.3e-2 / +6.5e-3）**
⇒ **不是持续效应，是偶发。** 只看末态会**高估**它的稳健性。

## 判据（**先写死**）
在**共同步（≤ min(两组末步)）**上：
* **N-1** 分别数"**有多少个采样步 `f3_area` 逐位不同**"；
* **N-2** 分别算 `|Δ f3_area| / f3_area` 的**中位**（只在该步不同时计入）；
* **N-3** 看**符号一致性**（同号步数 / 不同号步数）。
* **预言（`§144`/`§147`）**：**无投影组的 N-1 更大、N-2 更大、符号更一致。**
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def pattern(A, B, upto, col='f3_area_m2'):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = [s for s in sorted(set(sa) & set(sb), key=lambda x: int(x))
              if int(s) <= upto]
    same, diff = 0, []
    for s in common:
        try:
            a, b = float(sa[s][col]), float(sb[s][col])
        except (KeyError, TypeError, ValueError):
            continue
        if repr(a) == repr(b):
            same += 1
        else:
            diff.append((s, (b - a) / a if a else float('nan')))
    return common, same, diff


def main():
    print('=' * 108)
    print('_r286 —— Z-2 对齐比较：`f3_area` 的逐 step 分叉模式（投影 vs 无投影）')
    print('=' * 108)
    L, P = rows('p45L'), rows('p45P')
    L0, P0 = rows('p45L0'), rows('p45P0')
    if not all((L, P, L0, P0)):
        print('  ⚠ 缺数据'); return 2
    e1, e2 = int(L[-1]['step']), int(L0[-1]['step'])
    U = min(e1, e2)
    print('  投影组末步 %d；无投影组末步 %d ⇒ **共同步 ≤ %d**' % (e1, e2, U))
    print()
    print('  ## **N-1/N-2/N-3** 逐 step 模式')
    for lab, A, B in (('投影组（--facet-proj 10）', L, P),
                      ('**无投影组（--facet-proj 0）**', L0, P0)):
        common, same, diff = pattern(A, B, U)
        n = len(common)
        rel = [abs(d) for (_, d) in diff]
        pos = sum(1 for (_, d) in diff if d > 0)
        neg = sum(1 for (_, d) in diff if d < 0)
        print()
        print('     ### %s' % lab)
        print('        采样步数 %d ；**逐位相同的步 = %d ；不同的步 = %d**'
              % (n, same, len(diff)))
        if diff:
            print('        不同步：%s' % ', '.join(
                'step%s(%+.3e)' % (s, d) for (s, d) in diff))
            print('        `|Δ|/f3_area` **中位 = %.3e**，最大 = %.3e'
                  % (float(np.median(rel)), max(rel)))
            print('        符号：**正 %d / 负 %d** ⇒ %s'
                  % (pos, neg, '**一致**' if not (pos and neg) else '**混杂**'))
        else:
            print('        ⇒ **全程逐位相同**（处理完全没显现）')
    print()
    print('=' * 108)
    print('  ## 判定')
    print('=' * 108)
    c1, s1, d1 = pattern(L, P, U)
    c2, s2, d2 = pattern(L0, P0, U)
    r1 = float(np.median([abs(x) for (_, x) in d1])) if d1 else 0.0
    r2 = float(np.median([abs(x) for (_, x) in d2])) if d2 else 0.0
    print('     %-16s %-14s %-14s %s' % ('量', '投影组', '无投影组', '预言'))
    print('     %-16s %-14d %-14d %s' % ('不同的步数', len(d1), len(d2),
                                          '无投影应更多'))
    print('     %-16s %-14.3e %-14.3e %s' % ('中位 |Δ|/f3', r1, r2, '无投影应更大'))
    print('     %-16s %-14d %-14d' % ('逐位相同的步', s1, s2))
    if len(d2) > len(d1) and r2 > r1:
        print()
        print('     ⇒ ✅ **Z-2 成立**：无投影组的 `f3_area` **分叉步数更多、幅度更大**')
        print('        ⇒ 独立支持 `§144`/`§147`（投影压制界面能对形态的影响）。')
    elif len(d2) == len(d1):
        print()
        print('     ⇒ ⚠ 两组分叉步数相同 ⇒ **Z-2 不成立**（需如实报）。')
    else:
        print()
        print('     ⇒ ⚠ 方向不明确（步数 %d vs %d；幅度 %.3e vs %.3e）⇒ 如实记录。'
              % (len(d1), len(d2), r1, r2))
    print()
    print('  ⚠ 记账：无投影组只到 step %d ⇒ 本判据是**中途对齐**，非末态。' % U)
    return 0


if __name__ == '__main__':
    sys.exit(main())
