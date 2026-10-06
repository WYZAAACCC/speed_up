#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_run.py <子串> —— 在归档根目录下**递归找**匹配的算例目录及其快照数。"""
import glob
import os
import sys

ROOTS = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
pat = sys.argv[1] if len(sys.argv) > 1 else "t5AB"
for r in ROOTS:
    print("=== 根：%s（存在=%s）" % (r, os.path.isdir(r)))
    if not os.path.isdir(r):
        continue
    hits = [d for d in glob.glob(os.path.join(r, "*")) if pat in os.path.basename(d)]
    for d in sorted(hits):
        sns = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
        print("   %-52s 快照 %3d 个  %s"
              % (os.path.basename(d), len(sns),
                 ('%s … %s' % (os.path.basename(sns[0]), os.path.basename(sns[-1])))
                 if sns else ''))
    if not hits:
        print("   （无匹配）")
