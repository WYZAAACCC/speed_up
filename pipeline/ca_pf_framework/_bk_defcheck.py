#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_defcheck.py —— 核验：**最简命令行**（默认路径）与已验的 `eng12` 是否逐位一致。

忽略 `wall_s`（墙钟，必然不同）与 `t_s`（同为整数倍 dt，应相同）。
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'wall_s'}


def load(tag, root):
    p = os.path.join(HERE, root, tag, 'series.csv')
    return list(csv.DictReader(open(p)))


a = load('eng_eng12', '_exp/_bk_eng')
b = load('dry_def1', '_exp/_bk_eng')
print('行数: eng12=%d  def1=%d' % (len(a), len(b)))
bad = []
for i, (x, y) in enumerate(zip(a, b)):
    for k in x:
        if k in SKIP:
            continue
        if x[k] != y[k]:
            bad.append((i, k, x[k], y[k]))
print('逐位比较（忽略 wall_s）：差异字段数 = %d' % len(bad))
for t in bad[:12]:
    print('   step=%s  %s: eng12=%r  def1=%r' % (a[t[0]]['step'], t[1], t[2], t[3]))
print('⇒ %s' % ('**逐位一致**' if not bad else '**有差异**（见上）'))
