#!/usr/bin/env python3
"""看形核算例的守恒漂移轨迹 —— 是 AMR 重映射的误差，还是形核那一步引入的。"""
import csv
import os

f = "/root/work/nucchk/run/out_nuc.csv"
r = list(csv.DictReader(open(f)))
print("  行数 %d" % len(r))
ks = [c for c in r[0] if "total_solute" in c][0]
kg = [c for c in r[0] if "grain_tracker" in c]
ke = [c for c in r[0] if "n_elem" in c]
kg = kg[0] if kg else None
ke = ke[0] if ke else None
v0 = float(r[0][ks])
print("  %-14s %-16s %-10s %-10s %s" % ("t", "total_solute", "相对漂移", "晶粒数", "n_elem"))
print("  " + "-" * 64)
for x in r:
    v = float(x[ks])
    print("  %-14s %-16.10g %-10.2e %-10s %s" % (
        x.get("time"), v, abs(v - v0) / abs(v0),
        x.get(kg, "?") if kg else "?", x.get(ke, "?") if ke else "?"))
