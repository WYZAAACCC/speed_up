#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`run_ani_sweep.sh` 的报告：从各档的 run.log 里取 `align_melt` 时间序列。

⚠ 生产日志里有**很多张表**，列数会撞车（两列的表不止 `align_melt` 一张）。
所以必须**按表头认表**，不能按列数猜 —— 第一版就是这么读错的。
"""
import os
import re
import sys


def read_table(path, colname):
    """从 MOOSE 日志里取包含 colname 的那张表，返回 (time, value) 序列。"""
    if not os.path.exists(path):
        return []
    x = re.sub(r"\x1b\[[0-9;]*m", "",
               open(path, encoding="utf-8", errors="replace").read())
    lines = x.splitlines()
    out, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("|") and colname in s:
            hdr = [c.strip() for c in s.strip("|").split("|")]
            j, rows = i + 1, []
            while j < len(lines):
                r = lines[j].strip()
                if r.startswith("+"):
                    j += 1
                    continue
                if not r.startswith("|"):
                    break
                cells = [c.strip() for c in r.strip("|").split("|")]
                try:
                    d = dict(zip(hdr, [float(c) for c in cells]))
                except ValueError:
                    d = None
                if d and hdr[0] in d and colname in d:
                    rows.append(d)
                j += 1
            if rows:
                out = rows
            i = j
        else:
            i += 1
    return out


def main():
    root, alist = sys.argv[1], sys.argv[2].split()
    print("  %-8s %-12s %-14s %-14s %s" %
          ("A_ani", "末态 t", "align_melt 初", "align_melt 末", "变化"))
    print("  " + "-" * 68)
    res = {}
    for a in alist:
        p = os.path.join(root, f"a{a}", "run.log")
        rows = read_table(p, "align_melt")
        if len(rows) < 2:
            print("  %-8s ⚠ 没拿到 align_melt（超时/失败？）" % a)
            continue
        t0, v0 = rows[0]["time"], rows[0]["align_melt"]
        t1, v1 = rows[-1]["time"], rows[-1]["align_melt"]
        res[a] = (v0, v1)
        print("  %-8s %-12.3e %-14.5f %-14.5f %+.5f" % (a, t1, v0, v1, v1 - v0))

    print()
    if len(res) < 2:
        print("  数据不足，无法判读")
        return
    print("  读法：`align_melt` = **熔池区域**里 η 场与热梯度方向的对齐度")
    print("        0.5 = 完全随机；1.0 = 完全对齐（= 强择优/柱状晶）")
    print()
    a0 = res.get("0", (None, None))[1]
    for a in sorted(res, key=float):
        v0, v1 = res[a]
        d = ""
        if a0 is not None and a != "0":
            d = f"（末态相对 A=0 高 {v1 - a0:+.5f}）"
        print(f"    A_ani = {a:<7} 初 {v0:.5f} → 末 {v1:.5f}   {d}")

    print()
    if a0 is None:
        print("  ⚠ 没有 A=0 的对照档 ⇒ 判读不完整")
        return
    hi = max(v1 for _, v1 in res.values())
    if hi - a0 < 0.005:
        print("  ⇒ ⚠ **A_ani 在熔池区域几乎不产生择优**（相对 A=0 的差别 < 0.005）。")
        print("     ⇒ 那么柱状晶来自**热梯度本身**（模型本来就有 L ∝ exp(−Q/kbT)，")
        print("        液相迁移率比固相高 27 个数量级），而不是生长选择。")
        print("     ⇒ **这本身是结论**（见 PARAMETER_PROVENANCE.md §3.4 的建议①）。")
    else:
        phys = [v1 for a, (_, v1) in res.items() if float(a) <= 0.05]
        if phys and max(phys) - a0 > 0.5 * (hi - a0):
            print("  ⇒ ✅ 在**物理量级**（A ≤ 0.05）上择优就已达到饱和值的**一半以上**")
            print("     ⇒ **0.7 是多余的**，可以降到物理量级。")
        else:
            print("  ⇒ ⚠ 择优主要来自 A > 0.05 的取值")
            print("     ⇒ 若坚持要出柱状织构，需要重新审视这个参数（并给出理由）。")


if __name__ == "__main__":
    main()
