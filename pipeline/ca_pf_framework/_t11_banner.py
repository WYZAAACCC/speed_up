#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_banner.py <log> [patterns...] —— 读日志 banner（避免 shell 引号坑）。"""
import re
import sys

log = sys.argv[1]
pats = sys.argv[2:] or ['wrap', 'evloc', '周期', 'burst', 'qs.clock', '总根数',
                        '档数', 'nv=', '监控', 'R29', 'C-5', '体积']
rx = re.compile('|'.join(pats), re.I)
n = 0
with open(log, encoding='utf-8', errors='replace') as fh:
    for i, ln in enumerate(fh, 1):
        if rx.search(ln):
            print('L%-6d %s' % (i, ln.rstrip()[:165]))
            n += 1
            if n >= 40:
                break
print('---- 命中 %d 行 ----' % n)
