#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dbg_triage.py <log> —— 抽 `◆ s295 形核分诊（引擎 dbg）` 行（Q3 归因的权威输出）。"""
import re
import sys

log = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
hits = [ln for ln in lines if "s295" in ln or "形核分诊" in ln]
print("命中 %d 行（日志共 %d 行）" % (len(hits), len(lines)))
print("=" * 100)
for ln in hits[:n]:
    print(ln.strip()[:190])
if len(hits) > n:
    print("   …")
    for ln in hits[-n:]:
        print(ln.strip()[:190])

# 同时抽"被拒"行，看目标 vs 实有 的走势
rej = [ln for ln in lines if "被引擎拒" in ln]
print("\n'被引擎拒' 行数 = %d" % len(rej))
for ln in rej[-6:]:
    print("  " + ln.strip()[:170])
