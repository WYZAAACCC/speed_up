#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_p2read.py --- 读两个长跑臂**已落盘**的 series.csv，给 C1–C6 的现场读数。

用法: python3 _r581_p2read.py [tag ...]
"""
import os
import sys

import numpy as np

R = '_exp/_bk_p2'
tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
KEYS = ['step', 'Vt', 'nslab_n', 'nf3_col', 'nf2', 'nc_max', 'nc_sig', 'box_touch',
        'F3_area', 'nf3_area', 'r_selfac', 'blk_span_nm', 'blk_nprof', 'nblk_sig',
        'E_el_J', 'nfsv_nofield', 'nreg_used', 'T', 'df', 'ev', 'nuc']

for t in tags:
    p = os.path.join(R, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        print('%s: 缺 series.csv' % t)
        continue
    with open(p) as fh:
        hdr = fh.readline().strip().split(',')
    a = np.genfromtxt(p, delimiter=',', names=True)
    n = len(np.atleast_1d(a[hdr[0]]))
    print('=' * 92)
    print('%s : %d 列 × %d 行' % (t, len(hdr), n))
    print('=' * 92)
    cols = [c for c in hdr if any(k.lower() in c.lower() for k in KEYS)]
    for c in cols:
        v = np.atleast_1d(a[c]).astype(float)
        fin = v[np.isfinite(v)]
        if fin.size == 0:
            print('  %-22s 全 NaN' % c)
            continue
        if fin.size == 1:
            print('  %-22s 恒 %.6g' % (c, fin[0]))
        else:
            print('  %-22s 首 %-14.6g 末 %-14.6g  min %-12.6g max %-12.6g %s'
                  % (c, fin[0], fin[-1], fin.min(), fin.max(),
                     '（在变）' if fin.max() != fin.min() else '（恒定）'))
    # C3 的逐行判据：nslab_n == M 且 nf3_col == M-1
    for key, k2 in (('nslab_n', 'nf3_col'),):
        cands = [c for c in hdr if c == key]
        c2 = [c for c in hdr if c == k2]
        if cands and c2:
            x = np.atleast_1d(a[cands[0]]).astype(float)
            y = np.atleast_1d(a[c2]).astype(float)
            m = np.isfinite(x) & np.isfinite(y)
            if m.any():
                ok = (y[m] == x[m] - 1)
                print('  ⇒ C3 逐行判据 `%s == %s - 1`：%d/%d 行成立 ⇒ %s'
                      % (k2, key, int(ok.sum()), int(m.sum()),
                         '✅ 成立' if ok.all() else '⚠ 部分行不成立'))
    print()
