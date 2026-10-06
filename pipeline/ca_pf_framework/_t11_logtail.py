#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_logtail.py <log> [n] —— 日志尾部 + 健康检查（避免 shell 引号坑）。"""
import re
import sys

log = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
data = open(log, encoding='utf-8', errors='replace').read()
lines = data.splitlines()
print('日志 %s' % log)
print('  字节 = %d   行数 = %d' % (len(data), len(lines)))
bad = [i for i, ln in enumerate(lines, 1)
       if re.search(r'Traceback|^[A-Za-z]*Error:|error:', ln)]
print('  异常行数 = %d %s' % (len(bad), bad[:6]))
print('  ---- 末 %d 行 ----' % n)
for ln in lines[-n:]:
    print('  ' + ln[:170])
