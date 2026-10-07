#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dipchk.py <tag>... —— 核实 `mob_dip` 是否真的进入了该臂的运行。

## 为什么要查（`R677`）
`F8`（`dip=8`）与 `C4`（`dip=4`）在 `step 150` 的 PCA 读数**几乎逐位相同**
（7.00 vs 7.07 / 5.00 vs 5.09，跨度 3 位有效数字全同）
⇒ 按 `P7`/`R663`（`--beta-w 0.0` 曾让七臂作废）的教训，**先查参数是否生效**。

## 查什么
1. **`launch.json` / `meta.json` 里的命令行**（`_bk_exp.py` 是否落盘了 argv）；
2. 若没有，则**比两臂的 `series.csv`**：若**逐位相同** ⇒ `dip` 未生效（或该区间不受影响）。
"""
import csv
import json
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
TAGS = sys.argv[1:] or ["C4", "F8", "F6"]
print("=" * 92)
print("核实 `mob_dip` 是否生效")
print("=" * 92)
for t in TAGS:
    d = os.path.join(ROOT, "dry_%s" % t)
    if not os.path.isdir(d):
        print("【%s】无目录" % t)
        continue
    print("\n【%s】目录内容：" % t)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".npz"):
            print("   %s" % f)
    # 找任何含命令行的文件
    for f in os.listdir(d):
        p = os.path.join(d, f)
        if not os.path.isfile(p) or f.endswith(".npz"):
            continue
        if not f.endswith((".json", ".txt", ".log", ".sh")):
            continue
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "mob-dip" in txt or "mob_dip" in txt:
            print("   ⇒ `%s` 里含 mob-dip：" % f)
            for line in txt.splitlines():
                if "mob-dip" in line or "mob_dip" in line:
                    print("      %s" % line.strip()[:150])
print()
print("=" * 92)
print("比两臂 `series.csv` 是否逐位相同（若同 ⇒ `dip` 在该区间未生效）")
print("=" * 92)
data = {}
for t in TAGS:
    p = os.path.join(ROOT, "dry_%s" % t, "series.csv")
    if os.path.exists(p):
        data[t] = [r for r in csv.DictReader(open(p, encoding="utf-8"))]
for i in range(len(TAGS)):
    for j in range(i + 1, len(TAGS)):
        a, b = TAGS[i], TAGS[j]
        if a not in data or b not in data:
            continue
        ra, rb = data[a], data[b]
        n = min(len(ra), len(rb))
        same = 0
        diff0 = None
        for k in range(n):
            if ra[k] == rb[k]:
                same += 1
            elif diff0 is None:
                diff0 = k
        print("  %-6s vs %-6s ：前 %d 行里**逐位相同 %d 行**（%.0f%%）%s"
              % (a, b, n, same, 100.0 * same / max(n, 1),
                 '' if diff0 is None else '，首个不同在第 %d 行' % diff0))
