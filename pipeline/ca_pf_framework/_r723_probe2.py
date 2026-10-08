#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r723_probe2.py —— 精确复现 `analytic()` 里出错的赋值，打印每一步形状。"""
import numpy as np

N = 48
dx = 0.0625e-6
c = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
ctr = np.array([X.mean(), Y.mean(), Z.mean()])
bx = np.abs(X - ctr[0]); by = np.abs(Y - ctr[1]); bz = np.abs(Z - ctr[2])
rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
R = 0.25 * N * dx
d = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
which = np.argmax(np.stack([bx, by, bz], -1), -1)
print('d.dtype =', d.dtype, ' d.shape =', d.shape)
print('which.shape =', which.shape)
nb = np.zeros_like(X)
print('STEP0 nb.shape =', nb.shape, 'nb[...,0].shape =', nb[..., 0].shape)
comp = 0
m = (which == 0)
print('m.shape =', m.shape, 'm.sum() =', m.sum())
rhs = np.where(m, np.sign(d[..., comp]), nb[..., comp])
print('rhs.shape =', rhs.shape)
try:
    nb[..., comp] = rhs
    print('STEP1 OK  nb.shape =', nb.shape)
except Exception as e:
    print('STEP1 FAIL:', e)
# 改用显式 3D 构造
nb3 = np.zeros(X.shape + (3,))
print('nb3.shape =', nb3.shape, 'nb3[...,0].shape =', nb3[..., 0].shape)
nb3[..., comp] = rhs
print('STEP2 OK  nb3[...,0].max =', nb3[..., 0].max())
