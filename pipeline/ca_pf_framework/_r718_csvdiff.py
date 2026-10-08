#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r718_csvdiff.py <a.csv> <b.csv> —— 逐行逐列找两份 series.csv 的差异（V2 判据的定位工具）。"""
import csv
import sys

A = list(csv.reader(open(sys.argv[1], newline='')))
B = list(csv.reader(open(sys.argv[2], newline='')))
h = A[0]
print('列数 A=%d B=%d  行数 A=%d B=%d' % (len(h), len(B[0]), len(A), len(B)))
if h != B[0]:
    print('⛔ 表头不同')
    sys.exit(1)
ndiff = 0
for i, (ra, rb) in enumerate(zip(A[1:], B[1:]), 1):
    d = [(h[j], ra[j], rb[j]) for j in range(min(len(ra), len(rb))) if ra[j] != rb[j]]
    if d:
        ndiff += 1
        print('行 %d：%d 列不同' % (i, len(d)))
        for name, va, vb in d[:8]:
            print('    %-22s A=%-24s B=%s' % (name, va, vb))
if ndiff == 0:
    print('✅ 所有数据行逐列相同（那么 sha 差异只可能来自行尾/换行/编码）')
else:
    print('⇒ 共 %d 行有差异' % ndiff)
