#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_probe.py —— 打印锚点附近行的**真实字节**（定位为何不匹配）。"""
import sys

P = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"
with open(P, encoding="utf-8", newline="") as fh:
    lines = fh.read().split("\n")
print("总行数（按 \\n 切）= %d" % len(lines))
TARGETS = ["mob_iform='exp2'", "facet_proj=0,", "_r576_res", "facet_proj and int(facet_proj)"]
for t in TARGETS:
    hits = [i for i, l in enumerate(lines) if t in l]
    print("\n--- 含 %r 的行：%s ---" % (t, [h + 1 for h in hits][:6]))
    for h in hits[:3]:
        l = lines[h]
        print("  :%d  len=%d  repr=%r" % (h + 1, len(l), l[:120]))
        if l and l[0] not in ' \t':
            print("       ⚠ 首字符非空白")
        bad = [(j, hex(ord(c))) for j, c in enumerate(l) if ord(c) > 127 or c in '\r\t']
        if bad:
            print("       ⚠ 特殊字符：%s" % bad[:6])
