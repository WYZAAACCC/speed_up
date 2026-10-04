#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_scopt.py --- 给 `_t5_short.py` 补 `--nuc-supercrit` 声明（它已在透传、但没声明参数）。"""
import os
import py_compile
import shutil
import sys

TS = "/mnt/f/speed_up/pipeline/ca_pf_framework/_t5_short.py"
OLD = "    ap.add_argument('--nuc-occ-guard', type=int, default=0, choices=(0, 1, 2),\n"
NEW = ("    ap.add_argument('--nuc-supercrit', type=int, default=1, choices=(0, 1),\n"
       "                    help='s302: \\u8d85\\u4e34\\u754c\\u63a2\\u9488\\uff08\\u771f\\u653e+"
       "\\u56de\\u6eda\\uff09\\uff1b0=\\u5173\\u6389\\u63a2\\u9488')\n" + OLD)

with open(TS, "r", encoding="utf-8") as fh:
    t = fh.read()
n = t.count(OLD)
print("  锚点 %d 次 %s" % (n, "✓" if n == 1 else "❌"))
if n != 1:
    sys.exit(1)
print("  现有 nuc-supercrit 出现 %d 次（透传处）" % t.count("nuc-supercrit"))
t2 = t.replace(OLD, NEW, 1)
tmp = TS + ".sctmp"
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(t2)
try:
    py_compile.compile(tmp, doraise=True)
    print("  ✅ 语法编译通过")
except py_compile.PyCompileError as e:
    print("  ❌ 语法错：%s" % e); os.remove(tmp); sys.exit(1)
os.remove(tmp)
bak = TS + ".bak_scopt"
if not os.path.exists(bak):
    shutil.copy2(TS, bak); print("  备份 → %s" % os.path.basename(bak))
with open(TS, "w", encoding="utf-8") as fh:
    fh.write(t2)
with open(TS, "r", encoding="utf-8") as fh:
    t3 = fh.read()
ok = t3.count("ap.add_argument('--nuc-supercrit'") == 1
print("  写后复验 声明 1 处 %s" % ("✓" if ok else "❌"))
if not ok:
    sys.exit(1)
print("✅ 已补 --nuc-supercrit 声明")
