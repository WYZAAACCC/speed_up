#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_pdf_grep.py —— 用 PyMuPDF 读 PDF 并抽含关键词的行（本仓库标准读数通路）。

用法: _t11_pdf_grep.py <pdf> <正则> [上下文行数]
"""
import re
import sys

import fitz

p = sys.argv[1]
pat = re.compile(sys.argv[2], re.I)
ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 2
doc = fitz.open(p)
print(f"=== {p}  共 {doc.page_count} 页 ===")
n = 0
for pno in range(doc.page_count):
    lines = doc[pno].get_text().splitlines()
    for i, ln in enumerate(lines):
        if pat.search(ln):
            n += 1
            lo, hi = max(0, i - ctx), min(len(lines), i + ctx + 1)
            print(f"\n--- p{pno+1} L{i+1} ---")
            for j in range(lo, hi):
                print("   " + lines[j].strip()[:160])
print(f"\n命中 {n} 行")
