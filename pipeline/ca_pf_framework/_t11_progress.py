#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_progress.py —— 三个引擎的**真实时间步进度**。

## ⚠ 为什么必须改（2026-10-07 实测的教训）
第一版只解析**数据行 `[ N]`**，而数据行**只在 `--snap-every` / `--every` 的步上打印**
⇒ 实测 `c2B647` 已过 **step 90**（日志里有 `引擎形核 @ step 90`），
而第一版仍报"最新 step = 0" ⇒ **严重低估进度**。
⇒ 现在同时解析**引擎事件行**（`@ step N`）与数据行，取**最大值**。

判活纪律：本脚本只读日志文本；**是否卡死不由它判**（那要看 CPU 增量）。
"""
import os
import re
import time

OUT = "/mnt/f/speed_up/_w2_progress.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
L.append("%-9s %-8s %-11s %-11s %-9s %s"
         % ('tag', '行数', '数据行step', '事件行step', 'mtime', '真实进度'))
L.append("-" * 100)
now = time.time()
for t in ("c2Eq0", "c2B647", "c2PosA", "c2B15", "c2Arch3"):
    f = "/mnt/f/speed_up/_w2_%s.log" % t
    if not os.path.exists(f):
        L.append("%-9s %-8s %-11s %-11s %-9s %s" % (t, '—', '—', '—', '—', '(未创建)'))
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    ds = [int(m.group(1)) for m in re.finditer(r'^\s*\[\s*(\d+)\]', txt, re.M)]
    # 引擎事件行：`★★ **引擎形核** @ step 30：…`
    es = [int(m.group(1)) for m in re.finditer(r'@\s*step\s*(\d+)', txt)]
    mt = os.path.getmtime(f)
    best = max(ds + es) if (ds or es) else None
    L.append("%-9s %-8d %-11s %-11s %-9s %s"
             % (t, txt.count("\n"), ds[-1] if ds else '—',
                es[-1] if es else '—',
                time.strftime('%H:%M:%S', time.localtime(mt)),
                ('★ **step ≥ %d**（%.0f s 前写过日志）' % (best, now - mt))
                if best is not None else '⚠ 无 step 证据'))
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
