#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_verify_run.py <tag> —— 按硬步骤 A/C 核实一个算例的**生效配置**与**列接线**。"""
import csv
import json
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD2"
d = next((os.path.join(b, TAG) for b in BASES
          if os.path.isdir(os.path.join(b, TAG))), None)
if d is None:
    sys.exit("**找不到 %s**" % TAG)
print("目录 =", d)

mj = os.path.join(d, "meta.json")
if os.path.exists(mj):
    j = json.load(open(mj, encoding="utf-8"))
    a = j.get("exp_args", j)
    print("\n=== meta.json 关键项（硬步骤 A：唯一权威）===")
    for k in ("wrap_every", "wrap-every", "evloc", "burst_km", "burst-km",
              "nuc_shape", "nuc-shape", "nuc_block_target", "nuc-block-target",
              "alpha_km", "alpha-km", "plate_T", "plate-T", "plate_L", "plate-L",
              "plate_W", "plate-W", "eng_t_nm", "eng-t-nm", "eng_elong",
              "eng-elong", "steps", "T_end", "T-end", "nuc_law", "nuc-law",
              "qs_clock", "qs_dT", "nuc_block_parallel"):
        if k in a:
            print("  %-20s = %r" % (k, a[k]))
    print("  （exp_args 共 %d 项）" % len(a))
else:
    print("**meta.json 尚未写出**")

sp = os.path.join(d, "series.csv")
if os.path.exists(sp):
    with open(sp, encoding="utf-8") as fh:
        h = (fh.readline() or "").strip()
    cols = h.split(",") if h else []
    print("\n=== series.csv 列数 = %d ===" % len(cols))
    for c in ("wrap_any", "wrap_n", "wrap_fields", "evloc_dup", "evloc_n",
              "evloc_pairs", "evloc_min_nm", "blk_laths", "blk_span_nm",
              "nslab_nu", "Vt", "step"):
        print("  %-16s %s" % (c, ("第 %d 列" % cols.index(c)) if c in cols
                              else "**不在**"))
    rows = list(csv.DictReader(open(sp, encoding="utf-8")))
    print("  数据行数 = %d" % len(rows))
else:
    print("**series.csv 尚未写出**")
print("\n文件：", sorted(os.listdir(d)))
