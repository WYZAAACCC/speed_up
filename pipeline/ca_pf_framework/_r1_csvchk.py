#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_csvchk.py --- 核实 `series.csv` 的 `step` 列是否可用（不信 meta、不猜 every）。"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
for d in ['mid250_ns4', 'mid192_ns4', 'mid192_s2_ns4', 'e7_selfac', 'equi192_ns4']:
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('%-16s NO CSV' % d); continue
    rows = list(csv.DictReader(open(p)))
    print('%-16s rows=%-4d cols=%d' % (d, len(rows), len(rows[0])))
    print('   header[0:6] = %s' % list(rows[0].keys())[:6])
    for r in rows[:2] + rows[-2:]:
        print('   step=%-6s t_s=%-12s L_cal=%-10s W_cal=%-10s N_L=%-8s'
              % (r.get('step'), r.get('t_s'), r.get('L_cal'), r.get('W_cal'),
                 r.get('N_L')))
