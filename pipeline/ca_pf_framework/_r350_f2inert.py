#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r350_f2inert.py —— ★★★ `--f2-pair-gamma` 在 `--facet-proj 0` 下**是不是完全惰性**？

## 由来

`_r295` 的 R-2 终判：`r_selfac` 末态
* 归档（投影 10）：λ=0 → 0.616659，λ=1 → 0.616491 ⇒ 相对差 **−2.724e-04**
* 新（投影 0）  ：λ=0 → **0.548566**，λ=1 → **0.548566** ⇒ 相对差 **+0.000e+00**

**⇒ 不只是"没放大 10 倍"，而是"一点效应都没有"。**
（`_r280` 预登记的二分法"≥10× ⇒ ①主因 / ≈2.72e-04 ⇒ ②③约束"**没有覆盖这个结果** ——
必须如实报为**第三种结局**。）

## 本脚本要把它钉死

逐列比较 **`saSet2P0` vs `saSet2F2P0`** 的**整条 `series.csv`**：
* **A-1**：两臂**是否逐位相同**（相同列数 / 不同列数 / 最大相对差）；
* **A-2 对照**：同一方法比较 **`saSet2` vs `saSet2F2`**（投影 10，归档）
  ⇒ **必须**能测出差异（否则是"方法没有分辨力"，不是"效应为零"）；
* **A-3 对照**：`saSet2P0` vs 自己（应为 0 差异）⇒ 证明比较算子本身不产生假差异。

⚠ **A-2 是决定性的对照**：没有它，"0 差异"无法区分"真的惰性"与"我的比较坏了"。
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _r295_r280verdict import rows, coldiff   # noqa: E402


def show(lab, a, b):
    A, B = rows(a), rows(b)
    if not A or not B:
        print('  %-34s （缺数据）' % lab)
        return None
    U = min(int(A[-1]['step']), int(B[-1]['step']))
    s, ncol, worst = coldiff(A, B, upto=U)
    print('  %-34s 共同步≤%-5s **不同列 %-4d** 最大相对差 **%.3e** (%s)'
          % (lab, U, ncol, worst[0], worst[1]))
    return ncol, worst[0]


def main():
    print('=' * 104)
    print('_r350 —— `--f2-pair-gamma` 在投影 0 下是否**完全惰性**？')
    print('=' * 104)
    print()
    print('  ## A-1 被测：投影 0 下的 λ 效应')
    r1 = show('saSet2P0 vs saSet2F2P0', 'saSet2P0', 'saSet2F2P0')
    print()
    print('  ## **A-2 决定性对照**：投影 10（归档）下的同一比较')
    print('     ⇒ 必须能测出差异，否则 A-1 的"0"说明不了任何事')
    r2 = show('saSet2 vs saSet2F2（归档）', 'saSet2', 'saSet2F2')
    print()
    print('  ## A-3 负对照：自己 vs 自己（应恰好 0）')
    show('saSet2P0 vs saSet2P0', 'saSet2P0', 'saSet2P0')
    print()
    print('  ## 判定')
    if r2 is None or r2[0] == 0:
        print('  ❌ **A-2 对照失败**（归档两臂测不出差异）⇒ 比较算子没有分辨力')
        print('     ⇒ **A-1 的"0 差异"不可解读**（硬规则 ④/⑯）。')
        return 2
    print('  ✅ **A-2 对照通过**：归档两臂在 %d 个列上有差异、最大 %.3e'
          % (r2[0], r2[1]))
    if r1 is None:
        return 2
    if r1[0] == 0:
        print('  ⇒ ⇒ **A-1 = 0 个不同列 ⇒ `--f2-pair-gamma` 在 `--facet-proj 0` 下'
              '完全惰性（逐位相同）**')
        print('     ⇒ 与 `§170`（`advance` 的 `(karr,larr)` 基里 **F2 面片 ≡ 0**）**互相印证**：')
        print('        F2 的 γ 表**没有任何面片会去查它**。')
        print('     ⇒ 归档那 **−2.724e-04** 只能是 **`--facet-proj 10` 造出来的**。')
    else:
        print('  ⇒ A-1 仍有 %d 个不同列（最大 %.3e）⇒ **并非完全惰性**，'
              '还有一条未找到的通路（待办 E-1 继续）' % (r1[0], r1[1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
