#!/usr/bin/env python3
"""查 k_eff vs s 各算例的实际轨迹 —— 判断有没有跑到稳态。"""
import csv
import os

ROOT = "/root/work/keff_s"
for tag in ("s1", "s1000"):
    f = os.path.join(ROOT, tag, "case_out.csv")
    if not os.path.exists(f):
        print(tag, "没有 csv")
        continue
    r = list(csv.DictReader(open(f)))
    print("=== %s: %d 行 ===" % (tag, len(r)))
    print("  列:", list(r[0]))
    idx = [0, 1, len(r) // 2, len(r) - 1]
    for i in idx:
        if i >= len(r):
            continue
        x = r[i]
        print("   t=%-14s c_max=%-12s c_solid=%-12s c_far=%-12s total=%-12s solid_len=%-12s dt=%s" % (
            x.get("time"), x.get("c_max"), x.get("c_solid"), x.get("c_far"),
            x.get("total_c"), x.get("solid_len"), x.get("dt")))
    print()
