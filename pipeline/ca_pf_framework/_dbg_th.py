#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_th.py —— 定位 `_bk_cmp.robust_thickness` 读出 0 的原因。"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scipy import ndimage as ndi                            # noqa: E402

d = sys.argv[1]
snap = sorted([f for f in os.listdir(d) if f.startswith('snap_')])[-1]
z = np.load(os.path.join(d, snap))
reg = z['region']
dx = float(z['L']) / reg.shape[0]
n_hab = np.asarray(z['n_hab'], float)
print('snap=%s  N=%d  dx=%.2f nm  n_hab=%s' % (snap, reg.shape[0], dx * 1e9, n_hab))

st = np.zeros((3, 3, 3), bool)
for ax in range(3):
    for sh in (1, -1):
        sl = [1, 1, 1]
        sl[ax] = 0 if sh < 0 else 2
        st[tuple(sl)] = True
st[1, 1, 1] = True
print('structure 非零点数 =', int(st.sum()), '（应为 7）')

for k in (1, 2, 3):
    m = (reg == k)
    print('--- 场%d: 体素=%d' % (k, int(m.sum())))
    if not m.any():
        continue
    lab, n = ndi.label(m, structure=st)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    print('    分量数 n=%d  最大分量=%d' % (n, int(sz.max())))
    mm = (lab == int(np.argmax(sz))) if n > 1 else m
    idx = np.argwhere(mm)
    p = ((idx[:, 0] + 0.5) * n_hab[0] + (idx[:, 1] + 0.5) * n_hab[1]
         + (idx[:, 2] + 0.5) * n_hab[2]) * dx
    q = np.percentile(p, [0.5, 99.5])
    print('    p: min=%.1f max=%.1f nm   q=%s   厚度=%.1f nm'
          % (p.min() * 1e9, p.max() * 1e9, np.round(q * 1e9, 1),
             (q[1] - q[0]) * 1e9))
