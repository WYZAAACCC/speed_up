#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_lsdir.py —— 从 WSL 侧列举一个目录（诊断 9p 可见性）。"""
import os
import sys

p = sys.argv[1]
print(f"路径: {p}")
print(f"  exists={os.path.exists(p)}  isdir={os.path.isdir(p)}")
if os.path.isdir(p):
    for n in sorted(os.listdir(p)):
        fp = os.path.join(p, n)
        try:
            sz = os.path.getsize(fp) if os.path.isfile(fp) else -1
        except OSError as e:
            sz = f"ERR {e}"
        print(f"    {sz:>12}  {n}")
