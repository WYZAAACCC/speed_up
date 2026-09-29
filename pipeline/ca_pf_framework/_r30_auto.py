#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30：打印 auto_ctrl（唯一一次 `--arm auto`）的 psi_mean 序列与关键列。"""
import os
import csv
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

for p in sorted(glob.glob('_exp/_bk_ctrl/*/series.csv')):
    rs = list(csv.DictReader(open(p)))
    print('=' * 100)
    print(p, ' rows=%d' % len(rs))
    cols = ['step', 't_s', 'Vt', 'nslab_n', 'nf3_col', 'nf3', 'f3_pos_dx',
            'psi_mean', 'cfl_used', 'nreg_used']
    print('  ' + ' | '.join('%-11s' % c for c in cols))
    for r in rs:
        print('  ' + ' | '.join('%-11s' % (r.get(c, '')[:11]) for c in cols))
