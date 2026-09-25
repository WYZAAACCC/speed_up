#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_vcheck.py --- 隔离实验：界面速度定律 v = M*|df| 对 |df| 是否线性？
用 （平界面 slab、无弹性 C=None、无界面能 gamma=0、射线口径）。
若 v/(M df) 对全部 df 都 = 1 => 界面定律线性（RVE 里的反常不来自这里）。"""
import numpy as np
import _chk_w2 as W2

print('   df/1e8    df        v/(M df)   判定')
for a in [0.3, 0.5, 1.0, 2.0, 4.0, 8.0]:
    r, c = W2.run(N=48, dx=2e-9, M=1e-9, df=a * 1e8, nstep=40, verb=False)
    print('   %5.1f  %.3e   %8.4f   %s' % (a, a * 1e8, r, 'PASS' if abs(r - 1) < 0.02 else 'FAIL'))
