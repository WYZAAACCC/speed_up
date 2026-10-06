#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_progress.py —— 三个引擎的**时间步进度**（只看数据行 `[  N]`，不看告警）。"""
import os
import re
import time

OUT = "/mnt/f/speed_up/_w2_progress.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
L.append("%-9s %-7s %-9s %-11s %-11s %s"
         % ('tag', '行数', '最新step', '日志mtime', '距今(s)', '备注'))
L.append("-" * 96)
now = time.time()
for t in ("c2Eq0", "c2B647", "c2PosA", "c2B15", "c2Arch3"):
    f = "/mnt/f/speed_up/_w2_%s.log" % t
    if not os.path.exists(f):
        L.append("%-9s %-7s %-9s %-11s %-11s %s" % (t, '—', '—', '—', '—', '(未创建)'))
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    steps = [int(m.group(1)) for m in re.finditer(r'^\s*\[\s*(\d+)\]', txt, re.M)]
    mt = os.path.getmtime(f)
    L.append("%-9s %-7d %-9s %-11s %-11.0f %s"
             % (t, txt.count("\n"), steps[-1] if steps else '（尚无数据行）',
                time.strftime('%H:%M:%S', time.localtime(mt)), now - mt,
                '✅ 有数据行' if steps else '⚠ 仍在构造/播种期'))
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
