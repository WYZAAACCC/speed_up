#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_show_evloc_pts.py —— 用 csv 模块正确读 `evloc_pts`（避免手工逗号切分）。"""
import csv
import os
import sys

tag = sys.argv[1] if len(sys.argv) > 1 else "dry_evlocpts"
p = "/mnt/f/speed_up/_exp/_bk_t5/%s/series.csv" % tag
if not os.path.exists(p):
    sys.exit(f"不存在: {p}")
rows = list(csv.DictReader(open(p, encoding="utf-8")))
for r in rows:
    pts = r.get("evloc_pts", "")
    print(f"step={r.get('step'):>4}  n={r.get('evloc_n')}  "
          f"min_nm={r.get('evloc_min_nm')!r}  same_min_nm={r.get('evloc_same_min_nm')!r}"
          f"  dup={r.get('evloc_dup')}")
    if pts:
        for one in pts.split("|"):
            print(f"        {one}")
    print()
