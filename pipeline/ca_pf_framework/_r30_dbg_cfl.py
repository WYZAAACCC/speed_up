#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_dbg_cfl.py —— 调试：平界面 20 步后 d 剖面与零穿越。"""
import os
import sys
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np
import windowB_surface as W
from T16_verify_rve import C, EPS0, MOB, DF
import _r30_ctl_cfl as K

g = K.make(gamma=0.0)
dt = 0.15 * K.DX / (MOB * DF)
for it in range(21):
    if it:
        g.advance(dt, aniso=0.0, band_cells=20, mob_beta=0.0, adv_grad='proj2')
    d = (g.phi[0] - g.phi[1])[K.N // 2, K.N // 2, :]
    cr = np.flatnonzero(d[:-1] * d[1:] < 0)
    pos = []
    for i in cr:
        f = d[i] / (d[i] - d[i + 1])
        pos.append((i + 0.5 + f) * K.DX - 0.5 * K.L)
    if it in (0, 1, 5, 10, 20):
        print('it=%2d  零穿越 z(nm)=%s   d[14:19]=%s'
              % (it, ['%.1f' % (p * 1e9) for p in pos],
                 np.array2string(d[14:19] * 1e9, precision=1)))
print('末步 dG_max=%.4e' % g.dG_max)
