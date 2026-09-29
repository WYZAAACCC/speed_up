#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_traj2.py —— 引擎形核各臂 + 驱动层对照 的轨迹并排。"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = [('eng3', '_exp/_bk_eng/eng_eng3'), ('eng2', '_exp/_bk_eng/eng_eng2'),
         ('eng1', '_exp/_bk_eng/eng_eng1'), ('gs5', '_exp/_bk_gs/dry_gs5'),
         ('p3', '_exp/_bk_block/dry_p3')]
rows = {}
for tag, p in PAIRS:
    fp = os.path.join(HERE, p, 'series.csv')
    if os.path.exists(fp):
        rows[tag] = {int(r['step']): r for r in csv.DictReader(open(fp))}
print('%-6s %5s %6s %7s %10s %9s' % ('臂', 'step', 'nslab', 'nf3col',
                                     'F3 µm²', 'Vt µm³'))
print('-' * 50)
for st in (0, 60, 90, 120, 150, 180, 200):
    for tag, _p in PAIRS:
        if tag not in rows or st not in rows[tag]:
            continue
        r = rows[tag][st]
        print('%-6s %5s %6s %7s %10.4f %9.4f'
              % (tag, r['step'], r['nslab_n'], r['nf3_col'],
                 float(r['f3_area_m2']) * 1e12, float(r['Vt']) * 1e18))
    print()
