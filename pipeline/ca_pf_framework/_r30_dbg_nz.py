#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_dbg_nz.py —— 调试：格点对齐法向 n*=(0,0,1) 下 F3 胞为何为空。"""
import os
import sys
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np
import _bk_measure as BM

N = int(os.environ.get('NDBG', '16'))
DX = 62.5e-9
NH = np.array([0.0, 0.0, 1.0])
W_AX = np.array([0.70711, 0.70711, 0.0]); W_AX /= np.linalg.norm(W_AX)
A_AX = np.array([-0.4909, 0.4909, 0.7198]); A_AX /= np.linalg.norm(A_AX)
C0 = np.array([N * DX / 2] * 3)
AM = dict(n=NH, w=W_AX, a=A_AX)
T = 125e-9
reg = BM._stack_reg(N, DX, C0, NH, AM, 2, 2 * T, gap=0.0, w=320e-9, a=1200e-9)
for k in (1, 2):
    idx = np.argwhere(reg == k)
    print('场 %d: n=%d  x∈[%d,%d] y∈[%d,%d] z∈[%d,%d]'
          % (k, idx.shape[0], idx[:, 0].min(), idx[:, 0].max(),
             idx[:, 1].min(), idx[:, 1].max(), idx[:, 2].min(), idx[:, 2].max()))
    zc = np.bincount(idx[:, 2], minlength=N)
    print('   z 直方图(非零):', {int(z): int(v) for z, v in enumerate(zc) if v})
    yz = np.bincount(idx[:, 1], minlength=N)
    print('   y 直方图(非零):', {int(y): int(v) for y, v in enumerate(yz) if v})
    xz = np.bincount(idx[:, 0], minlength=N)
    print('   x 直方图(非零):', {int(x): int(v) for x, v in enumerate(xz) if v})
m1, m2 = (reg == 1), (reg == 2)
print('faces_between =', BM._faces_between(m1, m2))
r = BM.measure_state(reg, DX, NH, W_AX, A_AX, {1: 1, 2: 1})
print('f3_faces=%s f3_cells=%s f3_pos_n=%s' % (r['f3_faces'], r['f3_cells'], r['f3_pos_n']))
print('nslab_n=%s runs=%s n_1=%.0f n_2=%.0f' % (r['nslab_n'], r['runs'],
                                                 r['n_1'] * 1e9, r['n_2'] * 1e9))
