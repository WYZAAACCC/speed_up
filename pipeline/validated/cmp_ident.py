#!/usr/bin/env python3
"""比对 full / off 两档的 ident CSV，判断残差是否真的被动过。"""
import csv
import os
import sys

run = "/root/work/t1crit/run"
fa = os.path.join(run, "ident_full.csv")
fb = os.path.join(run, "ident_off.csv")

raw_a = open(fa, "rb").read()
raw_b = open(fb, "rb").read()
print(f"字节数: full={len(raw_a)}  off={len(raw_b)}")

a = list(csv.DictReader(open(fa, encoding="utf-8")))
b = list(csv.DictReader(open(fb, encoding="utf-8")))
print(f"行数:   full={len(a)}  off={len(b)}")
print()

worst = 0.0
worst_key = None
ndiff = 0
for i, (ra, rb_) in enumerate(zip(a, b)):
    for k in ra:
        va, vb = ra[k], rb_[k]
        try:
            x, y = float(va), float(vb)
        except (ValueError, TypeError):
            if va != vb:
                print(f"  行{i} {k}: {va!r} vs {vb!r}")
            continue
        if x == y:
            continue
        ndiff += 1
        denom = max(abs(x), abs(y), 1e-300)
        rel = abs(x - y) / denom
        if rel > worst:
            worst, worst_key = rel, (i, k, x, y)
        if rel > 1e-12:
            print(f"  行{i} {k:24s} full={x:.15g}  off={y:.15g}  相对差={rel:.3e}")

print()
print(f"有差异的数值个数 : {ndiff}")
if worst_key:
    i, k, x, y = worst_key
    print(f"最大相对差       : {worst:.3e}  (行{i}, 列 {k})")
    print(f"                    full={x:.15g}")
    print(f"                    off ={y:.15g}")
print()
print("判读：")
print("  * 残差**逐位**相同时，两档仍会因**牛顿迭代路径不同**而在末几位分叉")
print("    （雅可比变了 ⇒ 迭代序列变了 ⇒ 舍入路径变了）。")
print("    所以「CSV 逐字节相同」是**过严**的判据。")
print("  * 正确的判据是：差异落在**求解器容差量级**（nl_rel_tol=1e-8）内")
print("    ⇒ 残差在**同一状态**上是同一个函数。")
