#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_cmp.py —— 直接在 `_bk_cmp` 的调用侧打印中间量。"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_cmp as CMP                                          # noqa: E402
import _bk_measure as BM                                       # noqa: E402

d = os.path.join(HERE, sys.argv[1])
s = CMP.last_snap(d)
z = np.load(s)
reg = z['region']
dx = float(z['L']) / reg.shape[0]
n_hab = np.asarray(z['n_hab'], float)
vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
r = BM.measure_state(reg, dx, n_hab, z['w_ax'], z['a_ax'], vmap)
present = [k for k in sorted(vmap) if r['vol_%d' % k] > 0]
print('present =', present)
print('runs    =', r['runs'], ' nslab =', r['nslab_n'])
for k in present:
    t = CMP.robust_thickness(reg, dx, n_hab, k)
    print('  k=%d  vol=%.5g m³  n_k=%.1f nm  robust_thickness=%.2f nm  (type=%s)'
          % (k, r['vol_%d' % k], r['n_%d' % k] * 1e9, t, type(t).__name__))
th = {k: CMP.robust_thickness(reg, dx, n_hab, k) for k in present}
print('th =', th)
print("join =", '/'.join('%.0f' % th[k] for k in present))
