#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看 1D 移动前沿剖面有没有到稳态：L_eff 随时间还在不在变。"""
import csv
import glob
import math
import os
import sys

C0 = 0.036
XI = 2.0e-6
LMOB = 5.833e-4
DG = 3.6e5
V = 3.0 * XI * LMOB * DG
D = 2.8e-9 * 0.9
DC = D / V
KE = 0.630252
TOT = 2 * 2.8e-9 * 0.264 * C0 / V

d = sys.argv[1]
fs = sorted(glob.glob(os.path.join(d, "*prof*.csv")))
print(f"  {d}: 找到 {len(fs)} 个剖面文件")
if not fs:
    print("  目录内容：", sorted(os.listdir(d))[:6])
    sys.exit(0)

print(f"  δ_c = {DC*1e6:.4f} µm   精确预测 ∫(c−c0)dx = {TOT:.5e}   k_e = {KE:.6f}")
print()
print("  %-6s %-10s %-10s %-13s %-10s %-8s %s" %
      ("step", "c_max", "c(x=0)", "∫(c−c0)dx", "L_eff[µm]", "k_eff", "∫/预测"))
print("  " + "-" * 74)
idx = list(range(0, len(fs), max(1, len(fs) // 14)))
if len(fs) - 1 not in idx:
    idx.append(len(fs) - 1)
for i in idx:
    r = list(csv.DictReader(open(fs[i])))
    if not r:
        continue
    xs = [float(x["x"]) for x in r]
    cs = [float(x["c"]) for x in r]
    cmax = max(cs)
    tot = sum(0.5 * ((cs[k] - C0) + (cs[k + 1] - C0)) * (xs[k + 1] - xs[k])
              for k in range(len(xs) - 1))
    L = tot / (cmax - C0) if cmax > C0 else float("nan")
    tag = os.path.basename(fs[i])
    m = tag.rfind("_")
    print("  %-6s %-10.6f %-10.6f %-13.5e %-10.3f %-8.5f %.4f" %
          (tag[m + 1:-4], cmax, cs[0], tot, L * 1e6, C0 / cmax, tot / TOT))
print()
print(f"  L_eff/δ_c 末态 = {(tot/(cmax-C0))/DC:.2f}（目标 1.00）")
