#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_regress_read.py —— 读回归日志的**判据行**（纯 Python，避免 shell 引号坑）。"""
import re
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "/mnt/f/speed_up/_w2_regress_new.log"
KEY = ("差异字段数", "共有列", "G-1", "G-2", "G-3", "FAIL", "PASS",
       "逐位", "新列", "DONE", "未通过", "通过")
out = []
for ln in open(p, encoding="utf-8", errors="replace"):
    s = ln.rstrip()
    if any(k in s for k in KEY):
        out.append(s)
print("命中 %d 行（文件 %s）" % (len(out), p))
print("-" * 100)
for s in out[:60]:
    print("  " + s[:150])
