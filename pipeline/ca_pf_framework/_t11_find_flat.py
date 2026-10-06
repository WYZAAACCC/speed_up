#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_flat.py —— 找"平界面 + 常数驱动"那个正对照的脚本/算例（`windowB_surface.py:5337` 引用）。"""
import glob
import os

D = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PAT = ("band=20dx", "0.750", "v/M", "平界面", "_chk_w2", "constant_drive",
       "flat_iface", "planar")
hits = {}
for f in glob.glob(os.path.join(D, "*.py")) + glob.glob(os.path.join(D, "*.sh")):
    try:
        t = open(f, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    h = [p for p in PAT if p in t]
    if h:
        hits[os.path.basename(f)] = h
print("命中 %d 个文件" % len(hits))
for f, h in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:20]:
    print("  %-40s %s" % (f, ','.join(h[:5])))
print()
# 也找带 "平界面" 的文档段
for f in glob.glob(os.path.join(D, "*.md")):
    try:
        t = open(f, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    if "平界面" in t and ("0.750" in t or "1.0000" in t or "band=20dx" in t):
        print("  文档命中：%s" % os.path.basename(f))
