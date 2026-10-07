#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r158_impact.py —— **选支规则影响面清单**（数据驱动，不是凭印象列）。

## 为什么（`R30_AUDIT_LEDGER.md` §113 第六节）

`§113` 用**一个**观测量（`blk_alen_nm` +75%、`blk_span_nm` −30.6%）判定
"形态学结论会变"。但"**哪些**结论受影响、哪些不受"**必须逐列过一遍**，
否则要么漏（把受影响的当安全）、要么过（把安全的当受影响）。

## 做法

对 `dry_swN128`（`--rank1-swap none`）与 `dry_swINV128`（`invariant`）
—— **同一次运行的两条臂、只差这一个开关** —— 逐列比**末行**：

* 差异 > 1% ⇒ **受影响（定量）**；
* 差异 ≤ 1% ⇒ 该列**不受选支影响**；
* 只在一边存在的列 ⇒ 标注。

⚠ **口径**：只比**共有列**；`wall_s` 之类纯计时列排除。
⚠ **这条只回答"量变不变"**，**不回答"哪个对"**（那是物理前提，`§102`）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
A = 'dry_swN128'
B = 'dry_swINV128'
# 纯计时/环境列（不参与物理比较）
SKIP = {'wall_s', 'wall', 't_step_s', 'eta_s', 'elapsed_s', 'git', 'tag', 'out'}
TOL = 0.01          # 1%


def load(tag):
    p = os.path.join(MB, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    return rows[0], rows[-1]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    ra = load(A)
    rb = load(B)
    if ra is None or rb is None:
        print('⚠ 两臂数据不全'); return 2
    h0a, ta = ra
    h0b, tb = rb
    print('=' * 108)
    print('_r158 —— 选支规则的影响面清单（`%s` vs `%s`，**只差 `--rank1-swap`**）' % (A, B))
    print('=' * 108)
    print('  比较口径：**末行**（step %s / %s）；差异 > %.0f%% 记为"受影响"。'
          % (ta.get('step'), tb.get('step'), 100 * TOL))
    print()
    cols = [c for c in h0a if c in h0b and c not in SKIP]
    aff, safe, nonnum = [], [], []
    for c in cols:
        va, vb = num(ta.get(c)), num(tb.get(c))
        if va is None or vb is None:
            sa, sb = str(ta.get(c, '')), str(tb.get(c, ''))
            if sa != sb:
                nonnum.append((c, sa, sb))
            continue
        den = max(abs(va), abs(vb), 1e-300)
        rel = abs(va - vb) / den
        (aff if rel > TOL else safe).append((c, va, vb, rel))
    print('  **A. 受影响（差异 > 1%%）—— %d 列**' % len(aff))
    print('  %-18s %-18s %-18s %s' % ('列', A, B, '相对差'))
    for c, va, vb, rel in sorted(aff, key=lambda t: -t[3]):
        mark = ''
        if c.startswith('blk_') or c in ('Vt',):
            mark = '   ← **块几何**'
        print('  %-18s %-18.6g %-18.6g %+.2f%%%s' % (c, va, vb, 100 * rel, mark))
    print()
    print('  **B. 不受影响（差异 ≤ 1%%）—— %d 列**' % len(safe))
    print('     %s' % ', '.join(c for c, _, _, _ in sorted(safe)))
    print()
    if nonnum:
        print('  **C. 非数值列且不同 —— %d 列**' % len(nonnum))
        for c, sa, sb in nonnum[:12]:
            print('     %-16s %-28s %s' % (c, sa[:28], sb[:28]))
        print()
    print('  ---- 判读 ----')
    print('  * 受影响列里凡带**方向含义**的（`blk_span_nm` = 沿 `n*`、`blk_alen_nm` = 沿 `a`、')
    print('    `tip/side/wide_sep_nm` 等）⇒ **它们的"物理归属"随选支规则改变**')
    print('    ⇒ 引用这些数字时**必须注明是哪条选支规则**（`§113` 第六节）。')
    print('  * 不受影响的列（计数 / 面积 / 平整度 / 界面完整性）⇒ **可以照用**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
