#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 差异归因：把重初始化关掉/换强度，看看守恒漂移从哪里来。
   若 M4(reinit_every=0) 很小 ⇒ 泄漏在**重初始化路径**（它微移亚胞界面、触发 Stefan/Γ 记账）；
   若仍很大 ⇒ 泄漏在 Stefan/Γ 记账本身。"""
import numpy as np
from windowB_surface import LevelSetMulti


def run(reinit_every, iters=None, dt=4e-9, nstep=150, N=32, dx=2e-9):
    g = LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, -1e8],
                      reinit_every=reinit_every)
    if iters is not None:
        g.sussman_reinit = (lambda phi, _i=iters, _g=g: _g._sussman_fixed(phi, _i))
    g.seed_sphere(1, [0.5 * N * dx] * 3, 5 * dx)
    g.init_parent()
    g.c[:] = 0.036
    mb0, ms0 = g.totals()
    for _ in range(nstep):
        g.advance(dt)
        g.update_Gamma(dt)
    mb1, ms1 = g.totals()
    return abs((mb1 + ms1) - (mb0 + ms0)) / abs(mb0 + ms0)


print('---- M4 归因实验 ----')
print('   重初始化每 20 步（当前默认，iters=30）: 漂移 = %.3e' % run(20))
print('   完全关闭重初始化                     : 漂移 = %.3e' % run(0))
print('   重初始化每 5 步（更频繁）            : 漂移 = %.3e' % run(5))
