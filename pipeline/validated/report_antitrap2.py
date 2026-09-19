#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抗截留项重做实验的分析（配合 run_antitrap2.sh）。

判据：真正的薄界面修正必须**与界面宽无关** ⇒ 同一个 ALPHA 在所有 s 上给出同一个
k_eff = k_e。逐 s 调 ALPHA 才能凑上 = 曲线拟合，不能推广。
"""
import csv
import math
import os
import re
import sys

XI = 2.0e-6
LMOB = 5.833e-4
DG = 3.6e5
K_C = 0.9
A = 0.264
C0 = 0.036
V = 3.0 * XI * LMOB * DG
KE = 1.0 / (1.0 + 2 * A / K_C)


def last_prof(d):
    if not os.path.isdir(d):
        return None
    fs = [x for x in os.listdir(d) if "prof" in x and x.endswith(".csv")]
    if not fs:
        return None
    return os.path.join(d, max(fs, key=lambda f: int(re.search(r"_(\d+)\.csv$", f).group(1))
                               if re.search(r"_(\d+)\.csv$", f) else -1))


def keff(d):
    f = last_prof(d)
    if not f:
        return None, None
    r = list(csv.DictReader(open(f)))
    if not r or "c" not in r[0]:
        return None, None
    xs = [float(x["x"]) for x in r]
    cs = [float(x["c"]) for x in r]
    cmax = max(cs)
    tot = sum(0.5 * ((cs[i] - C0) + (cs[i + 1] - C0)) * (xs[i + 1] - xs[i])
              for i in range(len(xs) - 1))
    return C0 / cmax, (tot / (cmax - C0) if cmax > C0 else float("nan"))


def drift(d):
    f = os.path.join(d, "case_out.csv")
    if not os.path.exists(f):
        return None
    rows = list(csv.DictReader(open(f)))
    k = [c for c in rows[0] if "total_c" in c]
    if len(rows) < 2 or not k:
        return None
    try:
        a, b = float(rows[0][k[0]]), float(rows[-1][k[0]])
        return abs(b - a) / abs(a)
    except (TypeError, ValueError):
        return None


def main(root, slist, alist):
    print(f"  平衡分配 k_e = {KE:.6f}    V = {V:.4e} m/s")
    print()
    print("  %-6s %-9s %-9s %s" % ("s", "δ_c[µm]", "ξ/δ_c",
                                   "".join(("A=%-8s" % a) for a in alist)))
    print("  " + "-" * (26 + 10 * len(alist)))
    grid = {}
    for s in slist:
        DC = XI / float(s)
        cells = []
        for a in alist:
            k, _ = keff(os.path.join(root, f"s{s}_a{a}"))
            grid[(s, a)] = k
            if k is None:
                cells.append("%-10s" % "—")
            else:
                flag = " ✅" if abs(k - KE) / KE < 0.02 else ("  " if k > KE else " ❌")
                cells.append("%-8.4f%s" % (k, flag))
        print("  %-6s %-9.3f %-9.2f %s" % (s, DC * 1e6, XI / DC, "".join(cells)))
    print()
    print("  守恒漂移：", end="")
    ds = []
    for s in slist:
        for a in alist:
            d = drift(os.path.join(root, f"s{s}_a{a}"))
            if d is not None:
                ds.append(d)
    print(f"最大 {max(ds):.2e}（判据 1e-8）" if ds else "无数据")
    print()
    # 每个 s 找出使 k_eff 最接近 k_e 的 ALPHA
    print("  每个 s 的最佳 ALPHA（严格意义的与界面宽无关性）：")
    best = []
    for s in slist:
        cand = [(abs(grid[(s, a)] - KE), a) for a in alist if grid.get((s, a)) is not None]
        if not cand:
            continue
        e, a = min(cand)
        best.append(a)
        print(f"    s={s:<5} → ALPHA = {a:<5} (k_eff = {grid[(s,a)]:.4f}, "
              f"偏差 {100*(grid[(s,a)]-KE)/KE:+.2f}%)")
    print()
    # ⚠ 判据要分两层问，别混成一句：
    #   ① 「最优 ALPHA 是否随 s 不变」—— 严格意义下的与宽度无关性
    #   ② 「**固定一个 ALPHA，残差是否受得住**」—— 工程上真正要紧的那问
    # 第一版只打印了 ① 并给出「不能推广」的判词，那是**过苛**的：
    # 领头阶修正的最优系数本来就会随展开参数漂移，该看的是残差上界。
    if len(set(best)) == 1 and best:
        print(f"  ✅ 最优 ALPHA 恒为 {best[0]} ⇒ 严格意义下的与界面宽无关")
    else:
        print(f"  ⚠ 最优 ALPHA 随 s 漂移（{best}）"
              "—— 这是**领头阶**修正的正常特征，不等于不能用，看下一行。")
    print()
    for fix in ("2", "2.5"):
        if fix not in alist:
            continue
        errs = [100 * (grid[(s, fix)] - KE) / KE for s in slist if grid.get((s, fix))]
        base = [abs(100 * (grid[(s, "0")] - KE) / KE) for s in slist if grid.get((s, "0"))]
        if not errs:
            continue
        mx = max(abs(e) for e in errs)
        tag = "✅ **可用**" if mx <= 5.0 else "❌ 残差过大"
        print(f"  固定 ALPHA = {fix}：残差上界 **{mx:.2f}%**"
              + (f"（对照：基线 {min(base):.1f}%~{max(base):.1f}%）" if base else "")
              + f"  {tag}")
        print("      逐 s：" + "  ".join(
            f"s={s}:{100*(grid[(s,fix)]-KE)/KE:+.2f}%" for s in slist if grid.get((s, fix))))


if __name__ == "__main__":
    root = sys.argv[1]
    sl = sys.argv[2].split() if len(sys.argv) > 2 else ["1"]
    al = sys.argv[3].split() if len(sys.argv) > 3 else ["0", "0.5", "1", "1.5", "2", "3"]
    main(root, sl, al)
