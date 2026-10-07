#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r328_couplingsens.py —— `§166` 的**稳健性**：去趋势耦合对"窗宽"敏感吗？随时间增强吗？

## 为什么要查
`§166` 的 D-3（去平滑趋势残差）用了**窗宽 40**，得到 r = 0.969。
**⇒ 窗宽是**我选的** ⇒ 必须查它对结论的影响**（硬规则 ⑫/⑭ 的同类：
**判据里的自由参数必须扫一遍**）。

## 判据（**先写死**）
* **S-1** 窗宽扫描 `w ∈ {10, 20, 40, 80, 160}`：D-3 的 Pearson 应**同号且量级稳定**。
* **S-2 ★** **分段耦合**：把 400 步分成**前半/后半**（以及 4 段），
  各算 D-2（一阶差分）与 D-3。
  * **若耦合随时间**增强** ⇒ 支持"正反馈逐步建立"；
  * **若各段相当** ⇒ 耦合是**稳态**性质（不是"逐步建立"）。
* **S-3** 负对照（循环平移）在**每一段**都应显著更低。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_exp', '_bk_mb', 'dry_saSet2EDV', 'diag_edv.json')


def pear(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 4:
        return float('nan')
    sa, sb = a[m], b[m]
    if sa.std() < 1e-30 or sb.std() < 1e-30:
        return float('nan')
    return float(np.corrcoef(sa, sb)[0, 1])


def movavg(x, w):
    if w < 3:
        return x.copy()
    k = np.ones(w) / w
    pad = w // 2
    xp = np.pad(x, pad, mode='edge')
    return np.convolve(xp, k, mode='valid')[:len(x)]


def main():
    print('=' * 100)
    print('_r328 —— `§166` 稳健性：窗宽敏感性 + 分段耦合')
    print('=' * 100)
    d = json.load(open(P))
    rec = d['rec']
    st = np.array([r['step'] for r in rec], float)
    cv = np.array([r.get('vol_cv', np.nan) for r in rec], float)
    sp = np.array([r.get('med_spread', np.nan) for r in rec], float)
    m = np.isfinite(cv) & np.isfinite(sp)
    cv, sp, st = cv[m], sp[m], st[m]
    print('  有效点 %d（step %d … %d）' % (len(cv), st[0], st[-1]))

    print()
    print('  ## **S-1** 去平滑趋势残差的**窗宽敏感性**')
    print('     %-8s %-14s %s' % ('窗 w', 'D-3 Pearson', '判定'))
    for w in (10, 20, 40, 80, 160):
        r = pear(cv - movavg(cv, w), sp - movavg(sp, w))
        print('     %-8d %-14.4f %s' % (w, r,
              '✅ 强耦合' if r > 0.5 else ('⚠ 中等' if r > 0.2 else '❌ 弱')))
    print('     ⇒ 若各窗**同号且都 > 0.5** ⇒ 结论不依赖窗宽的选择。')

    print()
    print('  ## **S-2/S-3** 分段耦合（前半/后半 + 4 段）')
    print('     %-14s %-14s %-14s %-14s %s'
          % ('段', 'D-2 差分', 'D-3 残差(w=40)', '平移负对照', '该段 vol_cv 范围'))
    segs = [('前半 1–200', 0, 200), ('后半 201–400', 200, 400),
            ('1–100', 0, 100), ('101–200', 100, 200),
            ('201–300', 200, 300), ('301–400', 300, 400)]
    for (lab, lo, hi) in segs:
        mm = (st > lo) & (st <= hi)
        if mm.sum() < 20:
            continue
        c, s = cv[mm], sp[mm]
        r2 = pear(np.diff(c), np.diff(s))
        r3 = pear(c - movavg(c, 40), s - movavg(s, 40))
        r4 = pear(c, np.roll(s, min(50, len(s) // 3)))
        print('     %-14s %-14.4f %-14.4f %-14.4f %.3f – %.3f'
              % (lab, r2, r3, r4, c.min(), c.max()))
    print()
    h1 = pear(np.diff(cv[:200]), np.diff(sp[:200]))
    h2 = pear(np.diff(cv[200:]), np.diff(sp[200:]))
    print('     ⇒ 前半/后半的 **D-2**：**%.4f** vs **%.4f**' % (h1, h2))
    if h1 == h1 and h2 == h2:
        if h2 > h1 * 1.3:
            print('        ⇒ **耦合随时间增强** ⇒ 支持"正反馈逐步建立"')
        elif h1 > h2 * 1.3:
            print('        ⇒ 耦合随时间**减弱** ⇒ 更像早期瞬态')
        else:
            print('        ⇒ 前后半相当 ⇒ 耦合是**稳态**性质，不是"逐步建立"')
    print()
    print('  ⚠ 记账：分段后点数少（每段 100 点）⇒ 差分相关噪声更大，只看**方向与量级**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
