#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_blkcsv2.py <tag> [...] --- 读块的原始列（AGENTS.md §3.6：反复读到与 wc -l 一致）。"""
import csv
import os
import subprocess
import sys

TAGS = sys.argv[1:] or ["t5FIX", "t5BKMo", "t5ETAo"]
BASE = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_%s/series.csv"
COLS = ("step", "nslab_n", "nblk_sig", "n_var_sig", "blk_laths", "Vt")

for tag in TAGS:
    P = BASE % tag
    if not os.path.exists(P):
        print("%-8s ⚠ 无 CSV" % tag)
        continue
    nlines = int(subprocess.check_output(["wc", "-l", P]).split()[0])
    rows = []
    for _ in range(8):
        with open(P, "r", newline="", encoding="utf-8", errors="replace") as fh:
            rr = list(csv.DictReader(fh))
        if len(rr) >= len(rows):
            rows = rr
        if len(rows) >= nlines - 1:
            break
    full = len(rows) >= nlines - 1
    print("══ %s ══ wc -l=%d 解析=%d 一致=%s" % (tag, nlines, len(rows), full))
    if not rows:
        continue
    keep = [r for r in rows if (r.get("nblk_sig") or "").strip() != ""]
    show = keep if keep else rows
    last = None
    for r in show:
        line = "  step %-6s nslab=%-3s nblk=%-3s nvar=%-3s Vt=%-10s blk_laths=%s" % (
            r.get("step"), r.get("nslab_n"), r.get("nblk_sig"), r.get("n_var_sig"),
            (r.get("Vt") or "")[:9], r.get("blk_laths"))
        if line != last:
            print(line)
        last = line
    print("  （共 %d 行有块统计；末行 step=%s）" % (len(keep), rows[-1].get("step")))
