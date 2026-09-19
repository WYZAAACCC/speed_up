#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重做 run_kc_vs_keff.sh / run_kc_fix_res.sh 的分析。

## 为什么单独写一个
两个脚本里的分析取了 `fs[0]` —— 而 `LineValueSampler` 是**每个时间步写一个 CSV**
（`case_out_prof_0000.csv` … `case_out_prof_0406.csv`）。`os.listdir` 的顺序不保证是
时间序，所以 `fs[0]` 拿到的是**随机一个时间步的剖面**，不是末态。仿真本身没问题，
只是读错了文件。（这是本轮第二个「读错文件」的坑。）

本脚本：**按编号排序取最后一个**，并用 `case_out.csv` 的 `total_c` 校守恒、
用剖面里最后一行的 `time` 确认真的跑到了 end_time。

## 精确关系（模型自洽，与 κ_c 和网格都无关）

    ∫(c−c0)dz = 2·M·A·c0 / V            （CH 方程积分一次严格得到）
    k_eff = c0/c_max = 1/(1 + 2MA/(V·L_eff))
    ⇒ 目标 k_e = 1/(1+2A/k_c)      ⇔    L_eff = δ_c = D/V

用法：
    python3 report_kc_keff.py kc   <root>          # κ_c 扫描
    python3 report_kc_keff.py res  <root>          # s × nx 扫描
"""
import csv
import math
import os
import re
import sys

# --- front1d.i 的算例常数 ---
XI = 2.0e-6          # η 界面宽
LMOB = 5.833e-4
DG = 3.6e5
K_C = 0.9            # k_c
A = 0.264            # A_part
C0 = 0.036
M0 = 2.8e-9          # 基准 M（= D_L/k_c）
V = 3.0 * XI * LMOB * DG
KE = 1.0 / (1.0 + 2 * A / K_C)
DOM = 4.0e-5


def last_prof(d):
    """取**编号最大**的 prof CSV（= 末态）。"""
    if not os.path.isdir(d):
        return None
    fs = [x for x in os.listdir(d)
          if "prof" in x and x.endswith(".csv")]
    if not fs:
        return None

    def num(f):
        m = re.search(r"_(\d+)\.csv$", f)
        return int(m.group(1)) if m else -1

    return os.path.join(d, max(fs, key=num))


def read_prof(d):
    f = last_prof(d)
    if not f:
        return None
    r = list(csv.DictReader(open(f)))
    if not r or "c" not in r[0]:
        return None
    xs = [float(x["x"]) for x in r]
    cs = [float(x["c"]) for x in r]
    # 时间列可能叫 time 或不在（LineValueSampler 不含 time）——从文件名推不了，
    # 所以另读 case_out.csv 的末行拿 t / 守恒。
    return xs, cs, r


def total_drift(d):
    f = os.path.join(d, "case_out.csv")
    if not os.path.exists(f):
        return None, None
    try:
        rows = list(csv.DictReader(open(f)))
    except Exception:
        return None, None
    if len(rows) < 2:
        return None, None
    key = [k for k in rows[0] if "total_c" in k]
    tkey = [k for k in rows[0] if k.strip() == "time"]
    t = float(rows[-1][tkey[0]]) if tkey else float("nan")
    if not key:
        return t, None
    try:
        v0, v1 = float(rows[0][key[0]]), float(rows[-1][key[0]])
        return t, abs(v1 - v0) / abs(v0)
    except (TypeError, ValueError):
        return t, None


def metrics(d, C0_=C0):
    out = read_prof(d)
    if not out:
        return None
    xs, cs, _ = out
    cmax = max(cs)
    tot = sum(0.5 * ((cs[i] - C0_) + (cs[i + 1] - C0_)) * (xs[i + 1] - xs[i])
              for i in range(len(xs) - 1))
    keff = C0_ / cmax if cmax else float("nan")
    Leff = tot / (cmax - C0_) if cmax > C0_ else float("nan")
    t, drift = total_drift(d)
    return dict(cmax=cmax, tot=tot, keff=keff, Leff=Leff, t=t, drift=drift)


def head(tot_pred):
    print(f"  平衡分配 k_e = 1/(1+2A/k_c) = {KE:.6f}")
    print(f"  V = {V:.4e} m/s   δ_c(s=1) = D/V = {M0*K_C/V:.4e} m")
    print(f"  精确预测 ∫(c−c0)dx = 2MAc0/V = {tot_pred:.6e}（与 κ_c、网格无关）")
    print()


def report_kc(root, kclist):
    TOT = 2 * M0 * A * C0 / V
    DC = M0 * K_C / V
    head(TOT)
    print("  %-11s %-8s %-7s %-11s %-9s %-12s %-10s %-9s %s" %
          ("kappa_c", "ℓ_c[µm]", "P=ℓ_c/δc", "k_eff", "vs k_e", "∫(c−c0)dx",
           "L_eff[µm]", "L_eff/δc", "t_end"))
    print("  " + "-" * 100)
    rows = []
    for kc in kclist:
        lc = math.sqrt(float(kc) / K_C)
        d = os.path.join(root, "kc_" + kc)
        m = metrics(d)
        if not m:
            print("  %-11s %-8.3f %-7.3f  （没有剖面）" % (kc, lc * 1e6, lc / DC))
            continue
        rows.append((kc, lc, m))
        print("  %-11s %-8.3f %-7.3f %-11.6f %+-7.2f%% %-12.5e %-10.3f %-9.2f %.2e" %
              (kc, lc * 1e6, lc / DC, m["keff"], 100 * (m["keff"] - KE) / KE,
               m["tot"], m["Leff"] * 1e6, m["Leff"] / DC, m["t"]))
    print()
    if rows:
        dd = [abs(m["tot"] - TOT) / TOT for _, _, m in rows]
        print(f"  ∫(c−c0)dx 相对精确式 2MAc0/V 的最大偏差 = {max(dd)*100:.3f}%"
              f"   ⇒ {'精确关系成立 ✓' if max(dd) < 0.03 else '⚠ 需查（可能没到稳态）'}")
        dr = [m["drift"] for _, _, m in rows if m["drift"] is not None]
        if dr:
            print(f"  守恒漂移最大 = {max(dr):.2e}（判据 1e-8）")
        a, b = rows[0], rows[-1]
        print(f"  κ_c {a[0]} → {b[0]}：k_eff {a[2]['keff']:.4f} → {b[2]['keff']:.4f}"
              f"；L_eff/δ_c {a[2]['Leff']/DC:.2f} → {b[2]['Leff']/DC:.2f}（目标 1.00）")
        if abs(b[2]["keff"] - KE) / KE < 0.02:
            print("  ✅ **只改 κ_c 就把 k_eff 拉回平衡值** ⇒ 缺口 #3 是参数漏改，不是物理缺陷")
        else:
            print("  ⚠ k_eff 仍未到平衡值 ⇒ 还有别的机制（看 L_eff/δ_c 停在几）")


def report_res(root, slist, nwlist):
    print("  %-6s %-9s %-10s %-9s %-11s %-9s %-11s %-8s" %
          ("s", "δ_c[µm]", "δ_c/dx", "ξ/dx", "k_eff", "vs k_e", "L_eff/δ_c", "t_end"))
    print("  " + "-" * 88)
    for s in slist:
        sv = float(s)
        D = XI * V / sv
        DC = D / V
        for nx in nwlist:
            dx = DOM / int(nx)
            d = os.path.join(root, f"s{s}_n{nx}")
            m = metrics(d)
            if not m:
                continue
            flag = ""
            if abs(m["keff"] - KE) / KE < 0.02:
                flag = " ✅"
            elif m["keff"] > KE + 0.05:
                flag = " ← 被网格卡住"
            print("  %-6s %-9.4f %-10.2f %-9.2f %-11.6f %+-7.2f%% %-11.2f %-8.2e%s" %
                  (s, DC * 1e6, DC / dx, XI / dx, m["keff"],
                   100 * (m["keff"] - KE) / KE, m["Leff"] / DC, m["t"], flag))
        print()


if __name__ == "__main__":
    mode, root = sys.argv[1], sys.argv[2]
    if mode == "kc":
        lst = sys.argv[3].split() if len(sys.argv) > 3 else \
            ["1.125e-11", "1e-12", "1e-13", "1e-14", "1e-15"]
        report_kc(root, lst)
    else:
        sl = sys.argv[3].split() if len(sys.argv) > 3 else ["0.5", "1", "2", "4"]
        nl = sys.argv[4].split() if len(sys.argv) > 4 else ["40", "160"]
        report_res(root, sl, nl)
