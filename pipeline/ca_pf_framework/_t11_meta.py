#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_meta.py —— 读指定 PDF 的**元数据**与首页/末页特征，用于确定规范引用。

用法: _t11_meta.py "<精确文件名>"
"""
import os
import re
import sys

import pymupdf

PDFDIR = "/mnt/f/参考论文/马氏体仿真"
fn = sys.argv[1]
p = os.path.join(PDFDIR, fn)
if not os.path.exists(p):
    print(f"!! 不存在: {p}")
    raise SystemExit(1)

with pymupdf.open(p) as d:
    print("=== doc.metadata ===")
    for k, v in (d.metadata or {}).items():
        print(f"  {k:>16}: {v}")
    print(f"  页数: {d.page_count}")
    # 首页/末页的少量行 + 页脚（常含期刊卷页）
    for tag, i in (("首页", 0), ("第二页", 1), ("末页", d.page_count - 1)):
        t = d[i].get_text()
        lines = [x.strip() for x in t.splitlines() if x.strip()]
        print(f"\n=== {tag} 前 8 行 ===")
        for x in lines[:8]:
            print("   ", x[:120])
        print(f"--- {tag} 末 8 行 ---")
        for x in lines[-8:]:
            print("   ", x[:120])
    full = "\n".join(d[i].get_text() for i in range(d.page_count))

print("\n=== 全文里的 DOI / 期刊线索 ===")
pats = [r"10\.\d{4,9}/[^\s,;)\]]+", r"doi[^\n]{0,80}",
        r"(Acta Materialia|Computational Materials Science|Materials? (&|and) Design|"
        r"Scripta Materialia|Materials Science and Engineering[ A-Z]*|"
        r"Journal of Alloys and Compounds|ISIJ International|Materials Letters|"
        r"Metallurgical and Materials Transactions[ A-Z]*|"
        r"Modelling and Simulation[^\n]{0,40})",
        r"(Vol\.?|Volume)\s*\d{1,4}[^\n]{0,40}",
        r"(Received|Accepted|Available online|Article history)[^\n]{0,80}",
        r"\b(19|20)\d\d\b[^\n]{0,10}(pp\.|\d{1,5})"]
for pat in pats:
    hits = list(dict.fromkeys(m.group(0).strip() for m in re.finditer(pat, full, re.I)))
    if hits:
        print(f"\n  [{pat[:34]}…]")
        for h in hits[:6]:
            print("     ", h[:120])
