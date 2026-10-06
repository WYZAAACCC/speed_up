#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_event_rate.py <log> —— 事件/检查点里程碑的**速率**（用 log 行号间隔 + mtime 定基准）。

⚠ 日志行没有时间戳 ⇒ 只能用 (行数, 当前 mtime) 两个量估**区间速率**：
   已知「ckpt 0 @ 21:18:27」与「末次 mtime」，若两者之间落了 k 个事件
   ⇒ 平均 ≤ (mtime − 21:18:27)/k。
⚠ 这是**上界估计**（分母可能把未落事件的时间算进去）⇒ **不得**当精确值。
"""
import os
import re
import sys
import time

log = sys.argv[1]
pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else r'athermal 形核\*\* @ step')
lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines) if pat.search(ln)]
mt = os.path.getmtime(log)
print("日志 %s" % log)
print("  行数 = %d   文件 mtime = %s" % (len(lines),
                                        time.strftime('%H:%M:%S', time.localtime(mt))))
print("  匹配 `%s` 的行数 = %d" % (pat.pattern, len(hits)))
for ln_no, ln in hits[-10:]:
    i = ln.find('★★')
    txt = ln[i:i + 120] if i >= 0 else ln[:120]
    print("    L%-6d %s" % (ln_no, txt))
# 抽"累计 N/135"里的 N，给走势
cums = []
for ln in lines:
    m = re.search(r'累计 (\d+)/(\d+)', ln)
    if m:
        cums.append((int(m.group(1)), int(m.group(2))))
print("  「累计 N/135」出现 %d 次；末值 = %s" % (len(cums), cums[-1] if cums else None))
if cums:
    print("  ⇒ 累计根数轨迹（去重保序）：",
          [c for i, c in enumerate(cums) if i == 0 or c != cums[i - 1]][:24])
