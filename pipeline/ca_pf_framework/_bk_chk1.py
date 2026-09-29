#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_chk1.py —— 快速查一个臂的 series.csv 关键列（box_touch / ncomp / Δpos 何时起跳）。"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
p = sys.argv[1]
if not os.path.isabs(p):
    p = os.path.join(HERE, p)
with open(p, newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print('cols =', list(rows[0].keys()))
print('%6s %10s %10s %10s %9s %6s %6s %6s %8s' %
      ('step', 'V1', 'V2', 'a_1', 'dpos', 'nslab', 'nc1', 'nc2', 'wall'))
for r in rows:
    g = lambda k: r.get(k, '-')
    def f1(k):
        v = g(k)
        try:
            return float(v)
        except Exception:
            return float('nan')
    print('%6s %10.4f %10.4f %10.0f %9.3f %6s %6s %6s %8s' %
          (g('step'), f1('V1') * 1e18, f1('V2') * 1e18, f1('a_1') * 1e9,
           f1('f3_pos_dx'), g('nslab_n'), g('ncomp_1'), g('ncomp_2'),
           g('box_touch')))
