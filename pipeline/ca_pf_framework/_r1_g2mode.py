#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_g2mode.py --- ★★ G-2 守卫在**多核**算例上是否被误用？

G-2 的定义（`_r1_exp.py:42`）：「目标变体分成 >1 个连通分量 ⇒ `max−min` 被碎片绑架」。
这个定义**只对单核算例成立**。多核算例（实验 4/5/6/7）里，
目标变体**本来就**有 `nseed` 个连通分量 —— 那正是我们要的状态，不是污染。

`_r1_armhealth.py` 的表已经显示：`e4_lath6` 113/120 步、`e5_equi6` 97/98、
`e6_mid6` 111/125、`e7_selfac` **27/27** 步都打 G-2。

本脚本核实「那些步的 `ncomp` 到底等于几」：
  * 若 ≈ `nseed`（6）⇒ **守卫用错了**，G-2 在多核臂上**恒真** ⇒ 必须按模式区分；
  * 若远大于 `nseed` ⇒ 真有额外碎片核，G-2 是对的。
"""
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = ['e4_lath6', 'e5_equi6', 'e6_mid6', 'e7_selfac',
        'mid250_ns4', 'mid192_ns4']


def fnum(r, k):
    try:
        return float(r[k])
    except (TypeError, ValueError, KeyError):
        return float('nan')


print('=' * 104)
print('%-14s %8s %-26s %-26s %s'
      % ('算例', 'nseed', 'ncomp 取值(n, 次数)', 'nsig 取值(n, 次数)', 'debris 末值'))
print('=' * 104)
for d in ARMS:
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('%-14s 无 CSV' % d); continue
    rows = list(csv.DictReader(open(p)))
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    nseed = None
    if os.path.exists(mp):
        try:
            nseed = json.load(open(mp)).get('nseed')
        except Exception:                                        # noqa: BLE001
            pass
    nc = [fnum(r, 'ncomp') for r in rows]
    ns = [fnum(r, 'nsig') for r in rows]
    dc = [fnum(r, 'debris') for r in rows]

    def cnt(v):
        v = [x for x in v if np.isfinite(x)]
        if not v:
            return '（空）'
        u, c = np.unique(v, return_counts=True)
        return ', '.join('%g×%d' % (a, b) for a, b in zip(u, c))[:26]
    print('%-14s %8s %-26s %-26s %s'
          % (d, nseed, cnt(nc), cnt(ns),
             ('%.4f' % dc[-1]) if np.isfinite(dc[-1]) else '（空）'))
print('=' * 104)
print('判读：')
print('  * `nseed=1` 的臂：`ncomp>1` ⇒ 真的出现了第 2 个分量 ⇒ G-2 **用对了**。')
print('  * `nseed=6` 的臂：若 `ncomp` 就是 6（= nseed）⇒ G-2 **恒真、用错了**，')
print('    它把"我们刻意放的 6 个核"当成了污染 ⇒ 这些臂的形貌读数被**全部误判为无效**。')
print('=' * 104)
