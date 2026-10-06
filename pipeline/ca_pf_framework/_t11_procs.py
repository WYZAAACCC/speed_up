#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_procs.py [子串 ...] —— 列出匹配的 python 进程（纯 Python，不用 shell 引号）。"""
import os
import sys

pats = sys.argv[1:] or ["sentinel"]
for pid in sorted(os.listdir('/proc'), key=lambda x: int(x) if x.isdigit() else 0):
    if not pid.isdigit():
        continue
    try:
        raw = open('/proc/%s/cmdline' % pid, 'rb').read()
    except OSError:
        continue
    line = ' '.join(x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x)
    if not line:
        continue
    if any(p in line for p in pats):
        print("  PID %-7s %s" % (pid, line[:120]))
print("（列出模式：%s）" % pats)
