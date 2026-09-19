#!/usr/bin/env python3
"""读 kappa_c 代价核算的三个 CSV，输出关键指标。"""
import csv
import os

RUN = "/root/work/kc0cost/run"

print("  %-6s %-7s %-11s %-9s %-11s %-11s" %
      ("档", "行数", "末态 t", "末 n_elem", "Σ 线性迭代", "Σ 非线性"))
print("  " + "-" * 62)
for t in ("base", "kc0", "do3"):
    f = os.path.join(RUN, "out_%s.csv" % t)
    if not os.path.exists(f):
        print("  %-6s 还没跑完" % t)
        continue
    r = list(csv.DictReader(open(f)))
    if not r:
        print("  %-6s 空" % t)
        continue
    last = r[-1]
    tl = sum(int(x.get("n_lin") or 0) for x in r)
    tn = sum(int(x.get("n_nonlin") or 0) for x in r)
    print("  %-6s %-7d %-11s %-9s %-11d %-11d" %
          (t, len(r), last.get("time", "?"), last.get("n_elem", "?"), tl, tn))

print()
print("  注：`n_lin`/`n_nonlin` 是 MOOSE 的累积计数列，逐行求和无意义；")
print("      真正要比的是**每次线性求解的迭代次数**与**墙钟**，见 run_*.log 的 --timing 表。")
