#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_seed_check.py <arm> —— 检查该臂**实际播了几片**（判据：只播 1 片）。"""
import re
import sys

arm = sys.argv[1] if len(sys.argv) > 1 else "cubeEq0"
p = "/mnt/f/speed_up/_w2_%s.log" % arm
lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
print("【%s】%d 行" % (arm, len(lines)))
KEY = re.compile(r'实际播种|播种.*片|nslab=|grow_stack|只播|生长中的同变体')
hit = [ln.strip() for ln in lines if KEY.search(ln)]
for ln in hit[:10]:
    print("  " + ln[:180])
# 找 step 0 那一行数据（判据：nslab=1）
for ln in lines:
    if re.search(r'\[\s*0\]\s*Vt=', ln):
        print("\n  ★ step 0 数据行：")
        print("    " + ln.strip()[:190])
        m = re.search(r'nslab=(\d+)', ln)
        if m:
            n = int(m.group(1))
            print("    ⇒ nslab = %d  %s"
                  % (n, "✅ **只播 1 片**（隔离成功）" if n == 1
                     else "❌ **播了 %d 片**（隔离失败，需再查）" % n))
        break
