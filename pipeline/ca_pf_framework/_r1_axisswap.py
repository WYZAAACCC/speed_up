#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_axisswap.py --- 正对照：单变体算例里 `series.csv` 与 `pervar.csv` 必须**逐位相同**。

原理
----
`series.csv` 的主量测走第 482 行正确绑定的
`measure(g, K0, a_ax, w_ax, n_hab, ...)`；
`pervar.csv` 走第 649 行的 `measure(g, K, *axes_of(g, K), ...)`。
`axes_of()` 返回 **(n_hab, w_ax, a_ax)**，而 `measure` 形参是 **(a_ax, w_ax, n_hab)**
⇒ 修复前 `a` 与 `n*` **对调** ⇒ 两表在 `L`/`T`/`LT_cal` 上**必然不同**；
修复后（`kv=1`、只有一个变体时）两表**应当逐位相同**。

判据
----
  G-1 两表在 `L_cal`/`W_cal`/`T_cal`/`LT_cal` 上的**最大相对差**；
      修复后应 `< 1e-12`（同一次测量、同一批浮点运算）。
  G-2 若 `L` 与 `T` 对调，则 `L_cal` 的相对差会**很大**（种子 T=320 nm vs L=2000 nm）。
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
d = sys.argv[1] if len(sys.argv) > 1 else '_axis_smoke'
DIR = os.path.join(HERE, '_exp', d)
sp = os.path.join(DIR, 'series.csv')
pp = os.path.join(DIR, 'pervar.csv')
if not (os.path.exists(sp) and os.path.exists(pp)):
    print('✗ 缺 series.csv 或 pervar.csv：%s' % DIR); sys.exit(1)

ser = list(csv.DictReader(open(sp)))
per = list(csv.DictReader(open(pp)))
# 只比较**唯一那个变体**的行（pervar 的第一个变体）
v0 = per[0]['variant']
sub = [r for r in per if r['variant'] == v0]
print('=' * 92)
print('%s ：series.csv(%d 行) vs pervar.csv 变体 %s(%d 行)'
      % (d, len(ser), v0, len(sub)))
print('-' * 92)
COLS = ['L', 'W', 'T', 'Lb', 'Wb', 'Tb', 'LWo', 'LTo', 'ncell']
n = min(len(ser), len(sub))
print('%-10s %14s %14s %14s' % ('列', '最大绝对差', '最大相对差', '判定'))
worst = 0.0
for c in COLS:
    try:
        a = np.array([float(ser[i][c]) for i in range(n)])
        b = np.array([float(sub[i][c]) for i in range(n)])
    except (ValueError, KeyError):
        print('%-10s %14s %14s %14s' % (c, '—', '—', '（列空/缺，跳过）'))
        continue
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        print('%-10s %14s %14s %14s' % (c, '—', '—', '（含非有限值，跳过）'))
        continue
    ad = float(np.max(np.abs(a - b)))
    rd = float(np.max(np.abs(a - b) / np.maximum(np.abs(a), 1e-300)))
    worst = max(worst, rd)
    print('%-10s %14.4e %14.4e %14s'
          % (c, ad, rd, '✅ 一致' if rd < 1e-12 else
             ('⚠ 差异小' if rd < 1e-6 else '⛔ **不一致（轴对调？）**')))
print('-' * 92)
print('G-1 最大相对差 = %.3e ⇒ %s'
      % (worst, '✅ **两表逐位一致 ⇒ 轴序已正确**' if worst < 1e-12
         else '⛔ 仍不一致'))
if worst >= 1e-6:
    print('   参考：`mid` 种子 L=2000 nm、T=320 nm ⇒ 若 `a`↔`n*` 对调，'
          '`L_cal` 会差约 %.1f 倍' % (2000.0 / 320.0))
print('=' * 92)
