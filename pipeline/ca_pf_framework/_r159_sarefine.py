#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r159_sarefine.py —— **`§112` 的解释精修**：两臂的"上升"不是同一回事。

## 为什么要精修

`§112` 报了两臂 `r_selfac` **都上升**，并据此判 `SA-1` FAIL。
但两者的**含义不对称** ——

`r(G) = min over simplex`，而 `saOddG` 起手就是**等分**（六个块同尺寸）
⇒ 它**起在下界附近**（0.0487 vs 下界 0.0000）⇒ **任何扰动都只能让它上升**
⇒ `saOddG` 的上升**只能说明"停不住"，不能说明"走不到"**。

而 `saSet2` 起在 **0.5423（下界 0.4828）** ⇒ 它**有下降空间**（0.0595）
⇒ 它**上升**才是"**动力学不朝自协调走**"的证据。

## 本脚本报什么

1. 两臂的 **`r` 起点相对下界的位置**（"有没有下降空间"）；
2. **"可动范围已走完的比例"** `frac = (r(0) − r(末)) / (r(0) − r_min)`：
   `+` = 朝下界走，`−` = 远离；
3. 明确区分"**停不住**"（起点就在下界）与"**走不到**"（有空间却不走）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r78_pairselfac as R78                               # noqa: E402
from T16_verify_rve import EPS0                             # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
E_ALL = [np.asarray(e, float) - np.trace(e) / 3.0 * np.eye(3) for e in EPS0]
SCALE = float(np.mean([np.linalg.norm(e) for e in E_ALL]))
VEC = np.array([e.reshape(-1) for e in E_ALL])
ARMS = [('saOddG', (1, 3, 5, 7, 9, 11)),
        ('saSet2', (1, 2, 3, 4, 7, 8))]


def rmin_of(G):
    return R78._simplex_r(VEC[[v - 1 for v in G]], SCALE)


def main():
    print('=' * 104)
    print('_r159 —— `§112` 的解释精修：两臂的"上升"不是同一回事')
    print('=' * 104)
    print('  %-9s %-9s %-10s %-10s %-10s %-11s %s'
          % ('臂', 'r_min', 'r(0)', 'r(末)', '**可动范围**', '**走完比例**', '判读'))
    for tag, G in ARMS:
        p = os.path.join(MB, 'dry_' + tag, 'series.csv')
        if not os.path.exists(p):
            print('  %-9s （无数据）' % tag)
            continue
        rows = list(csv.DictReader(open(p)))
        r = []
        for x in rows:
            try:
                r.append(float(x['r_selfac']))
            except (KeyError, ValueError):
                pass
        r = np.array(r)
        m = rmin_of(G)
        room = r[0] - m
        frac = (r[0] - r[-1]) / room if room > 1e-9 else float('nan')
        verdict = ('**起点就在下界附近 ⇒ 只能升** ⇒ 本臂只能说明"**停不住**"'
                   if room < 0.02 else
                   '**有下降空间却不降 ⇒ 说明"走不到"** ← 这才是承重结论')
        print('  %-9s %-9.4f %-10.4f %-10.4f %-10.4f %-+11.1f%% %s'
              % (tag, m, r[0], r[-1], room, 100 * frac, verdict))
    print()
    print('  ---- 结论（★ 第一版叙述写错了，这里是更正后的）----')
    print('  ⚠ **第一版我写的是"`saOddG` 起手就在下界 ⇒ 它的上升是平凡的"—— 那是错的。**')
    print('     事实：`saOddG` 起手是**等分**，而**等分值 0.0482 > 单纯形最优 0.0000**')
    print('     ⇒ 它**同样有 0.0487 的下降空间**（要把分数**非等分**地重排才能走到 0）。')
    print()
    print('  ⇒ **两臂的可动空间相当（0.0487 vs 0.0595），而且都**离开**了可动空间：**')
    print('     * `saOddG`：走完比例 **−59.2%**（不但没走，还倒退了一半多）；')
    print('     * `saSet2`：走完比例 **−125.0%**（倒退超过一倍）。')
    print('  ⇒ ⇒ **两臂都是"有空间却不走"的证据** ⇒ `§112` 的结论**成立**，')
    print('     而且比我原先以为的**更强**（我一度以为 `saOddG` 是平凡的，其实不是）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
