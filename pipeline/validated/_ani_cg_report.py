#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`run_ani_cg.sh` 的报告：从 `case_out.csv` 读 `gr0_total` / `gr1_total`。

判据：`gr0` 的面积分数 = `gr0_total/(gr0_total+gr1_total)`。
它从 0.5 出发；**单调上升 = 竞争生长在起作用**；恒为 0.5 = 无择优。
"""
import csv
import os
import sys


def read(path):
    if not os.path.exists(path):
        return []
    rows = list(csv.DictReader(open(path, encoding="utf-8", errors="replace")))
    out = []
    for r in rows:
        try:
            a = float(r["gr0_total"])
            b = float(r["gr1_total"])
            t = float(r["time"])
        except (KeyError, TypeError, ValueError):
            continue
        if a + b > 0:
            out.append((t, a / (a + b)))
    return out


def main():
    root, alist = sys.argv[1], sys.argv[2].split()
    print("  %-8s %-12s %-11s %-11s %s" %
          ("A_ani", "末态 t", "面积分数 初", "面积分数 末", "相对 A=0 末态"))
    print("  " + "-" * 70)
    res = {}
    for a in alist:
        s = read(os.path.join(root, f"a{a}", "case_out.csv"))
        if len(s) < 2:
            print("  %-8s ⚠ 没拿到 CSV（超时/失败？）" % a)
            continue
        res[a] = (s[0][0], s[0][1], s[-1][0], s[-1][1])
        print("  %-8s %-12.3e %-11.4f %-11.4f" %
              (a, res[a][2], res[a][1], res[a][3]))

    print()
    if "0" not in res:
        print("  ⚠ 没有 A=0 的对照档 ⇒ 判读不完整")
        return
    _, _, _, f0 = res["0"]
    print(f"  对照 A=0：末态面积分数 {f0:.4f}（应当 ≈ 0.5，即无择优）")
    if abs(f0 - 0.5) > 0.02:
        print("  ⚠⚠ **对照档自己就偏了 0.5** ⇒ 测试构型有问题，下面的判读不成立")
        return
    print()
    print("  读法：面积分数越高 = 与梯度对齐的那个晶粒吃得越多 = 择优越强")
    print()
    for a in sorted(res, key=float):
        f = res[a][3]
        print(f"    A_ani = {a:<7} 末态 {f:.4f}   （相对 A=0：{f - f0:+.4f}）")
    print()
    hi = max(v[3] for v in res.values())
    gain_hi = hi - f0
    if gain_hi < 0.02:
        print("  ⇒ ⚠ **A_ani 在这个构型上几乎不产生择优**（最大增益 %.4f）" % gain_hi)
        print("     ⇒ 那柱状晶就不是生长选择产生的，是热梯度本身 —— **这本身是结论**。")
    else:
        phys = [(a, res[a][3]) for a in res if float(a) <= 0.05]
        if phys:
            pa, pf = max(phys, key=lambda kv: kv[1])
            frac = (pf - f0) / gain_hi if gain_hi else 0.0
            print(f"  ⇒ 物理量级（A ≤ 0.05）里最强的是 A = {pa}，增益 {pf - f0:+.4f}"
                  f"（= 最大增益的 {frac*100:.0f}%）")
            if frac > 0.5:
                print(f"     ✅ **在物理量级上择优就已达饱和值的一半以上 ⇒ 0.7 是多余的**")
            else:
                print(f"     ⚠ 择优主要靠 A > 0.05 ⇒ 需要重新审视这个参数")
        else:
            print("  ⚠ 没有 ≤0.05 的档，无法判读物理量级")


if __name__ == "__main__":
    main()
