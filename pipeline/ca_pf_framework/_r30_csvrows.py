#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：逐行打印一个算例的关键列（核对 psi_mean / cfl_used / Δpos）。"""
import csv
import sys

f = sys.argv[1]
keys = sys.argv[2].split(',') if len(sys.argv) > 2 else \
    ['step', 'psi_mean', 'cfl_used', 'nf3', 'f3_pos_m', 'f3_pos_dx']
r = list(csv.DictReader(open(f)))
print('%-8s ' % 'row' + ' '.join('%-22s' % k for k in keys))
for i, x in enumerate(r):
    print('%-8d ' % i + ' '.join('%-22s' % x.get(k, '-') for k in keys))
