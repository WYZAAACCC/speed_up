#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_grep.py <文件> <子串...> --- 受控 grep（避开 PowerShell 对 UTF-8 参数的破坏）。"""
import sys
p = sys.argv[1]
keys = sys.argv[2:]
hit = 0
for i, ln in enumerate(open(p, errors='replace'), 1):
    if any(k in ln for k in keys):
        print('%6d| %s' % (i, ln.rstrip()[:190]))
        hit += 1
print('---- %d 行命中 / 共 %d 行' % (hit, i if 'i' in dir() else 0))
