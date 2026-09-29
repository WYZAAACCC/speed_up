#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_scan.py —— 把 `_bk_smoke_f3.py` 各臂的 series.csv 汇成一张表（只读，不改数据）。"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '_exp', '_bk_f3smoke')
ARMS = sys.argv[1:] or ['ns0', 'ns1', 'ns2', 'main', 'ctrl_pos', 'ctrl_neg']
COLS = ['step', 'V1', 'V2', 'nf3', 'f3_area_m2', 'f3_pos_dx', 'nslab_n',
        'nf3_col', 'runs', 'ncomp_1', 'ncomp_2', 'n_1', 'w_1', 'a_1', 'box_touch']

HDR = ('%-9s %-5s | %9s %9s | %8s | %6s %8s %6s %-11s %5s %5s %5s'
       % ('arm', 'step', 'V1', 'V2', 'dpos_dx', 'nf3', 'f3_area', 'nslab',
          'runs', 'nc1', 'nc2', 'wall'))
print(HDR)
print('-' * len(HDR))
for a in ARMS:
    p = os.path.join(ROOT, a, 'series.csv')
    if not os.path.exists(p):
        print('%-9s  （缺 %s）' % (a, p))
        continue
    with open(p, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    last = int(float(rows[-1]['step']))
    for r in rows:
        st = int(float(r['step']))
        if st % 40 and st != last:
            continue
        d = r.get('f3_pos_dx', 'nan')
        g = lambda k, dv='-': r.get(k, dv)          # 容忍旧版 CSV 缺列
        print('%-9s %-5d | %9.4f %9.4f | %+8.3f | %6s %8.4f %6s %-11s %5s %5s %5s'
              % (a, st, float(r['V1']) * 1e18, float(r['V2']) * 1e18,
                 (float(d) if d not in ('', 'nan') else float('nan')),
                 g('nf3'), float(r['f3_area_m2']) * 1e12, g('nslab_n'),
                 g('runs'), g('ncomp_1'), g('ncomp_2'), g('box_touch')))
    print('-' * len(HDR))
