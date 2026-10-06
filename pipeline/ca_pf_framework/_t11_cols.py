#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cols.py <tag> —— 列出 series.csv 的**全部列名**（供 (2) 能量分解挑列）。"""
import csv
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
tag = (sys.argv[1] if len(sys.argv) > 1 else "t5AB_B")
tag = tag[4:] if tag.startswith('dry_') else tag
p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
if not os.path.exists(p):
    sys.exit("无 %s" % p)
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print("【%s】%d 行，%d 列" % (tag, len(rows), len(rows[0]) if rows else 0))
KEY = ("el", "E_", "dG", "df", "chem", "gamma", "f3_area", "f1_area",
       "Vt", "area", "psi", "mob", "ed_", "thick", "t_")
for i, c in enumerate(rows[0].keys() if rows else []):
    hit = any(k.lower() in c.lower() for k in KEY)
    print("  %3d  %-22s %s" % (i, c, '★' if hit else ''))
