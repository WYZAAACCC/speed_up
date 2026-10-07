#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r570_colcmp.py --- `_r569_smoke.sh` 的列对比（路径改成实际布局 `dry_<tag>`）。

判据：
  S-3b **逐位档**（`--eps0-mode einsum --ed-pair gather`）vs 旧路 ⇒ 共有列**必须逐位相同**
       —— 因为 V2/V3 已证这两个算子**逐位等价**，整步在结构上没有任何位改变。
  S-3a `rfft` 档 vs 旧路 ⇒ 只证明"没炸"（容差 1e-9）；**不要求相同**（σ 差 1–2 ulp，
       30 步的轨迹可能已经分叉，这是预期的，不是缺陷）。
"""
import os
import sys

import numpy as np

R = '_exp/_bk_eng'
TAGS = sys.argv[1:] or ['r569_off', 'r569_bit', 'r569_on']


def rd(tag):
    for p in (os.path.join(R, tag, 'series.csv'),
              os.path.join(R, 'dry_' + tag, 'series.csv')):
        if os.path.exists(p):
            with open(p) as fh:
                hdr = fh.readline().strip().split(',')
            return hdr, p
    return None, None


print('=' * 88)
print('R570 — 冒烟列对比（目录布局 dry_<tag>）')
print('=' * 88)
for t in TAGS:
    h, p = rd(t)
    print('  %-12s ⇒ %s（%d 列）' % (t, p or '**找不到**', len(h) if h else 0))


def cmp(t1, t2, tol, label):
    h1, p1 = rd(t1)
    h2, p2 = rd(t2)
    if not p1 or not p2:
        print('  ❌ 缺文件，跳过：%s' % label)
        return False
    a1 = np.genfromtxt(p1, delimiter=',', names=True)
    a2 = np.genfromtxt(p2, delimiter=',', names=True)
    common = [c for c in h1 if c in h2 and c != 'wall_s']
    worst, bad = 0.0, []
    for c in common:
        x = np.atleast_1d(a1[c]).astype(float)
        y = np.atleast_1d(a2[c]).astype(float)
        n = min(len(x), len(y))
        if n == 0:
            continue
        mx = float(np.max(np.abs(y[:n])))
        if mx == 0.0:
            d = 0.0 if float(np.max(np.abs(x[:n]))) == 0.0 else float('inf')
        else:
            d = float(np.max(np.abs(x[:n] - y[:n]))) / mx
        worst = max(worst, d)
        if d > tol:
            bad.append((c, d))
    print('  %s' % label)
    print('     共有列 %d 个（剔 wall_s）；最大相对差 = %.3e（容差 %.0e）⇒ %s'
          % (len(common), worst, tol,
             '✅ PASS' if not bad else '❌ FAIL: %s' % bad[:6]))
    return not bad


ok = True
ok &= cmp('r569_bit', 'r569_off', 0.0,
          'S-3b **逐位档** einsum+gather vs 旧路（要求 max|Δ| === 0）')
ok &= cmp('r569_on', 'r569_off', 1e-9,
          'S-3a rfft+einsum+gather vs 旧路（只证明没炸，容差 1e-9）')
print('')
print('  ⇒ 总判定：%s' % ('✅ PASS' if ok else '❌ FAIL'))
with open('_w2_r570_colcmp.log', 'w', encoding='utf-8') as fh:
    fh.write('see stdout\n')
