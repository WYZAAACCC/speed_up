#!/usr/bin/env python3
"""读生产 AMR 三档对照的结果。"""
import csv
import os

RUN = "/root/work/prodamr/run"
print("  %-8s %-8s %-16s %-14s %-16s %-12s" %
      ("档", "行数", "n_elem 首→末", "AMR", "total_solute 漂移", "liquid_frac"))
print("  " + "-" * 80)
base = {}
for d in ("uniform", "amr1", "amr2"):
    f = os.path.join(RUN, f"out_{d}.csv")
    if not os.path.exists(f):
        print("  %-8s 还没跑完" % d)
        continue
    r = list(csv.DictReader(open(f)))
    if not r:
        continue
    def col(n):
        k = [c for c in r[0] if n in c]
        return k[0] if k else None
    ke, ks, kl = col("n_elem"), col("total_solute"), col("liquid_frac")
    i0 = 1 if len(r) > 1 else 0
    e0, e1 = (r[i0][ke], r[-1][ke]) if ke else ("?", "?")
    amr = ("**已生效**" if e0 != e1 else "未生效") if ke else "?"
    try:
        v0, v1 = float(r[0][ks]), float(r[-1][ks])
        dr = "%.2e" % (abs(v1 - v0) / abs(v0)) if v0 else "0"
    except (TypeError, ValueError):
        dr = "?"
    lf = r[-1][kl] if kl else "?"
    print("  %-8s %-8d %-16s %-14s %-16s %-12s" % (d, len(r), f"{e0}→{e1}", amr, dr, lf))
    if kl:
        base[d] = float(lf)
print()
if "uniform" in base:
    for d in ("amr1", "amr2"):
        if d in base:
            print("  %s 的 liquid_frac 与 uniform 差 %.3f%%（判据 5%%）" %
                  (d, 100 * abs(base[d] - base["uniform"]) / abs(base["uniform"])))
