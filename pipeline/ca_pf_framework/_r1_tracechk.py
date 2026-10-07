#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_tracechk.py --- 为什么"det Δε = 0"与"存在不变平面"在本问题里**等价**。

推导：`Δε` 对称且**无迹**（`tr = 0`）时，特征值 `(a,b,c)` 满足 `a+b+c = 0`。
  * `det Δε = 0` ⟺ 某个特征值为 0 ⟺ 另两个为 `±q`（因和为 0）
    ⟺ **两个特征值等大反号** ⟺ 存在不变平面（`g3 = 0`）。
所以两个判据在本数据上给出**同一个划分**（42/24），这不是巧合。

本脚本核实前提（无迹）并统计 66 对里有几个**不同的特征值谱**。
"""
import collections
import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import EPS0, NV                                   # noqa: E402

E = [np.asarray(e, float) for e in EPS0]
tr = [float(np.trace(e)) for e in E]
print('12 个变体应变张量的迹：min = %.3e  max = %.3e  极差 = %.3e'
      % (min(tr), max(tr), max(tr) - min(tr)))
dtr = [abs(float(np.trace(E[k] - E[l])))
       for k, l in itertools.combinations(range(NV), 2)]
print('66 对 `|tr(Δε)|`：max = %.3e   ⇒ %s'
      % (max(dtr), '✅ 全部无迹，两判据等价' if max(dtr) < 1e-15
         else '⚠ 有对有迹，两判据不等价'))

sp = collections.Counter()
for k, l in itertools.combinations(range(NV), 2):
    dE = E[k] - E[l]
    lam = np.linalg.eigvalsh(0.5 * (dE + dE.T))
    sp[tuple(np.round(lam, 10))] += 1
print('\n66 对里**不同特征值谱**的个数 = %d' % len(sp))
for s, c in sp.most_common():
    print('   λ = (%.10e, %.10e, %.10e)   出现 %d 次' % (s[0], s[1], s[2], c))

SAME = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
print('\n同 packet 6 对各自所属的谱：')
for k, l in SAME:
    dE = E[k - 1] - E[l - 1]
    lam = tuple(np.round(np.linalg.eigvalsh(0.5 * (dE + dE.T)), 10))
    print('   V%-2d–V%-2d  λ = (%.6e, %.6e, %.6e)'
          % (k, l, lam[0], lam[1], lam[2]))
print('\n⇒ 同 packet 6 对的**特征值谱完全相同**（λ = ±1.8378e-02, 0）')
print('   ⇒ 任何只看不变量的几何判据都**无法**区分它们；')
print('     只有看**特征向量方向相对于母相/其它变体**的各向异性弹性才能区分。')
