#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_ab_diff.py <tagA> <tagB> —— A/B 两臂**共有 step** 的列对比（找"机制是否生效"的签名）。

用法：只比 **两臂都有的 step**（避免把"进度不同"误当"机制不同"，`P8`）。
"""
import csv
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
COLS = ["Vt", "nslab_n", "nf3_col", "n_obl", "dG_obl", "ed_obl",
        "dG_tip", "dG_side", "dG_wide", "dG_max_Jm3",
        "n_tip", "n_side", "n_wide", "ncomp_all", "ncompbig_max"]
A, B = sys.argv[1], sys.argv[2]


def load(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    if not os.path.exists(p):
        return {}
    d = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        d[int(r['step'])] = r
    return d


a, b = load(A), load(B)
common = sorted(set(a) & set(b))
print("=" * 100)
print("A=%s（%d 步）  B=%s（%d 步）  **共有 step = %s**" % (A, len(a), B, len(b), common))
print("=" * 100)
if not common:
    sys.exit("无共有 step ⇒ 无法比（跑一会儿再看）")
print("  %-16s %-14s %-14s %-9s" % ('列', 'A=' + A, 'B=' + B, '比值 B/A'))
for c in COLS:
    va, vb = a[common[-1]].get(c, ''), b[common[-1]].get(c, '')
    try:
        fa, fb = float(va), float(vb)
        r = ('%.3f' % (fb / fa)) if abs(fa) > 1e-300 else '—'
        flag = '  ★**不同**' if abs(fb - fa) > 1e-12 * max(abs(fa), abs(fb), 1) else '  （相同）'
        print("  %-16s %-14.6g %-14.6g %-9s%s" % (c, fa, fb, r, flag))
    except (TypeError, ValueError):
        print("  %-16s %-14s %-14s %-9s" % (c, va or '—', vb or '—', '—'))
print("\n  说明：**共有 step = %s**（取最后一步 %d 比）；"
      "若某列两臂**逐位相同** ⇒ 该机制**未在该列上留下签名**。" % (common, common[-1]))
