#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_csv_read.py <tag> [...] —— 按**列名**读 series.csv 的关键量（避免列号错位）。"""
import csv
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
COLS = ("step", "wall_s", "Vt", "nslab_n", "nslab_nu", "nf3_col", "runs",
        "vols", "ths", "ncomp_min", "ncomp_max", "ncompbig_max", "ncomp_all",
        "box_touch", "wrap_any", "wrap_n", "blk_laths", "blk_vars", "n_var_sig")
for tag in (sys.argv[1:] or ["c2B647", "c2Eq0"]):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    print("=" * 104)
    if not os.path.exists(p):
        print("【%s】无 series.csv" % tag)
        continue
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    print("【%s】%d 行" % (tag, len(rows)))
    for r in rows:
        print("  step=%-5s Vt=%-24s nslab_n=%-3s nslab_nu=%-3s nf3_col=%-3s runs=%-12s"
              % (r.get('step'), r.get('Vt'), r.get('nslab_n'),
                 r.get('nslab_nu'), r.get('nf3_col'), r.get('runs')))
        print("        vols=%-46s" % (r.get('vols') or ''))
        print("        ths =%-46s  ncomp(min/max/big/all)=%s/%s/%s/%s"
              % ((r.get('ths') or '')[:46], r.get('ncomp_min'), r.get('ncomp_max'),
                 r.get('ncompbig_max'), r.get('ncomp_all')))
