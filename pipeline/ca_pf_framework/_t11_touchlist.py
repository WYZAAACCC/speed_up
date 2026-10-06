#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_touchlist.py <tag> —— 列出 `box_touch` 的**确切**翻转点（不猜）。"""
import csv
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
for tag in (sys.argv[1:] or ["B40"]):
    t = tag[4:] if tag.startswith('dry_') else tag
    p = os.path.join(ROOT, "dry_%s" % t, "series.csv")
    if not os.path.exists(p):
        print("【%s】无 CSV" % t)
        continue
    rows = []
    for r in csv.DictReader(open(p, encoding="utf-8")):
        try:
            rows.append((int(r['step']), r.get('box_touch', '?'),
                         r.get('box_touch_core', '?'), float(r.get('Vt') or 'nan')))
        except (KeyError, ValueError):
            pass
    print("=" * 76)
    print("【%s】`box_touch` 全部取值（%d 行）" % (t, len(rows)))
    print("=" * 76)
    seq = [(s, bt) for s, bt, _, _ in rows]
    first1 = next((s for s, bt in seq if str(bt) == '1'), None)
    print("  ⇒ **首次 `box_touch=1` 的 step = %s**" % first1)
    print("  %-7s %-11s %-16s %s" % ('step', 'box_touch', 'box_touch_core', 'Vt'))
    for s, bt, bc, vt in rows:
        if s % 100 == 0 or (first1 is not None and abs(s - first1) <= 25):
            print("  %-7d %-11s %-16s %.6g" % (s, bt, bc, vt))
