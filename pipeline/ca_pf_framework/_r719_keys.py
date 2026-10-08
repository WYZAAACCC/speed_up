#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r719_keys.py <snap.npz> [...] —— 列出快照的键/类型/形状（**不假设**，先看清楚）。"""
import sys

import numpy as np

for p in sys.argv[1:]:
    print('=' * 90)
    print(p)
    print('=' * 90)
    try:
        z = np.load(p, allow_pickle=False)
    except Exception as e:
        print('  ⛔ 打不开: %s' % e)
        continue
    for k in sorted(z.files):
        a = np.asarray(z[k])
        extra = ''
        if a.size and a.dtype.kind in 'fi' and a.ndim <= 2:
            try:
                extra = '  min=%.6g max=%.6g' % (float(a.min()), float(a.max()))
            except Exception:
                pass
        if a.dtype.kind in 'US' and a.size:
            extra = '  = %r' % (a.ravel()[0],)
        print('  %-22s %-10s %-18s%s' % (k, a.dtype, str(a.shape), extra))
