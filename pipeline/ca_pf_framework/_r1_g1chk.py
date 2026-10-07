#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_g1chk.py --- ★★ 关键分诊：`mid250_ns4` 的"漂移"是不是 **G-1 盒壁**造成的？

为什么必须先查这个
------------------
`_r1_aniso.py` 显示 `mid250_ns4` 的 `ΔW:ΔL` 从 0.072 **升到** 0.114（晚期）。
若是**盒壁阻挡**（G-1：任一向跨度 > `--box-frac`·L ⇒ 形貌读数无效），
那么晚期窗口**本身就不可用**，"晚期=设计对比基准"的说法就站不住。

G-1 的定义在 `_r1_exp.py:41`：`box_touch=1` ⇒ 该步读数无效。
本脚本直接统计 `box_touch` / `ok` 两列随步的分布，并给出**未污染的可比窗口**。
"""
import csv
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')


def load(d):
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    every = 4.0
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            every = float(np.median(np.diff(mk)))
    rows = list(csv.DictReader(open(os.path.join(HERE, '_exp', d, 'series.csv'))))
    st = np.arange(len(rows), dtype=float) * every
    return st, rows


def fnum(r, k):
    v = r.get(k)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


for d in (sys.argv[1:] or ['mid250_ns4', 'mid250_base', 'mid192_ns4']):
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('%s: 无 CSV' % d); continue
    st, rows = load(d)
    print('=' * 100)
    print('%s   n=%d  step 0…%g' % (d, len(st), st[-1]))
    bt = np.array([fnum(r, 'box_touch') for r in rows])
    ok = np.array([fnum(r, 'ok') for r in rows])
    nc = np.array([fnum(r, 'ncomp') for r in rows])
    Lc = np.array([fnum(r, 'L_cal') for r in rows])
    print('   列是否可用：box_touch 非空 %d/%d ；ok 非空 %d/%d ；ncomp 非空 %d/%d'
          % (np.isfinite(bt).sum(), len(rows), np.isfinite(ok).sum(), len(rows),
             np.isfinite(nc).sum(), len(rows)))
    if np.isfinite(bt).any():
        bad = st[bt > 0]
        print('   **G-1 盒壁触发 %d 步**' % bad.size)
        if bad.size:
            print('      首次 step=%g（L_cal=%.0f nm）  末次 step=%g'
                  % (bad[0], Lc[bt > 0][0] * 1e9, bad[-1]))
            print('      触发步列表（前 20）：%s'
                  % ','.join(str(int(x)) for x in bad[:20]))
            print('   ⇒ 未污染的**最后可用窗口**：step ≤ %g' % (bad[0] - 4))
        else:
            print('   ⇒ ✅ 全程未触壁')
    if np.isfinite(ok).any() and (ok == 0).any():
        print('   `ok=0` 的步数：%d' % int((ok == 0).sum()))
    # 把 L_cal 与盒壁对比，看是否接近 --box-frac 限
    print('   L_cal 末值 = %.0f nm（盒子 24 µm，占比 %.0f%%）'
          % (Lc[-1] * 1e9, 100 * Lc[-1] * 1e6 / 24.0))
print('=' * 100)
