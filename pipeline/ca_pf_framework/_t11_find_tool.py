#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_tool.py —— 找仓库里**已存在的** "测引擎实际 v(n) 各向异性" 的工具。

判据：文件名或内容含 `v_a/v_w`、`9.90`、`vext`、`h(a)/h(w)`、`support` 的脚本。
"""
import glob
import os
import re

D = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PAT = ("v_a/v_w", "9.90", "9.9", "vext", "h(a)/h(w)", "fast_support",
       "support_factory", "wulff", "各向异性")
hits = {}
for f in glob.glob(os.path.join(D, "*.py")) + glob.glob(os.path.join(D, "*.sh")):
    try:
        t = open(f, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    hit = [p for p in PAT if p in t]
    if hit:
        hits[os.path.basename(f)] = hit
print("命中 %d 个文件（按命中数排序）" % len(hits))
print("-" * 96)
for f, h in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:26]:
    print("  %-34s %s" % (f, ','.join(h[:5])))
