#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r733_prog.py <root> [tag ...] —— 只读进度：`series.csv` 行数与末行 step。"""
import csv
import os
import sys

root = sys.argv[1]
tags = sys.argv[2:] or ['L_off', 'L_on']
for t in tags:
    p = os.path.join(root, 'dry_%s' % t, 'series.csv')
    if not os.path.isfile(p):
        print('%-8s 尚无 series.csv' % t)
        continue
    with open(p, newline='') as f:
        rows = list(csv.DictReader(f))
    if rows:
        print('%-8s %4d 行  末 step = %s   Vt = %s'
              % (t, len(rows), rows[-1].get('step'), rows[-1].get('Vt')))
    else:
        print('%-8s 0 行' % t)
