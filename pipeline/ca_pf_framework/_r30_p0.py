#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：反解 CSV 里 `f3_pos_dx` 用的 `P0`，定位 Δpos 的 1.4e-3 相对差来源。

`_bk_exp.py:710` 写的是 `f3_pos_dx = (pm − P0)/dx` ⇒ 从 CSV 的 `pm` 与
`f3_pos_dx` 可以**逐行反解** `P0 = pm − f3_pos_dx·dx`。若各行反解出的 `P0`
不一致，说明差值不是常数偏置，而是别的机制。
"""
import csv
import os
import sys

import numpy as np

d = sys.argv[1]
z0 = np.load(os.path.join(d, 'snap_00000.npz'))
dx = float(z0['L']) / z0['region'].shape[0]
print('dx = %.6g m' % dx)
with open(os.path.join(d, 'series.csv'), newline='') as fh:
    rows = list(csv.DictReader(fh))
print('%8s %-22s %-22s %-22s' % ('step', 'f3_pos_m(CSV)', 'f3_pos_dx(CSV)',
                                 'P0 = pm - d·dx'))
for r in rows:
    pm, pd = r.get('f3_pos_m'), r.get('f3_pos_dx')
    try:
        pm = float(pm); pd = float(pd)
    except (TypeError, ValueError):
        continue
    if not (np.isfinite(pm) and np.isfinite(pd)):
        continue
    print('%8s %-22.12g %-22.12g %-22.12g' % (r['step'], pm, pd, pm - pd * dx))
