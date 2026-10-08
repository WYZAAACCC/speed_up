#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_dbg2.py —— 用**线性场**孤立测 `conv1` 与一阶矩（线性场上一切应精确）。"""
import numpy as np
import sys
sys.path.insert(0, '.')
from _r727_lsq_exact import conv1, sep_moments

N = 8
dx = 1.0
c = np.arange(N, dtype=float) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
# 线性场 f = 3x + 5y - 2z  ⇒ 梯度 (3,5,-2)，一阶矩应为 3*dx*9 = 27（每轴 9 个 yz 组合）
f = 3.0 * X + 5.0 * Y - 2.0 * Z
print('f[0,0,0]=%.1f  f[1,0,0]=%.1f' % (f[0, 0, 0], f[1, 0, 0]))

K0 = np.array([1.0, 1.0, 1.0])
K1 = np.array([-1.0, 0.0, 1.0]) * dx

print('\n--- conv1 单轴测试（沿 ax=0）---')
a = conv1(f, K0, 0)
b = conv1(f, K1, 0)
print('K0 结果 shape=%s  期望 f 沿 x 的 3 点窗和' % (a.shape,))
print('  a[1,0,0]=%.1f  手算 f[0,0,0]+f[1,0,0]+f[2,0,0]=%.1f'
      % (a[1, 0, 0], f[0, 0, 0] + f[1, 0, 0] + f[2, 0, 0]))
print('K1 结果 b[1,0,0]=%.1f  手算 f[2,0,0]-f[0,0,0]=%.1f'
      % (b[1, 0, 0], f[2, 0, 0] - f[0, 0, 0]))
print('  ⇒ K1 正确? %s' % (abs(b[1, 0, 0] - (f[2, 0, 0] - f[0, 0, 0])) < 1e-12))

print('\n--- 三轴张量积 (K1,K0,K0) ---')
Mx = conv1(conv1(conv1(f, K1, 0), K0, 1), K0, 2)
exp = (f[2, 0, 0] - f[0, 0, 0]) * 9      # 9 个 (y,z) 组合
print('Mx[1,0,0]=%.3f  期望=%.3f' % (Mx[1, 0, 0], exp))
print('  逐点 Mx 是否恒为 3*dx*9=%.1f ?  min=%.3f max=%.3f'
      % (3.0 * dx * 9, Mx.min(), Mx.max()))

print('\n--- sep_moments 全量 ---')
S, Mx2, My2, Mz2 = sep_moments(f, dx)
print('S   in [%.1f, %.1f]  (期望 27 点窗和，随位置线性变)' % (S.min(), S.max()))
for nm, arr, g in (('Mx', Mx2, 3.0), ('My', My2, 5.0), ('Mz', Mz2, -2.0)):
    print('%s  in [%.4f, %.4f]  期望恒为 %.1f*%.0f*9=%.1f'
          % (nm, arr.min(), arr.max(), g, dx, g * dx * 9))
