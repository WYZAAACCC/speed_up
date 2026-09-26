#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1D 晶界 Gibbs 验证 —— 结果分析（读 params.json + gb_out.csv，不解析日志）

列序（MOOSE 按字母序写 CSV）：time, D_max, D_min, c_edge, c_max, c_min, hgb_max, total_c
"""
import csv
import json
import os
import sys

R = 8.314462618
V_M = 9.873e-6
C0 = 0.036


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/mnt/f/speed_up/pipeline/gibbs/results"
    rows = []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        try:
            m = json.load(open(os.path.join(p, "params.json"), encoding="utf-8"))
            r = list(csv.DictReader(open(os.path.join(p, "gb_out.csv"))))
        except Exception as e:
            print("  %-18s 读失败 %s" % (d, e))
            continue
        if not r:
            continue
        last, first = r[-1], r[0]

        def f(k):
            return float(last[k])

        cmax, cmin, cedge, ctot = f("c_max"), f("c_min"), f("c_edge"), f("total_c")
        hmax, dmin, dmax = f("hgb_max"), f("D_min"), f("D_max")
        jit = int((open(os.path.join(p, "jit.txt")).read().strip() or "1"))
        ncv = int((open(os.path.join(p, "nconv.txt")).read().strip() or "1"))
        c_ana, s_ana = m["c_GB_analytic"], m["s_analytic"]
        Glen = ctot - cedge * m["ldom"]
        Gm = m["rho_mol"] * Glen
        Gt = m["Gamma_phys_target"]
        drift = (ctot - float(first["total_c"])) / float(first["total_c"])
        fcc = R * m["T"] / (V_M * C0 * (1 - C0))
        wc = (m["kappa_c"] / fcc) ** 0.5
        rows.append(dict(tag=d, T=m["T"], kc=m["kappa_c"], dx=m["dx"], wgb=m["wgb"],
                         wc=wc, wcdx=wc / m["dx"], cmax=cmax, cana=c_ana,
                         err=(cmax - c_ana) / c_ana, s=cmax / cedge, sana=s_ana,
                         Gm=Gm, Gt=Gt, gr=Gm / Gt, drift=drift, cmin=cmin,
                         hmax=hmax, dmin=dmin, dmax=dmax, jit=jit, ncv=ncv,
                         nstep=len(r)))

    if not rows:
        print("没有结果")
        return

    print()
    print("=" * 122)
    print(" 核心判据：PDE 解出的峰 c_GB  vs  精确 McLean  c_GB/(1-c_GB)=(c0/(1-c0))*exp(-dG/(RT))")
    print("=" * 122)
    for T in sorted({r["T"] for r in rows}, reverse=True):
        grp = sorted([r for r in rows if r["T"] == T], key=lambda x: -x["kc"])
        print()
        print("  --- T = %.0f K ---" % T)
        print("  %-18s %-8s %-7s %-7s %11s %11s %9s %9s %9s %9s %8s" %
              ("tag", "kappa_c", "w_c/dx", "dx(m)", "c_max", "McLean",
               "偏差", "s_实测", "s_解析", "Γ比", "守恒漂移"))
        print("  " + "-" * 118)
        for r in grp:
            print("  %-18s %-8.0e %-7.2f %-7.3g %11.7f %11.7f %8.2f%% %9.4f %9.4f %9.3f %8.1e"
                  % (r["tag"], r["kc"], r["wcdx"], r["dx"], r["cmax"], r["cana"],
                     r["err"] * 100, r["s"], r["sana"], r["gr"], r["drift"]))
        best = min(grp, key=lambda x: abs(x["err"]))
        print("  ⇒ 最接近解析: kappa_c=%.0e（偏差 %+.2f%%，w_c/dx=%.2f）"
              % (best["kc"], best["err"] * 100, best["wcdx"]))
        print("  ⇒ 随 kappa_c 减小 |偏差| 是否单调降 ⇒ 见上表（判据：应收敛到 0）")

    print()
    print("=" * 122)
    print(" 温度依赖检查（s 应跟随 McLean 的高温稀释）")
    print("=" * 122)
    print("  %-6s %11s %11s %9s %9s" % ("T(K)", "s_实测(best kc)", "s_解析", "Γ比", "c_min"))
    for T in sorted({r["T"] for r in rows}, reverse=True):
        grp = [r for r in rows if r["T"] == T]
        b = min(grp, key=lambda x: abs(x["err"]))
        print("  %-6.0f %11.4f %11.4f %9.3f %9.5f" % (T, b["s"], b["sana"], b["gr"], b["cmin"]))

    print()
    print("=" * 122)
    print(" 健康检查")
    print("=" * 122)
    bad = [r for r in rows if r["jit"] != 0 or r["ncv"] != 0 or r["cmin"] <= 0]
    print("  JIT 失败 / 未收敛 / c_min<=0 的档数: %d  %s" %
          (len(bad), [r["tag"] for r in bad] if bad else "（无）"))
    print("  h_gb_max 范围: %.4f ~ %.4f （应 ~1）" %
          (min(r["hmax"] for r in rows), max(r["hmax"] for r in rows)))
    print("  D_min 范围: %.4e ~ %.4e （应 D_S=4e-13）" %
          (min(r["dmin"] for r in rows), max(r["dmin"] for r in rows)))
    print("  D_max 范围: %.4e ~ %.4e （应 D_GB=4e-10）" %
          (min(r["dmax"] for r in rows), max(r["dmax"] for r in rows)))


if __name__ == "__main__":
    main()