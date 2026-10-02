#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_snapkeys.py --- 探针：快照里 F3 相关的数组**到底是什么形状/含义**？
（要建 F3 邻接图，先得知道手里有什么 —— 不许猜。）"""
import os
import sys

import numpy as np

tag = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
d = os.path.join('_exp/_bk_p2', 'dry_' + tag)
c = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
           key=lambda f: int(f.split('_')[1].split('.')[0]))
snap = c[-1]
z = np.load(os.path.join(d, snap), allow_pickle=True)
print('=' * 92)
print('快照探针：%s / %s' % (tag, snap))
print('=' * 92)
for k in z.keys():
    a = z[k]
    try:
        sh = a.shape
        dt = a.dtype
    except Exception:
        sh, dt = '?', '?'
    extra = ''
    if getattr(a, 'dtype', None) is not None and a.dtype.kind in 'iuf' and a.size <= 200000:
        try:
            extra = '  min=%s max=%s' % (np.nanmin(a), np.nanmax(a))
        except Exception:
            extra = ''
    print('  %-16s shape=%-22s dtype=%-12s%s' % (k, sh, dt, extra))
    if a.dtype.kind in 'OU':
        print('       值 = %s' % (np.ravel(a)[:12],))
print()
print('── F3 相关数组的内容（前几个）──')
for k in ('band_idx', 'band_val', 'band_fld', 'band_cells', 'f3_pos_p0_m'):
    if k in z:
        a = z[k]
        print('  %s：size=%d' % (k, a.size))
        if a.dtype.kind in 'iuf' and a.size:
            print('    前 24 个 = %s' % (np.ravel(a)[:24],))
        elif a.size:
            print('    前 24 个 = %s' % (np.ravel(a)[:24],))
