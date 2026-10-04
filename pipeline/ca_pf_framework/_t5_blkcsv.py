#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 t5N276F 的 series.csv 里的 **块内板条数分布**（blk_laths）—— 核对 B=3 是否被兑现。
AGENTS.md §3.6：/mnt/f 的 9p 读会静默给旧数据 ⇒ 反复读到与 wc -l 一致为止。
"""
import csv
import os
import subprocess
import sys

P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_t5N276F/series.csv"
if not os.path.exists(P):
    print("不存在：", P)
    sys.exit(1)

nlines = int(subprocess.check_output(["wc", "-l", P]).split()[0])
rows = []
for _ in range(6):
    with open(P, "r", newline="", encoding="utf-8", errors="replace") as fh:
        rr = list(csv.DictReader(fh))
    if len(rr) >= len(rows):
        rows = rr
    if len(rows) >= nlines - 1:
        break
print("wc -l = %d ；解析出 %d 行（一致=%s）" % (nlines, len(rows), len(rows) >= nlines - 1))
if not rows:
    sys.exit(1)
print("列名 =", list(rows[0].keys()))


def g(r, k):
    v = r.get(k, "")
    return v


keys = [k for k in rows[0].keys() if k in ("step", "nslab_n", "nblk_sig", "n_var_sig", "blk_laths")]
if not keys:
    print("⚠ CSV 里没有 blk_laths 列")
    sys.exit(0)

print()
print("=== 块内板条数分布轨迹 ===")
for r in rows:
    print("  step %-6s nslab=%-3s nblk=%-3s nvar=%-3s blk_laths=%s"
          % (g(r, "step"), g(r, "nslab_n"), g(r, "nblk_sig"), g(r, "n_var_sig"), g(r, "blk_laths")))
