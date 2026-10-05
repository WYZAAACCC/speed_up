#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_show_evloc.py —— 显示某算例 series.csv 的 evloc_* 四列（R623 G5b 取证）。"""
import csv
import os
import sys

tag = sys.argv[1] if len(sys.argv) > 1 else "dry_evlocsmoke"
p = "/mnt/f/speed_up/_exp/_bk_t5/%s/series.csv" % tag
print(f"文件: {p}  exists={os.path.exists(p)}")
if not os.path.exists(p):
    sys.exit(1)
rows = list(csv.DictReader(open(p, encoding="utf-8")))
cols = [c for c in rows[0].keys() if c.startswith("evloc")]
print(f"行数 = {len(rows)}；evloc 列（{len(cols)}）: {cols}")
if not cols:
    sys.exit("⇒ **没有 evloc 列** ⇒ 接线未生效")
print()
print("  %-6s %-12s %-6s %-6s %-14s %s"
      % ("step", "min_nm", "dup", "n", "same_min_nm", "pairs"))
for r in rows:
    print("  %-6s %-12s %-6s %-6s %-14s %s"
          % (r.get("step"), repr(r.get("evloc_min_nm")), r.get("evloc_dup"),
             r.get("evloc_n"), repr(r.get("evloc_same_min_nm")),
             r.get("evloc_pairs")))
last = rows[-1]
print()
print("★ 判据（R623 §7 第 8 条）：`evloc_dup`（**跨变体**落点重合对数）应为 **0**")
print(f"   末行 evloc_dup = {last.get('evloc_dup')!r}   "
      f"evloc_n = {last.get('evloc_n')!r}")
print(f"   evloc_min_nm      = {last.get('evloc_min_nm')!r}（全体落点对最小距离，仅诊断）")
print(f"   evloc_same_min_nm = {last.get('evloc_same_min_nm')!r}"
      f"（**同变体**落点对最小距离 —— 与 plate_T 对照）")
try:
    _dup = int(last.get("evloc_dup") or 0)
    print("   ⇒ " + ("**PASS：无重合** ⇒ 「同一位置反复出事件」**不成立**"
                     if _dup == 0 else
                     f"**FAIL：检出 {_dup} 对重合** ⇒ G5b 的钝化缺口**成立**，需修"))
except (TypeError, ValueError):
    print("   ⇒ 无法判定（evloc_dup 非整数）")
