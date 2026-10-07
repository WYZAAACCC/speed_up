#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_alignchk.py --- 诊断 `align_deg`（分量主轴 vs `a`）与"沿 `a` 的跨度"为何矛盾。

现象
----
`equi192_ns4` 的日志说「定标 L/W/T **5815**/1416/1045 nm」⇒ **沿 `a` 的跨度最大**；
但 `align_deg`（分量 PCA 主轴与 `a` 的夹角）**末态 85.89°** ⇒ 主轴**几乎垂直于 `a`**。
两件事**不可能同时为真**（除非分量非凸/被碎屑主导）⇒ 必有一处量具错。

本脚本从 `series.csv` 里把这两列**并排**打出来（时间序列），看它们何时、以什么方式矛盾：
  * 若 `align_deg` 在 `nc=1` 时仍是 86°，而 `L_cal` 同时是最大跨度 ⇒ **`align_deg` 量具错**；
  * 若 86° 只出现在 `nc` 很大（碎屑多）的步 ⇒ 是**中位数被碎屑主导**，量具本身没错。
"""
import csv
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


d = sys.argv[1] if len(sys.argv) > 1 else 'equi192_ns4'
sp = os.path.join(HERE, '_exp', d, 'series.csv')
rows = list(csv.DictReader(open(sp)))
lp = os.path.join(HERE, '_exp', d, 'log.txt')
every = 4.0
if os.path.exists(lp):
    mk = [int(m.group(1)) for m in
          (PAT.match(l) for l in open(lp, errors='replace')) if m]
    if len(mk) > 2:
        every = float(np.median(np.diff(mk)))

print('=' * 100)
print('%s ：`align_deg`（主轴夹角）与三向跨度（**都是 nm**）并排' % d)
print('%8s %5s %10s %10s %10s %10s %9s %s'
      % ('step', 'nc', 'L(沿a)', 'W', 'T', 'align°', '最大向', '矛盾?'))
print('-' * 100)
bad = []
for i, r in enumerate(rows):
    st = i * every
    if i < max(len(rows) - 22, 0):
        continue
    L = fnum(r, 'L_cal') * 1e9
    W = fnum(r, 'W_cal') * 1e9
    T = fnum(r, 'T_cal') * 1e9
    al = fnum(r, 'align_deg')
    nc = fnum(r, 'ncomp')
    big = 'L' if (L >= W and L >= T) else ('W' if W >= T else 'T')
    contra = ''
    if np.isfinite(al) and np.isfinite(L):
        # 若主轴与 a 夹角 >60° 却又说 L 最大 ⇒ 矛盾
        if al > 60 and big == 'L':
            contra = '⚠ 矛盾'
            bad.append(st)
    print('%8g %5s %10.0f %10.0f %10.0f %9.2f %9s %s'
          % (st, ('%g' % nc) if np.isfinite(nc) else '—', L, W, T, al, big,
             contra))
print('-' * 100)
if bad:
    print('⇒ **矛盾出现在 step %s**：`align_deg>60°` 同时"沿 a 的跨度最大"'
          % ','.join('%g' % x for x in bad[:10]))
    print('   ⇒ 两列**不可能同时为真** ⇒ 其中一个是错的，须查清（见脚本头注释的分诊）。')
else:
    print('⇒ 本窗口内无矛盾（`align_deg` 高时 `nc` 也大 ⇒ 更可能是**碎屑主导中位数**）。')
print('=' * 100)
