#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_nvread.py --- 从 `_r581_nvscale.py` 的各臂日志里把 s/步 读数抓出来（**不等脚本结束**）。"""
import glob
import os
import re
import statistics
import sys

RE = re.compile(r'\[(\s*\d+)\]\s+Vt=([\d.eE+\-]+).*?\|\s*([\d.]+)s/步')
RE2 = re.compile(r'\[(\s*\d+)\]\s+.*?\|\s*([\d.]+)s/步')
rows = []
for p in sorted(glob.glob('_w2_r581_[AB]_N*.log'),
                key=lambda f: (os.path.getsize(f))):
    txt = open(p, errors='replace').read()
    v = [float(m.group(3)) for m in RE.finditer(txt)]
    if not v:
        v = [float(m.group(2)) for m in RE2.finditer(txt)]
    tag = os.path.basename(p)[len('_w2_r581_'):-4]
    rows.append((tag, v))
print('  %-16s %-6s %-10s %-10s %s' % ('臂', '读数', '末读数', '末4中位', '全部'))
print('  ' + '-' * 100)
for tag, v in rows:
    if not v:
        print('  %-16s %-6d %s' % (tag, 0, '（还没出读数）'))
        continue
    k = min(4, len(v))
    print('  %-16s %-6d %-10.4f %-10.4f %s'
          % (tag, len(v), v[-1], statistics.median(v[-k:]),
             ' '.join('%.3f' % x for x in v)))
