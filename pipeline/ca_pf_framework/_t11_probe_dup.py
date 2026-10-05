#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_probe_dup.py —— 找出 `verdict2.tsv` 里 451 行 vs 450 篇的差异行。"""
import csv
import os
from collections import Counter

P = "/mnt/f/speed_up/_litidx/verdict2.tsv"
PDFDIR = "/mnt/f/参考论文/马氏体仿真"

with open(P, encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh, delimiter="\t"))
real = sorted(f for f in os.listdir(PDFDIR) if f.lower().endswith(".pdf"))

print(f"verdict2.tsv 行数 = {len(rows)}   目录 PDF 数 = {len(real)}")
c = Counter(r["file"] for r in rows)
dups = [(k, v) for k, v in c.items() if v > 1]
print(f"\n文件名重复的条目（{len(dups)} 条）：")
for k, v in dups:
    print(f"   ×{v}  {k!r}  len={len(k)}")
    for r in rows:
        if r["file"] == k:
            print(f"        cat={r.get('category')!r:10} doi={r.get('doi','')!r:36} "
                  f"why={str(r.get('why'))[:40]!r}")

vf = set(c)
rf = set(real)
print(f"\n在 verdict 里但目录里没有（{len(vf-rf)} 条）：")
for k in sorted(vf - rf):
    print(f"   {k!r}")
print(f"\n在目录里但 verdict 里没有（{len(rf-vf)} 条）：")
for k in sorted(rf - vf):
    print(f"   {k!r}")
