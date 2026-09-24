#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 _stefan 内部逐步探针：找守恒漏发生在哪一步、哪条分支。"""
import numpy as np
from windowB_surface import LevelSetMulti

N, dx, dt = 32, 2e-9, 4e-9
g = LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, -1e8], reinit_every=20)
g.seed_sphere(1, [0.5 * N * dx] * 3, 5 * dx)
g.init_parent()
g.c[:] = 0.036

dbg = {'log': [], 'step': 0, 't0': 0.0}
orig = g._stefan


def wrapped(reg0, reg1, k_part=0.6303):
    dbg['step'] += 1
    return orig(reg0, reg1, k_part, dbg=dbg)


g._stefan = wrapped
mb0, ms0 = g.totals()
for k in range(60):
    g.advance(dt)
    g.update_Gamma(dt)
mb1, ms1 = g.totals()
print('总漂移 = %.3e' % (abs((mb1 + ms1) - (mb0 + ms0)) / abs(mb0 + ms0)))
print('%-6s %-12s %14s %8s' % ('step', 'branch', 'delta(mol)', 'n_swept'))
rows = sorted(dbg['log'], key=lambda r: -abs(r[2]))[:12]
for st, br, d, ns in rows:
    print('%-6d %-12s %14.3e %8d' % (st, br, d, ns))
s = sum(r[2] for r in dbg['log'])
print('探针累计 delta 之和 = %.3e' % s)
