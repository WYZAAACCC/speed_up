#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1D 晶界子模型可行性验证 —— 结果分析

配 run_gb_submodel_1d.sh。判据见该脚本头部注释。

读法（AGENTS.md 教训 20）：
  s = c_max / c_edge   —— 从**剖面**读，不从守恒量的差反推。
  c_edge 是远场（elementid 0）的当前值，不是初值 c_grain；
  封闭系统里 int(c - c_grain)dx 恒等于 0，用它反推会得到 0。
"""
import csv
import os
import sys

# ---- 生产常数（逐字取自 stage1_meltpool_c.i 的 [free_energy]）----
K_C, A_PART, C0, OMEGA0 = 0.9, 0.264, 0.036, -5e-11
DEN = K_C + 2 * A_PART                       # 1.428
C_S = K_C * C0 / DEN                         # 固相线成分 = 0.022689
A_H4 = 4 * abs(OMEGA0) / (DEN * C_S)         # 闭式，h_gb 峰值取 4
A_H1 = A_H4 / 4.0                            # 闭式，h_gb 峰值取 1
T11 = 1.3533e-9                              # T11 实测锚定（wGB=0.4 um 档反解）


def read_cases(root):
    cases = []
    p = os.path.join(root, "cases.txt")
    if not os.path.exists(p):
        return cases
    for ln in open(p, encoding="utf-8"):
        f = ln.split()
        if len(f) == 5:
            cases.append(dict(tag=f[0], dx=float(f[1]) * 1e-9,
                              wgb=float(f[2]) * 1e-9, ldom=float(f[3]) * 1e-9,
                              tend=float(f[4])))
    return cases


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/root/work/gb_sub1d"
    rows = []
    for c in read_cases(root):
        fp = os.path.join(root, c["tag"], "gb_out.csv")
        if not os.path.exists(fp):
            continue
        r = list(csv.DictReader(open(fp)))
        if not r:
            continue
        last = r[-1]
        prev = r[-2] if len(r) > 1 else last
        try:
            cmax, cmin = float(last["c_max"]), float(last["c_min"])
            cedge = float(last["c_edge"])
            hmax = float(last.get("hgb_max", "nan"))
        except (KeyError, ValueError) as e:
            print("  %s: 读列失败 %s; 可用列 %s" % (c["tag"], e, sorted(last.keys())))
            continue
        c = dict(c)
        c.update(cmax=cmax, cmin=cmin, cedge=cedge, hmax=hmax,
                 s=cmax / cedge if cedge else float("nan"),
                 dc=cmax - cmin,
                 prev_cmax=float(prev["c_max"]),
                 droptime=abs(cmax - float(prev["c_max"])) / max(abs(cmax), 1e-30),
                 nrows=len(r))
        rows.append(c)

    if not rows:
        print("没有结果。检查 %s" % root)
        return

    print()
    print("=" * 100)
    print(" 结果（s 从剖面读：c_max / c_edge）")
    print("=" * 100)
    print("  %-15s %8s %8s %11s %11s %9s %10s %9s" %
          ("tag", "dx(nm)", "wgb(nm)", "c_max", "c_edge", "s", "dc", "h_gb_max"))
    print("  " + "-" * 96)
    for r in rows:
        print("  %-15s %8.3f %8.2f %11.6f %11.6f %9.4f %10.5f %9.4f" %
              (r["tag"], r["dx"] * 1e9, r["wgb"] * 1e9,
               r["cmax"], r["cedge"], r["s"], r["dc"], r["hmax"]))

    print()
    print("=" * 100)
    print(" 判据 (2)：(s-1)*wgb 应该是常数   [wgb 单位 m]")
    print("=" * 100)
    print("  候选：  h_gb峰值=4 闭式 %.4e    h_gb峰值=1 闭式 %.4e    T11锚定 %.4e"
          % (A_H4, A_H1, T11))
    print("  候选比值： h4 / h1 = %.2f    h4 / T11 = %.2f    h1 / T11 = %.2f"
          % (A_H4 / A_H1, A_H4 / T11, A_H1 / T11))
    print()
    print("  %-15s %9s %10s %14s   %s" %
          ("tag", "wgb(nm)", "s", "(s-1)*wgb", "与三个候选的比"))
    print("  " + "-" * 96)
    bs = sorted([x for x in rows if x["tag"].startswith("B_")], key=lambda x: x["wgb"])
    for r in bs:
        inv = (r["s"] - 1.0) * r["wgb"]
        print("  %-15s %9.2f %10.4f %14.4e   h4=%+.2fx  h1=%+.2fx  T11=%+.2fx" %
              (r["tag"], r["wgb"] * 1e9, r["s"], inv,
               inv / A_H4, inv / A_H1, inv / T11))
    if len(bs) >= 2:
        invs = [(x["s"] - 1.0) * x["wgb"] for x in bs]
        mx, mn = max(invs), min(invs)
        print()
        print("  全档 (s-1)*wgb 的范围： %.4e ~ %.4e   最大/最小 = %.2f  （判据：应 ~1）"
              % (mn, mx, mx / mn))

    print()
    print("=" * 100)
    print(" 判据 (1)：主判据 —— wgb = 2 nm 的 s 落在 3~10 吗？")
    print("=" * 100)
    main = [r for r in rows if r["tag"] == "B_wgb2nm"]
    if main:
        r = main[0]
        ok = "PASS" if 3.0 <= r["s"] <= 10.0 else "FAIL"
        print("  s = %.4f    dc = %.5f    c_GB = %.5f    (判据 3~10)  -> %s"
              % (r["s"], r["dc"], r["cmax"], ok))
        print("  平衡自检：末态与上一步 c_max 的相对差 = %.2e  （应 << 1）" % r["droptime"])
    else:
        print("  缺 B_wgb2nm")

    print()
    print("=" * 100)
    print(" A 组（wgb=2nm 固定，扫 dx）：s 应随 dx->0 收敛")
    print("=" * 100)
    a = sorted([r for r in rows if r["tag"].startswith("A_")], key=lambda x: -x["dx"])
    for i, r in enumerate(a):
        d = "" if i == 0 else "   相对上一档 %+.2f%%" % ((r["s"] - a[i - 1]["s"]) / a[i - 1]["s"] * 100)
        print("  %-15s dx=%.3f nm   wgb/dx=%5.1f   s=%.5f%s"
              % (r["tag"], r["dx"] * 1e9, r["wgb"] / r["dx"], r["s"], d))


if __name__ == "__main__":
    main()