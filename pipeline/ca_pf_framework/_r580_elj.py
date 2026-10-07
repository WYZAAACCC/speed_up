#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r580_elj.py --- 把 `bis_base` / `bis_pfphi` / `bis_all` 的 `E_el_J` **逐行原始值**打出来。

## 为什么先看绝对值
`_r580_bisect_cmp.py` 用的判据是 `max|Δ| / max|ref|`。若 `E_el_J` 在时间上**穿过 0**
（本项目已多次遇到：step 0 的 `E_el_J = 0` 是"还没算"），相对判据会被**小分母放大**。
⇒ **在下任何结论前，先看绝对值**（`AGENTS §3.20`：能从原始读数看的，不要从比值反推）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '_exp', '_bk_eng')


def rd(t):
    p = os.path.join(R, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)


ARMS = ['bis_base', 'bis_pfphi', 'bis_all']
data = {}
for t in ARMS:
    h, a = rd(t)
    if a is None:
        print('  缺 %s' % t)
        continue
    data[t] = a

if 'bis_base' not in data:
    raise SystemExit(1)

print('  %-8s %-16s %-16s %-16s %s'
      % ('step', 'base', 'pfphi', 'all', '|Δ|(pfphi-base)'))
print('  ' + '-' * 78)
n = len(np.atleast_1d(data['bis_base']['E_el_J']))
for i in range(n):
    b = float(np.atleast_1d(data['bis_base']['E_el_J'])[i])
    p = float(np.atleast_1d(data['bis_pfphi']['E_el_J'])[i]) if 'bis_pfphi' in data else float('nan')
    a = float(np.atleast_1d(data['bis_all']['E_el_J'])[i]) if 'bis_all' in data else float('nan')
    print('  %-8d %-16.8e %-16.8e %-16.8e %.3e' % (i, b, p, a, abs(p - b)))

print()
print('  ── 也看看 `Vt`（广延量，反应"转变了多少"）是否一致 ──')
for k in ('Vt', 'f_var', 'nslab_n', 'nf3'):
    if k not in data['bis_base'].dtype.names:
        print('    （无列 %s）' % k)
        continue
    v = [float(np.atleast_1d(data[t][k])[-1]) if t in data else float('nan')
         for t in ARMS]
    print('    %-10s 末值： %s' % (k, '  '.join('%s=%.8e' % (t, x) for t, x in zip(ARMS, v))))
