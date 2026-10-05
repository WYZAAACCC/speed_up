#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dbg_template.py —— 定位 TEMPLATE 误判是哪条规则命中的（量具自检）。"""
import csv
import io
import re
import sys

sys.path.insert(0, ".")
import importlib.util

spec = importlib.util.spec_from_file_location("v2", "_t11_verdict2.py")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

rows = []
with open("/mnt/f/speed_up/_litidx/verdict2.tsv", encoding="utf-8") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        if r["category"] == "TEMPLATE":
            rows.append(r)

print(f"TEMPLATE 共 {len(rows)} 条")
from collections import Counter
c = Counter()
ex = {}
for r in rows:
    fn, title = r["file"], r["title"]
    which = []
    if v2.TEMPLATE.match(fn):
        which.append("TEMPLATE.match(file)")
    m = v2.TEMPLATE_TITLE.search(title)
    if m:
        which.append(f"TEMPLATE_TITLE.search(title) -> {m.group(0)!r}")
    m2 = v2.TEMPLATE_TITLE.search(fn)
    if m2:
        which.append(f"TEMPLATE_TITLE.search(file) -> {m2.group(0)!r}")
    for w in which:
        c[w.split(" -> ")[0]] += 1
        ex.setdefault(w.split(" -> ")[0], (fn, title, w))
print("\n=== 命中规则计数 ===")
for k, n in c.most_common():
    print(f"  {n:4d}  {k}")
print("\n=== 每类一个例子 ===")
for k, (fn, title, w) in ex.items():
    print(f"  [{k}]\n     file={fn}\n     title={title[:110]!r}\n     hit={w}")
print("\n=== 按标题的 'volume' 命中样本 ===")
n = 0
for r in rows:
    m = re.search(r"volume \d+,", r["title"], re.I)
    if m:
        n += 1
        if n <= 6:
            print(f"  {r['file'][:60]:<60} | {r['title'][:90]!r}")
print(f"  共 {n} 条标题含 'volume N,'")
