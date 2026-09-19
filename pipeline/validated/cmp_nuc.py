#!/usr/bin/env python3
"""比对「有粗化 / 无粗化」两个形核算例的守恒漂移与晶粒数。"""
import csv
import os
import sys

RUN = "/root/work/nucchk/run"
for tag, fn in (("有粗化 (0.1)", "out_nuc.csv"), ("无粗化 (0.0)", "out_noc.csv")):
    f = os.path.join(RUN, fn)
    if not os.path.exists(f):
        print("%s: 没有 %s" % (tag, fn))
        continue
    r = list(csv.DictReader(open(f)))
    if not r:
        continue
    ks = [c for c in r[0] if "total_solute" in c][0]
    kg = [c for c in r[0] if "grain_tracker" in c]
    ke = [c for c in r[0] if "n_elem" in c]
    kg, ke = (kg[0] if kg else None), (ke[0] if ke else None)
    v0 = float(r[0][ks])
    drift = abs(float(r[-1][ks]) - v0) / abs(v0)
    seq = [x.get(kg, "?") for x in r] if kg else []
    ne = [x.get(ke, "?") for x in r] if ke else []
    print("  %-14s 行数=%-3d 末 t=%-10s 漂移=%.2e" %
          (tag, len(r), r[-1].get("time"), drift))
    print("     晶粒数序列: %s" % seq)
    print("     n_elem    : %s" % ne)
