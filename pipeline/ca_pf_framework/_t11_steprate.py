#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_steprate.py <arm> —— 抽 `s/步` 逐段耗时（判"是否在变慢"）。"""
import re
import sys

arm = sys.argv[1] if len(sys.argv) > 1 else "c2Eq0"
p = "/mnt/f/speed_up/_w2_%s.log" % arm
txt = open(p, encoding="utf-8", errors="replace").read()
rows = []
for m in re.finditer(r'^\s*\[\s*(\d+)\].*?\|\s*([0-9.]+)s/步', txt, re.M):
    rows.append((int(m.group(1)), float(m.group(2))))
print("【%s】%d 行，%d 个数据点" % (arm, txt.count("\n"), len(rows)))
if len(rows) < 2:
    print("  （数据点不足）")
    sys.exit()
print("  %-8s %-10s %s" % ('step', 's/步', '相对首点'))
base = rows[0][1] if rows[0][1] > 0 else None
for st, sp in rows:
    print("  %-8d %-10.2f %s" % (st, sp, ("%.2fx" % (sp / base)) if base else '—'))
# 从 step 区间反推 wall 时间
import os
import time
mt = os.path.getmtime(p)
print("\n  日志 mtime = %s" % time.strftime('%H:%M:%S', time.localtime(mt)))
