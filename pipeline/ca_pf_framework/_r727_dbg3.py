#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_dbg3.py —— 打印线性场上 `Mx` 的**逐点值**，直接看错位量。"""
import numpy as np
import sys
sys.path.insert(0, '.')
from _r727_lsq_exact import conv1

N = 8
dx = 1.0
c = np.arange(N, dtype=float) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
f = 3.0 * X          # ★ 只留 x 依赖 ⇒ S 应为 27*3x，Mx 应恒为 3*dx*9 = 27
K0 = np.array([1.0, 1.0, 1.0])
K1 = np.array([-1.0, 0.0, 1.0]) * dx

S = conv1(conv1(conv1(f, K0, 0), K0, 1), K0, 2)
Mx = conv1(conv1(conv1(f, K1, 0), K0, 1), K0, 2)
print('f = 3x  ⇒ 期望 S[i] = 27*3*i*dx ,  Mx 恒 = 3*dx*9 = 27')
print()
print(' i   f[i,0,0]   S[i,0,0]   期望S     Mx[i,0,0]  期望Mx')
for i in range(N):
    print('%2d %10.1f %10.1f %10.1f %10.1f %8.1f'
          % (i, f[i, 0, 0], S[i, 0, 0], 27 * 3 * i * dx, Mx[i, 0, 0], 27.0))
print()
print('Mx 唯一值 =', np.unique(np.round(Mx, 9)))
print()
# 单轴一步
b = conv1(f, K1, 0)
print('单轴 K1 后 b[i,0,0]（应恒 = 3*2*dx = 6）:')
print('  ', np.round(b[:, 0, 0], 6))
b2 = conv1(conv1(f, K1, 0), K0, 1)
print('再过 K0(轴1) 后（应恒 = 6*3 = 18）:')
print('  ', np.round(b2[:, 0, 0], 6))
b3 = conv1(b2, K0, 2)
print('再过 K0(轴2) 后（应恒 = 18*3 = 54）:')
print('  ', np.round(b3[:, 0, 0], 6))
