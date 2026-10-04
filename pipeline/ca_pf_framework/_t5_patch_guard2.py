#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_guard2.py --- 允许 `--nuc-occ-guard 2`（s301 清理档）。"""
import py_compile
import shutil
import sys

OLD = "ap.add_argument('--nuc-occ-guard', type=int, default=0, choices=(0, 1),"
NEW = "ap.add_argument('--nuc-occ-guard', type=int, default=0, choices=(0, 1, 2),"
BASE = "/mnt/f/speed_up/pipeline/ca_pf_framework/"
FILES = ["_bk_exp.py", "_t5_short.py"]

for f in FILES:
    p = BASE + f
    with open(p, "r", encoding="utf-8") as fh:
        t = fh.read()
    n = t.count(OLD)
    print("  %s 锚点 %d 次 %s" % (f, n, "✓" if n == 1 else "❌"))
    if n != 1:
        sys.exit(1)
    t2 = t.replace(OLD, NEW, 1)
    tmp = p + ".g2tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t2)
    try:
        py_compile.compile(tmp, doraise=True)
    except py_compile.PyCompileError as e:
        print("  ❌ 语法错：%s" % e); sys.exit(1)
    import os
    os.remove(tmp)
    bak = p + ".bak_guard2"
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(t2)
    with open(p, "r", encoding="utf-8") as fh:
        t3 = fh.read()
    ok = t3.count(NEW) == 1
    print("  %s 写后复验 choices=(0,1,2) %s ；语法 OK" % (f, "✓" if ok else "❌"))
    if not ok:
        sys.exit(1)
print("✅ 允许 --nuc-occ-guard 2")
