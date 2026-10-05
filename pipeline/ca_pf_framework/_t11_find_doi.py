#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_doi.py —— 从指定 PDF 里抓 DOI / 期刊 / 卷页 / 作者（用于规范引用）。

用法: _t11_find_doi.py <序号>
"""
import os
import re
import sys

import pymupdf

PDFDIR = "/mnt/f/参考论文/马氏体仿真"
files = sorted(f for f in os.listdir(PDFDIR) if f.lower().endswith(".pdf"))

idx = int(sys.argv[1])
fn = files[idx]
p = os.path.join(PDFDIR, fn)
print(f"[{idx}] {fn}\n")

with pymupdf.open(p) as d:
    n = d.page_count
    # 每页都搜（页眉/页脚/首页/末页）
    allt = []
    for i in range(n):
        allt.append(d[i].get_text())
full = "\n".join(allt)

print("=== DOI 类命中 ===")
for m in re.finditer(r"(https?://doi\.org/[^\s]+|10\.\d{4,9}/[^\s,;)\]]+)", full):
    print("  ", m.group(0))
print("\n=== 期刊/卷页 行 ===")
for pat in (r"[A-Z][A-Za-z&\s\.]{6,60}\s+\d{2,4}\s*\(\s*20\d\d\s*\)\s*[\d,\s–\-]+",
            r"Acta Materialia[^\n]{0,60}", r"Computational Materials Science[^\n]{0,60}",
            r"Materials? (&|and) Design[^\n]{0,60}", r"Volume \d+[^\n]{0,60}",
            r"Received[^\n]{0,80}", r"Available online[^\n]{0,60}"):
    hits = re.findall(pat, full)
    for h in list(dict.fromkeys(hits))[:6]:
        print(f"  [{pat[:22]}…] {h.strip()[:110]}")

print("\n=== 首页前 700 字符（原始，含可能的页眉）===")
print(repr(allt[0][:700]))
print("\n=== 末页前 900 字符 ===")
print(repr(allt[-1][:900]))
