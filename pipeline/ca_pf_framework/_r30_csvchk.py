#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：核对 CSV 列对齐 —— `psi_mean` 与 `cfl_used` 到底哪列是 nan。"""
import csv
import sys

f = sys.argv[1]
r = list(csv.reader(open(f)))
h = r[0]
print('header 列数=%d' % len(h))
for tag, row in (('第 1 数据行', r[1]), ('第 12 数据行', r[12]),
                 ('末行', r[-1])):
    print('%s: 字段数=%d' % (tag, len(row)))
    for k, v in zip(h, row):
        print('    %-12s = %s' % (k, v))
    print()
