#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_f3chk.py <tag>... —— 检查 **`F3` 面片是否坍缩**（`R695` 的疑点）。

## 为什么要查
`B2L_pre` 的日志显示：`F3` 面数 **3036 → 13**、`nslab` **6 → 1**
⇒ **6 根板条合并成 1 个连通区**。
⚠ 若 `C4`（此前所有 `Λ` 读数的来源）也这样，则
**"长厚比 8.03" 可能测的是"整块 vs 腔"，而不是"单根板条"** ⇒ **解释需修正**。

## 判据
* `F3` 面数与面积随时间的变化；
* **`F3` 面积坍缩的步号**（用于确定 `Λ` 读数的**有效窗口**）。
"""
import csv
import os
import sys

ROOTS = [
    "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
    "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
]
TAGS = sys.argv[1:] or ["B2L_pre", "C4", "G4", "W0"]


def find(tag):
    for r in ROOTS:
        p = os.path.join(r, "dry_%s" % tag, "series.csv")
        if os.path.exists(p):
            return p
    return None


print("=" * 104)
print("`F3` 面片坍缩检查 —— 若面数掉到个位数，`Λ`/`f_flat` 的解释与有效窗口都要改")
print("=" * 104)
for t in TAGS:
    p = find(t)
    if not p:
        print("\n【%s】无 series.csv" % t)
        continue
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    if not rows:
        print("\n【%s】空" % t)
        continue
    cols = list(rows[0].keys())
    fc = next((c for c in cols if c.startswith("nf3")), None)
    ar = next((c for c in cols if c.startswith("f3_area_m2")), None)
    ns = next((c for c in cols if "nslab" in c), None)
    print("\n【%s】%d 行；列：nf3=%s  f3_area=%s  nslab=%s" % (t, len(rows), fc, ar, ns))
    if fc is None:
        print("     ⚠ 找不到 nf3 列")
        continue
    picks = [i for i in range(len(rows))
             if i % max(1, len(rows) // 7) == 0] + [len(rows) - 1]
    for i in sorted(set(picks)):
        r = rows[i]
        a = float(r[ar]) * 1e12 if ar else float('nan')
        print("     step %-5s  nf3=%-7s  f3_area=%.4f µm²  nslab=%s  Vt=%s"
              % (r.get("step"), r.get(fc), a, r.get(ns, "—"),
                 (float(r["Vt"]) if r.get("Vt") else float('nan'))))
