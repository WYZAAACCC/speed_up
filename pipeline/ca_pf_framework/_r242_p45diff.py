#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r242_p45diff.py —— P1-45 对照的**逐列差异**（判定"处理到底动没动结果"）。

## 为什么不能只看 `f3_area`

`§116` 的教训：**55/97 列会变、21 列不变** ⇒ 盯一个列会漏掉大部分影响；
反过来，**"处理没生效"也必须逐列证**。`_r236` 只看了 `f3_area` 的 4 位小数。

## 判据

* **P-1** 打印两臂在**共同步**上的**逐列**相对差，列出 Top-N 与"完全相同的列"计数。
* **P-2** 若**全部列**在所有共同步上逐位相同 ⇒ **处理没有产生任何影响**（需查为什么）。
* **P-3** 若只有少数列不同 ⇒ 列出它们，并给出**效应量级**。
* ⚠ 明确标注读的是**第几步**（硬规则③：不能把中途当末态）。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    A, B = rows('p45L'), rows('p45P')
    if A is None or B is None:
        print('⚠ 有一臂还没写 series.csv')
        return 2
    print('=' * 108)
    print('_r242 —— P1-45 对照逐列差异（ladder vs perstep）')
    print('=' * 108)
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    print('  p45L 行数 %d（末步 %s）；p45P 行数 %d（末步 %s）；共同步 %d 个：%s'
          % (len(A), A[-1]['step'], len(B), B[-1]['step'], len(common), common))
    print('  ⚠ **这是中途读数，不是末态**（判据 O-2 要 400 步跑完才读）。')
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    print('  可比列 = %d' % len(cols))
    same_all, diff = [], []
    for c in cols:
        worst = 0.0
        n_same = 0
        for s in common:
            try:
                fa, fb = float(sa[s][c]), float(sb[s][c])
            except (TypeError, ValueError):
                if (sa[s].get(c) or '') == (sb[s].get(c) or ''):
                    n_same += 1
                continue
            if fa != fa and fb != fb:
                n_same += 1
                continue
            if repr(fa) == repr(fb):
                n_same += 1
                continue
            den = max(abs(fa), abs(fb), 1e-300)
            worst = max(worst, abs(fa - fb) / den)
        if n_same == len(common):
            same_all.append(c)
        else:
            diff.append((c, worst))
    print()
    print('  ## **P-3** 有差异的列：**%d / %d**' % (len(diff), len(cols)))
    for (c, w) in sorted(diff, key=lambda d: -d[1])[:25]:
        print('     %-24s 最大相对差 **%.3e**' % (c, w))
    print()
    print('  ## **P-1** 逐位完全相同的列：**%d / %d**' % (len(same_all), len(cols)))
    if len(same_all) <= 30:
        print('     %s' % ', '.join(same_all))
    print()
    print('=' * 108)
    if not diff:
        print('  ⇒ ❌ **P-2：全部列逐位相同 ⇒ 处理（γ 差 1.815×）没有产生任何可测影响。**')
        print('     需查：是 F3 面积太小（`§142.1`：仅占 3.0%），还是 γ 没进速度律。')
    else:
        mx = max(w for _, w in diff)
        print('  ⇒ ✅ **处理确有影响**：%d 列不同，最大相对差 **%.3e**（列 `%s`）'
              % (len(diff), mx, max(diff, key=lambda d: d[1])[0]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
