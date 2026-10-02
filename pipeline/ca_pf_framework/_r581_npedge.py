#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_npedge.py --- 探针：把 numpy 在**边缘值**上的真实语义打出来（**不许猜**）。

为什么要它：C 扩展要逐位复刻 numpy，而 `np.sign(±0.0)` 与 `np.minimum` 的 NaN 行为
是**最容易记错**的两条。本轮第一版 C 就按"`np.sign(-0.0)` 返回 `-0.0`"写，
结果被边缘用例判据抓到（`(-0.0,-0.0)` 处 numpy 给 `+0.0`、C 给 `-0.0`）。
⇒ 先把真值打出来，再改 C。
"""
import numpy as np

print('=' * 78)
print('numpy 边缘语义探针  numpy=%s' % np.__version__)
print('=' * 78)


def bits(x):
    return hex(np.float64(x).view(np.uint64))


print('\n── np.sign ──')
for v in (0.0, -0.0, 1.0, -1.0, np.inf, -np.inf, np.nan, 5e-324, -5e-324):
    r = np.sign(v)
    print('  sign(%-10r) = %-10r  符号位=%s' % (v, float(r), np.signbit(r)))

print('\n── np.minimum / np.maximum 的 NaN 传播 ──')
for x, y in ((np.nan, 1.0), (1.0, np.nan), (np.nan, np.nan),
             (np.inf, 1.0), (-np.inf, 1.0), (0.0, -0.0), (-0.0, 0.0)):
    print('  minimum(%-8r, %-8r) = %-10r  max = %-10r'
          % (x, y, float(np.minimum(x, y)), float(np.maximum(x, y))))

print('\n── numpy `!=` 对 NaN 的行为（**量具陷阱**）──')
a = np.array([np.nan, 1.0, 0.0])
b = np.array([np.nan, 1.0, 0.0])
print('  count_nonzero(a != b) = %d  ← NaN 位置被算成"不等"!'
      % int(np.count_nonzero(a != b)))
print('  array_equal(a, b) = %s' % np.array_equal(a, b))
print('  array_equal(a, b, equal_nan=True) = %s'
      % np.array_equal(a, b, equal_nan=True))

print('\n── 复合：np.minimum 的 NaN 会不会在 _minmod 里"被 sign 掩盖" ──')
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_surface as W
a = np.array([np.nan]); b = np.array([1.0])
print('  _minmod(nan, 1.0)          = %r' % float(W._minmod(a, b)[0]))
aa, bb = np.abs(a), np.abs(b)
fmin_like = np.where(np.isnan(aa), bb, np.minimum(aa, bb))
print('  sign(nan)+sign(1)          = %r'
      % float((np.sign(a) + np.sign(b))[0]))
print('  ⇒ 用 fmin 语义算的 m       = %r ⇒ 乘积 = %r'
      % (float(fmin_like[0]),
         float((0.5 * (np.sign(a) + np.sign(b)) * fmin_like)[0])))
print('  ⇒ **sign(NaN) 已经给了 NaN ⇒ 乘积无论 m 是什么都是 NaN**')
print('     ⇒ 「fmin 丢 NaN 传播」这条负对照在本函数上**不可观测**（不是好对照）')
