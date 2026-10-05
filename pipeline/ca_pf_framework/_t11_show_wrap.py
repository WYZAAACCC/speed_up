#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_show_wrap.py —— 显示某算例 series.csv 里的 wrap 三列。"""
import csv
import os
import sys

tag = sys.argv[1] if len(sys.argv) > 1 else "dry_wrapsmoke"
p = "/mnt/f/speed_up/_exp/_bk_t5/%s/series.csv" % tag
print(f"文件: {p}  exists={os.path.exists(p)}")
if not os.path.exists(p):
    sys.exit(1)
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print(f"行数 = {len(rows)}")
cols = [c for c in rows[0].keys() if "wrap" in c]
print(f"含 'wrap' 的列（{len(cols)}）: {cols}")
if not cols:
    print("⇒ **没有 wrap 列** ⇒ 接线未生效")
    sys.exit(1)
print()
for r in rows:
    print("  step=%-5s wrap_any=%-14r wrap_n=%-4r wrap_fields=%r"
          % (r.get("step"), r.get("wrap_any"), r.get("wrap_n"),
             r.get("wrap_fields")))
# 分辨力自检
vals = [str(r.get("wrap_any", "")) for r in rows]
n_nonempty = sum(1 for v in vals if v not in ("", "None"))
print(f"\n★ 非空（= 检出绕盒）的行数 = {n_nonempty} / {len(rows)}")
print("   ⇒ " + ("**有分辨力**（至少检出过绕盒）✅" if n_nonempty
                 else "全为空 ⇒ 本算例未检出绕盒（**需换几何做正对照**）"))
