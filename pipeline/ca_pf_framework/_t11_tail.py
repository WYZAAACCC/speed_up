#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_tail.py <file> [n] —— 纯 Python 读尾（不经 shell 引号，也不依赖 WSL 的 9p 缓存）。"""
import sys

p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
with open(p, encoding="utf-8", errors="replace") as fh:
    lines = fh.read().splitlines()
print("文件 %s" % p)
print("  行数 = %d" % len(lines))
print("  ---- 末 %d 行 ----" % n)
for ln in lines[-n:]:
    print("  " + ln[:175])
