#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L6dbg.py --- 定位融合核 vs 归档的**第一处差异**（不猜，直接打印中间量）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
import _r581_ufv as C

N = 8
DX = 62.5e-9
rng = np.random.default_rng(1)
phi = rng.normal(size=(N, N, N)) * 1e-8
V = [rng.normal(size=(N, N, N)) * 1e-9 for _ in range(3)]
for a in V:
    a[rng.random((N, N, N)) < 0.5] = 0.0

order = 1
for ax in range(3):
    Va = V[ax]
    if not np.any(Va):
        print('axis %d 跳过' % ax); continue
    # ---- 归档的单轴 ----
    dm = (phi - np.roll(phi, 1, axis=ax)) / DX
    dp = (np.roll(phi, -1, axis=ax) - phi) / DX
    ref = np.where(Va > 0, Va * dm, Va * dp)
    # ---- C 的单轴 ----
    out = np.zeros_like(phi)
    C.ufv_accum(phi, np.ascontiguousarray(Va), DX, ax, 1, order, out)
    neq = int(np.count_nonzero(ref != out))
    print('axis %d : 单轴不等 = %d' % (ax, neq))
    if neq:
        idx = np.argwhere(ref != out)[0]
        i, j, k = (int(z) for z in idx)
        print('   第一处 (i,j,k) = (%d,%d,%d)' % (i, j, k))
        print('   phi[here]      = %.17g' % phi[i, j, k])
        if ax == 0:
            nb = ((i - 1) % N, j, k); nf = ((i + 1) % N, j, k)
        elif ax == 1:
            nb = (i, (j - 1) % N, k); nf = (i, (j + 1) % N, k)
        else:
            nb = (i, j, (k - 1) % N); nf = (i, j, (k + 1) % N)
        print('   phi[prev]      = %.17g' % phi[nb])
        print('   phi[next]      = %.17g' % phi[nf])
        print('   Va             = %.17g' % Va[i, j, k])
        print('   dm  归档=%.17g   dp 归档=%.17g' % (dm[i, j, k], dp[i, j, k]))
        print('   ref=%.17g   C=%.17g' % (ref[i, j, k], out[i, j, k]))
        print('   Va>0 ? %s' % (Va[i, j, k] > 0))
        print('   ref 选的支: %s'
              % ('Va*dm' if Va[i, j, k] > 0 else 'Va*dp'))
        print('   Va*dm = %.17g' % (Va[i, j, k] * dm[i, j, k]))
        print('   Va*dp = %.17g' % (Va[i, j, k] * dp[i, j, k]))
        break
