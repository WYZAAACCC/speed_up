#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pairgeo.py --- 把 66 对按 **Hadamard rank-1 类** 分组，看这一比特值多少。

`_r1_svcheck.py` 发现：66 对里 42 对 `σ₃ = 0`（真 rank-1），24 对 `σ₃ > 0`。
`_r1_paircorr.py` 发现：同 packet 的 6 对**全部** rank-1，而它们的
`E_min` 跨 39 倍。所以关键问题是：

  **rank-1 这一比特能把 `E_min` 缩到多窄？**
    * 若 rank-1 类内部 `E_min` 仍然跨很多量级 ⇒ rank-1 只是**极弱的筛子**，
      不能当相容性度量 —— 这也**同时解释了**为什么经典文献的 rank-1 判据
      在这里没有分辨力（它对同 packet 的 6 对**全判为相容**）。
    * 若 rank-1 类内部 `E_min` 很窄 ⇒ rank-1 是个好判据，我的结论要反过来写。

本脚本只读 `_exp/paircorr.csv`（`_r1_paircorr.py` 的产物）+ `EPS0` 重算 σ₃。
"""
import csv
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import EPS0, NV                                   # noqa: E402

E = [np.asarray(e, float) for e in EPS0]
CSV = os.path.join(HERE, '_exp', 'paircorr.csv')

rows = []
with open(CSV) as f:
    for d in csv.DictReader(f):
        k, l = int(d['k']), int(d['l'])
        dU = E[k - 1] - E[l - 1]
        s = np.linalg.svd(dU, compute_uv=False)
        rows.append((k, l, float(s[2] / s[0]), float(d['E_min']),
                     float(d['r_sym'])))
assert len(rows) == 66, len(rows)

s3 = np.array([x[2] for x in rows])
em = np.array([x[3] for x in rows])
r1 = s3 < 1e-6
print('=' * 88)
print('66 对按 Hadamard rank-1 类分组（读 `_exp/paircorr.csv`）')
print('=' * 88)
print('   rank-1 类（σ₃=0）：%2d 对      最大 σ₃/σ₁ = %.3e'
      % (int(r1.sum()), float(s3[r1].max()) if r1.any() else 0.0))
print('   非 rank-1 类      ：%2d 对      最小 σ₃/σ₁ = %.3e'
      % (int((~r1).sum()), float(s3[~r1].min()) if (~r1).any() else 0.0))

SAME = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
_S = set(SAME)
same = np.array([(x[0], x[1]) in _S for x in rows])

print('\n   %-22s %5s %12s %12s %10s' % ('域', 'n', 'E_min 最小', 'E_min 最大', '跨度'))
for tag, m in (('全部 66 对', np.ones(66, bool)),
               ('  └ rank-1 类', r1),
               ('  └ 非 rank-1 类', ~r1),
               ('同 packet 6 对', same),
               ('  其中 rank-1', same & r1),
               ('跨 packet 60 对', ~same),
               ('  其中 rank-1', (~same) & r1),
               ('  其中非 rank-1', (~same) & (~r1))):
    n = int(m.sum())
    if n == 0:
        print('   %-22s %5d  —' % (tag, 0))
        continue
    lo, hi = float(em[m].min()), float(em[m].max())
    print('   %-22s %5d %12.4e %12.4e %9.1f×'
          % (tag, n, lo, hi, hi / max(lo, 1e-300)))

print('\n   ⇒ 结论：')
lo, hi = float(em[r1].min()), float(em[r1].max())
print('     `rank-1` 类内部 `E_min` 跨 **%.1f 倍（%.0f 个量级）**。' %
      (hi / max(lo, 1e-300), np.log10(hi / max(lo, 1e-300))))
print('     ⇒ `rank-1` 只把候选缩到一半左右（42/66），**不是相容性度量**；')
print('       经典 rank-1 判据对**同 packet 的 6 对全部判为相容**，')
print('       而模型给它们的 `E_min` 跨 39 倍 ⇒ **判据在这里没有分辨力**。')
print('     ⇒ 必须用模型自己的 `E_min`（各向异性微弹性）排序。')
print('=' * 88)
