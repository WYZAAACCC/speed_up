#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_touchstep.py <tag>... —— 报每个臂**首次 `box_touch=1`** 的 step（找有效窗口上界）。

依据 `R647`：`box_touch=1` 之后形状读数不可作单根板条证据 ⇒ 必须逐臂标出。
"""
import csv
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
for tag in (sys.argv[1:] or ["L0", "B0", "B2", "B4", "E0", "L1", "B40", "P3", "P10", "P30"]):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    if not os.path.exists(p):
        print("  %-6s 无 CSV" % tag)
        continue
    first = None
    last = None
    with open(p, encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        key = "box_touch" if "box_touch" in cols else None
        if key is None:
            print("  %-6s CSV 里没有 box_touch 列" % tag)
            continue
        for r in rd:
            try:
                st = int(r["step"])
            except (KeyError, ValueError):
                continue
            last = st
            v = str(r.get(key, "")).strip()
            if v in ("1", "1.0", "True", "true") and first is None:
                first = st
    print("  %-6s 末 step=%-5s  首次 box_touch=1 @ step %s"
          % (tag, last, first if first is not None else "（全程 0）"))
