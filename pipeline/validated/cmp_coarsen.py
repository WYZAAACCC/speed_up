#!/usr/bin/env python3
"""粗化比例对守恒漂移与单元数的影响。"""
import csv
import os

RUN = "/root/work/nucchk/run"
CASES = (("0.00", "out_noc.csv"), ("0.02", "out_c0.02.csv"),
         ("0.05", "out_c0.05.csv"), ("0.10", "out_nuc.csv"))
print("  %-8s %-8s %-12s %-16s %s" % ("coarsen", "行数", "末 t", "守恒漂移", "n_elem 末"))
print("  " + "-" * 62)
for tag, fn in CASES:
    f = os.path.join(RUN, fn)
    if not os.path.exists(f):
        print("  %-8s 没有 %s" % (tag, fn)); continue
    r = list(csv.DictReader(open(f)))
    if not r:
        continue
    ks = [c for c in r[0] if "total_solute" in c][0]
    ke = [c for c in r[0] if "n_elem" in c]
    ke = ke[0] if ke else None
    v0 = float(r[0][ks])
    drift = abs(float(r[-1][ks]) - v0) / abs(v0)
    mark = "✅" if drift <= 1e-8 else "❌ 超判据"
    print("  %-8s %-8d %-12s %-16.2e %-8s %s" %
          (tag, len(r), r[-1].get("time"), drift,
           r[-1].get(ke, "?") if ke else "?", mark))
print()
print("  判据：T2 要求 total_solute 漂移 ≤ 1e-8")
