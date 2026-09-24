#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 第二级隔离：把 Stefan 关掉 / 把面-体交换关掉，分别看漂移来自哪一段。"""
import numpy as np
from windowB_surface import LevelSetMulti


def run(no_stefan=False, no_exchange=False, dt=4e-9, nstep=150, N=32, dx=2e-9):
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, -1e8],
                      reinit_every=20)
    if no_stefan:
        g._stefan = lambda reg0, reg1, k_part=0.6303: None
    if no_exchange:
        orig = g.update_Gamma
        g.update_Gamma = lambda dt, tau_ex=1e9, D_s=0.0: None
    g.seed_sphere(1, [0.5 * N * dx] * 3, 5 * dx)
    g.init_parent()
    g.c[:] = 0.036
    mb0, ms0 = g.totals()
    for _ in range(nstep):
        g.advance(dt)
        g.update_Gamma(dt)
    mb1, ms1 = g.totals()
    return abs((mb1 + ms1) - (mb0 + ms0)) / abs(mb0 + ms0)


print('---- M4 二级隔离 ----')
print('   全开（基准）        : %.3e' % run())
print('   关掉 Stefan         : %.3e' % run(no_stefan=True))
print('   关掉面-体交换       : %.3e' % run(no_exchange=True))
print('   两个都关            : %.3e' % run(no_stefan=True, no_exchange=True))
