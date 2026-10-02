#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_cols.py --- 列出 `series.csv` 的**全部列**并标注哪些在变（找 S4 的可观测量）。"""
import os
import sys

import numpy as np

R = '_exp/_bk_p2'
t = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
p = os.path.join(R, 'dry_' + t, 'series.csv')
with open(p) as fh:
    hdr = fh.readline().strip().split(',')
a = np.genfromtxt(p, delimiter=',', names=True)
print('%s : %d 列' % (t, len(hdr)))
for i, c in enumerate(hdr):
    try:
        v = np.atleast_1d(a[c]).astype(float)
    except Exception:
        print('  %2d %-24s （非数值）' % (i, c)); continue
    fin = v[np.isfinite(v)]
    if fin.size == 0:
        s = '全 NaN'
    elif fin.size == 1:
        s = '恒 %.6g' % fin[0]
    elif fin.max() == fin.min():
        s = '恒 %.6g（%d 行）' % (fin[0], fin.size)
    else:
        s = '首 %-12.5g 末 %-12.5g' % (fin[0], fin[-1])
    print('  %2d %-24s %s' % (i, c, s))
