#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_series_peek.py —— 用 `csv` 模块**按列名**读生产 series.csv（绝不用 -split/正则）。"""
import csv
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD1"
p = next((os.path.join(b, TAG, "series.csv") for b in BASES
          if os.path.exists(os.path.join(b, TAG, "series.csv"))), None)
if p is None:
    sys.exit("**找不到 series.csv**")
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print(f"【{TAG}】series.csv 行数 = {len(rows)}   文件 = {p}")
cols = ["step", "t_s", "wall_s", "Vt", "nslab_nu", "nslab_n", "nblk_sig",
        "blk_laths", "blk_span_nm", "blk_nlath", "blk_nprof", "n_var_sig", "f_var"]
for r in rows:
    print("  " + "  ".join(f"{c}={r.get(c)!r}" for c in cols if c in r))
if not rows:
    print("  （无数据行）")
