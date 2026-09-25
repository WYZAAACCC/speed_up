#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_mat.py --- 2x2 隔离矩阵：gamma(界面能) x 弹性，都在 df=-1e8 / nstep=60。
判据：哪个格子里晶核会长（f > f_seed=0.0987）？哪个格子里会整体消失（f=0, band=0）？"""
import windowB_surface as W
print('   gamma  elasticity   f_trans      band  ok')
for gm in (0.0, 0.15):
    for ce, tag in (('off', 'off '), (None, 'on  ')):
        out = W.M2_twelve_variants(N=32, nstep=60, df=-1e8, gamma=gm,
                                  C_override=ce, quiet=True)
        print('   %5.2f  %s        %9.6f  %6d %3d'
              % (gm, tag, out['f_trans'], out['band'], out['band_ok']))
