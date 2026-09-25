#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_pk.py --- 在同一 RVE 上对比：默认（pair_kernel=False）vs 按配对核（True）。
判据：f(|df|) 是否**单调增**（物理要求）+ 界面带是否健康。"""
import numpy as np
import windowB_surface as W

print('  pair_kernel  |df|/1e8  nstep   f_trans   band  ok')
for pk in (False, True):
    for a in [0.5, 1.0, 2.0]:
        kw = dict(pair_kernel=True, iface_band=2.0) if pk else {}
        out = W.M2_twelve_variants(N=32, nstep=60, df=a * 1e8, quiet=True, **kw)
        print('  %-11s %8.1f %6d %9.6f %6d %3d'
              % (str(pk), a, 60, out['f_trans'], out['band'], out['band_ok']))
