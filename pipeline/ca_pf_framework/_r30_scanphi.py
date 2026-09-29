#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30 只读审计：扫全部 snap_*.npz，列出含 'phi' 键的文件（I-6 证据）。"""
import os
import glob

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

withphi, nophi = [], []
for p in sorted(glob.glob('_exp/*/snap_*.npz')):
    try:
        with np.load(p) as d:
            keys = list(d.files)
    except Exception as e:
        print('ERR', p, e)
        continue
    (withphi if 'phi' in keys else nophi).append(p)

print('总计 %d 个 snap' % (len(withphi) + len(nophi)))
print('含 phi : %d' % len(withphi))
for p in withphi[:60]:
    print('   ', p)
print('无 phi : %d' % len(nophi))
# 是否有任何 snap 含 'psi' / 'sparse' 之类的键？
allk = set()
for p in sorted(glob.glob('_exp/*/snap_*.npz')):
    try:
        with np.load(p) as d:
            allk |= set(d.files)
    except Exception:
        pass
print('全部出现过的键 :', sorted(allk))
