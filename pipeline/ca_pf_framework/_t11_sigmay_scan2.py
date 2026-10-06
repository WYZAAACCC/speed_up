#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_sigmay_scan2.py —— ③-9 的第二轮：**放宽规则**并做**量具自检**。

## 为什么必须自检（`AGENTS.md` 教训 19）
  第一轮（`_t11_sigmay_scan.py`）报「173 篇、命中 0」。
  **0 命中既可能是"语料里真没有"，也可能是"我的正则/线索写错"** ——
  两者长得一模一样 ⇒ **必须先用一个"已知答案"跑通工具**。

## 自检（正对照）
  规则必须能命中一篇**明确含屈服强度 + MPa**的文本。用**放宽规则**
  （去掉温度线索）在同一语料上跑：若放宽后命中 `>0`，说明
  "字面抽取"这条路是通的，那么"严格规则的 0 命中"就是**温度线索**把结果筛没了。
"""
import os
import re

DIRS = ["/mnt/f/speed_up/_litidx/lit_txt",
        "/mnt/f/speed_up/lit/cache",
        "/mnt/f/speed_up/lit/A_txt"]
YLD = re.compile(r"yield\s+str|yield\s+stress|proof\s+str|σ\s*[yY]\b|\bsigma_?y\b",
                 re.I)
MPA = re.compile(r"(\d{2,4}(?:\.\d+)?)\s*MPa")
MAT = re.compile(r"Ti[-\s]?6Al[-\s]?4V|Ti64|Ti-64|Ti6Al4V", re.I)
# 温度线索（**放宽**：任何 3 位数 K 或 2–3 位数 °C，以及 RT/room/ambient/elevated）
TANY = re.compile(r"(\d{3,4}\s*K|\d{2,3}\s*°?\s*C|room\s+temp|ambient|elevated)", re.I)

files = 0
loose = 0          # 屈服 + MPa（无温度要求）—— **正对照**
withmat = 0        # 屈服 + MPa + 提到 Ti-64
withtemp = 0       # 屈服 + MPa + 任何温度线索
rows = []
for d in DIRS:
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        try:
            lines = open(os.path.join(d, fn), encoding="utf-8",
                         errors="replace").read().splitlines()
        except OSError:
            continue
        files += 1
        for i, ln in enumerate(lines):
            win = " ".join(lines[max(0, i - 1):i + 2])
            if not (YLD.search(win) and MPA.search(win)):
                continue
            loose += 1
            if MAT.search(win):
                withmat += 1
            if TANY.search(win):
                withtemp += 1
                if len(rows) < 30:
                    rows.append((fn, i + 1, win[:190],
                                 "Ti64" if MAT.search(win) else "  ? "))

print("=== 量具自检（正对照）===")
print(f"  扫描 {files} 篇")
print(f"  ① 屈服+MPa（**无**温度要求）命中 = **{loose}**"
      f"   ⇒ 正对照{'通过（抽取路径通）' if loose > 0 else '**失败（连正对照都 0 ⇒ 规则写错）**'}")
print(f"  ② 其中提到 Ti-64      = {wimat if False else 0}" .replace("wimat if False else 0", str(withmat)))
print(f"  ③ 其中有温度线索      = {withtemp}")
print("\n=== 有温度线索的前 30 处（人工判）===")
for fn, ln, txt, tag in rows:
    print(f"[{tag}] {fn[:46]:46} L{ln:<6} {txt}")
