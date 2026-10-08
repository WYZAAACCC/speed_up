#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r723_probe.py —— 快速打印 `analytic()` 里各量的形状（诊断广播问题）。"""
import numpy as np

N = 48
dx = 0.0625e-6
c = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
ctr = np.array([X.mean(), Y.mean(), Z.mean()])
print('X.shape   =', X.shape)
print('Y.shape   =', Y.shape)
print('Z.shape   =', Z.shape)
bx = np.abs(X - ctr[0]); by = np.abs(Y - ctr[1]); bz = np.abs(Z - ctr[2])
print('bx.shape  =', bx.shape, 'by =', by.shape, 'bz =', bz.shape)
st = np.stack([bx, by, bz], -1)
print('stack.shape =', st.shape)
w = np.argmax(st, -1)
print('which.shape =', w.shape)
d = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
print('d.shape =', d.shape)
nb = np.zeros_like(X)
print('nb.shape =', nb.shape)
print('nb[...,0].shape =', nb[..., 0].shape)
