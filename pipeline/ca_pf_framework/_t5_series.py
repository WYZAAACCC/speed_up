#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_series.py --- 打印某臂的 series 关键列（避开 PowerShell 引号地狱）"""
import csv
import glob
import os
import sys

TAGS = sys.argv[1:] or ['t5G3']
KEY = ('nslab_n', 'nslab_n1', 'nf3', 'nf3_col', 'nf2', 'nblk_sig', 'f_var',
       'n_var_sig', 'r_selfac', 'box_touch')
for t in TAGS:
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    if not os.path.exists(p):
        print('  %-7s ⚠ 无 series' % t)
        continue
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    L = r[-1]
    print('  ── %s：%d 行，末步 %s ──' % (t, len(r), L['step']))
    for c in KEY:
        if c in L:
            print('     %-12s = %s' % (c, (L[c] or '')[:46]))
    print('     Vt           = %s' % L['Vt'][:20])
    ns = [(x['step'], x.get('nslab_n')) for x in r if (x.get('nslab_n') or '').strip()]
    print('     nslab_n 轨迹 = %s' % ns[:12])
    # 该臂的目录体积与检查点数
    d = os.path.dirname(p)
    ck = glob.glob(os.path.join(d, 'ckpt', '*.npz'))
    sn = glob.glob(os.path.join(d, 'snap_*.npz'))
    print('     ckpt=%d 个  snap=%d 个' % (len(ck), len(sn)))
