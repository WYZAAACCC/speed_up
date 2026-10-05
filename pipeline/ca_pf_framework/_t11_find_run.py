#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_run.py —— 从 WSL 侧定位算例目录与 nuc_dbg.json（避开 9p/大小写缓存坑）。

用法: _t11_find_run.py <tag 关键字>
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
key = sys.argv[1] if len(sys.argv) > 1 else "drvsmoke"
hits = []
for base in (os.path.join(ROOT, "_exp"), "/mnt/f/_exp", os.path.join(ROOT, "_exp", "_bk_t5")):
    if not os.path.isdir(base):
        continue
    for dirpath, dirnames, filenames in os.walk(base):
        if key in dirpath and "nuc_dbg.json" in filenames:
            hits.append(os.path.join(dirpath, "nuc_dbg.json"))
        if dirpath.count(os.sep) - base.count(os.sep) > 3:
            dirnames[:] = []
print(f"命中 {len(hits)} 个：")
for h in sorted(set(hits)):
    print("  ", h, os.path.getsize(h), "B")
for h in sorted(set(hits))[:2]:
    d = json.load(open(h, encoding="utf-8"))
    print(f"\n=== {h} ===")
    print(f"顶层键（{len(d)}）: {sorted(d.keys())}")
    for k in ("drive_pick", "dbg", "n_eng_ev"):
        if k in d:
            print(f"  {k} = {json.dumps(d[k], ensure_ascii=False)[:900]}")
