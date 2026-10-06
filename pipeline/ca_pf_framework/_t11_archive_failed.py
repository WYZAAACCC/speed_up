#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_archive_failed.py —— 把**失败的尝试产物**改名归档（**绝不删除**）。

用法: _t11_archive_failed.py <reason> <dir> [dir ...]
  目录可给绝对路径或相对 `_exp/_bk_t5` 的 tag 名。

依据（本仓库纪律）：数据**改名保留、绝不删除**；失败尝试要留痕（便于复现/复盘）。
"""
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BASES = [os.path.join(ROOT, "_exp", "_bk_t5"),
         "/mnt/f/speed_up/_exp/_bk_t5"]

if len(sys.argv) < 3:
    sys.exit(__doc__)
reason, targets = sys.argv[1], sys.argv[2:]
stamp = time.strftime("%Y%m%d_%H%M%S")
for t in targets:
    p = t if os.path.isabs(t) else None
    if p is None:
        for b in BASES:
            if os.path.isdir(os.path.join(b, t)):
                p = os.path.join(b, t)
                break
    if p is None or not os.path.isdir(p):
        print(f"  ⚠ 找不到目录：{t}")
        continue
    dst = "%s_FAILED_%s_%s" % (p.rstrip('/'), reason, stamp)
    if os.path.exists(dst):
        print(f"  ⚠ 目标已存在，跳过：{dst}")
        continue
    shutil.move(p, dst)
    print(f"  ✅ {os.path.basename(p)}")
    print(f"       → {os.path.basename(dst)}")
