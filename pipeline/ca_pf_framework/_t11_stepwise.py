#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_stepwise.py —— 看每个臂**每个 step 的输出行**及其时间戳（定位"卡在哪一步"）。

判活纪律：本脚本只读日志文本；**是否卡死**不由它判（那要 CPU 增量，见 `_t11_cpu_audit.py`）。
"""
import os
import re
import time

OUT = "/mnt/f/speed_up/_w2_stepwise.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
for t in ("c2Eq0", "c2B647"):
    f = "/mnt/f/speed_up/_w2_%s.log" % t
    if not os.path.exists(f):
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    lines = txt.splitlines()
    L.append("=" * 96)
    L.append("【%s】共 %d 行；数据行（`[ N]`）与关键里程碑：" % (t, len(lines)))
    for i, ln in enumerate(lines):
        if re.match(r'^\s*\[\s*\d+\]', ln) or '形核' in ln or 'dt=' in ln \
                or '构造' in ln or '播种' in ln:
            # 抽 s/步 与 step
            st = re.match(r'^\s*\[\s*(\d+)\]', ln)
            sp = re.search(r'\|\s*([0-9.]+)\s*$', ln.strip())
            km = re.match(r'^\s*\[\s*(\d+)\]', ln)
            tag = ('数据行 step=%s' % st.group(1)) if st else '里程碑'
            L.append("   L%-4d %-16s %s" % (i + 1, tag, ln.strip()[:120]))
    L.append("")
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
