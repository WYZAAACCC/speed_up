#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_1step.py --- 单步增量 vs |df|：直接给「界面位移 / 驱动」的符号与斜率。
Δf(1 步) 应随 |df| 单调增（界面速度 ∝ 驱动）。同时打印 dt 与 global dG_max。"""
import numpy as np
import windowB_surface as W
o0 = W.M2_twelve_variants(N=32, nstep=0, df=1e8, quiet=True)
f0 = o0['f_trans']
print('   seed f0 = %.6f' % f0)
print('   |df|/1e8   dt(s)      dG_max      f(1步)    df_1step   band')
for a in [0.3, 0.5, 1.0, 2.0, 4.0]:
    o = W.M2_twelve_variants(N=32, nstep=1, df=a * 1e8, quiet=True)
    g = o['g']
    dtv = 0.15 * g.dx / (g.M * max(getattr(g, 'dG_max', 0.0), 1e-30))
    print('   %8.1f  %.3e  %.4e  %9.6f  %+9.2e  %6d'
          % (a, dtv, getattr(g, 'dG_max', float('nan')), o['f_trans'],
             o['f_trans'] - f0, o['band']))
