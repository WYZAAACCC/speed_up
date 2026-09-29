#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_dbg_col.py —— 为什么 6 层堆叠的柱剖面里 `runs` 少了场 4？"""
import os
import sys
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np
import _bk_measure as BM
sys.path.insert(0, _HERE)
import _r30_ctl_measure as A

reg = A.stack(6, T_dx=2.0)
prof, runs = BM.column_profile(reg, A.DX, A.N_HAB, A.W_AX, A.A_AX,
                               set(range(1, 7)), r_col=300e-9)
print('prof =', prof)
print('runs =', runs)
# 手工复算每个 bin 的构成
m_all = np.isin(reg, list(range(1, 7)))
N = reg.shape[0]
ii = np.arange(N) * A.DX
cnt = float(m_all.sum())
s = [m_all.sum(axis=(1, 2)), m_all.sum(axis=(0, 2)), m_all.sum(axis=(0, 1))]
c = np.array([float((ii * s[t]).sum()) / cnt for t in range(3)])
rc = int(np.ceil(300e-9 / A.DX)) + 1
bb = BM._bbox_of(m_all, pad=rc)
sub_m = m_all[bb]
sub_r = reg[bb]
cc = BM._sub_coord(bb, A.DX)
r3 = [cc[t] - c[t] for t in range(3)]
r3 = [r3[0][:, None, None], r3[1][None, :, None], r3[2][None, None, :]]
pa = A.A_AX[0] * r3[0] + A.A_AX[1] * r3[1] + A.A_AX[2] * r3[2]
pw = A.W_AX[0] * r3[0] + A.W_AX[1] * r3[1] + A.W_AX[2] * r3[2]
pn = A.N_HAB[0] * r3[0] + A.N_HAB[1] * r3[1] + A.N_HAB[2] * r3[2]
col = sub_m & (pa ** 2 + pw ** 2 <= 300e-9 ** 2)
print('柱内胞数 = %d（占全部 α′ 的 %.1f%%）'
      % (col.sum(), 100.0 * col.sum() / m_all.sum()))
v = pn[col]
ids = sub_r[col]
edges = np.arange(v.min() - 0.5 * A.DX, v.max() + 1.5 * A.DX, A.DX)
idxb = np.digitize(v, edges) - 1
print('bin 数 = %d,  edges[0]=%.3fΔx' % (len(edges) - 1, edges[0] / A.DX))
for b in range(len(edges) - 1):
    sel = (idxb == b)
    if not sel.any():
        print('  bin %2d  [%.3f,%.3f)Δx  空' % (b, edges[b] / A.DX, edges[b + 1] / A.DX))
        continue
    bc = np.bincount(ids[sel])
    nz = {int(k): int(x) for k, x in enumerate(bc) if x}
    print('  bin %2d  [%+.3f,%+.3f)Δx  n=%4d  场分布=%s  mode=%d'
          % (b, edges[b] / A.DX, edges[b + 1] / A.DX, int(sel.sum()), nz,
             int(bc.argmax())))
# 每层在柱内有多少胞
print('柱内各场胞数 =', {k: int((ids == k).sum()) for k in range(7)})
