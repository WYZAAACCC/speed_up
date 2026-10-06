#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_tail3.py —— 三个引擎的日志尾部（看它们各自走到哪一步）。"""
import os

OUT = "/mnt/f/speed_up/_w2_tail3.txt"
L = []
for t in ("c2Eq0", "c2B647", "c2PosA"):
    f = "/mnt/f/speed_up/_w2_%s.log" % t
    L.append("=" * 100)
    if not os.path.exists(f):
        L.append("【%s】(未创建)" % t)
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    lines = txt.splitlines()
    L.append("【%s】%d 行  mtime=%s" % (
        t, len(lines),
        __import__('time').strftime('%H:%M:%S',
                                    __import__('time').localtime(os.path.getmtime(f)))))
    for ln in lines[-6:]:
        L.append("   " + ln[:165])
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
