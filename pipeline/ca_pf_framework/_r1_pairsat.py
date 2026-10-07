#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pairsat.py --- 核查一个异常：24 个非 rank-1 对的 `E_min` 是否**逐位相同**。

`_r1_pairgeo.py` 打印出「非 rank-1 类：min = max = 4.6261e+05，跨度 1.0×」。
两种可能，**必须分开**：

  (a) **真退化** —— 模型配对能量有饱和地板（例如 rank-1 分量可被某个 `n`
      完全消掉，剩下由共同的 rank-2 分量决定）。
  (b) **伪影** —— `argmin_normal` 在这 24 对上没找到盆地，返回了一个
      由网格/迭代决定的常数。

判据
----
  S-1 打印这 24 个值的**全精度**，看是否逐位相同。
  S-2 若是同一值，检查对应的 `n*` 是否也同一（真退化 ⇒ 允许不同 `n` 同能量；
      伪影 ⇒ 通常 `n` 也怪）。
  S-3 独立复算：用**另起一个种子**的 `argmin_normal`（`seed=99`，更大 `nsamp`）
      重跑这 24 对，若 `E_min` 不变 ⇒ (a)；若变小 ⇒ (b)，原值作废。
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from windowB_surface import _argmin_normal                      # noqa: E402
from T16_verify_rve import C, EPS0, NV                          # noqa: E402

E = [np.asarray(e, float) for e in EPS0]
rows = list(csv.DictReader(open(os.path.join(HERE, '_exp', 'paircorr.csv'))))
rk2 = []
for d in rows:
    k, l = int(d['k']), int(d['l'])
    s = np.linalg.svd(E[k - 1] - E[l - 1], compute_uv=False)
    if s[2] / s[0] > 1e-6:
        rk2.append((k, l, float(d['E_min']),
                    np.array([float(d['nx']), float(d['ny']), float(d['nz'])]),
                    float(s[2] / s[0])))

print('=' * 88)
print('S-1 24 个非 rank-1 对的 `E_min` 全精度：')
v = np.array([x[2] for x in rk2])
print('   n = %d' % len(v))
print('   min  = %.17e' % v.min())
print('   max  = %.17e' % v.max())
print('   极差 = %.3e   （相对极差 %.3e）' % (v.max() - v.min(),
                                             (v.max() - v.min()) / v.max()))
ident = (v.max() - v.min()) == 0.0
print('   ⇒ %s' % ('**逐位相同**' if ident else '**不完全相同**（有真实分散）'))

print('\nS-2 对应的 `n*`：')
for x in rk2:
    print('   V%-2d–V%-2d  σ₃/σ₁=%.4f  E_min=%.10e  n*=[%+.4f %+.4f %+.4f]'
          % (x[0], x[1], x[4], x[2], x[3][0], x[3][1], x[3][2]))

print('\nS-3 独立复算（`seed=99`，`nsamp=120000`）：')
bad = 0
for x in rk2:
    de = E[x[0] - 1] - E[x[1] - 1]
    n2, e2, cert = _argmin_normal(C, de, nsamp=120000, seed=99)
    chg = (e2 - x[2]) / max(abs(x[2]), 1e-300)
    if chg < -1e-9:
        bad += 1
    print('   V%-2d–V%-2d  原 %.10e → 新 %.10e  相对变化 %+.3e  n2=[%+.4f %+.4f %+.4f]'
          % (x[0], x[1], x[2], e2, chg, n2[0], n2[1], n2[2]))
print('\n   ⇒ 找到更低能量的对数：%d/%d  ⇒ %s'
      % (bad, len(rk2),
         '✅ 原值不是漏找盆地（支持 (a) 真退化）' if bad == 0
         else '⛔ 原 `E_min` 偏大（(b) 伪影），须作废并重算'))
print('=' * 88)
