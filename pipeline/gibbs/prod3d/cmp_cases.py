#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按**列名**对比多个算例的末态（不再按列序号切 —— 两个算例的列布局可能不同）。

⚠ 本文件是因为"按序号切列"踩过两次坑（列错位 ⇒ 把 gam1_max 当成 gam1_int 报警）才写的。

用法: python3 cmp_cases.py <case_out.csv> [<case_out.csv> ...] [--cols=a,b,c]
"""
import csv
import os
import sys

DEFAULT = ["time", "depletion", "c_int_pp", "c_min", "c_max",
           "gam0_int", "gam0_max", "gam1_int", "gam1_max"]


def read_last(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else {}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cols = DEFAULT
    for a in sys.argv[1:]:
        if a.startswith("--cols") and "=" in a:
            cols = a.split("=", 1)[1].split(",")
    paths = []
    for p in args:
        if not os.path.exists(p):
            print("  **缺文件** %s" % p)
            continue
        paths.append((os.path.basename(os.path.dirname(os.path.abspath(p))), read_last(p)))
    print("=" * 100)
    print("按列名对比末态（%d 个算例）" % len(paths))
    print("=" * 100)
    for name, r in paths:
        print("  [%s]" % name)
        for c in cols:
            if c in r:
                print("      %-14s = %s" % (c, r[c]))
        print()


if __name__ == "__main__":
    main()
