#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_fresh_ls.py —— 列举目录，并**只过滤目标名前缀**（避免 head 截断误导）。"""
import os
import sys

base = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
need = sys.argv[1] if len(sys.argv) > 1 else "dry_drvsmoke"
print(f"base exists={os.path.isdir(base)}")
try:
    names = sorted(os.listdir(base))
except OSError as e:
    sys.exit(f"listdir 失败: {e}")
print(f"共 {len(names)} 项；含 {need!r} 的项：{[n for n in names if need in n] or '（无）'}")
p = os.path.join(base, need)
print(f"目标存在？ {os.path.exists(p)}")
if os.path.isdir(p):
    for n in sorted(os.listdir(p)):
        fp = os.path.join(p, n)
        print(f"   {os.path.getsize(fp):>12}  {n}")
