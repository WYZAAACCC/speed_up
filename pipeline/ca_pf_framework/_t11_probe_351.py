#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_probe_351.py —— 读 351-360.pdf 的 DOI/标题/关键段（疑似 Murzinova 同刊后续工作）。"""
import os

import pymupdf

P = "/mnt/f/参考论文/马氏体仿真/351-360.pdf"
with pymupdf.open(P) as d:
    print(f"页数 {d.page_count}")
    t0 = d[0].get_text()
    print("\n=== 首页前 2200 字符 ===")
    print(t0[:2200])
    full = "\n".join(d[p].get_text() for p in range(min(d.page_count, 12)))
import re
print("\n=== DOI / 期刊 行 ===")
for m in re.finditer(r"(doi[^\n]{0,80}|10\.\d{4,5}/[^\s]+|Letters on Materials[^\n]{0,60})",
                     full, re.I):
    print("  ", m.group(0)[:110])

print("\n=== 关键词命中 ===")
for kw in ("martensit", "Ti-6Al-4V", "lath", "interface energy", "surface energy",
           "interfacial", "nucleation", "phase field", "misfit", "elastic",
           "titanium", "alpha", "beta", "γ", "J/m"):
    n = len(re.findall(re.escape(kw), full, re.I))
    if n:
        print(f"  {kw:<18} {n}")
