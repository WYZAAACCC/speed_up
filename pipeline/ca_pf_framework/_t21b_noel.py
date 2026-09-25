#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_noel.py --- 隔离实验：**关掉弹性**（C=None）的 12 变体 RVE。
目的：把 f(|df|) 的反常（低驱动长得更快）归因到"化学驱动路径"还是"弹性相互作用"。
若关掉弹性后 f 随 |df| **单调增** => 反常来自弹性项；否则来自化学/推进路径。"""
import numpy as np
import windowB_surface as W

print('   |df|/1e8  nstep   f_trans   band  ok')
for a in [0.5, 1.0, 2.0]:
    out = W.M2_twelve_variants(N=32, nstep=60, df=a * 1e8, C_override='off',
                               quiet=True)
    print('   %8.1f %6d %9.6f %6d %3d' % (a, 60, out['f_trans'], out['band'], out['band_ok']))
