#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_prod_1d.sh 的分析：生产工作点上模型给多少溶质截留。

关键输出「低估倍数」= (1−k_eff_物理)/(1−k_eff_模型)：界面**排出**的溶质量 ∝ (1−k)，
所以这个倍数就是模型少排了多少溶质 ⇒ 微偏析被低估多少倍。
本项目要预测的正是微偏析（晶界偏析 Γ_GB 的来源）。
"""
import csv
import math
import os
import re
import sys

XI = 2.0e-6
K_C = 0.9
A = 0.264
C0 = 0.036
D = 2.8e-9 * 0.9
KE = 1.0 / (1.0 + 2 * A / K_C)
# 物理上的 Aziz 截留（a0 = 0.3 nm）：k(V) = (k_e + V/V_D)/(1 + V/V_D)
A0 = 3.0e-10


def last_prof(d):
    if not os.path.isdir(d):
        return None
    fs = [x for x in os.listdir(d) if "prof" in x and x.endswith(".csv")]
    if not fs:
        return None

    def num(f):
        m = re.search(r"_(\d+)\.csv$", f)
        return int(m.group(1)) if m else -1

    return os.path.join(d, max(fs, key=num))


def main(root, vlist, nx):
    dx = 4.0e-5 / float(nx)
    print(f"  k_e（模型设计值）= {KE:.6f}    dx = {dx:.3e} m")
    print()
    print("  %-10s %-11s %-9s %-10s %-10s %-11s %-10s %s" %
          ("V[m/s]", "δ_c[m]", "δ_c/dx", "k_eff(模型)", "k_eff(Aziz)",
           "L_eff/δ_c", "守恒漂移", "低估倍数"))
    print("  " + "-" * 92)
    for v in vlist:
        vt = float(v)
        d = os.path.join(root, f"v{v}")
        f = last_prof(d)
        if not f:
            print("  %-10s %-11.3e %-9.4f  没有剖面" % (v, D / vt, D / vt / dx))
            continue
        r = list(csv.DictReader(open(f)))
        xs = [float(x["x"]) for x in r]
        cs = [float(x["c"]) for x in r]
        cmax = max(cs)
        tot = sum(0.5 * ((cs[i] - C0) + (cs[i + 1] - C0)) * (xs[i + 1] - xs[i])
                  for i in range(len(xs) - 1))
        keff = C0 / cmax
        Leff = tot / (cmax - C0) if cmax > C0 else float("nan")
        DC = D / vt
        # Aziz 物理截留
        Vd = D / A0
        kaz = (KE + vt / Vd) / (1.0 + vt / Vd)
        # 低估倍数：以模型的 k_eff 相对 Aziz 物理值
        under = (1 - kaz) / (1 - keff) if keff < 1 else float("inf")
        dr = ""
        fo = os.path.join(d, "case_out.csv")
        if os.path.exists(fo):
            rows = list(csv.DictReader(open(fo)))
            kk = [c for c in rows[0] if "total_c" in c]
            if len(rows) > 1 and kk:
                try:
                    a, b = float(rows[0][kk[0]]), float(rows[-1][kk[0]])
                    dr = "%.1e" % (abs(b - a) / abs(a))
                except (TypeError, ValueError):
                    pass
        print("  %-10s %-11.3e %-9.4f %-10.6f %-10.6f %-11.3f %-10s %.1f×" %
              (v, DC, DC / dx, keff, kaz, Leff / DC, dr, under))
    print()
    print("  读法：")
    print("    * `k_eff(模型)` 越接近 1 ⇒ 界面几乎不排溶质 ⇒ **没有微偏析**")
    print("    * `k_eff(Aziz)` 是物理上的截留值（a0=0.3nm，LPBF 下几乎不截留，≈k_e）")
    print("    * **低估倍数 = (1−k_Aziz)/(1−k_模型)**，即模型少排了多少倍溶质")


if __name__ == "__main__":
    main(sys.argv[1],
         sys.argv[2].split() if len(sys.argv) > 2 else ["0.6"],
         int(sys.argv[3]) if len(sys.argv) > 3 else 160)
